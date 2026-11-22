"""Evidence-contract status for the patch-inspired downstream pipeline."""

from __future__ import annotations


def case_stage_status(metadata):
    """Return explicit availability and reason for each downstream stage."""
    audit = metadata.get("audit", {})
    spacing = audit.get("spacing_xy_mm")
    timestamps = audit.get("timestamps_s")
    reference = dict(metadata.get("reference") or {})
    config = metadata.get("config") or {}
    for name in ("EF", "EDV", "ESV", "HR", "CO"):
        reference.setdefault(name, config.get(name))
    split_unit = metadata.get("patient_identity_scope")
    if split_unit is None:
        split_unit = "study_proxy" if metadata.get("dataset_kind") == "echonet_dynamic" else "patient"
    calibrated = isinstance(spacing, list) and len(spacing) == 2
    timed = isinstance(timestamps, list) and len(timestamps) >= 2
    full_cycle = bool(metadata.get("full_cycle_verified", False))
    has_hr = reference.get("HR") is not None or metadata.get("hr_reference") is not None
    has_co = reference.get("CO") is not None or metadata.get("co_reference") is not None

    def available(ok, reason):
        return {"status": "available" if ok else "unavailable", "reason": None if ok else reason}

    stages = {
        "input_bmode_or_video": available(True, ""),
        "lv_segmentation": available(bool(metadata.get("gt_scope")), "missing_expert_or_trace_masks"),
        "physical_geometry": available(calibrated, "missing_spatial_calibration"),
        "edv_esv": available(calibrated, "missing_spatial_calibration"),
        "sv": available(calibrated, "missing_spatial_calibration"),
        "ef": available(calibrated or metadata.get("dataset_kind") == "echonet_dynamic",
                        "missing_spatial_calibration_for_volume_ratio"),
        "hr": available(timed and full_cycle, "missing_verified_full_cycle_or_reliable_time"),
        "co": available(timed and full_cycle and has_hr and has_co,
                         "missing_verified_full_cycle_or_independent_HR_CO_reference"),
        "patient_level_split": available(split_unit == "patient", "dataset_has_no_patient_identifier"),
    }
    stages["dataset_reference_labels"] = available(
        any(reference.get(name) is not None for name in ("EF", "EDV", "ESV")),
        "missing_dataset_reference_labels")
    return stages


def aggregate_stage_status(metadata_values):
    """Aggregate case statuses without turning missing evidence into zeros."""
    metadata_values = list(metadata_values)
    names = sorted({name for meta in metadata_values for name in case_stage_status(meta)})
    result = {}
    for name in names:
        statuses = [case_stage_status(meta)[name] for meta in metadata_values]
        available = sum(item["status"] == "available" for item in statuses)
        reasons = sorted({item["reason"] for item in statuses if item["reason"]})
        result[name] = {
            "available_cases": available,
            "total_cases": len(statuses),
            "coverage": available / len(statuses) if statuses else 0.0,
            "status": "available" if available == len(statuses) and statuses else
                      "partial" if available else "unavailable",
            "reasons": reasons,
        }
    return result
