"""Generic publication-style analysis for CAMUS/EchoNet public baselines."""

from __future__ import annotations

import html
from collections import defaultdict
from pathlib import Path

import numpy as np

from .analysis import digest, load_bundle, number
from ..data.transforms import Transform
from ..utils.io import write_csv, write_json


BLUE = "#31688e"
ORANGE = "#d98239"
GREY = "#747b83"
GREEN = "#39977d"


def _style():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({
        "font.family": "sans-serif", "font.sans-serif": ["Arial", "DejaVu Sans"],
        "font.size": 8, "axes.titlesize": 9, "axes.labelsize": 8,
        "xtick.labelsize": 7, "ytick.labelsize": 7, "legend.fontsize": 7,
        "legend.frameon": False, "axes.spines.top": False,
        "axes.spines.right": False, "pdf.fonttype": 42, "svg.fonttype": "none",
    })
    return plt


def _export(fig, output, figures, caption):
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output.with_suffix(".png"), dpi=300, bbox_inches="tight")
    fig.savefig(output.with_suffix(".pdf"), bbox_inches="tight")
    fig.savefig(output.with_suffix(".svg"), bbox_inches="tight")
    figures.append({"stem": output.name, "caption": caption})


def _patient_means(rows, key):
    grouped = defaultdict(list)
    for row in rows:
        value = number(row.get(key))
        if np.isfinite(value):
            grouped[row["patient_id"]].append(value)
    return {pid: float(np.mean(values)) for pid, values in grouped.items()}


def _plot_training(data, plt, output, figures):
    history = data["history"]
    fig, ax = plt.subplots(figsize=(5.8, 3.3))
    epoch = [number(row.get("epoch")) for row in history]
    train = [number(row.get("train_bce")) for row in history]
    val = [number(row.get("val_bce")) for row in history]
    ax.plot(epoch, train, color=BLUE, label="Train")
    ax.plot(epoch, val, color=ORANGE, label="Validation")
    ax.set(xlabel="Epoch", ylabel="Segmentation BCE", title="Training and validation")
    ax.legend()
    ax.grid(alpha=.18)
    _export(fig, output / "01_training", figures,
            "Training and validation loss from the matched checkpoint; the test split is not used for model selection.")
    plt.close(fig)


def _plot_segmentation(data, plt, output, figures):
    metrics = [("dice", "Dice"), ("iou", "IoU"), ("assd", "ASSD"), ("hd95", "HD95")]
    distance_units = sorted({row.get("distance_unit") for row in data["structure"]
                             if row.get("distance_unit") in ("mm", "pixel")})
    fig, axes = plt.subplots(1, len(metrics), figsize=(8.4, 2.8), squeeze=False)
    for ax, (key, label) in zip(axes[0], metrics):
        if key in ("assd", "hd95"):
            groups = [list(_patient_means(
                [row for row in data["structure"] if row.get("distance_unit") == unit], key
            ).values()) for unit in distance_units]
            tick_labels = [f"{unit}; n={len(group)}" for unit, group in zip(distance_units, groups)]
            title = f"{label} ({'/'.join(distance_units) or 'unavailable'})"
        else:
            values = list(_patient_means(data["structure"], key).values())
            groups = [values] if values else []
            tick_labels = [f"n={len(values)}"] if values else []
            title = label
        groups = [group for group in groups if group]
        if groups:
            ax.boxplot(groups, patch_artist=True,
                       boxprops={"facecolor": "#d9e8ee", "edgecolor": BLUE},
                       medianprops={"color": ORANGE}, whiskerprops={"color": BLUE},
                       capprops={"color": BLUE}, flierprops={"marker": ".", "color": GREY})
            for position, values in enumerate(groups, start=1):
                ax.scatter(np.full(len(values), position), values, s=5, color=BLUE, alpha=.45)
            ax.set_xticks(range(1, len(groups) + 1), tick_labels[:len(groups)])
        else:
            ax.text(.5, .5, "Unavailable", ha="center", va="center", transform=ax.transAxes)
            ax.set_xticks([])
        ax.set_title(title)
        ax.grid(axis="y", alpha=.18)
    fig.tight_layout()
    _export(fig, output / "02_segmentation", figures,
            "Subject-level segmentation distributions. Boundary distances retain their source unit (mm or pixel) and are never pooled across calibration units.")
    plt.close(fig)


def function_pairs(rows):
    """Aggregate repeated observations within each subject/source/view."""
    grouped = defaultdict(dict)
    for row in rows:
        source = (row.get("method"), row.get("reference_scope"), row.get("view", "unknown"))
        for key, unit in (("EDV", "mL"), ("ESV", "mL"), ("SV", "mL"), ("EF", "%"), ("CO", "L/min")):
            prediction, reference = number(row.get(key)), number(row.get("ref_" + key))
            if np.isfinite(prediction) and np.isfinite(reference):
                group_key = (*source, key, unit)
                grouped[group_key].setdefault(row["patient_id"], []).append((prediction, reference))
    output = []
    for (method, scope, view, key, unit), patients in sorted(grouped.items()):
        for patient_id, values in sorted(patients.items()):
            prediction, reference = np.mean(values, axis=0)
            output.append({"patient_id": patient_id, "method": method,
                           "reference_scope": scope, "view": view,
                           "metric": key, "unit": unit,
                           "prediction": float(prediction), "reference": float(reference),
                           "difference": float(prediction - reference)})
    return output


def _plot_function_pairs(pairs, plt, output, figures):
    if pairs:
        groups = defaultdict(list)
        for row in pairs:
            key = (row["method"], row["reference_scope"], row["view"], row["metric"], row["unit"])
            groups[key].append(row)
        ordered = sorted(groups.items())
    else:
        ordered = []
    fig, axes = plt.subplots(max(1, len(ordered)), 2,
                             figsize=(7.0, max(3.0, 2.65 * len(ordered))), squeeze=False)
    for index, (identity, rows) in enumerate(ordered):
        method, scope, view, key, unit = identity
        pred = np.asarray([row["prediction"] for row in rows], float)
        ref = np.asarray([row["reference"] for row in rows], float)
        diff = pred - ref
        n = len(rows)
        title = f"{key} | {method} | {scope} | {view} | n={n}"
        ax = axes[index, 0]
        lo, hi = min(pred.min(), ref.min()), max(pred.max(), ref.max())
        margin = max((hi - lo) * .1, 1.)
        ax.scatter(ref, pred, color=BLUE, s=16, edgecolor="white", linewidth=.3)
        ax.plot([lo - margin, hi + margin], [lo - margin, hi + margin], "--", color=GREY, linewidth=.8)
        ax.set(xlabel=f"Reference ({unit})", ylabel=f"Prediction ({unit})", title=title)
        ax.grid(alpha=.18)

        ax = axes[index, 1]
        means = (pred + ref) / 2
        bias = float(np.mean(diff))
        sd = float(np.std(diff, ddof=1)) if n > 1 else np.nan
        ax.scatter(means, diff, color=BLUE, s=16, edgecolor="white", linewidth=.3)
        ax.axhline(0, color=GREY, linewidth=.7)
        ax.axhline(bias, color=ORANGE, linewidth=1.)
        if np.isfinite(sd):
            ax.axhline(bias + 1.96 * sd, color=ORANGE, linestyle="--", linewidth=.8)
            ax.axhline(bias - 1.96 * sd, color=ORANGE, linestyle="--", linewidth=.8)
        ax.set(xlabel=f"Pair mean ({unit})", ylabel=f"Prediction - reference ({unit})",
               title=f"Bland–Altman; bias {bias:.2f}" + (f"; LoA [{bias-1.96*sd:.2f}, {bias+1.96*sd:.2f}]" if np.isfinite(sd) else ""))
        ax.grid(alpha=.18)
    if not ordered:
        for ax in axes[0]:
            ax.text(.5, .5, "No paired calibrated reference", ha="center", va="center", transform=ax.transAxes)
            ax.set_axis_off()
    fig.tight_layout()
    _export(fig, output / "03_function_agreement", figures,
            "Subject-level scatter and Bland–Altman comparisons are separated by metric, method, view and reference source. Limits of agreement are descriptive and use the sample standard deviation; pixel-proxy EF is never mixed with calibrated volume measures.")
    plt.close(fig)


def _plot_evidence(data, plt, output, figures):
    rows = [(name, 100 * item.get("coverage", 0), item.get("status", "unavailable"))
            for name, item in data["summary"].get("evidence_status", {}).items()]
    rows.sort(key=lambda item: item[0])
    fig, ax = plt.subplots(figsize=(7.0, max(2.4, .38 * len(rows) + .8)))
    labels = [row[0] for row in rows]
    values = [row[1] for row in rows]
    colors = [GREEN if row[2] == "available" else ORANGE if row[2] == "partial" else GREY for row in rows]
    y = np.arange(len(rows))
    ax.barh(y, values, color=colors, height=.58)
    ax.set(yticks=y, yticklabels=labels, xlabel="Evaluated-case coverage (%)", xlim=(0, 100),
           title="Evidence coverage along the downstream pipeline")
    ax.invert_yaxis()
    for index, value in enumerate(values):
        ax.text(min(value + 1, 98), index, f"{value:.1f}%", va="center", fontsize=7)
    ax.grid(axis="x", alpha=.18)
    fig.tight_layout()
    _export(fig, output / "04_evidence_coverage", figures,
            "Coverage is reported by evidence stage. Unavailable references are not replaced with zero-valued errors.")
    plt.close(fig)


def _plot_case_morphology_curve(data, plt, output, figures):
    """Pair labeled ED/ES overlays with geometry inferred for every frame."""
    if data["prepared"] is None:
        return
    case_ids = sorted({row["case_id"] for row in data["structure"]})
    if not case_ids:
        return
    case_id = case_ids[0]
    meta = data["metadata"][case_id]
    with np.load(data["prepared"] / (case_id + ".npz"), allow_pickle=False) as archive:
        arrays = {key: archive[key] for key in archive.files}
    with np.load(data["results"] / (case_id + "_pred.npz"), allow_pickle=False) as archive:
        predicted = archive["masks"]
    frames = arrays["frames"]
    if predicted.shape != frames.shape:
        raise ValueError(f"{case_id}: predicted masks do not align with the prepared video")
    transform_record = meta["audit"]["transform"]
    transform = Transform(tuple(transform_record["original_hw"]),
                          tuple(transform_record["crop_xyxy"]),
                          tuple(transform_record["output_hw"]))
    truth = dict(zip(arrays["original_gt_indices"].tolist(), arrays["original_gt"]))
    records = sorted((row for row in data["frames"] if row["case_id"] == case_id),
                     key=lambda row: int(row["frame"]))
    use_ml = any(np.isfinite(number(row.get("volume_ml"))) for row in records)
    curve_key = "analysis_volume_ml" if use_ml else "analysis_volume_pixel3_proxy"
    curve_label = "Inferred volume (mL)" if use_ml else "Inferred pixel-volume proxy (pixel³)"
    frame_x = np.asarray([int(row["frame"]) for row in records], float)
    curve_y = np.asarray([number(row.get(curve_key)) for row in records], float)

    fig, axes = plt.subplots(1, 3, figsize=(9.0, 3.4),
                             gridspec_kw={"width_ratios": [1, 1, 1.5]})
    for ax, phase in zip(axes[:2], ("ED", "ES")):
        frame_index = int(meta["phases"][phase])
        ax.imshow(frames[frame_index], cmap="gray", vmin=0, vmax=255)
        if predicted[frame_index].any():
            ax.contour(predicted[frame_index], levels=[.5], colors=[GREEN],
                       linewidths=.9, linestyles="--")
        if frame_index in truth:
            reference = transform.image(truth[frame_index], label=True)
            if reference.any():
                ax.contour(reference, levels=[.5], colors=[ORANGE], linewidths=.85)
        ax.set_title(f"{phase}, frame {frame_index}")
        ax.set_xticks([]); ax.set_yticks([])
    axes[0].plot([], [], color=ORANGE, label="Expert trace")
    axes[0].plot([], [], color=GREEN, linestyle="--", label="Prediction")
    axes[0].legend(loc="lower left", fontsize=6)

    ax = axes[2]
    ax.plot(frame_x, curve_y, color=BLUE, linewidth=1.2)
    for phase, color in (("ED", ORANGE), ("ES", GREEN)):
        frame_index = int(meta["phases"][phase])
        if frame_index < len(curve_y) and np.isfinite(curve_y[frame_index]):
            ax.scatter([frame_index], [curve_y[frame_index]], color=color, s=24,
                       zorder=3, label=f"Traced {phase}")
    valid = np.flatnonzero(np.isfinite(curve_y))
    if len(valid) >= 2:
        auto_ed = int(valid[np.argmax(curve_y[valid])])
        after = valid[valid > auto_ed]
        if len(after):
            auto_es = int(after[np.argmin(curve_y[after])])
            ax.scatter([auto_ed, auto_es], [curve_y[auto_ed], curve_y[auto_es]],
                       marker="x", color=GREY, s=28, label="Inferred extrema")
    ax.set(xlabel="Original video frame index", ylabel=curve_label,
           title="All-frame inference")
    ax.grid(alpha=.18)
    ax.legend(fontsize=6, loc="best")
    fig.suptitle(f"Representative case: {case_id}", fontsize=9)
    fig.tight_layout()
    _export(fig, output / "05_case_morphology_and_curve", figures,
            "Case selected by first available labeled case identifier in lexical order, not by test performance. ED/ES panels compare traced frames; the geometry curve uses every inferred frame, including unlabeled frames. Pixel³ values are uncalibrated proxies, not absolute volumes.")
    plt.close(fig)


def build_public_analysis(results, training, prepared, output):
    """Build generic figures that remain valid for one-view EchoNet studies."""
    data = load_bundle(results, training, prepared)
    output = Path(output).resolve()
    forbidden = [data["results"], data["training"]]
    if data["prepared"] is not None:
        forbidden.append(data["prepared"])
    if any(output == path or output in path.parents or path in output.parents for path in forbidden):
        raise ValueError("analysis output must be separate from source results, weights and prepared data")
    output.mkdir(parents=True, exist_ok=True)
    source = output / "source_data"
    source.mkdir(exist_ok=True)
    for name in ("structure", "function", "frames"):
        write_csv(source / (name + ".csv"), data[name])
    write_csv(source / "evidence_status.csv", [
        {"stage": name, **item} for name, item in data["summary"].get("evidence_status", {}).items()
    ])
    training_csv = data["training"] / "training.csv"
    if training_csv.is_file():
        import shutil
        shutil.copyfile(training_csv, source / "training.csv")
    plt = _style()
    figures = []
    _plot_training(data, plt, output, figures)
    _plot_segmentation(data, plt, output, figures)
    paired_function_rows = function_pairs(data["function"])
    write_csv(source / "function_pairs_patient_level.csv", paired_function_rows)
    _plot_function_pairs(paired_function_rows, plt, output, figures)
    _plot_evidence(data, plt, output, figures)
    _plot_case_morphology_curve(data, plt, output, figures)
    manifest = {
        "schema_version": 1,
        "experiment": data["results"].name,
        "weights_sha256": data["summary"]["weights_sha256"],
        "figures": figures,
        "sources_sha256": data["sources"],
        "dataset_kinds": data["summary"].get("dataset_kinds", []),
        "split_units": data["summary"].get("split_units", []),
        "patient_level_statistics": data["summary"].get("split_units") == ["patient"],
        "clinical_validation": False,
    }
    write_json(output / "analysis_manifest.json", manifest)
    text = ["# Public baseline analysis", "",
            f"Dataset kinds: {', '.join(manifest['dataset_kinds']) or 'unspecified'}.",
            f"Split units: {', '.join(manifest['split_units']) or 'unspecified'}", "",
            "The figures follow the patch-inspired downstream order. Missing spatial calibration, verified full cycles, independent heart-rate references, and independent cardiac-output references remain unavailable; no zero-valued errors are imputed.", ""]
    for figure in figures:
        text += [f"## {figure['stem']}", "", f"![{figure['stem']}]({figure['stem']}.png)", "", figure["caption"], ""]
    (output / "RESULTS_ANALYSIS.md").write_text("\n".join(text), encoding="utf-8")
    html_parts = ["<!doctype html><meta charset='utf-8'><title>Public baseline analysis</title>",
                  "<style>body{font:16px system-ui;max-width:1050px;margin:32px auto;padding:0 22px;color:#203342;line-height:1.6}img{width:100%;height:auto}section{border-top:1px solid #dbe2e7;margin:36px 0;padding-top:18px}.note{background:#f2f6f8;padding:14px}</style>",
                  f"<h1>Public downstream baseline</h1><p class='note'>Dataset kinds: {html.escape(', '.join(manifest['dataset_kinds']))}. Split units: {html.escape(', '.join(manifest['split_units']))}. Missing evidence is shown as unavailable.</p>"]
    for figure in figures:
        name = html.escape(figure["stem"])
        html_parts.append(f"<section><h2>{name}</h2><img src='{name}.png' alt='{name}'><p>{html.escape(figure['caption'])}</p><a href='{name}.pdf'>PDF</a> · <a href='{name}.svg'>SVG</a></section>")
    (output / "index.html").write_text("\n".join(html_parts), encoding="utf-8")
    return {"output": str(output), "figures": len(figures), "patients": data["summary"].get("patients", 0)}
