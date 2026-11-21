"""Rebuild a reference-inspired LV image matrix and physical diameter profiles."""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from style.palette import (COLORS, LINEWIDTH, apply_style, export_figure,
                           figure_size, panel_heading)
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np
from _paper_common import Canvas, alignment, provenance, write_csv, write_json
from _lv_results_common import (contour_legend, expert_features, fixed_examples,
                                geometry_case, observed_overlay, source_dependencies)

STEM = 'fig_r01_lv_morphology'
OUT = ROOT/'figures'/STEM


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--alignment-auditor', type=Path)
    args = parser.parse_args()
    font = apply_style()
    (OUT/'source_data').mkdir(parents=True, exist_ok=True)
    chosen, selection_path = fixed_examples()
    sources = [Path(__file__), selection_path, *source_dependencies()]
    fig = plt.figure(figsize=figure_size(height_mm=170))
    canvas = Canvas(fig)
    fig.legend(handles=contour_legend(), loc='upper center', bbox_to_anchor=(.5, 1), ncol=2)
    images, ids, display, profiles, loaded = [], [], [], [], {}
    for row, selected in enumerate(chosen):
        patient = selected['case_id'].split('_')[0]
        panel_heading(fig, 'ab'[row],
                      f"Patient {patient[-4:]} · 2CH sequence rank {selected['rank']}/164", 6, 158-47*row)
        for col, (view, phase) in enumerate([('2CH','ED'),('2CH','ES'),('4CH','ED'),('4CH','ES')]):
            case = patient+'_'+view
            if case not in loaded:
                loaded[case] = geometry_case(case)
                sources.extend(loaded[case][-1])
            meta, arrays, features, time, _ = loaded[case]
            ax = canvas.axes(6+43.3*col, 118-47*row, 41, 41*170/200)
            record = observed_overlay(ax, meta, arrays, meta['phases'][phase],
                                      scale=True, label=f'{view} · {phase}')
            record.update({'panel': 'ab'[row], 'selection_basis': selected})
            display.append(record)
            images.append(ax)
            ids.append(f'{row}_{col}')
    # Profiles quantify the median-ranked sequence and its separately acquired view.
    plot_axes = []
    x = (np.arange(20)+.5)*5
    handles = []
    for col, view in enumerate(['2CH','4CH']):
        panel_heading(fig, 'cd'[col], f'{view} diameter profiles · patient 0327', 6+91*col, 63)
        ax = canvas.axes(19+91*col, 22, 62, 34)
        meta, arrays, features, _, _ = loaded['patient0327_'+view]
        for source, color in [('Prediction','primary'),('Expert','expert_contour')]:
            for phase, linestyle in [('ED','-'),('ES','--')]:
                feature = (features[str(meta['phases'][phase])] if source == 'Prediction'
                           else expert_features(meta, arrays, phase))
                values = np.asarray(feature['diameters_mm'])
                assert len(values) == 20 and np.isfinite(values).all()
                ax.plot(x, values, color=COLORS[color], linestyle=linestyle,
                        linewidth=LINEWIDTH['primary' if source == 'Prediction' else 'reference'])
                if col == 0:
                    handles.append(Line2D([], [], color=COLORS[color], linestyle=linestyle,
                                           linewidth=LINEWIDTH['primary'], label=f'{source} · {phase}'))
                profiles.extend({'case_id':'patient0327_'+view, 'phase':phase, 'source':source,
                                 'layer':i+1, 'proxy_axis_position_percent':float(t),
                                 'diameter_mm':float(v), 'axis_definition':'each_contour_own_PCA_proxy_axis'}
                                for i, (t,v) in enumerate(zip(x, values)))
        ax.set(xlim=(0,100), ylim=(0,60), xticks=[0,25,50,75,100], yticks=[0,20,40,60],
               xlabel='Proxy-axis position (%)', ylabel='Derived diameter (mm)')
        assert max(r['diameter_mm'] for r in profiles) < 60
        plot_axes.append(ax)
    fig.legend(handles=handles, loc='lower center', bbox_to_anchor=(.5, .006), ncol=4)
    write_csv(OUT/'source_data/example_selection.csv', chosen)
    write_csv(OUT/'source_data/diameter_profiles.csv', profiles)
    write_json(OUT/'source_data/image_display.json', display)
    all_axes = images+plot_axes
    all_ids = ids+['c','d']
    alignment(fig, OUT, STEM, all_axes, all_ids,
              [[f'{r}_{c}' for c in range(4)] for r in range(2)]+[['c','d']],
              [[f'0_{c}', f'1_{c}'] for c in range(4)], args.alignment_auditor)
    export_figure(fig, OUT/STEM)
    plt.close(fig)
    caption = """Figure R1 | LV morphology and contour-derived diameter profiles in paired CAMUS views.
a,b, Two patients shown in a common 2CH/4CH × ED/ES image matrix. Selection was fixed before this figure: patient0327_2CH and patient0229_2CH ranked 83rd and first, respectively, in ascending ED/ES mean Dice among 164 test view sequences. The paired 4CH views were added without reranking; the ranks do not describe patient-level or 4CH performance. Blue and dashed magenta contours denote prediction and expert annotation. All eight native 112 × 112 cache images use an unchanged 0–255 gray window and a common 200 × 170 mm physical field with padding, preserved aspect ratio and no further cropping. Scale bars, 20 mm. c,d, Twenty contour-derived transverse diameters for patient0327, displayed separately for 2CH and 4CH (solid, ED; dashed, ES). Position is normalized along each contour's independently estimated proxy axis; the profiles do not establish corresponding anatomical locations or anatomical landmark accuracy. No profile smoothing was applied. These are descriptive examples (two patients, four view sequences, eight labeled frames; profiles from one patient), not cohort estimates. The views were acquired separately and are not synchronized or reconstructed in 3D. Geometry uses the existing unvalidated contour/PCA heuristic; expert-derived measurements are not independent clinical standards. The public transthoracic CAMUS data do not represent patch recordings. CAMUS: Leclerc et al., IEEE TMI (2019), doi:10.1109/TMI.2019.2900516; CC BY-NC-SA 4.0.
"""
    assert len(caption.split()) < 250
    (OUT/'caption_en.md').write_text(caption, encoding='utf-8')
    provenance(OUT, sources, figure='Fig.R1', status='provisional results candidate; awaiting user review',
               core_conclusion='Calibrated LV contours support view-specific spatial morphology profiles at the observed ED and ES.',
               panel_roles={'a':'Median-ranked sequence with paired view', 'b':'Existing lowest-ranked sequence with paired view',
                            'c':'2CH spatial quantification', 'd':'4CH spatial quantification'},
               adaptation='Organization only: Wu and Lee 2025, DOI 10.1109/TUFFC.2025.3557519, user-supplied Fig.7 image matrix and Fig.6e profiles. Full text unavailable; no beamformer claims transferred.',
               n_patients=2, n_view_sequences=4, n_labeled_frames=8, n_profile_values=len(profiles),
               sample_selection=chosen, uncertainty='Individual descriptive examples, no population inference or CI.',
               image_display=display, reference_scope='Expert contours only; no anatomical point reference.',
               font_path=font, width_mm=183, height_mm=170,
               external_alignment_auditor_used=args.alignment_auditor is not None)
    print(f'Fig.R1: 8 real frames, {len(profiles)} profile values; caption {len(caption.split())} words')


if __name__ == '__main__':
    main()
