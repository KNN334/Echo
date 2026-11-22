"""Run the five LV segmentation baselines with independent random seeds."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import statistics
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import yaml

from lvseg.evaluate import evaluate_model
from lvseg.train import train_model


TEST_METRICS = (
    "patient_mean_dice", "patient_mean_miou", "patient_mean_precision",
    "patient_mean_recall", "patient_mean_hd95", "patient_mean_asd",
)
DEFAULT_SEEDS = (2026, 2027, 2028, 2029, 2030)


def _best_validation(history: list[dict]) -> dict:
    if not history:
        raise ValueError("Training history is empty")
    return min(history, key=lambda row: row["val_loss"])


def _mean_sd(values: list[float]) -> tuple[float, float]:
    return statistics.mean(values), statistics.stdev(values) if len(values) > 1 else 0.0


def _aggregate_model_runs(model: str, runs: list[dict]) -> dict:
    row = {"model": model, "run_count": len(runs),
           "seeds": [run["seed"] for run in runs]}
    for key, prefix in (("best_validation_dice", "validation_mean_dice"),
                        ("best_validation_loss", "validation_mean_loss")):
        mean, sd = _mean_sd([float(run[key]) for run in runs])
        row[prefix] = mean
        row[prefix.replace("mean", "sd")] = sd
    for metric in TEST_METRICS:
        mean, sd = _mean_sd([float(run["test_metrics"][metric]) for run in runs])
        row[metric] = mean
        row[f"{metric}_sd"] = sd
    return row


def _select_baseline(rows: list[dict]) -> str:
    """Select by mean validation Dice, with mean validation loss as tie-breaker."""
    if not rows:
        raise ValueError("No model results to select from")
    return max(rows, key=lambda row: (
        row["validation_mean_dice"], -row["validation_mean_loss"]))["model"]


def _training_is_complete(run_dir: Path, model: str, seed: int,
                          training_config: dict) -> bool:
    run_path, history_path, checkpoint_path = (
        run_dir / "run.json", run_dir / "history.json", run_dir / "best.pt")
    if not all(path.is_file() for path in (run_path, history_path, checkpoint_path)):
        return False
    run = json.loads(run_path.read_text(encoding="utf-8"))
    history = json.loads(history_path.read_text(encoding="utf-8"))
    return (run.get("model") == model and run.get("seed") == seed and
            run.get("config") == training_config and
            run.get("epochs_completed") == len(history) and
            bool(history) and checkpoint_path.stat().st_size > 0)


def _fixed_patient_ids(manifest_path: Path) -> set[str]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    return {case["patient_id"] for case in manifest["cases"]}


def _write_reports(report_root: Path, seeds: list[int], records: list[dict],
                   rows: list[dict], selected: str) -> None:
    report_root.mkdir(parents=True, exist_ok=True)
    metric_fields = [field for metric in TEST_METRICS
                     for field in (metric, f"{metric}_sd")]
    fields = ["model", "selected_by_validation", "run_count", "seeds",
              "validation_mean_dice", "validation_sd_dice",
              "validation_mean_loss", "validation_sd_loss", *metric_fields]
    with (report_root / "model_comparison.csv").open(
            "w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({**row, "selected_by_validation": row["model"] == selected,
                             "seeds": ",".join(map(str, row["seeds"]))})

    protocol = {
        "seeds": seeds,
        "runs_per_model": len(seeds),
        "selection_metric": "mean validation Dice at the checkpoint with minimum validation loss",
        "selected_baseline": selected,
        "test_set_used_for_selection": False,
        "test_metric_summary": "mean and sample standard deviation across independent seeds; each seed first averages labeled-frame metrics within patient",
    }
    (report_root / "repeated_runs.json").write_text(json.dumps({
        "protocol": protocol,
        "models": rows,
        "runs": records,
    }, indent=2), encoding="utf-8")

    summary_path = report_root / "summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.exists() else {}
    evaluation = summary.setdefault("evaluation_protocol", {})
    evaluation.update({
        "training_seeds": seeds,
        "runs_per_model": len(seeds),
        "selection": protocol["selection_metric"],
        "test_set_used_for_model_selection": False,
        "test_metric_aggregation": protocol["test_metric_summary"],
    })
    summary["project_version"] = "0.8.0"
    summary["selected_baseline"] = selected
    summary["models"] = rows
    summary["runs_file"] = "repeated_runs.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    results_path = report_root / "RESULTS.md"
    if results_path.exists():
        text = results_path.read_text(encoding="utf-8")
        section_start = text.index("## 基线性能")
        section_end = text.index("## 容积一致性", section_start)
        lines = [
            "## 基线性能", "",
            f"五种模型在相同患者级划分上各进行 {len(seeds)} 次独立训练（随机种子：{', '.join(map(str, seeds))}）。每次训练按验证损失选择权重；基线按跨种子的验证集 Dice 均值选择，测试集不参与模型选择。表中验证集 Dice 和各测试指标均为跨种子均值 ± 样本标准差；每次测试指标先按患者求均值。", "",
            f"按验证集 Dice 均值选出的基线：**{selected}**。", "",
            "| 模型 | 验证集 Dice | 测试 Dice | 测试 mIoU | Precision | Recall | HD95 (mm) | ASD (mm) |",
            "|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
        for row in rows:
            model_name = f"**{row['model']}**" if row["model"] == selected else row["model"]
            values = [
                f"{row['validation_mean_dice']:.4f} ± {row['validation_sd_dice']:.4f}",
                f"{row['patient_mean_dice']:.4f} ± {row['patient_mean_dice_sd']:.4f}",
                f"{row['patient_mean_miou']:.4f} ± {row['patient_mean_miou_sd']:.4f}",
                f"{row['patient_mean_precision']:.4f} ± {row['patient_mean_precision_sd']:.4f}",
                f"{row['patient_mean_recall']:.4f} ± {row['patient_mean_recall_sd']:.4f}",
                f"{row['patient_mean_hd95']:.2f} ± {row['patient_mean_hd95_sd']:.2f}",
                f"{row['patient_mean_asd']:.2f} ± {row['patient_mean_asd_sd']:.2f}",
            ]
            lines.append(f"| {model_name} | " + " | ".join(values) + " |")
        text = text[:section_start] + "\n".join(lines) + "\n\n" + text[section_end:]
        marker = "## 容积一致性\n"
        text = text.replace(marker, marker +
                            "\n体积一致性细表记录的是首轮种子 2026 的结果；重复训练的分割指标汇总见 `repeated_runs.json`。\n", 1)
        results_path.write_text(text, encoding="utf-8", newline="\n")


def run_repeated_baselines(config_path: Path, seeds: list[int], device: str) -> dict:
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    dataset = config["dataset"]
    models = config["training"]["models"]
    prepared_root = Path(dataset["prepared_root"])
    train_manifest = prepared_root / "splits" / "train.json"
    val_manifest = prepared_root / "splits" / "val.json"
    test_manifest = prepared_root / "splits" / "test.json"
    expected_train = _fixed_patient_ids(train_manifest)
    expected_val = _fixed_patient_ids(val_manifest)
    expected_test = _fixed_patient_ids(test_manifest)
    if expected_train & expected_val or (expected_train | expected_val) & expected_test:
        raise ValueError("Patient overlap across the fixed train/validation/test split")

    legacy_root = Path("runs/lvseg_baselines")
    repeated_root = Path("runs/lvseg_repeated")
    records = []
    for seed in seeds:
        training_config = {**config["training"], "seed": seed}
        for model in models:
            run_dir = legacy_root / model if seed == 2026 else repeated_root / f"seed_{seed}" / model
            checkpoint = run_dir / "best.pt"
            if not _training_is_complete(run_dir, model, seed, training_config):
                if seed == 2026:
                    raise ValueError(f"Cannot reuse the existing seed-2026 run: {model}")
                run_config = {**config, "training": training_config}
                train_model(model, train_manifest, val_manifest, run_dir,
                            config=run_config, device=device, overwrite=True)

            run_metadata = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
            if set(run_metadata["train_patients"]) != expected_train or set(
                    run_metadata["val_patients"]) != expected_val:
                raise ValueError(f"Fixed train/validation patients changed for {model}, seed {seed}")
            validation = _best_validation(json.loads(
                (run_dir / "history.json").read_text(encoding="utf-8")))

            evaluation_dir = run_dir / "evaluation"
            summary_path = evaluation_dir / "summary.json"
            if (not summary_path.is_file() or
                    summary_path.stat().st_mtime < checkpoint.stat().st_mtime):
                test_summary = evaluate_model(
                    checkpoint, test_manifest, evaluation_dir, device=device,
                    threshold=float(config["evaluation"]["threshold"]),
                    min_period_s=float(config["evaluation"]["min_heart_period_s"]),
                    max_period_s=float(config["evaluation"]["max_heart_period_s"]))
            else:
                test_summary = json.loads(summary_path.read_text(encoding="utf-8"))
            if test_summary.get("test_patients") != len(expected_test):
                raise ValueError(f"Incomplete test evaluation for {model}, seed {seed}")
            record = {
                "seed": seed, "model": model,
                "best_epoch": validation["epoch"],
                "best_validation_loss": validation["val_loss"],
                "best_validation_dice": validation["val_dice"],
                "test_metrics": {metric: test_summary.get(metric) for metric in TEST_METRICS},
            }
            records.append(record)
            print(f"Completed {model}, seed {seed}: val Dice="
                  f"{validation['val_dice']:.4f}, test Dice="
                  f"{test_summary['patient_mean_dice']:.4f}", flush=True)

    rows = [_aggregate_model_runs(model, [record for record in records
                                          if record["model"] == model])
            for model in models]
    selected = _select_baseline(rows)
    report_root = Path("reports/lvseg_baselines")
    _write_reports(report_root, seeds, records, rows, selected)
    return {"selected_baseline": selected, "models": rows}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("configs/lvseg.yaml"))
    parser.add_argument("--seeds", nargs="+", type=int, default=list(DEFAULT_SEEDS))
    parser.add_argument("--device", default="auto")
    args = parser.parse_args(argv)
    seeds = list(dict.fromkeys(args.seeds))
    if len(seeds) < 2:
        parser.error("at least two independent seeds are required")
    result = run_repeated_baselines(args.config, seeds, args.device)
    print(json.dumps({"selected_baseline": result["selected_baseline"],
                      "seeds": seeds}, indent=2), flush=True)


if __name__ == "__main__":
    main()
