"""Convert source CAMUS cine volumes to compact, auditable LV cases."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re

import numpy as np
from PIL import Image


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_info(path: Path) -> dict[str, str]:
    fields = {}
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        match = re.match(r"\s*([^:#]+?)\s*:\s*(.*?)\s*$", line)
        if match:
            fields[match.group(1).strip()] = match.group(2).strip()
    return fields


def _resize(array: np.ndarray, hw: tuple[int, int], *, mask: bool) -> np.ndarray:
    height, width = hw
    resample = Image.Resampling.NEAREST if mask else Image.Resampling.BILINEAR
    return np.stack([
        np.asarray(Image.fromarray(frame).resize((width, height), resample=resample))
        for frame in array
    ])


def _read_volume(path: Path) -> tuple[np.ndarray, tuple[float, float]]:
    import SimpleITK as sitk

    image = sitk.ReadImage(str(path))
    if image.GetDimension() != 3:
        raise ValueError(f"Expected a cine NIfTI volume, got {image.GetDimension()}D: {path}")
    frames = sitk.GetArrayFromImage(image)
    if frames.ndim != 3 or not len(frames):
        raise ValueError(f"Invalid cine frame array: {path}")
    spacing_x, spacing_y = image.GetSpacing()[:2]
    if min(spacing_x, spacing_y) <= 0:
        raise ValueError(f"Invalid physical pixel spacing: {path}")
    return frames, (float(spacing_x), float(spacing_y))


def prepare_camus(raw_root: str | Path, output_root: str | Path, split_path: str | Path,
                  *, image_hw: tuple[int, int] = (224, 320), overwrite: bool = False) -> dict:
    """Build 2CH/4CH full-frame cases; only ED/ES masks are marked labeled."""
    raw_root, output_root, split_path = map(Path, (raw_root, output_root, split_path))
    if len(image_hw) != 2 or any(int(value) < 32 or int(value) % 32 for value in image_hw):
        raise ValueError("image_hw must contain height and width divisible by 32")
    image_hw = tuple(map(int, image_hw))
    source_manifest_path = raw_root / "download_manifest.json"
    source_manifest = json.loads(source_manifest_path.read_text(encoding="utf-8"))
    if not source_manifest.get("complete"):
        raise ValueError("Raw CAMUS download is incomplete; prepare only a complete verified download")
    source_hashes = {row["path"]: row["sha256"] for row in source_manifest["files"]}
    assignments = json.loads(split_path.read_text(encoding="utf-8"))["patients"]
    if len(assignments) != 500 or set(assignments.values()) != {"train", "val", "test"}:
        raise ValueError("Expected fixed train/val/test patient assignments for all 500 CAMUS patients")
    if output_root.exists() and any(output_root.iterdir()) and not overwrite:
        raise FileExistsError(f"Prepared data directory is not empty: {output_root}")
    output_root.mkdir(parents=True, exist_ok=True)
    split_cases = {name: [] for name in ("train", "val", "test")}
    cases = []

    for patient_id in sorted(assignments):
        patient_raw = raw_root / patient_id
        for view in ("2CH", "4CH"):
            stem = f"{patient_id}_{view}_half_sequence"
            image_path, label_path = patient_raw / f"{stem}.nii.gz", patient_raw / f"{stem}_gt.nii.gz"
            info_path = patient_raw / f"Info_{view}.cfg"
            required = (image_path, label_path, info_path)
            for path in required:
                relative = path.relative_to(raw_root).as_posix()
                if not path.is_file() or relative not in source_hashes:
                    raise FileNotFoundError(f"Verified CAMUS source file is missing: {path}")
                if _sha256(path) != source_hashes[relative]:
                    raise ValueError(f"CAMUS source file changed after download: {path}")

            frames, spacing = _read_volume(image_path)
            source_labels, label_spacing = _read_volume(label_path)
            if source_labels.shape != frames.shape:
                raise ValueError(f"Image and expert-label cine dimensions differ: {patient_id} {view}")
            if not np.allclose(label_spacing, spacing, rtol=1e-5, atol=1e-6):
                raise ValueError(f"Image and expert-label physical spacing differ: {patient_id} {view}")
            info = _read_info(info_path)
            phase_indices = {name: int(info[name]) - 1 for name in ("ED", "ES")}
            fps = float(info["FrameRate"])
            if not np.isfinite(fps) or fps <= 0:
                raise ValueError(f"Invalid frame rate in {info_path}")
            if any(index < 0 or index >= len(frames) for index in phase_indices.values()):
                raise ValueError(f"ED/ES frame outside cine sequence: {patient_id} {view}")
            if phase_indices["ED"] == phase_indices["ES"]:
                raise ValueError(f"ED and ES frames must differ: {patient_id} {view}")

            labeled = np.zeros(len(frames), dtype=bool)
            labeled[list(phase_indices.values())] = True
            masks = np.zeros_like(frames, dtype=np.uint8)
            masks[list(phase_indices.values())] = (
                source_labels[list(phase_indices.values())] == 1).astype(np.uint8)
            if any(not masks[index].any() for index in phase_indices.values()):
                raise ValueError(f"An ED/ES expert LV mask is empty: {patient_id} {view}")

            prepared_frames = _resize(np.clip(np.rint(frames), 0, 255).astype(np.uint8),
                                      image_hw, mask=False)
            prepared_masks = _resize(masks, image_hw, mask=True).astype(np.uint8)
            case_id = f"{patient_id}_{view}"
            scale_x = image_hw[1] / frames.shape[2]
            scale_y = image_hw[0] / frames.shape[1]
            npz_path = output_root / f"{case_id}.npz"
            json_path = output_root / f"{case_id}.json"
            np.savez_compressed(npz_path, frames=prepared_frames, masks=prepared_masks,
                                labeled=labeled, original_shape=np.asarray(frames.shape[1:]),
                                original_gt=masks[labeled].copy(),
                                original_gt_indices=np.flatnonzero(labeled))
            metadata = {
                "case_id": case_id,
                "patient_id": patient_id,
                "view": view,
                "split": assignments[patient_id],
                "frame_count": int(len(frames)),
                "image_hw": list(image_hw),
                "original_hw": list(map(int, frames.shape[1:])),
                "spacing_xy_mm": list(spacing),
                "spacing_xy_mm_processed": [
                    spacing[0] * frames.shape[2] / image_hw[1],
                    spacing[1] * frames.shape[1] / image_hw[0],
                ],
                "transform": {
                    "original_to_prepared": [[scale_x, 0.0, 0.5 * scale_x - 0.5],
                                              [0.0, scale_y, 0.5 * scale_y - 0.5],
                                              [0.0, 0.0, 1.0]],
                    "prepared_to_original": [[1.0 / scale_x, 0.0, 0.5 / scale_x - 0.5],
                                              [0.0, 1.0 / scale_y, 0.5 / scale_y - 0.5],
                                              [0.0, 0.0, 1.0]],
                    "coordinate_convention": "PIL_resize_half_pixel_centers",
                },
                "fps": fps,
                "timestamps_s": (np.arange(len(frames), dtype=float) / fps).tolist(),
                "phases": phase_indices,
                "labeled_frames": sorted(phase_indices.values()),
                "sequence_type": "half_sequence",
                "complete_cycle_verified": False,
                "ground_truth_scope": "expert_ED_ES_frames_only",
                "source_files": {
                    path.name: {"sha256": source_hashes[path.relative_to(raw_root).as_posix()]}
                    for path in required
                },
            }
            json_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
            case = {"case_id": case_id, "patient_id": patient_id, "view": view,
                    "split": assignments[patient_id], "frame_count": len(frames),
                    "labeled_frames": list(phase_indices.values())}
            cases.append(case)
            split_cases[assignments[patient_id]].append(case)

    dataset_manifest = {
        "schema_version": 1,
        "dataset": "CAMUS",
        "source_manifest_sha256": _sha256(source_manifest_path),
        "license": source_manifest["license"],
        "patients": len(assignments),
        "cases": cases,
        "case_count": len(cases),
        "complete": len(cases) == 1000,
        "limitations": [
            "CAMUS sequences are half-cycle clips; no repeated ED peaks, HR, or CO are inferred.",
            "2CH and 4CH sequences are separate acquisitions and are not time-synchronized.",
            "Only expert ED/ES frames contribute segmentation supervision or manual-mask comparisons.",
        ],
    }
    (output_root / "manifest.json").write_text(json.dumps(dataset_manifest, indent=2), encoding="utf-8")
    for split, rows in split_cases.items():
        if not rows:
            raise ValueError(f"Patient split has no cases: {split}")
        split_path_out = output_root / "splits" / f"{split}.json"
        split_path_out.parent.mkdir(parents=True, exist_ok=True)
        split_path_out.write_text(json.dumps({"split": split, "dataset_root": "..",
                                              "cases": rows}, indent=2), encoding="utf-8")
    return {"patients": len(assignments), "cases": len(cases),
            "case_splits": {split: len(rows) for split, rows in split_cases.items()},
            "labeled_frames": sum(len(row["labeled_frames"]) for row in cases),
            "complete": dataset_manifest["complete"]}
