"""Prepare authorized EchoNet-Dynamic A4C videos for external evaluation."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
import re

import numpy as np
from PIL import Image, ImageDraw


def _key(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


def _field(row: dict, *names: str):
    keys = {_key(name) for name in names}
    return next((value for name, value in row.items() if _key(name) in keys), None)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_video(path: Path):
    import cv2

    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        raise ValueError(f"Could not open EchoNet video: {path}")
    fps = float(capture.get(cv2.CAP_PROP_FPS))
    frames = []
    while True:
        ok, bgr = capture.read()
        if not ok:
            break
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        frames.append(gray)
    capture.release()
    if not frames:
        raise ValueError(f"EchoNet video has no decoded frames: {path}")
    return np.stack(frames), fps


def _read_trace_index(csv_path: Path) -> dict:
    index = {}
    with csv_path.open(newline="", encoding="utf-8-sig") as stream:
        for row in csv.DictReader(stream):
            filename = Path(str(_field(row, "FileName"))).stem
            frame = int(_field(row, "Frame"))
            index.setdefault(filename, {}).setdefault(frame, []).append((
                float(_field(row, "X1")), float(_field(row, "Y1")),
                float(_field(row, "X2")), float(_field(row, "Y2")),
            ))
    return index


def _traced_masks(trace_index: dict, filename: str, n_frames: int, hw: tuple[int, int]):
    grouped = trace_index.get(Path(filename).stem, {})
    masks = np.zeros((n_frames, *hw), dtype=np.uint8)
    labeled = np.zeros(n_frames, dtype=bool)
    for frame, lines in grouped.items():
        if not 0 <= frame < n_frames:
            raise ValueError(f"EchoNet trace frame is outside the video: {filename} {frame}")
        points = np.asarray(lines, dtype=float)
        if len(points) < 3:
            continue
        polygon = np.concatenate((points[1:, :2], points[1:, 2:][::-1]), axis=0)
        canvas = Image.new("L", (hw[1], hw[0]))
        ImageDraw.Draw(canvas).polygon([tuple(point) for point in polygon], fill=1)
        mask = np.asarray(canvas, dtype=np.uint8)
        if mask.any():
            masks[frame] = mask
            labeled[frame] = True
    return masks, labeled


def _resize(array: np.ndarray, hw: tuple[int, int], *, mask: bool):
    height, width = hw
    resample = Image.Resampling.NEAREST if mask else Image.Resampling.BILINEAR
    return np.stack([np.asarray(Image.fromarray(frame).resize((width, height), resample))
                     for frame in array])


def prepare_echonet(raw_root: str | Path, output_root: str | Path, *,
                    image_hw: tuple[int, int] = (192, 256), limit: int | None = None) -> dict:
    """Decode all source frames; only supplied contours are marked labeled.

    Obtain the original videos through the Stanford AIMI portal after accepting
    the official research-use terms. This function does not fetch or redistribute
    the controlled dataset.
    """
    raw_root, output_root = Path(raw_root), Path(output_root)
    if len(image_hw) != 2 or any(int(value) < 32 or int(value) % 32 for value in image_hw):
        raise ValueError("image_hw must contain height and width divisible by 32")
    image_hw = tuple(map(int, image_hw))
    filelist_path, traces_path = raw_root / "FileList.csv", raw_root / "VolumeTracings.csv"
    videos_root = raw_root / "Videos"
    if not filelist_path.is_file() or not traces_path.is_file() or not videos_root.is_dir():
        raise FileNotFoundError("Expected FileList.csv, VolumeTracings.csv, and Videos/ from authorized data")
    with filelist_path.open(newline="", encoding="utf-8-sig") as stream:
        rows = list(csv.DictReader(stream))
    if not rows:
        raise ValueError("EchoNet FileList.csv is empty")
    selected = rows[:limit] if limit else rows
    source_hashes = {path.name: _sha256(path) for path in (filelist_path, traces_path)}
    trace_index = _read_trace_index(traces_path)
    output_root.mkdir(parents=True, exist_ok=True)
    cases, failures = [], []
    for row in selected:
        value = _field(row, "FileName", "Filename")
        filename = Path(str(value)).name
        if Path(filename).suffix.lower() != ".avi":
            filename += ".avi"
        video_path = videos_root / filename
        try:
            frames, video_fps = _read_video(video_path)
            fps_value = _field(row, "FPS", "FrameRate")
            fps = float(fps_value) if fps_value not in (None, "") else video_fps
            if not np.isfinite(fps) or fps <= 0:
                raise ValueError(f"EchoNet video lacks a valid frame rate: {filename}")
            masks, labeled = _traced_masks(trace_index, filename, len(frames),
                                           tuple(frames.shape[1:]))
            height, width = frames.shape[1:]
            prepared_frames = _resize(frames, image_hw, mask=False).astype(np.uint8)
            prepared_masks = _resize(masks, image_hw, mask=True).astype(np.uint8)
            stem = Path(filename).stem
            case_id = "echonet_" + re.sub(r"[^A-Za-z0-9_.-]+", "_", stem)
            split = str(_field(row, "Split") or "").strip().lower()
            split = {"valid": "val", "validation": "val"}.get(split, split)
            if split not in {"train", "val", "test"}:
                raise ValueError(f"Unknown official EchoNet split {split!r} for {filename}")
            patient_value = _field(row, "PatientID", "Patient", "SubjectID")
            patient_id = str(patient_value).strip() if patient_value else f"study_{stem}"
            case = {"case_id": case_id, "patient_id": patient_id, "view": "A4C",
                    "split": split, "frame_count": len(frames),
                    "labeled_frames": np.flatnonzero(labeled).tolist()}
            np.savez_compressed(output_root / f"{case_id}.npz", frames=prepared_frames,
                                masks=prepared_masks, labeled=labeled,
                                original_gt=masks[labeled],
                                original_gt_indices=np.flatnonzero(labeled),
                                original_shape=np.asarray([height, width]))
            ed_es = {}
            labeled_indices = np.flatnonzero(labeled)
            if len(labeled_indices) >= 2:
                areas = masks[labeled].sum(axis=(1, 2))
                ed_es = {"ED": int(labeled_indices[np.argmax(areas)]),
                         "ES": int(labeled_indices[np.argmin(areas)])}
                if ed_es["ED"] == ed_es["ES"]:
                    ed_es = {}
            metadata = {
                **case,
                "original_hw": [height, width],
                "image_hw": list(image_hw),
                "spacing_xy_mm": None,
                "fps": fps,
                "timestamps_s": (np.arange(len(frames), dtype=float) / fps).tolist(),
                "full_source_clip_decoded": True,
                # The evaluator still requires adjacent predicted ED peaks
                # before deriving HR; this only enables that check.
                "complete_cycle_verified": True,
                "sequence_type": "full_video",
                "phases": ed_es,
                "ground_truth_scope": "expert_traced_frames_only",
                "patient_identity_scope": "patient" if patient_value else "study_proxy",
                "source_files": {
                    "video": {"path": f"Videos/{filename}", "sha256": _sha256(video_path)},
                    "FileList.csv": {"sha256": source_hashes["FileList.csv"]},
                    "VolumeTracings.csv": {"sha256": source_hashes["VolumeTracings.csv"]},
                },
                "reference": {
                    "source": "EchoNet-Dynamic_FileList",
                    "EF": float(_field(row, "EF")) if _field(row, "EF") not in (None, "") else None,
                    "EDV_ml": float(_field(row, "EDV")) if _field(row, "EDV") not in (None, "") else None,
                    "ESV_ml": float(_field(row, "ESV")) if _field(row, "ESV") not in (None, "") else None,
                },
                "preprocess": {
                    "original_to_prepared": [
                        [image_hw[1] / width, 0.0, 0.5 * image_hw[1] / width - 0.5],
                        [0.0, image_hw[0] / height, 0.5 * image_hw[0] / height - 0.5],
                        [0.0, 0.0, 1.0],
                    ],
                    "timestamp_source": "FileList_or_video_container_frame_rate",
                },
            }
            (output_root / f"{case_id}.json").write_text(json.dumps(metadata, indent=2),
                                                        encoding="utf-8")
            cases.append(case)
        except Exception as error:
            failures.append({"filename": filename, "error": str(error)})

    manifest = {"schema_version": 1, "dataset": "EchoNet-Dynamic",
                "license": "Stanford AIMI research-use terms; obtain the source files through the authorized portal",
                "source_files": source_hashes, "view_scope": ["A4C"],
                "patients_or_studies": len({row["patient_id"] for row in cases}),
                "case_count": len(cases), "cases_expected": len(selected),
                "complete": not failures and len(cases) == len(rows),
                "split_unit": "patient" if all(row["patient_id"] != row["case_id"] for row in cases)
                else "study_proxy", "failures": failures, "cases": cases,
                "limitations": [
                    "No spatial calibration: Simpson outputs are pixel3_proxy, not mL.",
                    "A4C only; this dataset cannot supply a synchronized second plane.",
                    "No HR or CO reference labels; HR may be estimated only between detected ED peaks.",
                    "Only the official research-use split is preserved.",
                ]}
    (output_root / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    for split in ("train", "val", "test"):
        rows = [case for case in cases if case["split"] == split]
        if not rows:
            continue
        split_path = output_root / "splits" / f"{split}.json"
        split_path.parent.mkdir(parents=True, exist_ok=True)
        split_path.write_text(json.dumps({"split": split, "dataset_root": "..", "cases": rows},
                                         indent=2), encoding="utf-8")
    return {"cases": len(cases), "labeled_frames": sum(len(row["labeled_frames"]) for row in cases),
            "failures": len(failures), "complete": manifest["complete"]}
