import numpy as np

from lvseg.metrics.cycles import bland_altman, cycle_metrics
from lvseg.metrics.volume import simpson_biplane, simpson_single_plane


def test_single_plane_simpson_disk_volume_uses_physical_pixel_spacing():
    mask = np.zeros((120, 50), dtype=bool)
    mask[10:110, 15:35] = True
    volume = simpson_single_plane(mask, (1.0, 1.0), disks=20)
    expected = np.pi / 4 * 20**2 * 100 / 1000
    assert np.isclose(volume, expected, rtol=0.08)


def test_biplane_simpson_uses_cross_plane_diameters():
    first = np.zeros((120, 50), dtype=bool)
    second = np.zeros((120, 50), dtype=bool)
    first[10:110, 15:35] = True
    second[10:110, 20:30] = True
    volume = simpson_biplane(first, second, (1, 1), (1, 1), disks=20)
    expected = np.pi / 4 * 20 * 10 * 100 / 1000
    assert np.isclose(volume, expected, rtol=0.10)


def test_cycle_metrics_find_ed_peaks_es_troughs_and_report_full_indicators():
    times = np.arange(0, 4.01, 0.01)
    volumes = 75 + 25 * np.cos(2 * np.pi * (times - 0.5))
    result = cycle_metrics(volumes, times, complete_cycle=True)
    assert len(result["ed_frames"]) == 4
    assert len(result["cycles"]) == 3
    cycle = result["cycles"][0]
    assert np.isclose(cycle["T_s"], 1.0, atol=0.02)
    assert np.isclose(cycle["HR_bpm"], 60.0, atol=2.0)
    assert np.isclose(cycle["SV"], 50.0, atol=1.0)
    assert np.isclose(cycle["EF_percent"], 50.0, atol=1.0)
    assert np.isclose(cycle["CO_L_per_min"], 3.0, atol=0.1)


def test_incomplete_cycle_never_claims_heart_rate_or_output():
    result = cycle_metrics([100, 80, 60, 40], [0, 0.1, 0.2, 0.3], complete_cycle=False)
    assert result["status"] == "incomplete_cycle"
    assert result["status_reason"] == "source_sequence_not_verified_as_complete_cycle"
    assert result["cycles"] == []


def test_complete_sequence_without_adjacent_detected_peaks_has_reasoned_null_hr():
    result = cycle_metrics([60, 100, 80, 70, 65], [0, 0.1, 0.2, 0.3, 0.4],
                           complete_cycle=True)
    assert result["status"] == "no_complete_peak_pair"
    assert result["events"][0]["HR_bpm"] is None
    assert result["events"][0]["HR_unavailable_reason"] == "no_adjacent_detected_EDV_peak"


def test_unscaled_full_video_keeps_hr_and_ef_but_marks_absolute_co_unavailable():
    times = np.arange(0, 3.01, 0.01)
    volumes = 75 + 25 * np.cos(2 * np.pi * times)
    result = cycle_metrics(volumes, times, complete_cycle=True,
                           volume_unit="pixel3_proxy", calibrated_volume=False)
    cycle = result["cycles"][0]
    assert cycle["HR_bpm"] is not None
    assert cycle["EF_percent"] > 0
    assert cycle["CO_ml_per_min"] is None
    assert cycle["CO_proxy_per_min"] is not None
    assert cycle["CO_unavailable_reason"] == "missing_spatial_calibration"


def test_cycle_detection_never_connects_ed_peaks_across_missing_volume_frames():
    volumes = [60, 100, 80, 70, np.nan, 60, 100, 80, 70]
    times = np.arange(len(volumes), dtype=float) * 0.1
    result = cycle_metrics(volumes, times, complete_cycle=True)
    assert result["status"] == "no_complete_peak_pair"
    assert len(result["events"]) == 2
    assert all(event["HR_bpm"] is None for event in result["events"])
    assert all(event["HR_unavailable_reason"] == "no_adjacent_detected_EDV_peak"
               for event in result["events"])


def test_bland_altman_reports_bias_and_limits_of_agreement():
    result = bland_altman([12, 18, 25], [10, 20, 22])
    assert result["n"] == 3
    assert np.isclose(result["bias"], 1.0)
    assert result["loa_lower"] < result["bias"] < result["loa_upper"]
