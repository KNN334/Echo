"""Show spatial coverage and volume-path relationships of the frozen proxy geometry."""
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
from matplotlib.lines import Line2D
import numpy as np
from src.geometry.mask_features import main_component, mask_features
from _paper_common import (Canvas, FROZEN, RUN, alignment, calibrated_overlay, load_case,
                           provenance, read_csv, read_json, write_csv, write_json)

STEM = 'fig_s06_geometry_coverage'
OUT = ROOT/'figures'/STEM
AUDIT = ROOT/'reports/result_integrity/camus_cuda_progress_20261121'
METRICS = ['proxy_axis_to_mask_span', 'mask_area_beyond_proxy_base_fraction']
SOURCE_COLORS = {'pred': 'primary', 'expert': 'expert_contour'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--alignment-auditor', type=Path)
    args = parser.parse_args()
    font = apply_style()
    (OUT/'source_data').mkdir(parents=True, exist_ok=True)
    split_path = ROOT/'configs/camus_splits.json'
    patients = sorted(p for p, s in read_json(split_path)['patients'].items() if s == 'test')
    geometry_path = AUDIT/'geometry_diagnostics.csv'
    ratio_path = AUDIT/'cross_geometry_volume_ratios.csv'
    geometry, ratios = read_csv(geometry_path), read_csv(ratio_path)
    functions = {(r['patient_id'], r['method'], r['view']): r for r in read_csv(RUN/'function.csv')}
    assert len(patients) == 82 and len(geometry) == 656 and len(ratios) == 328
    assert {r['patient_id'] for r in geometry} == set(patients)
    keys = {(r['case_id'], r['phase'], r['source']) for r in geometry}
    assert len(keys) == 656
    grouped = defaultdict(list)
    for r in geometry:
        grouped[(r['patient_id'], r['phase'], r['source'])].append(r)
    patient_rows = []
    for patient in patients:
        for phase in ['ED', 'ES']:
            for source in ['pred', 'expert']:
                group = grouped[(patient, phase, source)]
                assert len(group) == 2 and {r['view'] for r in group} == {'2CH', '4CH'}
                patient_rows.append({'patient_id': patient, 'phase': phase, 'source': source,
                                     'n_views': 2, **{metric: float(np.mean([float(r[metric]) for r in group]))
                                                     for metric in METRICS}})
    for r in ratios:
        group = grouped[(r['patient_id'], r['phase'], r['source'])]
        mean_single = float(np.mean([float(g['volume_ml']) for g in group]))
        function = functions[(r['patient_id'], '20_disks_shorter_axis', 'biplane')]
        metric = 'EDV' if r['phase'] == 'ED' else 'ESV'
        biplane = float(function[('ref_' if r['source'] == 'expert' else '')+metric])
        assert mean_single > 0
        assert np.allclose([mean_single, biplane, biplane/mean_single],
                           [float(r['mean_single_plane_ml']), float(r['biplane_ml']),
                            float(r['biplane_to_mean_single_ratio'])], rtol=1e-12, atol=1e-12)
    assert len(patient_rows) == 328
    write_csv(OUT/'source_data/source_geometry.csv', geometry)
    write_csv(OUT/'source_data/patient_geometry.csv', patient_rows)
    write_csv(OUT/'source_data/volume_paths.csv', ratios)
    selection_path = FROZEN/'source_data/example_selection.csv'
    selected = next(r for r in read_csv(selection_path) if r['selection'] == 'Median')
    assert selected['case_id'] == 'patient0327_2CH' and int(selected['rank']) == 83
    case = selected['case_id']
    meta, arrays, image_sources = load_case(case)
    index = meta['phases']['ED']
    mask = arrays['original_gt'][list(arrays['original_gt_indices']).index(index)]
    scale = np.asarray(meta['audit']['spacing_xy_mm'])
    feature = mask_features(mask, scale)
    clean, _ = main_component(mask)
    points = feature['landmarks_xy']
    apex = np.asarray(points['apex'])*scale
    base = (np.asarray(points['base_left'])+np.asarray(points['base_right']))*scale/2
    length = np.linalg.norm(base-apex)
    direction = (base-apex)/length
    side = np.array([direction[1], -direction[0]])
    xy = np.argwhere(clean)[:, ::-1]*scale
    projection = (xy-apex)@direction
    beyond = np.zeros_like(clean)
    beyond[tuple(np.argwhere(clean)[projection > length].T)] = True
    selected_geometry = next(r for r in geometry if r['case_id'] == case and r['phase'] == 'ED'
                             and r['source'] == 'expert')
    measures = {'proxy_axis_to_mask_span': float(length/np.ptp(projection)),
                'mask_area_beyond_proxy_base_fraction': float(np.mean(projection > length)),
                'axis_length_mm': float(length), 'full_mask_projected_span_mm': float(np.ptp(projection))}
    assert all(np.isclose(v, float(selected_geometry[k]), rtol=1e-12, atol=1e-12)
               for k, v in measures.items())
    fig = plt.figure(figsize=figure_size(height_mm=170))
    canvas = Canvas(fig)
    canvas.text(8, 164, 'Spatial coverage and volume paths of the existing contour-derived proxy geometry')
    handles = [Line2D([], [], marker=('o' if source == 'pred' else '^'), linestyle='none', color=COLORS[SOURCE_COLORS[source]],
                      markersize=MARKER_SIZE['primary'], label=label)
               for source, label in [('pred', 'Prediction'), ('expert', 'Expert contour')]]
    fig.legend(handles=handles, loc='upper center', bbox_to_anchor=(.66, .948), ncol=2)
    panel_heading(fig, 'a', '2CH · ED · patient 0327', 8, 154)
    image_ax = canvas.axes(17, 91, 68, 68*170/200)
    display = calibrated_overlay(image_ax, meta, arrays, 'ED', field_mm=(200, 170), contours=False, scale=False)
    right, bottom = image_ax.get_xlim()[1], image_ax.get_ylim()[0]
    image_ax.plot([right-50, right-30], [bottom-5, bottom-5],
                  color=COLORS['image_annotation'], linewidth=LINEWIDTH['scale'])
    image_ax.text(right-40, bottom-10, '20 mm', ha='center', color=COLORS['image_annotation'])
    display['scale_bar_mm'] = 20
    display['scale_bar_placement'] = 'Lower padded black field, outside the native raster rectangle'
    x, y = np.arange(clean.shape[1])*scale[0], np.arange(clean.shape[0])*scale[1]
    image_ax.contourf(x, y, beyond.astype(float), levels=[.5, 1.5],
                      colors=[COLORS['expert_contour']], alpha=.45)
    image_ax.contour(x, y, clean, levels=[.5], colors=[COLORS['expert_contour']],
                     linewidths=LINEWIDTH['reference'])
    lateral = (xy-base)@side
    basal_line = base + np.asarray([lateral.min(), lateral.max()])[:, None]*side
    image_ax.plot([apex[0], base[0]], [apex[1], base[1]], color=COLORS['image_annotation'],
                  linewidth=LINEWIDTH['primary'])
    image_ax.plot(basal_line[:, 0], basal_line[:, 1], color=COLORS['image_annotation'],
                  linestyle='--', linewidth=LINEWIDTH['reference'])
    display['contours'] = 'Original expert contour plus own inferred proxy axis/base; no predicted contour displayed'
    display['fill'] = 'Expert-contour area beyond own proxy base; not error or probability'
    canvas.text(8, 87, 'White: proxy axis / dashed basal line')
    canvas.text(8, 83, 'Magenta fill: contour area beyond the line')
    write_json(OUT/'source_data/example_geometry.json',
               {'selection': selected, 'display': display, 'source': 'expert', 'phase': 'ED',
                'apex_proxy_mm': apex.tolist(), 'base_proxy_mm': base.tolist(),
                'basal_display_segment_mm': basal_line.tolist(),
                'beyond_pixel_count': int(beyond.sum()), 'clean_mask_pixel_count': int(clean.sum()),
                'fill': 'Area beyond own proxy base; not error or probability', **measures})
    plot_axes, stats = [], []
    for letter, xpos, ypos, metric, title, ylabel, limit, multiplier in [
            ('b', 110, 103, METRICS[0], 'Axial extent covered', 'Proxy axis / contour span (%)', 100, 100),
            ('c', 19, 28, METRICS[1], 'Contour area beyond proxy base', 'Area beyond proxy base (%)', 100, 100),
            ('d', 110, 28, 'biplane_to_mean_single_ratio', 'Biplane / mean single-plane volume', 'Volume ratio', 1, 1)]:
        panel_heading(fig, letter, title, xpos-11, ypos+51)
        ax = canvas.axes(xpos, ypos, 65, 43)
        for phase_index, phase in enumerate(['ED', 'ES']):
            grouped_values = {}
            for source in ['pred', 'expert']:
                records = (patient_rows if metric in METRICS else ratios)
                group = sorted([r for r in records if r['phase'] == phase and r['source'] == source],
                               key=lambda r: r['patient_id'])
                assert len(group) == 82 and [r['patient_id'] for r in group] == patients
                values = np.array([float(r[metric])*multiplier for r in group])
                assert (values >= 0).all() and (values <= limit).all()
                grouped_values[source] = values
                stats.append({'metric': metric, 'phase': phase, 'source': source, 'n_patients': 82,
                              'unit': '%' if multiplier == 100 else 'ratio',
                              'mean': float(values.mean()), 'sample_sd': float(values.std(ddof=1)),
                              'median': float(np.median(values)), 'minimum': float(values.min()),
                              'maximum': float(values.max())})
            offsets = np.linspace(-.06, .06, 82)
            for j in range(82):
                ax.plot(phase_index+np.array([-.18, .18])+offsets[j],
                        [grouped_values['pred'][j], grouped_values['expert'][j]],
                        color=COLORS['muted'], alpha=.16, linewidth=LINEWIDTH['comparison'], zorder=1)
            for source, shift, marker in [('pred', -.18, 'o'), ('expert', .18, '^')]:
                values = grouped_values[source]
                color = COLORS[SOURCE_COLORS[source]]
                ax.scatter(phase_index+shift+offsets, values, color=color, marker=marker,
                           alpha=.65, s=MARKER_SIZE['primary']**2, edgecolors='none', zorder=2)
                ax.errorbar(phase_index+shift+.09, values.mean(), yerr=values.std(ddof=1),
                            marker='D', color=color, markerfacecolor=COLORS['background'],
                            markersize=MARKER_SIZE['reference'], linewidth=LINEWIDTH['primary'],
                            capsize=MARKER_SIZE['primary'], zorder=3)
        ax.set(xlim=(-.5, 1.5), ylim=(0, limit), xticks=[0, 1], xticklabels=['ED', 'ES'],
               yticks=np.linspace(0, limit, 5), ylabel=ylabel)
        ax.tick_params(axis='x', length=0)
        ax.spines['bottom'].set_visible(False)
        plot_axes.append(ax)
    write_csv(OUT/'source_data/panel_statistics.csv', stats)
    canvas.text(8, 15, 'b–d: 82 patients per phase/source; points/links: patients; diamonds/whiskers: mean ± sample SD.')
    canvas.text(8, 10, 'b,c average the two views per patient. d uses separately acquired views at their expert ED/ES phases.')
    canvas.text(8, 5, 'Proxy geometry is unvalidated; contour-derived references are not independent clinical volumes. CAMUS, not patch data.')
    alignment(fig, OUT, STEM, [image_ax, *plot_axes], list('abcd'), [['c', 'd']],
              [['b', 'd']], args.alignment_auditor)
    export_figure(fig, OUT/STEM)
    plt.close(fig)
    caption = """Supplementary Figure 6 | Spatial coverage and volume paths of the existing contour-derived proxy geometry.
a, A calibrated CAMUS 2CH ED image from patient0327, the previously fixed median-ranked sequence (83/164 by sequence Dice). The expert contour is magenta; the solid white segment is its inferred proxy axis, the dashed line its proxy base, and the filled region the contour area beyond that line. These are derived geometric constructions, not independently annotated anatomical landmarks. The unchanged 112 × 112 cache frame uses a 0–255 gray window, preserved physical aspect and a 200 × 170 mm padded field without additional cropping. Scale bar, 20 mm. b,c, Proxy-axis length divided by full contour projection span, and area beyond the proxy base, respectively. Each point averages the two views within one patient, source and expert phase. d, Existing biplane 20-disk volume divided by the mean of the two single-plane area–length volumes, with no recalibration or geometry modification. Ratios also depend on formula and paired-view geometry; they do not isolate a causal contribution of coverage. The views were acquired separately; paired expert phases do not establish synchronization. Each phase/source includes all 82 patients. Blue circles and magenta triangles denote predicted and expert-contour constructions; gray links connect the same patient, and diamonds/whiskers show mean ± patient sample standard deviation. The cohort uses 656 source/view/phase records and 328 volume ratios. All observations are retained; no confidence intervals or hypothesis tests are calculated. The geometric paths have different spatial coverage and are not interchangeable clinical volumes. Neither has an independent clinical volume standard; proxy geometry remains unvalidated. Public CAMUS half-sequences are not patch recordings; HR/CO are unavailable. CAMUS: Leclerc et al., IEEE TMI (2019), doi:10.1109/TMI.2019.2900516; CC BY-NC-SA 4.0.
"""
    (OUT/'caption_en.md').write_text(caption, encoding='utf-8')
    sources = [Path(__file__), OUT/'figure_contract.md', split_path, geometry_path, ratio_path,
               AUDIT/'audit.json', RUN/'function.csv', selection_path, *image_sources,
               ROOT/'src/geometry/mask_features.py', ROOT/'src/geometry/volume.py',
               ROOT/'src/data/transforms.py']
    provenance(OUT, sources, figure='Fig.S6', n_patients=82, n_source_geometry_rows=656,
               n_patient_phase_source_geometry=328, n_volume_path_ratios=328, n_example_frames=1,
               example_selection=selected, image_display=display, statistical_unit='Patient',
               variability='Patient sample SD; no confidence intervals', hypothesis_tests=None,
               reference_scope='Derived contour geometry; no independent anatomical or clinical volume truth',
               exclusions=[], geometry_changed=False, image_scale='Original spatial calibration',
               alignment_groups={'rows': [['c', 'd']], 'columns': [['b', 'd']],
                                 'image_a': 'Measured; calibrated image aspect not comparable to statistical axes'},
               font_path=font, width_mm=183, height_mm=170,
               external_alignment_auditor_used=args.alignment_auditor is not None)
    print(f'Fig.S6: 656 geometry records / 328 volume ratios; caption {len(caption.split())} words')


if __name__ == '__main__':
    main()
