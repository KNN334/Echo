"""Black-background mask plates for a fixed held-out patient."""

from __future__ import annotations

import json
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", str(Path(".work/matplotlib").resolve()))

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image


def square_panel(image, original_hw, *, mask=False, size=256):
    """Restore source aspect ratio and letterbox without cropping the field of view."""
    height, width = original_hw
    scale = size / max(height, width)
    display_hw = (max(1, round(height * scale)), max(1, round(width * scale)))
    resampling = Image.Resampling.NEAREST if mask else Image.Resampling.BILINEAR
    values = np.asarray(image, dtype=np.uint8) * (255 if mask else 1)
    resized = np.asarray(Image.fromarray(values).resize(display_hw[::-1], resampling))
    panel = np.zeros((size, size), dtype=np.uint8)
    top, left = (size - display_hw[0]) // 2, (size - display_hw[1]) // 2
    panel[top:top + display_hw[0], left:left + display_hw[1]] = resized
    return panel


def save_mask_plate(fig, output, *, require_matplotlib_panel_alignment=None):
    """Save readable previews and editable vector-text exports with layout evidence."""
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.canvas.draw()
    boxes = [ax.get_window_extent().bounds for ax in fig.axes]
    widths = [box[2] / fig.dpi * 72 for box in boxes]
    heights = [box[3] / fig.dpi * 72 for box in boxes]
    delta = max(max(widths) - min(widths), max(heights) - min(heights))
    if delta > 1.5:
        raise RuntimeError("Mask comparison panels have unequal display dimensions")
    output.with_suffix(".alignment.json").write_text(json.dumps({
        "panel_count": len(boxes), "rectangles_pixels": boxes,
        "widths_pt": widths, "heights_pt": heights,
        "tolerance_pt": 1.5, "status": "PASS",
    }, indent=2), encoding="utf-8")
    if require_matplotlib_panel_alignment:
        require_matplotlib_panel_alignment(
            fig, json_out=output.with_suffix(".layout-audit.json"), strict=True)
    with plt.rc_context({"font.family": "sans-serif", "font.sans-serif": ["DejaVu Sans"],
                         "pdf.fonttype": 42, "svg.fonttype": "none"}):
        fig.savefig(output.with_suffix(".png"), dpi=300)
        fig.savefig(output.with_suffix(".pdf"))
        svg = output.with_suffix(".svg")
        fig.savefig(svg)
        svg.write_text("\n".join(line.rstrip() for line in svg.read_text(
            encoding="utf-8").splitlines()) + "\n", encoding="utf-8", newline="\n")


def export_mask_grid(images, labels, labeled, predictions, metadata, output, *,
                     alignment_audit=None):
    """Render every cine frame and save an ED still for the expert-mask layout."""
    names = list(predictions)
    include_expert = len(names) == 6
    if len(names) not in (5, 6):
        raise ValueError("The README mask grid requires five or six models")
    phases = metadata.get("phases", {})
    snapshot = len(images) // 2
    if include_expert:
        snapshot = phases.get("ED")
        if snapshot is None or not 0 <= snapshot < len(images) or not labeled[snapshot]:
            raise ValueError("The expert-mask comparison requires an annotated ED frame")
    columns = 4 if include_expert else 3
    titles = ["B-mode input", *(["Expert mask"] if include_expert else []), *names]
    fig, axes = plt.subplots(2, columns, figsize=(7.2, 7.2 * 2 / columns + 0.8), dpi=300)
    fig.subplots_adjust(left=0.005, right=0.995, top=0.995, bottom=0.065,
                        wspace=0.012, hspace=0.012)
    artists = []
    for ax, name in zip(axes.flat, titles):
        # A black label band keeps text outside the ultrasound / mask pixels.
        artists.append(ax.imshow(np.zeros((280, 256, 3), dtype=np.uint8),
                                 interpolation="nearest"))
        ax.text(0.025, 0.025, name, transform=ax.transAxes, color="white",
                fontsize=8, ha="left", va="bottom")
        ax.set_axis_off()
    footer = fig.text(0.012, 0.022, "", fontsize=7.2, color="#333333")
    rendered = []
    phases = {int(index): phase for phase, index in phases.items()}
    for index, image in enumerate(images):
        bodies = [square_panel(image, metadata["original_hw"])]
        if include_expert:
            bodies.append(square_panel(labels[index], metadata["original_hw"], mask=True)
                          if labeled[index] else np.zeros_like(bodies[0]))
        bodies.extend(square_panel(predictions[name][index], metadata["original_hw"],
                                   mask=True) for name in names)
        for artist, body in zip(artists, bodies):
            rgb = np.repeat(body[:, :, None], 3, axis=2)
            # Expert contours appear only in the input panel on labeled frames.
            if artist is artists[0] and labeled[index]:
                ref = square_panel(labels[index], metadata["original_hw"], mask=True) > 0
                interior = ref.copy()
                interior[1:-1, 1:-1] &= (ref[:-2, 1:-1] & ref[2:, 1:-1] &
                                        ref[1:-1, :-2] & ref[1:-1, 2:])
                rgb[ref & ~interior] = (255, 190, 20)
            artist.set_data(np.pad(rgb, ((0, 24), (0, 0), (0, 0))))
        times = metadata.get("timestamps_s")
        timestamp = times[index] if times is not None else index / float(metadata["fps"])
        state = phases.get(index, "labeled") if labeled[index] else "unavailable"
        footer.set_text(f"{metadata['case_id']} | frame {index}/{len(images) - 1} | "
                        f"{timestamp:.3f} s | expert label: {state}")
        if index == snapshot:
            save_mask_plate(fig, output, require_matplotlib_panel_alignment=alignment_audit)
        fig.canvas.draw()
        # Video previews are reduced to even pixel dimensions; still images remain 300 dpi.
        video_frame = Image.fromarray(np.asarray(fig.canvas.buffer_rgba())[:, :, :3])
        rendered.append(np.asarray(video_frame.resize(
            (1008, 616 if include_expert else 784), Image.Resampling.LANCZOS)))
    plt.close(fig)
    return rendered


def plot_multiview_mask_comparison(prepared_root, test_manifest, results_root,
                                   model_names, output, *, patient_id,
                                   alignment_audit=None, extra_predictions=None):
    """Compare ED/ES separately in A4C and A2C; never pair asynchronous frames."""
    prepared_root, results_root, output = map(Path, (prepared_root, results_root, output))
    manifest = json.loads(Path(test_manifest).read_text(encoding="utf-8"))
    if manifest.get("split") != "test":
        raise ValueError("README patient examples must come from the fixed test split")
    cases = {case["view"]: case for case in manifest["cases"]
             if case["patient_id"] == patient_id}
    if not {"4CH", "2CH"}.issubset(cases):
        raise ValueError(f"Both 4CH and 2CH are required for {patient_id}")
    examples = []
    for view, label in (("4CH", "A4C (4CH)"), ("2CH", "A2C (2CH)")):
        case_id = cases[view]["case_id"]
        metadata = json.loads((prepared_root / f"{case_id}.json").read_text(encoding="utf-8"))
        with np.load(prepared_root / f"{case_id}.npz", allow_pickle=False) as arrays:
            frames = arrays["frames"]
            labeled = arrays["labeled"].astype(bool)
            references = dict(zip(arrays["original_gt_indices"], arrays["original_gt"]))
        predictions = {}
        for name in model_names:
            if extra_predictions and name in extra_predictions:
                predictions[name] = extra_predictions[name][case_id]
            else:
                path = results_root / name / "evaluation" / "predicted_masks" / f"{case_id}.npz"
                with np.load(path, allow_pickle=False) as arrays:
                    predictions[name] = arrays["masks"]
            if predictions[name].shape != (len(frames), *metadata["original_hw"]):
                raise ValueError(f"Prediction coordinates differ for {name} / {case_id}")
        for phase in ("ED", "ES"):
            index = int(metadata["phases"][phase])
            if not labeled[index] or index not in references:
                raise ValueError(f"Expert {phase} mask is unavailable for {case_id}")
            panels = [square_panel(frames[index], metadata["original_hw"]),
                      square_panel(references[index], metadata["original_hw"], mask=True)]
            panels.extend(square_panel(predictions[name][index], metadata["original_hw"],
                                       mask=True) for name in model_names)
            examples.append((label, phase, index, case_id, panels))

    columns = ["B-mode input", "Expert mask", *model_names]
    fig, axes = plt.subplots(4, len(columns), figsize=(7.2, 4.65), squeeze=False)
    fig.subplots_adjust(left=0.105, right=0.995, top=0.91, bottom=0.07,
                        wspace=0.025, hspace=0.035)
    for row, (view, phase, index, _, panels) in enumerate(examples):
        for column, panel in enumerate(panels):
            ax = axes[row, column]
            ax.imshow(panel, cmap="gray", vmin=0, vmax=255, interpolation="nearest")
            ax.set_axis_off()
            if row == 0:
                ax.set_title(columns[column], fontsize=6.2, pad=6)
        axes[row, 0].text(-0.10, 0.5, f"{view}\n{phase}\nframe {index}",
                          transform=axes[row, 0].transAxes, ha="right", va="center",
                          fontsize=6.3, linespacing=1.35)
    fig.suptitle(f"{patient_id} | Left-ventricular masks across views and models",
                 fontsize=8.5, y=0.985)
    fig.text(0.5, 0.025, "ED/ES are selected within each view; the two cines are separate acquisitions.",
             ha="center", fontsize=6.5, color="#444444")
    save_mask_plate(fig, output, require_matplotlib_panel_alignment=alignment_audit)
    plt.close(fig)

    provenance = {
        "patient_id": patient_id,
        "selection_rule": "same patient as the existing README cine; no metric-based selection",
        "model_order": model_names,
        "examples": [{"case_id": case, "view_display": view, "phase": phase,
                      "frame": index, "expert_label_available": True}
                     for view, phase, index, case, _ in examples],
        "display": "full field of view, original aspect ratio, black square letterbox; "
                   "B-mode uses prepared model inputs; nearest-neighbor binary masks; no mask cleanup",
        "source": "fixed held-out CAMUS test split; per-model representative checkpoints",
        "synchronized_views": False,
        "files": [output.name, output.with_suffix(".pdf").name,
                  output.with_suffix(".svg").name],
    }
    output.with_suffix(".json").write_text(json.dumps(provenance, indent=2), encoding="utf-8")
    return output
