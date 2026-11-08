import numpy as np
from scipy import ndimage


def segmentation_metrics(pred, truth, spacing_xy=None):
    p, g = np.asarray(pred, bool), np.asarray(truth, bool)
    if p.shape != g.shape:
        raise ValueError("mask dimensions differ")
    total = p.sum() + g.sum()
    dice = float(2 * (p & g).sum() / total) if total else None
    result = {"dice": dice, "assd": None, "hd95": None, "hd_max": None,
              "distance_unit": "mm" if spacing_xy is not None else "pixel",
              "distance_status": "ok"}
    if not p.any() or not g.any():
        result["distance_status"] = "empty_prediction_or_reference"
        return result
    ps = p & ~ndimage.binary_erosion(p)
    gs = g & ~ndimage.binary_erosion(g)
    sampling = tuple(spacing_xy[::-1]) if spacing_xy is not None else (1., 1.)
    p2g = ndimage.distance_transform_edt(~gs, sampling=sampling)[ps]
    g2p = ndimage.distance_transform_edt(~ps, sampling=sampling)[gs]
    d = np.concatenate([p2g, g2p])
    result.update(assd=float(d.mean()), hd95=float(np.percentile(d, 95)), hd_max=float(d.max()))
    return result


def landmark_errors(pred, truth, spacing_xy=None):
    if pred is None or truth is None:
        return None
    spacing = np.array(spacing_xy if spacing_xy is not None else [1., 1.])
    return {key: float(np.linalg.norm((np.asarray(pred[key]) - np.asarray(truth[key])) * spacing))
            for key in ("apex", "base_left", "base_right")}


def mae_summary(rows, keys=("EDV", "ESV", "SV", "EF", "CO"), seed=2026):
    """Patient-level paired means; bootstrap patient means to avoid pseudo-replication."""
    units = {"EDV": "mL", "ESV": "mL", "SV": "mL", "EF": "percentage_points", "CO": "L/min"}
    rng = np.random.default_rng(seed)
    result = {}
    for key in keys:
        grouped = {}
        for row in rows:
            p, r = row.get(key), row.get("ref_" + key)
            if p is not None and r is not None and np.isfinite(p) and np.isfinite(r):
                grouped.setdefault(row["patient_id"], []).append(float(p-r))
        means = np.array([np.mean(x) for x in grouped.values()])
        errors = np.array([np.mean(np.abs(x)) for x in grouped.values()])
        if not len(means):
            result[key] = {"mae": None, "n_patients": 0, "unit": units[key], "reason": "no_valid_paired_reference"}
            continue
        boot = [float(rng.choice(errors, len(errors), replace=True).mean()) for _ in range(1000)] if len(errors) > 1 else None
        sd = float(means.std(ddof=1)) if len(means) > 1 else None
        result[key] = {"mae": float(errors.mean()), "bias": float(means.mean()), "n_patients": len(means),
                       "unit": units[key], "mae_ci95": np.percentile(boot, [2.5,97.5]).tolist() if boot else None,
                       "patient_mean_limits_of_agreement": [float(means.mean()-1.96*sd),float(means.mean()+1.96*sd)] if sd is not None else None}
    return result
