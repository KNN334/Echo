"""左室连通区域、轮廓关键点及面积/长轴特征；关键点为代理估计。"""
import numpy as np
from scipy import ndimage
from .volume import single_plane_volume


def main_component(mask):
    """保留最大连通区域并填洞，同时返回其占比。"""
    lab, n = ndimage.label(np.asarray(mask, bool))
    if n == 0:
        return np.zeros_like(mask, bool), 0.
    sizes = np.bincount(lab.ravel())
    sizes[0] = 0
    largest = lab == sizes.argmax()
    return ndimage.binary_fill_holes(largest), float(sizes.max() / max(1, (lab > 0).sum()))

def infer_landmarks(mask, spacing_xy=(1., 1.)):
    """假定图像纵轴向下，用轮廓主轴估计关键点；旋转或非标准切面需复核。"""
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
    # 在长轴靠基底的 40% 区间搜索最宽横截面，减少单个离群像素的影响。
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
    """从左室掩膜提取面积、长轴、直径及有标定时的容积估计。"""
    clean, component_fraction = main_component(mask)
    if clean.sum() < 10:
        return {"valid": False, "reason": "empty_or_tiny_LV", "volume_ml": None, "area_pixels": int(clean.sum())}
    # 缺少空间标定时只保留像素几何量，不能把 pixel³ 当成 mL。
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
    # 在物理坐标中沿横截面密集采样，兼容横纵像素间距不相等的情况。
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
            "volume_ml": single_plane_volume(area, length) if calibrated else None,
            "volume_pixel3": single_plane_volume(area, length, calibrated=False) if not calibrated else None,
            "volume_method": "single_plane_area_length_approximation"}
