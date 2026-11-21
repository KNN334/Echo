"""Post-freeze, read-only numerical audit. No model inference or figure updates.

Run from the project root with the project Python environment. Snapshot tables
are the evidence basis. Original saved masks are read only after provenance
hashes are checked. Only this review directory receives audit outputs.
"""
import csv
import hashlib
import json
import math
import statistics as st
import subprocess
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
PACKET = OUT / 'packet'
SNAP = PACKET / 'snapshot'


def js(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def rows(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def near(a, b):
    assert math.isclose(float(a), float(b), rel_tol=1e-9, abs_tol=1e-9), (a, b)


def agreement(pred, ref):
    diff = [p-r for p, r in zip(pred, ref)]
    bias = st.fmean(diff)
    sd = st.stdev(diff)
    pm, rm = st.fmean(pred), st.fmean(ref)
    sse = sum(d*d for d in diff)
    sst = sum((r-rm)**2 for r in ref)
    r = sum((p-pm)*(q-rm) for p, q in zip(pred, ref)) / math.sqrt(
        sum((p-pm)**2 for p in pred)*sst)
    return dict(n=len(pred), mae=st.fmean(abs(d) for d in diff),
                rmse=math.sqrt(sse/len(diff)), bias=bias,
                loa_low=bias-1.96*sd, loa_high=bias+1.96*sd,
                pearson_r=r, pearson_r_squared=r*r,
                predictive_R_squared=1-sse/sst)


def main():
    review_lock = js(OUT/'reviews_lock.json')
    assert review_lock['all_reports_finalized_before_comparison']
    for name, expected in review_lock['report_sha256'].items():
        assert sha(OUT/name) == expected, name
    packet_lock = js(OUT/'packet_lock.json')
    for name, expected in packet_lock.items():
        assert sha(PACKET/name) == expected, name
    hashes = {}
    for path in sorted((SNAP/'figures').glob('*/provenance.json')):
        for name, expected in js(path)['sources_sha256'].items():
            assert name not in hashes or hashes[name] == expected, name
            hashes[name] = expected
    for name, expected in hashes.items():
        assert sha(ROOT/name) == expected, name

    results = {'scope': 'Saved-output reproduction, not retraining or new inference',
               'tolerance_absolute_and_relative': 1e-9,
               'packet_files_verified': len(packet_lock),
               'original_source_files_hash_verified': len(hashes), 'checks': {}}
    splits = js(SNAP/'configs/camus_splits.json')['patients']
    assert Counter(splits.values()) == {'train':347, 'val':71, 'test':82}
    metadata = [js(p) for p in sorted((SNAP/'data/processed/camus').glob('patient*_?CH.json'))]
    assert len(metadata) == 1000
    assert len({m['patient_id'] for m in metadata}) == 500
    assert all(m['split'] == splits[m['patient_id']] for m in metadata)
    assert all(m['sequence_type'] == 'half_sequence' for m in metadata)
    assert all(m['audit']['roi_reviewed'] is False for m in metadata)
    assert sum(m['audit']['n_frames'] for m in metadata) == 19232
    test_meta = {m['patient_id']+'_'+m['view']:m for m in metadata if m['split']=='test'}
    assert len(test_meta) == 164
    assert sum(m['audit']['n_frames'] for m in test_meta.values()) == 3167
    results['checks']['cohort'] = dict(patients=500, views=1000, frames=19232,
        split=dict(Counter(splits.values())), test_patients=82, test_sequences=164,
        test_frames=3167, roi_reviewed_count=0)
    reverse_by_split=Counter(m['split'] for m in metadata if m['phases']['ED']>m['phases']['ES'])
    assert dict(reverse_by_split)=={'train':17,'val':1,'test':3}
    results['checks']['cohort']['reverse_phase_sequences_by_split']=dict(reverse_by_split)

    # Independently restore masks using the declared nearest-neighbour convention.
    source_frames = rows(SNAP/'figures/table_s02_segmentation/source_data/frame_metrics.csv')
    original_structures = {(r['case_id'],int(r['frame'])):r for r in
                           rows(SNAP/'runs/camus_cuda_progress/structure.csv')}
    patients = defaultdict(lambda: defaultdict(list))
    by_case = defaultdict(list)
    for r in source_frames:
        by_case[r['case_id']].append(r)
    for case, group in by_case.items():
        meta = test_meta[case]
        transform = meta['audit']['transform']
        x0,y0,x1,y1 = transform['crop_xyxy']
        spacing = meta['audit']['spacing_xy_mm'][::-1]
        with np.load(ROOT/'data/processed/camus'/(case+'.npz'), allow_pickle=False) as cache:
            truth = cache['original_gt']
            indices = list(cache['original_gt_indices'])
        with np.load(ROOT/'runs/camus_cuda_progress'/(case+'_pred.npz'), allow_pickle=False) as saved:
            masks = saved['masks']
        for r in group:
            frame = int(r['frame'])
            p = np.zeros(tuple(transform['original_hw']), dtype=np.uint8)
            p[y0:y1,x0:x1] = np.asarray(Image.fromarray(masks[frame].astype('uint8')).resize(
                (x1-x0,y1-y0), Image.Resampling.NEAREST))
            p = p.astype(bool)
            g = truth[indices.index(frame)].astype(bool)
            a,b,i,u = int(p.sum()), int(g.sum()), int((p&g).sum()), int((p|g).sum())
            assert (a,b,i,u) == tuple(int(r[k]) for k in ['prediction_pixels','expert_pixels',
                                                        'intersection_pixels','union_pixels'])
            dice, iou = 2*i/(a+b), i/u
            near(dice, r['dice']); near(iou, r['iou']); near(iou, dice/(2-dice))
            ps = p & ~ndimage.binary_erosion(p)
            gs = g & ~ndimage.binary_erosion(g)
            distances = np.concatenate([ndimage.distance_transform_edt(~gs,sampling=spacing)[ps],
                                        ndimage.distance_transform_edt(~ps,sampling=spacing)[gs]])
            computed = dict(dice=dice, iou=iou, assd=float(distances.mean()),
                            hd95=float(np.percentile(distances,95)),hd_max=float(distances.max()))
            raw = original_structures[case,frame]
            for metric,value in computed.items():
                near(value,r[metric])
                if metric != 'iou': near(value,raw[metric])
                patients[r['patient_id']][metric].append(value)
    assert len(source_frames)==328 and len(patients)==82
    summary = js(SNAP/'runs/camus_cuda_progress/summary.json')
    segmentation = {}
    for metric in ['dice','iou','assd','hd95','hd_max']:
        values = [st.fmean(p[metric]) for p in patients.values()]
        segmentation[metric] = dict(mean=st.fmean(values),sample_sd=st.stdev(values))
    for metric,key in [('dice','dice_patient_mean'),('assd','assd_mm'),('hd95','hd95_mm')]:
        near(segmentation[metric]['mean'],summary[key])
    stratified=rows(SNAP/'figures/table_s02_segmentation/source_data/patient_stratum_metrics.csv')
    for row in rows(SNAP/'figures/table_s02_segmentation/source_data/stratum_statistics.csv'):
        group=[r for r in stratified if r['stratum']==row['stratum']]
        vals=[float(r[row['metric']]) for r in group]
        assert len(group)==int(row['n_patients'])==82
        near(st.fmean(vals),row['mean']); near(st.stdev(vals),row['sample_sd'])
    results['checks']['segmentation_reproduction'] = dict(labeled_frames=328,
        inferential_unit='82 patient means, four labeled frames per patient',
        restored_masks_rechecked=True, physical_distance_metrics_recomputed=True,
        metrics=segmentation, patient_stratum_rows=738, stratum_metric_summaries=45)

    functions = rows(SNAP/'runs/camus_cuda_progress/function.csv')
    fmap = {(r['patient_id'],r['method'],r['view']):r for r in functions}
    assert len(functions)==len(fmap)==490
    assert all(not r[k] for r in functions for k in ['HR','CO','ref_CO'])
    pairs = rows(SNAP/'figures/table_s01_function/source_data/agreement_pairs.csv')
    stats = rows(SNAP/'figures/table_s01_function/source_data/agreement_statistics.csv')
    pair_groups = defaultdict(list)
    for r in pairs:
        raw = fmap[r['patient_id'],r['method'],r['view']]
        near(r['prediction'],raw[r['metric']]); near(r['reference'],raw['ref_'+r['metric']])
        near(r['difference'],float(r['prediction'])-float(r['reference']))
        pair_groups[r['method'],r['view'],r['metric']].append(r)
    for row in stats:
        group = pair_groups[row['method'],row['view'],row['metric']]
        assert len({r['patient_id'] for r in group})==len(group)
        computed = agreement([float(r['prediction']) for r in group],
                             [float(r['reference']) for r in group])
        for key,value in computed.items(): near(value,row[key])
    assert len(pair_groups)==len(stats)==21 and len(pairs)==1712
    main_stats = rows(SNAP/'figures/table_02_function/source_data/agreement_statistics.csv')
    for row in main_stats:
        view='biplane'
        group=sorted(pair_groups[row['method'],view,row['metric']],key=lambda r:r['patient_id'])
        computed=agreement([float(r['prediction']) for r in group],
                           [float(r['reference']) for r in group])
        for key,value in computed.items(): near(value,row[key])
        absolute=np.abs([float(r['difference']) for r in group])
        boot=np.random.default_rng(2026).choice(absolute,(2000,len(absolute)),replace=True).mean(1)
        low,high=np.percentile(boot,[2.5,97.5])
        near(low,row['mae_ci_low']); near(high,row['mae_ci_high'])
    results['checks']['functional_reproduction'] = dict(source_rows=490,
        unique_patient_method_view_rows=490, metric_groups=21, metric_pairs=1712,
        main_metrics=main_stats,bootstrap_recomputed=dict(repetitions=2000,seed=2026,unit='patient'),
        negative_predictive_r2_retained=[{k:r[k] for k in ['method','metric','predictive_R_squared']}
                                       for r in main_stats if float(r['predictive_R_squared'])<0])

    ledger=rows(SNAP/'figures/fig_s09_output_availability/source_data/sequence_ledger.csv')
    frames=rows(SNAP/'runs/camus_cuda_progress/frames.csv')
    frame_groups=defaultdict(list)
    for r in frames:
        frame_groups[r['case_id']].append(r)
        near(r['analysis_volume_ml'],8*float(r['area_mm2'])**2/(3*math.pi*float(r['long_axis_mm']))/1000)
    orders=Counter()
    auto_count=0
    for row in ledger:
        case=row['case_id']; meta=test_meta[case]
        order='ED_to_ES' if meta['phases']['ED']<meta['phases']['ES'] else 'ES_to_ED'
        assert row['stored_phase_order']==order
        orders[order]+=1
        group=sorted(frame_groups[case],key=lambda r:int(r['frame']))
        for i,r in enumerate(group):
            assert int(r['frame'])==i
            near(r['time_s'],i/float(meta['fps']))
        volumes=[float(r['analysis_volume_ml']) for r in group]
        ed=volumes.index(max(volumes))
        available=ed<len(volumes)-1
        assert available==(row['automatic_output_available']=='True')
        if available:
            es=min(range(ed+1,len(volumes)),key=lambda i:volumes[i])
            assert (ed,es)==(int(row['automatic_ED_frame']),int(row['automatic_ES_frame']))
            auto_count+=1
    assert dict(orders)=={'ED_to_ES':161,'ES_to_ED':3} and auto_count==162
    assert len(frames)==3167 and sum(len(g)-1 for g in frame_groups.values())==3003
    unpaired=rows(SNAP/'figures/table_s01_function/source_data/unpaired_metrics.csv')
    assert len(unpaired)==10 and all(not r['prediction'] and r['reason'] for r in unpaired)
    invalid=fmap['patient0072','single_plane_area_length','2CH']
    assert float(invalid['ESV'])>float(invalid['EDV']) and not invalid['SV'] and not invalid['EF']
    results['checks']['temporal_and_nulls'] = dict(frames=3167,adjacent_pairs=3003,
        stored_order=dict(orders),auto_available=auto_count,attempted=164,
        missing_metric_records=10,hr_co_are_null=True,
        reverse_sequences=[r for r in ledger if r['stored_phase_order']=='ES_to_ED'])

    gstats=rows(SNAP/'figures/fig_s06_geometry_coverage/source_data/panel_statistics.csv')
    bias_stats=rows(SNAP/'figures/fig_s07_ef_reference_bias/source_data/agreement_statistics.csv')
    bias={r['comparison']:float(r['bias']) for r in bias_stats}
    near(bias['P_minus_G']+bias['G_minus_L'],bias['P_minus_L'])
    vertices=rows(SNAP/'figures/fig_r03_diameter_surface/source_data/observed_vertices.csv')
    heatmap=rows(SNAP/'figures/fig_r02_systolic_dynamics/source_data/frame_diameters.csv')
    assert vertices==heatmap and len(vertices)==720
    log=rows(SNAP/'checkpoints/camus_cuda_progress/training.csv')
    best=min(log,key=lambda r:float(r['val_bce']))
    assert best['epoch']=='7' and len(log)==30
    assert sha(ROOT/'checkpoints/camus_cuda_progress/best.pt')==summary['weights_sha256']
    run=js(SNAP/'checkpoints/camus_cuda_progress/run.json')
    assert set(run['train_patients'])=={p for p,s in splits.items() if s=='train'}
    assert set(run['val_patients'])=={p for p,s in splits.items() if s=='val'}
    assert set(run['test_patients'])=={p for p,s in splits.items() if s=='test'}
    results['checks']['geometry_reference_and_display'] = dict(
        geometry_diagnostics=gstats,mean_signed_bias_identity=bias,
        r2_r3_identical_measurements=720,independent_patients_in_r2_r3=2,
        intermediate_manual_contour_reference='unavailable',anatomical_point_reference='unavailable')
    results['checks']['experimental_identity'] = dict(
        evaluation_commit=summary['git_commit'],weight_sha256=summary['weights_sha256'],
        epochs=30,selected_epoch=7,selected_validation_bce=float(best['val_bce']),
        split_membership_verified=True,full_retraining_or_inference_reproduction=False,
        current_default_config_is_not_the_evaluated_experiment=True)
    prepared=js(SNAP/'docs/data_sources/prepared_provenance.json')
    legacy_preprocess=subprocess.check_output(['git','show',
        prepared['code_commit']+':cardiac/preprocess.py'],cwd=ROOT)
    support=OUT/'audit_support'
    support.mkdir(exist_ok=True)
    (support/'preprocessing_eefbd61.py').write_bytes(legacy_preprocess)
    results['checks']['preprocessing_identity'] = dict(
        commit=prepared['code_commit'],
        source_sha256=hashlib.sha256(legacy_preprocess).hexdigest(),
        source_copy='audit_support/preprocessing_eefbd61.py',
        static_inspection='Image support is computed from frames only. Labels enter crop/resize and audit counts, not image-support selection.',
        full_raw_data_preprocessing_reproduction=False,
        current_label_guard_not_attributed_to_historical_experiment=True)
    results['all_deterministic_assertions_passed']=True
    (OUT/'numeric_audit.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in results.items() if k!='checks'},indent=2))
    print('Completed saved-mask, metric, source-identity and table reproduction.')


if __name__=='__main__':
    main()
