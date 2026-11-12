"""按患者汇总 MAE、偏倚和自助法区间。"""
import numpy as np


def mae_summary(rows, keys=("EDV", "ESV", "SV", "EF", "CO"), seed=2026):
    """先在患者内汇总配对误差，再按患者自助采样估计 MAE 区间，避免重复计数。"""
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
