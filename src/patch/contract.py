"""Validation for patch acquisition records and evidence boundaries.

The contract deliberately accepts planning records with missing values. Missing
spatial or temporal evidence is reported as an explicit limitation instead of
being filled from a paper or a container playback rate.
"""

from pathlib import Path
import json

import numpy as np
import yaml


INPUT_LEVELS = {
    "channel_rf",
    "channel_iq",
    "beamformed_rf",
    "beamformed_iq",
    "envelope",
    "bmode",
}
EVIDENCE_KINDS = {"public_observed", "patch_observed", "simulated"}
REVIEW_STATES = {"pending", "reviewed", "rejected"}


def load_patch_record(path):
    """Load a JSON or YAML patch record without altering unknown fields."""
    path = Path(path)
    if path.suffix.lower() == ".json":
        return json.loads(path.read_text(encoding="utf-8"))
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _finite_positive_pair(value):
    try:
        array = np.asarray(value, dtype=float)
    except (TypeError, ValueError):
        return False
    return array.shape == (2,) and bool(np.all(np.isfinite(array) & (array > 0)))


def validate_patch_record(record, require_data=False):
    """Return a structured validation report for one patch session record.

    ``require_data=False`` is intended for planning templates. Set it to True
    at ingestion time to require a real input path and a checksum.
    """
    errors = []
    issues = []
    if not isinstance(record, dict):
        return {"valid": False, "errors": ["record_must_be_mapping"], "issues": []}
    if record.get("schema_version") != 1:
        errors.append("unsupported_schema_version")

    identity = record.get("identity") or {}
    if identity.get("evidence_kind") not in EVIDENCE_KINDS:
        errors.append("missing_or_invalid_evidence_kind")
    if identity.get("split") not in {None, "train", "val", "test", "development"}:
        errors.append("invalid_split")

    source = record.get("input") or {}
    level = source.get("level")
    if level not in INPUT_LEVELS:
        errors.append("missing_or_invalid_input_level")
    if require_data and not source.get("path"):
        errors.append("missing_input_path")
    if require_data and not source.get("sha256"):
        errors.append("missing_input_sha256")

    geometry = record.get("image_geometry") or {}
    calibrated = _finite_positive_pair(geometry.get("spacing_xy_mm"))
    map_path = geometry.get("pixel_to_physical_map_path")
    if not calibrated and not map_path:
        issues.append("missing_spatial_calibration")

    timing = record.get("timing") or {}
    has_verified_timing = bool(
        timing.get("frame_acquisition_times_s_path")
        or timing.get("verified_acquisition_fps")
    )
    if not has_verified_timing:
        issues.append("missing_verified_acquisition_timing")
    if timing.get("container_playback_fps") and not has_verified_timing:
        issues.append("playback_fps_not_acquisition_timing")
    cycle = timing.get("cycle_completeness", "unknown")
    if cycle not in {"unknown", "partial", "full"}:
        errors.append("invalid_cycle_completeness")
    if cycle != "full":
        issues.append("full_cycle_not_verified")

    processing = record.get("processing") or {}
    if level in {"channel_rf", "channel_iq"} and not processing.get("beamformer"):
        issues.append("beamformer_not_recorded")
    if level in {"channel_iq", "beamformed_iq"} and not source.get("complex_representation"):
        issues.append("iq_convention_not_recorded")

    review = record.get("review") or {}
    for name in (
        "metadata_review",
        "anatomy_and_view_review",
        "spatial_calibration_review",
        "timing_review",
        "independent_reference_review",
    ):
        state = review.get(name, "pending")
        if state not in REVIEW_STATES:
            errors.append(f"invalid_review_state:{name}")
    if review.get("metadata_review") != "reviewed":
        issues.append("metadata_review_pending")

    reference = record.get("reference") or {}
    independent_reference = bool(reference.get("independent_of_prediction_and_geometry"))
    outputs = {
        "can_compute_absolute_volume": bool(calibrated or map_path),
        "can_compute_hr": has_verified_timing and cycle == "full",
        "can_compute_co": has_verified_timing and cycle == "full" and independent_reference,
        "independent_reference_available": independent_reference,
    }
    return {
        "valid": not errors,
        "errors": errors,
        "issues": issues,
        "input_level": level,
        "spatial_calibrated": bool(calibrated or map_path),
        "timing_verified": has_verified_timing,
        "cycle_completeness": cycle,
        "outputs": outputs,
    }
