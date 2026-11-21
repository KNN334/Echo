"""按配置构建网络、加载兼容 EchoNet 的检查点、分批推理。"""
import numpy as np

from .deeplabv3 import deeplabv3_resnet50
from ..data.transforms import normalize


def build_model(config=None):
    """模型工厂；当前实现用户指定的单前景 DeepLabV3 基线。"""
    config = config or {'name': 'deeplabv3_resnet50'}
    if config.get('name') != 'deeplabv3_resnet50':
        raise ValueError(f'不支持的模型：{config.get("name")}')
    if config.get('in_channels', 3) != 3 or config.get('num_classes', 1) != 1:
        raise ValueError('EchoNet 基线要求 3 个输入通道和 1 个前景 logit。')
    return deeplabv3_resnet50()


def load_checkpoint(path, device='cpu', model_config=None):
    """读取可信检查点；兼容旧权重及 DataParallel 的 module. 前缀。"""
    import torch
    checkpoint = torch.load(path, map_location='cpu', weights_only=False)
    stored = checkpoint.get('model_config') if isinstance(checkpoint, dict) else None
    if stored is not None and model_config is not None and stored != model_config:
        raise ValueError('配置中的模型定义与检查点中的模型定义不一致。')
    model = build_model(model_config or stored)
    state = checkpoint.get('state_dict', checkpoint)
    model.load_state_dict({key.removeprefix('module.'): value for key, value in state.items()}, strict=True)
    return model.to(device).eval(), checkpoint


def predict(model, frames, mean, std, device, batch=16):
    """输出 T×H×W 前景概率，固定评价阈值在评估引擎中定义。"""
    import torch
    result = []
    with torch.inference_mode():
        for start in range(0, len(frames), batch):
            logits = model(normalize(frames[start:start + batch], mean, std).to(device))['out']
            result.append(logits[:, 0].sigmoid().cpu().numpy())
    return np.concatenate(result)
