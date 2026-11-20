"""Rebuild Fig. 2: all-patient segmentation metrics and frozen ranked ED/ES examples."""
import argparse
from collections import defaultdict
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from style.palette import (COLORS, LINEWIDTH, MARKER_SIZE, apply_style, export_figure,
                           figure_size, panel_heading)
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np
from src.data.transforms import Transform
from src.metrics.segmentation import segmentation_metrics
from _paper_common import (Canvas, FROZEN, RUN, alignment, calibrated_overlay, load_case,
                           provenance, read_csv, read_json, write_csv)

OUT = ROOT/'figures/fig_02_segmentation_validation'
STEM = 'fig_02_segmentation_validation'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--alignment-auditor', type=Path)
    args = parser.parse_args()
    font = apply_style()
    OUT.mkdir(exist_ok=True)
    (OUT/'source_data').mkdir(exist_ok=True)
    structure_path = RUN/'structure.csv'
    selection_path = FROZEN/'source_data/example_selection.csv'
    rows = read_csv(structure_path)
    by_patient = defaultdict(list)
    for row in rows:
        assert row['distance_unit'] == 'mm' and row['distance_status'] == 'ok'
        by_patient[row['patient_id']].append(row)
    assert len(rows) == 328 and len(by_patient) == 82
    split_path = ROOT/'configs/camus_splits.json'
    split = read_json(split_path)['patients']
    assert set(by_patient) == {p for p, s in split.items() if s == 'test'}
    summary = []
    for patient, group in sorted(by_patient.items()):
        assert len(group) == 4 and sorted(r['view'] for r in group) == ['2CH', '2CH', '4CH', '4CH']
        assert len(set((r['view'], r['frame']) for r in group)) == 4
        summary.append({'patient_id': patient, 'n_labeled_frames': len(group),
                        **{metric: float(np.mean([float(r[metric]) for r in group]))
                           for metric in ['dice', 'assd', 'hd95']}})
    write_csv(OUT/'source_data/patient_metrics.csv', summary)
    write_csv(OUT/'source_data/frame_metrics.csv', rows)
    selection = read_csv(selection_path)
    assert [r['case_id'] for r in selection] == [
        'patient0229_2CH', 'patient0189_4CH', 'patient0327_2CH', 'patient0075_4CH']
    write_csv(OUT/'source_data/example_selection.csv', selection)
    # Verify the existing ranking, rather than selecting cases again by appearance.
    by_case = defaultdict(list)
    for row in rows:
        by_case[row['case_id']].append(float(row['dice']))
    ranking = sorted(by_case, key=lambda key: (np.mean(by_case[key]), key))
    for selected in selection:
        case = selected['case_id']
        assert ranking[int(selected['rank'])-1] == case
        assert np.isclose(float(selected['mean_dice']), np.mean(by_case[case]), atol=1e-12)

    fig = plt.figure(figsize=figure_size(height_mm=170))
    canvas = Canvas(fig)
    canvas.text(8, 165, 'Test set: 82 patients · 164 view sequences · 328 expert-labeled ED/ES frames')
    stats_axes = []
    statistical_summary = []
    specs = [('dice', 'a', 'Overlap', 'Dice', (.75, 1.0), [.75, .8, .9, 1.0]),
             ('assd', 'b', 'Surface distance', 'ASSD (mm)', (0, 5), [0, 1, 2, 3, 4, 5]),
             ('hd95', 'c', 'Boundary outliers', 'HD95 (mm)', (0, 16), [0, 4, 8, 12, 16])]
    for x, (metric, letter, title, ylabel, limits, ticks) in zip([16, 78, 140], specs):
        panel_heading(fig, letter, title, x-8, 156)
        values = np.array([r[metric] for r in summary])
        assert np.isfinite(values).all() and values.min() >= limits[0] and values.max() <= limits[1]
        mean, sd = float(values.mean()), float(values.std(ddof=1))
        precision = 3 if metric == 'dice' else 2
        canvas.text(x-1, 149, f'{mean:.{precision}f} ± {sd:.{precision}f}'+(' mm' if metric != 'dice' else ''))
        statistical_summary.append({'metric': metric, 'n_patients': len(values), 'n_frames': len(rows),
                                    'mean': mean, 'sample_sd': sd, 'minimum': float(values.min()),
                                    'median': float(np.median(values)), 'maximum': float(values.max())})
        ax = canvas.axes(x, 115, 37, 29)
        ax.boxplot([values], positions=[.8], widths=.18, whis=(0, 100), showfliers=False,
                    patch_artist=False,
                    boxprops={'color': COLORS['axis'], 'linewidth': LINEWIDTH['comparison']},
                    medianprops={'color': COLORS['axis'], 'linewidth': LINEWIDTH['primary']},
                    whiskerprops={'color': COLORS['axis'], 'linewidth': LINEWIDTH['comparison']},
                    capprops={'color': COLORS['axis'], 'linewidth': LINEWIDTH['comparison']})
        offsets = [int(digest_bytes(r['patient_id'])[:8], 16)/0xffffffff for r in summary]
        ax.scatter(1.06+.22*np.array(offsets), values, s=MARKER_SIZE['primary']**2,
                   color=COLORS['primary'], alpha=.7, edgecolors='none')
        ax.set(xlim=(.55, 1.45), ylim=limits, ylabel=ylabel, yticks=ticks, xticks=[])
        ax.spines['bottom'].set_visible(False)
        stats_axes.append(ax)
    write_csv(OUT/'source_data/distribution_summary.csv', statistical_summary)
    canvas.text(8, 108, 'Points: patient means over 2 views × 2 phases. Boxes: median/IQR; whiskers: min–max. Text: mean ± SD.')
    panel_heading(fig, 'd', 'Fixed-rank ED/ES examples', 8, 100)
    fig.legend(handles=[
        Line2D([], [], color=COLORS['primary'], linewidth=LINEWIDTH['primary'], label='Prediction'),
        Line2D([], [], color=COLORS['expert_contour'], linewidth=LINEWIDTH['reference'],
               linestyle='--', label='Expert')], loc='center right', bbox_to_anchor=(175/183, 100/170), ncol=2)
    image_axes, image_ids, images, image_metrics = [], [], [], []
    sources = [structure_path, selection_path, split_path, Path(__file__)]
    # Same 270 × 200 mm field across all eight panels; only black padding is added.
    field = (270, 200)
    for col, (x, selected) in enumerate(zip([8, 52, 96, 140], selection)):
        case = selected['case_id']
        meta, arrays, paths = load_case(case)
        sources.extend(paths)
        patient_short = meta['patient_id'].replace('patient', '')
        canvas.text(x, 91, f"{selected['selection']} · rank {selected['rank']}/164", fontweight='bold')
        canvas.text(x, 86, f'Patient {patient_short} · {meta["view"]}')
        for phase, y in [('ED', 56), ('ES', 18)]:
            ax = canvas.axes(x, y, 38, 38*field[1]/field[0])
            images.append(calibrated_overlay(ax, meta, arrays, phase, field_mm=field))
            phase_index = meta['phases'][phase]
            metric_row = next(r for r in rows if r['case_id'] == case and int(r['frame']) == phase_index)
            tr = meta['audit']['transform']
            transform = Transform(tuple(tr['original_hw']), tuple(tr['crop_xyxy']), tuple(tr['output_hw']))
            restored = transform.restore_mask(arrays['prediction'][phase_index])
            truth = arrays['original_gt'][list(arrays['original_gt_indices']).index(phase_index)]
            checked = segmentation_metrics(restored, truth, meta['audit']['spacing_xy_mm'])
            assert all(np.isclose(checked[key], float(metric_row[key]), atol=1e-10)
                       for key in ['dice', 'assd', 'hd95']), (case, phase)
            image_metrics.append({'selection': selected['selection'], 'phase': phase, **metric_row})
            canvas.text(x, y-4, f"{phase} · Dice {float(metric_row['dice']):.3f}")
            canvas.text(x, y-8, f"ASSD {float(metric_row['assd']):.2f} · HD95 {float(metric_row['hd95']):.2f} mm")
            image_axes.append(ax)
            image_ids.append(f'd{col+1}_{phase}')
    canvas.text(8, 3, 'All panels: 270 × 200 mm field; 20 mm bars. Cached images: 112 × 112. No added crop or intensity adjustment.')
    write_csv(OUT/'source_data/example_frame_metrics.csv', image_metrics)
    image_rows = [[f'd{col}_{phase}' for col in range(1, 5)] for phase in ['ED', 'ES']]
    image_columns = [[f'd{col}_ED', f'd{col}_ES'] for col in range(1, 5)]
    alignment(fig, OUT, STEM, stats_axes+image_axes, ['a', 'b', 'c']+image_ids,
              [['a', 'b', 'c']]+image_rows, image_columns, args.alignment_auditor)
    export_figure(fig, OUT/STEM)
    plt.close(fig)
    caption = """Figure 2 | Patient-level LV segmentation performance and fixed-rank qualitative examples on CAMUS.
a–c, Dice, average symmetric surface distance (ASSD) and 95th-percentile Hausdorff distance (HD95) for the frozen DeepLabV3–ResNet50 baseline. Each blue point is the arithmetic mean of four expert-labeled frames (2CH/4CH × ED/ES) for one test patient (n = 82 patients; 328 frames). Boxes show the median and interquartile range; whiskers span the minimum to maximum. Text reports the mean ± sample standard deviation across patient means. Horizontal offsets only separate points. No patients or outliers were excluded; no hypothesis tests are shown. Distances were evaluated in original image coordinates with original spatial calibration, before geometry-specific mask cleaning. d, ED and ES examples at the pre-existing lowest, first-quartile, median and third-quartile ranks of ED/ES mean Dice among 164 view sequences; these are deterministic ranked examples, not random patient samples. Blue solid and magenta dashed contours denote restored predictions and original expert annotations, respectively. The lowest-ranked case retains its ES failure (Dice = 0.443). All eight panels preserve physical aspect and share a 270 × 200 mm field with black padding, 20 mm scale bars and fixed grayscale limits. Images are the stored 112 × 112 caches; no additional crop, intensity adjustment or temporal synthesis was applied. Only ED/ES have expert contours. These are public transthoracic half-sequences, not wearable patch acquisitions. CAMUS: Leclerc et al., IEEE TMI (2019), doi:10.1109/TMI.2019.2900516; CC BY-NC-SA 4.0.
"""
    (OUT/'caption_en.md').write_text(caption, encoding='utf-8')
    provenance(OUT, sources, figure='Fig.2', archetype='image plate + quant',
               core_conclusion='The entire test-cohort distribution and frozen ranked examples expose spatial accuracy and its failure boundary.',
               panel_roles={'a': 'overlap', 'b': 'average contour distance', 'c': 'tail contour distance',
                            'd': 'fixed-rank qualitative interpretation including the lowest-case ES failure'},
               n_patients=82, n_labeled_frames=328, excluded_patients=[], excluded_frames=[],
               new_statistics='Arithmetic mean of the four existing frame metrics per patient; descriptive mean/sample SD/min/median/max only.',
               boxes='median/IQR; whiskers full observed range; no confidence interval',
               patient_dot_offsets='Deterministic hash-based horizontal display offsets only; metric values unchanged.',
               sample_selection=selection, image_display=images,
               example_image_metric_verification='All 8 displayed frames: Dice/ASSD/HD95 independently recomputed from displayed original-coordinate masks and matched to frozen CSV.',
               font_path=font, width_mm=183, height_mm=170,
               external_alignment_auditor_used=args.alignment_auditor is not None)
    print(f'Fig.2 exported to {OUT}; n=82/328; caption {len(caption.split())} words')


def digest_bytes(value):
    import hashlib
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


if __name__ == '__main__':
    main()
