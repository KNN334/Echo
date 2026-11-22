"""Build the videos and figures embedded by the project README."""

from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import yaml

from lvseg.visualization.comparison import (
    plot_baseline_comparison,
    plot_volume_accuracy_comparison,
)
from lvseg.visualization.volume_curve import plot_volume_curve
from lvseg.visualization.video import export_readme_videos


def _refresh_metrics_table(readme: Path, comparison_csv: Path) -> None:
    with comparison_csv.open(newline="", encoding="utf-8-sig") as stream:
        rows = list(csv.DictReader(stream))
    table_rows = [
        "| 模型 | Dice | mIoU | Precision | Recall | HD95 (mm) | ASD (mm) |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    columns = (
        ("patient_mean_dice", "patient_mean_dice_sd", 4),
        ("patient_mean_miou", "patient_mean_miou_sd", 4),
        ("patient_mean_precision", "patient_mean_precision_sd", 4),
        ("patient_mean_recall", "patient_mean_recall_sd", 4),
        ("patient_mean_hd95", "patient_mean_hd95_sd", 2),
        ("patient_mean_asd", "patient_mean_asd_sd", 2),
    )
    for row in rows:
        values = [f"{float(row[mean]):.{digits}f} ± {float(row[sd]):.{digits}f}"
                  for mean, sd, digits in columns]
        table_rows.append(f"| {row['model']} | " + " | ".join(values) + " |")
    text = readme.read_text(encoding="utf-8")
    start_marker = "<!-- SEGMENTATION_METRICS_TABLE_START -->"
    end_marker = "<!-- SEGMENTATION_METRICS_TABLE_END -->"
    before, rest = text.split(start_marker, 1)
    _, after = rest.split(end_marker, 1)
    readme.write_text(before + start_marker + "\n\n" + "\n".join(table_rows) +
                      "\n\n" + end_marker + after, encoding="utf-8", newline="\n")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/lvseg.yaml")
    args = parser.parse_args(argv)
    config = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))
    prepared_root = Path(config["dataset"]["prepared_root"])
    test_manifest = prepared_root / "splits" / "test.json"
    results_root = Path(config["evaluation"]["output_root"])
    models = config["training"]["models"]
    assets = Path("reports/lvseg_baselines/assets")
    assets.mkdir(parents=True, exist_ok=True)

    alignment_audit = None
    audit_scripts = os.environ.get("NATURE_FIGURE_AUDIT_DIR")
    if audit_scripts:
        sys.path.insert(0, audit_scripts)
        from audit_panel_alignment import require_matplotlib_panel_alignment
        alignment_audit = require_matplotlib_panel_alignment

    plot_baseline_comparison(results_root, models,
                             output=assets / "segmentation_model_comparison.png",
                             alignment_audit=alignment_audit)
    plot_volume_accuracy_comparison(
        results_root, models, assets / "volume_accuracy_comparison.png",
        alignment_audit=alignment_audit)
    summaries = [json.loads((results_root / name / "evaluation" / "summary.json").read_text(
        encoding="utf-8")) for name in models]
    best_model = max(summaries, key=lambda row: row["patient_mean_dice"])["model"]
    case_id = json.loads(test_manifest.read_text(encoding="utf-8"))["cases"][0]["case_id"]
    plot_volume_curve(results_root / best_model / "evaluation", case_id,
                      assets / "volume_waveform.png")
    video_metadata = export_readme_videos(
        prepared_root, test_manifest, results_root, assets)
    _refresh_metrics_table(Path("README.md"), Path("reports/lvseg_baselines/model_comparison.csv"))
    (assets / "README_assets.json").write_text(json.dumps({
        "best_model": best_model,
        "best_case": case_id,
        "videos": video_metadata,
        "figures": ["segmentation_model_comparison.png",
                    "volume_accuracy_comparison.png", "volume_waveform.png"],
    }, indent=2), encoding="utf-8")
    print(json.dumps(video_metadata, indent=2))
    return video_metadata


if __name__ == "__main__":
    main()
