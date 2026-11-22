"""Compare held-out patient-level segmentation and volume agreement."""

from __future__ import annotations

import csv
import json
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", str(Path(".work/matplotlib").resolve()))

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D


def _read_csv(path: Path):
    with path.open(newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def _audit_two_panel_geometry(fig, axes, report_path: Path) -> None:
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    boxes = [axis.get_window_extent(renderer=renderer) for axis in axes]
    widths = [box.width / fig.dpi * 72.0 for box in boxes]
    heights = [box.height / fig.dpi * 72.0 for box in boxes]
    width_delta, height_delta = max(widths) - min(widths), max(heights) - min(heights)
    report = {
        "panel_count": len(boxes), "widths_pt": widths, "heights_pt": heights,
        "max_width_difference_pt": width_delta,
        "max_height_difference_pt": height_delta,
        "tolerance_pt": 1.5,
        "status": "PASS" if width_delta <= 1.5 and height_delta <= 1.5 else "FAIL",
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    if report["status"] != "PASS":
        raise RuntimeError(f"Comparable plot panels are misaligned: {report}")


def plot_mask_comparison(split_manifest: str | Path, evaluation_dir: str | Path,
                         output: str | Path) -> Path:
    """Show expert and predicted contours on labeled test frames only."""
    split_manifest, evaluation_dir, output = map(Path,
                                                  (split_manifest, evaluation_dir, output))
    manifest = json.loads(split_manifest.read_text(encoding="utf-8"))
    dataset_root = (split_manifest.parent / manifest["dataset_root"]).resolve()
    selected = {}
    for case in manifest["cases"]:
        selected.setdefault(case["view"], case)

    examples = []
    for view, case in selected.items():
        case_id = case["case_id"]
        metadata = json.loads((dataset_root / f"{case_id}.json").read_text(encoding="utf-8"))
        with np.load(dataset_root / f"{case_id}.npz", allow_pickle=False) as arrays:
            frames = arrays["frames"]
            labels = arrays["masks"]
            labeled = arrays["labeled"].astype(bool)
        predicted_path = evaluation_dir / "predicted_masks" / f"{case_id}.npz"
        with np.load(predicted_path, allow_pickle=False) as arrays:
            predictions = arrays["model_grid_masks"]
        for phase in ("ED", "ES"):
            index = metadata.get("phases", {}).get(phase)
            if index is None or not 0 <= int(index) < len(frames) or not labeled[int(index)]:
                continue
            index = int(index)
            examples.append((view, phase, index, frames[index], labels[index],
                             predictions[index]))

    if not examples:
        raise ValueError("No expert-labeled ED/ES frames available for mask comparison")
    columns = min(2, len(examples))
    rows = int(np.ceil(len(examples) / columns))
    fig, axes = plt.subplots(rows, columns, figsize=(5.0 * columns, 4.2 * rows),
                             squeeze=False)
    for ax, (view, phase, index, image, reference, prediction) in zip(axes.flat, examples):
        ax.imshow(image, cmap="gray", vmin=0, vmax=255)
        if reference.any():
            ax.contour(reference, levels=[0.5], colors=["#FFD166"], linewidths=1.4)
        if prediction.any():
            ax.contour(prediction, levels=[0.5], colors=["#06D6A0"], linewidths=1.2)
        ax.set_title(f"{view} {phase} · frame {index}")
        ax.axis("off")
    for ax in axes.flat[len(examples):]:
        ax.axis("off")
    legend = [Line2D([0], [0], color="#FFD166", lw=1.6, label="Expert mask"),
              Line2D([0], [0], color="#06D6A0", lw=1.6, label="Model prediction")]
    fig.legend(handles=legend, loc="lower center", bbox_to_anchor=(0.5, 0.01),
               ncol=2, frameon=False)
    fig.suptitle("LV contours on labeled test frames", y=0.98)
    fig.subplots_adjust(left=0.01, right=0.99, top=0.92, bottom=0.08,
                        wspace=0.02, hspace=0.08)
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=240, bbox_inches="tight")
    plt.close(fig)
    return output


def plot_baseline_comparison(results_root: str | Path, model_names: list[str], *,
                             output: str | Path | None = None,
                             alignment_audit=None) -> Path:
    results_root = Path(results_root)
    summaries, dice, iou = [], [], []
    for name in model_names:
        summary = json.loads((results_root / name / "evaluation" / "summary.json").read_text(
            encoding="utf-8"))
        summaries.append(summary)
        dice.append(list(summary["dice_by_patient"].values()))
        iou.append(list(summary["miou_by_patient"].values()))
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5), sharey=True, constrained_layout=True)
    palette = ["#407B9E", "#9B6BA8", "#4F8A70", "#CB8B46", "#555A68"]
    for ax, values, title in zip(axes, (dice, iou), ("Patient-level Dice", "Patient-level mIoU")):
        parts = ax.boxplot(values, patch_artist=True, showfliers=False,
                           medianprops={"color": "#202020", "linewidth": 1.5},
                           whiskerprops={"color": "#555555"}, capprops={"color": "#555555"})
        for box, color in zip(parts["boxes"], palette):
            box.set_facecolor(color)
            box.set_alpha(0.72)
        ax.set_xticks(np.arange(1, len(model_names) + 1), model_names, rotation=28, ha="right")
        ax.set_title(title)
        ax.set_ylim(0, 1.02)
        ax.grid(axis="y", color="#E6E6E6", linewidth=0.7)
        ax.spines[["right", "top"]].set_visible(False)
        ax.set_ylabel("Score" if ax is axes[0] else "")
    fig.suptitle("LV segmentation on the fixed held-out patient split")
    output = Path(output) if output else results_root / "baseline_comparison.png"
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.canvas.draw()
    audit_dir = Path(".work/lvseg_figure_qa")
    _audit_two_panel_geometry(fig, axes,
                              audit_dir / "segmentation_model_comparison.alignment.json")
    if alignment_audit:
        alignment_audit(fig, json_out=audit_dir / "segmentation_model_comparison.skill.json",
                        overlay_svg=audit_dir / "segmentation_model_comparison.alignment.svg",
                        strict=True)
    fig.savefig(output, dpi=240, bbox_inches="tight")
    qa_pdf = audit_dir / "segmentation_model_comparison.pdf"
    qa_pdf.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(qa_pdf, bbox_inches="tight")
    plt.close(fig)
    return output


def plot_volume_accuracy_comparison(results_root: str | Path,
                                    model_names: list[str],
                                    output: str | Path | None = None,
                                    alignment_audit=None) -> Path:
    """Compare patient-level absolute Simpson-volume error by view and model."""
    results_root = Path(results_root)
    palette = ["#407B9E", "#9B6BA8", "#4F8A70", "#CB8B46", "#555A68"]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.6), sharey=True,
                             constrained_layout=True)
    for ax, view in zip(axes, ("2CH", "4CH")):
        distributions = []
        for model_name in model_names:
            rows = _read_csv(results_root / model_name / "evaluation" /
                             "labeled_frame_metrics.csv")
            by_patient = {}
            for row in rows:
                if row["view"] != view or not row.get("volume") or not row.get("reference_volume"):
                    continue
                error = abs(float(row["volume"]) - float(row["reference_volume"]))
                by_patient.setdefault(row["patient_id"], []).append(error)
            distributions.append([float(np.mean(values)) for _, values in sorted(by_patient.items())])

        boxes = ax.boxplot(distributions, patch_artist=True, showfliers=False,
                           medianprops={"color": "#202020", "linewidth": 1.4},
                           whiskerprops={"color": "#555555"},
                           capprops={"color": "#555555"})
        for index, (box, values, color) in enumerate(zip(boxes["boxes"], distributions, palette), 1):
            box.set_facecolor(color)
            box.set_alpha(0.70)
            if values:
                jitter = np.linspace(-0.08, 0.08, len(values))
                ax.scatter(np.full(len(values), index) + jitter, values, s=10,
                           color=color, alpha=0.45, edgecolors="none", zorder=3)
                ax.scatter(index, np.mean(values), marker="D", s=25,
                           color="#B23A48", edgecolors="white", linewidths=0.4, zorder=4)
        ax.set_xticks(np.arange(1, len(model_names) + 1), model_names,
                      rotation=26, ha="right")
        ax.set_title(view)
        ax.set_ylabel("Patient-level mean absolute error (mL)")
        ax.grid(axis="y", color="#E6E6E6", linewidth=0.7)
        ax.spines[["right", "top"]].set_visible(False)
    fig.suptitle("Single-plane Simpson volume agreement with expert-mask estimates")
    fig.text(0.5, -0.015,
             "Dots = test patients; boxes = median and IQR; red diamond = mean. Expert-mask volumes use the same geometry method, not an independent clinical reference.",
             ha="center", fontsize=8)
    output = Path(output) if output else results_root / "volume_accuracy_comparison.png"
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.canvas.draw()
    audit_dir = Path(".work/lvseg_figure_qa")
    _audit_two_panel_geometry(fig, axes,
                              audit_dir / "volume_accuracy_comparison.alignment.json")
    if alignment_audit:
        alignment_audit(fig, json_out=audit_dir / "volume_accuracy_comparison.skill.json",
                        overlay_svg=audit_dir / "volume_accuracy_comparison.alignment.svg",
                        strict=True)
    fig.savefig(output, dpi=240, bbox_inches="tight")
    qa_pdf = audit_dir / "volume_accuracy_comparison.pdf"
    qa_pdf.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(qa_pdf, bbox_inches="tight")
    plt.close(fig)
    return output


def plot_volume_bland_altman(results_root: str | Path,
                            model_name: str | None = None) -> Path:
    evaluation = (Path(results_root) if model_name is None else
                  Path(results_root) / model_name / "evaluation")
    rows = _read_csv(evaluation / "labeled_frame_metrics.csv")
    views = sorted({row["view"] for row in rows}) or ["2CH", "4CH"]
    fig, axes = plt.subplots(1, len(views), figsize=(4.5 * len(views), 4.4),
                             constrained_layout=True, squeeze=False, sharey=False)
    for ax, view in zip(axes.flat, views):
        selected = [row for row in rows if row["view"] == view and row.get("volume")
                    and row.get("reference_volume")]
        ax.set_title(f"{view} · {len(selected)} labeled frames")
        ax.set_xlabel("Mean of predicted and expert-mask volume")
        ax.set_ylabel("Predicted minus expert-mask volume")
        if not selected:
            ax.text(0.5, 0.5, "No valid labeled-frame volume pairs",
                    transform=ax.transAxes, ha="center", va="center")
            ax.spines[["right", "top"]].set_visible(False)
            continue
        pred = np.asarray([float(row["volume"]) for row in selected])
        reference = np.asarray([float(row["reference_volume"]) for row in selected])
        mean = (pred + reference) / 2
        difference = pred - reference
        bias = float(difference.mean()) if len(difference) else 0.0
        spread = float(difference.std(ddof=1)) if len(difference) > 1 else None
        ax.scatter(mean, difference, c="#2C7DA0", s=20, alpha=0.68,
                   edgecolors="none", rasterized=True)
        ax.axhline(bias, color="#C43C39", linewidth=1.3, label=f"Bias {bias:.1f}")
        if spread is not None:
            ax.axhline(bias + 1.96 * spread, color="#666666", linestyle="--", linewidth=1,
                       label="95% limits")
            ax.axhline(bias - 1.96 * spread, color="#666666", linestyle="--", linewidth=1)
        unit = selected[0]["volume_unit"] if selected else "mL"
        ax.set_xlabel(f"Mean of predicted and expert-mask volume ({unit})")
        ax.grid(color="#EEEEEE", linewidth=0.6)
        ax.spines[["right", "top"]].set_visible(False)
        ax.legend(frameon=False, loc="best")
    axes.flat[0].set_ylabel("Predicted minus expert-mask volume")
    plot_name = model_name or evaluation.parent.name
    fig.suptitle(f"{plot_name}: labeled-frame volume agreement")
    output = evaluation / "volume_bland_altman.png"
    fig.savefig(output, dpi=240, bbox_inches="tight")
    plt.close(fig)
    return output
