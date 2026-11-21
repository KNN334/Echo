"""Rebuild two native-grid LV diameter surfaces over observed ED-ES intervals."""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from style.palette import (COLORS, CMAPS, LINEWIDTH, MM_PER_INCH, apply_style,
                           export_figure, figure_size, panel_heading)
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import colors
from matplotlib.cm import ScalarMappable
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import numpy as np
from _paper_common import Canvas, alignment, provenance, read_csv, write_csv, write_json
from _lv_results_common import fixed_examples, geometry_case, source_dependencies

STEM = 'fig_r03_diameter_surface'
OUT = ROOT/'figures'/STEM
HEIGHT_MM = 115
VIEW = {'elev':27, 'azim':-55}
LIMITS = {'time_s':[0,.32], 'proxy_position_percent':[0,100], 'diameter_mm':[0,60]}


def native_mesh(case, time, widths):
    """Adjacent observed vertices only; omit every cell containing missing data."""
    positions = (np.arange(20)+.5)*5
    triangles, facet_rows = [], []
    used = set()
    for frame in range(len(time)-1):
        for layer in range(19):
            corners = [(frame,layer), (frame+1,layer), (frame+1,layer+1), (frame,layer+1)]
            if not all(np.isfinite(widths[f,l]) for f,l in corners):
                continue
            for triplet in [(0,1,2), (0,2,3)]:
                nodes = [corners[k] for k in triplet]
                vertices = [[float(time[f]),float(positions[l]),float(widths[f,l])] for f,l in nodes]
                triangles.append(vertices)
                used.update(nodes)
                facet_rows.append({'case_id':case, 'facet':len(facet_rows),
                                   **{f'vertex_{k+1}_frame':f for k,(f,l) in enumerate(nodes)},
                                   **{f'vertex_{k+1}_layer':l+1 for k,(f,l) in enumerate(nodes)},
                                   'color_mean_diameter_mm':float(np.mean([v[2] for v in vertices]))})
    assert used == set(zip(*np.where(np.isfinite(widths)))), 'An isolated finite value needs a point marker'
    return triangles, facet_rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--alignment-auditor', type=Path)
    args = parser.parse_args()
    font = apply_style()
    (OUT/'source_data').mkdir(parents=True, exist_ok=True)
    (OUT/'qa').mkdir(exist_ok=True)
    chosen, selection_path = fixed_examples()
    r2_path = ROOT/'figures/fig_r02_systolic_dynamics/source_data/frame_diameters.csv'
    r2_rows = read_csv(r2_path)
    sources = [Path(__file__), OUT/'figure_contract.md', selection_path, r2_path, *source_dependencies()]
    fig = plt.figure(figsize=figure_size(height_mm=HEIGHT_MM))
    canvas = Canvas(fig)
    norm = colors.Normalize(*LIMITS['diameter_mm'], clip=False)
    axes, vertices, facets, sequence_rows = [], [], [], []
    for col, selected in enumerate(chosen):
        case = selected['case_id']
        meta, arrays, features, time, paths = geometry_case(case, verify_all=True)
        sources.extend(paths)
        assert len(time) == 18
        widths = np.array([features[str(i)]['diameters_mm'] if features[str(i)]['valid']
                           else [np.nan]*20 for i in range(len(time))], dtype=float)
        assert widths.shape == (18,20)
        r2 = [r for r in r2_rows if r['case_id'] == case]
        assert len(r2) == widths.size
        for r in r2:
            assert np.isclose(float(r['time_s']), time[int(r['frame'])], rtol=0, atol=1e-15)
            value = widths[int(r['frame']),int(r['layer'])-1]
            assert (float(r['diameter_mm']) == value) if r['diameter_mm'] else np.isnan(value)
        triangles, face_rows = native_mesh(case, time, widths)
        facets.extend(face_rows)
        vertices.extend({'case_id':case, 'frame':i, 'time_s':float(t), 'layer':l+1,
                         'proxy_axis_position_percent':float((l+.5)*5),
                         'diameter_mm':float(v) if np.isfinite(v) else None}
                        for i,t in enumerate(time) for l,v in enumerate(widths[i]))
        seq = {'case_id':case, 'selection':selected['selection'], 'rank':int(selected['rank']),
               'rank_denominator':int(selected['of_cases']), 'n_patients':1,
               'n_observed_frames':len(time), 'n_layers':20, 'n_values':int(widths.size),
               'n_valid_values':int(np.isfinite(widths).sum()), 'fps':meta['fps'],
               'start_s':float(time[0]), 'end_s':float(time[-1]),
               'min_diameter_mm':float(np.nanmin(widths)), 'max_diameter_mm':float(np.nanmax(widths)),
               'n_triangles':len(face_rows), 'roi_reviewed':meta['audit']['roi_reviewed']}
        sequence_rows.append(seq)
        assert 0 <= np.nanmin(widths) <= np.nanmax(widths) < 60
        assert time[0] == 0 and time[-1] < .32
        panel_heading(fig, 'ab'[col], f"Patient {meta['patient_id'][-4:]} · 2CH", 5+91*col, 108)
        canvas.text(10+91*col, 102, f"18 observed frames × 20 layers · rank {selected['rank']}/164")
        # Fixed camera and box aspect; no data-dependent geometry or framing.
        ax = fig.add_axes([(2+91*col)/183, 24/HEIGHT_MM, 78/183, 78/HEIGHT_MM],
                          projection='3d', proj_type='ortho')
        ax.view_init(**VIEW)
        ax.set_box_aspect((1.4,1,.85), zoom=.9)
        collection = Poly3DCollection(triangles, zsort='average', shade=False,
                        facecolors=CMAPS['sequential'](norm([r['color_mean_diameter_mm'] for r in face_rows])),
                        edgecolors=colors.to_rgba(COLORS['axis'], .3),
                        linewidths=LINEWIDTH['comparison']*.35, antialiased=True)
        collection.set_rasterized(False)
        ax.add_collection3d(collection)
        ax.set(xlim=LIMITS['time_s'], ylim=LIMITS['proxy_position_percent'], zlim=LIMITS['diameter_mm'],
               xticks=[0,.1,.2,.3], yticks=[0,50,100], zticks=[0,20,40,60])
        ax.xaxis.set_rotate_label(False)
        ax.yaxis.set_rotate_label(False)
        ax.set_xlabel('Time from ED (s)', labelpad=12, rotation=0)
        ax.set_ylabel('Proxy-axis position (%)', labelpad=12, rotation=0)
        ax.set_zlabel('Derived diameter (mm)', labelpad=1)
        ax.tick_params(pad=0)
        ax.grid(False)
        for axis in [ax.xaxis, ax.yaxis, ax.zaxis]:
            axis.pane.fill = False
            axis.pane.set_edgecolor(COLORS['background'])
            axis.line.set_color(COLORS['axis'])
            axis.line.set_linewidth(LINEWIDTH['comparison'])
        axes.append(ax)
    cbax = canvas.axes(55, 10, 73, 3)
    scalar = ScalarMappable(norm=norm, cmap=CMAPS['sequential'])
    colorbar = fig.colorbar(scalar, cax=cbax, orientation='horizontal', ticks=[0,20,40,60])
    colorbar.set_label('Derived diameter (mm)', labelpad=1)
    colorbar.outline.set_visible(False)
    write_csv(OUT/'source_data/observed_vertices.csv', vertices)
    write_csv(OUT/'source_data/mesh_facets.csv', facets)
    write_csv(OUT/'source_data/sequences.csv', sequence_rows)
    write_csv(OUT/'source_data/example_selection.csv', chosen)
    write_json(OUT/'source_data/display_settings.json', {
        'view':VIEW, 'projection':'orthographic', 'box_aspect':[1.4,1,.85], 'box_zoom':.9,
        'shared_limits':LIMITS, 'colormap':'cividis', 'shade':False,
        'mesh':'Each valid adjacent native-grid cell split at the fixed (0,2) diagonal; original vertices only.',
        'color':'Arithmetic mean diameter of the three original vertices in each triangle.',
        'missing_values':'Omit every four-corner cell containing any nonfinite vertex; do not bridge gaps.',
        'smoothing':False, 'new_time_samples':0, 'new_position_samples':0,
        'outside_observed_ED_ES':'No mesh; blank', 'HR':None, 'CO':None})
    alignment(fig, OUT, STEM, axes, ['a','b'], [['a','b']], [], args.alignment_auditor)
    # Record true final projected data limits, rather than only allocated rectangles.
    fig.canvas.draw()
    write_json(OUT/'qa/projected_bounds.json', {
        name:{'axes_rectangle_fraction':list(ax.get_position().bounds),
              'tight_bbox_pt':list(np.asarray(ax.get_tightbbox(fig.canvas.get_renderer()).bounds)*72/fig.dpi)}
        for name,ax in zip(['a','b'],axes)})
    export_figure(fig, OUT/STEM)
    plt.close(fig)
    caption = """Figure R3 | Native-grid LV diameter surfaces over the observed ED–ES interval.
a,b, Predicted contour-derived transverse diameters in patient0327_2CH and patient0229_2CH, respectively. These pre-existing examples ranked 83rd and first in ascending ED/ES mean Dice among 164 test view sequences; selection was unchanged from Figures R1/R2. Each panel contains 18 observed frames × 20 proxy-axis positions (360 values; two patients and 720 values in total). The horizontal axes represent time from ED, derived from the reported frame rate, and normalized position along each frame's independently estimated contour/PCA proxy axis. Height encodes diameter in millimetres. Adjacent original measurement nodes are joined with planar triangles using a fixed mesh diagonal; no measurement nodes, time samples or spatial samples are added. Facet color is the arithmetic mean diameter of its three vertices. Both panels use identical orthographic views, box proportions, axis ranges and a shared 0–60 mm cividis scale, without lighting or smoothing. Surfaces stop at each observed ES (0.2815 and 0.3009 s); all fluctuations are retained. These descriptive examples contain repeated observations, not 720 independent subjects, and provide no cohort inference. The unvalidated proxy axis is re-estimated per frame; mesh rows do not identify fixed anatomical tissue or measure strain. Intermediate frames have no expert reference. These surfaces are scalar visualizations, not three-dimensional LV reconstructions or acoustic beam-amplitude maps. Public transthoracic CAMUS half-sequences do not demonstrate continuous patch monitoring or full-cycle HR/CO. CAMUS: Leclerc et al., IEEE TMI (2019), doi:10.1109/TMI.2019.2900516; CC BY-NC-SA 4.0.
"""
    assert len(caption.split()) < 250, len(caption.split())
    (OUT/'caption_en.md').write_text(caption, encoding='utf-8')
    provenance(OUT, sources, figure='Fig.R3', status='candidate; awaiting user review',
               archetype='quantitative grid',
               core_conclusion='Existing contour-derived diameters describe layer-wise variation across the actually observed ED-ES interval.',
               panel_roles={'a':'Existing median-ranked example', 'b':'Existing lowest-ranked example'},
               adaptation='New scientific content; scalar-surface display inspired by the verified user-supplied Wu and Lee 2025 Fig.6a-d, DOI 10.1109/TUFFC.2025.3557519. No acoustic dB or 3D anatomical claims transferred; full text unavailable.',
               n_patients=2, n_sequences=2, n_frames=36, n_diameter_values=len(vertices),
               n_triangles=len(facets), sample_selection=chosen, sequence_summary=sequence_rows,
               statistical_unit='Two descriptive patients; frames and layers are repeated observations.',
               uncertainty='No aggregate, interval or statistical test; individual raw measurements.',
               temporal_processing={'smoothing':False, 'new_samples':0, 'phase_replacement':False,
                                    'reflection':False, 'concatenation':False, 'HR':None, 'CO':None},
               display=VIEW, projection='orthographic', shared_limits=LIMITS,
               reference='Prediction-only spatial diameters; no intermediate expert reference.',
               font_path=font, width_mm=183, height_mm=HEIGHT_MM,
               external_alignment_auditor_used=args.alignment_auditor is not None)
    print(f'Fig.R3: {len(vertices)} original values; {len(facets)} display facets; {len(caption.split())} caption words')


if __name__ == '__main__':
    main()
