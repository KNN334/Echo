"""Rebuild Table 2 from frozen patient pairs; preserve reference scopes and failures."""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import matplotlib
matplotlib.use('Agg')
import numpy as np
from style.palette import apply_style
from _paper_common import FROZEN, RUN, provenance, read_csv, read_json, write_csv
from _paper_tables import render_table, write_markdown

OUT = ROOT/'figures/table_02_function'
STEM = 'table_02_function'
AUDIT = ROOT/'reports/result_integrity/camus_cuda_progress_20261121'


def statistics(prediction, reference):
    difference = prediction-reference
    bias = float(difference.mean())
    sd = float(difference.std(ddof=1))
    denominator = float(np.sum((reference-reference.mean())**2))
    assert len(prediction)>1 and denominator>0 and np.ptp(prediction)>0
    r = float(np.corrcoef(prediction,reference)[0,1])
    return {'n':len(prediction),'mae':float(np.abs(difference).mean()),
            'rmse':float(np.sqrt(np.mean(difference**2))),'bias':bias,
            'loa_low':bias-1.96*sd,'loa_high':bias+1.96*sd,
            'pearson_r':r,'pearson_r_squared':r*r,
            'predictive_R_squared':1-float(np.sum(difference**2))/denominator}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--alignment-auditor',type=Path)
    args = parser.parse_args()
    font = apply_style()
    (OUT/'source_data').mkdir(parents=True,exist_ok=True)
    source = RUN/'function.csv'
    rows = read_csv(source)
    old_stats = read_csv(FROZEN/'source_data/agreement_statistics.csv')
    old_pairs = read_csv(FROZEN/'source_data/agreement_pairs.csv')
    audit_stats = read_csv(AUDIT/'function_agreement.csv')
    split_path = ROOT/'configs/camus_splits.json'
    expected = {p for p,s in read_json(split_path)['patients'].items() if s=='test'}
    assert len(expected)==82
    frozen = read_json(FROZEN/'analysis_manifest.json')
    assert frozen['bootstrap']=={'unit':'patient','repetitions':2000,'seed':2026}
    assert all(not r['HR'] and not r['CO'] and not r['ref_CO'] for r in rows)
    specs = [('20_disks_shorter_axis',m,'same_geometry_from_expert_ED_ES_contours')
             for m in ['EDV','ESV','SV','EF']]
    specs.append(('biplane_vs_CAMUS_reported_EF','EF','CAMUS_Info_cfg_EF'))
    stats, pairs = [], []
    for method,metric,scope in specs:
        group = sorted([r for r in rows if r['method']==method],key=lambda r:r['patient_id'])
        assert {r['patient_id'] for r in group}==expected and len(group)==82
        assert all(r['reference_scope']==scope and r[metric] and r['ref_'+metric] for r in group)
        assert all(r['phase_selection']=='reference_ED_ES_for_segmentation_error_isolation' for r in group)
        prediction = np.asarray([float(r[metric]) for r in group])
        reference = np.asarray([float(r['ref_'+metric]) for r in group])
        assert np.isfinite(prediction).all() and np.isfinite(reference).all()
        stat = statistics(prediction,reference)
        old = next(r for r in old_stats if r['method']==method and r['metric']==metric)
        audited = next(r for r in audit_stats if r['method']==method and r['metric']==metric)
        for key in ['n','mae','bias','loa_low','loa_high']:
            assert np.isclose(stat[key],float(old[key]),rtol=1e-10,atol=1e-10)
        for key in ['rmse']:
            assert np.isclose(stat[key],float(audited[key]),rtol=1e-10,atol=1e-10)
        assert np.isclose(stat['pearson_r'],float(audited['r']),rtol=1e-10,atol=1e-10)
        for row,pred,ref in zip(group,prediction,reference):
            frozen_pair = next(r for r in old_pairs if r['patient_id']==row['patient_id'] and
                               r['method']==method and r['metric']==metric)
            assert float(frozen_pair['prediction'])==pred and float(frozen_pair['reference'])==ref
            pairs.append({'patient_id':row['patient_id'],'method':method,'metric':metric,
                          'reference_scope':scope,'prediction':float(pred),'reference':float(ref),
                          'difference':float(pred-ref),'phase_selection':row['phase_selection']})
        stats.append({'method':method,'metric':metric,'reference_scope':scope,
                      'error_unit':'pp' if metric=='EF' else 'mL',**stat,
                      'mae_ci_low':float(old['mae_ci_low']),'mae_ci_high':float(old['mae_ci_high']),
                      'mae_ci_source':'Frozen 2000-resample patient bootstrap; seed 2026'})

    table_rows = [(True,['Expert contours + same biplane geometry (not an independent clinical volume standard)']+['']*7)]
    for index,s in enumerate(stats):
        if index==4:
            table_rows.append((True,['CAMUS dataset EF clinical label (Info.cfg); separate reference']+['']*7))
        metric = s['metric'] if s['metric']!='EF' else 'LVEF'
        table_rows.append((False,[metric+' ('+s['error_unit']+')',str(s['n']),
                          f"{s['mae']:.2f} [{s['mae_ci_low']:.2f}, {s['mae_ci_high']:.2f}]",
                          f"{s['rmse']:.2f}",f"{s['bias']:+.2f}",
                          f"[{s['loa_low']:.2f}, {s['loa_high']:.2f}]",
                          f"{s['pearson_r']:.3f}",f"{s['predictive_R_squared']:.3f}"]))
    notes = [
        'One pair per test patient; all 82 patients retained per row. Expert ED/ES phases; 20 disks, shorter axis.',
        'MAE intervals: frozen patient bootstrap, 2,000 resamples, seed 2026. EF errors use percentage points (pp).',
        'Bias = prediction - reference; 95% LOA = bias +/- 1.96 sample SD, not a confidence or acceptability interval.',
        'Predictive R\N{SUPERSCRIPT TWO} = 1 - SSE/SST against the reference; it is not Pearson r\N{SUPERSCRIPT TWO}. No significance tests were used.',
        'Current proxy-axis geometry has a coverage mismatch. Shared geometry is not an independent gold standard.',
        'HR/CO: null, n = 0; no complete cycle/reliable reference HR or independent CO. No patch acquisition.',
        'Single-plane and automatic-phase results have different n and remain separate for Supplementary Table 1.'
    ]
    caption = ('Table 2 | Patient-level functional agreement for the frozen CAMUS baseline.\n\n'
               'The first block compares predicted EDV, ESV, SV and LVEF with expert ED/ES contours '
               'processed using the same 20-disk biplane geometry and shorter long axis. These references '
               'are not independent clinical volume standards. The second block compares predicted '
               'LVEF separately with CAMUS Info.cfg clinical EF labels. Each row includes all 82 test '
               'patients, without outlier exclusion or imputation. MAE is reported with its previously '
               'frozen percentile 95% confidence interval from 2,000 patient bootstrap resamples '
               '(seed 2026); intervals were not recomputed or selected in this batch. RMSE, signed bias, '
               'descriptive 95% limits of agreement (LOA), Pearson r and predictive R\N{SUPERSCRIPT TWO} '
               'are calculated from the original paired values. Bias is prediction minus reference; '
               'LOA are bias +/- 1.96 times the sample standard deviation of differences, not '
               'confidence intervals or clinical acceptance limits. Predictive R\N{SUPERSCRIPT TWO} is '
               '1 - SSE/SST relative to the reference mean and differs from squared correlation. '
               'EF errors are percentage points (pp). The existing proxy-axis coverage mismatch and '
               'potential cancellation of reference and prediction biases remain unresolved. HR and '
               'CO are unavailable, not zero, because complete-cycle/reliable reference HR and '
               'independent CO evidence are absent. No hypothesis tests, recalibration, new inference '
               'or wearable-acquisition claims are made.\n')
    headers = ['Metric\n(error unit)','n','MAE\n[95% CI]','RMSE','Bias','95% LOA','Pearson\nr','Predictive\nR\N{SUPERSCRIPT TWO}']
    dimensions = render_table(OUT,STEM,'Table 2 | Functional agreement with distinct reference scopes',
                              headers,[22,8,35,15,15,31,18,27],table_rows,notes,
                              height_mm=112,row_height_mm=6.3,header_top_mm=99,
                              auditor=args.alignment_auditor)
    write_csv(OUT/'source_data/agreement_statistics.csv',stats)
    write_csv(OUT/'source_data/agreement_pairs.csv',pairs)
    unavailable = [{'metric':m,'n':0,'value':None,'reason':reason} for m,reason in [
        ('HR','No complete cardiac cycle or reliable independent reference heart rate'),
        ('CO','No complete cycle/reliable reference HR and no independent CO reference')]]
    from _paper_common import write_json
    write_json(OUT/'source_data/unavailable_metrics.json',unavailable)
    (OUT/'caption_en.md').write_text(caption,encoding='utf-8')
    write_markdown(OUT/(STEM+'.md'),caption,headers,table_rows,notes)
    provenance(OUT,[source,RUN/'summary.json',split_path,Path(__file__),ROOT/'figures/_paper_tables.py',
                    FROZEN/'source_data/agreement_statistics.csv',FROZEN/'source_data/agreement_pairs.csv',
                    AUDIT/'function_agreement.csv',AUDIT/'report.md'],
               table='Table 2',statistical_unit='One paired value per patient per metric',
               n_patients_per_row=82,n_reported_pairs=len(pairs),excluded_pairs=[],
               new_statistics='All five predictive R-squared values exported; paired point statistics rechecked.',
               mae_confidence_intervals=frozen['bootstrap'],new_confidence_intervals=False,
               predictive_R_squared_definition='1 - sum((prediction-reference)^2) / sum((reference-mean(reference))^2)',
               hypothesis_tests=None,geometry_status='Existing range mismatch retained; no correction/refitting.',
               full_function_scope='Other geometric/view/phase scopes reserved for Supplementary Table 1.',
               font_path=font,**dimensions,external_alignment_auditor_used=args.alignment_auditor is not None)
    print(f'Table 2: 5 metrics, {len(pairs)} patient-metric pairs; {OUT}')


if __name__=='__main__':
    main()
