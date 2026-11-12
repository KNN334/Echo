"""重构回归：配置合并、路径独立和三阶段真实调用链。"""
from pathlib import Path
import importlib.util

import numpy as np
import pytest
import yaml

from src.config.loader import load_config
from src.utils.io import read_json, write_json


def test_yaml_components_override_and_provenance(tmp_path, monkeypatch):
    """嵌套配置保留未覆盖默认值；每个输入 YAML 都记录摘要。"""
    model = tmp_path / 'model.yaml'
    model.write_text('name: deeplabv3_resnet50\nin_channels: 3\nnum_classes: 1\n', encoding='utf-8')
    config = tmp_path / 'experiment.yaml'
    config.write_text(yaml.safe_dump({
        'defaults': [{'model': 'model.yaml'}],
        'data': {'dataset': 'data/processed/example', 'split_assignments': 'assignments.json',
                 'train_path': 'train.json', 'val_path': 'val.json', 'test_path': 'test.json',
                 'expected_patients': 3},
        'train': {'output': 'checkpoints/example', 'initial_weights': None, 'epochs': 2},
        'test': {'weights': 'checkpoints/example/best.pt', 'output': 'runs/example'},
    }), encoding='utf-8')
    monkeypatch.chdir(tmp_path)
    result = load_config(config)
    assert result['train']['epochs'] == 2 and result['train']['batch_size'] == 8
    assert result['train']['initial_weights'] is None
    assert result['model']['num_classes'] == 1
    assert set(result['_config_sources']) == {str(config), str(model)}
    assert all(len(value) == 64 for value in result['_config_sources'].values())
    assert load_config()['data']['expected_patients'] == 500


def test_yaml_defaults_reject_cycle_and_non_mapping(tmp_path):
    config = tmp_path / 'loop.yaml'
    config.write_text('defaults:\n  - model: loop.yaml\n', encoding='utf-8')
    with pytest.raises(ValueError, match='循环'):
        load_config(config)
    config.write_text('- unsupported\n', encoding='utf-8')
    with pytest.raises(ValueError, match='映射'):
        load_config(config)


@pytest.mark.skipif(importlib.util.find_spec('torch') is None, reason='optional model dependency')
def test_three_stage_scripts_from_yaml(tmp_path, monkeypatch):
    """小型网络执行优化/存取权重/几何评价，核查新配置确实被入口使用。"""
    import torch
    from scripts.prepare_data import main as prepare
    from scripts.train import main as train
    from scripts.evaluate import main as evaluate
    from src.data.transforms import Transform
    from src.engine import trainer
    from src.models import build
    from src.utils import hash as hash_utils

    class TinySegmentation(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.layer = torch.nn.Conv2d(3, 1, 1)
            torch.nn.init.constant_(self.layer.weight, .2)
            torch.nn.init.constant_(self.layer.bias, 0.)

        def forward(self, image):
            return {'out': self.layer(image)}

    monkeypatch.setattr(trainer, 'build_model', lambda config: TinySegmentation())
    monkeypatch.setattr(build, 'build_model', lambda config: TinySegmentation())
    monkeypatch.setattr(hash_utils, 'provenance', lambda: {})
    dataset = tmp_path / 'dataset'
    dataset.mkdir()
    y, x = np.ogrid[:32, :32]
    masks = np.stack([(((x - 16) / radius) ** 2 + ((y - 16) / 12) ** 2 < 1)
                      for radius in (9, 6)]).astype(np.uint8)
    transform = Transform((32, 32), (0, 0, 32, 32), (32, 32))
    cases = []
    for index, split in enumerate(('train', 'val', 'test')):
        for view in ('2CH', '4CH'):
            pid = f'patient{index:04d}'
            case_id = pid + '_' + view
            np.savez(dataset / (case_id + '.npz'), frames=masks * 200, masks=masks,
                     labeled=np.ones(2, bool), original_gt=masks, original_gt_indices=[0, 1])
            write_json(dataset / (case_id + '.json'), {
                'patient_id': pid, 'view': view, 'split': split,
                'phases': {'ED': 0, 'ES': 1}, 'sequence_type': 'half_sequence',
                'audit': {'transform': transform.record([.5, .5]), 'spacing_xy_mm': [.5, .5],
                          'timestamps_s': None, 'roi_reviewed': False, 'n_frames': 2},
            })
            cases.append({'case_id': case_id, 'patient_id': pid, 'view': view, 'split': split,
                          'frames': 2, 'labeled_frames': 2})
    write_json(dataset / 'manifest.json', {'cases': cases, 'failures': []})
    options = {
        'data': {'adapter': 'prepared', 'dataset': str(dataset), 'expected_patients': 3,
                 'split_assignments': str(tmp_path / 'assignments.json'),
                 **{name + '_path': str(dataset / 'splits' / (name + '.json'))
                    for name in ('train', 'val', 'test')}},
        'train': {'output': str(tmp_path / 'checkpoints'), 'initial_weights': None,
                  'epochs': 2, 'batch_size': 3, 'device': 'cpu', 'cpu_threads': 2},
        'test': {'weights': str(tmp_path / 'checkpoints' / 'best.pt'),
                 'output': str(tmp_path / 'results'), 'device': 'cpu', 'cpu_threads': 2},
    }
    config_path = tmp_path / 'experiment.yaml'
    config_path.write_text(yaml.safe_dump(options), encoding='utf-8')
    # 入口从任意工作目录调用；prepare 的审计也隔离到临时目录。
    monkeypatch.chdir(tmp_path)
    import scripts.prepare_data as entry
    original_path = entry.project_path
    monkeypatch.setattr(entry, 'project_path', lambda value: tmp_path / value
                        if value == 'runs/data_preparation' else original_path(value))
    assert prepare(['--config', str(config_path)])['patients'] == 3
    assert len(train(['--config', str(config_path)])) == 2
    result = evaluate(['--config', str(config_path)])
    assert result['cases_failed'] == 0 and result['dice_patient_mean'] == 1.
    assert result['beats'] == 0 and result['manual_keypoint_error'] is None
    assert result['function']['20_disks_shorter_axis']['CO']['mae'] is None
    assert (tmp_path / 'results' / 'report.html').is_file()
    snapshot = read_json(tmp_path / 'checkpoints' / 'experiment.json')
    assert snapshot['config']['data']['adapter'] == 'prepared'
    checkpoint = torch.load(tmp_path / 'checkpoints' / 'best.pt', weights_only=False)
    assert checkpoint['model_config']['name'] == 'deeplabv3_resnet50'
    assert checkpoint['run']['train_patients'] == ['patient0000']
    with pytest.raises(FileExistsError):
        train(['--config', str(config_path)])
