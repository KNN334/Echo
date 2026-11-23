"""Rebuild the static website demo from the published DRA-UNet preview and checkpoint."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
from PIL import Image, ImageSequence
import torch

from lvseg.evaluate import _case_data, _predict
from lvseg.metrics.cycles import cycle_metrics
from lvseg.metrics.volume import simpson_single_plane
from lvseg.models import build_model
from lvseg.visualization.video import render_overlay_frames


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("web/src/assets"))
    args = parser.parse_args()
    preview = Path("reports/lvseg_ablation/assets")
    output = args.output
    provenance = json.loads((preview / "provenance.json").read_text(encoding="utf-8"))
    path = Path("runs/lvseg_ablation/seed_2026/DTE/best.pt")
    if hashlib.sha256(path.read_bytes()).hexdigest() != provenance["checkpoint_sha256"]:
        raise ValueError("The checkpoint differs from the published preview")
    torch.set_num_threads(2)
    with torch.serialization.safe_globals([torch.torch_version.TorchVersion]):
        checkpoint = torch.load(path, map_location="cpu", weights_only=True)
    model = build_model("DRA-UNet", base_channels=checkpoint["model_config"]["base_channels"])
    model.load_state_dict(checkpoint["state_dict"])

    prepared = Path("data/processed/camus_video")
    manifest = json.loads((prepared / "splits/test.json").read_text(encoding="utf-8"))
    cases = sorted((row for row in manifest["cases"] if row["view"] == "2CH"),
                   key=lambda row: row["patient_id"])[:10]
    developed = set(checkpoint["run"]["train_patients"]) | set(checkpoint["run"]["val_patients"])
    if manifest["split"] != "test" or developed.intersection(row["patient_id"] for row in cases):
        raise ValueError("Website cines must use the fixed held-out set")
    output.mkdir(parents=True, exist_ok=True)
    records = [
        export_case(prepared, row, output, preview, provenance, model, checkpoint)
        for row in cases
    ]
    (output / "camus-cases.json").write_text(
        json.dumps(records, indent=2, allow_nan=False) + "\n", encoding="utf-8", newline="\n")

    history = json.loads(path.with_name("history.json").read_text(encoding="utf-8"))
    losses = [{"epoch": row["epoch"], "train": row["train_components"]["segmentation"],
               "validation": row["validation_segmentation_loss"]} for row in history]
    (output / "dra-training-loss.json").write_text(
        json.dumps(losses, indent=2, allow_nan=False) + "\n", encoding="utf-8", newline="\n")


def export_case(prepared, case, output, preview, provenance, model, checkpoint):
    images, labels, labeled, references, meta = _case_data(prepared, case)
    norm = checkpoint["normalization"]
    masks = _predict(model, images, norm["mean"], norm["std"], "cpu",
                     threshold=provenance["threshold"])
    times = meta["timestamps_s"]
    spacing = meta["spacing_xy_mm"]
    width, height = reversed(meta["original_hw"])
    volumes = [simpson_single_plane(
        np.asarray(Image.fromarray(mask).resize((width, height), Image.Resampling.NEAREST)),
        spacing,
    ) for mask in masks]
    summary = cycle_metrics(volumes, times, complete_cycle=meta["complete_cycle_verified"])
    expert_volumes = {
        phase: simpson_single_plane(references[index], spacing) if index in references else None
        for phase, index in meta["phases"].items()
    }

    tile_width, tile_height, columns = 384, 288, 5
    rows = (len(images) + columns - 1) // columns
    atlas = Image.new("RGB", (columns * tile_width, rows * tile_height))
    overlays = render_overlay_frames(images, masks, labels, labeled, meta, "DRA-UNet")
    if case["patient_id"] == provenance["patient_id"]:
        with Image.open(preview / f"dra_{case['case_id']}.gif") as clip:
            if clip.n_frames != len(overlays):
                raise ValueError("Published preview frame count differs from measurements")
            for index, frame in enumerate(ImageSequence.Iterator(clip)):
                expected = overlays[index][..., ::-1]
                if np.abs(np.asarray(frame.convert("RGB"), dtype=float) - expected).mean() > 3:
                    raise ValueError(f"Preview pixels differ from regenerated segmentation at {index}")
    for index, frame in enumerate(overlays):
        rgb = Image.fromarray(frame[-images.shape[1] * 2:, :, ::-1])
        tile = rgb.resize((tile_width, tile_height), Image.Resampling.LANCZOS)
        atlas.paste(tile, (index % columns * tile_width, index // columns * tile_height))
    filename = f"{case['case_id']}.webp"
    atlas.save(output / filename, quality=90)
    return {
        "patient_id": case["patient_id"],
        "source": "CAMUS fixed test split",
        "model": provenance["model"],
        "seed": provenance["seed"],
        "checkpoint_sha256": provenance["checkpoint_sha256"],
        "view": "A2C",
        "fps": meta["fps"],
        "spacing_mm": spacing,
        "complete_cycle_verified": meta["complete_cycle_verified"],
        "expert_phases": meta["phases"],
        "expert_volumes_ml": expert_volumes,
        "image_quality": meta.get("image_quality"),
        "atlas": {"columns": columns, "rows": rows, "width": tile_width, "height": tile_height},
        "atlas_file": filename,
        "frames": [{"index": index, "time_s": time, "volume_ml": volume}
                   for index, (time, volume) in enumerate(zip(times, volumes, strict=True))],
        "events": summary["events"],
    }


if __name__ == "__main__":
    main()
