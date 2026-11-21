"""Rebuild Supplementary Fig. 1: all frozen same-geometry SV and EF pairs."""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from style.palette import (COLORS, LINEWIDTH, MARKER_SIZE, apply_style, export_figure,
                           figure_size, panel_heading)
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from _paper_common import (Canvas, FROZEN, RUN, alignment, provenance, read_csv,
                           read_json, write_csv)

OUT = ROOT/'figures/fig_s01_sv_ef_agreement'
STEM = 'fig_s01_sv_ef_agreement'
AUDIT = ROOT/'reports/result_integrity/camus_cuda_progress_20261121'


def statistics(prediction, reference):
    difference = prediction-reference
    bias = float(difference.mean())
    sd = float(difference.std(ddof=1))
    sst = float(np.sum((reference-reference.mean())**2))
    assert len(prediction)>1 and sst>0 and np.ptp(prediction)>0
    r = float(np.corrcoef(prediction,reference)[0,1])
    return {'n':len(prediction),'mae':float(np.abs(difference).mean()),
            'rmse':float(np.sqrt(np.mean(difference**2))),'bias':bias,
            'loa_low':bias-1.96*sd,'loa_high':bias+1.96*sd,
            'pearson_r':r,'pearson_r_squared':r*r,
            'predictive_R_squared':1-float(np.sum(difference**2))/sst}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--alignment-auditor',type=Path)
    args = parser.parse_args()
    font = apply_style()
    (OUT/'source_data').mkdir(parents=True,exist_ok=True)
    split_path = ROOT/'configs/camus_splits.json'
    expected = {p for p,s in read_json(split_path)['patients'].items() if s=='test'}
    assert len(expected)==82
    source = RUN/'function.csv'
    rows = sorted([r for r in read_csv(source) if r['method']=='20_disks_shorter_axis'],
                  key=lambda r:r['patient_id'])
    assert len(rows)==len({r['patient_id'] for r in rows})==82
    assert {r['patient_id'] for r in rows}==expected
    assert all(r['reference_scope']=='same_geometry_from_expert_ED_ES_contours' and
               r['phase_selection']=='reference_ED_ES_for_segmentation_error_isolation' for r in rows)
    frozen_pairs = read_csv(FROZEN/'source_data/agreement_pairs.csv')
    frozen_stats = read_csv(FROZEN/'source_data/agreement_statistics.csv')
    audited_stats = read_csv(AUDIT/'function_agreement.csv')
    table_stats_path = ROOT/'figures/table_02_function/source_data/agreement_statistics.csv'
    table_stats = read_csv(table_stats_path)
    fig = plt.figure(figsize=figure_size(height_mm=170))
    canvas = Canvas(fig)
    canvas.text(8,164,'Expert ED/ES contours + the same 20-disk biplane geometry',color=COLORS['expert_contour'])
    scatter_axes, ba_axes, pairs, stats, ranges = [], [], [], [], []
    for col,metric in enumerate(['SV','EF']):
        unit = 'mL' if metric=='SV' else 'pp'
        value_unit = 'mL' if metric=='SV' else '%'
        display = 'SV' if metric=='SV' else 'LVEF'
        pred = np.asarray([float(r[metric]) for r in rows])
        ref = np.asarray([float(r['ref_'+metric]) for r in rows])
        assert np.isfinite(pred).all() and np.isfinite(ref).all()
        stat = statistics(pred,ref)
        old = next(s for s in frozen_stats if s['method']=='20_disks_shorter_axis' and s['metric']==metric)
        audited = next(s for s in audited_stats if s['method']=='20_disks_shorter_axis' and s['metric']==metric)
        table = next(s for s in table_stats if s['method']=='20_disks_shorter_axis' and s['metric']==metric)
        for key in ['n','mae','bias','loa_low','loa_high']:
            assert np.isclose(stat[key],float(old[key]),rtol=1e-11,atol=1e-11)
        for key in ['rmse','pearson_r','predictive_R_squared']:
            assert np.isclose(stat[key],float(table[key]),rtol=1e-11,atol=1e-11)
        assert np.isclose(stat['pearson_r'],float(audited['r']),rtol=1e-11,atol=1e-11)
        for row,p,g in zip(rows,pred,ref):
            frozen = next(s for s in frozen_pairs if s['method']=='20_disks_shorter_axis' and
                          s['metric']==metric and s['patient_id']==row['patient_id'])
            assert float(frozen['prediction'])==p and float(frozen['reference'])==g
            pairs.append({'patient_id':row['patient_id'],'metric':metric,'prediction':float(p),
                          'reference':float(g),'difference':float(p-g),'pair_mean':float((p+g)/2),
                          'value_unit':value_unit,'error_unit':unit,
                          'reference_scope':row['reference_scope'],'phase_selection':row['phase_selection']})
        stats.append({'metric':metric,'error_unit':unit,**stat})
        x = 24+89*col
        panel_heading(fig,'ab'[col],display,x-16,155)
        canvas.text(x-9,148,f"n = 82 · MAE {stat['mae']:.2f} {unit} · r = {stat['pearson_r']:.3f}")
        ax = canvas.axes(x,97,44,44)
        # The same 0-100 display scale is used in both columns; units stay distinct.
        limits = (0,100)
        assert min(pred.min(),ref.min())>=0 and max(pred.max(),ref.max())<=100
        ax.plot(limits,limits,color=COLORS['axis'],linestyle='--',linewidth=LINEWIDTH['comparison'])
        ax.scatter(ref,pred,s=MARKER_SIZE['primary']**2,color=COLORS['primary'],alpha=.75,edgecolors='none')
        ax.set(xlim=limits,ylim=limits,xticks=[0,50,100],yticks=[0,50,100],
               xlabel=f'Contour reference ({value_unit})',ylabel=f'Predicted {display} ({value_unit})')
        ax.set_aspect('equal',adjustable='box')
        scatter_axes.append(ax)
        panel_heading(fig,'cd'[col],display+' difference',x-16,81)
        canvas.text(x-9,74,f"Bias {stat['bias']:+.2f}; LOA {stat['loa_low']:.2f} to {stat['loa_high']:.2f} {unit}")
        ax = canvas.axes(x,24,44,44)
        diff,mean = pred-ref,(pred+ref)/2
        assert diff.min()>-40 and diff.max()<40 and -40<stat['loa_low']<stat['loa_high']<40
        ax.axhline(0,color=COLORS['muted'],linestyle=':',linewidth=LINEWIDTH['comparison'])
        for value,style,color in [(stat['bias'],'-',COLORS['primary']),
                                  (stat['loa_low'],'--',COLORS['axis']),
                                  (stat['loa_high'],'--',COLORS['axis'])]:
            ax.axhline(value,color=color,linestyle=style,linewidth=LINEWIDTH['comparison'])
        ax.scatter(mean,diff,s=MARKER_SIZE['primary']**2,color=COLORS['primary'],alpha=.75,edgecolors='none')
        ax.set(xlim=limits,ylim=(-40,40),xticks=[0,50,100],yticks=[-40,-20,0,20,40],
               xlabel=f'Pair mean ({value_unit})',ylabel=f'Prediction − reference ({unit})')
        ba_axes.append(ax)
        ranges.append({'metric':metric,'scatter_xy_limits':[0,100],
                       'ba_x_limits':[0,100],'ba_y_limits':[-40,40],'all_82_pairs_visible':True})
    canvas.text(8,8,'Same-geometry references are not independent clinical standards; proxy-axis coverage remains unresolved.')
    canvas.text(8,3,'All 82 patients retained per metric · LOA = bias ± 1.96 sample SD; not confidence or acceptance limits.')
    axes = scatter_axes+ba_axes
    alignment(fig,OUT,STEM,axes,list('abcd'),[['a','b'],['c','d']],[['a','c'],['b','d']],args.alignment_auditor)
    export_figure(fig,OUT/STEM)
    plt.close(fig)
    write_csv(OUT/'source_data/agreement_pairs.csv',pairs)
    write_csv(OUT/'source_data/agreement_statistics.csv',stats)
    caption = """Supplementary Figure 1 | Same-geometry biplane stroke-volume and ejection-fraction agreement.
a,b, Predicted stroke volume (SV) and left ventricular ejection fraction (LVEF) versus values derived from expert ED/ES contours using the same 20-disk biplane algorithm and shorter proxy long axis. Dashed diagonals indicate identity. Each panel includes all 82 test patients, one pair per patient; no outliers were excluded. Annotations show n, mean absolute error (MAE) and Pearson r. c,d, Corresponding Bland–Altman plots, with paired means on the horizontal axis and prediction minus contour reference on the vertical axis. Blue solid lines denote bias; dark dashed lines denote descriptive 95% limits of agreement (LOA), calculated as bias ± 1.96 times the sample standard deviation of differences. Dotted lines mark zero. LOA are not confidence intervals or clinical acceptance limits. EF errors use percentage points (pp); SV errors use mL. Both columns use matching numerical axis ranges while retaining their respective units. These contour-derived references are not independent clinical standards. The existing proxy-axis coverage mismatch remains unresolved, and these results do not establish clinical absolute-volume accuracy or wearable performance. No hypothesis tests, confidence intervals, smoothing, new inference or recalibration were introduced. CAMUS: Leclerc et al., IEEE TMI (2019), doi:10.1109/TMI.2019.2900516; CC BY-NC-SA 4.0.
"""
    assert len(caption.split())<250
    (OUT/'caption_en.md').write_text(caption,encoding='utf-8')
    provenance(OUT,[source,split_path,RUN/'summary.json',Path(__file__),table_stats_path,
                   FROZEN/'source_data/agreement_pairs.csv',FROZEN/'source_data/agreement_statistics.csv',
                   AUDIT/'function_agreement.csv',AUDIT/'report.md'],
               figure='Fig.S1',archetype='quantitative grid',
               core_conclusion='Same-geometry SV and EF retain substantial error and wide agreement limits.',
               panel_roles={'a/b':'Association for the two supplementary functional endpoints',
                            'c/d':'Signed disagreement and its limits for those same endpoints'},
               reference_figures='Hu Fig.5c / EchoPrime SI Fig.1; scatter/BA organization only, no assets copied.',
               n_patients_per_metric=82,excluded_pairs=[],axis_ranges=ranges,
               statistics='Recomputed from function.csv and verified against frozen pairs, audit and Table 2.',
               confidence_intervals=None,hypothesis_tests=None,
               geometry_status='Frozen proxy-axis range mismatch retained; no refitting or correction.',
               font_path=font,width_mm=183,height_mm=170,
               external_alignment_auditor_used=args.alignment_auditor is not None)
    print(f'Fig.S1: 82 patients/metric, {len(pairs)} pairs; caption {len(caption.split())} words; {OUT}')


if __name__=='__main__':
    main()
