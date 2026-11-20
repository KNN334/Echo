"""Rebuild Fig. 4 from observed ED–ES half-sequences; no full-cycle synthesis."""
import argparse
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
from _paper_common import (Canvas, FROZEN, PREPARED, RUN, alignment, provenance,
                           read_csv, read_json, write_csv)

OUT = ROOT/'figures/fig_04_half_sequence'
STEM = 'fig_04_half_sequence'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--alignment-auditor', type=Path)
    args = parser.parse_args()
    font = apply_style()
    OUT.mkdir(exist_ok=True)
    (OUT/'source_data').mkdir(exist_ok=True)
    selection_path = FROZEN/'source_data/example_selection.csv'
    selection = read_csv(selection_path)
    assert [r['case_id'] for r in selection]==[
        'patient0229_2CH','patient0189_4CH','patient0327_2CH','patient0075_4CH']
    all_frames = read_csv(RUN/'frames.csv')
    functions = read_csv(RUN/'function.csv')
    loaded, source_rows, endpoint_rows, curve_statistics = [], [], [], []
    sources = [selection_path,RUN/'frames.csv',RUN/'function.csv',Path(__file__)]
    for chosen in selection:
        case = chosen['case_id']
        meta_path = PREPARED/(case+'.json')
        feature_path = RUN/(case+'_features.json')
        meta = read_json(meta_path)
        features = read_json(feature_path)['frames']
        assert meta['sequence_type']=='half_sequence' and meta['split']=='test'
        assert meta['audit']['timestamp_source']=='derived_from_fps'
        ed,es = [meta['phases'][p] for p in ['ED','ES']]
        assert ed<es
        rows = sorted([r for r in all_frames if r['case_id']==case],key=lambda r:int(r['frame']))
        assert [int(r['frame']) for r in rows]==list(range(meta['audit']['n_frames']))
        observed = [r for r in rows if ed<=int(r['frame'])<=es]
        # All four preselected cases end at ES. Never manufacture a later ED.
        assert len(observed)==len(rows) and ed==0 and es==len(rows)-1
        time = np.array([float(r['time_s']) for r in observed])
        assert np.all(np.diff(time)>0)
        assert np.allclose(time,np.arange(len(time))/meta['fps'])
        volume = []
        for row in observed:
            f = features[row['frame']]
            good = row['valid']=='True' and f.get('valid') and bool(row['analysis_volume_ml'])
            value = float(row['analysis_volume_ml']) if good else np.nan
            assert row['temporal_filtered']=='False'
            if good:
                assert np.isfinite(value) and np.isclose(value,f['volume_ml'])
                assert np.isclose(value,float(row['volume_ml']))
            volume.append(value)
            source_rows.append({'selection':chosen['selection'],**row})
        volume = np.asarray(volume)
        reference = next(r for r in functions if r['patient_id']==meta['patient_id'] and
                         r['view']==meta['view'] and r['method']=='single_plane_area_length')
        assert reference['reference_scope']=='same_geometry_from_expert_ED_ES_contours'
        ref_volume = np.array([float(reference['ref_'+k]) for k in ['EDV','ESV']])
        assert np.allclose(volume[[ed,es]],[float(reference[k]) for k in ['EDV','ESV']])
        assert np.isfinite(ref_volume).all()
        change = np.abs(np.diff(volume))/volume[:-1]
        for phase,index,ref_value in zip(['ED','ES'],[ed,es],ref_volume):
            endpoint_rows.append({'case_id':case,'phase':phase,'frame':index,'time_s':float(time[index]),
                                  'prediction_ml':float(volume[index]),'expert_same_geometry_ml':float(ref_value),
                                  'reference_scope':reference['reference_scope']})
        stat = {'selection':chosen['selection'],'case_id':case,'rank_of_view_sequences':int(chosen['rank']),
                'n_ranked_view_sequences':int(chosen['of_cases']),'n_patients':1,
                'n_observed_frames':len(time),'n_valid_volumes':int(np.isfinite(volume).sum()),
                'fps':meta['fps'],'duration_s':float(time[-1]),
                'max_adjacent_relative_volume_change':float(np.nanmax(change)),
                'roi_reviewed':meta['audit']['roi_reviewed']}
        curve_statistics.append(stat)
        loaded.append((chosen,meta,time,volume,ref_volume,stat))
        sources.extend([meta_path,feature_path])
    assert len({m['patient_id'] for _,m,*_ in loaded})==4
    # Uniform physical axes display every value, including the high-volume Q3 case.
    x_limit = float(np.ceil(max(t[-1] for _,_,t,*_ in loaded)/.05)*.05)
    all_values = np.concatenate([np.r_[v,ref] for _,_,_,v,ref,_ in loaded])
    y_limit = float(np.ceil(np.nanmax(all_values)/100)*100)
    assert np.isclose(x_limit,.45) and np.isclose(y_limit,600)
    fig = plt.figure(figsize=figure_size(height_mm=170))
    canvas = Canvas(fig)
    fig.legend(handles=[
        Line2D([],[],color=COLORS['primary'],linewidth=LINEWIDTH['primary'],marker='o',
               markersize=MARKER_SIZE['primary'],label='Prediction · each observed frame'),
        Line2D([],[],color=COLORS['expert_contour'],linestyle='none',marker='D',
               markersize=MARKER_SIZE['reference'],label='Expert ED/ES · same geometry')],
               loc='upper left',bbox_to_anchor=(8/183,167/170),ncol=2)
    axes = []
    for i,(chosen,meta,time,volume,ref_volume,stat) in enumerate(loaded):
        x,y = (17,105) if i==0 else (109,105) if i==1 else (17,32) if i==2 else (109,32)
        title_y = 155 if i<2 else 82
        title = chosen['selection']+'-ranked sequence · '+meta['view']
        panel_heading(fig,'abcd'[i],title,x-9,title_y)
        canvas.text(x-9,title_y-5,f"Patient {meta['patient_id'].replace('patient','')} · rank {chosen['rank']}/164 · {len(time)} frames")
        canvas.text(x-9,title_y-10,f"Max adjacent volume change: {100*stat['max_adjacent_relative_volume_change']:.1f}%")
        ax = canvas.axes(x,y,66,37)
        ax.plot(time,volume,color=COLORS['primary'],linewidth=LINEWIDTH['primary'],marker='o',
                 markersize=MARKER_SIZE['primary'])
        # No connecting line or reference interpolation between the expert endpoints.
        ax.plot(time[[0,-1]],ref_volume,linestyle='none',marker='D',markersize=MARKER_SIZE['reference'],
                 color=COLORS['expert_contour'])
        for phase,t in zip(['ED','ES'],time[[0,-1]]):
            ax.axvline(t,color=COLORS['muted'],linestyle=':',linewidth=LINEWIDTH['comparison'],zorder=0)
            ax.text(t+(.006 if phase=='ED' else -.006),570,phase,
                     ha='left' if phase=='ED' else 'right',va='top',color=COLORS['muted'])
        ax.set(xlim=(-.02,x_limit),ylim=(-20,y_limit),
               xticks=[0,.1,.2,.3,.4],yticks=[0,200,400,600],
               xlabel='Time from ED (s; FPS-derived)',ylabel='Single-plane volume (mL)')
        assert time.min()>=0 and time.max()<=x_limit
        assert np.nanmin(volume)>=0 and max(np.nanmax(volume),ref_volume.max())<y_limit
        axes.append(ax)
        canvas.text(x-9,89 if i<2 else 16,
                    f'Pred ED/ES {volume[0]:.1f}/{volume[-1]:.1f} · ref {ref_volume[0]:.1f}/{ref_volume[-1]:.1f} mL')
    canvas.text(8,7,'Same area–length geometry; current proxy-axis definition is unvalidated. All panels share both axis ranges.')
    canvas.text(8,2,'Observed ED–ES only · expert reference at two endpoints · no full beat, temporal synthesis, HR or CO.')
    write_csv(OUT/'source_data/frames.csv',source_rows)
    write_csv(OUT/'source_data/expert_endpoints.csv',endpoint_rows)
    write_csv(OUT/'source_data/curve_statistics.csv',curve_statistics)
    write_csv(OUT/'source_data/example_selection.csv',selection)
    alignment(fig,OUT,STEM,axes,list('abcd'),[['a','b'],['c','d']],[['a','c'],['b','d']],args.alignment_auditor)
    export_figure(fig,OUT/STEM)
    plt.close(fig)
    caption = """Figure 4 | Observed ED–ES half-sequence volume estimates and endpoint references in fixed-rank CAMUS examples.
a–d, The pre-existing lowest, first-quartile, median and third-quartile examples ranked by ED/ES mean Dice among 164 test view sequences, matching Figure 2. Each panel represents one patient and one view: patient0229_2CH (18 frames), patient0189_4CH (24 frames), patient0327_2CH (18 frames) and patient0075_4CH (16 frames). Blue circles show every valid observed-frame single-plane area–length volume; straight segments join adjacent observations without adding samples. Magenta diamonds show the expert-contour volumes at ED and ES, calculated with the same geometry; these are not independent clinical volume standards. No expert reference trajectory is available between the endpoints. Vertical dotted lines mark the expert-labeled ED/ES times. Time is derived from each sequence's reported frame rate and starts at ED. Both axes are shared across all panels; traces stop at the observed ES rather than extending to the plot boundary. Endpoint values and the largest adjacent-frame relative volume change, defined as |V(t+1)−V(t)|/V(t), are reported descriptively. All original frame values and fluctuations are retained, with invalid values left as gaps. No smoothing, phase replacement, reflection, sequence concatenation or complete-beat interpolation was applied. The current proxy-axis geometry is unvalidated, and temporal jumps must not be interpreted as established physiological events. The views were acquired separately. These public transthoracic CAMUS half-sequences do not demonstrate continuous patch monitoring; HR/CO are unavailable. CAMUS: Leclerc et al., IEEE TMI (2019), doi:10.1109/TMI.2019.2900516; CC BY-NC-SA 4.0.
"""
    assert len(caption.split())<250
    (OUT/'caption_en.md').write_text(caption,encoding='utf-8')
    provenance(OUT,sources,figure='Fig.4',archetype='quantitative grid',
               core_conclusion='Observed half-sequence estimates expose temporal variation and endpoint mismatch without establishing full-cycle or wearable accuracy.',
               panel_roles={'a':'Lowest-rank failure boundary','b':'Existing Q1 example','c':'Existing median example','d':'Existing Q3 example with high volumes'},
               adaptation='Time-series organization only from Ouyang Fig.2f and Hu Fig.5b; their full-beat claims are not transferred.',
               n_patients_total=4,n_frames_total=len(source_rows),sample_selection=selection,
               statistical_unit='One patient/view per panel; frames are repeated observations, not independent patients.',
               reference='Two same-geometry expert endpoints only; no reference curve.',
               temporal_processing={'timestamp_source':'derived_from_fps','smoothing':False,'new_samples':0,
                                    'reflection':False,'concatenation':False,'phase_replacement':False,
                                    'invalid_values':'NaN gaps, never joined across missing data',
                                    'outside_ED_ES_frames':0,'HR':None,'CO':None},
               axis_ranges={'x_s':[-.02,x_limit],'y_ml':[-20,y_limit],
                            'negative_margin':'Display padding so ED and near-zero reference markers are fully visible; no negative observations.'},
               source_image_panels='None; the matching real images are already provided in Fig.2.',
               curve_statistics=curve_statistics,excluded_frames=[],
               font_path=font,width_mm=183,height_mm=170,
               external_alignment_auditor_used=args.alignment_auditor is not None)
    print(f'Fig.4 exported to {OUT}; 4 patients/{len(source_rows)} frames; caption {len(caption.split())} words')


if __name__=='__main__':
    main()
