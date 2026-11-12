"""训练进度展示：本地时间戳、批次进度、耗时、速度和阶段剩余时间。"""
from datetime import datetime
import sys
import time
from pathlib import Path


class TrainingLogger:
    """控制台和日志文件使用同一时间戳，进度条仅显示在控制台。"""

    def __init__(self, output):
        self.path = Path(output) / 'training.log'

    def __call__(self, message):
        from tqdm import tqdm
        line = f'[{timestamp()}] {message}'
        tqdm.write(line, file=sys.stdout)
        with self.path.open('a', encoding='utf-8') as stream:
            stream.write(line + '\n')


class BestCheckpoint:
    """仅根据验证损失保存最佳模型，并可选择在无改善时提前停止。"""

    def __init__(self, path, patience=None, min_delta=0.0):
        if patience is not None and (isinstance(patience, bool) or not isinstance(patience, int) or patience < 1):
            raise ValueError('early_stopping_patience 必须为正整数或 null。')
        if not 0 <= min_delta < float('inf'):
            raise ValueError('min_delta 必须为有限非负数。')
        self.path, self.patience, self.min_delta = Path(path), patience, min_delta
        self.best = self.reference = float('inf')
        self.bad_epochs = 0

    def update(self, validation_loss, checkpoint):
        import math
        import torch
        if not math.isfinite(validation_loss):
            raise ValueError('验证损失非有限值，停止训练。')
        # 无论是否开启早停，最佳权重始终对应最小验证损失。
        if validation_loss < self.best:
            torch.save(checkpoint, self.path)
            self.best = validation_loss
        if validation_loss < self.reference - self.min_delta:
            self.reference, self.bad_epochs = validation_loss, 0
        else:
            self.bad_epochs += 1
        return self.patience is not None and self.bad_epochs >= self.patience


def timestamp():
    """使用含时区的本地时间，便于对应 PyCharm 输出和实验记录。"""
    return datetime.now().astimezone().isoformat(timespec='seconds')


def duration(seconds):
    """将耗时转为时分秒；尚无观测时明确表示仍在估计。"""
    if seconds is None:
        return 'estimating'
    seconds = max(0, round(seconds))
    return f'{seconds // 3600:02d}:{seconds // 60 % 60:02d}:{seconds % 60:02d}'


class BatchProgress:
    """一轮中的训练或验证进度；实际样本数用于计算含末批的处理速度。"""

    def __init__(self, total, description):
        from tqdm import tqdm
        self.started = self.last_batch = time.perf_counter()
        self.samples = self.batches = 0
        self.loss_sum = 0.0
        self.seconds = 0.0
        self.bar = tqdm(total=total, desc=description, unit='batch', file=sys.stdout,
                        ascii=True, dynamic_ncols=True, mininterval=.5,
                        bar_format='{desc} {percentage:3.0f}%|{bar:16}| {n_fmt}/{total_fmt} '
                                   '[{elapsed}<{remaining}, {rate_fmt}] {postfix}')

    def update(self, loss, samples):
        """在本批计算完成后更新；GPU 调用方应先完成同步或读取 loss.item()。"""
        now = time.perf_counter()
        batch_seconds = now - self.last_batch
        self.seconds = now - self.started
        self.samples += samples
        self.batches += 1
        self.loss_sum += loss
        self.bar.set_postfix_str(
            f'{datetime.now().astimezone():%H:%M:%S} loss={loss:.4f} '
            f'avg={self.loss_sum / self.batches:.4f} '
            f'{batch_seconds:.3f}s/batch {self.samples / max(self.seconds, 1e-9):.1f}img/s',
            refresh=False)
        self.bar.update(1)
        self.last_batch = now

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.seconds = time.perf_counter() - self.started
        self.bar.close()
