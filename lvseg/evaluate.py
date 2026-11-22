"""Infer every frame; compare masks and Simpson volume only where labels exist."""

from __future__ import annotations

import csv
import json
from pathlib import Path
import time

import numpy as np
import torch
from PIL import Image

from .metrics.cycles import bland_altman, cycle_metrics
from .metrics.segmentation import overlap_metrics
from .metrics.volume import simpson_single_plane
from .models import build_model


def _write_csv(path: Path, rows: list[dict]):
    fields = sorted({key for row in rows for key in row})
    with path.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _predict(model, frames, mean, std, device, batch_size=4, threshold=0.5):
    result = []
    model.eval()
    with torch.inference_mode():
        for start in range(0, len(frames), batch_size):
            image = torch.from_numpy(frames[start:start + batch_size].copy()).float()[:, None] / 255.0
            image = (image - mean) / std
            result.extend((model(image.to(device)).sigmoid()[:, 0] >= threshold).cpu().numpy())
    return np.asarray(result, dtype=np.uint8)


def _case_data(dataset_root: Path, case: dict):
    case_id = case["case_id"]
    with np.load(dataset_root / f"{case_id}.npz", allow_pickle=False) as arrays:
        loaded = {name: arrays[name] for name in arrays.files}
    metadata = json.loads((dataset_root / f"{case_id}.json").read_text(encoding="utf-8"))
    frames, masks, labeled = loaded["frames"], loaded["masks"], loaded["labeled"].astype(bool)
    original_gt = {int(index): mask for index, mask in
                   zip(loaded["original_gt_indices"], loaded["original_gt"])}
    if frames.ndim != 3 or masks.shape != frames.shape or labeled.shape != (len(frames),):
        raise ValueError(f"Invalid prepared video case: {case_id}")
    if set(original_gt) != set(np.flatnonzero(labeled)):
        raise ValueError(f"Original expert masks and labeled-frame indices differ: {case_id}")
    return frames, masks, labeled, original_gt, metadata


def evaluate_model(checkpoint_path: str | Path, split_manifest: str | Path,
                   output_dir: str | Path, *, device: str = "auto", batch_size: int = 4,
                   threshold: float = 0.5, min_period_s: float = 0.30,
                   max_period_s: float = 2.50) -> dict:
    if not 0.0 < threshold < 1.0:
        raise ValueError("threshold must be between zero and one")
    checkpoint_path, split_manifest, output_dir = map(Path,
                                                       (checkpoint_path, split_manifest, output_dir))
    manifest_path = split_manifest.resolve()
    split_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    if split_data.get("split") != "test":
        raise ValueError("Final evaluation requires the fixed test manifest")
    dataset_root = (manifest_path.parent / split_data["dataset_root"]).resolve()
    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    run = checkpoint["run"]
    test_patients = {case["patient_id"] for case in split_data["cases"]}
    developed_patients = set(run["train_patients"]) | set(run["val_patients"])
    if test_patients & developed_patients:
        raise ValueError("Patient leakage between model development and final test split")
    if device == "auto":
        device = "cuda" if torch.cuda.is_available() else "cpu"
    torch.set_num_threads(2)
    model = build_model(checkpoint["model"],
                        base_channels=checkpoint["model_config"]["base_channels"]).to(device)
    model.load_state_dict(checkpoint["state_dict"], strict=True)
    mean, std = checkpoint["normalization"]["mean"], checkpoint["normalization"]["std"]
    output_dir.mkdir(parents=True, exist_ok=True)
    masks_dir = output_dir / "predicted_masks"
    masks_dir.mkdir(exist_ok=True)
    frame_rows, label_rows, event_rows = [], [], []
    volume_by_patient_view = {}
    patient_dice = {}
    patient_iou = {}
    patient_miou = {}
    patient_other_metrics = {}
    started = time.time()

    for case_index, case in enumerate(split_data["cases"], start=1):
        frames, _, labeled, original_gt, metadata = _case_data(dataset_root, case)
        predicted_small = _predict(model, frames, mean, std, device, batch_size, threshold)
        original_h, original_w = metadata["original_hw"]
        spacing = metadata.get("spacing_xy_mm")
        if spacing is None:
            spacing_for_geometry = (1.0, 1.0)
            volume_unit = "pixel3_proxy"
        else:
            spacing_for_geometry = spacing
            volume_unit = "mL"
        unit_scale = 1000.0 if spacing is None else 1.0
        predictions = [np.asarray(Image.fromarray(mask).resize(
            (original_w, original_h), resample=Image.Resampling.NEAREST), dtype=np.uint8)
            for mask in predicted_small]
        np.savez_compressed(masks_dir / f"{case['case_id']}.npz",
                            masks=predictions, model_grid_masks=predicted_small)
        volumes = []
        times = metadata.get("timestamps_s")
        if times is None and metadata.get("fps"):
            times = (np.arange(len(frames)) / float(metadata["fps"])).tolist()
        for index, prediction in enumerate(predictions):
            volume_base = simpson_single_plane(prediction, spacing_for_geometry)
            volume = volume_base * unit_scale if volume_base is not None else None
            volumes.append(np.nan if volume is None else volume)
            row = {"patient_id": case["patient_id"], "case_id": case["case_id"],
                   "view": case["view"], "frame": index,
                   "time_s": times[index] if times is not None else None,
                   "volume": volume, "volume_unit": volume_unit,
                   "volume_unavailable_reason": (
                       None if volume is not None else "empty_or_invalid_predicted_lv_mask"),
                   "volume_method": "single_plane_simpson_disk",
                   "label_available": bool(labeled[index]),
                   "predicted_area_pixels": int(prediction.sum())}
            frame_rows.append(row)
            if labeled[index]:
                reference_mask = original_gt[index]
                scores = overlap_metrics(prediction, reference_mask, spacing)
                reference_base = simpson_single_plane(reference_mask, spacing_for_geometry)
                reference_volume = reference_base * unit_scale if reference_base is not None else None
                phase_name = next((phase for phase, frame in metadata.get("phases", {}).items()
                                   if int(frame) == index), "other_labeled_frame")
                label_rows.append({**row, **scores, "phase": phase_name,
                                   "reference_volume": reference_volume,
                                   "reference_volume_unavailable_reason": (
                                       None if reference_volume is not None else
                                       "empty_or_invalid_expert_lv_mask"),
                                   "volume_reference": "same_simpson_method_on_expert_mask",
                                   "volume_difference": (volume - reference_volume)
                                   if volume is not None and reference_volume is not None else None})
                patient_dice.setdefault(case["patient_id"], []).append(scores["dice"])
                patient_iou.setdefault(case["patient_id"], []).append(scores["iou"])
                patient_miou.setdefault(case["patient_id"], []).append(scores["miou"])
                patient_metrics = patient_other_metrics.setdefault(case["patient_id"], {})
                for metric in ("precision", "recall", "hd95", "asd"):
                    patient_metrics.setdefault(metric, []).append(scores[metric])
                patient_view = volume_by_patient_view.setdefault(
                    (case["patient_id"], case["view"]), [[], []])
                if volume is not None and reference_volume is not None:
                    patient_view[0].append(volume)
                    patient_view[1].append(reference_volume)

        event_summary = {"events": [], "cycles": [], "status": "missing_time_axis",
                         "status_reason": "timestamps_missing"}
        if times is not None:
            event_summary = cycle_metrics(
                volumes, times, complete_cycle=bool(metadata.get("complete_cycle_verified", False)),
                volume_unit=volume_unit, calibrated_volume=spacing is not None,
                min_period_s=min_period_s, max_period_s=max_period_s)
        predicted_phase_by_frame = {}
        for event in event_summary["events"]:
            predicted_phase_by_frame[event["ed_frame"]] = "EDV"
            predicted_phase_by_frame[event["es_frame"]] = "ESV"
            event_rows.append({"patient_id": case["patient_id"], "case_id": case["case_id"],
                               "view": case["view"], **event,
                               "cycle_status": event_summary["status"],
                               "cycle_status_reason": event_summary["status_reason"],
                               "sequence_type": metadata.get("sequence_type")})
        if not event_summary["events"]:
            event_rows.append({
                "patient_id": case["patient_id"], "case_id": case["case_id"],
                "view": case["view"], "ed_frame": None, "es_frame": None,
                "EDV": None, "ESV": None, "SV": None, "EF_percent": None,
                "T_s": None, "HR_bpm": None, "CO_ml_per_min": None,
                "CO_L_per_min": None, "CO_proxy_per_min": None,
                "HR_unavailable_reason": event_summary["status_reason"],
                "CO_unavailable_reason": (
                    "missing_spatial_calibration" if spacing is None else
                    event_summary["status_reason"]),
                "cycle_status": event_summary["status"],
                "cycle_status_reason": event_summary["status_reason"],
                "sequence_type": metadata.get("sequence_type"),
            })
        for phase, index in metadata.get("phases", {}).items():
            if labeled[int(index)]:
                frame_rows[len(frame_rows) - len(frames) + int(index)]["reference_phase"] = phase
        first_row = len(frame_rows) - len(frames)
        for offset, marker in predicted_phase_by_frame.items():
            frame_rows[first_row + offset]["detected_phase"] = marker
        if case_index % 10 == 0 or case_index == len(split_data["cases"]):
            print(f"{checkpoint['model']} test videos: {case_index}/"
                  f"{len(split_data['cases'])}", flush=True)

    patient_mean_pairs = []
    for (patient_id, view), (predicted, reference) in sorted(volume_by_patient_view.items()):
        if predicted and reference:
            patient_mean_pairs.append({"patient_id": patient_id, "view": view,
                                       "predicted": float(np.mean(predicted)),
                                       "reference": float(np.mean(reference))})
    ba_by_view_frames, ba_by_view_patients = {}, {}
    for view in sorted({row["view"] for row in label_rows}):
        unit = "mL" if "mL" in {row["volume_unit"] for row in label_rows if row["view"] == view} \
            else "pixel3_proxy"
        frame_pairs = [row for row in label_rows if row["view"] == view]
        ba_by_view_frames[view] = bland_altman(
            [row["volume"] for row in frame_pairs],
            [row["reference_volume"] for row in frame_pairs], unit=unit)
        patient_pairs = [row for row in patient_mean_pairs if row["view"] == view]
        ba_by_view_patients[view] = bland_altman(
            [row["predicted"] for row in patient_pairs],
            [row["reference"] for row in patient_pairs], unit=unit)
    per_patient_dice = {patient: float(np.mean(scores)) for patient, scores in patient_dice.items()}
    per_patient_iou = {patient: float(np.mean(scores)) for patient, scores in patient_iou.items()}
    per_patient_miou = {patient: float(np.mean(scores)) for patient, scores in patient_miou.items()}
    per_patient_metrics = {}
    for patient, metrics in patient_other_metrics.items():
        per_patient_metrics[patient] = {}
        for metric, values in metrics.items():
            valid = [value for value in values if value is not None and np.isfinite(value)]
            per_patient_metrics[patient][metric] = float(np.mean(valid)) if valid else None
    patient_metric_means = {}
    for metric in ("precision", "recall", "hd95", "asd"):
        values = [row[metric] for row in per_patient_metrics.values()
                  if row[metric] is not None]
        patient_metric_means[metric] = float(np.mean(values)) if values else None
    summary = {
        "model": checkpoint["model"], "test_patients": len(test_patients),
        "test_cines": len(split_data["cases"]), "inference_frames": len(frame_rows),
        "labeled_frames": len(label_rows),
        "unlabeled_inference_frames": sum(not row["label_available"] for row in frame_rows),
        "patient_mean_dice": float(np.mean(list(per_patient_dice.values()))) if per_patient_dice else None,
        "patient_mean_iou": float(np.mean(list(per_patient_iou.values()))) if per_patient_iou else None,
        "patient_mean_miou": float(np.mean(list(per_patient_miou.values()))) if per_patient_miou else None,
        "patient_mean_precision": patient_metric_means["precision"],
        "patient_mean_recall": patient_metric_means["recall"],
        "patient_mean_hd95": patient_metric_means["hd95"],
        "patient_mean_asd": patient_metric_means["asd"],
        "boundary_distance_unit": "mm" if spacing is not None else "pixel",
        "frame_mean_iou": float(np.mean([row["iou"] for row in label_rows])) if label_rows else None,
        "dice_by_patient": per_patient_dice,
        "iou_by_patient": per_patient_iou,
        "miou_by_patient": per_patient_miou,
        "segmentation_metrics_by_patient": per_patient_metrics,
        "volume_units": sorted({row["volume_unit"] for row in frame_rows}),
        "volume_bland_altman_by_labeled_frame_view": ba_by_view_frames,
        "volume_bland_altman_by_patient_view_means": ba_by_view_patients,
        "volume_bland_altman_note": "Frame-level Bland-Altman uses expert ED/ES masks and repeats within patient; patient-level analysis first averages labeled phases within each patient and view.",
        "phase_algorithm": "predicted_framewise_volume_extrema_without_label_input",
        "segmentation_threshold": threshold,
        "sequence_types": sorted({str(row.get("sequence_type")) for row in event_rows}),
        "event_count": sum(row.get("ed_frame") is not None for row in event_rows),
        "sequence_count": len(split_data["cases"]),
        "events_with_hr_estimate": sum(row.get("HR_bpm") is not None for row in event_rows),
        "events_with_calibrated_co": sum(
            row.get("CO_ml_per_min") is not None for row in event_rows),
        "events_with_proxy_co": sum(row.get("CO_proxy_per_min") is not None for row in event_rows),
        "elapsed_s": time.time() - started,
    }
    _write_csv(output_dir / "all_frame_volumes.csv", frame_rows)
    _write_csv(output_dir / "labeled_frame_metrics.csv", label_rows)
    _write_csv(output_dir / "phase_events.csv", event_rows)
    _write_csv(output_dir / "patient_view_volume_pairs.csv", patient_mean_pairs)
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary
