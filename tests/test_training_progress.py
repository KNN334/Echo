"""训练可观测性回归：不完整末批、速度计时、日志及模型选择。"""
from datetime import datetime
import importlib.util

import numpy as np
import pytest


pytestmark = pytest.mark.skipif(importlib.util.find_spec('tqdm') is None,
                                reason='optional training progress dependency')


@pytest.mark.skipif(importlib.util.find_spec('torch') is None, reason='optional model dependency')
def test_early_stopping_still_saves_small_improvements(tmp_path):
    """早停阈值不应阻止保存实际最小验证损失，非有限损失不能写权重。"""
    import torch
    from src.engine.callbacks import BestCheckpoint
    callback = BestCheckpoint(tmp_path / 'best.pt', patience=2, min_delta=.05)
    assert not callback.update(.90, {'epoch': 1})
    assert not callback.update(.89, {'epoch': 2})
    assert callback.update(.88, {'epoch': 3})
    assert torch.load(tmp_path / 'best.pt', weights_only=True)['epoch'] == 3
    with pytest.raises(ValueError, match='非有限'):
        callback.update(float('nan'), {'epoch': 4})


def test_progress_counts_actual_samples_in_short_final_batch(monkeypatch, capsys):
    """末批仅一帧时不能按八帧计算吞吐量；日志保留当前及平均损失。"""
    from src.engine import callbacks as progress
    ticks = iter([0., 2., 3., 3.])
    monkeypatch.setattr(progress.time, 'perf_counter', lambda: next(ticks))
    with progress.BatchProgress(2, 'Epoch 1/1 Train') as bar:
        bar.update(.5, 8)
        bar.update(.1, 1)
    assert bar.samples == 9 and bar.seconds == 3 and bar.bar.n == 2
    shown = capsys.readouterr().out
    assert '100%' in shown and '2/2' in shown
    assert '3.0img/s' in shown and 'avg=0.3000' in shown


@pytest.mark.skipif(importlib.util.find_spec('torch') is None, reason='optional model dependency')
def test_training_logs_timings_preserves_selection_and_never_reads_test(tmp_path, monkeypatch, capsys):
    """两轮短训练覆盖真实优化循环、训练/验证计时与最佳权重；测试文件故意缺失。"""
    import torch
    from src.engine import trainer as model
    from src.utils.io import read_json, write_json
    from src.utils.hash import sha256
    torch.set_num_threads(2)

    class SmallSegmentation(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.layer = torch.nn.Conv2d(3, 1, 1)

        def forward(self, x):
            return {'out': self.layer(x)}

    monkeypatch.setattr(model, 'build_model', SmallSegmentation)
    root = tmp_path / 'prepared'
    root.mkdir()
    cases = []
    for split, count in (('train', 5), ('val', 3), ('test', 1)):
        cases.append({'case_id': split, 'patient_id': split, 'split': split})
        if split == 'test':
            continue
        frames = np.arange(count * 16, dtype=np.uint8).reshape(count, 4, 4)
        np.savez(root / (split + '.npz'), frames=frames, masks=(frames > 20).astype(np.uint8),
                 labeled=np.ones(count, bool))
        write_json(root / (split + '.json'), {'split': split})
    write_json(root / 'manifest.json', {'cases': cases})
    for split in ('train', 'val'):
        write_json(root / (split + '_input.json'), {
            'split': split, 'dataset_root': '.',
            'dataset_manifest_sha256': sha256(root / 'manifest.json'),
            'cases': [row for row in cases if row['split'] == split],
        })
    output = tmp_path / 'training'
    history = model.train(root / 'train_input.json', root / 'val_input.json',
                          output, epochs=2, batch=2, device='cpu')
    assert len(history) == 2
    for row in history:
        assert datetime.fromisoformat(row['started_at']).tzinfo is not None
        assert datetime.fromisoformat(row['finished_at']) >= datetime.fromisoformat(row['started_at'])
        assert row['epoch_seconds'] >= row['train_seconds'] + row['val_seconds']
        assert row['train_frames_per_second'] == pytest.approx(5 / row['train_seconds'])
        assert row['val_frames_per_second'] == pytest.approx(3 / row['val_seconds'])
    assert history[0]['estimated_remaining_seconds'] > 0
    assert history[-1]['estimated_remaining_seconds'] == 0
    checkpoint = torch.load(output / 'best.pt', weights_only=False)
    assert checkpoint['epoch'] == min(history, key=lambda r: r['val_bce'])['epoch']
    assert read_json(output / 'run.json')['train_patients'] == ['train']
    assert read_json(output / 'run.json')['val_patients'] == ['val']
    assert (output / 'training.csv').is_file()
    log = (output / 'training.log').read_text(encoding='utf-8')
    assert 'Epoch 2/2' in log and 'img/s' in log
    shown = capsys.readouterr().out
    assert 'Train' in shown and 'Val' in shown and '3/3' in shown and '2/2' in shown
