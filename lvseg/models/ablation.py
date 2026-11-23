"""Independently switchable additions to the established Attention U-Net."""

from __future__ import annotations

import torch
from torch import nn

from .architectures import AttentionUNet, _groups, _up


class SEGate(nn.Module):
    """Channel reweighting on a skip, replacing the decoder-conditioned AG."""

    def __init__(self, channels, reduction=16):
        super().__init__()
        self.weights = nn.Sequential(
            nn.AdaptiveAvgPool2d(1), nn.Conv2d(channels, max(4, channels // reduction), 1),
            nn.ReLU(inplace=True), nn.Conv2d(max(4, channels // reduction), channels, 1),
            nn.Sigmoid())

    def forward(self, skip, gate):
        return skip * self.weights(skip)


class DilatedResidualBlock(nn.Module):
    """Local convolution plus dilation-2 convolution and a projected residual."""

    def __init__(self, in_channels, out_channels):
        super().__init__()
        self.body = nn.Sequential(
            nn.Conv2d(in_channels, out_channels, 3, padding=1, bias=False),
            nn.GroupNorm(_groups(out_channels), out_channels), nn.ReLU(inplace=True),
            nn.Conv2d(out_channels, out_channels, 3, padding=2, dilation=2, bias=False),
            nn.GroupNorm(_groups(out_channels), out_channels))
        self.shortcut = (nn.Identity() if in_channels == out_channels else
                         nn.Conv2d(in_channels, out_channels, 1, bias=False))
        self.activation = nn.ReLU(inplace=True)

    def forward(self, x):
        return self.activation(self.body(x) + self.shortcut(x))


class BottleneckConvLSTM(nn.Module):
    def __init__(self, channels):
        super().__init__()
        self.hidden = max(8, channels // 2)
        self.gates = nn.Conv2d(channels + self.hidden, self.hidden * 4, 3, padding=1)
        self.project = nn.Conv2d(self.hidden, channels, 1)

    def forward(self, sequence, lengths):
        batch, steps, _, height, width = sequence.shape
        hidden = sequence.new_zeros(batch, self.hidden, height, width)
        cell = torch.zeros_like(hidden)
        for step in range(steps):
            ingate, forget, candidate, outgate = self.gates(
                torch.cat((sequence[:, step], hidden), dim=1)).chunk(4, dim=1)
            next_cell = forget.sigmoid() * cell + ingate.sigmoid() * candidate.tanh()
            next_hidden = outgate.sigmoid() * next_cell.tanh()
            valid = (step >= steps - lengths).reshape(batch, 1, 1, 1)
            cell = torch.where(valid, next_cell, cell)
            hidden = torch.where(valid, next_hidden, hidden)
        return sequence[:, -1] + self.project(hidden)


class AblationUNet(AttentionUNet):
    def __init__(self, in_channels=1, base=24, *, se=False, dilated_residual=False,
                 temporal=False, edge=False, context_frames=3):
        super().__init__(in_channels, base, depth=4)
        self.temporal, self.edge = temporal, edge
        self.context_frames = context_frames if temporal else 1
        widths = [base * 2**index for index in range(5)]
        if se:
            self.gates = nn.ModuleList(SEGate(width) for width in reversed(widths[:-1]))
        if dilated_residual:
            self.encoders = nn.ModuleList(DilatedResidualBlock(
                in_channels if index == 0 else widths[index - 1], width)
                for index, width in enumerate(widths))
        if temporal:
            self.fusion = BottleneckConvLSTM(widths[-1])
        if edge:
            self.edge_head = nn.Sequential(
                nn.Conv2d(widths[0], widths[0], 3, padding=1), nn.ReLU(inplace=True),
                nn.Conv2d(widths[0], 1, 1))

    def forward_with_aux(self, x, lengths=None):
        if x.ndim == 4:
            x = x[:, None]
        batch, steps, channels, height, width = x.shape
        if lengths is None:
            lengths = torch.full((batch,), steps, device=x.device, dtype=torch.long)
        if not self.temporal:
            x, steps = x[:, -1:], 1
        features = x.reshape(batch * steps, channels, height, width)
        skips = []
        for encoder in self.encoders[:-1]:
            features = encoder(features)
            skips.append(features.reshape(batch, steps, *features.shape[1:])[:, -1])
            features = self.pool(features)
        features = self.encoders[-1](features)
        sequence = features.reshape(batch, steps, *features.shape[1:])
        features = self.fusion(sequence, lengths) if self.temporal else sequence[:, -1]
        for decoder, gate, skip in zip(self.decoders, self.gates, reversed(skips)):
            features = decoder(torch.cat((_up(features, skip), gate(skip, features)), dim=1))
        return self.head(features), self.edge_head(features) if self.edge else None

    def forward(self, x, lengths=None):
        return self.forward_with_aux(x, lengths)[0]
