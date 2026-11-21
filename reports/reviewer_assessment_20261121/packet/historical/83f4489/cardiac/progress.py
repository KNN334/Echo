"""训练进度展示：本地时间戳、批次进度、耗时、速度和阶段剩余时间。"""
from datetime import datetime
import sys
import time


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
