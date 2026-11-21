"""Rebuild output availability and original half-sequence phase-order boundaries."""
import argparse
from collections import Counter, defaultdict
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from style.palette import (COLORS, LINEWIDTH, MARKER_SIZE, apply_style,
                           export_figure, figure_size, panel_heading)
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import numpy as np
from _paper_common import (Canvas, PREPARED, RUN, alignment, calibrated_overlay, load_case,
                           provenance, read_csv, read_json, write_csv, write_json)
from _lv_results_common import contour_legend

STEM = 'fig_s09_output_availability'
OUT = ROOT/'figures'/STEM
METRICS = ['EDV', 'ESV', 'SV', 'EF']
SPECS = [('20_disks_shorter_axis', 'biplane', 'Biplane · expert phases'),
         ('single_plane_area_length', '2CH', '2CH · expert phases'),
         ('single_plane_area_length', '4CH', '4CH · expert phases'),
         ('single_plane_auto_extrema_2CH', '2CH', '2CH · auto extrema'),
         ('single_plane_auto_extrema_4CH', '4CH', '4CH · auto extrema'),
         ('biplane_vs_CAMUS_reported_EF', 'biplane', 'Clinical-label EF')]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--alignment-auditor', type=Path)
    args = parser.parse_args()
    font = apply_style()
    (OUT/'source_data').mkdir(parents=True, exist_ok=True)
    split_path = ROOT/'configs/camus_splits.json'
    patients = sorted(p for p, s in read_json(split_path)['patients'].items() if s == 'test')
    raw = read_csv(RUN/'function.csv')
    functions = {(r['patient_id'], r['method'], r['view']): r for r in raw}
    assert len(raw) == len(functions) == 490 and len(patients) == 82
    assert all(not r[k] for r in raw for k in ['HR', 'CO', 'ref_CO'])
    groups = defaultdict(list)
    for r in read_csv(RUN/'frames.csv'):
        groups[r['case_id']].append(r)
    sources = [Path(__file__), OUT/'figure_contract.md', split_path, RUN/'function.csv', RUN/'frames.csv',
               ROOT/'figures/_lv_results_common.py']
    sequence_ledger = []
    for patient in patients:
        for view in ['2CH', '4CH']:
            case = patient+'_'+view
            path = PREPARED/(case+'.json')
            meta = read_json(path)
            sources.append(path)
            assert meta['split'] == 'test' and meta['sequence_type'] == 'half_sequence'
            assert int(meta['config']['ED'])-1 == meta['phases']['ED']
            assert int(meta['config']['ES'])-1 == meta['phases']['ES']
            seq = sorted(groups[case], key=lambda r: int(r['frame']))
            assert [int(r['frame']) for r in seq] == list(range(meta['audit']['n_frames']))
            assert np.allclose([float(r['time_s']) for r in seq], meta['audit']['timestamps_s'])
            valid = [r for r in seq if r['valid'] == 'True' and r['analysis_volume_ml']]
            maximum = max(valid, key=lambda r: float(r['analysis_volume_ml']))
            later = [r for r in valid if int(r['frame']) > int(maximum['frame'])]
            auto = functions.get((patient, 'single_plane_auto_extrema_'+view, view))
            assert (auto is not None) == bool(later)
            if auto:
                minimum = min(later, key=lambda r: float(r['analysis_volume_ml']))
                assert int(auto['ed_frame']) == int(maximum['frame'])
                assert int(auto['es_frame']) == int(minimum['frame'])
            else:
                assert case in ['patient0068_4CH', 'patient0203_4CH']
                assert int(maximum['frame']) == len(seq)-1 == meta['phases']['ED']
            sequence_ledger.append({'case_id': case, 'patient_id': patient, 'view': view, 'n_frames': len(seq),
                                    'expert_ED_frame': meta['phases']['ED'], 'expert_ES_frame': meta['phases']['ES'],
                                    'stored_phase_order': 'ED_to_ES' if meta['phases']['ED'] < meta['phases']['ES'] else 'ES_to_ED',
                                    'automatic_output_available': auto is not None,
                                    'automatic_ED_frame': int(auto['ed_frame']) if auto else None,
                                    'automatic_ES_frame': int(auto['es_frame']) if auto else None,
                                    'maximum_volume_frame': int(maximum['frame']),
                                    'missing_reason': '' if auto else 'Maximum at final expert ED; no subsequent frame under frozen rule'})
    reverse = [r for r in sequence_ledger if r['stored_phase_order'] == 'ES_to_ED']
    assert {r['case_id'] for r in reverse} == {'patient0068_4CH', 'patient0203_4CH', 'patient0217_2CH'}
    assert sum(r['automatic_output_available'] for r in sequence_ledger) == 162
    write_csv(OUT/'source_data/sequence_ledger.csv', sequence_ledger)
    write_csv(OUT/'source_data/reverse_phase_sequences.csv', reverse)
    table_path = ROOT/'figures/table_s01_function/source_data/patient_scope_availability.csv'
    previous_availability = read_csv(table_path)
    sources.append(table_path)
    availability, cells, unpaired = [], [], []
    for method, view, label in SPECS:
        metrics = ['EF'] if method == 'biplane_vs_CAMUS_reported_EF' else METRICS
        for patient in patients:
            r = functions.get((patient, method, view))
            valid_metrics = [m for m in metrics if r is not None and r[m] and r['ref_'+m]]
            old = next(v for v in previous_availability if (v['patient_id'], v['method'], v['view']) == (patient, method, view))
            assert old['valid_metrics'] == ';'.join(valid_metrics)
            availability.append({'patient_id': patient, 'method': method, 'view': view,
                                 'reference_scope': r['reference_scope'] if r else 'same_geometry_from_expert_ED_ES_contours',
                                 'source_row_present': r is not None, 'valid_metrics': ';'.join(valid_metrics),
                                 'reason': r['issues'] if r else 'Stored ES_to_ED; maximum at final ED, no later ES under frozen rule'})
            for metric in metrics:
                if metric not in valid_metrics:
                    if r:
                        assert patient == 'patient0072' and view == '2CH' and metric in ['SV', 'EF']
                        assert float(r['ESV']) > float(r['EDV'])
                    unpaired.append({'patient_id': patient, 'method': method, 'view': view, 'metric': metric,
                                     'value': None, 'reason': availability[-1]['reason']})
        for metric in METRICS:
            applicable = metric in metrics
            valid_n = sum(metric in a['valid_metrics'].split(';') for a in availability if a['method'] == method and a['view'] == view) if applicable else None
            cells.append({'method': method, 'view': view, 'display_scope': label, 'metric': metric,
                          'applicable': applicable, 'valid_patients': valid_n,
                          'attempted_patients': 82 if applicable else None})
    assert len(availability) == 492 and len(cells) == 24 and len(unpaired) == 10
    assert sum(c['valid_patients'] for c in cells if c['applicable']) == 1712
    write_csv(OUT/'source_data/patient_scope_availability.csv', availability)
    write_csv(OUT/'source_data/availability_cells.csv', cells)
    write_csv(OUT/'source_data/unpaired_metrics.csv', unpaired)
    write_json(OUT/'source_data/unavailable_metrics.json', [
        {'metric': 'HR', 'value': None, 'reason': 'No complete cycle or reliable independent reference HR'},
        {'metric': 'CO', 'value': None, 'reason': 'No complete cycle/reliable HR and no independent CO'}])
    fig = plt.figure(figsize=figure_size(height_mm=170))
    canvas = Canvas(fig)
    canvas.text(8, 164, 'Functional output availability and original phase-order boundaries')
    fig.legend(handles=contour_legend(), loc='upper center', bbox_to_anchor=(.5, .947), ncol=2)
    panel_heading(fig, 'a', 'Reference-paired patients / 82', 8, 151)
    a = canvas.axes(43, 103, 41, 37)
    for row, (_, _, label) in enumerate(SPECS):
        for col, metric in enumerate(METRICS):
            item = cells[row*4+col]
            a.add_patch(Rectangle((col-.48, row-.43), .96, .86,
                                  facecolor=COLORS['primary'] if item['applicable'] else COLORS['muted'],
                                  alpha=.09 if item['applicable'] else .04, edgecolor='none'))
            a.text(col, row, str(item['valid_patients'])+'/82' if item['applicable'] else '—',
                   ha='center', va='center', color=COLORS['text'])
    a.set(xlim=(-.5, 3.5), ylim=(5.5, -.5), xticks=range(4), xticklabels=['EDV', 'ESV', 'SV', 'LVEF'],
           yticks=range(6), yticklabels=[s[2] for s in SPECS])
    a.xaxis.tick_top()
    a.tick_params(length=0)
    for spine in a.spines.values():
        spine.set_visible(False)
    frame_exports = []
    panel_heading(fig, 'b', 'Actual trajectory · patient 0072 · 2CH', 99, 151)
    primary = functions[('patient0072', 'single_plane_area_length', '2CH')]
    canvas.text(109, 145, f"EDV {float(primary['EDV']):.2f}; ESV {float(primary['ESV']):.2f} mL → SV/EF null")
    b = canvas.axes(110, 103, 65, 37)
    for ax, case, ls in [(b, 'patient0072_2CH', '-')]:
        seq = sorted(groups[case], key=lambda r: int(r['frame']))
        meta = read_json(PREPARED/(case+'.json'))
        t = np.array([float(r['time_s']) for r in seq])
        v = np.array([float(r['analysis_volume_ml']) for r in seq])
        assert np.isclose(v[meta['phases']['ED']], float(primary['EDV']))
        assert np.isclose(v[meta['phases']['ES']], float(primary['ESV']))
        ax.plot(t, v, color=COLORS['primary'], linestyle=ls, linewidth=LINEWIDTH['primary'])
        for phase, marker in [('ED', 'o'), ('ES', '^')]:
            i = meta['phases'][phase]
            ax.scatter(t[i], v[i], marker=marker, s=MARKER_SIZE['reference']**2,
                       color=COLORS['primary'], label='Expert '+phase)
        frame_exports.extend({'case_id': case, 'frame': int(r['frame']), 'time_s': float(r['time_s']),
                              'volume_ml': float(r['analysis_volume_ml']),
                              'expert_phase': next((p for p, i in meta['phases'].items() if i == int(r['frame'])), '')} for r in seq)
    b.legend(loc='upper right')
    panel_heading(fig, 'c', 'Actual expert ED/ES endpoints · 0072', 8, 75)
    meta, arrays, image_sources = load_case('patient0072_2CH')
    sources.extend(image_sources)
    images, display = [], []
    for x, phase in [(10, 'ED'), (48, 'ES')]:
        canvas.text(x, 68, f"2CH · {phase} · f{meta['phases'][phase]}")
        image_ax = canvas.axes(x, 32, 35, 35*220/240)
        record = calibrated_overlay(image_ax, meta, arrays, phase, field_mm=(240, 220), scale=False)
        right, bottom = image_ax.get_xlim()[1], image_ax.get_ylim()[0]
        image_ax.plot([right-50, right-30], [bottom-8, bottom-8],
                       color=COLORS['image_annotation'], linewidth=LINEWIDTH['scale'])
        record['scale_bar_mm'] = 20
        display.append(record)
        images.append(image_ax)
    canvas.text(10, 26, 'Scale bars: 20 mm · contour-derived geometry')
    panel_heading(fig, 'd', 'No subsequent frame after ED maximum', 99, 75)
    canvas.text(109, 69, 'Both missing auto4CH outputs · stored ES→ED')
    d = canvas.axes(110, 25, 65, 37)
    for case, linestyle in [('patient0068_4CH', '-'), ('patient0203_4CH', '--')]:
        seq = sorted(groups[case], key=lambda r: int(r['frame']))
        meta_case = read_json(PREPARED/(case+'.json'))
        t = np.array([float(r['time_s']) for r in seq])
        v = np.array([float(r['analysis_volume_ml']) for r in seq])
        assert meta_case['phases']['ED'] == len(seq)-1 and meta_case['phases']['ES'] == 0
        assert np.argmax(v) == len(seq)-1
        d.plot(t, v, color=COLORS['primary'], linestyle=linestyle, linewidth=LINEWIDTH['primary'],
               label=case[7:11]+' · ES→ED')
        d.scatter(t[-1], v[-1], color=COLORS['primary'], marker='o', s=MARKER_SIZE['reference']**2)
        frame_exports.extend({'case_id': case, 'frame': int(r['frame']), 'time_s': float(r['time_s']),
                              'volume_ml': float(r['analysis_volume_ml']),
                              'expert_phase': next((p for p, i in meta_case['phases'].items() if i == int(r['frame'])), '')} for r in seq)
    d.legend(loc='upper left')
    for ax in [b, d]:
        ax.set(xlim=(0, .7), ylim=(0, 160), xticks=[0, .2, .4, .6], yticks=[0, 40, 80, 120, 160],
               xlabel='Observed time (s; FPS-derived)', ylabel='Single-plane volume (mL)')
    assert len(frame_exports) == 81
    write_csv(OUT/'source_data/example_trajectories.csv', frame_exports)
    write_json(OUT/'source_data/image_display.json', display)
    canvas.text(8, 12, 'a: availability within each scope, not clinical validity. — = not applicable; missing values are never zero-filled.')
    canvas.text(8, 7, 'Three ES→ED sequences retained; 0217_2CH still has auto output. Numeric availability is not correct phase localization.')
    alignment(fig, OUT, STEM, [a, b, *images, d], ['a', 'b', 'c1', 'c2', 'd'],
              [['c1', 'c2']], [['b', 'd']], args.alignment_auditor)
    export_figure(fig, OUT/STEM)
    plt.close(fig)
    caption = """Supplementary Figure 9 | Functional output availability and original phase-order boundaries.
a, Valid prediction–reference pairs out of 82 attempted test patients in each scope. The first five rows use corresponding expert-contour geometric references; only the final row uses CAMUS Info.cfg clinical EF labels. Dashes denote non-applicable cells, not missing measurements or zero values. These counts match the 21 groups in Supplementary Table1. Availability does not establish clinical validity. b, All 14 observed frames of patient0072_2CH; expert-phase predicted ESV exceeds EDV, so the original SV/EF remain null. Markers identify expert ED/ES frame positions on the prediction curve, not independent reference volumes. c, Actual ED/ES frames from this patient, with predicted and expert contours. The 112 × 112 cache images retain the same 0–255 gray window, physical aspect and padded 240 × 220 mm field without further cropping. Scale bars, 20 mm. d, All observed frames of both missing automatic4CH outputs, patient0068 (36 frames) and patient0203 (31 frames). Both are stored ES→ED, with the maximum at the final expert ED; the existing maximum-then-later-minimum rule has no subsequent frame. No sequence was reversed or rule changed. A third ES→ED sequence, patient0217_2CH, still has an automatic numeric output; its phase positions are supplied in the complete ledger. Numeric output is not evidence of correct phase localization. All 492 patient–scope records, 164 sequence records and ten unavailable metric records are supplied. Times are FPS-derived. No interpolation, cycle synthesis, HR/CO or patch-recording claims are made. Contour-derived geometry remains unvalidated and is not an independent clinical volume standard. CAMUS: Leclerc et al., IEEE TMI (2019), doi:10.1109/TMI.2019.2900516; CC BY-NC-SA 4.0.
"""
    (OUT/'caption_en.md').write_text(caption, encoding='utf-8')
    provenance(OUT, sources, figure='Fig.S9', n_patients=82, n_patient_scopes=492,
               n_applicable_metric_groups=21, n_valid_metric_pairs=1712, n_unpaired_metric_records=10,
               n_sequence_records=164, n_auto_outputs=162, reverse_phase_sequences=reverse,
               n_example_frames=81, image_display=display, statistical_unit='Patient within each scope',
               confidence_intervals=None, hypothesis_tests=None, exclusions=[], rules_changed=False,
               phase_order_changed=False, font_path=font, width_mm=183, height_mm=170,
               alignment_groups={'rows': [['c1', 'c2']], 'columns': [['b', 'd']],
                                 'matrix_a': 'Measured; matrix aspect not comparable to time-series axes'},
               external_alignment_auditor_used=args.alignment_auditor is not None)
    print(f'Fig.S9: 21 availability groups / 164 sequence ledger / 81 example frames; caption {len(caption.split())} words')


if __name__ == '__main__':
    main()
