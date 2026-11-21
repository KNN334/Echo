"""依据实际时间戳和完整峰间周期识别心搏。"""
import numpy as np
from scipy.signal import find_peaks
from ..geometry.functional import functional


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
