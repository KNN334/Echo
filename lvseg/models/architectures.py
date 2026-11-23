"""Five conventional LV segmentation models under one logits interface."""

from __future__ import annotations

import torch
from torch import nn
from torch.nn import functional as F


MODEL_NAMES = ("UNet", "Attention-UNet", "UNet++", "UNet-mini", "VGG16-UNet")


def _groups(channels: int) -> int:
    return next(group for group in (8, 4, 2, 1) if channels % group == 0)


class ConvBlock(nn.Module):
    def __init__(self, in_channels: int, out_channels: int, *, layers: int = 2):
        super().__init__()
        blocks = []
        for index in range(layers):
            source = in_channels if index == 0 else out_channels
            blocks.extend((nn.Conv2d(source, out_channels, 3, padding=1, bias=False),
                           nn.GroupNorm(_groups(out_channels), out_channels),
                           nn.ReLU(inplace=True)))
        self.layers = nn.Sequential(*blocks)

    def forward(self, x):
        return self.layers(x)


def _up(x: torch.Tensor, reference: torch.Tensor) -> torch.Tensor:
    return F.interpolate(x, size=reference.shape[-2:], mode="bilinear", align_corners=False)


class UNet(nn.Module):
    def __init__(self, in_channels: int = 1, base: int = 32, depth: int = 4):
        super().__init__()
        widths = [base * (2 ** index) for index in range(depth + 1)]
        self.encoders = nn.ModuleList()
        previous = in_channels
        for width in widths:
            self.encoders.append(ConvBlock(previous, width))
            previous = width
        self.pool = nn.MaxPool2d(2)
        self.decoders = nn.ModuleList([
            ConvBlock(widths[index] + widths[index + 1], widths[index])
            for index in range(depth - 1, -1, -1)
        ])
        self.head = nn.Conv2d(widths[0], 1, 1)

    def forward(self, x):
        skips = []
        for encoder in self.encoders[:-1]:
            x = encoder(x)
            skips.append(x)
            x = self.pool(x)
        x = self.encoders[-1](x)
        for decoder, skip in zip(self.decoders, reversed(skips)):
            x = decoder(torch.cat((_up(x, skip), skip), dim=1))
        return self.head(x)


class AttentionGate(nn.Module):
    def __init__(self, skip_channels: int, gate_channels: int, hidden: int):
        super().__init__()
        self.skip = nn.Conv2d(skip_channels, hidden, 1, bias=False)
        self.gate = nn.Conv2d(gate_channels, hidden, 1, bias=False)
        self.score = nn.Sequential(nn.ReLU(inplace=True), nn.Conv2d(hidden, 1, 1), nn.Sigmoid())

    def forward(self, skip, gate):
        weights = self.score(self.skip(skip) + self.gate(_up(gate, skip)))
        return skip * weights


class AttentionUNet(UNet):
    def __init__(self, in_channels: int = 1, base: int = 32, depth: int = 4):
        super().__init__(in_channels, base, depth)
        widths = [base * (2 ** index) for index in range(depth + 1)]
        self.gates = nn.ModuleList([
            AttentionGate(widths[index], widths[index + 1], max(widths[index] // 2, 8))
            for index in range(depth - 1, -1, -1)
        ])

    def forward(self, x):
        skips = []
        for encoder in self.encoders[:-1]:
            x = encoder(x)
            skips.append(x)
            x = self.pool(x)
        x = self.encoders[-1](x)
        for decoder, gate, skip in zip(self.decoders, self.gates, reversed(skips)):
            attended = gate(skip, x)
            x = decoder(torch.cat((_up(x, skip), attended), dim=1))
        return self.head(x)


class UNetPlusPlus(nn.Module):
    def __init__(self, in_channels: int = 1, base: int = 24, depth: int = 4):
        super().__init__()
        self.pool = nn.MaxPool2d(2)
        self.nodes = nn.ModuleDict()
        widths = [base * (2 ** index) for index in range(depth + 1)]
        for level in range(depth + 1):
            self.nodes[f"{level}_0"] = ConvBlock(in_channels if level == 0 else widths[level - 1],
                                                   widths[level])
        for column in range(1, depth + 1):
            for level in range(depth - column + 1):
                self.nodes[f"{level}_{column}"] = ConvBlock(
                    widths[level] * column + widths[level + 1], widths[level])
        self.head = nn.Conv2d(widths[0], 1, 1)

    def forward(self, x):
        nodes = {}
        for level in range(max(int(key.split("_")[0]) for key in self.nodes) + 1):
            source = x if level == 0 else self.pool(nodes[(level - 1, 0)])
            nodes[(level, 0)] = self.nodes[f"{level}_0"](source)
        depth = max(int(key.split("_")[0]) + int(key.split("_")[1]) for key in self.nodes)
        for column in range(1, depth + 1):
            for level in range(depth - column + 1):
                same_level = [nodes[(level, previous)] for previous in range(column)]
                deeper = _up(nodes[(level + 1, column - 1)], same_level[0])
                nodes[(level, column)] = self.nodes[f"{level}_{column}"](
                    torch.cat([*same_level, deeper], dim=1))
        return self.head(nodes[(0, depth)])


class VGG16UNet(nn.Module):
    """VGG16-style encoder with U-Net skip decoding; initialized from scratch."""

    def __init__(self, in_channels: int = 1):
        super().__init__()
        widths, layers = (64, 128, 256, 512), (2, 2, 3, 3)
        self.pool = nn.MaxPool2d(2)
        self.encoder = nn.ModuleList()
        previous = in_channels
        for width, count in zip(widths, layers):
            self.encoder.append(ConvBlock(previous, width, layers=count))
            previous = width
        self.bridge = ConvBlock(512, 512, layers=3)
        self.decoder = nn.ModuleList([
            ConvBlock(512 + 512, 256), ConvBlock(256 + 256, 128),
            ConvBlock(128 + 128, 64), ConvBlock(64 + 64, 32),
        ])
        self.head = nn.Conv2d(32, 1, 1)

    def forward(self, x):
        skips = []
        for encoder in self.encoder:
            x = encoder(x)
            skips.append(x)
            x = self.pool(x)
        x = self.bridge(x)
        for decoder, skip in zip(self.decoder, reversed(skips)):
            x = decoder(torch.cat((_up(x, skip), skip), dim=1))
        return self.head(x)


def build_model(name: str, *, in_channels: int = 1, base_channels: int | None = None,
                ablation: dict | None = None) -> nn.Module:
    if base_channels is None:
        base_channels = 24 if name == "DRA-UNet" else 32
    if name == "DRA-UNet":
        from .ablation import AblationUNet
        if ablation is not None:
            raise ValueError("DRA-UNet has a fixed architecture")
        return AblationUNet(in_channels, base_channels, dilated_residual=True,
                            temporal=True, edge=True, context_frames=3)
    if name == "LV-Ablation":
        from .ablation import AblationUNet
        return AblationUNet(in_channels, base_channels, **(ablation or {}))
    if name == "UNet":
        return UNet(in_channels, base_channels, depth=4)
    if name == "Attention-UNet":
        return AttentionUNet(in_channels, base_channels, depth=4)
    if name == "UNet++":
        return UNetPlusPlus(in_channels, base_channels, depth=4)
    if name == "UNet-mini":
        return UNet(in_channels, max(base_channels // 2, 8), depth=2)
    if name == "VGG16-UNet":
        return VGG16UNet(in_channels)
    raise ValueError(f"Unknown segmentation model {name!r}; choose from {(*MODEL_NAMES, 'DRA-UNet')}")
