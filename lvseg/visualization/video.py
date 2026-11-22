"""Export README-ready cine overlays for the selected model and all baselines."""

from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from .mask_panels import export_mask_grid


def _boundary(mask: np.ndarray) -> np.ndarray:
    mask = np.asarray(mask, dtype=np.uint8)
    eroded = cv2.erode(mask, np.ones((3, 3), dtype=np.uint8))
    return (mask > 0) & (eroded == 0)


def _overlay(image: np.ndarray, prediction: np.ndarray,
             reference: np.ndarray | None, scale: int) -> np.ndarray:
    gray = cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    canvas = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    pred = cv2.resize(prediction.astype(np.uint8), (canvas.shape[1], canvas.shape[0]),
                      interpolation=cv2.INTER_NEAREST) > 0
    color = np.asarray((40, 210, 40), dtype=np.uint8)
    tinted = canvas.copy()
    tinted[pred] = color
    canvas = cv2.addWeighted(canvas, 0.66, tinted, 0.34, 0)
    pred_edge = _boundary(pred)
    canvas[pred_edge] = (35, 240, 80)
    if reference is not None:
        ref = cv2.resize(reference.astype(np.uint8), (canvas.shape[1], canvas.shape[0]),
                         interpolation=cv2.INTER_NEAREST) > 0
        canvas[_boundary(ref)] = (20, 190, 255)
    return canvas


def _write_mp4(path: Path, frames: list[np.ndarray], fps: float) -> None:
    if not frames:
        raise ValueError("Cannot write an empty segmentation video")
    height, width = frames[0].shape[:2]
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"),
                             float(fps), (width, height))
    if not writer.isOpened():
        raise RuntimeError(f"Cannot create video file: {path}")
    try:
        for frame in frames:
            if frame.shape != (height, width, 3):
                raise ValueError("All rendered video frames must have identical dimensions")
            writer.write(frame)
    finally:
        writer.release()


def _write_gif(path: Path, frames: list[np.ndarray], duration_ms: int = 100) -> None:
    gif_frames = [Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)) for frame in frames]
    gif_frames[0].save(path, save_all=True, append_images=gif_frames[1:],
                       duration=duration_ms, loop=0, optimize=True)


def export_readme_videos(prepared_root: str | Path, test_manifest: str | Path,
                         results_root: str | Path, output_dir: str | Path, *,
                         best_model: str | None = None, alignment_audit=None) -> dict:
    prepared_root, test_manifest = Path(prepared_root), Path(test_manifest)
    results_root, output_dir = Path(results_root), Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    cases = json.loads(test_manifest.read_text(encoding="utf-8"))["cases"]
    selected_case = next(case for case in cases if case["view"] == "2CH")
    case_id = selected_case["case_id"]
    metadata = json.loads((prepared_root / f"{case_id}.json").read_text(encoding="utf-8"))
    with np.load(prepared_root / f"{case_id}.npz", allow_pickle=False) as arrays:
        images = arrays["frames"]
        labels = arrays["masks"]
        labeled = arrays["labeled"].astype(bool)
    if len(images) == 0 or len(images) != len(labeled):
        raise ValueError(f"Invalid cine sequence for README visualization: {case_id}")
    model_summaries = [
        json.loads((results_root / model / "evaluation" / "summary.json").read_text(
            encoding="utf-8"))
        for model in ("UNet", "Attention-UNet", "UNet++", "UNet-mini", "VGG16-UNet")
    ]
    best = best_model or max(model_summaries,
                             key=lambda row: row["patient_mean_dice"])["model"]
    if best not in {row["model"] for row in model_summaries}:
        raise ValueError(f"Selected baseline is not in the video comparison: {best}")
    checkpoint_run = json.loads((results_root / best / "run.json").read_text(
        encoding="utf-8"))
    predictions = {}
    for summary in model_summaries:
        name = summary["model"]
        prediction_path = (results_root / name / "evaluation" / "predicted_masks" /
                           f"{case_id}.npz")
        with np.load(prediction_path, allow_pickle=False) as arrays:
            predictions[name] = arrays["model_grid_masks"]
        if len(predictions[name]) != len(images):
            raise ValueError(f"Prediction and cine frame counts differ for {name} / {case_id}")

    scale, header = 2, 64
    predicted_phase = {int(index): phase for phase, index in metadata.get("phases", {}).items()}
    best_frames = []
    for index, image in enumerate(images):
        reference = labels[index] if labeled[index] else None
        body = _overlay(image, predictions[best][index], reference, scale)
        frame = np.zeros((body.shape[0] + header, body.shape[1], 3), dtype=np.uint8)
        frame[header:] = body
        phase = predicted_phase.get(index, "unlabeled frame")
        timestamp = index / float(metadata["fps"])
        cv2.putText(frame, f"{best} | {case_id} | frame {index} | {timestamp:.3f} s",
                    (12, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (245, 245, 245), 1,
                    cv2.LINE_AA)
        state = f"Expert label: {phase}" if labeled[index] else "Expert label: unavailable"
        cv2.putText(frame, state, (12, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.53,
                    (20, 190, 255) if labeled[index] else (190, 190, 190), 1,
                    cv2.LINE_AA)
        best_frames.append(frame)

    slug = f"{metadata['patient_id']}_{metadata['view']}"
    comparison_preview = output_dir / f"five_model_{slug}.png"
    compare_frames = [cv2.cvtColor(frame, cv2.COLOR_RGB2BGR) for frame in export_mask_grid(
        images, labels, labeled, predictions, metadata, comparison_preview,
        alignment_audit=alignment_audit)]
    best_video = output_dir / f"best_model_{slug}.mp4"
    best_gif = output_dir / f"best_model_{slug}.gif"
    comparison_video = output_dir / f"five_model_{slug}.mp4"
    comparison_gif = output_dir / f"five_model_{slug}.gif"
    fps = float(metadata["fps"])
    _write_mp4(best_video, best_frames, fps)
    _write_gif(best_gif, best_frames)
    _write_mp4(comparison_video, compare_frames, fps)
    _write_gif(comparison_gif, compare_frames)
    metadata_out = {
        "patient_id": metadata["patient_id"], "case_id": case_id,
        "view": metadata["view"], "frames": int(len(images)), "source_fps": fps,
        "labeled_frames": int(labeled.sum()), "unlabeled_frames": int((~labeled).sum()),
        "best_model_by_patient_mean_dice": best,
        "representative_checkpoint_seed": checkpoint_run.get("seed"),
        "files": [best_video.name, best_gif.name, comparison_video.name,
                  comparison_gif.name, comparison_preview.name,
                  comparison_preview.with_suffix(".pdf").name,
                  comparison_preview.with_suffix(".svg").name],
        "overlay": "best-model video: green = model mask; amber = expert-mask contour where labeled",
        "comparison_layout": "2 by 3: B-mode input and five black-background binary masks; "
                             "amber expert contour on input only where labeled; no mask cleanup",
        "comparison_preview_frame": int(len(images) // 2),
        "comparison_aspect_ratio": "restored original aspect ratio with square letterboxing",
        "source": "fixed held-out CAMUS test split",
    }
    (output_dir / "video_metadata.json").write_text(
        json.dumps(metadata_out, indent=2), encoding="utf-8")
    return metadata_out
