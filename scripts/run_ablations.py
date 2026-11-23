"""Run the preregistered CAMUS module ablations without test-driven selection."""

from __future__ import annotations

import argparse
import gc
import json
from pathlib import Path
import statistics
import sys
import time

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import torch
import yaml

from lvseg.ablation_experiment import evaluate_validation, save_json, sha256, train_variant
from lvseg.data.temporal import LabeledClips
from lvseg.evaluate import _write_csv, evaluate_model


SOURCES = ("configs/lvseg_ablation.yaml", "docs/lvseg_ablation_protocol.md",
           "lvseg/models/ablation.py", "lvseg/models/architectures.py",
           "lvseg/data/temporal.py", "lvseg/losses.py", "lvseg/ablation_experiment.py",
           "lvseg/train.py", "lvseg/evaluate.py", "lvseg/metrics/segmentation.py",
           "lvseg/metrics/volume.py", "lvseg/metrics/cycles.py", "scripts/run_ablations.py")
METRICS = ("dice", "miou", "precision", "recall", "hd95", "asd", "volume_absolute_error_ml")


def summarize(records, config):
    rows = []
    baseline = {row["seed"]: row["validation"]["metrics"] for row in records if row["variant"] == "B"}
    for variant, options in config["variants"].items():
        runs = [record for record in records if record["variant"] == variant]
        if not runs:
            continue
        row = {"variant": variant, **options, "runs": len(runs),
               "seeds": [run["seed"] for run in runs],
               "parameters": runs[0]["validation"]["parameter_count"]}
        for key in METRICS:
            values = [run["validation"]["metrics"][key] for run in runs]
            row[key] = statistics.mean(values)
            row[key + "_sd"] = statistics.stdev(values) if len(values) > 1 else None
        deltas = [run["validation"]["metrics"]["dice"] - baseline[run["seed"]]["dice"]
                  for run in runs if run["seed"] in baseline]
        row["paired_dice_deltas"] = deltas
        row["paired_wins"] = sum(delta > 0 for delta in deltas)
        row["mean_paired_dice_gain"] = statistics.mean(deltas) if deltas else None
        for sigma in config["evaluation"]["noise_sigmas"]:
            noise_key = f"noise_{sigma}"
            row[noise_key + "_dice"] = statistics.mean(run[noise_key]["metrics"]["dice"] for run in runs)
        rows.append(row)
    return rows


def write_reports(report, records, rows, config, *, complete=False, selection=None):
    save_json(report / "results.json", {"complete": complete, "split": "val",
              "test_used_for_selection": False, "selection": selection,
              "models": rows, "runs": records})
    _write_csv(report / "validation_comparison.csv", rows)
    lines = ["# Attention-UNet 模块消融结果", "",
             "固定患者级划分；本表为原始尺寸上按患者汇总的验证指标，结构选择未使用测试集。",
             "B 为本轮相同训练配置下重新训练的 Attention-UNet；S=SE 替换 AG，D=空洞残差编码器，T=最深层 ConvLSTM，E=边缘分支及 Sobel 损失。", "",
             f"状态：{'全部验证实验完成' if complete else '实验进行中，当前均值仅覆盖已完成种子'}。", "",
             "| 组别 | 次数 | Dice | mIoU | Precision | Recall | HD95 (mm) | ASD (mm) | 容积 MAE (mL) | ΔDice 对 B | 参数 (M) |",
             "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for row in rows:
        gain = row["mean_paired_dice_gain"]
        lines.append(f"| {row['variant']} | {row['runs']} | {row['dice']:.4f} | "
                     f"{row['miou']:.4f} | {row['precision']:.4f} | {row['recall']:.4f} | "
                     f"{row['hd95']:.2f} | {row['asd']:.2f} | {row['volume_absolute_error_ml']:.2f} | "
                     f"{gain:+.4f} | {row['parameters'] / 1e6:.2f} |")
    lines += ["", "## 验证集人工散斑压力测试", "",
              "固定噪声与病例；I_noisy=clip(I×(1+σZ),0,1)。越高越好。", "",
              "| 组别 | 干净 Dice | σ=0.1 Dice | σ=0.2 Dice | 配对种子胜出次数 |",
              "|---|---:|---:|---:|---:|"]
    for row in rows:
        lines.append(f"| {row['variant']} | {row['dice']:.4f} | {row['noise_0.1_dice']:.4f} | "
                     f"{row['noise_0.2_dice']:.4f} | {row['paired_wins']}/{row['runs']} |")
    if selection:
        lines += ["", "## 预设标准下的选择", "", selection["explanation"], "",
                  "主指标：跨种子验证 Dice；预设收益标准为比 B 增加至少 0.002、至少两个配对种子胜出且平均 HD95 不恶化。",
                  "完整种子结果、离散程度、上下文覆盖率和同几何法容积 Bland–Altman 见 `results.json`。"]
    lines += ["", "本轮为三次独立训练的探索性验证，未证明模块新颖性、临床有效性或贴片域泛化。",
              "容积参考由专家掩膜经相同单平面几何法得到；CAMUS 半周期不计算 HR/CO。", ""]
    (report / "RESULTS.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("configs/lvseg_ablation.yaml"))
    parser.add_argument("--device", default="auto")
    parser.add_argument("--stage", choices=("validation", "final-test"), default="validation")
    args = parser.parse_args(argv)
    config = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    device = ("cuda" if torch.cuda.is_available() else "cpu") if args.device == "auto" else args.device
    torch.set_num_threads(2)
    if device.startswith("cuda"):
        torch.backends.cudnn.benchmark = True
    report = Path(config["evaluation"]["report_root"])
    output = Path(config["evaluation"]["output_root"])
    report.mkdir(parents=True, exist_ok=True)
    output.mkdir(parents=True, exist_ok=True)
    prepared = Path(config["dataset"]["prepared_root"])
    manifests = {split: prepared / "splits" / f"{split}.json" for split in ("train", "val", "test")}
    patients = {split: {row["patient_id"] for row in json.loads(path.read_text(
        encoding="utf-8"))["cases"]} for split, path in manifests.items()}
    if patients["train"] & patients["val"] or (patients["train"] | patients["val"]) & patients["test"]:
        raise ValueError("Patient overlap across experiment splits")
    fixed_path = Path(config["dataset"]["fixed_patient_splits"])
    fixed = json.loads(fixed_path.read_text(encoding="utf-8"))["patients"]
    for split in patients:
        if patients[split] != {patient for patient, assigned in fixed.items() if assigned == split}:
            raise ValueError(f"The established patient split changed: {split}")
    input_hashes = {}
    for split in ("train", "val"):
        for case in json.loads(manifests[split].read_text(encoding="utf-8"))["cases"]:
            for extension in (".json", ".npz"):
                path = prepared / f"{case['case_id']}{extension}"
                input_hashes[path.as_posix()] = sha256(path)
    audit_path = report / "input_hashes.json"
    if audit_path.exists():
        if json.loads(audit_path.read_text(encoding="utf-8")) != input_hashes:
            raise ValueError("Prepared development input changed after experiment freeze")
    else:
        save_json(audit_path, input_hashes)
    source_hashes = {path: sha256(path) for path in SOURCES}
    manifest_hashes = {split: sha256(path) for split, path in manifests.items()}
    lock = {"config": config, "source_hashes": source_hashes, "manifest_hashes": manifest_hashes,
            "patient_counts": {key: len(values) for key, values in patients.items()},
            "test_used_for_selection": False, "fixed_split_sha256": sha256(fixed_path),
            "input_audit_sha256": sha256(audit_path)}
    protocol_path = report / "protocol_lock.json"
    if protocol_path.is_file():
        if json.loads(protocol_path.read_text(encoding="utf-8")) != lock:
            raise ValueError("Preregistered code/configuration changed; use a new experiment version")
    else:
        save_json(protocol_path, lock)
    if args.stage == "final-test":
        selection = json.loads((report / "selection_lock.json").read_text(encoding="utf-8"))
        if not selection["eligible"]:
            raise ValueError("No improvement passed validation; discuss the next design before final testing")
        final = []
        for seed in config["training"]["seeds"]:
            for variant in config["variants"]:
                run_dir = output / f"seed_{seed}" / variant
                final_summary = run_dir / "test" / "summary.json"
                summary = (json.loads(final_summary.read_text(encoding="utf-8"))
                           if final_summary.is_file() else evaluate_model(
                               run_dir / "best.pt", manifests["test"], run_dir / "test", device=device))
                final.append({"seed": seed, "variant": variant, "summary": summary})
                save_json(report / "final_test.json", {"selection": selection, "runs": final})
        return

    started = time.time()
    train_set = LabeledClips(manifests["train"], context_frames=config["training"]["context_frames"],
                             augment=config["training"]["horizontal_flip"])
    val_set = LabeledClips(manifests["val"], context_frames=config["training"]["context_frames"])
    val_set.mean, val_set.std = train_set.mean, train_set.std
    records = []
    for seed in config["training"]["seeds"]:
        for variant, options in config["variants"].items():
            run_dir = output / f"seed_{seed}" / variant
            metadata = train_variant(variant, options, seed, config, train_set, val_set, run_dir, device)
            record = {"seed": seed, "variant": variant, "options": options,
                      "training_seconds": metadata["elapsed_s"], "run_dir": run_dir.as_posix()}
            record["validation"] = evaluate_validation(
                run_dir / "best.pt", val_set, run_dir / "validation", config, device)
            for sigma in config["evaluation"]["noise_sigmas"]:
                record[f"noise_{sigma}"] = evaluate_validation(
                    run_dir / "best.pt", val_set, run_dir / f"noise_{sigma}", config, device,
                    noise_sigma=sigma)
            records.append(record)
            rows = summarize(records, config)
            write_reports(report, records, rows, config)
            print(f"COMPLETED {len(records)}/{len(config['variants']) * len(config['training']['seeds'])}: "
                  f"{variant} seed={seed} val_dice={record['validation']['metrics']['dice']:.5f} "
                  f"total_hours={(time.time()-started)/3600:.2f}", flush=True)
            gc.collect()
            if device.startswith("cuda"):
                torch.cuda.empty_cache()
    baseline = next(row for row in rows if row["variant"] == "B")
    candidates = [row for row in rows if row["variant"] != "B"]
    best = max(candidates, key=lambda row: (row["dice"], -row["hd95"], -row["parameters"]))
    eligible_candidates = [row for row in candidates
                           if row["mean_paired_dice_gain"] >= config["evaluation"]["minimum_dice_gain"]
                           and row["paired_wins"] >= 2 and row["hd95"] <= baseline["hd95"]]
    eligible = bool(eligible_candidates)
    selected = max(eligible_candidates, key=lambda row: (row["dice"], -row["hd95"], -row["parameters"])) \
        if eligible else baseline
    selection = {"selected": selected["variant"], "best_candidate": best["variant"],
                 "eligible": eligible, "test_used_for_selection": False,
                 "explanation": f"验证集最佳新结构为 {best['variant']}，Dice={best['dice']:.4f}，"
                 f"相对本轮 B 的配对均值差 {best['mean_paired_dice_gain']:+.4f}，"
                 f"种子胜出 {best['paired_wins']}/{best['runs']}。"
                 + (f"候选 {selected['variant']} 达到预设标准，可冻结后进行最终测试。" if eligible else
                    "未达到全部预设收益条件，保留 Attention-UNet，先讨论下一轮方案。"),
                 "protocol_sha256": sha256(protocol_path),
                 "checkpoint_hashes": {record["run_dir"]: record["validation"]["checkpoint_sha256"]
                                       for record in records}}
    save_json(report / "selection_lock.json", selection)
    write_reports(report, records, rows, config, complete=True, selection=selection)
    print(selection["explanation"], flush=True)


if __name__ == "__main__":
    main()
