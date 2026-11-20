"""Audit frozen result arithmetic and all labeled test masks; never rewrite results."""
import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import numpy as np
from src.data.transforms import Transform
from src.geometry.functional import functional
from src.geometry.mask_features import main_component, mask_features
from src.geometry.volume import biplane_volume
from src.metrics.segmentation import segmentation_metrics

RUN = ROOT/'runs/camus_cuda_progress'
DATA = ROOT/'data/processed/camus'
OLD = ROOT/'reports/result_analysis/camus_cuda_progress'
OUT = ROOT/'reports/result_integrity/camus_cuda_progress_20261121'


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def read_csv(path):
    with path.open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))


def write_csv(name, rows):
    with (OUT/name).open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def finite(value):
    return value is not None and value != '' and np.isfinite(float(value))


def close(a, b):
    if a is None or a == '' or b is None or b == '':
        return (a is None or a == '') and (b is None or b == '')
    return bool(np.isclose(float(a), float(b), rtol=1e-10, atol=1e-8))


def distribution(values):
    a = np.asarray(values, dtype=float)
    assert len(a) and np.isfinite(a).all()
    q = np.percentile(a, [0, 25, 50, 75, 100])
    return dict(zip(['min', 'q1', 'median', 'q3', 'max'], map(float, q))) | {
        'n': len(a), 'mean': float(a.mean()), 'sample_sd': float(a.std(ddof=1)) if len(a)>1 else None}


def agreement(pred, ref):
    pred, ref = np.asarray(pred, float), np.asarray(ref, float)
    difference = pred-ref
    bias, sd = float(difference.mean()), float(difference.std(ddof=1))
    return {'n': len(pred), 'mae': float(np.abs(difference).mean()),
            'rmse': float(np.sqrt(np.mean(difference**2))), 'bias': bias,
            'loa_low': bias-1.96*sd, 'loa_high': bias+1.96*sd,
            'r': float(np.corrcoef(pred, ref)[0, 1])}


def axis_diagnostic(mask, features, spacing):
    """Measure the part of the actual mask beyond the inferred basal plane.

    This is a geometric consistency diagnostic, not manual landmark accuracy.
    """
    clean, _ = main_component(mask)
    points = features['landmarks_xy']
    scale = np.asarray(spacing)
    apex = np.asarray(points['apex'])*scale
    base = (np.asarray(points['base_left'])+np.asarray(points['base_right']))*scale/2
    length = np.linalg.norm(base-apex)
    direction = (base-apex)/length
    xy = np.argwhere(clean)[:, ::-1]*scale
    projection = (xy-apex)@direction
    return {'axis_length_mm': float(length),
            'full_mask_projected_span_mm': float(np.ptp(projection)),
            'proxy_axis_to_mask_span': float(length/np.ptp(projection)),
            'mask_area_beyond_proxy_base_fraction': float(np.mean(projection>length)),
            'disk_integrated_area_to_full_area': float(np.sum(features['diameters_mm'])*length/20/features['area_mm2'])}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    frozen = read_json(OLD/'analysis_manifest.json')
    issues = []
    checks = Counter()
    hashes = []
    for name, expected in frozen['sources_sha256'].items():
        actual = digest(ROOT/name)
        hashes.append({'file': name, 'expected': expected, 'actual': actual, 'matches': actual == expected})
        if actual != expected:
            issues.append({'type': 'frozen_source_changed', 'file': name})
    write_csv('frozen_source_hashes.csv', hashes)
    split = read_json(ROOT/'configs/camus_splits.json')['patients']
    test_patients = {p for p, s in split.items() if s == 'test'}
    cases = [c for c in read_json(DATA/'manifest.json')['cases'] if c['split'] == 'test']
    assert len(test_patients) == 82 and len(cases) == 164
    structures = read_csv(RUN/'structure.csv')
    frames = read_csv(RUN/'frames.csv')
    functions = read_csv(RUN/'function.csv')
    summary = read_json(RUN/'summary.json')
    structure_index = {(r['case_id'], int(r['frame'])):r for r in structures}
    frame_index = {(r['case_id'], int(r['frame'])):r for r in frames}
    assert len(structure_index) == len(structures) == 328
    assert len(frame_index) == len(frames) == 3167
    assert {r['patient_id'] for r in structures} == test_patients
    assert all(not r[k] for r in functions for k in ['HR', 'CO', 'ref_CO'])
    assert all(not r['manual_keypoint_error'] for r in structures)
    checked_frames, geometry, phase_rows, curve_rows, original_sources = [], [], [], [], []
    paired = defaultdict(lambda: defaultdict(dict))
    reported_ef = defaultdict(set)
    for number, case in enumerate(cases, 1):
        key, patient, view = case['case_id'], case['patient_id'], case['view']
        paths = [DATA/(key+'.json'), DATA/(key+'.npz'), RUN/(key+'_pred.npz')]
        original_sources.extend(paths)
        meta = read_json(paths[0])
        saved = read_json(RUN/(key+'_features.json'))['frames']
        with np.load(paths[1], allow_pickle=False) as data:
            image, labeled, truth, gt_indices = data['frames'], data['labeled'], data['original_gt'], data['original_gt_indices']
        with np.load(paths[2], allow_pickle=False) as data:
            prediction = data['masks']
        assert image.shape == prediction.shape and image.shape[1:] == (112,112)
        assert np.isin(prediction, [0,1]).all()
        assert set(gt_indices) == set(meta['phases'].values()) == set(np.flatnonzero(labeled))
        assert meta['patient_id'] == patient and split[patient] == 'test'
        assert meta['sequence_type'] == 'half_sequence'
        reported_ef[patient].add(float(meta['config']['EF']))
        tr = meta['audit']['transform']
        transform = Transform(tuple(tr['original_hw']), tuple(tr['crop_xyxy']), tuple(tr['output_hw']))
        assert np.allclose(np.array(tr['original_to_processed'])@np.array(tr['processed_to_original']), np.eye(3))
        sx, sy = meta['audit']['spacing_xy_mm']
        assert np.allclose(tr['processed_spacing_xy_mm'], [sx/transform.matrix[0,0], sy/transform.matrix[1,1]])
        assert meta['audit']['timestamp_source'] == 'derived_from_fps'
        times = np.asarray(meta['audit']['timestamps_s'])
        assert np.allclose(times, np.arange(len(image))/meta['fps'])
        sequence_volumes = []
        for index in range(len(image)):
            f, row = saved[str(index)], frame_index[(key,index)]
            for csv_key, feature_key in [('area_mm2','area_mm2'), ('long_axis_mm','long_axis_mm'), ('volume_ml','volume_ml')]:
                if not close(row[csv_key], f.get(feature_key)):
                    issues.append({'type':'frame_feature_mismatch', 'case':key, 'frame':index, 'field':csv_key})
            assert close(row['volume_ml'], row['analysis_volume_ml']) and row['temporal_filtered'] == 'False'
            assert close(row['time_s'], times[index])
            if f.get('valid'):
                expected = 8*f['area_mm2']**2/(3*np.pi*f['long_axis_mm'])/1000
                assert close(expected, f['volume_ml'])
                assert len(f['diameters_mm']) == 20 and min(f['diameters_mm']) >= 0
                assert 0 <= float(row['confidence']) <= 1
            sequence_volumes.append(float(row['analysis_volume_ml']) if finite(row['analysis_volume_ml']) else np.nan)
            checks['stored_frame_feature_and_formula'] += 1
        volumes = np.asarray(sequence_volumes)
        adjacent = np.abs(np.diff(volumes))/volumes[:-1]
        curve_rows.append({'case_id':key,'patient_id':patient,'view':view,'n_frames':len(image),
                           'invalid_frames':int(np.count_nonzero(~np.isfinite(volumes))),
                           'max_adjacent_relative_volume_change':float(np.nanmax(adjacent)),
                           'roi_reviewed':meta['audit']['roi_reviewed']})
        for phase, index in meta['phases'].items():
            gt = truth[list(gt_indices).index(index)]
            restored = transform.restore_mask(prediction[index])
            metrics = segmentation_metrics(restored, gt, [sx,sy])
            old = structure_index[(key,index)]
            for metric in ['dice','assd','hd95','hd_max']:
                if not close(metrics[metric], old[metric]):
                    issues.append({'type':'mask_metric_mismatch','case':key,'frame':index,'metric':metric})
            checked_frames.append({'case_id':key,'patient_id':patient,'view':view,'phase':phase,'frame':index,
                                   **{k:metrics[k] for k in ['dice','assd','hd95','hd_max']}})
            pred_features = mask_features(restored,[sx,sy])
            truth_features = mask_features(gt,[sx,sy])
            for k in ['area_mm2','long_axis_mm','volume_ml']:
                if not close(pred_features.get(k),saved[str(index)].get(k)):
                    issues.append({'type':'restored_geometry_mismatch','case':key,'frame':index,'metric':k})
            assert np.allclose(pred_features['diameters_mm'],saved[str(index)]['diameters_mm'])
            paired[patient][phase][view] = {'pred':pred_features,'ref':truth_features}
            for source, mask, features in [('pred',restored,pred_features),('expert',gt,truth_features)]:
                geometry.append({'case_id':key,'patient_id':patient,'view':view,'phase':phase,'source':source,
                                 'area_mm2':features['area_mm2'],'volume_ml':features['volume_ml'],
                                 **axis_diagnostic(mask,features,[sx,sy])})
            checks['labeled_mask_metrics_and_geometry'] += 1
        if number % 20 == 0:
            print(f'Checked {number}/164 view sequences',flush=True)
    assert all(len(values)==1 for values in reported_ef.values()), '2CH/4CH EF-label conflict'
    reported_ef = {p:next(iter(v)) for p,v in reported_ef.items()}
    for row in functions:
        patient,view,method=row['patient_id'],row['view'],row['method']
        if method == 'single_plane_area_length':
            pred = functional(*[paired[patient][p][view]['pred']['volume_ml'] for p in ['ED','ES']])
            ref = functional(*[paired[patient][p][view]['ref']['volume_ml'] for p in ['ED','ES']])
        elif method in ['20_disks_shorter_axis','biplane_vs_CAMUS_reported_EF']:
            values = {source:[biplane_volume(paired[patient][p]['2CH'][source],paired[patient][p]['4CH'][source])
                              for p in ['ED','ES']] for source in ['pred','ref']}
            pred,ref=functional(*values['pred']),functional(*values['ref'])
            if method == 'biplane_vs_CAMUS_reported_EF':
                ref={k:reported_ef[patient] if k=='EF' else None for k in ['EDV','ESV','SV','EF']}
        else:
            sequence = sorted([r for r in frames if r['patient_id']==patient and r['view']==view],key=lambda r:int(r['frame']))
            v=np.array([float(r['analysis_volume_ml']) if finite(r['analysis_volume_ml']) and r['valid']=='True' else np.nan for r in sequence])
            valid=np.flatnonzero(np.isfinite(v));ed=int(valid[np.argmax(v[valid])]);after=valid[valid>ed]
            assert len(after)>0
            es=int(after[np.argmin(v[after])]);assert (ed,es)==(int(row['ed_frame']),int(row['es_frame']))
            pred=functional(v[ed],v[es])
            ref=functional(*[paired[patient][p][view]['ref']['volume_ml'] for p in ['ED','ES']])
            phase_rows.append({'patient_id':patient,'view':view,'auto_ed':ed,'auto_es':es,
                                'ed_frame_error':row['ed_frame_error'],'es_frame_error':row['es_frame_error']})
        for k in ['EDV','ESV','SV','EF']:
            if not close(pred[k],row[k]) or not close(ref[k],row['ref_'+k]):
                issues.append({'type':'function_mismatch','patient_id':patient,'method':method,'view':view,'metric':k})
        checks['functional_rows_recomputed']+=1
    assert Counter((r['patient_id'],r['view']) for r in functions if r['method']=='single_plane_area_length').most_common(1)[0][1] == 1
    biplane=[r for r in functions if r['method']=='20_disks_shorter_axis']
    agreement_rows=[]
    for method in sorted({r['method'] for r in functions}):
        for view in sorted({r['view'] for r in functions if r['method']==method}):
            for metric in ['EDV','ESV','SV','EF']:
                group=[r for r in functions if r['method']==method and r['view']==view and finite(r[metric]) and finite(r['ref_'+metric])]
                if group:
                    agreement_rows.append({'method':method,'view':view,'metric':metric,'reference_scope':group[0]['reference_scope'],
                                           **agreement([float(r[metric]) for r in group],[float(r['ref_'+metric]) for r in group])})
    for old in read_csv(OLD/'source_data/agreement_statistics.csv'):
        new=next(r for r in agreement_rows if r['method']==old['method'] and r['metric']==old['metric'])
        for k in ['n','mae','bias','loa_low','loa_high']:
            assert close(new[k],old[k]),(k,new,old)
    ref_label=agreement([float(r['ref_EF']) for r in biplane],[reported_ef[r['patient_id']] for r in biplane])
    ratios=[]
    for row in biplane:
        p=row['patient_id']
        single=[r for r in functions if r['patient_id']==p and r['method']=='single_plane_area_length']
        for source,prefix in [('pred',''),('expert','ref_')]:
            for phase,metric in [('ED','EDV'),('ES','ESV')]:
                mean_single=np.mean([float(r[prefix+metric]) for r in single])
                ratios.append({'patient_id':p,'phase':phase,'source':source,'mean_single_plane_ml':float(mean_single),
                               'biplane_ml':float(row[prefix+metric]),'biplane_to_mean_single_ratio':float(row[prefix+metric])/mean_single})
    patient_metrics=[]
    for p in sorted(test_patients):
        g=[r for r in checked_frames if r['patient_id']==p]
        assert len(g)==4
        patient_metrics.append({'patient_id':p,**{k:float(np.mean([r[k] for r in g])) for k in ['dice','assd','hd95']}})
    segmentation={k:distribution([r[k] for r in patient_metrics]) for k in ['dice','assd','hd95']}
    assert close(segmentation['dice']['mean'],summary['dice_patient_mean'])
    assert close(segmentation['assd']['mean'],summary['assd_mm'])
    assert close(segmentation['hd95']['mean'],summary['hd95_mm'])
    # Normalization is reconstructed from labeled training pixels only.
    count,total,squares=0,0.,0.
    for c in read_json(DATA/'manifest.json')['cases']:
        if c['split']!='train':continue
        with np.load(DATA/(c['case_id']+'.npz'),allow_pickle=False) as data:
            pixels=data['frames'][data['labeled']].astype(float)
        count+=pixels.size;total+=pixels.sum();squares+=np.square(pixels).sum()
    mean=total/count;std=np.sqrt(squares/count-mean**2)
    assert np.allclose(summary['normalization']['mean'],mean) and np.allclose(summary['normalization']['std'],std)
    log=read_csv(ROOT/'checkpoints/camus_cuda_progress/training.csv')
    best=min(log,key=lambda r:float(r['val_bce']))
    diagnostics={}
    for source in ['expert','pred']:
        for phase in ['ED','ES']:
            group=[r for r in geometry if r['source']==source and r['phase']==phase]
            diagnostics[source+'_'+phase]={k:distribution([r[k] for r in group]) for k in [
                'proxy_axis_to_mask_span','mask_area_beyond_proxy_base_fraction','disk_integrated_area_to_full_area']}
    result={'experiment':'camus_cuda_progress','audit_scope':'All existing test results; no model change or new inference.',
            'hard_mismatch_count':len(issues),'hard_mismatches':issues,'checks':dict(checks),
            'frozen_sources':len(hashes),'frozen_source_matches':sum(r['matches'] for r in hashes),
            'test_patients':82,'test_view_sequences':164,'test_labeled_frames':328,'test_all_frames':3167,
            'segmentation_patient_distributions':segmentation,'expert_geometry_EF_vs_dataset_label':ref_label,
            'proxy_axis_diagnostics':diagnostics,
            'method_volume_ratio':{source+'_'+phase:distribution([r['biplane_to_mean_single_ratio'] for r in ratios if r['source']==source and r['phase']==phase])
                                   for source in ['expert','pred'] for phase in ['ED','ES']},
            'diagnostic_frame_dice_below_0_8':sum(r['dice']<.8 for r in checked_frames),
            'diagnostic_frame_dice_below_0_5':sum(r['dice']<.5 for r in checked_frames),
            'invalid_function_rows':[r for r in functions if not finite(r['EF'])],
            'auto_extrema_missing_cases':{view:sorted(test_patients-{r['patient_id'] for r in functions if r['method']=='single_plane_auto_extrema_'+view}) for view in ['2CH','4CH']},
            'curve_quality':{'invalid_frames':sum(r['invalid_frames'] for r in curve_rows),
                              'max_adjacent_relative_change':max(r['max_adjacent_relative_volume_change'] for r in curve_rows),
                              'cases_with_adjacent_change_above_0_2':sum(r['max_adjacent_relative_volume_change']>.2 for r in curve_rows),
                              'roi_reviewed_cases':sum(r['roi_reviewed'] for r in curve_rows),
                              'thresholds':'Display diagnostics only; not validated clinical rejection rules; no exclusions.'},
            'normalization':{'labeled_training_pixels':count,'mean':mean,'std':float(std),'matches_recorded':True},
            'training':{'best_validation_epoch':int(best['epoch']),'best_val_bce':float(best['val_bce']),
                         'last_val_bce':float(log[-1]['val_bce']),'best_train_bce':float(best['train_bce']),
                         'last_train_bce':float(log[-1]['train_bce'])},
            'sources_sha256':{p.relative_to(ROOT).as_posix():digest(p) for p in [Path(__file__),*original_sources]}}
    write_csv('recomputed_frame_metrics.csv',checked_frames)
    write_csv('geometry_diagnostics.csv',geometry)
    write_csv('function_agreement.csv',agreement_rows)
    write_csv('cross_geometry_volume_ratios.csv',ratios)
    write_csv('curve_quality.csv',curve_rows)
    write_csv('auto_phase_checks.csv',phase_rows)
    (OUT/'audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:result[k] for k in ['hard_mismatch_count','checks','frozen_source_matches','expert_geometry_EF_vs_dataset_label','auto_extrema_missing_cases','curve_quality','training']},ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
