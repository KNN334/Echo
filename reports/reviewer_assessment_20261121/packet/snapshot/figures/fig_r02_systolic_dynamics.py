"""Rebuild observed ED-ES image strips, diameter maps and area-length volumes."""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from style.palette import (COLORS, CMAPS, LINEWIDTH, MARKER_SIZE, apply_style,
                           export_figure, figure_size, panel_heading)
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np
from _paper_common import (Canvas, RUN, alignment, provenance, read_csv,
                           write_csv, write_json)
from _lv_results_common import (contour_legend, fixed_examples, geometry_case,
                                observed_overlay, source_dependencies, time_edges)

STEM = 'fig_r02_systolic_dynamics'
OUT = ROOT/'figures'/STEM


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--alignment-auditor', type=Path)
    args = parser.parse_args()
    font = apply_style()
    (OUT/'source_data').mkdir(parents=True, exist_ok=True)
    chosen, selection_path = fixed_examples()
    sources = [Path(__file__), selection_path, RUN/'frames.csv', RUN/'function.csv', *source_dependencies()]
    frame_table, function_table = read_csv(RUN/'frames.csv'), read_csv(RUN/'function.csv')
    fig = plt.figure(figsize=figure_size(height_mm=170))
    canvas = Canvas(fig)
    fig.legend(handles=contour_legend(), loc='upper center', bbox_to_anchor=(.5, 1), ncol=2)
    image_axes, image_ids, display, geometry, diameters, endpoints, loaded = [], [], [], [], [], [], []
    for row, selected in enumerate(chosen):
        case = selected['case_id']
        meta, arrays, features, time, paths = geometry_case(case, verify_all=True)
        sources.extend(paths)
        rows = sorted([r for r in frame_table if r['case_id'] == case], key=lambda r:int(r['frame']))
        assert [int(r['frame']) for r in rows] == list(range(len(time)))
        assert np.allclose([float(r['time_s']) for r in rows], time)
        volume, widths = [], []
        for index, t in enumerate(time):
            f, r = features[str(index)], rows[index]
            valid = f.get('valid', False) and r['valid'] == 'True'
            assert r['temporal_filtered'] == 'False'
            v = f['volume_ml'] if valid else np.nan
            d = np.asarray(f['diameters_mm']) if valid else np.full(20, np.nan)
            assert len(d) == 20
            if valid:
                assert np.isclose(v, float(r['volume_ml'])) and np.isclose(v, float(r['analysis_volume_ml']))
            volume.append(v)
            widths.append(d)
            geometry.append({'case_id':case, 'frame':index, 'time_s':float(t), 'valid':bool(valid),
                             'area_mm2':f.get('area_mm2') if valid else None,
                             'long_axis_mm':f.get('long_axis_mm') if valid else None,
                             'volume_ml':float(v) if valid else None,
                             'phase':next((p for p,i in meta['phases'].items() if i == index), 'intermediate')})
            diameters.extend({'case_id':case, 'frame':index, 'time_s':float(t), 'layer':layer+1,
                              'proxy_axis_position_percent':float((layer+.5)*5),
                              'diameter_mm':float(value) if np.isfinite(value) else None}
                             for layer,value in enumerate(d))
        volume, widths = np.asarray(volume), np.asarray(widths)
        reference = next(r for r in function_table if r['patient_id'] == meta['patient_id']
                         and r['view'] == meta['view'] and r['method'] == 'single_plane_area_length')
        assert reference['reference_scope'] == 'same_geometry_from_expert_ED_ES_contours'
        ref_volume = np.array([float(reference['ref_'+k]) for k in ['EDV','ESV']])
        assert np.allclose(volume[[0,-1]], [float(reference[k]) for k in ['EDV','ESV']])
        for phase, index, value in zip(['ED','ES'], [0,len(time)-1], ref_volume):
            endpoints.append({'case_id':case, 'phase':phase, 'frame':index,
                              'time_s':float(time[index]), 'expert_same_geometry_ml':float(value),
                              'reference_scope':reference['reference_scope']})
        loaded.append((meta, time, volume, widths, ref_volume))
        patient = meta['patient_id'][-4:]
        panel_heading(fig, 'ab'[row], f'Patient {patient} · 2CH · {len(time)} observed frames', 6, 159-44*row)
        # Actual frames nearest five uniformly spaced indices; no new image samples.
        indices = np.rint(np.linspace(0, len(time)-1, 5)).astype(int)
        for col, index in enumerate(indices):
            ax = canvas.axes(6+35*col, 126-44*row, 31, 31*170/200)
            phase = 'ED' if index == 0 else 'ES' if index == len(time)-1 else f'F{index+1}'
            record = observed_overlay(ax, meta, arrays, int(index), scale=col == 4)
            canvas.text(6+35*col, 154-44*row, f'{phase} · {time[index]:.3f} s')
            display.append(record)
            image_axes.append(ax)
            image_ids.append(f'{row}_{col}')
    map_axes = []
    for col, (meta, time, volume, widths, ref_volume) in enumerate(loaded):
        panel_heading(fig, 'cd'[col], f"Patient {meta['patient_id'][-4:]} · 2CH", 6+60*col, 72)
        ax = canvas.axes(17+60*col, 30, 42, 34)
        assert np.nanmax(widths) < 60 and np.nanmin(widths) >= 0
        mesh = ax.pcolormesh(time_edges(time), np.linspace(0,100,21), np.ma.masked_invalid(widths.T),
                             cmap=CMAPS['sequential'], vmin=0, vmax=60, shading='flat',
                             edgecolors='none', antialiased=False)
        ax.set(xlim=(-.01,.32), ylim=(100,0), xticks=[0,.1,.2,.3], yticks=[0,50,100],
               xlabel='Time from ED (s)', ylabel='Proxy-axis position (%)')
        map_axes.append(ax)
    cbax = canvas.axes(17, 10, 102, 2.5)
    colorbar = fig.colorbar(mesh, cax=cbax, orientation='horizontal', ticks=[0,20,40,60])
    colorbar.set_label('Derived diameter (mm)', labelpad=1)
    colorbar.outline.set_visible(False)
    panel_heading(fig, 'e', 'Single-plane volume', 126, 72)
    ax_volume = canvas.axes(137, 30, 42, 34)
    handles = []
    for (meta, time, volume, widths, ref_volume), linestyle, marker in zip(loaded, ['-','--'], ['o','^']):
        ax_volume.plot(time, volume, color=COLORS['primary'], linestyle=linestyle, marker=marker,
                       linewidth=LINEWIDTH['primary'], markersize=MARKER_SIZE['primary'])
        ax_volume.plot(time[[0,-1]], ref_volume, color=COLORS['expert_contour'], linestyle='none',
                       marker='D', markersize=MARKER_SIZE['reference'])
        handles.append(Line2D([], [], color=COLORS['primary'], linestyle=linestyle, marker=marker,
                               linewidth=LINEWIDTH['primary'], markersize=MARKER_SIZE['primary'],
                               label=f"Patient {meta['patient_id'][-4:]}"))
        assert np.nanmax(np.r_[volume,ref_volume]) < 200
    handles.append(Line2D([], [], color=COLORS['expert_contour'], linestyle='none', marker='D',
                           markersize=MARKER_SIZE['reference'], label='Expert ED/ES'))
    ax_volume.set(xlim=(-.01,.32), ylim=(-5,200), xticks=[0,.1,.2,.3], yticks=[0,100,200],
                  xlabel='Time from ED (s)', ylabel='Volume (mL)')
    fig.legend(handles=handles, loc='lower left', bbox_to_anchor=(137/183, 2/170),
               borderaxespad=0, labelspacing=.2)
    write_csv(OUT/'source_data/example_selection.csv', chosen)
    write_csv(OUT/'source_data/frame_geometry.csv', geometry)
    write_csv(OUT/'source_data/frame_diameters.csv', diameters)
    write_csv(OUT/'source_data/expert_endpoints.csv', endpoints)
    write_json(OUT/'source_data/image_display.json', display)
    write_json(OUT/'source_data/heatmap_cells.json', {
        meta['patient_id']+'_'+meta['view']: {'time_cell_edges_s':time_edges(time).tolist(),
                  'position_edges_percent':np.linspace(0,100,21).tolist(),
                  'values':'frame_diameters.csv; all real observed frames',
                  'interpolation':False, 'outside_observed_interval':'blank', 'range_mm':[0,60]}
        for meta,time,*_ in loaded})
    alignment(fig, OUT, STEM, image_axes+map_axes+[ax_volume], image_ids+['c','d','e'],
              [[f'{r}_{c}' for c in range(5)] for r in range(2)]+[['c','d','e']],
              [[f'0_{c}',f'1_{c}'] for c in range(5)], args.alignment_auditor)
    export_figure(fig, OUT/STEM)
    plt.close(fig)
    caption = """Figure R2 | Observed ED–ES LV morphology and geometric time courses.
a,b, Five actual frames illustrate each of two 2CH half-sequences (18 frames each): patient0327 and patient0229, selected previously at ranks 83/164 and 1/164 by ED/ES mean Dice. Indices are the nearest integers to five uniformly spaced positions in each observed sequence; all frames are retained in quantitative panels. Blue contours are predictions; dashed magenta expert contours are available only at ED and ES. Native 112 × 112 images share an unchanged gray window, physical aspect ratio and 200 × 170 mm field. Scale bars, 20 mm. c,d, Predicted transverse diameters at 20 normalized proxy-axis positions across all 18 observed frames per sequence (720 measurements total), with a shared 0–60 mm cividis scale. Cells represent individual measurements without interpolation and stop exactly at the observed ES. Proxy axes are re-estimated per frame; rows do not track fixed tissue or measure strain. e, All 36 single-plane area–length volume estimates; straight segments connect adjacent measurements without smoothing or added samples. Magenta diamonds show four expert-contour endpoint volumes calculated by the same geometric method, not independent clinical gold standards. Time is derived from reported frame rates. These two-patient descriptive examples retain all fluctuations and do not establish intermediate-frame accuracy, physiological event timing or cohort-level dynamics. The unvalidated proxy-axis heuristic remains unchanged. Public transthoracic CAMUS half-sequences are not continuous patch recordings; full-cycle HR/CO are unavailable. CAMUS: Leclerc et al., IEEE TMI (2019), doi:10.1109/TMI.2019.2900516; CC BY-NC-SA 4.0.
"""
    assert len(caption.split()) < 250
    (OUT/'caption_en.md').write_text(caption, encoding='utf-8')
    provenance(OUT, sources, figure='Fig.R2', status='provisional results candidate; awaiting user review',
               core_conclusion='Observed LV segmentation supports frame-wise spatial diameter maps and single-plane volume trajectories over the acquired ED-ES interval.',
               panel_roles={'a':'Median-ranked sequence: actual images', 'b':'Lowest-ranked sequence: actual images',
                            'c':'Median-ranked sequence: diameter time map', 'd':'Lowest-ranked sequence: diameter time map',
                            'e':'Raw area-length volume trajectories and expert endpoints'},
               adaptation='Wu and Lee 2025 Fig.7 image matrix plus Fig.6e profile-to-quantity organization, seen in user screenshot; time mapping is a new project-specific analysis, not a claim from that paper.',
               n_patients=2, n_sequences=2, n_observed_frames=len(geometry), n_diameter_values=len(diameters),
               n_displayed_images=len(display), sample_selection=chosen,
               uncertainty='Descriptive repeated observations in two patients, no population inference or CI.',
               temporal_processing={'timestamp_source':'derived_from_fps', 'smoothing':False, 'new_samples':0,
                                    'reflection':False, 'concatenation':False, 'phase_replacement':False,
                                    'invalid_values':'masked cells and disconnected NaN curves', 'HR':None, 'CO':None},
               image_display=display, heatmap_limits_mm=[0,60], volume_limits_ml=[-5,200],
               axis_padding='Small negative display margins keep real ED and low reference markers visible; no negative observations.',
               font_path=font, width_mm=183, height_mm=170,
               external_alignment_auditor_used=args.alignment_auditor is not None)
    print(f'Fig.R2: {len(geometry)} actual frames, {len(diameters)} diameter values; caption {len(caption.split())} words')


if __name__ == '__main__':
    main()
