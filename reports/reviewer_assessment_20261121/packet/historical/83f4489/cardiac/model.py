"""模型模块：构建 EchoNet 风格单输出分割网络，加载权重、训练及推理。"""
from pathlib import Path
import random
import sys
import time
import numpy as np
from .common import read_json, write_json, write_csv, provenance, sha256
from .progress import BatchProgress, timestamp, duration


def build_model():
    """构建 EchoNet 风格的 DeepLabV3-ResNet50 单通道分割模型。"""
    import torch
    import torchvision
    model = torchvision.models.segmentation.deeplabv3_resnet50(
        weights=None, weights_backbone=None, aux_loss=False)
    # 输入为复制后的三通道灰度，输出每像素一个左室前景 logit。
    model.classifier[-1] = torch.nn.Conv2d(model.classifier[-1].in_channels, 1, kernel_size=1)
    return model


def load_checkpoint(path, device="cpu"):
    """加载检查点并兼容带 module. 前缀的参数名称。"""
    import torch
    model = build_model()
    # 官方可信权重可能含 NumPy 优化器状态；此加载方式只适用于可信检查点。
    checkpoint = torch.load(path, map_location="cpu", weights_only=False)
    state = checkpoint.get("state_dict", checkpoint)
    state = {k.removeprefix("module."): v for k, v in state.items()}
    model.load_state_dict(state, strict=True)
    model.to(device).eval()
    return model, checkpoint


def normalize(frames, mean, std):
    """将灰度帧复制为三通道并按训练集统计量标准化。"""
    import torch
    # T×H×W 转成 T×3×H×W；mean/std 均按通道广播。
    x = torch.from_numpy(frames.astype(np.float32))[:, None].repeat(1, 3, 1, 1)
    return (x - torch.tensor(mean, dtype=torch.float32)[None, :, None, None]) / torch.tensor(std, dtype=torch.float32)[None, :, None, None]


def predict(model, frames, mean, std, device, batch=16):
    """分批执行分割推理并返回每像素前景概率。"""
    import torch
    result = []
    with torch.inference_mode():
        for start in range(0, len(frames), batch):
            logits = model(normalize(frames[start:start+batch], mean, std).to(device))["out"]
            result.append(logits[:, 0].sigmoid().cpu().numpy())
    return np.concatenate(result)


def train(processed, output, epochs=30, batch=8, lr=1e-4, seed=2026, weights=None, device="cuda", max_cases=None):
    """在固定患者划分上训练 CAMUS 分割适配模型。

    processed 为预处理目录；weights 为可选初始化权重，device 选择 cpu/cuda。
    仅使用专家标注帧训练，验证集选择最佳轮次；测试数据不参与优化。
    output 保存 run.json、training.csv、best.pt，函数返回逐轮损失记录。
    """
    import torch
    from tqdm import tqdm
    started_at, started = timestamp(), time.perf_counter()

    def log(message):
        """控制台和纯文本日志使用相同时间戳，进度条不写入日志文件。"""
        line = f'[{timestamp()}] {message}'
        tqdm.write(line, file=sys.stdout)
        with (output / 'training.log').open('a', encoding='utf-8') as stream:
            stream.write(line + '\n')

    torch.manual_seed(seed)
    random.seed(seed)
    np.random.seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    root, output = Path(processed), Path(output)
    output.mkdir(parents=True, exist_ok=True)
    log(f'开始加载数据；device={device}，epochs={epochs}，batch_size={batch}。')
    entries = read_json(root / "manifest.json")["cases"]
    all_patients=set(x['patient_id'] for x in entries)
    grouped = {split: [x for x in entries if x["split"] == split] for split in ("train", "val", "test")}
    if max_cases:
        grouped = {k: v[:max_cases] for k,v in grouped.items()}
    if not grouped["train"] or not grouped["val"]:
        raise ValueError("nonempty patient-independent training and validation sets required")

    def arrays(split):
        """汇总指定数据划分中有专家标注帧的图像与掩膜数组。"""
        images, labels = [], []
        for row in tqdm(grouped[split], desc=f'Load {split}', unit='view',
                        file=sys.stdout, ascii=True, dynamic_ncols=True):
            with np.load(root / (row["case_id"] + ".npz")) as d:
                images.extend(d["frames"][d["labeled"]])
                labels.extend(d["masks"][d["labeled"]])
        return np.asarray(images), np.asarray(labels)

    tx, ty = arrays("train")
    vx, vy = arrays("val")
    if not len(tx) or not len(vx):
        raise ValueError("no annotated train/validation frames")
    log(f'数据加载完成：训练 {len(tx)} 帧，验证 {len(vx)} 帧；正在初始化模型。')
    # 均值和标准差只来自训练集，验证与测试复用这些统计量。
    mean, std = [float(tx.mean())]*3, [max(float(tx.std()), 1.)]*3
    model = load_checkpoint(weights, device)[0] if weights else build_model().to(device)
    # 本项目采用 AdamW 和均值 BCE 适配 CAMUS；上游使用 SGD 和求和 BCE，
    # 因损失尺度不同，此处学习率不能直接当作论文训练设置的严格复现。
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=0)
    run = {**provenance(), "model": "echonet_deeplabv3_resnet50_one_logit", "mean": mean, "std": std,
           "normalization_unit": "uint8_0_255", "epochs": epochs, "batch_size": batch, "lr": lr, "seed": seed,
           "optimizer": "AdamW", "loss": "mean_BCE", "BN": "frozen_running_statistics",
           "reproduction_scope": "EchoNet_architecture_CAMUS_training_adaptation_not_exact_paper_reproduction",
           "train_patients": sorted(set(x["patient_id"] for x in grouped["train"])),
           "val_patients": sorted(set(x["patient_id"] for x in grouped["val"])),
           "test_patients": sorted(set(x["patient_id"] for x in grouped["test"])),
           "input_manifest_sha256": sha256(root / "manifest.json"),
           "initial_weights_sha256": sha256(weights) if weights else None,
           "experiment_type": "smoke_training_not_final" if max_cases else
                               "partial_dataset_baseline" if len(all_patients)<500 else "baseline_training",
           "prepared_dataset_patients":len(all_patients),
           "full_500_patient_CAMUS_prepared":len(all_patients)==500,
           "torch_version": torch.__version__, "device": device,
           "started_at": started_at,
           "timing_scope": "wall_clock_including_data_loading_model_initialization_and_checkpoint_io"}
    train_views={x['case_id'] for x in grouped['train']}
    run['train_case_ids']=sorted(train_views)
    run['val_case_ids']=sorted(x['case_id'] for x in grouped['val'])
    run['test_case_ids']=sorted(x['case_id'] for x in grouped['test'])
    run['input_case_metadata_sha256']={x['case_id']:sha256(root/(x['case_id']+'.json'))
                                       for split in ('train','val') for x in grouped[split]}
    for x in ("train", "val"):
        if set(run[x + "_patients"]) & set(run["test_patients"]):
            raise ValueError("patient leakage")
    write_json(output / "run.json", run)
    log(f'模型就绪，准备耗时 {duration(time.perf_counter() - started)}。'
        '进度条 ETA 为当前阶段估计；整次训练 ETA 在首轮完成后显示。')
    history, best = [], float("inf")
    loop_started = time.perf_counter()
    for epoch in range(epochs):
        epoch_started_at, epoch_started = timestamp(), time.perf_counter()
        log(f'Epoch {epoch + 1}/{epochs} 开始。')
        model.train()
        # 小批量训练冻结 BN 的运行统计量，但仍更新其可学习的仿射参数。
        for module in model.modules():
            if isinstance(module, torch.nn.modules.batchnorm._BatchNorm):
                module.eval()
        losses = []
        order = np.random.permutation(len(tx))
        with BatchProgress((len(tx) + batch - 1) // batch, f'Epoch {epoch + 1}/{epochs} Train') as train_progress:
            for start in range(0, len(tx), batch):
                idx = order[start:start+batch]
                x = normalize(tx[idx], mean, std).to(device)
                target = torch.from_numpy(ty[idx].astype(np.float32))[:, None].to(device)
                optimizer.zero_grad(set_to_none=True)
                # 前向计算像素分类损失，再反向传播并更新参数。
                logits = model(x)["out"]
                loss = torch.nn.functional.binary_cross_entropy_with_logits(logits, target)
                loss.backward()
                optimizer.step()
                # item() 等待 CUDA 当前批计算完成，避免只统计异步任务提交时间。
                losses.append(float(loss.item()))
                train_progress.update(losses[-1], len(idx))
        model.eval()
        # 验证阶段只计算损失，不记录梯度、不更新参数。
        vloss = []
        with torch.inference_mode(), BatchProgress(
                (len(vx) + batch - 1) // batch, f'Epoch {epoch + 1}/{epochs} Val') as val_progress:
            for start in range(0, len(vx), batch):
                y = torch.from_numpy(vy[start:start+batch].astype(np.float32))[:, None].to(device)
                logits = model(normalize(vx[start:start+batch], mean, std).to(device))["out"]
                vloss.append(float(torch.nn.functional.binary_cross_entropy_with_logits(logits, y).item()))
                val_progress.update(vloss[-1], len(y))
        row = {"epoch": epoch + 1, "train_bce": float(np.mean(losses)), "val_bce": float(np.mean(vloss))}
        checkpoint_started = time.perf_counter()
        if row["val_bce"] < best:
            # 最佳模型由验证损失选择；权重同时携带归一化和运行来源信息。
            best = row["val_bce"]
            torch.save({"state_dict": model.state_dict(), "epoch": epoch+1, "mean": mean, "std": std, "run": run}, output / "best.pt")
        checkpoint_seconds = time.perf_counter() - checkpoint_started
        elapsed = time.perf_counter() - started
        remaining = (time.perf_counter() - loop_started) / (epoch + 1) * (epochs - epoch - 1)
        row.update(started_at=epoch_started_at, finished_at=timestamp(),
                   train_seconds=train_progress.seconds, val_seconds=val_progress.seconds,
                   checkpoint_seconds=checkpoint_seconds, epoch_seconds=time.perf_counter() - epoch_started,
                   total_elapsed_seconds=elapsed, estimated_remaining_seconds=remaining,
                   train_frames_per_second=len(tx) / max(train_progress.seconds, 1e-9),
                   val_frames_per_second=len(vx) / max(val_progress.seconds, 1e-9))
        history.append(row)
        write_csv(output / "training.csv", history)
        log(f'Epoch {epoch + 1}/{epochs} 完成 ({(epoch + 1) / epochs:.1%})；'
            f'train_bce={row["train_bce"]:.6f}，val_bce={row["val_bce"]:.6f}；'
            f'本轮 {duration(row["epoch_seconds"])}，累计 {duration(elapsed)}，'
            f'整次训练预计剩余 {duration(remaining)}；'
            f'训练 {row["train_frames_per_second"]:.1f} img/s。')
    log(f'训练完成，累计 {duration(time.perf_counter() - started)}；最佳验证 BCE={best:.6f}。')
    return history
