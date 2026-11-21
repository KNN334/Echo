"""Rebuild S2: fixed half-sequence extrema, phase localization and paired EF."""
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
import numpy as np

from _paper_common import (Canvas, FROZEN, PREPARED, RUN, alignment, provenance,
                           read_csv, read_json, write_csv, write_json)

STEM = 'fig_s02_phase_selection'
OUT = ROOT/'figures'/STEM
AUDIT = ROOT/'reports/result_integrity/camus_cuda_progress_20261121'
REF = 'same_geometry_from_expert_ED_ES_contours'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--alignment-auditor', type=Path)
    args = parser.parse_args()
    font = apply_style()
    (OUT/'source_data').mkdir(parents=True, exist_ok=True)
    split_path = ROOT/'configs/camus_splits.json'
    expected = {p for p, s in read_json(split_path)['patients'].items() if s == 'test'}
    assert len(expected) == 82
    sources = [Path(__file__), OUT/'figure_contract.md', split_path, RUN/'function.csv',
               RUN/'frames.csv', RUN/'summary.json',
               FROZEN/'source_data/paired_phase_errors.csv', AUDIT/'auto_phase_checks.csv']
    function = read_csv(RUN/'function.csv')
    lookup = {(r['method'], r['view'], r['patient_id']): r for r in function}
    assert len(lookup) == len(function) == 490
    frame_groups = defaultdict(list)
    for row in read_csv(RUN/'frames.csv'):
        assert row['temporal_filtered'] == 'False'
        frame_groups[row['case_id']].append(row)
    old_pairs = {(r['patient_id'], r['view']): r
                 for r in read_csv(FROZEN/'source_data/paired_phase_errors.csv')}
    old_phases = {(r['patient_id'], r['view']): r for r in read_csv(AUDIT/'auto_phase_checks.csv')}
    assert len(old_pairs) == 161 and len(old_phases) == 162
    pairs, phase_rows, coverage, full_stats, paired_stats = [], [], [], [], []
    for view in ['2CH', '4CH']:
        expert_errors, auto_errors = [], []
        for patient in sorted(expected):
            case = patient+'_'+view
            meta_path = PREPARED/(case+'.json')
            meta = read_json(meta_path)
            sources.append(meta_path)
            assert meta['split'] == 'test' and meta['sequence_type'] == 'half_sequence'
            fps = float(meta['fps'])
            assert np.isfinite(fps) and fps > 0 and meta['source']['fps'] == 'Info.cfg:FrameRate'
            rows = sorted(frame_groups[case], key=lambda r: int(r['frame']))
            assert [int(r['frame']) for r in rows] == list(range(meta['audit']['n_frames']))
            times = np.array([float(r['time_s']) for r in rows])
            assert np.allclose(times, np.arange(len(rows))/fps, atol=1e-12, rtol=0)
            assert np.allclose(times, meta['audit']['timestamps_s'], atol=1e-12, rtol=0)
            valid = [i for i, r in enumerate(rows) if r['valid'] == 'True' and r['analysis_volume_ml']
                     and np.isfinite(float(r['analysis_volume_ml']))]
            assert len(valid) >= 2
            volumes = [float(rows[i]['analysis_volume_ml']) for i in valid]
            ed = valid[int(np.argmax(volumes))]
            later = [i for i in valid if i > ed]
            expert = lookup[('single_plane_area_length', view, patient)]
            auto = lookup.get(('single_plane_auto_extrema_'+view, view, patient))
            assert expert['reference_scope'] == REF
            if expert['EF'] and expert['ref_EF']:
                expert_errors.append(abs(float(expert['EF'])-float(expert['ref_EF'])))
            if not later:
                assert auto is None and view == '4CH' and patient in {'patient0068', 'patient0203'}
                assert ed == len(rows)-1
                coverage.append({'patient_id': patient, 'view': view, 'auto_output': False,
                                 'paired_EF': False, 'fps': fps, 'maximum_frame': ed,
                                 'reason': 'Maximum at final frame; no later valid ES under frozen rule'})
                continue
            es = min(later, key=lambda i: float(rows[i]['analysis_volume_ml']))
            assert auto is not None and auto['reference_scope'] == REF
            assert auto['phase_selection'] == 'predicted_ED_then_ES_within_available_sequence'
            assert int(auto['ed_frame']) == ed and int(auto['es_frame']) == es
            assert int(old_phases[(patient, view)]['auto_ed']) == ed
            assert int(old_phases[(patient, view)]['auto_es']) == es
            assert np.isclose(float(auto['EDV']), float(rows[ed]['analysis_volume_ml']))
            assert np.isclose(float(auto['ESV']), float(rows[es]['analysis_volume_ml']))
            for phase, selected in [('ED', ed), ('ES', es)]:
                reference_frame = int(meta['phases'][phase])
                signed_frames = selected-reference_frame
                absolute_frames = abs(signed_frames)
                assert absolute_frames == int(auto[phase.lower()+'_frame_error'])
                assert absolute_frames == int(old_phases[(patient, view)][phase.lower()+'_frame_error'])
                signed_s = float(times[selected]-times[reference_frame])
                assert np.isclose(signed_s, signed_frames/fps, atol=1e-12)
                phase_rows.append({'patient_id': patient, 'case_id': case, 'view': view, 'phase': phase,
                                   'selected_frame': selected, 'expert_frame': reference_frame,
                                   'signed_offset_frames': signed_frames, 'absolute_offset_frames': absolute_frames,
                                   'fps': fps, 'signed_offset_s': signed_s,
                                   'absolute_offset_ms': 1000*abs(signed_s)})
            assert auto['EF'] and auto['ref_EF'] and float(auto['ref_EF']) == float(expert['ref_EF'])
            auto_error = abs(float(auto['EF'])-float(auto['ref_EF']))
            auto_errors.append(auto_error)
            good = bool(expert['EF'] and expert['ref_EF'])
            coverage.append({'patient_id': patient, 'view': view, 'auto_output': True,
                             'paired_EF': good, 'fps': fps, 'maximum_frame': ed,
                             'reason': '' if good else 'Expert-phase prediction ESV > EDV; original EF null'})
            if not good:
                assert patient == 'patient0072' and view == '2CH'
                assert float(expert['ESV']) > float(expert['EDV'])
                continue
            expert_error = abs(float(expert['EF'])-float(expert['ref_EF']))
            old = old_pairs[(patient, view)]
            for key, value in [('expert_phase_abs_error_pp', expert_error),
                               ('auto_extrema_abs_error_pp', auto_error),
                               ('paired_error_change_pp', auto_error-expert_error)]:
                assert np.isclose(float(old[key]), value, atol=1e-12, rtol=0)
            pairs.append({'patient_id': patient, 'view': view,
                          'expert_phase_prediction_EF': float(expert['EF']),
                          'auto_extrema_prediction_EF': float(auto['EF']),
                          'expert_contour_same_geometry_reference_EF': float(expert['ref_EF']),
                          'expert_phase_abs_error_pp': expert_error, 'auto_extrema_abs_error_pp': auto_error,
                          'paired_error_change_pp': auto_error-expert_error})
        for condition, errors in [('expert_phase', expert_errors), ('auto_extrema', auto_errors)]:
            full_stats.append({'view': view, 'condition': condition, 'scope': 'all_valid_per_condition',
                               'n': len(errors), 'mae_pp': float(np.mean(errors)),
                               'sample_sd_absolute_error_pp': float(np.std(errors, ddof=1))})
        group = [r for r in pairs if r['view'] == view]
        a, b = [np.array([r[key] for r in group]) for key in
                ['expert_phase_abs_error_pp', 'auto_extrema_abs_error_pp']]
        paired_stats.append({'view': view, 'n_common': len(group), 'expert_phase_mae_pp': float(a.mean()),
                             'auto_extrema_mae_pp': float(b.mean()), 'paired_mean_change_pp': float((b-a).mean()),
                             'expert_phase_sample_sd_pp': float(a.std(ddof=1)),
                             'auto_extrema_sample_sd_pp': float(b.std(ddof=1))})
    assert len(pairs) == 161 and len(phase_rows) == 324 and len(coverage) == 164
    assert [r['n_common'] for r in paired_stats] == [81, 80]
    write_csv(OUT/'source_data/paired_EF.csv', pairs)
    write_csv(OUT/'source_data/paired_statistics.csv', paired_stats)
    write_csv(OUT/'source_data/all_valid_EF_statistics.csv', full_stats)
    write_csv(OUT/'source_data/phase_offsets.csv', phase_rows)
    write_csv(OUT/'source_data/sequence_coverage.csv', coverage)

    fig = plt.figure(figsize=figure_size(height_mm=158))
    canvas = Canvas(fig)
    canvas.text(8, 152, 'Expert ED/ES versus automatic extrema within observed CAMUS half-sequences')
    canvas.text(8, 147, 'EF reference: expert contours + same single-plane geometry; not an independent clinical standard')
    axes = []
    for x, letter, view, stat in zip([19, 110], ['a', 'b'], ['2CH', '4CH'], paired_stats):
        panel_heading(fig, letter, f"{view} · paired EF (n = {stat['n_common']})", x-11, 136)
        canvas.text(x-1, 130, f"MAE {stat['expert_phase_mae_pp']:.2f} → {stat['auto_extrema_mae_pp']:.2f} pp · "
                    f"Δ {stat['paired_mean_change_pp']:+.2f}")
        ax = canvas.axes(x, 90, 65, 36)
        group = [r for r in pairs if r['view'] == view]
        offsets = np.linspace(-.08, .08, len(group))
        for j, r in enumerate(group):
            ax.plot([offsets[j], 1+offsets[j]], [r['expert_phase_abs_error_pp'], r['auto_extrema_abs_error_pp']],
                    color=COLORS['muted'], alpha=.20, linewidth=LINEWIDTH['comparison'])
        for i, (key, marker) in enumerate([('expert_phase_abs_error_pp', 'o'), ('auto_extrema_abs_error_pp', '^')]):
            values = np.array([r[key] for r in group])
            assert values.min() >= 0 and values.max() <= 40
            ax.scatter(i+offsets, values, color=COLORS['primary'], marker=marker,
                       s=MARKER_SIZE['primary']**2, alpha=.75, edgecolors='none', zorder=2)
            ax.errorbar(i+.22, values.mean(), yerr=values.std(ddof=1), color=COLORS['axis'],
                        marker='D', markerfacecolor=COLORS['background'], markersize=MARKER_SIZE['reference'],
                        linewidth=LINEWIDTH['primary'], capsize=MARKER_SIZE['primary'], zorder=3)
        ax.set(xlim=(-.2, 1.4), ylim=(0, 40), yticks=[0, 10, 20, 30, 40], xticks=[0, 1],
               xticklabels=['Expert ED/ES', 'Auto extrema'], ylabel='Absolute EF difference (pp)')
        ax.spines['bottom'].set_visible(False)
        ax.tick_params(axis='x', length=0)
        axes.append(ax)
    limit = max(100, np.ceil(max(r['absolute_offset_ms'] for r in phase_rows)/100)*100)
    ecdf, phase_stats = [], []
    for x, letter, view in zip([19, 110], ['c', 'd'], ['2CH', '4CH']):
        n = sum(r['view'] == view and r['auto_output'] for r in coverage)
        panel_heading(fig, letter, f'{view} phase localization · n = {n}', x-11, 76)
        exact_counts = {p: sum(r['view'] == view and r['phase'] == p and r['absolute_offset_frames'] == 0
                               for r in phase_rows) for p in ['ED', 'ES']}
        canvas.text(x-1, 70, f"Exact ED {exact_counts['ED']}/{n} · ES {exact_counts['ES']}/{n}")
        ax = canvas.axes(x, 26, 65, 36)
        for phase, ls in [('ED', '-'), ('ES', '--')]:
            group = [r for r in phase_rows if r['view'] == view and r['phase'] == phase]
            values = np.array([r['absolute_offset_ms'] for r in group])
            xs = np.unique(np.r_[0, values, limit])
            ys = np.array([100*np.count_nonzero(values <= v)/len(values) for v in xs])
            ax.step(xs, ys, where='post', color=COLORS['primary'], linestyle=ls,
                    linewidth=LINEWIDTH['primary'], label=phase)
            ecdf.extend({'view': view, 'phase': phase, 'absolute_offset_ms': float(v),
                         'cumulative_percent': float(y), 'n': len(values)} for v, y in zip(xs, ys))
            phase_stats.append({'view': view, 'phase': phase, 'n': len(values),
                                'exact_frames_n': exact_counts[phase], 'exact_percent': 100*exact_counts[phase]/len(values),
                                'mean_absolute_offset_ms': float(values.mean()), 'median_absolute_offset_ms': float(np.median(values)),
                                'maximum_absolute_offset_ms': float(values.max()),
                                'mean_absolute_offset_frames': float(np.mean([r['absolute_offset_frames'] for r in group]))})
        ax.set(xlim=(0, limit), ylim=(0, 105), xticks=np.arange(0, limit+1, 100),
               yticks=[0, 25, 50, 75, 100], xlabel='Absolute phase offset (ms)', ylabel='Cumulative patients (%)')
        if view == '2CH':
            ax.legend(loc='lower right')
        axes.append(ax)
    canvas.text(8, 12, 'Points/links: paired patients; diamonds/whiskers: mean ± sample SD. Phase times are FPS-derived.')
    canvas.text(8, 7, 'Auto coverage: 2CH 82/82, 4CH 80/82. Unpaired: 0072 (predicted EF null), 0068/0203 (no ordered extrema).')
    write_csv(OUT/'source_data/phase_ECDF.csv', ecdf)
    write_csv(OUT/'source_data/phase_statistics.csv', phase_stats)
    alignment(fig, OUT, STEM, axes, ['a', 'b', 'c', 'd'], [['a', 'b'], ['c', 'd']],
              [['a', 'c'], ['b', 'd']], args.alignment_auditor)
    export_figure(fig, OUT/STEM)
    plt.close(fig)
    caption = """Supplementary Figure 2 | Phase localization and functional quantification within observed CAMUS half-sequences.
a,b, Paired absolute EF differences for the frozen baseline using expert ED/ES frames or its existing automatic extrema rule (2CH, n = 81; 4CH, n = 80 common valid patients). References are expert ED/ES contours processed with the same single-plane area–length geometry, not independent clinical standards or CAMUS clinical EF labels. Points represent patients, gray lines connect pairs, and diamonds/whiskers show the patient mean ± sample standard deviation; the mean absolute difference is MAE. Horizontal offsets only separate points. c,d, Empirical cumulative distributions of absolute ED/ES frame offsets converted to milliseconds using each sequence's recorded frame rate (2CH, n = 82; 4CH, n = 80). Solid/dashed curves denote ED/ES; exact frame matches are stated. Steps describe empirical distributions, not interpolated cardiac trajectories. The frozen rule selects the maximum valid predicted volume and then the minimum valid volume after it within the available sequence. All 162 existing automatic outputs were checked against the original frame series and metadata. Automatic coverage is 82/82 and 80/82 patients. Patient0072 has null expert-phase 2CH EF because predicted ESV exceeds EDV, while its automatic output remains in c. Patients0068/0203 have no automatic 4CH output because the maximum occurs at the final frame with no later ES. Complete coverage and unmatched records are supplied; no values were imputed or rules changed. No hypothesis tests, complete-cycle synthesis, HR/CO or wearable-acquisition claims are made. The proxy-axis geometry remains unvalidated. CAMUS: Leclerc et al., IEEE TMI (2019), doi:10.1109/TMI.2019.2900516; CC BY-NC-SA 4.0.
"""
    (OUT/'caption_en.md').write_text(caption, encoding='utf-8')
    provenance(OUT, sources, figure='Fig.S2', statistical_unit='patient within a single view',
               n_paired_EF={'2CH': 81, '4CH': 80}, n_localization={'2CH': 82, '4CH': 80},
               attempted_each_view=82, reference_scope=REF, new_model_or_phase_selection=False,
               phase_rule='Replay frozen maximum-valid-volume then minimum-later-valid-volume rule only',
               missing_auto_4CH=['patient0068', 'patient0203'], invalid_expert_EF_2CH=['patient0072'],
               hypothesis_tests=None, confidence_intervals=None, variability='Patient sample SD; one fixed model',
               temporal_plot='ECDF of phase offsets; no reconstruction, interpolation or smoothing of cardiac trajectories',
               font_path=font, width_mm=183, height_mm=158,
               external_alignment_auditor_used=args.alignment_auditor is not None)
    print(f'Fig.S2: 161 EF pairs, 162 auto outputs / 164 sequences; caption {len(caption.split())} words')


if __name__ == '__main__':
    main()
