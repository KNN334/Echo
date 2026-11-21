import pytest

from src.patch.contract import validate_patch_record


def _record(**overrides):
    record = {
        "schema_version": 1,
        "identity": {"evidence_kind": "patch_observed", "split": "train"},
        "input": {"level": "bmode", "path": "frame.npz", "sha256": "abc"},
        "image_geometry": {"spacing_xy_mm": [0.4, 0.4]},
        "timing": {
            "verified_acquisition_fps": 30,
            "cycle_completeness": "full",
        },
        "review": {"metadata_review": "reviewed"},
        "reference": {"independent_of_prediction_and_geometry": True},
    }
    for key, value in overrides.items():
        record[key] = value
    return record


def test_complete_record_permits_only_evidenced_outputs():
    report = validate_patch_record(_record(), require_data=True)

    assert report["valid"]
    assert report["outputs"] == {
        "can_compute_absolute_volume": True,
        "can_compute_hr": True,
        "can_compute_co": True,
        "independent_reference_available": True,
    }


def test_missing_calibration_and_full_cycle_are_explicit_limits():
    record = _record(
        image_geometry={},
        timing={"container_playback_fps": 30, "cycle_completeness": "partial"},
        reference={},
    )
    report = validate_patch_record(record)

    assert report["valid"]
    assert report["outputs"]["can_compute_absolute_volume"] is False
    assert report["outputs"]["can_compute_hr"] is False
    assert report["outputs"]["can_compute_co"] is False
    assert "missing_spatial_calibration" in report["issues"]
    assert "playback_fps_not_acquisition_timing" in report["issues"]
    assert "full_cycle_not_verified" in report["issues"]


def test_require_data_rejects_untraceable_input():
    record = _record(input={"level": "channel_rf"})
    report = validate_patch_record(record, require_data=True)

    assert report["valid"] is False
    assert "missing_input_path" in report["errors"]
    assert "missing_input_sha256" in report["errors"]
    assert "beamformer_not_recorded" in report["issues"]


@pytest.mark.parametrize("level", ["channel_rf", "channel_iq", "beamformed_iq"])
def test_raw_or_iq_inputs_require_processing_metadata(level):
    record = _record(input={"level": level})
    report = validate_patch_record(record)

    assert report["valid"]
    if level == "channel_rf":
        assert "beamformer_not_recorded" in report["issues"]
    else:
        assert "iq_convention_not_recorded" in report["issues"]
