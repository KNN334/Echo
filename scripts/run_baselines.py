"""Train and evaluate the five predeclared LV segmentation baselines."""

from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

os.environ.setdefault("MPLCONFIGDIR", str(Path(".work/matplotlib").resolve()))

import yaml

from lvseg.evaluate import evaluate_model
from lvseg.train import train_model
from lvseg.visualization.volume_curve import plot_volume_curve
from lvseg.visualization.comparison import (
    plot_baseline_comparison,
    plot_mask_comparison,
    plot_volume_bland_altman,
)


def _validate_prepared(root: Path, split_file: Path):
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    if not manifest.get("complete") or manifest.get("patients") != 500 or manifest.get("case_count") != 1000:
        raise ValueError("Expected complete prepared CAMUS: 500 patients, 1000 2CH/4CH cine cases")
    split = json.loads(split_file.read_text(encoding="utf-8"))
    if len(split["patients"]) != 500:
        raise ValueError("Fixed patient split does not contain all 500 CAMUS patients")
    patient_sets = {name: {pid for pid, assigned in split["patients"].items() if assigned == name}
                    for name in ("train", "val", "test")}
    if {name: len(patients) for name, patients in patient_sets.items()} != {
            "train": 400, "val": 50, "test": 50}:
        raise ValueError("Unexpected CAMUS fixed split sizes")
    for name in patient_sets:
        path = root / "splits" / f"{name}.json"
        rows = json.loads(path.read_text(encoding="utf-8"))["cases"]
        patients = {row["patient_id"] for row in rows}
        if patients != patient_sets[name]:
            raise ValueError(f"{name} case manifest does not match the fixed patient-level split")
    if patient_sets["train"] & patient_sets["val"] or patient_sets["test"] & (
            patient_sets["train"] | patient_sets["val"]):
        raise ValueError("Patient overlap across train/validation/test")


def _write_comparison(output: Path, summaries: list[dict]):
    fields = ("model", "test_patients", "test_cines", "inference_frames", "labeled_frames",
              "unlabeled_inference_frames", "patient_mean_dice", "frame_mean_iou")
    with (output / "baseline_comparison.csv").open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows({key: summary.get(key) for key in fields} for summary in summaries)
    (output / "baseline_comparison.json").write_text(
        json.dumps(summaries, indent=2), encoding="utf-8")


def _write_project_report(results_root: Path, model_names: list[str]):
    project_root = results_root.parent.parent
    report_root = project_root / "reports" / "lvseg_baselines"
    report_root.mkdir(parents=True, exist_ok=True)
    raw = json.loads((project_root / "data/raw/camus_video/download_manifest.json").read_text(
        encoding="utf-8"))
    prepared = json.loads((project_root / "data/processed/camus_video/manifest.json").read_text(
        encoding="utf-8"))
    split = json.loads((project_root / "configs/splits/camus_patients.json").read_text(
        encoding="utf-8"))
    summaries = [json.loads((results_root / name / "evaluation" / "summary.json").read_text(
        encoding="utf-8")) for name in model_names]
    comparison_rows = []
    for summary in summaries:
        row = {key: summary.get(key) for key in (
            "model", "test_patients", "test_cines", "inference_frames", "labeled_frames",
            "unlabeled_inference_frames", "patient_mean_dice", "patient_mean_iou",
            "frame_mean_iou", "event_count", "events_with_hr_estimate",
            "events_with_calibrated_co")}
        for scope, source in (
            ("frame", summary["volume_bland_altman_by_labeled_frame_view"]),
            ("patient", summary["volume_bland_altman_by_patient_view_means"]),
        ):
            for view, stats in source.items():
                for metric in ("n", "unit", "bias", "loa_lower", "loa_upper"):
                    row[f"{scope}_{view}_ba_{metric}"] = stats[metric]
        comparison_rows.append(row)
    fields = list(comparison_rows[0])
    with (report_root / "model_comparison.csv").open(
            "w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(comparison_rows)

    report_data = {
        "project_version": "0.6.0",
        "dataset": {
            "name": "CAMUS", "raw_complete": raw["complete"],
            "raw_patients": raw["patients_requested"],
            "raw_files_verified": raw["files_verified"],
            "raw_files_expected": raw["files_expected"],
            "raw_bytes_verified": raw["bytes_verified"],
            "raw_failures": len(raw["failures"]),
            "raw_inventory_sha256": raw["source_inventory_sha256"],
            "license": raw["license"], "prepared_complete": prepared["complete"],
            "prepared_patients": prepared["patients"], "prepared_cines": prepared["case_count"],
            "prepared_frames": sum(case["frame_count"] for case in prepared["cases"]),
            "expert_labeled_frames": sum(
                len(case["labeled_frames"]) for case in prepared["cases"]),
            "fixed_split_patients": {
                name: sum(value == name for value in split["patients"].values())
                for name in ("train", "val", "test")},
        },
        "evaluation_protocol": {
            "test_patients": 50, "test_cines": 100, "all_test_frames_inferred": True,
            "labels_used_for_training": "expert ED/ES frames from training patients only",
            "labels_used_for_iou_dice": "expert-labeled frames from test patients only",
            "volume_reference": "same single-plane Simpson method on expert masks; not an independent clinical reference",
            "phase_source": "framewise predicted volume curve; labels do not select predicted extrema",
            "sequence_scope": "CAMUS half-cycle; no adjacent ED peaks for HR or CO",
            "simpson": "20-disk single-plane estimate; 2CH and 4CH are separate unsynchronized clips",
            "threshold": 0.5, "selection": "validation loss only",
        },
        "models": comparison_rows,
    }
    (report_root / "summary.json").write_text(
        json.dumps(report_data, indent=2), encoding="utf-8")

    lines = [
        "# CAMUS 左心室视频分割基线结果", "",
        "本报告记录左心室分割代码在完整 CAMUS 数据上的固定患者级基线运行。公开数据工程结果不构成贴片成像或临床验证。", "",
        "## 数据与划分", "",
        f"- 原始数据：{raw['patients_requested']} 名患者，{raw['files_verified']:,}/{raw['files_expected']:,} 个文件通过官方 SHA-256 校验；{raw['bytes_verified']:,} 字节，失败 {len(raw['failures'])}。",
        f"- 处理数据：{prepared['patients']} 名患者、{prepared['case_count']} 条 2CH/4CH cine、{report_data['dataset']['prepared_frames']:,} 帧；专家 ED/ES 掩码 {report_data['dataset']['expert_labeled_frames']:,} 帧。",
        f"- 固定患者集合：训练 {report_data['dataset']['fixed_split_patients']['train']}、验证 {report_data['dataset']['fixed_split_patients']['val']}、测试 {report_data['dataset']['fixed_split_patients']['test']} 名。",
        "- 原始影像以多帧 NIfTI cine 提供；处理保留帧顺序、像素间距、帧率、原始 ED/ES 掩码及坐标变换。CAMUS 遵循 CC BY-NC-SA 4.0 非商业科研条款与引用要求。", "",
        "## 基线性能", "",
        "五个模型使用共同的患者划分、192×256 输入、训练标注帧归一化、BCE + soft Dice、AdamW、固定 0.5 阈值和验证损失选模。测试集不参与归一化、选模或阈值调整。",
        f"每个模型测试 {summaries[0]['test_patients']} 名患者、{summaries[0]['test_cines']} 段 cine；{summaries[0]['inference_frames']:,} 帧全部推理，其中 {summaries[0]['labeled_frames']} 帧带标签，{summaries[0]['unlabeled_inference_frames']:,} 帧无标签。", "",
        "| 模型 | 患者平均 Dice | 患者平均 IoU | 标注帧 | 全帧推理 |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in comparison_rows:
        lines.append(
            f"| {row['model']} | {row['patient_mean_dice']:.4f} | "
            f"{row['patient_mean_iou']:.4f} | {row['labeled_frames']} | "
            f"{row['inference_frames']} |")

    lines.extend(["", "## 容积一致性", "",
                  "每帧预测掩码恢复到原图网格后，用原图像素间距计算 20 圆盘单平面 Simpson 估计，并按时间排列成容积波形。预测容积峰谷与人工 ED/ES 参考帧分开标记；人工标签不参与预测峰谷选择。2CH/4CH 是不同采集序列，不假设同步，也不逐帧组合。",
                  "容积 Bland–Altman 只使用有人工掩码的测试帧。预测掩码和专家掩码均使用同一 Simpson 方法，因而此项是同几何法轮廓代理的一致性，不是独立临床容积验证。逐帧配对存在患者内重复测量；患者/视图均值分析另行给出：", "",
                  "| 模型 | 视图 | 标注帧 bias [95% LoA] | 患者均值 bias [95% LoA] |",
                  "|---|---|---:|---:|"])
    for summary in summaries:
        frame_stats = summary["volume_bland_altman_by_labeled_frame_view"]
        patient_stats = summary["volume_bland_altman_by_patient_view_means"]
        for view in sorted(frame_stats):
            frame, patient = frame_stats[view], patient_stats[view]
            lines.append(
                f"| {summary['model']} | {view} | "
                f"{frame['bias']:.2f} [{frame['loa_lower']:.2f}, {frame['loa_upper']:.2f}] mL | "
                f"{patient['bias']:.2f} [{patient['loa_lower']:.2f}, "
                f"{patient['loa_upper']:.2f}] mL |")
    lines.extend(["", "CAMUS 仅提供半周期视频，HR/CO 按完整周期缺失原因保留为空。单平面 Simpson 估计不等于同步双平面测量或独立临床容积。", "",
                  "## 结果文件", "",
                  "- `model_comparison.csv` 与 `summary.json`：机器可读的固定测试结果及协议。",
                  "- `runs/lvseg_baselines/baseline_comparison.png`：五模型分割比较图。",
                  "- 每模型 `evaluation/`：全帧容积、标注帧指标、相位事件、预测掩码、波形图、标注帧轮廓图、Bland–Altman 图和汇总 JSON。", ""])
    (report_root / "RESULTS.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/lvseg.yaml")
    parser.add_argument("--stage", choices=("train", "evaluate", "all"), default="all")
    parser.add_argument("--model", action="append", help="Repeat to select individual baselines")
    parser.add_argument("--epochs", type=int, help="Override epochs for a clearly marked smoke run")
    parser.add_argument("--device", default="auto")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--reuse-checkpoints", action="store_true",
                        help="Skip training models that already have a checkpoint")
    parser.add_argument("--limit-test-cines", type=int, help="Use only the first test cases for smoke checks")
    parser.add_argument("--external-test-manifest",
                        help="Optional authorized dataset split manifest with split=test")
    args = parser.parse_args(argv)
    config = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))
    data, training, evaluation = config["dataset"], config["training"], config["evaluation"]
    prepared_root = Path(data["prepared_root"])
    if args.stage in ("train", "evaluate", "all"):
        _validate_prepared(prepared_root, Path(data["fixed_patient_splits"]))
    models = args.model or training["models"]
    unknown = set(models) - set(training["models"])
    if unknown:
        raise ValueError(f"Unconfigured baseline(s): {sorted(unknown)}")
    output_root = Path(evaluation["output_root"])
    output_root.mkdir(parents=True, exist_ok=True)
    summaries = []
    for name in models:
        model_dir = output_root / name
        checkpoint = model_dir / "best.pt"
        if args.stage in ("train", "all"):
            if checkpoint.is_file() and args.reuse_checkpoints and not args.overwrite:
                print(f"Reusing existing checkpoint: {name}", flush=True)
            else:
                result = train_model(name, prepared_root / "splits/train.json",
                                     prepared_root / "splits/val.json", model_dir,
                                     config=config, device=args.device, epochs=args.epochs,
                                     overwrite=args.overwrite)
                print(f"Training complete: {name}, best validation loss="
                      f"{result['best_val_loss']:.5f}", flush=True)
        if args.stage in ("evaluate", "all"):
            if not checkpoint.is_file():
                raise FileNotFoundError(f"Missing model checkpoint: {checkpoint}")
            test_manifest = prepared_root / "splits/test.json"
            if args.limit_test_cines:
                limited = json.loads(test_manifest.read_text(encoding="utf-8"))
                limited["cases"] = limited["cases"][:args.limit_test_cines]
                limited["dataset_root"] = os.path.relpath(prepared_root, start=model_dir)
                test_manifest = model_dir / "test_smoke.json"
                test_manifest.parent.mkdir(parents=True, exist_ok=True)
                test_manifest.write_text(json.dumps(limited, indent=2), encoding="utf-8")
            result_dir = model_dir / "evaluation"
            result = evaluate_model(
                checkpoint, test_manifest, result_dir, device=args.device,
                threshold=float(evaluation["threshold"]),
                min_period_s=float(evaluation["min_heart_period_s"]),
                max_period_s=float(evaluation["max_heart_period_s"]))
            summaries.append(result)
            plot_volume_bland_altman(output_root, name)
            plot_mask_comparison(
                test_manifest, result_dir, result_dir / "mask_comparison_example.png")
            if result.get("test_cines"):
                first_case = json.loads(test_manifest.read_text(encoding="utf-8"))["cases"][0]
                plot_volume_curve(result_dir, first_case["case_id"],
                                  result_dir / "volume_curve_example.png")
            if args.external_test_manifest:
                external_manifest = Path(args.external_test_manifest)
                external_name = external_manifest.parent.parent.name
                external_dir = model_dir / "external_evaluation" / external_name
                external_result = evaluate_model(
                    checkpoint, external_manifest, external_dir, device=args.device,
                    threshold=float(evaluation["threshold"]),
                    min_period_s=float(evaluation["min_heart_period_s"]),
                    max_period_s=float(evaluation["max_heart_period_s"]))
                external_result["dataset"] = external_name
                (external_dir / "summary.json").write_text(
                    json.dumps(external_result, indent=2), encoding="utf-8")
                plot_volume_bland_altman(external_dir)
                external_cases = json.loads(external_manifest.read_text(encoding="utf-8"))["cases"]
                if external_cases:
                    plot_volume_curve(external_dir, external_cases[0]["case_id"],
                                      external_dir / "volume_curve_example.png")
                print(f"External evaluation complete: {name} on {external_name}; "
                      f"units={external_result['volume_units']}", flush=True)
            print(f"Evaluation complete: {name}, patient-mean Dice="
                  f"{result['patient_mean_dice']}", flush=True)
    if summaries:
        _write_comparison(output_root, summaries)
        plot_baseline_comparison(output_root, [row["model"] for row in summaries])
        if len(summaries) == len(training["models"]):
            _write_project_report(output_root, training["models"])
    return summaries


def cli():
    main()


if __name__ == "__main__":
    main()
