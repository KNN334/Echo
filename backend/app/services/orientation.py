"""Detect horizontal ultrasound fans and map predictions back to the source."""

import cv2
import numpy as np


def _fan_mask(frame: np.ndarray) -> np.ndarray | None:
    thumbnail = cv2.resize(frame, (128, 128), interpolation=cv2.INTER_AREA)
    count, components, stats, _ = cv2.connectedComponentsWithStats((thumbnail > 8).astype(np.uint8))
    if count < 2:
        return None
    label = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    x, y, width, height, area = stats[label]
    if min(width, height) < 48 or area < 0.35 * width * height:
        return None
    return components[y:y + height, x:x + width] == label


def _taper(mask: np.ndarray) -> float:
    """Score a fan with its narrow end at the top from the sector footprint."""
    rows = len(mask)
    widths = mask.mean(axis=1)
    near = float(widths[round(0.06 * rows):round(0.20 * rows)].mean())
    center = float(widths[round(0.40 * rows):round(0.60 * rows)].mean())
    wide = float(widths[round(0.60 * rows):round(0.78 * rows)].mean())
    if center < 0.42 or wide < 0.54 or near > 0.54 * wide or center < 1.30 * near:
        return 0.0
    return wide - near


def fan_rotation(frame: np.ndarray) -> int:
    """Return counterclockwise quarter turns for a confident sideways fan."""
    mask = _fan_mask(frame)
    if mask is None:
        return 0
    upright = _taper(mask)
    left = _taper(np.rot90(mask, -1))
    right = _taper(np.rot90(mask, 1))
    if left > max(upright, right) + 0.15:
        return -1
    if right > max(upright, left) + 0.15:
        return 1
    return 0


def sequence_rotation(frames: list[np.ndarray]) -> int:
    """Use one transform for the whole clip so temporal context stays aligned."""
    sample = sorted(set(np.linspace(0, len(frames) - 1, num=min(5, len(frames)), dtype=int)))
    votes = [fan_rotation(frames[index]) for index in sample]
    for turns in (-1, 1):
        if votes.count(turns) > len(votes) / 2:
            return turns
    return 0
