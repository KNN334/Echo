"""Label-free ED/ES phase detection and cycle-derived cardiac indicators."""

from __future__ import annotations

import numpy as np
from scipy.signal import find_peaks


def cycle_metrics(volumes, timestamps_s, *, complete_cycle: bool,
                  volume_unit: str = "mL", calibrated_volume: bool = True,
                  min_period_s: float = 0.30, max_period_s: float = 2.50,
                  prominence_fraction: float = 0.04) -> dict:
    volumes = np.asarray(volumes, dtype=float)
    times = np.asarray(timestamps_s, dtype=float)
    if volumes.ndim != 1 or times.shape != volumes.shape:
        raise ValueError("Volumes and timestamps must be equal-length vectors")
    if len(times) < 3 or not np.isfinite(times).all() or np.any(np.diff(times) <= 0):
        return {"ed_frames": [], "es_frames": [], "events": [], "cycles": [],
                "status": "unreliable_time_axis",
                "status_reason": "timestamps_missing_nonfinite_or_nonmonotonic"}
    delta = float(np.median(np.diff(times)))
    if min_period_s <= 0 or max_period_s <= min_period_s:
        raise ValueError("Cycle period limits must be positive and increasing")
    distance = max(1, int(np.ceil(min_period_s / delta)))
    finite = np.isfinite(volumes) & (volumes > 0)
    segments = []
    indices = np.flatnonzero(finite)
    if len(indices):
        breaks = np.flatnonzero(np.diff(indices) > 1) + 1
        segments = np.split(indices, breaks)
    cycles = []
    events = []
    for segment in segments:
        if len(segment) < 3:
            continue
        curve = volumes[segment]
        prominence = max(float(np.ptp(curve)) * prominence_fraction, 1e-9)
        local, _ = find_peaks(curve, distance=distance, prominence=prominence)
        local_peaks = set(int(index) for index in local)
        if len(curve) >= 2 and curve[0] >= curve[1] and curve[0] - np.min(curve) >= prominence:
            local_peaks.add(0)
        if len(curve) >= 2 and curve[-1] >= curve[-2] and curve[-1] - np.min(curve) >= prominence:
            local_peaks.add(len(curve) - 1)
        local_valleys, _ = find_peaks(-curve, prominence=prominence)
        local_troughs = set(int(index) for index in local_valleys)
        if len(curve) >= 2 and curve[0] <= curve[1] and np.max(curve) - curve[0] >= prominence:
            local_troughs.add(0)
        if len(curve) >= 2 and curve[-1] <= curve[-2] and np.max(curve) - curve[-1] >= prominence:
            local_troughs.add(len(curve) - 1)
        local_peaks = sorted(int(index) for index in local_peaks)
        local_troughs = sorted(int(index) for index in local_troughs)
        for position, local_ed in enumerate(local_peaks):
            local_end = local_peaks[position + 1] if position + 1 < len(local_peaks) else len(segment)
            es_candidates = [index for index in local_troughs if local_ed < index < local_end]
            if not es_candidates:
                continue
            local_es = min(es_candidates, key=lambda index: curve[index])
            ed, es = int(segment[local_ed]), int(segment[local_es])
            edv, esv = float(volumes[ed]), float(volumes[es])
            if esv >= edv or edv <= 0:
                continue
            event = {"ed_frame": ed, "es_frame": es,
                     "ed_time_s": float(times[ed]), "es_time_s": float(times[es]),
                     "EDV": edv, "ESV": esv, "SV": edv - esv,
                     "volume_unit": volume_unit,
                     "EF_percent": 100.0 * (edv - esv) / edv,
                     "next_ed_frame": None, "T_s": None, "HR_bpm": None,
                     "CO_ml_per_min": None, "CO_L_per_min": None,
                     "CO_proxy_per_min": None,
                     "HR_unavailable_reason": None, "CO_unavailable_reason": None}
            if complete_cycle and position + 1 < len(local_peaks):
                next_ed = int(segment[local_peaks[position + 1]])
                period = float(times[next_ed] - times[ed])
                event.update(next_ed_frame=next_ed, next_ed_time_s=float(times[next_ed]), T_s=period)
                if min_period_s <= period <= max_period_s:
                    hr = 60.0 / period
                    event["HR_bpm"] = hr
                    if calibrated_volume:
                        event.update(CO_ml_per_min=event["SV"] * hr,
                                     CO_L_per_min=event["SV"] * hr / 1000.0)
                    else:
                        event["CO_proxy_per_min"] = event["SV"] * hr
                    cycles.append(event)
                else:
                    event["HR_unavailable_reason"] = "detected_period_outside_configured_range"
            if event["HR_bpm"] is None and event["HR_unavailable_reason"] is None:
                event["HR_unavailable_reason"] = (
                    "source_sequence_not_verified_as_complete_cycle" if not complete_cycle else
                    "no_adjacent_detected_EDV_peak")
            if not calibrated_volume:
                event["CO_unavailable_reason"] = "missing_spatial_calibration"
            elif event["CO_L_per_min"] is None:
                event["CO_unavailable_reason"] = (
                    event["HR_unavailable_reason"] or "missing_valid_EDV_ESV_pair")
            events.append(event)
    events.sort(key=lambda event: event["ed_frame"])
    if cycles:
        status, status_reason = "ok", None
    elif not complete_cycle:
        status, status_reason = "incomplete_cycle", "source_sequence_not_verified_as_complete_cycle"
    elif not any(event["HR_bpm"] is not None for event in events):
        status, status_reason = "no_complete_peak_pair", "fewer_than_two_detected_EDV_peaks"
    else:
        status, status_reason = "no_valid_period", "all_detected_periods_outside_configured_range"
    return {"ed_frames": [event["ed_frame"] for event in events],
            "es_frames": [event["es_frame"] for event in events],
            "events": events, "cycles": cycles, "status": status,
            "status_reason": status_reason}


def bland_altman(predicted, reference, *, unit: str = "mL") -> dict:
    predicted = np.asarray(predicted, dtype=float)
    reference = np.asarray(reference, dtype=float)
    valid = np.isfinite(predicted) & np.isfinite(reference)
    predicted, reference = predicted[valid], reference[valid]
    if not len(predicted):
        return {"n": 0, "unit": unit, "bias": None, "loa_lower": None, "loa_upper": None}
    difference = predicted - reference
    bias = float(difference.mean())
    sd = float(difference.std(ddof=1)) if len(difference) > 1 else None
    return {"n": int(len(difference)), "unit": unit, "bias": bias,
            "loa_lower": bias - 1.96 * sd if sd is not None else None,
            "loa_upper": bias + 1.96 * sd if sd is not None else None}
