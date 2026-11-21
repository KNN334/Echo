"""训练损失：单前景像素均值 BCE，与已有 CAMUS 适配基线一致。"""


def segmentation_loss(logits, target):
    """logits 与 target 都为 B×1×H×W；目标为二值专家左室标签。"""
    import torch.nn.functional as F
    return F.binary_cross_entropy_with_logits(logits, target)
