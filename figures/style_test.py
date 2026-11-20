"""Build the approved Arial / Nature style test from frozen CAMUS results.

One run produces editable PDF plus 600 dpi TIFF/PNG; no training or inference.
"""
import argparse
import csv
import hashlib
import importlib.metadata
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from style.palette import (BODY_PT, CMAPS, COLORS, DPI, LINEWIDTH, MARKER_SIZE, PANEL_PT,
                           METHOD_COLORS, MM_PER_INCH, apply_style, export_figure,
                           figure_size, panel_heading)
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle
import numpy as np

OUT = ROOT / 'figures/style_test'
RUN = ROOT / 'runs/camus_cuda_progress'
PREPARED = ROOT / 'data/processed/camus'
OLD = ROOT / 'reports/result_analysis/camus_cuda_progress'


def read_csv(path):
    with path.open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_csv(name, rows):
    with (OUT / 'source_data' / name).open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--alignment-auditor', type=Path)
    args = parser.parse_args()
    font_path = apply_style()
    OUT.mkdir(exist_ok=True)
    (OUT / 'source_data').mkdir(exist_ok=True)
    selection_path = OLD / 'source_data/example_selection.csv'
    selected = next(row for row in read_csv(selection_path) if row['selection'] == 'Lowest')
    case = selected['case_id']
    meta_path = PREPARED / (case + '.json')
    cache_path = PREPARED / (case + '.npz')
    prediction_path = RUN / (case + '_pred.npz')
    meta = json.loads(meta_path.read_text(encoding='utf-8'))
    with np.load(cache_path, allow_pickle=False) as arrays:
        frames, expert = arrays['frames'], arrays['masks']
    with np.load(prediction_path, allow_pickle=False) as arrays:
        prediction = arrays['masks']
    assert frames.shape == expert.shape == prediction.shape
    curve = sorted([row for row in read_csv(RUN / 'frames.csv') if row['case_id'] == case],
                   key=lambda row: int(row['frame']))
    assert [int(row['frame']) for row in curve] == list(range(len(frames)))
    time = np.array([float(row['time_s']) for row in curve])
    volume = np.array([float(row['analysis_volume_ml']) if row['valid'] == 'True'
                       and row['analysis_volume_ml'] else np.nan for row in curve])
    assert np.all(np.diff(time) > 0)
    frow = next(row for row in read_csv(RUN / 'function.csv')
                if row['patient_id'] == meta['patient_id'] and row['view'] == meta['view']
                and row['method'] == 'single_plane_area_length')
    phase_indices = [meta['phases'][phase] for phase in ['ED', 'ES']]
    reference_volume = [float(frow[key]) for key in ['ref_EDV', 'ref_ESV']]
    image_phase = 'ES'
    image_index = meta['phases'][image_phase]
    structure = next(row for row in read_csv(RUN / 'structure.csv')
                     if row['case_id'] == case and int(row['frame']) == image_index)
    statistics_path = OLD / 'source_data/agreement_statistics.csv'
    bars = [row for row in read_csv(statistics_path)
            if row['method'] == '20_disks_shorter_axis'
            and row['reference_scope'] == 'same_geometry_from_expert_ED_ES_contours'
            and row['metric'] in ['EDV', 'ESV', 'SV']]
    bars.sort(key=lambda row: ['EDV', 'ESV', 'SV'].index(row['metric']))
    assert len(bars) == 3 and all(int(row['n']) == 82 for row in bars)
    sources = [selection_path, meta_path, cache_path, prediction_path, statistics_path,
               OLD / 'analysis_manifest.json', RUN / 'frames.csv', RUN / 'function.csv',
               RUN / 'structure.csv', ROOT / 'style/paper.mplstyle', ROOT / 'style/palette.py',
               ROOT / 'style/requirements.txt', Path(__file__).resolve()]
    frozen = json.loads((OLD / 'analysis_manifest.json').read_text(encoding='utf-8'))
    for path in sources:
        relative = path.relative_to(ROOT).as_posix()
        if relative in frozen['sources_sha256']:
            assert digest(path) == frozen['sources_sha256'][relative], relative
    write_csv('curve.csv', curve)
    write_csv('bars.csv', bars)
    fig = plt.figure(figsize=figure_size(height_mm=145))
    width_mm, height_mm = fig.get_size_inches() * MM_PER_INCH

    def axes_mm(x, y, width, height):
        return fig.add_axes([x / width_mm, y / height_mm, width / width_mm, height / height_mm])

    def text_mm(x, y, text, **kwargs):
        return fig.text(x / width_mm, y / height_mm, text, **kwargs)

    panel_heading(fig, 'a', 'Palette and perceptual scales', 8, 136)
    for index, (key, label) in enumerate([
            ('primary', 'Current'), ('regularized', 'Regularized'),
            ('comparison_reserved', 'Reserved'), ('expert_contour', 'Expert')]):
        x = 8 + index * 20
        text_mm(x, 125, label)
        fig.add_artist(Rectangle((x / width_mm, 117 / height_mm), 15 / width_mm, 4 / height_mm,
                                 transform=fig.transFigure, facecolor=COLORS[key], edgecolor='none'))
        text_mm(x, 112, COLORS[key])
    for key, label, y in [('sequential', 'cividis', 100), ('diverging', 'vik', 90)]:
        text_mm(8, y + 1, label)
        color_ax = axes_mm(27, y, 61, 3)
        color_ax.imshow(np.linspace(0, 1, 256)[None, :], aspect='auto', cmap=CMAPS[key],
                        interpolation='none')
        color_ax.set_axis_off()
    text_mm(8, 84, 'Color keys only; no probability map is implied.')

    panel_heading(fig, 'b', 'ED–ES half-sequence · n = 1', 103, 136)
    curve_ax = axes_mm(103, 86, 74, 39)
    curve_ax.plot(time, volume, color=METHOD_COLORS['camus_cuda_progress'],
                  linewidth=LINEWIDTH['primary'], label='Current method')
    curve_ax.plot(time[phase_indices], reference_volume, linestyle='none', marker='D',
                  markersize=MARKER_SIZE['reference'], color=COLORS['expert_contour'],
                  label='Expert ED/ES')
    curve_ax.set(xlabel='Time (s)', ylabel='Volume (mL)',
                 xlim=(-0.03*time[-1], 1.03*time[-1]))
    curve_ax.set_xticks(np.arange(0, time[-1] + 1e-9, 0.1))
    curve_ax.legend(loc='lower left', bbox_to_anchor=(0, 1.03), ncol=2)

    panel_heading(fig, 'c', f'LV contours · 2CH · {image_phase}', 8, 73)
    image_ax = axes_mm(8, 20, 53, 44)
    sx, sy = meta['audit']['transform']['processed_spacing_xy_mm']
    image_height, image_width = frames.shape[1:]
    x = np.arange(image_width) * sx
    y = np.arange(image_height) * sy
    extent = [-sx / 2, (image_width - 0.5) * sx, (image_height - 0.5) * sy, -sy / 2]
    image_ax.imshow(frames[image_index], cmap=CMAPS['image'], vmin=0, vmax=255,
                    extent=extent, origin='upper', interpolation='none', aspect='equal')
    image_ax.contour(x, y, expert[image_index], levels=[0.5], colors=[COLORS['expert_contour']],
                     linestyles='--', linewidths=LINEWIDTH['reference'])
    image_ax.contour(x, y, prediction[image_index], levels=[0.5], colors=[COLORS['primary']],
                     linewidths=LINEWIDTH['primary'])
    image_ax.set_xlim(extent[:2])
    image_ax.set_ylim(extent[2:])
    image_ax.set_axis_off()
    scale_y = y[-1] - 12
    image_ax.plot([10, 30], [scale_y, scale_y], color=COLORS['image_annotation'],
                  linewidth=LINEWIDTH['scale'])
    image_ax.text(20, scale_y - 4, '20 mm', ha='center', color=COLORS['image_annotation'])
    legend_ax = axes_mm(64, 46, 24, 19)
    legend_ax.set_axis_off()
    legend_ax.legend(handles=[
        Line2D([], [], color=COLORS['primary'], linewidth=LINEWIDTH['primary'], label='Prediction'),
        Line2D([], [], color=COLORS['expert_contour'], linewidth=LINEWIDTH['reference'],
               linestyle='--', label='Expert')], loc='upper left')
    text_mm(64, 43, meta['patient_id'])
    text_mm(64, 38, 'Rank 1 / 164')
    text_mm(64, 33, f"{image_phase} Dice {float(structure['dice']):.3f}")
    text_mm(64, 28, '112 × 112 cache')
    text_mm(64, 23, 'Lowest-rank case')

    panel_heading(fig, 'd', 'Biplane volume errors', 103, 73)
    text_mm(103, 66, 'n = 82 patients; 95% bootstrap CI')
    bar_ax = axes_mm(103, 21, 74, 39)
    centers = np.array([float(row['mae']) for row in bars])
    lo = np.array([float(row['mae_ci_low']) for row in bars])
    hi = np.array([float(row['mae_ci_high']) for row in bars])
    bar_ax.bar(np.arange(3), centers, width=0.55, color=COLORS['primary'])
    bar_ax.errorbar(np.arange(3), centers, yerr=[centers-lo, hi-centers],
                    fmt='none', ecolor=COLORS['clinical_label'], capsize=3,
                    elinewidth=LINEWIDTH['comparison'])
    upper_limit = np.ceil(hi.max() / 2) * 2 + 2
    bar_ax.set(xlabel='Parameter', ylabel='MAE (mL)', ylim=(0, upper_limit),
               xticks=np.arange(3), xticklabels=[row['metric'] for row in bars],
               yticks=np.arange(0, upper_limit + 1, 2))
    text_mm(8, 10, 'CAMUS public data; ED–ES half-sequence only. Not wearable acquisition.')
    text_mm(8, 5, 'Expert-contour volumes use the same geometry; not an independent clinical reference.')

    fig.canvas.draw()
    comparable_axes = [curve_ax, bar_ax]
    rects = [list(ax.get_window_extent().transformed(fig.dpi_scale_trans.inverted()).bounds)
             for ax in comparable_axes]
    for component in [0, 2, 3]:
        assert abs(rects[0][component] - rects[1][component]) * 72 <= 1.5
    measured = {'rectangles_inch': rects, 'tolerance_pt': 1.5,
                'scope': 'Quantitative b/d axes; palette card and calibrated image are not comparable plot areas.'}
    (OUT / 'style_test.plot_rectangles.json').write_text(json.dumps(measured, indent=2) + '\n', encoding='utf-8')
    if args.alignment_auditor:
        spec = importlib.util.spec_from_file_location('paper_alignment_audit', args.alignment_auditor)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.require_matplotlib_panel_alignment(
            fig, axes=comparable_axes, panel_ids=['b', 'd'], column_groups=[['b', 'd']],
            json_out=OUT / 'style_test.alignment.json', strict=True)
    export_figure(fig, OUT / 'style_test')
    plt.close(fig)
    provenance = {
        'purpose': 'style_test_not_manuscript_results_figure',
        'approved_choices': ['1A', '2A', '3A', '4A', '5A'],
        'experiment': 'camus_cuda_progress', 'new_inference_or_training': False,
        'sample_selection': selected, 'image_phase': image_phase, 'image_frame': image_index,
        'phase_selection_reason': 'ES of the fixed lowest-ranked case, to show the existing failure visibly.',
        'image_display': {'source_shape': list(frames[image_index].shape), 'vmin': 0, 'vmax': 255,
                          'interpolation': 'none', 'crop': 'none beyond stored preprocessing',
                          'gamma': 'unchanged', 'processed_spacing_xy_mm': [sx, sy],
                          'physical_aspect_preserved': True, 'scale_bar_mm': 20,
                          'roi_reviewed': meta['audit']['roi_reviewed']},
        'curve': {'n_patients': 1, 'n_frames': len(time),
                  'valid_volumes': int(np.isfinite(volume).sum()),
                  'timestamp_source': meta['audit']['timestamp_source'],
                  'reference': frow['reference_scope'], 'interpolated_or_extended': False},
        'bars': {'n_patients_each': 82, 'method': bars[0]['method'],
                 'reference': bars[0]['reference_scope'], 'interval': 'Existing patient bootstrap 95% MAE CI',
                 'bootstrap_repetitions': frozen['bootstrap']['repetitions'],
                 'bootstrap_seed': frozen['bootstrap']['seed'],
                 'new_statistics_computed': False},
        'font_path': font_path, 'body_pt': BODY_PT, 'panel_pt': PANEL_PT,
        'width_mm': width_mm, 'height_mm': height_mm, 'raster_dpi': DPI,
        'versions': {key: importlib.metadata.version(key)
                     for key in ['matplotlib', 'numpy', 'Pillow', 'cmcrameri']},
        'sources_sha256': {path.relative_to(ROOT).as_posix(): digest(path) for path in sources},
        'alignment_external_auditor_used': args.alignment_auditor is not None,
    }
    (OUT / 'provenance.json').write_text(json.dumps(provenance, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'output': str(OUT), 'selected_case': case, 'frames': len(time),
                      'bar_n': 82, 'width_mm': width_mm, 'height_mm': height_mm}, ensure_ascii=False))


if __name__ == '__main__':
    main()
