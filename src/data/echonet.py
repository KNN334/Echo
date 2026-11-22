"""EchoNet-Dynamic raw-video preparation into the project's auditable schema.

The public EchoNet release does not expose a patient identifier in every
version of ``FileList.csv``.  When it is absent, this module keeps one study
per ``patient_id`` proxy and records that limitation explicitly; downstream
reports must not call that split patient-level validation.
"""

from __future__ import annotations

import csv
import re
from pathlib import Path

import numpy as np

from .medical_io import echonet_traces, read_video
from .metadata import audit_metadata
from .transforms import Transform
from ..utils.hash import sha256
from ..utils.io import write_json, write_npz


def _key(value):
    return re.sub(r"[^a-z0-9]", "", str(value).lower())


def _field(row, *names):
    wanted = {_key(name) for name in names}
    for key, value in row.items():
        if _key(key) in wanted:
            return value
    return None


def _number(value):
    if value in (None, ""):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if np.isfinite(result) else None


def _filename(value):
    if not value:
        return None
    name = Path(str(value)).name
    return name if Path(name).suffix else name + ".avi"


def read_echonet_filelist(root):
    """Read and validate the official ``FileList.csv`` rows."""
    root = Path(root).resolve()
    path = root / "FileList.csv"
    if not path.is_file():
        raise FileNotFoundError(f"EchoNet FileList.csv not found: {path}")
    with path.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    if not rows:
        raise ValueError(f"EchoNet FileList.csv is empty: {path}")
    for row in rows:
        name = _filename(_field(row, "FileName", "Filename"))
        split = _field(row, "Split")
        if not name or not split:
            raise ValueError("EchoNet FileList.csv requires FileName and Split")
        row["_filename"] = name
        row["_split"] = str(split).strip().lower()
    return rows


def _phase_indices(masks, labeled):
    indices = np.flatnonzero(labeled)
    if len(indices) < 2:
        return {}
    areas = np.asarray([masks[index].sum() for index in indices], float)
    if not np.isfinite(areas).all() or np.max(areas) <= 0:
        return {}
    ed = int(indices[np.argmax(areas)])
    es = int(indices[np.argmin(areas)])
    if ed == es:
        return {}
    return {"ED": ed, "ES": es}


def _case_id(filename):
    stem = Path(filename).stem
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", stem).strip("._")
    if not safe:
        raise ValueError(f"invalid EchoNet filename: {filename}")
    return "echonet_" + safe


def prepare_echonet(raw_root, output_root, *, output_hw=(112, 112), limit=None,
                    overwrite=False):
    """Materialize EchoNet videos and traces as ``frames/masks`` NPZ cases.

    A video remains available for inference even when it has zero or one
    traced frame. Only its annotated frames enter supervised training; ED/ES
    reference-phase analyses are available only when two distinct phases can
    be identified from the traces.

    The function is intentionally independent of torch/torchvision so that
    dataset preparation can be audited on a CPU-only environment.
    """
    raw_root = Path(raw_root).resolve()
    output_root = Path(output_root).resolve()
    if output_root.exists() and any(output_root.iterdir()) and not overwrite:
        raise FileExistsError(f"output directory is not empty: {output_root}")
    output_root.mkdir(parents=True, exist_ok=True)
    rows = read_echonet_filelist(raw_root)
    trace_path = raw_root / "VolumeTracings.csv"
    if not trace_path.is_file():
        raise FileNotFoundError(f"EchoNet VolumeTracings.csv not found: {trace_path}")
    cases, failures, split_units = [], [], set()
    for row in rows[:limit] if limit else rows:
        filename = row["_filename"]
        case_id = _case_id(filename)
        video_path = raw_root / "Videos" / filename
        try:
            frames, video_meta = read_video(video_path)
            original_h, original_w = frames.shape[1:]
            masks, labeled = echonet_traces(trace_path, filename, len(frames),
                                             (original_h, original_w))
            phases = _phase_indices(masks, labeled)
            transform = Transform((original_h, original_w),
                                  (0, 0, original_w, original_h), tuple(output_hw))
            processed_frames = np.stack([transform.image(frame) for frame in frames]).astype(np.uint8)
            processed_masks = np.stack([transform.image(mask, label=True) for mask in masks]).astype(np.uint8)
            original_gt = masks[labeled].astype(np.uint8)
            fps = _number(_field(row, "FPS", "FrameRate"))
            if fps is None:
                fps = video_meta.get("fps")
            audit = audit_metadata(len(frames), spacing_xy=None, fps=fps,
                                   timestamps_s=None,
                                   source={"video_sha256": sha256(video_path),
                                          "filelist_sha256": sha256(raw_root / "FileList.csv"),
                                          "timestamp_source": "FileList_or_container_rate_not_acquisition_verified"})
            audit["container_timestamps_s"] = video_meta.get("container_timestamps_s")
            audit["transform"] = transform.record(None)
            audit["roi_reviewed"] = False
            audit["issues"].append("missing_patient_identifier" if not _field(row, "PatientID", "Patient") else "")
            audit["issues"] = [issue for issue in audit["issues"] if issue]
            patient_value = _field(row, "PatientID", "Patient", "SubjectID")
            patient_id = str(patient_value).strip() if patient_value not in (None, "") else f"study_{Path(filename).stem}"
            split_unit = "patient" if patient_value not in (None, "") else "study_proxy"
            split_units.add(split_unit)
            metadata = {
                "dataset": "EchoNet-Dynamic",
                "dataset_kind": "echonet_dynamic",
                "patient_id": patient_id,
                "study_id": Path(filename).stem,
                "patient_identity_scope": split_unit,
                "view": "A4C",
                "split": row["_split"],
                "phases": phases,
                "sequence_type": "sequence_unverified",
                "full_cycle_verified": False,
                "temporal_contract": {
                    "timestamps_source": audit["timestamp_source"],
                    "full_cycle_verified": False,
                    "hr_co_ready": False,
                },
                "gt_scope": "expert_traced_frames_only",
                "config": {
                    "EF": _number(_field(row, "EF")),
                    "EDV": _number(_field(row, "EDV")),
                    "ESV": _number(_field(row, "ESV")),
                    "FrameRate": fps,
                },
                "reference": {
                    "scope": "EchoNet_dataset_labels",
                    "EF": _number(_field(row, "EF")),
                    "EDV": _number(_field(row, "EDV")),
                    "ESV": _number(_field(row, "ESV")),
                    "CO": None,
                    "HR": None,
                },
                "audit": audit,
                "preprocess_config": {"output_hw": list(output_hw),
                                       "intensity_range": [0, 255],
                                       "roi_reviewed": False},
            }
            write_npz(output_root / (case_id + ".npz"),
                      frames=processed_frames, masks=processed_masks,
                      labeled=labeled.astype(bool), original_gt=original_gt,
                      original_gt_indices=np.flatnonzero(labeled))
            write_json(output_root / (case_id + ".json"), metadata)
            cases.append({"case_id": case_id, "patient_id": patient_id,
                          "view": "A4C", "split": row["_split"],
                          "frames": int(len(frames)),
                          "labeled_frames": int(labeled.sum()),
                          "study_id": Path(filename).stem})
        except Exception as error:
            failures.append({"case_id": case_id, "filename": filename,
                             "error": str(error)})
    if not cases:
        raise ValueError("EchoNet preparation produced no cases")
    manifest = {
        "schema_version": 1,
        "dataset": "EchoNet-Dynamic",
        "dataset_kind": "echonet_dynamic",
        "split_unit": "patient" if split_units == {"patient"} else "study_proxy",
        "source_root": str(raw_root),
        "source_filelist_sha256": sha256(raw_root / "FileList.csv"),
        "source_traces_sha256": sha256(trace_path),
        "cases": cases,
        "failures": failures,
    }
    write_json(output_root / "manifest.json", manifest)
    return {"cases": len(cases), "failures": len(failures),
            "patients": len({row["patient_id"] for row in cases}),
            "split_unit": manifest["split_unit"],
            "manifest": str(output_root / "manifest.json")}
