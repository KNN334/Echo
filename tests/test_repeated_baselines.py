import json

from scripts.export_readme_assets import _refresh_metrics_table
from scripts.run_repeated_baselines import _select_baseline


def test_baseline_selection_uses_mean_validation_dice_not_test_dice():
    rows = [
        {"model": "UNet", "validation_mean_dice": 0.92,
         "validation_mean_loss": 0.12, "patient_mean_dice": 0.99},
        {"model": "Attention-UNet", "validation_mean_dice": 0.94,
         "validation_mean_loss": 0.13, "patient_mean_dice": 0.91},
    ]

    assert _select_baseline(rows) == "Attention-UNet"


def test_metrics_table_keeps_header_and_rows_in_one_markdown_table(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    report_dir = tmp_path / "reports" / "lvseg_baselines"
    report_dir.mkdir(parents=True)
    (report_dir / "repeated_runs.json").write_text(json.dumps({
        "protocol": {"runs_per_model": 2, "selected_baseline": "UNet"},
        "models": [{
            "model": "UNet", "validation_mean_dice": 0.94, "validation_sd_dice": 0.01,
            "patient_mean_dice": 0.93, "patient_mean_dice_sd": 0.02,
            "patient_mean_miou": 0.92, "patient_mean_miou_sd": 0.02,
            "patient_mean_precision": 0.95, "patient_mean_precision_sd": 0.01,
            "patient_mean_recall": 0.92, "patient_mean_recall_sd": 0.02,
            "patient_mean_hd95": 3.2, "patient_mean_hd95_sd": 0.4,
            "patient_mean_asd": 1.1, "patient_mean_asd_sd": 0.1,
        }],
    }), encoding="utf-8")
    intro = (
        "下表为固定患者级测试集上按患者先求均值、再跨患者汇总的结果。mIoU 是前景与背景 IoU 的均值。"
        "Dice、mIoU、Precision 和 Recall 越高越好；HD95 与 ASD 越低越好。HD95 是双向表面距离合并后的 95 百分位，"
        "ASD 是双向平均表面距离；距离以原始图像像素间距换算为 mm。每名患者的 ED/ES 标注帧用于分割评价，"
        "整段视频（包括无标签帧）都参与推理和容积曲线。"
    )
    readme = tmp_path / "README.md"
    readme.write_text(
        "### 最高 Dice 基线：U-Net\n\n" + intro + "\n\n"
        "<!-- SEGMENTATION_METRICS_TABLE_START -->\n| old |\n"
        "<!-- SEGMENTATION_METRICS_TABLE_END -->\n",
        encoding="utf-8",
    )

    _refresh_metrics_table(readme, tmp_path / "unused.csv")

    result = readme.read_text(encoding="utf-8")
    start = result.index("<!-- SEGMENTATION_METRICS_TABLE_START -->")
    end = result.index("<!-- SEGMENTATION_METRICS_TABLE_END -->")
    table_rows = [line for line in result[start:end].splitlines() if line.startswith("|")]
    assert len(table_rows) == 3
    assert table_rows[0].startswith("| 模型 | 验证集 Dice | 测试 Dice |")
    assert all(line.count("|") == 9 for line in table_rows)
    assert "### 验证集重复实验选出的基线：UNet" in result
    assert "独立训练 2 次" in result
