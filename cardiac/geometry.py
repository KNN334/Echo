"""Physical LV geometry. Heuristic landmarks are not manual anatomical truth."""
import numpy as np
from scipy import ndimage


def main_component(mask):
    lab, n = ndimage.label(np.asarray(mask, bool))
    if n == 0:
        return np.zeros_like(mask, bool), 0.
    sizes = np.bincount(lab.ravel())
    sizes[0] = 0
    largest = lab == sizes.argmax()
    return ndimage.binary_fill_holes(largest), float(sizes.max() / max(1, (lab > 0).sum()))


def infer_landmarks(mask, spacing_xy=(1., 1.)):
    """Image-down orientation assumed; review on rotated/nonstandard apical views."""
    mask, _ = main_component(mask)
    yx = np.argwhere(mask)
    if len(yx) < 10:
        return None
    xy = yx[:, ::-1] * np.array(spacing_xy)
    center = xy.mean(0)
    _, vec = np.linalg.eigh(np.cov(xy.T))
    axis = vec[:, -1]
    if axis[1] < 0:
        axis *= -1
    side = np.array([axis[1], -axis[0]])
    a, b = (xy - center) @ axis, (xy - center) @ side
    lo, hi = np.percentile(a, [.5, 99.5])
    apex_band = xy[a <= lo + .02 * (hi - lo)]
    apex = apex_band.mean(0)
    # Broadest basal cross-section in basal 40%; stable against a single outlying pixel.
    candidates = []
    for level in np.linspace(lo + .6 * (hi - lo), hi, 30):
        idx = np.abs(a - level) < max(min(spacing_xy), (hi - lo) / 50)
        if idx.sum() >= 3:
            ql, qr = np.percentile(b[idx], [1, 99])
            candidates.append((qr - ql, level, ql, qr))
    if not candidates:
        return None
    _, level, left, right = max(candidates)
    base = center + level * axis
    points = np.array([apex, base + left * side, base + right * side]) / spacing_xy
    if points[1, 0] > points[2, 0]:
        points[[1, 2]] = points[[2, 1]]
    return {"apex": points[0].tolist(), "base_left": points[1].tolist(), "base_right": points[2].tolist(),
            "source": "contour_PCA_heuristic_requires_review"}


def mask_features(mask, spacing_xy=None, landmarks=None, disks=20):
    clean, component_fraction = main_component(mask)
    if clean.sum() < 10:
        return {"valid": False, "reason": "empty_or_tiny_LV", "volume_ml": None, "area_pixels": int(clean.sum())}
    # Pixel geometry retained when calibration is unavailable; never call pixel^3 mL.
    spacing = np.array(spacing_xy if spacing_xy is not None else (1., 1.), float)
    points = landmarks or infer_landmarks(clean, spacing)
    if points is None:
        return {"valid": False, "reason": "landmarks_unavailable", "volume_ml": None}
    apex = np.array(points["apex"]) * spacing
    base = (np.array(points["base_left"]) + np.array(points["base_right"])) * spacing / 2
    direction = base - apex
    length = float(np.linalg.norm(direction))
    if length <= 0:
        return {"valid": False, "reason": "zero_long_axis", "volume_ml": None}
    axis = direction / length
    side = np.array([axis[1], -axis[0]])
    centers = (np.arange(disks) + .5) * length / disks
    widths = []
    # Oversampled binary line integral provides stable diameters in anisotropic pixels.
    extent = float(np.linalg.norm(np.array(clean.shape[::-1]) * spacing))
    step = min(spacing) / 2
    offset = np.arange(-extent / 2, extent / 2 + step, step)
    for t in centers:
        line = apex + t * axis + offset[:, None] * side
        coords = (line / spacing)[:, ::-1].T
        samples = ndimage.map_coordinates(clean.astype(float), coords, order=0, mode="constant", cval=0)
        widths.append(float(samples.sum() * step))
    area = float(clean.sum() * np.prod(spacing))
    calibrated = spacing_xy is not None
    y, x = np.where(clean)
    touches_edge = bool(np.any((y == 0) | (y == clean.shape[0]-1) | (x == 0) | (x == clean.shape[1]-1)))
    return {"valid": True, "area_pixels": int(clean.sum()), "area_mm2": area if calibrated else None,
            "long_axis_mm": length if calibrated else None, "long_axis_pixels": length if not calibrated else None,
            "landmarks_xy": points, "largest_component_fraction": component_fraction,
            "touches_image_edge": touches_edge, "diameters_mm": widths if calibrated else None,
            "volume_ml": float(8 * area**2 / (3 * np.pi * length) / 1000) if calibrated else None,
            "volume_pixel3": float(8 * area**2 / (3 * np.pi * length)) if not calibrated else None,
            "volume_method": "single_plane_area_length_approximation"}


def biplane_volume(a, b):
    if not a.get("valid") or not b.get("valid") or a.get("diameters_mm") is None or b.get("diameters_mm") is None:
        return None
    d1, d2 = np.array(a["diameters_mm"]), np.array(b["diameters_mm"])
    if len(d1) != len(d2):
        raise ValueError("biplane disk counts differ")
    # Explicit convention: equal normalized positions, shorter of the two long axes.
    length = min(a["long_axis_mm"], b["long_axis_mm"])
    return float(np.sum(np.pi * d1 * d2 / 4) * length / len(d1) / 1000)


def functional(edv, esv, hr=None):
    result = {"EDV": edv, "ESV": esv, "SV": None, "EF": None, "HR": hr, "CO": None, "issues": []}
    if edv is None or esv is None or not np.isfinite(edv) or not np.isfinite(esv) or not 0 <= esv < edv:
        result["issues"].append("invalid_or_missing_EDV_ESV")
        return result
    result.update(SV=float(edv - esv), EF=float(100 * (edv - esv) / edv))
    if hr is not None and np.isfinite(hr) and hr > 0:
        result["CO"] = float(result["SV"] * hr / 1000)
    else:
        result["issues"].append("missing_full_cycle_or_reference_HR_no_CO")
    return result
