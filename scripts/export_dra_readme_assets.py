"""Create DRA-UNet examples for the same fixed patient as the baseline README."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import cv2
import numpy as np
from PIL import Image
import torch

from lvseg.evaluate import _case_data, _predict
from lvseg.models import build_model
from lvseg.visualization.mask_panels import export_mask_grid, plot_multiview_mask_comparison
from lvseg.visualization.video import _write_gif, _write_mp4, render_overlay_frames


BASELINES = ("UNet", "Attention-UNet", "UNet++", "UNet-mini", "VGG16-UNet")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path,
                        default=Path("runs/lvseg_ablation/seed_2026/DTE/best.pt"))
    parser.add_argument("--results", type=Path, default=Path("reports/lvseg_ablation/results.json"))
    parser.add_argument("--prepared", type=Path, default=Path("data/processed/camus_video"))
    parser.add_argument("--baselines", type=Path, default=Path("runs/lvseg_baselines"))
    parser.add_argument("--output", type=Path, default=Path("reports/lvseg_ablation/assets"))
    parser.add_argument("--device", default="cpu")
    args = parser.parse_args()

    report = json.loads(args.results.read_text(encoding="utf-8"))
    selected = report["selection"]["selected"]
    if not report["complete"] or report["split"] != "val" or selected != "DTE":
        raise ValueError("The published model must match the completed DTE validation selection.")
    checkpoint_hash = hashlib.sha256(args.checkpoint.read_bytes()).hexdigest()
    matched = [run for run in report["runs"]
               if run["variant"] == selected and run["validation"]["checkpoint_sha256"] == checkpoint_hash]
    if len(matched) != 1:
        raise ValueError("Checkpoint does not match the selected validation result.")
    run = matched[0]
    with torch.serialization.safe_globals([torch.torch_version.TorchVersion]):
        checkpoint = torch.load(args.checkpoint, map_location="cpu", weights_only=True)
    model = build_model("DRA-UNet", base_channels=checkpoint["model_config"]["base_channels"]).to(
        args.device).eval()
    model.load_state_dict(checkpoint["state_dict"], strict=True)
    torch.set_num_threads(2)
    manifest_path = args.prepared / "splits" / "test.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest["split"] != "test":
        raise ValueError("The selected illustration must come from the fixed test split.")
    patient_id = "patient0015"
    cases = {case["view"]: case for case in manifest["cases"] if case["patient_id"] == patient_id}
    if set(cases) != {"2CH", "4CH"}:
        raise ValueError("The README patient must have both 2CH and 4CH cines.")
    if patient_id in set(checkpoint["run"]["train_patients"]) | set(checkpoint["run"]["val_patients"]):
        raise ValueError("The displayed patient overlaps model development.")
    norm = checkpoint["normalization"]
    original_predictions = {}
    example_views = {}
    args.output.mkdir(parents=True, exist_ok=True)
    names = (*BASELINES, "DRA-UNet")
    for view in ("2CH", "4CH"):
        case = cases[view]
        images, labels, labeled, _, metadata = _case_data(args.prepared, case)
        predicted = _predict(model, images, norm["mean"], norm["std"], args.device)
        if predicted.shape != images.shape:
            raise ValueError("The number or size of predicted frames does not match the cine.")
        height, width = metadata["original_hw"]
        example_views[view] = {
            "frame_count": len(images),
            "source_fps": metadata["fps"],
            "labeled_phase_indices": metadata["phases"],
        }
        original_predictions[case["case_id"]] = np.stack([
            np.asarray(Image.fromarray(mask).resize((width, height), Image.Resampling.NEAREST))
            for mask in predicted
        ])
        if view != "2CH":
            continue
        overlay = render_overlay_frames(images, predicted, labels, labeled, metadata, "DRA-UNet")
        _write_gif(args.output / "dra_patient0015_2CH.gif", overlay)
        _write_mp4(args.output / "dra_patient0015_2CH.mp4", overlay, metadata["fps"])
        predictions = {}
        for name in BASELINES:
            path = args.baselines / name / "evaluation" / "predicted_masks" / f"{case['case_id']}.npz"
            with np.load(path, allow_pickle=False) as archive:
                predictions[name] = archive["model_grid_masks"]
            if predictions[name].shape != images.shape:
                raise ValueError(f"Baseline prediction dimensions differ for {name}.")
        predictions["DRA-UNet"] = predicted
        comparison = export_mask_grid(images, labels, labeled, predictions, metadata,
                                      args.output / "six_model_patient0015_2CH.png")
        comparison = [cv2.cvtColor(frame, cv2.COLOR_RGB2BGR) for frame in comparison]
        _write_gif(args.output / "six_model_patient0015_2CH.gif", comparison)
        _write_mp4(args.output / "six_model_patient0015_2CH.mp4", comparison, metadata["fps"])

    plot_multiview_mask_comparison(
        args.prepared, manifest_path, args.baselines, names,
        args.output / "multiview_masks_patient0015.png", patient_id=patient_id,
        extra_predictions={"DRA-UNet": original_predictions})
    provenance = {
        "model": "DRA-UNet", "ablation_variant": selected, "seed": run["seed"],
        "checkpoint_sha256": checkpoint_hash, "patient_id": patient_id,
        "patient_selection": "same fixed test patient used by existing baseline previews",
        "threshold": 0.5, "views": example_views,
        "baseline_checkpoint_seed": 2026,
        "expert_labels": "displayed only at ED and ES; all frames receive predictions",
        "license": "CAMUS CC BY-NC-SA 4.0; see docs/data_sources/CAMUS_LICENSE_TERMS.md",
    }
    (args.output / "provenance.json").write_text(
        json.dumps(provenance, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(provenance, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
