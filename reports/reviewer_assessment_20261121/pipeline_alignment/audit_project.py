"""Read-only audit of acquired data and the approved pipeline.

Writes this audit directory and clearly marked engineering fixtures under .work.
Does not train, perform model inference, regenerate data, or update figures.
"""
import ast
from collections import Counter, defaultdict
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from src.config.loader import load_config
from src.data.prepare import validate_prepared
from src.data.transforms import Transform
from src.utils.io import read_json


def digest(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def write_json(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8')


def write_csv(path, rows):
    with path.open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def describe(values):
    return dict(min=float(np.min(values)), median=float(np.median(values)), max=float(np.max(values)))


def inventory():
    rows = []
    for group in ('src', 'scripts', 'tests', 'figures', 'style'):
        for path in sorted((ROOT/group).rglob('*.py')):
            text = path.read_text(encoding='utf-8-sig')
            tree = ast.parse(text, filename=str(path))
            definitions = [f'{node.name}:{node.lineno}' for node in ast.walk(tree)
                           if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))]
            rows.append(dict(path=path.relative_to(ROOT).as_posix(), group=group,
                             lines=len(text.splitlines()), sha256=digest(path),
                             definitions=';'.join(definitions)))
    write_csv(OUT/'code_inventory.csv', rows)
    return rows


def audit_camus(config):
    summary = validate_prepared(config['data'], check_arrays=False)
    root = ROOT/config['data']['dataset']
    manifest = read_json(root/'manifest.json')
    official = read_json(ROOT/'docs/data_sources/camus_download_manifest.json')
    expected = {f['path']: f for patient in official['patients'] for f in patient['files']}
    cases, counts, raw_checks = [], Counter(), Counter()
    patient_efs = defaultdict(list)
    values = defaultdict(list)
    for row in manifest['cases']:
        key = row['case_id']
        path = root/(key+'.npz')
        meta_path = root/(key+'.json')
        meta = read_json(meta_path)
        audit, tr = meta['audit'], meta['audit']['transform']
        transform = Transform(tuple(tr['original_hw']), tuple(tr['crop_xyxy']), tuple(tr['output_hw']))
        with np.load(path, allow_pickle=False) as archive:
            arrays = {name: archive[name] for name in archive.files}
        frames, masks, labeled = (arrays[k] for k in ('frames', 'masks', 'labeled'))
        gt, indices = arrays['original_gt'], arrays['original_gt_indices']
        n = len(frames)
        assert frames.ndim == 3 and masks.shape == frames.shape and labeled.shape == (n,), key
        assert frames.dtype == np.uint8 and labeled.dtype == np.bool_, key
        assert np.isfinite(frames).all() and np.isin(masks, [0, 1]).all() and np.isin(gt, [0, 1]).all(), key
        assert n == row['frames'] == audit['n_frames'] and int(labeled.sum()) == row['labeled_frames'] == 2, key
        assert tuple(frames.shape[1:]) == tuple(tr['output_hw']) == (112, 112), key
        assert np.array_equal(indices, np.flatnonzero(labeled)), key
        assert gt.shape == (2, *tr['original_hw']) and not masks[~labeled].any(), key
        assert np.array_equal(np.stack([transform.image(g, label=True) for g in gt]), masks[labeled]), key
        ed, es = meta['phases']['ED'], meta['phases']['ES']
        assert sorted((ed, es)) == [0, n-1] and sorted((ed, es)) == indices.tolist(), key
        assert (int(meta['config']['ED'])-1, int(meta['config']['ES'])-1) == (ed, es), key
        times = np.asarray(audit['timestamps_s'], float)
        assert times.shape == (n,) and np.isfinite(times).all() and np.all(np.diff(times) > 0), key
        assert np.allclose(times, np.arange(n)/float(meta['fps'])), key
        spacing = np.asarray(audit['spacing_xy_mm'], float)
        assert spacing.shape == (2,) and np.all(np.isfinite(spacing) & (spacing > 0)), key
        source_key = '/'.join(Path(meta['input_path']).parts[-2:])
        config_key = f'{row["patient_id"]}/Info_{row["view"]}.cfg'
        assert meta['source']['sha256'] == expected[source_key]['sha256'], key
        assert meta['source']['config_sha256'] == expected[config_key]['sha256'], key
        raw_checks['sequence_and_config_source_hash_matches'] += 1
        raw_checks['referenced_raw_sequences_present_locally'] += int((ROOT/meta['input_path']).is_file())
        counts['frames'] += n
        counts['labeled_frames'] += int(labeled.sum())
        counts['roi_reviewed'] += int(audit['roi_reviewed'])
        counts[meta['sequence_type']] += 1
        counts['ED_then_ES' if ed < es else 'ES_then_ED'] += 1
        counts['timing_'+audit['timestamp_source']] += 1
        patient_efs[row['patient_id']].append(float(meta['config']['EF']))
        for field, val in [('fps', meta['fps']), ('sequence_frames', n), ('duration_s', times[-1]-times[0]),
                           ('original_height', tr['original_hw'][0]), ('original_width', tr['original_hw'][1]),
                           ('spacing_x_mm', spacing[0]), ('spacing_y_mm', spacing[1]),
                           ('processed_spacing_x_mm', tr['processed_spacing_xy_mm'][0]),
                           ('processed_spacing_y_mm', tr['processed_spacing_xy_mm'][1])]:
            values[field].append(val)
        cases.append(dict(case_id=key, patient_id=row['patient_id'], split=row['split'], view=row['view'],
                          sequence_type=meta['sequence_type'], frames=n, labeled_frames=int(labeled.sum()),
                          ed_frame=ed, es_frame=es, fps=meta['fps'], timestamp_source=audit['timestamp_source'],
                          roi_reviewed=audit['roi_reviewed'], original_height=tr['original_hw'][0],
                          original_width=tr['original_hw'][1], array_bytes=path.stat().st_size,
                          array_sha256=digest(path), metadata_sha256=digest(meta_path)))
    assert len(patient_efs) == 500 and len(cases) == 1000
    assert set(patient_efs) == {p['patient_id'] for p in official['patients']}
    conflicts = [pid for pid, ef in patient_efs.items() if len(set(ef)) != 1]
    write_csv(OUT/'case_audit.csv', cases)
    return dict(existing_validator=summary, all_1000_arrays_decoded=True,
                original_label_resize_identity_passed=True, counts=dict(counts),
                ranges={k: describe(v) for k, v in values.items()},
                cross_view_ef_label_conflicts=conflicts, source_hash_checks=dict(raw_checks),
                cached_array_bytes=sum(r['array_bytes'] for r in cases),
                local_raw_root_exists=(ROOT/'data/raw/CAMUS').exists(),
                historical_download_manifest=dict(complete=official['complete'],
                    patients=len(official['patients']), files=len(expected), failures=official['failures']),
                remote_release_reverified=False,
                acquired_processed_dataset_directories=sorted(p.name for p in (ROOT/'data/processed').iterdir() if p.is_dir()),
                full_raw_preprocessing_reexecuted=False), cases


def engineering_probes():
    from src.data.camus.prepare import prepare_case
    from src.data.metadata import audit_metadata
    from src.engine.evaluator import evaluate
    from src.temporal.beat_detection import detect_beats

    # Synthetic fixtures are software probes only, never scientific observations.
    frames = np.zeros((2, 24, 24), np.uint8)
    frames[:, 3:15, 3:15] = 100
    frames[:, 21, 21] = 200
    first = np.zeros_like(frames)
    first[:, 5:10, 5:10] = 1
    second = first.copy()
    second[:, 20:23, 20:23] = 1
    meta = dict(patient_id='ENGINEERING_PROBE_ONLY', view='4CH')
    a, ma = prepare_case(frames, first, np.ones(2, bool), meta, {'output_hw': [24, 24]})
    b, mb = prepare_case(frames, second, np.ones(2, bool), meta, {'output_hw': [24, 24]})
    support = dict(identical_input_images=True, only_reference_labels_changed=True,
                   resulting_image_pixels_differ=int(np.count_nonzero(a['frames'] != b['frames'])),
                   first_auto_support_applied=ma['audit']['auto_support_applied'],
                   second_auto_support_applied=mb['audit']['auto_support_applied'])
    try:
        prepare_case(frames, np.zeros_like(frames), np.zeros(2, bool), meta)
    except ValueError as error:
        no_labels = dict(accepted=False, error=str(error))
    else:
        no_labels = dict(accepted=True)

    gap_t = [0., .1, .2, .9, 1., 1.1, 1.2]
    gap_v = [50., 100., 60., 40., 60., 100., 50.]
    beats = detect_beats(gap_v, gap_t, np.ones(7, bool))
    gap = dict(all_valid_flags_true=True, median_step_s=float(np.median(np.diff(gap_t))),
               largest_step_s=float(np.max(np.diff(gap_t))), accepted_beats=len(beats),
               accepted_frame_intervals=[[r['ed_frame'], r['next_ed_frame']] for r in beats])
    rate = audit_metadata(3, fps=50, source={'fps': 'container_rate_not_acquisition_verified'})
    unverified_rate = dict(timestamp_source=rate['timestamp_source'], timestamps_s=rate['timestamps_s'],
                           issues=rate['issues'], source=rate['metadata_source'])

    probe_root = ROOT/'.work/pipeline_alignment_probes'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')
    assert probe_root.resolve().is_relative_to((ROOT/'.work').resolve())
    probe_root.mkdir(parents=True, exist_ok=False)
    marker = probe_root/'NOT_MODEL_WEIGHTS.txt'
    marker.write_text('ENGINEERING PROBE. Model loader and prediction are mocked.', encoding='utf-8')
    key, pid = 'ENGINEERING_PROBE_ONLY_4CH', 'ENGINEERING_PROBE_ONLY'
    yy, xx = np.ogrid[:64, :64]
    masks = np.stack([(((xx-32)/r)**2+((yy-30)/24)**2 < 1).astype(np.uint8) for r in (17, 15, 12, 10)])
    images = masks*100
    transform = Transform((64, 64), (0, 0, 64, 64), (64, 64))
    fixture_meta = dict(audit=dict(transform=transform.record([1., 1.]), spacing_xy_mm=[1., 1.],
                                  timestamps_s=[0., .02, .04, .06], roi_reviewed=True),
                        phases={'ED': 0, 'ES': 3}, sequence_type='half_sequence', config={})

    class Source:
        cases = [dict(case_id=key, patient_id=pid, view='4CH')]

        def __init__(self, with_labels):
            self.with_labels = with_labels

        def load_case(self, case):
            data = dict(frames=images)
            if self.with_labels:
                data.update(original_gt_indices=np.array([0, 3]), original_gt=masks[[0, 3]])
            return data, fixture_meta

    reference = probe_root/'MOCK_REFERENCE_NOT_CLINICAL.json'
    write_json(reference, {pid: {'EF': 55.}})
    results = {}
    for name, with_labels in [('unlabeled', False), ('single_view_external', True)]:
        with patch('src.engine.evaluator.build_adapter', return_value=Source(with_labels)), \
             patch('src.models.build.load_checkpoint', return_value=(None, {'mean': [0.]*3, 'std': [1.]*3})), \
             patch('src.models.build.predict', return_value=masks*.98+.01) as predict_mock, \
             patch('src.visualization.report.build_report', return_value='engineering probe only'):
            summary = evaluate(probe_root/'NOT_A_REAL_MANIFEST.json', marker, probe_root/name,
                               device='cpu', adapter='prepared', references=reference)
        results[name] = dict(cases_failed=summary['cases_failed'], frames=summary['frames'],
                             function_groups=list(summary['function']), prediction_mock_calls=predict_mock.call_count,
                             failure_messages=[r['error'] for r in summary['failures']])
    return dict(scope='Synthetic software fixtures only; not study simulations, new model inference or clinical results.',
                probe_artifacts=probe_root.relative_to(ROOT).as_posix(),
                label_dependent_preprocessing=support, no_label_preparation=no_labels,
                timestamp_gap=gap, container_rate_trust=unverified_rate, evaluation=results)


def experiments(config):
    rows = []
    for root_name, pattern in [('checkpoints', '*/run.json'), ('runs', '*/summary.json')]:
        for path in sorted((ROOT/root_name).glob(pattern)):
            data = read_json(path)
            rows.append(dict(path=path.relative_to(ROOT).as_posix(), sha256=digest(path),
                             recorded_commit=data.get('git_commit'), split=data.get('split'),
                             experiment_type=data.get('experiment_type'),
                             train_patients=len(data['train_patients']) if 'train_patients' in data else None,
                             val_patients=len(data['val_patients']) if 'val_patients' in data else None,
                             patients_attempted=data.get('patients_attempted'), cases_attempted=data.get('cases_attempted'),
                             cases_failed=data.get('cases_failed'), epochs_completed=data.get('epochs_completed'),
                             best_epoch=data.get('best_epoch'), weights_sha256=data.get('weights_sha256')))
    initial = ROOT/'checkpoints/echonet_official.pt'
    expected = read_json(ROOT/'docs/data_sources/echonet_weights.json')
    assert digest(initial) == expected['sha256']
    write_csv(OUT/'experiment_inventory.csv', rows)
    return dict(current_train_output=config['train']['output'], current_test_output=config['test']['output'],
                current_test_output_has_summary=(ROOT/config['test']['output']/'summary.json').exists(),
                current_initial_weights_hash_verified=True,
                official_echonet_data_downloaded_to_data=False,
                echonet_assets_in_project='vendor source and segmentation initialization weights; no EchoNet dataset adapter or acquired video cohort',
                plot_entry_default='runs/camus_cuda_progress and checkpoints/camus_cuda_progress',
                primary_paper_source='figures/_paper_common.py fixed RUN/FROZEN paths',
                inventory_rows=len(rows))


def main():
    config = load_config()
    code = inventory()
    config_paths = sorted((ROOT/'configs').rglob('*.yaml')) + [ROOT/'configs/camus_splits.json']
    config_hashes = {p.relative_to(ROOT).as_posix(): digest(p) for p in config_paths}
    dataset, cases = audit_camus(config)
    print('Decoded and checked all 1000 CAMUS cache files.', flush=True)
    probe = engineering_probes()
    experiment = experiments(config)
    for row in code:
        assert digest(ROOT/row['path']) == row['sha256'], row['path']
    for relative, expected in config_hashes.items():
        assert digest(ROOT/relative) == expected, relative
    for row in cases:
        assert digest(ROOT/'data/processed/camus'/(row['case_id']+'.npz')) == row['array_sha256'], row['case_id']
        assert digest(ROOT/'data/processed/camus'/(row['case_id']+'.json')) == row['metadata_sha256'], row['case_id']
    review_root = OUT.parent
    locks = read_json(review_root/'reviews_lock.json')['report_sha256']
    for relative, expected in locks.items():
        assert digest(review_root/relative) == expected, relative
    packet = read_json(review_root/'packet_lock.json')
    for relative, expected in packet.items():
        assert digest(review_root/'packet'/relative) == expected, relative
    figures = read_json(review_root/'packet/manifest.json')['files']
    figure_count = 0
    for entry in figures:
        if entry['path'].startswith('figures/'):
            assert digest(ROOT/entry['path']) == entry['sha256'], entry['path']
            figure_count += 1
    report = dict(audit_utc=datetime.now(timezone.utc).isoformat(),
                  source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                  scope='Local current-code/data alignment audit with isolated engineering fixtures; no reshaping implemented.',
                  python_files_by_group=dict(Counter(r['group'] for r in code)),
                  lines_by_group={g: sum(r['lines'] for r in code if r['group'] == g) for g in {r['group'] for r in code}},
                  config_sha256=config_hashes, acquired_data=dataset, experiments=experiment,
                  engineering_probes=probe,
                  integrity=dict(all_code_and_config_files_unchanged=True,
                                 all_1000_cache_arrays_and_sidecars_unchanged=True,
                                 original_frozen_reports=len(locks), packet_files=len(packet),
                                 unchanged_original_figure_assets=figure_count),
                  not_executed=['training', 'model inference', 'new test-set evaluation', 'full raw preprocessing',
                                'new data download', 'study simulation', 'figure regeneration', 'project reshaping'])
    write_json(OUT/'audit.json', report)
    print(json.dumps(dict(data=dataset['counts'], probes=probe, integrity=report['integrity']), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
