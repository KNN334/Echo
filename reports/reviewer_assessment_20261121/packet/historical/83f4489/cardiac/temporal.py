"""时序分析：在有效连续区间平滑容积，仅依据可用时间信息识别完整心搏。"""
import numpy as np
from scipy.signal import find_peaks, savgol_filter
from .geometry import functional


def smooth_curve(volumes, valid, window=5):
    """只在连续有效区间内平滑容积曲线，不跨越无效帧插值。"""
    values = np.asarray(volumes, float).copy()
    mask = np.asarray(valid, bool) & np.isfinite(values)
    cuts = np.diff(np.r_[False, mask, False].astype(int))
    for start, end in zip(np.flatnonzero(cuts == 1), np.flatnonzero(cuts == -1)):
        w = min(window, end-start)
        w -= 1-w % 2
        if w >= 3:
            values[start:end] = savgol_filter(values[start:end], w, 2)
    return values


def detect_beats(volumes, timestamps, valid, min_hr=30, max_hr=200):
    """依据实际时间戳识别完整周期；缺失时间或间断区间不补造周期。"""
    if timestamps is None:
        return []
    t, v = np.asarray(timestamps, float), np.asarray(volumes, float)
    good = np.asarray(valid, bool) & np.isfinite(v)
    if len(t) < 3 or len(t) != len(v) or np.any(np.diff(t) <= 0):
        return []
    # 每个有效区间单独找峰；边界峰缺少完整周期，不能用于心率估计。
    cuts = np.diff(np.r_[False, good, False].astype(int))
    rows = []
    for start, end in zip(np.flatnonzero(cuts == 1), np.flatnonzero(cuts == -1)):
        peaks, _ = find_peaks(v[start:end], distance=max(1, int(60/max_hr/np.median(np.diff(t)))),
                              prominence=max(1e-6, np.ptp(v[start:end]) * .1))
        peaks += start
        for ed, nxt in zip(peaks[:-1], peaks[1:]):
            # 相邻舒张末期峰定义一个周期，其间容积最小帧为收缩末期。
            hr = 60 / (t[nxt]-t[ed])
            if not min_hr <= hr <= max_hr or not np.all(good[ed:nxt+1]):
                continue
            es = ed + int(np.argmin(v[ed:nxt+1]))
            f = functional(float(v[ed]), float(v[es]), float(hr))
            if f["SV"] is not None:
                rows.append({"ed_frame": int(ed), "es_frame": int(es), "next_ed_frame": int(nxt),
                             "ed_time_s": float(t[ed]), "next_ed_time_s": float(t[nxt]), **f})
    return rows


def quality_flags(features, roi_reviewed, confidence=None):
    """为分割几何质量问题生成标记，不改变人工审核状态。"""
    flags = []
    if not features.get("valid"):
        flags.append(features.get("reason", "invalid_geometry"))
    if features.get("touches_image_edge"):
        flags.append("LV_touches_image_edge")
    if features.get("largest_component_fraction", 1) < .9:
        flags.append("fragmented_segmentation")
    if not roi_reviewed:
        flags.append("roi_not_reviewed")
    if confidence is not None and confidence < .65:
        flags.append("low_segmentation_confidence")
    return flags
