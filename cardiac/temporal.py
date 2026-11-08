import numpy as np
from scipy.signal import find_peaks, savgol_filter
from .geometry import functional


def smooth_curve(volumes, valid, window=5):
    """Only smooth contiguous valid segments; never bridge missing observations."""
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
    if timestamps is None:
        return []
    t, v = np.asarray(timestamps, float), np.asarray(volumes, float)
    good = np.asarray(valid, bool) & np.isfinite(v)
    if len(t) < 3 or len(t) != len(v) or np.any(np.diff(t) <= 0):
        return []
    # Peaks are detected on each valid segment; boundary maxima lack a complete beat.
    cuts = np.diff(np.r_[False, good, False].astype(int))
    rows = []
    for start, end in zip(np.flatnonzero(cuts == 1), np.flatnonzero(cuts == -1)):
        peaks, _ = find_peaks(v[start:end], distance=max(1, int(60/max_hr/np.median(np.diff(t)))),
                              prominence=max(1e-6, np.ptp(v[start:end]) * .1))
        peaks += start
        for ed, nxt in zip(peaks[:-1], peaks[1:]):
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
