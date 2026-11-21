"""Rebuild Supplementary Fig. 7: three-way EF differences and mean-bias identity."""
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
                           read_json, write_csv, write_json)

OUT = ROOT/'figures/fig_s07_ef_reference_bias'
STEM = 'fig_s07_ef_reference_bias'
AUDIT = ROOT/'reports/result_integrity/camus_cuda_progress_20261121'


def statistics(prediction, reference):
    d = prediction-reference
    bias,sd = float(d.mean()),float(d.std(ddof=1))
    sst = float(np.sum((reference-reference.mean())**2))
    assert len(d)>1 and sst>0 and np.ptp(prediction)>0
    r = float(np.corrcoef(prediction,reference)[0,1])
    return {'n':len(d),'mae':float(np.abs(d).mean()),'rmse':float(np.sqrt(np.mean(d*d))),
            'bias':bias,'loa_low':bias-1.96*sd,'loa_high':bias+1.96*sd,
            'pearson_r':r,'pearson_r_squared':r*r,
            'predictive_R_squared':1-float(np.sum(d*d))/sst}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--alignment-auditor',type=Path)
    args = parser.parse_args()
    font = apply_style()
    (OUT/'source_data').mkdir(parents=True,exist_ok=True)
    source = RUN/'function.csv'
    rows = read_csv(source)
    grouped = {}
    for method in ['20_disks_shorter_axis','biplane_vs_CAMUS_reported_EF']:
        selected = [r for r in rows if r['method']==method]
        grouped[method] = {r['patient_id']:r for r in selected}
        assert len(selected)==len(grouped[method])==82
    split_path = ROOT/'configs/camus_splits.json'
    expected = {p for p,s in read_json(split_path)['patients'].items() if s=='test'}
    assert len(expected)==82 and all(set(group)==expected for group in grouped.values())
    ids = sorted(expected)
    biplane,label = grouped['20_disks_shorter_axis'],grouped['biplane_vs_CAMUS_reported_EF']
    assert all(biplane[p]['reference_scope']=='same_geometry_from_expert_ED_ES_contours' and
               label[p]['reference_scope']=='CAMUS_Info_cfg_EF' for p in ids)
    assert all(biplane[p]['phase_selection']==label[p]['phase_selection']==
               'reference_ED_ES_for_segmentation_error_isolation' for p in ids)
    assert all(float(biplane[p]['EF'])==float(label[p]['EF']) for p in ids)
    prediction = np.asarray([float(biplane[p]['EF']) for p in ids])
    geometry = np.asarray([float(biplane[p]['ref_EF']) for p in ids])
    clinical = np.asarray([float(label[p]['ref_EF']) for p in ids])
    assert np.isfinite(np.column_stack([prediction,geometry,clinical])).all()
    errors = np.column_stack([prediction-geometry,geometry-clinical,prediction-clinical])
    assert np.allclose(errors[:,0]+errors[:,1],errors[:,2],rtol=1e-12,atol=1e-12)
    means = errors.mean(axis=0)
    assert np.isclose(means[0]+means[1],means[2],rtol=1e-12,atol=1e-12)
    combinations = [(prediction,geometry,'P_minus_G'),(geometry,clinical,'G_minus_L'),
                    (prediction,clinical,'P_minus_L')]
    stats = [{ 'comparison':name,'error_unit':'pp',**statistics(p,r)} for p,r,name in combinations]
    audit = read_json(AUDIT/'audit.json')['expert_geometry_EF_vs_dataset_label']
    for key in ['n','mae','rmse','bias','loa_low','loa_high']:
        assert np.isclose(stats[1][key],audit[key],rtol=1e-11,atol=1e-11)
    assert np.isclose(stats[1]['pearson_r'],audit['r'],rtol=1e-11,atol=1e-11)
    frozen_pairs = read_csv(FROZEN/'source_data/agreement_pairs.csv')
    frozen_stats = read_csv(FROZEN/'source_data/agreement_statistics.csv')
    for index,method in [(0,'20_disks_shorter_axis'),(2,'biplane_vs_CAMUS_reported_EF')]:
        previous = next(r for r in frozen_stats if r['method']==method and r['metric']=='EF')
        for key in ['n','mae','bias','loa_low','loa_high']:
            assert np.isclose(stats[index][key],float(previous[key]),rtol=1e-11,atol=1e-11)
        for patient,p,r in zip(ids,combinations[index][0],combinations[index][1]):
            old = next(s for s in frozen_pairs if s['patient_id']==patient and s['method']==method and s['metric']=='EF')
            assert float(old['prediction'])==p and float(old['reference'])==r
    patient_rows = [{'patient_id':patient,'prediction_ef_percent':float(p),'expert_geometry_ef_percent':float(g),
                     'camus_label_ef_percent':float(l),'P_minus_G_pp':float(p-g),
                     'G_minus_L_pp':float(g-l),'P_minus_L_pp':float(p-l)}
                    for patient,p,g,l in zip(ids,prediction,geometry,clinical)]
    write_csv(OUT/'source_data/ef_triplets.csv',patient_rows)
    write_csv(OUT/'source_data/agreement_statistics.csv',stats)
    write_json(OUT/'source_data/bias_identity.json',{
        'n_patients':82,'definition':'(P-G)+(G-L)=P-L, per patient and for means; not a causal attribution.',
        'mean_P_minus_G_pp':float(means[0]),'mean_G_minus_L_pp':float(means[1]),
        'mean_P_minus_L_pp':float(means[2]),'identity_residual_pp':float(means[0]+means[1]-means[2]),
        'mae_additivity':False,'confidence_intervals':None,'hypothesis_tests':None})
    fig = plt.figure(figsize=figure_size(height_mm=170))
    canvas = Canvas(fig)
    canvas.text(8,166,'P: predicted EF · G: expert-contour EF (same geometry) · L: CAMUS clinical EF label')
    axes = []
    panel_heading(fig,'a','Expert geometry versus label',8,158)
    s = stats[1]
    canvas.text(15,151,f"n = 82 · MAE {s['mae']:.2f} pp · r = {s['pearson_r']:.3f}")
    ax = canvas.axes(24,101,44,44)
    assert min(geometry.min(),clinical.min())>=0 and max(geometry.max(),clinical.max())<=100
    ax.plot([0,100],[0,100],color=COLORS['axis'],linestyle='--',linewidth=LINEWIDTH['comparison'])
    ax.scatter(clinical,geometry,s=MARKER_SIZE['primary']**2,color=COLORS['expert_contour'],alpha=.8,edgecolors='none')
    ax.set(xlim=(0,100),ylim=(0,100),xticks=[0,50,100],yticks=[0,50,100],
           xlabel='CAMUS label L (%)',ylabel='Expert geometry G (%)')
    ax.set_aspect('equal',adjustable='box')
    axes.append(ax)
    panel_heading(fig,'b','Reference disagreement',97,158)
    canvas.text(104,151,f"Bias {s['bias']:+.2f}; LOA {s['loa_low']:.2f} to {s['loa_high']:.2f} pp")
    ax = canvas.axes(113,101,44,44)
    ax.axhline(0,color=COLORS['muted'],linestyle=':',linewidth=LINEWIDTH['comparison'])
    for value,style,color in [(s['bias'],'-',COLORS['expert_contour']),
                              (s['loa_low'],'--',COLORS['axis']),(s['loa_high'],'--',COLORS['axis'])]:
        ax.axhline(value,color=color,linestyle=style,linewidth=LINEWIDTH['comparison'])
    assert errors.min()>-40 and errors.max()<40
    ax.scatter((geometry+clinical)/2,errors[:,1],s=MARKER_SIZE['primary']**2,
               color=COLORS['expert_contour'],alpha=.8,edgecolors='none')
    ax.set(xlim=(0,100),ylim=(-40,40),xticks=[0,50,100],yticks=[-40,-20,0,20,40],
           xlabel='Pair mean (%)',ylabel='G − L (pp)')
    axes.append(ax)
    panel_heading(fig,'c','Within-patient signed differences',8,87)
    canvas.text(15,80,'n = 82 · each thin line joins one patient')
    ax = canvas.axes(24,30,44,44)
    # Fixed offsets depend only on sorted patient ID, never on EF or error magnitude.
    offsets = np.linspace(-.13,.13,len(ids))
    for patient_errors,offset in zip(errors,offsets):
        ax.plot(np.arange(3)+offset,patient_errors,color=COLORS['muted'],alpha=.2,
                linewidth=LINEWIDTH['comparison'],zorder=1)
    for col,color,marker in [(0,COLORS['primary'],'o'),(1,COLORS['expert_contour'],'s'),
                              (2,COLORS['primary'],'^')]:
        ax.scatter(np.full(len(ids),col)+offsets,errors[:,col],s=MARKER_SIZE['primary']**2,
                   color=color,marker=marker,alpha=.7,edgecolors='none',zorder=2)
    ax.axhline(0,color=COLORS['axis'],linestyle=':',linewidth=LINEWIDTH['comparison'],zorder=0)
    ax.set(xlim=(-.45,2.45),ylim=(-40,40),xticks=[0,1,2],xticklabels=['P − G','G − L','P − L'],
           yticks=[-40,-20,0,20,40],xlabel='Paired comparisons',ylabel='Signed EF difference (pp)')
    axes.append(ax)
    panel_heading(fig,'d','Mean-bias identity',97,87)
    canvas.text(104,80,f'{means[0]:+.2f} + {means[1]:.2f} = {means[2]:+.2f} pp; n = 82')
    ax = canvas.axes(113,30,44,44)
    starts = [0,float(means[0]),0]
    for x,value,start,color in zip(range(3),means,starts,
                                   [COLORS['primary'],COLORS['expert_contour'],COLORS['primary']]):
        ax.bar(x,value,bottom=start,width=.5,color=color,edgecolor='none',zorder=2)
        ax.annotate(f'{value:+.2f}',(x,start+value),xytext=(0,-10 if x==0 else 10),
                    textcoords='offset points',ha='center',va='top' if x==0 else 'bottom')
    ax.plot([.25,.75],[means[0],means[0]],color=COLORS['muted'],linestyle='--',linewidth=LINEWIDTH['comparison'])
    ax.plot([1.25,1.75],[means[2],means[2]],color=COLORS['muted'],linestyle='--',linewidth=LINEWIDTH['comparison'])
    ax.axhline(0,color=COLORS['axis'],linestyle=':',linewidth=LINEWIDTH['comparison'],zorder=0)
    ax.set(xlim=(-.45,2.45),ylim=(-40,40),xticks=[0,1,2],xticklabels=['P − G','G − L','P − L'],
           yticks=[-40,-20,0,20,40],xlabel='Signed components and total',ylabel='Mean bias (pp)')
    axes.append(ax)
    canvas.text(8,14,'Opposing signed biases can cancel; individual errors remain wide. MAE values cannot be added.')
    canvas.text(8,9,'G is a same-geometry reference, not an independent clinical volume standard; coverage mismatch remains.')
    canvas.text(8,4,'All 82 patients retained · descriptive post hoc analysis · no refitting, clinical acceptance test or patch acquisition.')
    alignment(fig,OUT,STEM,axes,list('abcd'),[['a','b'],['c','d']],[['a','c'],['b','d']],args.alignment_auditor)
    export_figure(fig,OUT/STEM)
    plt.close(fig)
    caption = """Supplementary Figure 7 | Distinct EF references and cancellation of opposing signed biases.
P denotes predicted LVEF, G denotes LVEF derived from expert ED/ES contours using the same 20-disk biplane geometry and shorter proxy axis, and L denotes the CAMUS Info.cfg clinical EF label. All analyses retain the same 82 test patients. a, G versus L; the dashed diagonal marks identity. b, Corresponding Bland–Altman plot: the solid purple line marks bias and dark dashed lines mark descriptive 95% limits of agreement (LOA = bias ± 1.96 sample standard deviations); the dotted line marks zero. LOA are not confidence intervals or acceptance limits. c, Three signed differences for each patient, connected by thin grey lines. Fixed horizontal offsets follow patient-ID order and do not alter values. Blue circles/triangles represent P−G/P−L; purple squares represent G−L. d, Floating bars show the exact mean-bias identity: −5.81 + 7.37 = +1.56 percentage points (pp). This is an algebraic decomposition of observed signed means, not a causal attribution or an uncertainty interval; MAEs are not additive. Panels b–d share the same difference-axis range. Small mean bias therefore coexists with substantial individual disagreement. G is not an independent clinical volume standard, and the existing proxy-axis coverage mismatch remains unresolved. This descriptive post hoc analysis uses no exclusions, tests, confidence intervals, new inference or recalibration and makes no wearable-acquisition claim. CAMUS: Leclerc et al., IEEE TMI (2019), doi:10.1109/TMI.2019.2900516; CC BY-NC-SA 4.0.
"""
    assert len(caption.split())<250
    (OUT/'caption_en.md').write_text(caption,encoding='utf-8')
    provenance(OUT,[source,split_path,Path(__file__),RUN/'summary.json',AUDIT/'audit.json',AUDIT/'report.md',
                   FROZEN/'source_data/agreement_pairs.csv',FROZEN/'source_data/agreement_statistics.csv'],
               figure='Fig.S7',archetype='quantitative grid',
               core_conclusion='Opposing observed signed biases partly cancel; small total bias does not establish individual accuracy.',
               panel_roles={'a':'The two references have a systematic offset','b':'Its sign and spread',
                            'c':'Patient-level paired differences','d':'Exact identity of the three observed means'},
               reference_figures='Ouyang Fig.2a / Hu Fig.5c for agreement layout only; three-way diagnostic is original.',
               n_patients=82,excluded_patients=[],horizontal_offsets='Fixed patient-ID order, ±0.13 category units.',
               axis_ranges={'scatter_xy':[0,100],'all_difference_y':[-40,40]},
               inference='Descriptive post hoc; no causal attribution, hypothesis tests, new confidence intervals or refitting.',
               uncertainty_exemption='Panel d illustrates an algebraic identity of observed means, not a population estimate with new inference; panel c shows all patient values.',
               geometry_status='Frozen proxy-axis coverage mismatch retained.',
               font_path=font,width_mm=183,height_mm=170,
               external_alignment_auditor_used=args.alignment_auditor is not None)
    print(f'Fig.S7: {len(ids)} complete triplets; caption {len(caption.split())} words; {OUT}')


if __name__=='__main__':
    main()
