"""集中设置随机种子和确定性选项。"""
import random
import numpy as np


def seed_everything(seed):
    """固定 Python、NumPy 和 PyTorch 的种子，不访问测试数据。"""
    import torch
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
