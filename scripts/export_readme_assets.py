"""Build the videos and figures embedded by the project README."""

from __future__ import annotations

import argparse
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
    repeated_results = Path("reports/lvseg_baselines/repeated_runs.json")
    if not repeated_results.is_file():
        raise FileNotFoundError(
            "Repeated baseline results are required before refreshing the README table")
    repeated = json.loads(repeated_results.read_text(encoding="utf-8"))
    rows = repeated["models"]
    selected = repeated["protocol"]["selected_baseline"]
    table_rows = [
        "| 模型 | 验证集 Dice | 测试 Dice | 测试 mIoU | Precision | Recall | HD95 (mm) | ASD (mm) |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    columns = (
        ("patient_mean_dice", 4),
        ("patient_mean_miou", 4),
        ("patient_mean_precision", 4),
        ("patient_mean_recall", 4),
        ("patient_mean_hd95", 2),
        ("patient_mean_asd", 2),
    )
    for row in rows:
        values = [f"{float(row[mean]):.{digits}f}" for mean, digits in columns]
        validation = f"{float(row['validation_mean_dice']):.4f}"
        model = f"**{row['model']}** ✓" if row["model"] == selected else row["model"]
        table_rows.append(f"| {model} | {validation} | " + " | ".join(values) + " |")
    text = readme.read_text(encoding="utf-8")
    start_marker = "<!-- SEGMENTATION_METRICS_TABLE_START -->"
    end_marker = "<!-- SEGMENTATION_METRICS_TABLE_END -->"
    before, rest = text.split(start_marker, 1)
    _, after = rest.split(end_marker, 1)
    before = before.replace("### 最高 Dice 基线：U-Net",
                            f"### 验证集重复实验选出的基线：{selected}")
    before = before.replace(
        "下表为固定患者级测试集上按患者先求均值、再跨患者汇总的结果。mIoU 是前景与背景 IoU 的均值。Dice、mIoU、Precision 和 Recall 越高越好；HD95 与 ASD 越低越好。HD95 是双向表面距离合并后的 95 百分位，ASD 是双向平均表面距离；距离以原始图像像素间距换算为 mm。每名患者的 ED/ES 标注帧用于分割评价，整段视频（包括无标签帧）都参与推理和容积曲线。",
        f"五种基线在固定患者划分下各独立训练 {repeated['protocol']['runs_per_model']} 次。按跨种子的验证集 Dice 均值选择基线；测试集不用于选模。表中验证 Dice 与测试指标均为跨种子均值；每次测试指标先在患者内平均，再汇总。mIoU 是前景与背景 IoU 的均值，HD95/ASD 使用原始像素间距换算为 mm。测试集 ED/ES 标注帧用于分割评价，整段视频（包括无标签帧）都参与推理和容积曲线。")
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
    repeated = json.loads(Path("reports/lvseg_baselines/repeated_runs.json").read_text(
        encoding="utf-8"))
    best_model = repeated["protocol"]["selected_baseline"]
    case_id = json.loads(test_manifest.read_text(encoding="utf-8"))["cases"][0]["case_id"]
    plot_volume_curve(results_root / best_model / "evaluation", case_id,
                      assets / "volume_waveform.png")
    video_metadata = export_readme_videos(
        prepared_root, test_manifest, results_root, assets, best_model=best_model)
    _refresh_metrics_table(Path("README.md"), Path("reports/lvseg_baselines/model_comparison.csv"))
    readme_path = Path("README.md")
    readme_text = readme_path.read_text(encoding="utf-8")
    readme_text = readme_text.replace(
        "![U-Net 对测试视频逐帧分割]",
        f"![{best_model} 对测试视频逐帧分割]")
    readme_path.write_text(readme_text, encoding="utf-8", newline="\n")
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
