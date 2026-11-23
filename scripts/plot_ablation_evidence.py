"""Plot matched validation evidence from existing checkpoints' metric CSVs."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from statistics import mean, median

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.ticker import MaxNLocator
import numpy as np


DISPLAY_NAMES = {"B": "Attention-UNet", "DTE": "DRA-UNet"}


def read_rows(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def write_rows(path, rows):
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def save(fig, output, name):
    fig.savefig(output / f"{name}.png", dpi=300)
    fig.savefig(output / f"{name}.pdf")
    fig.savefig(output / f"{name}.svg")
    plt.close(fig)


def plot_seed_dice(result, output):
    labels = [model["variant"] for model in result["models"] if model["variant"] != "B"]
    by_seed = {(run["variant"], run["seed"]): run["validation"]["metrics"]["dice"]
               for run in result["runs"]}
    seeds = sorted(seed for variant, seed in by_seed if variant == "B")
    fig, ax = plt.subplots(figsize=(7.2, 3.8), layout="constrained")
    positions = np.arange(len(labels))
    for index, seed in enumerate(seeds):
        values = [100 * (by_seed[name, seed] - by_seed["B", seed]) for name in labels]
        ax.scatter(values, positions + (index - (len(seeds) - 1) / 2) * .19,
                   label=str(seed), s=24, zorder=3)
    ax.axvline(0, color="#697583", linewidth=.8)
    ax.axvline(.2, color="#697583", linestyle=":", linewidth=.9)
    ax.set(yticks=positions, yticklabels=[DISPLAY_NAMES.get(name, name) for name in labels],
           xlabel="Paired Dice difference (percentage points)",
           title="CAMUS validation | Difference from Attention U-Net by seed")
    ax.invert_yaxis()
    ax.legend(title="Training seed", loc="lower center", bbox_to_anchor=(.5, 1.08),
              ncols=len(seeds))
    save(fig, output, "seed_dice")


def plot_matched_evidence(result, output, reference, candidate, prepared):
    runs = {(run["variant"], run["seed"]): Path(run["run_dir"]) for run in result["runs"]}
    seeds = sorted(seed for name, seed in runs if name == reference and (candidate, seed) in runs)
    if not seeds:
        raise ValueError("No matching seeds for the selected contrast.")

    patients, strata, curves = {}, [], []
    labels = ("dice", "hd95", "asd", "volume_absolute_error_ml")
    colors = {reference: "#64748b", candidate: "#116b75"}
    fig, ax = plt.subplots(figsize=(7.2, 3.2), layout="constrained")
    phases_by_case = {}
    for seed in seeds:
        ref_dir, candidate_dir = (runs[name, seed] for name in (reference, candidate))
        for name, root in ((reference, ref_dir), (candidate, candidate_dir)):
            history = json.loads((root / "history.json").read_text(encoding="utf-8"))
            for row in history:
                curves.append({"variant": name, "seed": seed, "epoch": row["epoch"],
                               **{key: row[key] for key in ("validation_segmentation_loss",
                                                           "epoch_seconds")}})
            ax.plot([row["epoch"] for row in history],
                    [row["validation_segmentation_loss"] for row in history],
                    color=colors[name], alpha=.68)

        def paired_csv(filename, keys):
            sources = [read_rows(path / "validation" / filename) for path in (ref_dir, candidate_dir)]
            indexed = [{tuple(row[key] for key in keys): row for row in data} for data in sources]
            if indexed[0].keys() != indexed[1].keys():
                raise ValueError("The two variants have different validation observations.")
            return [(row, indexed[1][key]) for key, row in indexed[0].items()]

        for before, after in paired_csv("patient_metrics.csv", ("patient_id",)):
            patients.setdefault(before["patient_id"], []).append(
                {key: float(after[key]) - float(before[key])
                 for key in labels if before[key] and after[key]})
        for before, after in paired_csv("labeled_frame_metrics.csv", ("case_id", "frame")):
            case = before["case_id"]
            if case not in phases_by_case:
                metadata = json.loads((prepared / f"{case}.json").read_text(encoding="utf-8"))
                if metadata["split"] != "val":
                    raise ValueError(f"Expected validation data for {case}.")
                phases_by_case[case] = {int(index): label for label, index in
                                       metadata["phases"].items()}
            phase = phases_by_case[case][int(before["frame"])]
            strata.append({"seed": seed, "patient_id": before["patient_id"], "view": before["view"],
                           "phase": phase, "reference_context": before["context_length"],
                           "candidate_context": after["context_length"],
                           **{f"delta_{key}": float(after[key]) - float(before[key])
                              if before[key] and after[key] else None for key in labels}})

    before_label = DISPLAY_NAMES.get(reference, reference)
    after_label = DISPLAY_NAMES.get(candidate, candidate)
    ax.legend(handles=[Line2D([0], [0], label=label, color=colors[name])
                       for name, label in ((reference, before_label), (candidate, after_label))])
    ax.set(xlabel="Training epoch", ylabel="Validation BCE + Dice loss",
           title=f"{before_label} vs {after_label} | One curve per seed")
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    save(fig, output, "convergence")
    write_rows(output / "convergence.csv", curves)
    write_rows(output / "frame_pairs.csv", strata)

    patient_rows = [{"patient_id": patient, "paired_seeds": len(values),
                     **{f"delta_{key}": mean([row[key] for row in values if key in row])
                        if any(key in row for row in values) else None for key in labels}}
                    for patient, values in sorted(patients.items())]
    write_rows(output / "patient_pairs.csv", patient_rows)
    deltas = sorted(100 * row["delta_dice"] for row in patient_rows)
    fig, ax = plt.subplots(figsize=(7.2, 3.4), layout="constrained")
    ax.ecdf(deltas, color="#116b75")
    ax.axvline(0, color="#697583", linewidth=.8)
    ax.set(xlabel="Per-patient Dice difference (percentage points)", ylabel="Cumulative fraction",
           title=f"{after_label} minus {before_label} | {len(deltas)} validation patients")
    save(fig, output, "patient_dice")

    summaries = []
    for seed in seeds:
        for view in ("2CH", "4CH"):
            for phase in ("ED", "ES"):
                group = [row for row in strata if (row["seed"], row["view"], row["phase"])
                         == (seed, view, phase)]
                summary = {"seed": seed, "view": view, "phase": phase,
                           "patients": len({row["patient_id"] for row in group})}
                for key in labels:
                    values = [row[f"delta_{key}"] for row in group if row[f"delta_{key}"] is not None]
                    summary[f"mean_delta_{key}"] = mean(values) if values else None
                summaries.append(summary)
    write_rows(output / "phase_view_summary.csv", summaries)
    print(f"{candidate} vs {reference}: {sum(delta > 0 for delta in deltas)}/{len(deltas)} "
          f"patients improved, median {median(deltas):+.3f} Dice points.")


def plot_history_controls(source, output, candidate):
    rows = read_rows(source)
    controls = {"current_only": "Current frame only", "repeated_target": "Repeated target",
                "reversed_history": "Reversed past frames"}
    labels = [name for name in controls if any(row["condition"] == name for row in rows)]
    seeds = sorted({row["seed"] for row in rows})
    fig, ax = plt.subplots(figsize=(7.2, 2.8), layout="constrained")
    positions = np.arange(len(labels))
    for index, seed in enumerate(seeds):
        means = [100 * mean(float(row["delta_dice"]) for row in rows
                            if row["condition"] == name and row["seed"] == seed)
                 for name in labels]
        ax.scatter(means, positions + (index - (len(seeds) - 1) / 2) * .16,
                   label=seed, s=26)
    ax.axvline(0, color="#697583", linewidth=.8)
    ax.set(yticks=positions, yticklabels=[controls[name] for name in labels],
           xlabel="Dice with real history minus control (percentage points)",
           title=f"{DISPLAY_NAMES.get(candidate, candidate)} | Same labeled target and frozen weights")
    ax.invert_yaxis()
    ax.legend(loc="lower center", bbox_to_anchor=(.5, 1.08), ncols=len(seeds))
    save(fig, output, "context_dice")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("results", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--reference", default="B")
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--prepared", type=Path, default=Path("data/processed/camus_video"))
    parser.add_argument("--context-deltas", type=Path)
    args = parser.parse_args()
    result = json.loads(args.results.read_text(encoding="utf-8"))
    if result["split"] != "val" or not result["complete"]:
        raise ValueError("Provide the complete validation results for a single round.")
    plt.rcParams.update({"font.family": "Arial", "font.size": 9, "pdf.fonttype": 42,
                         "svg.fonttype": "none", "axes.spines.top": False,
                         "axes.spines.right": False, "legend.frameon": False})
    args.output.mkdir(parents=True, exist_ok=True)
    plot_seed_dice(result, args.output)
    plot_matched_evidence(result, args.output, args.reference, args.candidate, args.prepared)
    if args.context_deltas:
        plot_history_controls(args.context_deltas, args.output, args.candidate)


if __name__ == "__main__":
    main()
