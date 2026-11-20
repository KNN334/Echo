"""Rebuild Fig. 3: frozen biplane volumes and EF, with separate reference scopes."""
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
import numpy as np
from _paper_common import (Canvas, FROZEN, RUN, alignment, provenance, read_csv,
                           read_json, write_csv)

OUT = ROOT/'figures/fig_03_function_agreement'
STEM = 'fig_03_function_agreement'
AUDIT = ROOT/'reports/result_integrity/camus_cuda_progress_20261121'


def statistics(prediction, reference):
    """Descriptive paired statistics; predictive R² is not Pearson r squared."""
    difference = prediction-reference
    bias = float(difference.mean())
    sd = float(difference.std(ddof=1))
    sst = float(np.sum((reference-reference.mean())**2))
    assert len(prediction)>1 and sst>0 and np.ptp(prediction)>0
    r = float(np.corrcoef(prediction, reference)[0, 1])
    return {'n':len(prediction), 'mae':float(np.mean(np.abs(difference))),
            'rmse':float(np.sqrt(np.mean(difference**2))), 'bias':bias,
            'loa_low':bias-1.96*sd, 'loa_high':bias+1.96*sd,
            'pearson_r':r, 'pearson_r_squared':r*r,
            'predictive_R_squared':1-float(np.sum(difference**2))/sst}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--alignment-auditor', type=Path)
    args = parser.parse_args()
    font = apply_style()
    OUT.mkdir(exist_ok=True)
    (OUT/'source_data').mkdir(exist_ok=True)
    source = RUN/'function.csv'
    rows = read_csv(source)
    frozen_statistics = read_csv(FROZEN/'source_data/agreement_statistics.csv')
    frozen_pairs = read_csv(FROZEN/'source_data/agreement_pairs.csv')
    audit_statistics = read_csv(AUDIT/'function_agreement.csv')
    split_path = ROOT/'configs/camus_splits.json'
    expected = {p for p,s in read_json(split_path)['patients'].items() if s=='test'}
    assert len(expected)==82
    specs = [
        ('EDV', '20_disks_shorter_axis', 'same_geometry_from_expert_ED_ES_contours', 'mL', (0,220), [0,100,200]),
        ('ESV', '20_disks_shorter_axis', 'same_geometry_from_expert_ED_ES_contours', 'mL', (0,220), [0,100,200]),
        ('EF', 'biplane_vs_CAMUS_reported_EF', 'CAMUS_Info_cfg_EF', 'pp', (0,100), [0,50,100])]
    fig = plt.figure(figsize=figure_size(height_mm=170))
    canvas = Canvas(fig)
    canvas.text(8, 164, 'EDV / ESV: expert contours + the same geometry', color=COLORS['expert_contour'])
    canvas.text(132, 164, 'EF: CAMUS clinical labels', color=COLORS['clinical_label'])
    all_axes, all_pairs, all_statistics, ranges = [], [], [], []
    scatter_axes, ba_axes = [], []
    for col,(metric,method,scope,unit,limits,ticks) in enumerate(specs):
        group = sorted([r for r in rows if r['method']==method],key=lambda r:r['patient_id'])
        assert len(group)==len({r['patient_id'] for r in group})==82
        assert {r['patient_id'] for r in group}==expected
        assert all(r['reference_scope']==scope and r[metric] and r['ref_'+metric] for r in group)
        pred = np.array([float(r[metric]) for r in group])
        ref = np.array([float(r['ref_'+metric]) for r in group])
        assert np.isfinite(pred).all() and np.isfinite(ref).all()
        stat = statistics(pred,ref)
        old = next(r for r in frozen_statistics if r['method']==method and r['metric']==metric)
        verified = next(r for r in audit_statistics if r['method']==method and r['metric']==metric)
        for key in ['n','mae','bias','loa_low','loa_high']:
            assert np.isclose(stat[key],float(old[key]),atol=1e-10)
        assert np.isclose(stat['rmse'],float(verified['rmse']),atol=1e-10)
        assert np.isclose(stat['pearson_r'],float(verified['r']),atol=1e-10)
        for row,p,r in zip(group,pred,ref):
            previous = next(v for v in frozen_pairs if v['patient_id']==row['patient_id'] and
                            v['method']==method and v['metric']==metric)
            assert np.isclose(float(previous['prediction']),p) and np.isclose(float(previous['reference']),r)
            all_pairs.append({'patient_id':row['patient_id'],'method':method,'reference_scope':scope,
                              'metric':metric,'prediction':float(p),'reference':float(r),
                              'difference':float(p-r),'pair_mean':float((p+r)/2)})
        all_statistics.append({'method':method,'reference_scope':scope,'metric':metric,
                               'error_unit':unit,**stat})
        x = 16+62*col
        panel_heading(fig, 'abc'[col], 'LVEF' if metric=='EF' else metric, x-8, 155)
        canvas.text(x-1,149,f"n = {stat['n']} · MAE {stat['mae']:.2f} {unit}")
        canvas.text(x-1,144,f"r = {stat['pearson_r']:.3f}")
        ax = canvas.axes(x,101,37,37)
        ax.plot(limits,limits,linestyle='--',color=COLORS['axis'],linewidth=LINEWIDTH['comparison'],zorder=1)
        ax.scatter(ref,pred,s=MARKER_SIZE['primary']**2,color=COLORS['primary'],alpha=.75,edgecolors='none',zorder=2)
        assert min(pred.min(),ref.min())>=limits[0] and max(pred.max(),ref.max())<=limits[1]
        ax.set(xlim=limits,ylim=limits,xticks=ticks,yticks=ticks,
               xlabel='CAMUS label (%)' if metric=='EF' else 'Contour reference (mL)',
               ylabel='Predicted EF (%)' if metric=='EF' else 'Predicted '+metric+' (mL)')
        ax.set_aspect('equal',adjustable='box')
        scatter_axes.append(ax)
        panel_heading(fig, 'def'[col], 'LVEF difference' if metric=='EF' else metric+' difference',x-8,85)
        canvas.text(x-1,79,f"Bias {stat['bias']:+.2f} {unit}")
        canvas.text(x-1,74,f"LOA {stat['loa_low']:.2f} to {stat['loa_high']:.2f} {unit}")
        ax = canvas.axes(x,30,37,37)
        difference = pred-ref
        mean = (pred+ref)/2
        ax.axhline(0,color=COLORS['muted'],linestyle=':',linewidth=LINEWIDTH['comparison'],zorder=0)
        for value,linestyle,color in [(stat['bias'],'-',COLORS['primary']),
                                      (stat['loa_low'],'--',COLORS['axis']),
                                      (stat['loa_high'],'--',COLORS['axis'])]:
            ax.axhline(value,color=color,linestyle=linestyle,linewidth=LINEWIDTH['comparison'],zorder=1)
        ax.scatter(mean,difference,s=MARKER_SIZE['primary']**2,color=COLORS['primary'],alpha=.75,edgecolors='none',zorder=2)
        error_limits=(-40,40)
        assert difference.min()>error_limits[0] and difference.max()<error_limits[1]
        assert error_limits[0]<stat['loa_low']<stat['loa_high']<error_limits[1]
        ax.set(xlim=limits,ylim=error_limits,xticks=ticks,yticks=[-40,-20,0,20,40],
               xlabel='Pair mean (%)' if metric=='EF' else 'Pair mean (mL)',
               ylabel='EF difference (pp)' if metric=='EF' else 'Prediction − reference (mL)')
        ba_axes.append(ax)
        ranges.append({'metric':metric,'scatter_xy_limits':list(limits),'ba_x_limits':list(limits),
                       'ba_y_limits':list(error_limits),'all_82_pairs_visible':True})
    canvas.text(8,14,'Volumes share contour-derived geometry; no independent clinical volume standard.')
    canvas.text(8,9,'Current proxy-axis geometry has a range mismatch; small EF bias does not establish accuracy.')
    canvas.text(8,4,'All points retained · n = 82 each · LOA = bias ± 1.96 sample SD; not confidence or acceptability limits.')
    write_csv(OUT/'source_data/agreement_pairs.csv',all_pairs)
    write_csv(OUT/'source_data/agreement_statistics.csv',all_statistics)
    all_axes=scatter_axes+ba_axes
    alignment(fig,OUT,STEM,all_axes,list('abcdef'),[['a','b','c'],['d','e','f']],
              [['a','d'],['b','e'],['c','f']],args.alignment_auditor)
    export_figure(fig,OUT/STEM)
    plt.close(fig)
    caption = """Figure 3 | Biplane volume agreement and the separate CAMUS EF-label comparison for the frozen baseline.
a–c, Predicted EDV, ESV and LVEF versus their respective references; dashed diagonals indicate identity. EDV/ESV references are computed from expert ED/ES contours using the same 20-disk biplane geometry as predictions, with the shorter long axis. They are not independent clinical volume standards. LVEF is compared separately with CAMUS Info.cfg EF labels. Each panel contains all 82 test patients, one paired value per patient; no pairs or outliers were excluded. Text gives n, mean absolute error (MAE) and Pearson r. d–f, Corresponding Bland–Altman plots: the horizontal coordinate is the paired mean and the vertical coordinate is prediction minus reference. Blue solid lines show mean differences; dark dashed lines show descriptive 95% limits of agreement (LOA), calculated as bias ± 1.96 times the sample standard deviation of paired differences; dotted lines indicate zero. LOA are neither confidence intervals nor predefined clinical acceptance limits. EF errors are in percentage points (pp). Volume panels share axis ranges; each scatter has equal horizontal and vertical scales. The current contour-derived proxy-axis definition produces a geometric coverage mismatch, and opposing geometry-reference and segmentation offsets can partly cancel in EF bias. These results characterize the existing engineering baseline without establishing clinical accuracy, continuous wearable monitoring or patch acquisition. No hypothesis tests, smoothing or recalibration were applied. CAMUS: Leclerc et al., IEEE TMI (2019), doi:10.1109/TMI.2019.2900516.
"""
    assert len(caption.split())<250
    (OUT/'caption_en.md').write_text(caption,encoding='utf-8')
    provenance(OUT,[source,RUN/'summary.json',split_path,FROZEN/'source_data/agreement_pairs.csv',
                   FROZEN/'source_data/agreement_statistics.csv',AUDIT/'function_agreement.csv',
                   AUDIT/'report.md',Path(__file__)],
               figure='Fig.3',archetype='quantitative grid',
               core_conclusion='Frozen function errors must be interpreted against distinct reference scopes and an unvalidated geometry definition.',
               panel_roles={'a/b':'Same-geometry EDV/ESV association','c':'Separate dataset EF-label comparison',
                            'd/e/f':'Signed errors and wide agreement limits'},
               adaptation='Structural adaptation of scatter/BA layouts; no published figure assets copied.',
               n_patients_per_metric=82,excluded_pairs=[],axis_ranges=ranges,
               new_statistics='Paired MAE/RMSE/bias/LOA/Pearson r recomputed and checked; predictive R² and r² separately exported.',
               predictive_R_squared_definition='1 − sum((prediction-reference)^2)/sum((reference-mean(reference))^2)',
               uncertainty='Descriptive LOA only; no new confidence intervals or hypothesis tests.',
               geometry_status='Existing proxy-axis range mismatch retained; no correction, refitting or test-based recalibration.',
               font_path=font,width_mm=183,height_mm=170,
               external_alignment_auditor_used=args.alignment_auditor is not None)
    print(f'Fig.3 exported to {OUT}; n=82 each; caption {len(caption.split())} words')


if __name__=='__main__':
    main()
