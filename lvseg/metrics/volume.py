"""Single-plane and synchronized biplane Simpson disk calculations."""

from __future__ import annotations

import numpy as np


def _disk_profile(mask, spacing_xy_mm, disks):
    mask = np.asarray(mask, dtype=bool)
    if mask.ndim != 2 or not mask.any() or disks < 2:
        return None
    spacing_x, spacing_y = map(float, spacing_xy_mm)
    if min(spacing_x, spacing_y) <= 0:
        return None
    y, x = np.nonzero(mask)
    points = np.column_stack((x * spacing_x, y * spacing_y)).astype(np.float64)
    centered = points - points.mean(axis=0)
    covariance = centered.T @ centered / max(len(points), 1)
    eigenvalues, eigenvectors = np.linalg.eigh(covariance)
    long_axis = eigenvectors[:, int(np.argmax(eigenvalues))]
    short_axis = np.array([-long_axis[1], long_axis[0]])
    longitudinal = centered @ long_axis
    transverse = centered @ short_axis
    lower, upper = float(longitudinal.min()), float(longitudinal.max())
    length = upper - lower
    if not np.isfinite(length) or length <= 0:
        return None
    edges = np.linspace(lower, upper, disks + 1)
    widths = []
    for index in range(disks):
        selected = ((longitudinal >= edges[index]) &
                    (longitudinal < edges[index + 1] if index + 1 < disks else
                     longitudinal <= edges[index + 1]))
        if not selected.any():
            widths.append(0.0)
        else:
            widths.append(float(transverse[selected].max() - transverse[selected].min() +
                                min(spacing_x, spacing_y)))
    widths = np.asarray(widths, dtype=float)
    if np.count_nonzero(widths) < max(2, disks // 2):
        return None
    # The apical endpoint is narrower; put both view profiles in apex-to-base order.
    edge_width = max(1, disks // 5)
    if widths[:edge_width].mean() > widths[-edge_width:].mean():
        widths = widths[::-1]
    return length, widths


def simpson_single_plane(mask, spacing_xy_mm, *, disks: int = 20) -> float | None:
    """Estimate mL using one plane and an explicit circular-cross-section assumption."""
    profile = _disk_profile(mask, spacing_xy_mm, disks)
    if profile is None:
        return None
    length, widths = profile
    disk_length = length / disks
    volume_mm3 = float(np.sum(np.pi / 4.0 * widths ** 2 * disk_length))
    return volume_mm3 / 1000.0 if np.isfinite(volume_mm3) and volume_mm3 > 0 else None


def simpson_biplane(mask_2ch, mask_4ch, spacing_2ch_xy_mm, spacing_4ch_xy_mm,
                    *, disks: int = 20) -> float | None:
    """Biplane Simpson volume; inputs must be views acquired at the same time."""
    a = _disk_profile(mask_2ch, spacing_2ch_xy_mm, disks)
    b = _disk_profile(mask_4ch, spacing_4ch_xy_mm, disks)
    if a is None or b is None:
        return None
    length = min(a[0], b[0])
    coordinate = (np.arange(disks) + 0.5) / disks
    da = np.interp(coordinate, (np.arange(disks) + 0.5) / disks, a[1])
    db = np.interp(coordinate, (np.arange(disks) + 0.5) / disks, b[1])
    volume_mm3 = float(np.sum(np.pi / 4.0 * da * db * (length / disks)))
    return volume_mm3 / 1000.0 if np.isfinite(volume_mm3) and volume_mm3 > 0 else None
