"""Rebuild observed half-sequence variation without reordering or filling cardiac cycles."""
import argparse
from collections import Counter, defaultdict
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from style.palette import (CMAPS, COLORS, LINEWIDTH, MARKER_SIZE, apply_style,
                           export_figure, figure_size, panel_heading, symmetric_error_norm)
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from _paper_common import (Canvas, PREPARED, RUN, alignment, provenance, read_csv,
                           read_json, write_csv, write_json)
from _lv_results_common import (contour_legend, geometry_case, observed_overlay,
                                source_dependencies)

STEM = 'fig_s08_observed_temporal_variation'
OUT = ROOT/'figures'/STEM
AUDIT = ROOT/'reports/result_integrity/camus_cuda_progress_20261121'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--alignment-auditor', type=Path)
    args = parser.parse_args()
    font = apply_style()
    (OUT/'source_data').mkdir(parents=True, exist_ok=True)
    split_path = ROOT/'configs/camus_splits.json'
    patients = sorted(p for p, s in read_json(split_path)['patients'].items() if s == 'test')
    grouped = defaultdict(list)
    for r in read_csv(RUN/'frames.csv'):
        assert r['temporal_filtered'] == 'False'
        grouped[r['case_id']].append(r)
    old_path = AUDIT/'curve_quality.csv'
    old = {r['case_id']: r for r in read_csv(old_path)}
    sources = [Path(__file__), OUT/'figure_contract.md', split_path, RUN/'frames.csv', old_path,
               *source_dependencies()]
    frames, adjacent, sequences = [], [], []
    for patient in patients:
        for view in ['2CH', '4CH']:
            case = patient+'_'+view
            seq = sorted(grouped[case], key=lambda r: int(r['frame']))
            path = PREPARED/(case+'.json')
            meta = read_json(path)
            sources.append(path)
            assert meta['split'] == 'test' and meta['sequence_type'] == 'half_sequence'
            assert [int(r['frame']) for r in seq] == list(range(meta['audit']['n_frames']))
            assert {int(meta['config'][p])-1 for p in ['ED', 'ES']} == set(meta['phases'].values())
            order = 'ED_to_ES' if meta['phases']['ED'] < meta['phases']['ES'] else 'ES_to_ED'
            t = np.array([float(r['time_s']) for r in seq])
            assert np.allclose(t, meta['audit']['timestamps_s']) and np.allclose(t, np.arange(len(t))/meta['fps'])
            assert all(r['valid'] == 'True' for r in seq), 'Record invalid observations before defining adjacent pairs'
            area, length, volume = [np.array([float(r[k]) for r in seq])
                                    for k in ['area_mm2', 'long_axis_mm', 'analysis_volume_ml']]
            assert np.isfinite([area, length, volume]).all() and min(area.min(), length.min(), volume.min()) > 0
            assert np.allclose(volume, 8*area**2/(3*np.pi*length)/1000, rtol=1e-12)
            assert all(np.isclose(float(r['volume_ml']), float(r['analysis_volume_ml'])) for r in seq)
            for i, r in enumerate(seq):
                frames.append({'case_id': case, 'patient_id': patient, 'view': view, 'frame': i,
                               'time_s': float(t[i]), 'stored_phase_order': order,
                               'expert_phase': next((p for p, j in meta['phases'].items() if j == i), ''),
                               'area_mm2': float(area[i]), 'proxy_axis_mm': float(length[i]),
                               'volume_ml': float(volume[i]), 'valid': True})
            delta_a, delta_l, delta_v = [100*np.diff(v)/v[:-1] for v in [area, length, volume]]
            assert np.allclose(1+delta_v/100, (1+delta_a/100)**2/(1+delta_l/100), rtol=1e-12)
            for i in range(len(seq)-1):
                adjacent.append({'case_id': case, 'patient_id': patient, 'view': view,
                                 'stored_phase_order': order, 'previous_frame': i, 'next_frame': i+1,
                                 'previous_time_s': float(t[i]), 'next_time_s': float(t[i+1]),
                                 'dt_ms': float(1000*(t[i+1]-t[i])), 'area_change_percent': float(delta_a[i]),
                                 'proxy_axis_change_percent': float(delta_l[i]),
                                 'volume_change_percent': float(delta_v[i]),
                                 'absolute_volume_change_percent': float(abs(delta_v[i]))})
            peak = float(np.max(abs(delta_v)))
            assert np.isclose(peak/100, float(old[case]['max_adjacent_relative_volume_change']))
            assert int(old[case]['invalid_frames']) == 0
            sequences.append({'case_id': case, 'patient_id': patient, 'view': view,
                              'n_frames': len(seq), 'n_adjacent_pairs': len(seq)-1,
                              'stored_phase_order': order, 'expert_ED_frame': meta['phases']['ED'],
                              'expert_ES_frame': meta['phases']['ES'], 'fps': meta['fps'],
                              'duration_s': float(t[-1]-t[0]), 'invalid_frames': 0,
                              'max_absolute_adjacent_volume_change_percent': peak})
    assert len(patients) == 82 and len(sequences) == 164 and len(frames) == 3167 and len(adjacent) == 3003
    assert Counter(r['stored_phase_order'] for r in sequences) == {'ED_to_ES': 161, 'ES_to_ED': 3}
    write_csv(OUT/'source_data/all_observed_frames.csv', frames)
    write_csv(OUT/'source_data/adjacent_changes.csv', adjacent)
    write_csv(OUT/'source_data/sequence_summary.csv', sequences)
    stats = []
    fig = plt.figure(figsize=figure_size(height_mm=170))
    canvas = Canvas(fig)
    canvas.text(8, 164, 'Observed frame-wise geometry within all 164 CAMUS half-sequences')
    fig.legend(handles=contour_legend(), loc='upper center', bbox_to_anchor=(.5, .947), ncol=2)
    panel_heading(fig, 'a', 'Largest adjacent volume change', 8, 151)
    canvas.text(18, 145, '82 paired patients · one value per view')
    a = canvas.axes(19, 103, 65, 37)
    values = {}
    for view in ['2CH', '4CH']:
        group = sorted([r for r in sequences if r['view'] == view], key=lambda r: r['patient_id'])
        values[view] = np.array([r['max_absolute_adjacent_volume_change_percent'] for r in group])
        v = values[view]
        stats.append({'view': view, 'n_patients': 82, 'mean_percent': float(v.mean()),
                      'sample_sd_percent': float(v.std(ddof=1)), 'median_percent': float(np.median(v)),
                      'minimum_percent': float(v.min()), 'maximum_percent': float(v.max())})
    offsets = np.linspace(-.08, .08, 82)
    for i in range(82):
        a.plot([offsets[i], 1+offsets[i]], [values['2CH'][i], values['4CH'][i]],
               color=COLORS['muted'], alpha=.18, linewidth=LINEWIDTH['comparison'])
    for xpos, view, marker in [(0, '2CH', 'o'), (1, '4CH', '^')]:
        v = values[view]
        assert v.max() < 70
        a.scatter(xpos+offsets, v, color=COLORS['primary'], marker=marker,
                  s=MARKER_SIZE['primary']**2, alpha=.7, edgecolors='none', zorder=2)
        a.errorbar(xpos+.22, v.mean(), yerr=v.std(ddof=1), color=COLORS['axis'], marker='D',
                   markerfacecolor=COLORS['background'], markersize=MARKER_SIZE['reference'],
                   linewidth=LINEWIDTH['primary'], capsize=MARKER_SIZE['primary'], zorder=3)
    a.set(xlim=(-.2, 1.4), ylim=(0, 70), yticks=[0, 20, 40, 60], xticks=[0, 1],
           xticklabels=['2CH', '4CH'], ylabel='Maximum |ΔV / previous V| (%)')
    a.spines['bottom'].set_visible(False)
    a.tick_params(axis='x', length=0)
    write_csv(OUT/'source_data/maximum_change_statistics.csv', stats)
    panel_heading(fig, 'b', 'Adjacent area / proxy-axis changes', 99, 151)
    canvas.text(109, 145, '3,003 observed pairs · repeated within patients')
    b = canvas.axes(110, 103, 65, 37)
    da, dl, dv = [np.array([r[k] for r in adjacent]) for k in
                  ['area_change_percent', 'proxy_axis_change_percent', 'volume_change_percent']]
    assert min(da) > -25 and max(da) < 25 and min(dl) > -40 and max(dl) < 60 and max(abs(dv)) < 70
    points = b.scatter(da, dl, c=dv, cmap=CMAPS['diverging'], norm=symmetric_error_norm(70),
                       s=MARKER_SIZE['primary']**2/2, alpha=.65, edgecolors='none')
    b.set(xlim=(-25, 25), ylim=(-40, 60), xticks=[-20, 0, 20], yticks=[-40, 0, 40, 60],
           xlabel='Area change (%)', ylabel='Proxy-axis change (%)')
    color_ax = canvas.axes(117, 89, 51, 2)
    cb = fig.colorbar(points, cax=color_ax, orientation='horizontal', ticks=[-60, 0, 60])
    cb.solids.set_rasterized(False)
    cb.outline.set_visible(False)
    cb.set_label('Volume change (%)', labelpad=4)
    case = 'patient0329_2CH'
    meta, arrays, features, times, case_sources = geometry_case(case, verify_all=True)
    sources.extend(case_sources)
    selected = [r for r in frames if r['case_id'] == case]
    assert len(selected) == 20 and meta['phases'] == {'ED': 0, 'ES': 19}
    step = next(r for r in adjacent if r['case_id'] == case and r['previous_frame'] == 18)
    write_csv(OUT/'source_data/example_frames.csv', selected)
    write_json(OUT/'source_data/example_step.json', step)
    panel_heading(fig, 'c', 'Actual trajectory · patient 0329 · 2CH', 8, 74)
    canvas.text(18, 68, f"f18→19: ΔV {step['volume_change_percent']:+.1f}%; Δaxis {step['proxy_axis_change_percent']:+.1f}%")
    c = canvas.axes(19, 24, 65, 37)
    volumes = np.array([r['volume_ml'] for r in selected])
    c.plot(times, volumes, color=COLORS['primary'], linewidth=LINEWIDTH['primary'])
    c.scatter(times[[18, 19]], volumes[[18, 19]], color=COLORS['primary'], s=MARKER_SIZE['reference']**2)
    c.set(xlim=(0, .4), ylim=(0, 110), xticks=[0, .1, .2, .3, .4], yticks=[0, 25, 50, 75, 100],
           xlabel='Observed time (s; FPS-derived)', ylabel='Single-plane volume (mL)')
    panel_heading(fig, 'd', 'Actual frames and per-frame proxy axes', 99, 74)
    images, display = [], []
    scale = np.asarray(meta['audit']['spacing_xy_mm'])
    for x, frame in [(108, 18), (145, 19)]:
        canvas.text(x, 66, f'f{frame} · {times[frame]:.3f} s')
        ax = canvas.axes(x, 33, 32, 32*170/200)
        record = observed_overlay(ax, meta, arrays, frame, scale=False)
        points = features[str(frame)]['landmarks_xy']
        apex = np.asarray(points['apex'])*scale
        base = (np.asarray(points['base_left'])+np.asarray(points['base_right']))*scale/2
        ax.plot([apex[0], base[0]], [apex[1], base[1]], color=COLORS['image_annotation'],
                 linewidth=LINEWIDTH['primary'])
        right, bottom = ax.get_xlim()[1], ax.get_ylim()[0]
        ax.plot([right-50, right-30], [bottom-8, bottom-8], color=COLORS['image_annotation'],
                 linewidth=LINEWIDTH['scale'])
        record.update({'scale_bar_mm': 20, 'proxy_axis_apex_mm': apex.tolist(),
                       'proxy_axis_base_mm': base.tolist(), 'axis_reference': 'Independently inferred per frame; unvalidated'})
        display.append(record)
        images.append(ax)
        canvas.text(x, 29, 'Intermediate' if frame == 18 else 'ES · expert contour')
    canvas.text(108, 23, 'White: proxy axis. Both scale bars: 20 mm')
    write_json(OUT/'source_data/image_display.json', display)
    canvas.text(8, 12, 'a: diamonds/whiskers = mean ± patient sample SD. b: individual adjacent pairs; no inferential tests.')
    canvas.text(8, 7, 'Original order retained: 161 ED→ES, 3 ES→ED. No smoothing, reversal, filling or complete-cycle synthesis.')
    alignment(fig, OUT, STEM, [a, b, c, *images], ['a', 'b', 'c', 'd1', 'd2'],
              [['a', 'b'], ['d1', 'd2']], [['a', 'c']], args.alignment_auditor)
    export_figure(fig, OUT/STEM)
    plt.close(fig)
    caption = """Supplementary Figure 8 | Observed frame-wise geometry within CAMUS half-sequences.
a, Largest absolute adjacent volume change relative to the previous frame, using all 164 sequences from 82 paired test patients. Circles/triangles denote 2CH/4CH; gray links connect patients, and diamonds/whiskers show mean ± patient sample standard deviation. b, All 3,003 observed adjacent pairs: relative area versus inferred long-axis change, colored by signed relative volume change with a shared symmetric scale. The area–length identity links these measurements; the plot is descriptive, with repeated observations within patients and no inferential test or confidence interval. c, All 20 original frames of the previously documented patient0329_2CH example. The final adjacent step increases volume by 51.4% while the inferred axis shortens by 32.5%; the measured area changes by 1.1%. No smoothing or replacement values are used. d, Actual frames18/19 with predicted contours, each frame's own inferred axis in white, and the expert contour at ES only. No intermediate expert annotation exists. Images retain the 112 × 112 cache data, unchanged 0–255 gray window, calibrated aspect and common padded 200 × 170 mm field, without cropping. Scale bars, 20 mm. Proxy axes are unvalidated constructions, not anatomical point labels or tracked tissue. All 3,167 frames remain in their stored order: 161 sequences have ED before ES and three have ES before ED. Times are FPS-derived; no reversal, reflection, interpolation or complete-cycle synthesis occurs. These public transthoracic CAMUS data are not wearable recordings. HR/CO remain unavailable. CAMUS: Leclerc et al., IEEE TMI (2019), doi:10.1109/TMI.2019.2900516; CC BY-NC-SA 4.0.
"""
    (OUT/'caption_en.md').write_text(caption, encoding='utf-8')
    provenance(OUT, sources, figure='Fig.S8', n_patients=82, n_sequences=164, n_frames=3167,
               n_adjacent_pairs=3003, n_invalid_frames=0, stored_order={'ED_to_ES': 161, 'ES_to_ED': 3},
               statistical_unit='Patient per view in a; repeated adjacent observations in b',
               confidence_intervals=None, hypothesis_tests=None, example_selection='Previously documented patient0329_2CH frames18/19',
               image_display=display, phase_order_changed=False, geometry_changed=False,
               temporal_interpolation=None, exclusions=[], font_path=font, width_mm=183, height_mm=170,
               alignment_groups={'rows': [['a', 'b'], ['d1', 'd2']], 'columns': [['a', 'c']]},
               external_alignment_auditor_used=args.alignment_auditor is not None)
    print(f'Fig.S8: 3167 frames / 3003 adjacent pairs; caption {len(caption.split())} words')


if __name__ == '__main__':
    main()
