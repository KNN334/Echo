"""实验入口回归：检查数据完整性、配置一致性、标签保留和产物保护。"""
from pathlib import Path

import numpy as np
import pytest

from src.utils.io import read_json, write_json
from src.data.prepare import prepare_split_manifests, validate_prepared
from src.utils.run import require_new_output
from src.data.transforms import Transform


@pytest.fixture
def prepared_data(tmp_path):
    """构造三个互斥患者、各两切面的处理后数据，包含原始专家标签。"""
    root = tmp_path / 'processed'
    root.mkdir()
    transform = Transform((10, 12), (0, 0, 12, 10), (8, 8)).record(None)
    split_path = tmp_path / 'splits.json'
    splits = {'patient0001': 'train', 'patient0008': 'val', 'patient0004': 'test'}
    write_json(split_path, {'patients': splits})
    cases = []
    original = np.zeros((2, 10, 12), np.uint8)
    original[:, 2:8, 3:9] = 1
    frames = np.zeros((2, 8, 8), np.uint8)
    masks = np.zeros_like(frames)
    audit = {'transform': transform, 'n_frames': 2, 'timestamps_s': None}
    for pid, split in splits.items():
        for view in ('2CH', '4CH'):
            key = f'{pid}_{view}'
            np.savez_compressed(root / (key + '.npz'), frames=frames, masks=masks,
                                labeled=np.ones(2, bool), original_gt=original,
                                original_gt_indices=np.array([0, 1]))
            write_json(root / (key + '.json'), {
                'patient_id': pid, 'view': view, 'split': split,
                'audit': audit,
            })
            cases.append({'case_id': key, 'patient_id': pid, 'view': view,
                          'split': split, 'frames': 2, 'labeled_frames': 2})
    write_json(root / 'manifest.json', {'cases': cases, 'failures': []})
    data = {'dataset': str(root), 'split_assignments': str(split_path),
            'expected_patients': 3, 'views': ['2CH', '4CH'], 'split_seed': 2026}
    for split in ('train', 'val', 'test'):
        data[f'{split}_path'] = str(root / 'splits' / f'{split}.json')
    prepare_split_manifests(data)
    return data


def test_prepared_cache_checks_contents_and_patient_coverage(prepared_data):
    """完整读取缓存并核查三个划分，不能将部分患者当作全量。"""
    summary = validate_prepared(prepared_data, check_arrays=True)
    assert summary['patients'] == 3 and summary['cases'] == 6
    assert summary['patient_splits'] == {'train': 1, 'val': 1, 'test': 1}
    with pytest.raises(ValueError, match='患者覆盖'):
        validate_prepared({**prepared_data, 'expected_patients': 500})


def test_prepared_cache_rejects_patient_split_change(prepared_data):
    """处理后数据清单不能与固定患者划分清单冲突。"""
    path = Path(prepared_data['dataset']) / 'manifest.json'
    manifest = read_json(path)
    manifest['cases'][0]['split'] = 'test'
    write_json(path, manifest)
    with pytest.raises(ValueError, match='固定患者清单'):
        validate_prepared(prepared_data)


def test_prepared_cache_rejects_lost_original_label_identity(prepared_data):
    """原始标签帧索引损坏时必须停止，而非默默测试错误参考帧。"""
    path = Path(prepared_data['dataset']) / 'patient0001_2CH.npz'
    with np.load(path) as archive:
        arrays = {key: archive[key] for key in archive.files}
    arrays['original_gt_indices'] = np.array([0, 0])
    np.savez_compressed(path, **arrays)
    with pytest.raises(ValueError, match='原始专家标签'):
        validate_prepared(prepared_data, check_arrays=True)


def test_output_directory_protects_existing_model(tmp_path):
    """再次运行训练或测试时不能覆盖旧文件；空的新目录可以使用。"""
    output = tmp_path / 'experiment'
    require_new_output(output)
    output.mkdir()
    require_new_output(output)
    model = output / 'best.pt'
    model.write_bytes(b'existing model')
    with pytest.raises(FileExistsError):
        require_new_output(output)
    assert model.read_bytes() == b'existing model'


def test_validation_accepts_a_different_dataset_view_convention(prepared_data):
    """统一处理数据接口不写死 CAMUS 的切面名和每患者两个切面。"""
    root = Path(prepared_data['dataset'])
    manifest = read_json(root / 'manifest.json')
    manifest['cases'] = manifest['cases'][::2]
    for row in manifest['cases']:
        row['view'] = 'CUSTOM_VIEW'
        path = root / (row['case_id'] + '.json')
        meta = read_json(path)
        meta['view'] = 'CUSTOM_VIEW'
        write_json(path, meta)
    write_json(root / 'manifest.json', manifest)
    prepare_split_manifests(prepared_data)
    summary = validate_prepared({**prepared_data, 'views': ['CUSTOM_VIEW']})
    assert summary['patients'] == 3 and summary['cases'] == 3
