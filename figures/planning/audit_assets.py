"""Read existing CAMUS artifacts without training, inference, or metric selection."""
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def extent(values):
    return {'min': min(values), 'median': float(np.median(values)), 'max': max(values)}


def main():
    prepared = ROOT / 'data/processed/camus'
    cases = read_json(prepared / 'manifest.json')['cases']
    metadata = []
    split_patients = {}
    total_frames = 0
    labeled_frames = 0
    array_failures = []
    for case in cases:
        case_id = case['case_id']
        meta = read_json(prepared / (case_id + '.json'))
        metadata.append(meta)
        split_patients.setdefault(meta['split'], set()).add(meta['patient_id'])
        try:
            with np.load(prepared / (case_id + '.npz'), allow_pickle=False) as arrays:
                frames, masks, labeled = (arrays[k] for k in ('frames', 'masks', 'labeled'))
                assert frames.shape == masks.shape == (meta['audit']['n_frames'], 112, 112)
                assert frames.dtype == np.uint8
                assert labeled.shape == (len(frames),)
                assert int(labeled.sum()) == 2
                assert arrays['original_gt'].shape == (2, *meta['audit']['transform']['original_hw'])
                assert set(arrays['original_gt_indices'].tolist()) == set(meta['phases'].values())
                total_frames += len(frames)
                labeled_frames += int(labeled.sum())
        except (OSError, ValueError, KeyError, AssertionError) as error:
            array_failures.append({'case_id': case_id, 'error': repr(error)})
    overlaps = {a + '_' + b: sorted(split_patients[a] & split_patients[b])
                for a, b in [('train', 'val'), ('train', 'test'), ('val', 'test')]}
    main_run = ROOT / 'runs/camus_cuda_progress'
    frozen = read_json(ROOT / 'reports/result_analysis/camus_cuda_progress/analysis_manifest.json')
    frozen_checks = {path: sha256(ROOT / path) == expected
                     for path, expected in frozen['sources_sha256'].items()}
    predictions = sorted(main_run.glob('*_pred.npz'))
    prediction_failures = []
    for path in predictions:
        case_id = path.name.removesuffix('_pred.npz')
        meta = read_json(prepared / (case_id + '.json'))
        with np.load(path, allow_pickle=False) as arrays:
            if arrays['masks'].shape != (meta['audit']['n_frames'], 112, 112):
                prediction_failures.append(case_id)
    runs = []
    for path in sorted((ROOT / 'runs').glob('*/summary.json')):
        summary = read_json(path)
        if 'function' not in summary:
            continue
        runs.append({'path': path.relative_to(ROOT).as_posix(),
                     'sha256': sha256(path), 'summary': summary})
    tables = []
    for name in ['frames', 'structure', 'function', 'beats']:
        path = main_run / (name + '.csv')
        with path.open(encoding='utf-8-sig', newline='') as stream:
            reader = csv.DictReader(stream)
            rows = list(reader)
            tables.append({'path': path.relative_to(ROOT).as_posix(), 'rows': len(rows),
                           'columns': reader.fieldnames, 'sha256': sha256(path)})
    raw_manifest = read_json(ROOT / 'docs/data_sources/camus_download_manifest.json')
    result = {
        'audit_date_local': '2026-11-20',
        'scope': 'read_only_local_inventory_not_new_clinical_validation',
        'raw_data': {'local_raw_directory_exists': (ROOT / 'data/raw').exists(),
                     'historical_download_complete_flag': raw_manifest['complete'],
                     'historical_manifest_patients': len(raw_manifest['patients']),
                     'historical_manifest_files': sum(len(p['files']) for p in raw_manifest['patients']),
                     'remote_release_reverified': False},
        'prepared': {
            'manifest_cases': len(cases), 'decoded_array_files': len(cases) - len(array_failures),
            'failures': array_failures, 'total_frames': total_frames, 'expert_labeled_frames': labeled_frames,
            'patients_by_split': {k: len(v) for k, v in split_patients.items()},
            'patient_split_overlaps': overlaps,
            'sequence_types': dict(Counter(m['sequence_type'] for m in metadata)),
            'roi_reviewed': dict(Counter(str(m['audit']['roi_reviewed']) for m in metadata)),
            'quality_by_view': dict(Counter(m['config']['ImageQuality'] for m in metadata)),
            'frames_per_sequence': extent([m['audit']['n_frames'] for m in metadata]),
            'original_height_px': extent([m['audit']['transform']['original_hw'][0] for m in metadata]),
            'original_width_px': extent([m['audit']['transform']['original_hw'][1] for m in metadata]),
            'original_spacing_mm': extent([s for m in metadata for s in m['spacing_xy_mm']]),
            'processed_spacing_x_mm': extent([m['audit']['transform']['processed_spacing_xy_mm'][0] for m in metadata]),
            'processed_spacing_y_mm': extent([m['audit']['transform']['processed_spacing_xy_mm'][1] for m in metadata]),
            'fps': extent([m['fps'] for m in metadata]),
            'timestamp_sources': dict(Counter(m['audit']['timestamp_source'] for m in metadata)),
            'duration_s': extent([m['audit']['timestamps_s'][-1] - m['audit']['timestamps_s'][0] for m in metadata])},
        'main_frozen_experiment': {'name': 'camus_cuda_progress',
                                   'source_sha256_match': frozen_checks,
                                   'prediction_files': len(predictions),
                                   'prediction_shape_failures': prediction_failures,
                                   'tables': tables},
        'existing_evaluations': runs,
        'latest_training_has_test_output': (ROOT / 'runs/camus_regularized_v2').exists(),
        'new_training_or_evaluation_executed': False,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'asset_inventory.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'prepared_cases': len(cases), 'array_failures': len(array_failures),
                      'frozen_sources': len(frozen_checks), 'hash_mismatches': sum(not v for v in frozen_checks.values()),
                      'prediction_files': len(predictions), 'split_overlaps': overlaps}, ensure_ascii=False))
    if array_failures or prediction_failures or not all(frozen_checks.values()) or any(overlaps.values()):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
