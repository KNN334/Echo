"""Rebuild patient-level quality stratification and spatial/clinical-label EF associations."""
import argparse
from collections import defaultdict
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from style.palette import (COLORS, LINEWIDTH, MARKER_SIZE, apply_style,
                           export_figure, figure_size, panel_heading)
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from _paper_common import (Canvas, FROZEN, PREPARED, RUN, alignment, provenance,
                           read_csv, read_json, write_csv)

STEM = 'fig_s04_quality_associations'
OUT = ROOT/'figures'/STEM
QUALITIES = ['Good', 'Medium', 'Poor']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--alignment-auditor', type=Path)
    args = parser.parse_args()
    font = apply_style()
    (OUT/'source_data').mkdir(parents=True, exist_ok=True)
    split_path = ROOT/'configs/camus_splits.json'
    patients = sorted(p for p, s in read_json(split_path)['patients'].items() if s == 'test')
    structures = read_csv(RUN/'structure.csv')
    functions = read_csv(RUN/'function.csv')
    old_path = FROZEN/'source_data/error_associations.csv'
    old = {r['patient_id']: r for r in read_csv(old_path)}
    ef = {r['patient_id']: r for r in functions if r['method'] == 'biplane_vs_CAMUS_reported_EF'}
    assert len(patients) == len(ef) == len(old) == 82 and len(structures) == 328
    assert set(patients) == set(ef) == set(old)
    grouped = defaultdict(list)
    for r in structures:
        assert r['distance_unit'] == 'mm' and r['distance_status'] == 'ok'
        grouped[r['patient_id']].append(r)
    rows, sources = [], [Path(__file__), OUT/'figure_contract.md', split_path,
                         RUN/'structure.csv', RUN/'function.csv', old_path]
    for patient in patients:
        group = grouped[patient]
        assert len(group) == 4 and {r['view'] for r in group} == {'2CH', '4CH'}
        grades = []
        for view in ['2CH', '4CH']:
            path = PREPARED/(patient+'_'+view+'.json')
            meta = read_json(path)
            sources.append(path)
            assert meta['split'] == 'test' and meta['sequence_type'] == 'half_sequence'
            assert {int(r['frame']) for r in group if r['view'] == view} == set(meta['phases'].values())
            grades.append(meta['config']['ImageQuality'])
            assert float(meta['config']['EF']) == float(ef[patient]['ref_EF'])
        quality = max(grades, key=QUALITIES.index)
        dice = float(np.mean([float(r['dice']) for r in group]))
        hd95 = float(np.mean([float(r['hd95']) for r in group]))
        prediction, reference = float(ef[patient]['EF']), float(ef[patient]['ref_EF'])
        error = abs(prediction-reference)
        assert quality == old[patient]['worst_view_quality']
        assert np.allclose([dice, error], [float(old[patient]['mean_dice']),
                                          float(old[patient]['reported_ef_abs_error_pp'])])
        rows.append({'patient_id': patient, 'quality_2CH': grades[0], 'quality_4CH': grades[1],
                     'worst_view_quality': quality, 'n_labeled_frames': 4, 'mean_dice': dice,
                     'mean_hd95_mm': hd95, 'predicted_biplane_EF': prediction,
                     'CAMUS_Info_cfg_EF': reference, 'clinical_label_EF_abs_difference_pp': error})
    write_csv(OUT/'source_data/patient_analysis.csv', rows)
    stats = []
    for quality in QUALITIES:
        group = [r for r in rows if r['worst_view_quality'] == quality]
        for metric in ['mean_dice', 'clinical_label_EF_abs_difference_pp']:
            values = np.array([r[metric] for r in group])
            stats.append({'worst_view_quality': quality, 'metric': metric, 'n_patients': len(group),
                          'mean': float(values.mean()), 'sample_sd': float(values.std(ddof=1)),
                          'minimum': float(values.min()), 'maximum': float(values.max())})
    assert [s['n_patients'] for s in stats[::2]] == [31, 39, 12]
    write_csv(OUT/'source_data/quality_statistics.csv', stats)
    fig = plt.figure(figsize=figure_size(height_mm=158))
    canvas = Canvas(fig)
    canvas.text(8, 152, 'Patient-level performance across recorded CAMUS image-quality strata')
    canvas.text(8, 147, 'Frozen baseline · 82 test patients · EF reference: Info.cfg clinical labels')
    axes = []
    for x, letter, metric, title in [
            (19, 'a', 'mean_dice', 'LV overlap by image quality'),
            (110, 'b', 'clinical_label_EF_abs_difference_pp', 'Clinical-label EF by image quality')]:
        panel_heading(fig, letter, title, x-11, 136)
        ax = canvas.axes(x, 92, 65, 37)
        for i, quality in enumerate(QUALITIES):
            values = np.array([r[metric] for r in rows if r['worst_view_quality'] == quality])
            offsets = np.linspace(-.13, .13, len(values))
            ax.scatter(i+offsets, values, s=MARKER_SIZE['primary']**2, color=COLORS['primary'],
                       alpha=.72, edgecolors='none')
            ax.errorbar(i+.23, values.mean(), yerr=values.std(ddof=1), marker='D',
                        color=COLORS['axis'], markerfacecolor=COLORS['background'],
                        markersize=MARKER_SIZE['reference'], linewidth=LINEWIDTH['primary'],
                        capsize=MARKER_SIZE['primary'])
        ax.set(xticks=range(3), xticklabels=['Good\nn = 31', 'Medium\nn = 39', 'Poor\nn = 12'],
               xlim=(-.35, 2.45))
        ax.tick_params(axis='x', length=0)
        ax.spines['bottom'].set_visible(False)
        if metric == 'mean_dice':
            assert all(.75 <= r[metric] <= 1 for r in rows)
            ax.set(ylim=(.75, 1), yticks=[.75, .8, .85, .9, .95, 1], ylabel='Patient mean Dice')
        else:
            assert all(0 <= r[metric] <= 40 for r in rows)
            ax.set(ylim=(0, 40), yticks=[0, 10, 20, 30, 40], ylabel='Absolute EF difference (pp)')
        axes.append(ax)
    correlations = []
    for x, letter, metric, title, xlabel in [
            (19, 'c', 'mean_dice', 'Overlap versus functional agreement', 'Patient mean Dice'),
            (110, 'd', 'mean_hd95_mm', 'Boundary versus functional agreement', 'Patient mean HD95 (mm)')]:
        values = np.array([r[metric] for r in rows])
        errors = np.array([r['clinical_label_EF_abs_difference_pp'] for r in rows])
        rvalue = float(np.corrcoef(values, errors)[0, 1])
        correlations.append({'x_metric': metric, 'y_metric': 'clinical_label_EF_abs_difference_pp',
                             'n_patients': 82, 'pearson_r': rvalue, 'hypothesis_test': 'None'})
        panel_heading(fig, letter, title, x-11, 77)
        canvas.text(x-1, 71, f'Pearson r = {rvalue:.3f} · n = 82')
        ax = canvas.axes(x, 26, 65, 37)
        ax.scatter(values, errors, color=COLORS['primary'], alpha=.72, edgecolors='none',
                   s=MARKER_SIZE['primary']**2)
        ax.set(ylim=(0, 40), yticks=[0, 10, 20, 30, 40], xlabel=xlabel,
               ylabel='Absolute EF difference (pp)')
        if metric == 'mean_dice':
            ax.set(xlim=(.75, 1), xticks=[.75, .8, .85, .9, .95, 1])
        else:
            upper = float(np.ceil(values.max()/2)*2)
            ax.set(xlim=(0, upper), xticks=np.arange(0, upper+1, 2))
        axes.append(ax)
    write_csv(OUT/'source_data/associations.csv', correlations)
    canvas.text(8, 12, 'Points: patients; diamonds/whiskers: mean ± sample SD. Quality: worse of the two recorded view grades.')
    canvas.text(8, 7, 'Observational strata; exploratory associations without fitted curves or significance tests. CAMUS, not patch data.')
    alignment(fig, OUT, STEM, axes, list('abcd'), [['a', 'b'], ['c', 'd']],
              [['a', 'c'], ['b', 'd']], args.alignment_auditor)
    export_figure(fig, OUT/STEM)
    plt.close(fig)
    caption = """Supplementary Figure 4 | Patient-level performance across CAMUS image-quality strata.
a,b, Patient mean LV Dice and absolute EF differences from CAMUS Info.cfg clinical EF labels, grouped by the worse of each patient's two recorded view-quality grades (Good, n = 31; Medium, n = 39; Poor, n = 12). Dice is averaged across both views and expert ED/ES frames before grouping. Points denote patients; diamonds and whiskers show the group mean ± patient sample standard deviation. Horizontal offsets separate points without changing measured values. Lower-quality strata have lower mean Dice, whereas EF differences do not increase monotonically across the recorded quality grades. The strata are observational, unbalanced and potentially confounded; the plot does not establish a causal effect of quality. c,d, Patient mean Dice and patient mean HD95 versus absolute clinical-label EF differences, using all 82 fixed test patients. HD95 is in original calibrated millimetres and averaged over the same four labeled frames. Pearson r describes exploratory within-cohort associations; no regression model, confidence interval, hypothesis test or multiplicity adjustment is applied. Each patient contributes one point per panel, rather than four independent frame observations. Biplane EF uses the existing 20-disk, shorter-axis calculation at expert phases. Clinical EF labels are distinct from expert-contour same-geometry references. Proxy-axis geometry remains unvalidated; this analysis does not establish external generalization or clinical substitutability. All patients and extreme values are retained, with no imputation or new training. Public transthoracic CAMUS half-sequences are not wearable recordings; HR/CO are unavailable. CAMUS: Leclerc et al., IEEE TMI (2019), doi:10.1109/TMI.2019.2900516; CC BY-NC-SA 4.0.
"""
    (OUT/'caption_en.md').write_text(caption, encoding='utf-8')
    provenance(OUT, sources, figure='Fig.S4', n_patients=82, n_labeled_frames=328,
               quality_definition='Worse of two original Info.cfg ImageQuality grades',
               quality_group_n={'Good': 31, 'Medium': 39, 'Poor': 12},
               statistical_unit='Patient; spatial metrics averaged over 2 views x 2 phases',
               variability='Patient sample SD; scatter associations have no aggregate uncertainty',
               confidence_intervals=None, hypothesis_tests=None, fitted_curve=None,
               exclusions=[], reference_scope='CAMUS_Info_cfg_EF', font_path=font,
               width_mm=183, height_mm=158,
               external_alignment_auditor_used=args.alignment_auditor is not None)
    print(f'Fig.S4: 82 patients / 6 stratum statistics / 2 associations; caption {len(caption.split())} words')


if __name__ == '__main__':
    main()
