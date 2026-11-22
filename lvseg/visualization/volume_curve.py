"""Render the per-frame Simpson curve and predicted cardiac phase markers."""

from __future__ import annotations

import csv
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", str(Path(".work/matplotlib").resolve()))

import matplotlib.pyplot as plt
import numpy as np


def _read_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def plot_volume_curve(results_dir: str | Path, case_id: str, output: str | Path) -> Path:
    results_dir, output = Path(results_dir), Path(output)
    rows = [row for row in _read_csv(results_dir / "all_frame_volumes.csv")
            if row["case_id"] == case_id]
    if not rows:
        raise ValueError(f"No per-frame volume rows found for case {case_id}")
    events = [row for row in _read_csv(results_dir / "phase_events.csv")
              if row["case_id"] == case_id]
    labels = [row for row in _read_csv(results_dir / "labeled_frame_metrics.csv")
              if row["case_id"] == case_id]
    x = np.asarray([float(row["time_s"]) if row["time_s"] else int(row["frame"])
                    for row in rows])
    volume = np.asarray([float(row["volume"]) if row["volume"] else np.nan for row in rows])
    time_available = all(row["time_s"] for row in rows)
    unit = rows[0]["volume_unit"]
    fig, ax = plt.subplots(figsize=(10, 5.2))
    ax.plot(x, volume, color="#146C94", linewidth=1.8, label="Per-frame predicted Simpson volume")
    if labels:
        label_x = [float(row["time_s"]) if time_available else int(row["frame"]) for row in labels]
        ref = [float(row["reference_volume"]) if row["reference_volume"] else np.nan
               for row in labels]
        ax.scatter(label_x, ref, facecolors="none", edgecolors="#555555", s=45,
                   linewidths=1.2, zorder=3, label="Expert-mask volume (labeled frames)")
    marker_style = {
        "EDV": ("EDV peak", "#C43C39", "o"),
        "ESV": ("ESV trough", "#4976A8", "s"),
        "ED": ("Reference ED frame", "#DC8D24", "^"),
        "ES": ("Reference ES frame", "#6B7F4A", "v"),
    }
    labeled_markers = set()
    for index, row in enumerate(rows):
        for phase in (row.get("detected_phase"), row.get("reference_phase")):
            if phase not in marker_style:
                continue
            label, color, marker = marker_style[phase]
            marker_x = float(row["time_s"]) if time_available else index
            marker_y = float(row["volume"]) if row["volume"] else np.nan
            scatter_options = ({"facecolors": "none", "edgecolors": color,
                                "linewidths": 1.5, "s": 72} if phase in ("ED", "ES") else
                               {"color": color, "s": 52})
            ax.scatter([marker_x], [marker_y], marker=marker, zorder=5,
                       label=label if label not in labeled_markers else None,
                       **scatter_options)
            labeled_markers.add(label)
            display_phase = {"EDV": "EDV", "ESV": "ESV", "ED": "Reference ED",
                             "ES": "Reference ES"}[phase]
            right_half = marker_x > (float(np.nanmin(x)) + float(np.nanmax(x))) / 2
            x_offset = -8 if right_half else 8
            y_offset = {"EDV": 10, "ED": 30, "ESV": 10, "ES": 30}[phase]
            ax.annotate(f"{display_phase} {marker_y:.1f} {unit}", (marker_x, marker_y),
                        xytext=(x_offset, y_offset), textcoords="offset points",
                        ha="right" if right_half else "left", color=color, fontsize=8,
                        bbox={"boxstyle": "round,pad=0.2", "facecolor": "white",
                              "edgecolor": "none", "alpha": 0.78})
    for event in events:
        if event.get("HR_bpm"):
            co_text = (f"CO = {float(event['CO_L_per_min']):.2f} L/min"
                       if event.get("CO_L_per_min") is not None else
                       f"CO proxy = {float(event['CO_proxy_per_min']):.1f} {unit}/min")
            ax.text(0.02, 0.98, f"T = {float(event['T_s']):.3f} s   "
                    f"HR = {float(event['HR_bpm']):.1f} bpm\n"
                    f"SV = {float(event['SV']):.1f} {unit}   "
                    f"EF = {float(event['EF_percent']):.1f}%   {co_text}",
                    transform=ax.transAxes, va="top", fontsize=8,
                    bbox={"boxstyle": "round,pad=0.35", "facecolor": "white", "alpha": 0.88})
    if not any(row.get("HR_bpm") for row in events):
        status_reason = events[0].get("cycle_status_reason") if events else "missing_phase_events"
        message = {
            "source_sequence_not_verified_as_complete_cycle":
                "Source sequence is not a verified full cycle; HR/CO unavailable",
            "fewer_than_two_detected_EDV_peaks":
                "Fewer than two EDV peaks detected; HR/CO unavailable",
            "timestamps_missing": "No reliable time axis; HR/CO unavailable",
        }.get(status_reason, "HR/CO unavailable: " + str(status_reason or "no valid cycle"))
        ax.text(0.02, 0.98, message,
                transform=ax.transAxes, va="top", fontsize=8,
                bbox={"boxstyle": "round,pad=0.35", "facecolor": "white", "alpha": 0.88})
    ax.set_xlabel("Time (s)" if time_available else "Frame index")
    ax.set_ylabel(f"LV volume ({unit})")
    ax.set_title(f"{rows[0]['patient_id']} · {rows[0]['view']} · {case_id}")
    ax.spines[["right", "top"]].set_visible(False)
    handles, legend_labels = ax.get_legend_handles_labels()
    fig.legend(handles, legend_labels, frameon=False, loc="lower center",
               bbox_to_anchor=(0.5, 0.01), ncol=3, fontsize=8)
    fig.subplots_adjust(left=0.11, right=0.98, top=0.87, bottom=0.24)
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=220, bbox_inches="tight", pad_inches=0.1)
    plt.close(fig)
    return output
