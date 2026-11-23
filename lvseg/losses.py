"""Sparse-label segmentation and auxiliary boundary objectives."""

import torch
from torch.nn import functional as F

from .train import _loss


def sobel(image):
    kernel = image.new_tensor([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]]) / 8
    kernels = torch.stack((kernel, kernel.T))[:, None]
    return F.conv2d(F.pad(image, (1, 1, 1, 1), mode="replicate"), kernels)


def segmentation_boundary_loss(logits, target, edge_logits=None, *, edge_weight=0.1,
                               sobel_weight=0.1):
    segmentation = _loss(logits, target)
    if edge_logits is None:
        return segmentation, {"segmentation": segmentation.detach()}
    target_gradient = sobel(target)
    edge_target = (target_gradient.abs().sum(dim=1, keepdim=True) > 0).to(target.dtype)
    positives = edge_target.sum()
    positive_weight = ((edge_target.numel() - positives) / positives.clamp_min(1)).clamp(1, 20)
    edge_loss = F.binary_cross_entropy_with_logits(edge_logits, edge_target,
                                                  pos_weight=positive_weight)
    sobel_loss = F.l1_loss(sobel(logits.sigmoid()), target_gradient)
    total = segmentation + edge_weight * edge_loss + sobel_weight * sobel_loss
    return total, {"segmentation": segmentation.detach(), "edge": edge_loss.detach(),
                   "sobel": sobel_loss.detach()}
