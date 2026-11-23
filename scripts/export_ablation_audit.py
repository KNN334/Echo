"""Export per-seed validation metrics, paired differences, and a readable audit."""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
import statistics


METRICS = (
    "dice",
    "miou",
    "precision",
    "recall",
    "hd95",
    "asd",
    "volume_absolute_error_ml",
)


def _write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        raise ValueError("No completed runs were found in the experiment summary")
    with path.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def export_audit(source: Path, output: Path) -> None:
    result = json.loads(source.read_text(encoding="utf-8"))
    records = result["runs"]
    baseline = {
        run["seed"]: run["validation"]["metrics"]
        for run in records
        if run["variant"] == "B"
    }
    if not baseline:
        raise ValueError("The results file must include a B baseline for each seed")

    detailed = []
    paired = []
    grouped = defaultdict(list)
    for run in records:
        validation = run["validation"]
        metrics = validation["metrics"]
        reference = baseline[run["seed"]]
        row = {
            "seed": run["seed"],
            "variant": run["variant"],
            "se": run["options"]["se"],
            "dilated_residual": run["options"]["dilated_residual"],
            "temporal": run["options"]["temporal"],
            "edge": run["options"]["edge"],
            "best_epoch": validation["best_epoch"],
            "context_lengths": json.dumps(validation["context_lengths"], sort_keys=True),
        }
        for metric in METRICS:
            row[metric] = metrics[metric]
        row["noise_0.1_dice"] = run["noise_0.1"]["metrics"]["dice"]
        row["noise_0.2_dice"] = run["noise_0.2"]["metrics"]["dice"]
        row["checkpoint_sha256"] = validation["checkpoint_sha256"]
        detailed.append(row)
        grouped[run["variant"]].append(row)

        paired_row = {"seed": run["seed"], "variant": run["variant"]}
        for metric in METRICS:
            paired_row[f"delta_{metric}"] = metrics[metric] - reference[metric]
        paired.append(paired_row)

    output.mkdir(parents=True, exist_ok=True)
    _write_csv(output / "per_seed_metrics.csv", detailed)
    _write_csv(output / "paired_deltas.csv", paired)

    summary = []
    for variant, runs in grouped.items():
        summary_row = {
            "variant": variant,
            "runs": len(runs),
        }
        for metric in METRICS:
            summary_row[metric] = statistics.mean(row[metric] for row in runs)
            summary_row[f"mean_delta_{metric}"] = statistics.mean(
                row[f"delta_{metric}"] for row in paired if row["variant"] == variant
            )
        summary.append(summary_row)
    _write_csv(output / "variant_summary.csv", summary)

    lines = [
        "# 首轮模块消融审计",
        "",
        f"首轮状态为 {'完成' if result['complete'] else '进行中'}，共记录 {len(records)} 次训练。",
        "所有差值均为候选模型减去同随机种子 B。Dice、mIoU、Precision、Recall 越高越好。",
        "HD95、ASD 和容积 MAE 越低越好。DTE 对应 DRA-UNet，逐种子指标见同目录 CSV。",
        "",
        "| 变体 | Dice | mIoU | Precision | Recall | HD95 (mm) | ASD (mm) | 容积 MAE (mL) | 配对 ΔDice |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary:
        lines.append(
            f"| {row['variant']} | {row['dice']:.4f} | {row['miou']:.4f} | {row['precision']:.4f} | "
            f"{row['recall']:.4f} | {row['hd95']:.2f} | {row['asd']:.2f} | "
            f"{row['volume_absolute_error_ml']:.2f} | {row['mean_delta_dice']:+.4f} |"
        )
    lines += [
        "",
        "## 同种子配对差值",
        "",
        "每个单元格为候选减 B。负的边界距离或容积误差差值表示改善。",
        "",
        "| 种子 | 变体 | ΔDice | ΔPrecision | ΔRecall | ΔHD95 (mm) | ΔASD (mm) | Δ容积 MAE (mL) |",
        "|---:|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in paired:
        lines.append(
            f"| {row['seed']} | {row['variant']} | {row['delta_dice']:+.5f} | "
            f"{row['delta_precision']:+.5f} | {row['delta_recall']:+.5f} | "
            f"{row['delta_hd95']:+.3f} | {row['delta_asd']:+.3f} | "
            f"{row['delta_volume_absolute_error_ml']:+.3f} |"
        )
    (output / "FIRST_ROUND_AUDIT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("results", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    export_audit(args.results, args.output)


if __name__ == "__main__":
    main()
