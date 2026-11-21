"""校验帧率、时间戳和空间标定，不推造缺失的生理信息。"""
import numpy as np


def audit_metadata(n_frames, spacing_xy=None, fps=None, timestamps_s=None, source=None):
    """校验帧数、像素间距和时间信息，不为缺失元数据臆造数值。"""
    issues = []
    spacing = None
    if spacing_xy is not None:
        a = np.asarray(spacing_xy, float)
        if a.shape != (2,) or not np.all(np.isfinite(a) & (a > 0)):
            raise ValueError("spacing_xy_mm must contain two finite positive values")
        spacing = a.tolist()
    else:
        issues.append("missing_spatial_calibration")
    if fps is not None and (not np.isfinite(fps) or fps <= 0):
        raise ValueError("fps must be positive and finite")
    t = None
    kind = "missing"
    if timestamps_s is not None:
        t = np.asarray(timestamps_s, float)
        if t.shape != (n_frames,) or not np.all(np.isfinite(t)) or np.any(np.diff(t) <= 0):
            raise ValueError("timestamps must match frames and be strictly increasing")
        kind = "provided"
        if len(t) > 1 and fps is not None and abs(np.median(np.diff(t)) * fps - 1) > 0.05:
            raise ValueError("fps and timestamps disagree by more than 5 percent")
    elif fps is not None:
        t = np.arange(n_frames, dtype=float) / fps
        kind = "derived_from_fps"
    else:
        issues.append("missing_timing_no_HR_or_CO")
    return {"n_frames": int(n_frames), "spacing_xy_mm": spacing,
            "fps": fps, "timestamps_s": None if t is None else t.tolist(),
            "timestamp_source": kind, "metadata_source": source or {}, "issues": issues}
