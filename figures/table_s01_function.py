"""Rebuild all 21 functional scopes with complete patient availability and null reasons."""
import argparse
from collections import defaultdict
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import matplotlib
matplotlib.use('Agg')
import numpy as np
from style.palette import apply_style
from _paper_common import FROZEN, RUN, provenance, read_csv, read_json, write_csv, write_json
from _paper_tables import render_table, write_markdown
from table_02_function import statistics

STEM = 'table_s01_function'
OUT = ROOT/'figures'/STEM
AUDIT = ROOT/'reports/result_integrity/camus_cuda_progress_20261121'
GEOMETRY = 'same_geometry_from_expert_ED_ES_contours'
METRICS = ['EDV', 'ESV', 'SV', 'EF']
SPECS = [
    ('20_disks_shorter_axis', 'biplane', METRICS, GEOMETRY,
     'Expert ED/ES · biplane 20 disks, shorter axis · same-geometry expert reference'),
    ('single_plane_area_length', '2CH', METRICS, GEOMETRY,
     'Expert ED/ES · single plane, area–length · 2CH · same-geometry expert reference'),
    ('single_plane_area_length', '4CH', METRICS, GEOMETRY,
     'Expert ED/ES · single plane, area–length · 4CH · same-geometry expert reference'),
    ('single_plane_auto_extrema_2CH', '2CH', METRICS, GEOMETRY,
     'Automatic extrema · single plane, area–length · 2CH · expert ED/ES contour reference'),
    ('single_plane_auto_extrema_4CH', '4CH', METRICS, GEOMETRY,
     'Automatic extrema · single plane, area–length · 4CH · expert ED/ES contour reference'),
    ('biplane_vs_CAMUS_reported_EF', 'biplane', ['EF'], 'CAMUS_Info_cfg_EF',
     'Expert ED/ES · biplane prediction versus CAMUS clinical EF label (Info.cfg)')]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--alignment-auditor', type=Path)
    args = parser.parse_args()
    font = apply_style()
    (OUT/'source_data').mkdir(parents=True, exist_ok=True)
    split_path = ROOT/'configs/camus_splits.json'
    expected = {p for p, s in read_json(split_path)['patients'].items() if s == 'test'}
    assert len(expected) == 82
    raw = read_csv(RUN/'function.csv')
    assert len(raw) == 490 and {r['patient_id'] for r in raw} == expected
    assert all(not r['HR'] and not r['CO'] and not r['ref_CO'] for r in raw)
    lookup = {(r['method'], r['view'], r['patient_id']): r for r in raw}
    assert len(lookup) == 490
    audit = {(r['method'], r['view'], r['metric']): r for r in read_csv(AUDIT/'function_agreement.csv')}
    main_stats = {(r['method'], r['metric']): r for r in read_csv(
        ROOT/'figures/table_02_function/source_data/agreement_statistics.csv')}
    summary = read_json(RUN/'summary.json')['function']
    frame_groups = defaultdict(list)
    for row in read_csv(RUN/'frames.csv'):
        frame_groups[row['case_id']].append(row)
    pairs, excluded, availability, stats, table_rows = [], [], [], [], []
    for method, view, metrics, scope, title in SPECS:
        table_rows.append((True, [title]+['']*7))
        for patient in sorted(expected):
            row = lookup.get((method, view, patient))
            if row is None:
                assert method == 'single_plane_auto_extrema_4CH' and patient in {'patient0068', 'patient0203'}
                frames = sorted(frame_groups[patient+'_'+view], key=lambda r: int(r['frame']))
                valid = [r for r in frames if r['valid'] == 'True' and r['analysis_volume_ml']]
                maximum = max(valid, key=lambda r: float(r['analysis_volume_ml']))
                assert int(maximum['frame']) == len(frames)-1
                reason = 'Maximum at final frame; no later ES under frozen ordered-extrema rule'
            else:
                assert row['reference_scope'] == scope
                reason = row['issues']
            availability.append({'patient_id': patient, 'method': method, 'view': view,
                                 'reference_scope': scope, 'source_row_present': row is not None,
                                 'valid_metrics': ';'.join(m for m in metrics if row and row[m] and row['ref_'+m]),
                                 'prediction_EDV': float(row['EDV']) if row and row['EDV'] else None,
                                 'prediction_ESV': float(row['ESV']) if row and row['ESV'] else None,
                                 'issues': reason})
            for metric in metrics:
                if not row or not row[metric] or not row['ref_'+metric]:
                    if row:
                        assert patient == 'patient0072' and method == 'single_plane_area_length' and view == '2CH'
                        assert metric in ['SV', 'EF'] and float(row['ESV']) > float(row['EDV'])
                    excluded.append({'patient_id': patient, 'method': method, 'view': view, 'metric': metric,
                                     'prediction': None, 'reference': float(row['ref_'+metric]) if row else None,
                                     'reason': reason})
                    continue
                prediction, reference = float(row[metric]), float(row['ref_'+metric])
                assert np.isfinite([prediction, reference]).all()
                pairs.append({'patient_id': patient, 'method': method, 'view': view, 'metric': metric,
                              'reference_scope': scope, 'phase_selection': row['phase_selection'],
                              'prediction': prediction, 'reference': reference, 'difference': prediction-reference})
        for metric in metrics:
            group = [r for r in pairs if r['method'] == method and r['view'] == view and r['metric'] == metric]
            p, r = [np.array([x[k] for x in group]) for k in ['prediction', 'reference']]
            stat = statistics(p, r)
            old = audit[(method, view, metric)]
            assert old['reference_scope'] == scope
            for key in ['n', 'mae', 'rmse', 'bias', 'loa_low', 'loa_high']:
                assert np.isclose(stat[key], float(old[key]), atol=1e-10, rtol=1e-10)
            assert np.isclose(stat['pearson_r'], float(old['r']), atol=1e-10, rtol=1e-10)
            summary_key = method+'_'+view if method == 'single_plane_area_length' else method
            assert summary[summary_key][metric]['n_patients'] == len(group)
            assert np.isclose(summary[summary_key][metric]['mae'], stat['mae'])
            if (method, metric) in main_stats:
                primary = main_stats[(method, metric)]
                for key in stat:
                    assert np.isclose(stat[key], float(primary[key]), atol=1e-10, rtol=1e-10)
            unit = 'pp' if metric == 'EF' else 'mL'
            stats.append({'method': method, 'view': view, 'metric': metric, 'reference_scope': scope,
                          'phase_selection': group[0]['phase_selection'], 'error_unit': unit,
                          'attempted_patients': 82, 'unpaired_patients': 82-len(group), **stat})
            table_rows.append((False, [('LVEF' if metric == 'EF' else metric)+' ('+unit+')', str(stat['n']),
                                       f"{stat['mae']:.2f}", f"{stat['rmse']:.2f}", f"{stat['bias']:+.2f}",
                                       f"[{stat['loa_low']:.2f}, {stat['loa_high']:.2f}]",
                                       f"{stat['pearson_r']:.3f}", f"{stat['predictive_R_squared']:.3f}"]))
    assert len(stats) == 21 and len(pairs) == 1712 and len(excluded) == 10 and len(availability) == 492
    write_csv(OUT/'source_data/agreement_statistics.csv', stats)
    write_csv(OUT/'source_data/agreement_pairs.csv', pairs)
    write_csv(OUT/'source_data/unpaired_metrics.csv', excluded)
    write_csv(OUT/'source_data/patient_scope_availability.csv', availability)
    write_json(OUT/'source_data/unavailable_metrics.json', [
        {'metric': 'HR', 'value': None, 'n': 0, 'reason': 'No complete cycle or reliable reference HR'},
        {'metric': 'CO', 'value': None, 'n': 0, 'reason': 'No complete cycle/reliable reference HR or independent CO'}])
    notes = [
        'One pair per patient per row. EDV/ESV/SV errors: mL; LVEF errors: percentage points (pp).',
        'Expert contours + matching geometry are derived references, not independent clinical volume standards.',
        'Only the final block uses Info.cfg clinical EF labels. Different reference scopes must not be pooled or ranked.',
        '2CH expert-phase SV/EF: patient0072 invalid (ESV > EDV). Auto 4CH: patient0068/0203 have no ordered extrema.',
        'Bias = prediction - reference; LOA = bias +/- 1.96 sample SD. Predictive R² = 1 - SSE/SST, not squared r.',
        'Point estimates only; primary MAE confidence intervals are in Table 2. No new bootstrap or significance tests.',
        'HR/CO remain null: no complete cycle/reliable reference HR or independent CO. CAMUS half-sequences, not patch data.',
        'Proxy-axis coverage remains unvalidated; the reported agreement does not resolve that limitation.'
    ]
    headers = ['Metric\n(error unit)', 'n', 'MAE', 'RMSE', 'Bias', '95% LOA', 'Pearson\nr', 'Predictive\nR²']
    caption = """Supplementary Table 1 | Complete patient-level functional results across geometric, view, phase-selection and reference scopes.
All 21 existing method–metric groups are reported for the frozen CAMUS baseline. Each row uses one valid prediction–reference pair per patient, with its own effective n out of 82 attempted test patients. Biplane predictions use 20 disks and the shorter long axis; single-plane predictions use area–length geometry. Except for the final block, references are expert ED/ES contours processed with the matching geometry, not independent clinical volume standards. Automatic-extrema predictions remain referenced to expert ED/ES contour-derived measurements. Only the final block compares biplane EF with CAMUS Info.cfg clinical EF labels. MAE, RMSE, prediction-minus-reference bias, descriptive 95% limits of agreement (LOA), Pearson r and predictive R² are calculated from the original pairs. LOA are bias ± 1.96 times the sample standard deviation of differences, not confidence intervals or acceptance limits; predictive R² = 1 − SSE/SST is distinct from squared correlation. Negative R² values are retained. EF errors use percentage points (pp). The five primary results match Table 2, where primary MAE confidence intervals remain available; no new confidence intervals or tests were calculated. Patient0072 has null expert-phase 2CH SV/EF because ESV exceeds EDV. Automatic 4CH results omit patients0068/0203 because the final-frame maximum leaves no later ES under the frozen rule. All 492 patient–scope availability records, 1,712 valid metric pairs and 10 unpaired metric records are supplied. No rule changes, imputation or outlier removal occurred. HR/CO remain unavailable; the proxy-axis coverage limitation persists. Data are public CAMUS transthoracic half-sequences, not wearable recordings (Leclerc et al., IEEE TMI 2019, doi:10.1109/TMI.2019.2900516; CC BY-NC-SA 4.0).
"""
    dimensions = render_table(OUT, STEM, 'Supplementary Table 1 | Complete functional quantification scopes',
                              headers, [23, 8, 18, 18, 18, 36, 20, 30], table_rows, notes,
                              height_mm=170, row_height_mm=4, header_top_mm=157,
                              auditor=args.alignment_auditor)
    (OUT/'caption_en.md').write_text(caption, encoding='utf-8')
    write_markdown(OUT/(STEM+'.md'), caption, headers, table_rows, notes)
    provenance(OUT, [Path(__file__), OUT/'figure_contract.md', ROOT/'figures/_paper_tables.py',
                    ROOT/'figures/table_02_function.py', split_path, RUN/'function.csv', RUN/'summary.json',
                    RUN/'frames.csv', AUDIT/'function_agreement.csv',
                    ROOT/'figures/table_02_function/source_data/agreement_statistics.csv'],
               table='Table S1', n_scopes=6, n_metric_groups=21, attempted_patients_per_scope=82,
               n_available_source_rows=490, n_patient_scope_records=492, n_valid_metric_pairs=1712,
               n_unpaired_metric_records=10, hypothesis_tests=None, new_confidence_intervals=False,
               point_statistics_match_existing_audit=True, primary_point_statistics_match_table_2=True,
               reference_scope='Five geometry-specific contour-reference scopes and one separate clinical-label EF scope',
               predictive_R_squared='1 - SSE/SST(reference); retain negatives',
               font_path=font, **dimensions, external_alignment_auditor_used=args.alignment_auditor is not None)
    print(f'Table S1: 21 groups / 1712 pairs / 10 null records; caption {len(caption.split())} words')


if __name__ == '__main__':
    main()
