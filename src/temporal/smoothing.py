"""只在连续有效区间平滑，不跨越缺失数据。"""
import numpy as np
from scipy.signal import savgol_filter


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
