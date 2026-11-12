"""训练/验证引擎：数据集、网络、损失及回调分别由各自模块提供。"""
from pathlib import Path
import time
import numpy as np

from ..data.base import build_adapter, build_dataset
from ..models.build import build_model, load_checkpoint
from ..models.losses import segmentation_loss
from ..utils.hash import provenance, sha256
from ..utils.io import write_json, write_csv
from ..utils.seed import seed_everything
from .callbacks import BatchProgress, BestCheckpoint, TrainingLogger, timestamp, duration


def train(train_path, val_path, output, epochs=30, batch=8, lr=1e-4, seed=2026,
          weights=None, device='cuda', max_cases=None, model_config=None,
          adapter='camus', early_stopping_patience=None, min_delta=0.0):
    """只读取训练、验证清单；训练集统计归一化，验证损失选择最佳轮次。

    计时覆盖数据读取、模型初始化、优化、验证和保存。保留 best.pt、
    run.json、training.csv 和带时间戳的 training.log，不读取测试图像。
    """
    import torch
    from torch.utils.data import DataLoader

    if (isinstance(epochs, bool) or not isinstance(epochs, int) or epochs < 1 or
            isinstance(batch, bool) or not isinstance(batch, int) or batch < 1):
        raise ValueError('epochs 和 batch 必须为正整数。')
    if not np.isfinite(lr) or lr <= 0:
        raise ValueError('学习率必须为有限正数。')
    started_at, started = timestamp(), time.perf_counter()
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    log = TrainingLogger(output)
    selector = BestCheckpoint(output / 'best.pt', early_stopping_patience, min_delta)
    seed_everything(seed)

    train_adapter = build_adapter(train_path, 'train', adapter)
    val_adapter = build_adapter(val_path, 'val', adapter)
    if train_adapter.root != val_adapter.root:
        raise ValueError('训练集和验证集必须来自同一处理后数据目录。')
    train_cases, val_cases = train_adapter.cases, val_adapter.cases
    if max_cases:
        train_cases, val_cases = train_cases[:max_cases], val_cases[:max_cases]
    if not train_cases or not val_cases:
        raise ValueError('训练集和验证集均必须非空。')
    train_patients = {row['patient_id'] for row in train_cases}
    val_patients = {row['patient_id'] for row in val_cases}
    if train_patients & val_patients:
        raise ValueError('患者级划分错误：训练集和验证集存在同一患者。')

    log(f'开始加载数据；device={device}，epochs={epochs}，batch_size={batch}。')
    training = build_dataset(train_adapter, train_cases, 'Load train')
    validation = build_dataset(val_adapter, val_cases, 'Load val')
    # 只从训练帧计算统计量；验证集复用相同值。
    mean = [float(training.frames.mean())] * 3
    std = [max(float(training.frames.std()), 1.)] * 3
    training.set_normalization(mean, std)
    validation.set_normalization(mean, std)
    # num_workers=0 便于 Windows/PyCharm 首次运行，避免额外工作进程。
    train_loader = DataLoader(training, batch_size=batch, shuffle=True, num_workers=0)
    val_loader = DataLoader(validation, batch_size=batch, shuffle=False, num_workers=0)
    log(f'数据加载完成：训练 {len(training)} 帧，验证 {len(validation)} 帧；正在初始化模型。')
    if weights:
        model = load_checkpoint(weights, device, model_config)[0]
    else:
        model = (build_model(model_config) if model_config is not None else build_model()).to(device)
    # 保持既有基线的 AdamW + 均值 BCE；不是上游 SGD + 求和 BCE 的严格复现。
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=0)
    run = {
        **provenance(), 'model': 'echonet_deeplabv3_resnet50_one_logit',
        'model_config': model_config, 'adapter': adapter, 'mean': mean, 'std': std,
        'normalization_unit': 'uint8_0_255', 'epochs': epochs, 'batch_size': batch,
        'lr': lr, 'seed': seed, 'optimizer': 'AdamW', 'loss': 'mean_BCE',
        'BN': 'frozen_running_statistics',
        'reproduction_scope': 'EchoNet_architecture_CAMUS_training_adaptation_not_exact_paper_reproduction',
        'train_patients': sorted(train_patients), 'val_patients': sorted(val_patients),
        'train_val_patients': len(train_patients | val_patients),
        'train_case_ids': sorted(row['case_id'] for row in train_cases),
        'val_case_ids': sorted(row['case_id'] for row in val_cases),
        'input_manifest_sha256': sha256(train_adapter.root / 'manifest.json'),
        'train_manifest_sha256': sha256(train_path), 'val_manifest_sha256': sha256(val_path),
        'initial_weights_sha256': sha256(weights) if weights else None,
        'experiment_type': 'smoke_training_not_final' if max_cases else 'training',
        'torch_version': torch.__version__, 'device': device, 'started_at': started_at,
        'early_stopping_patience': early_stopping_patience, 'min_delta': min_delta,
        'timing_scope': 'wall_clock_including_data_loading_model_initialization_and_checkpoint_io',
    }
    run['input_case_metadata_sha256'] = {
        row['case_id']: sha256(source.root / (row['case_id'] + '.json'))
        for source, rows in ((train_adapter, train_cases), (val_adapter, val_cases)) for row in rows
    }
    write_json(output / 'run.json', run)
    log(f'模型就绪，准备耗时 {duration(time.perf_counter() - started)}。'
        '进度条 ETA 为当前阶段估计；整次训练 ETA 在首轮完成后显示。')
    history = []
    loop_started = time.perf_counter()
    for epoch in range(epochs):
        epoch_started_at, epoch_started = timestamp(), time.perf_counter()
        log(f'Epoch {epoch + 1}/{epochs} 开始。')
        model.train()
        # 小批量训练冻结 BN 运行统计量，保留其可学习参数。
        for module in model.modules():
            if isinstance(module, torch.nn.modules.batchnorm._BatchNorm):
                module.eval()
        losses = []
        with BatchProgress(len(train_loader), f'Epoch {epoch + 1}/{epochs} Train') as train_progress:
            for images, target in train_loader:
                optimizer.zero_grad(set_to_none=True)
                logits = model(images.to(device))['out']
                loss = segmentation_loss(logits, target.to(device))
                loss.backward()
                optimizer.step()
                # item() 等待本批 GPU 运算完成后计时。
                losses.append(float(loss.item()))
                train_progress.update(losses[-1], len(images))
        model.eval()
        val_losses = []
        with torch.inference_mode(), BatchProgress(
                len(val_loader), f'Epoch {epoch + 1}/{epochs} Val') as val_progress:
            for images, target in val_loader:
                logits = model(images.to(device))['out']
                val_losses.append(float(segmentation_loss(logits, target.to(device)).item()))
                val_progress.update(val_losses[-1], len(images))
        row = {'epoch': epoch + 1, 'train_bce': float(np.mean(losses)),
               'val_bce': float(np.mean(val_losses))}
        checkpoint_started = time.perf_counter()
        should_stop = selector.update(row['val_bce'], {
            'state_dict': model.state_dict(), 'epoch': epoch + 1,
            'model_config': model_config, 'mean': mean, 'std': std, 'run': run,
        })
        checkpoint_seconds = time.perf_counter() - checkpoint_started
        elapsed = time.perf_counter() - started
        remaining = (time.perf_counter() - loop_started) / (epoch + 1) * (epochs - epoch - 1)
        row.update(started_at=epoch_started_at, finished_at=timestamp(),
                   train_seconds=train_progress.seconds, val_seconds=val_progress.seconds,
                   checkpoint_seconds=checkpoint_seconds, epoch_seconds=time.perf_counter() - epoch_started,
                   total_elapsed_seconds=elapsed, estimated_remaining_seconds=remaining,
                   train_frames_per_second=len(training) / max(train_progress.seconds, 1e-9),
                   val_frames_per_second=len(validation) / max(val_progress.seconds, 1e-9))
        history.append(row)
        write_csv(output / 'training.csv', history)
        log(f'Epoch {epoch + 1}/{epochs} 完成 ({(epoch + 1) / epochs:.1%})；'
            f'train_bce={row["train_bce"]:.6f}，val_bce={row["val_bce"]:.6f}；'
            f'本轮 {duration(row["epoch_seconds"])}，累计 {duration(elapsed)}，'
            f'整次训练预计剩余 {duration(remaining)}；'
            f'训练 {row["train_frames_per_second"]:.1f} img/s。')
        if should_stop:
            log(f'验证损失连续 {selector.bad_epochs} 轮未达到改善阈值，提前停止。')
            break
    log(f'训练完成，累计 {duration(time.perf_counter() - started)}；最佳验证 BCE={selector.best:.6f}。')
    return history
