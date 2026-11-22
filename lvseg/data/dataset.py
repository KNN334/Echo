"""A frame dataset that admits only expert-labeled frames to supervision."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import Dataset


class LabeledFrames(Dataset):
    def __init__(self, manifest_path: str | Path, *, augment: bool = False):
        manifest_path = Path(manifest_path).resolve()
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("split") not in {"train", "val", "test"}:
            raise ValueError(f"Invalid frame dataset split: {manifest_path}")
        dataset_root = (manifest_path.parent / manifest["dataset_root"]).resolve()
        self.frames, self.masks, self.patient_ids, self.case_ids = [], [], [], []
        self.augment = augment
        for case in manifest["cases"]:
            if case.get("split") != manifest["split"]:
                raise ValueError(f"Case split does not match manifest: {case.get('case_id')}")
            path = dataset_root / f"{case['case_id']}.npz"
            with np.load(path, allow_pickle=False) as arrays:
                frames = arrays["frames"]
                masks = arrays["masks"]
                labeled = arrays["labeled"].astype(bool)
            if frames.ndim != 3 or masks.shape != frames.shape or labeled.shape != (len(frames),):
                raise ValueError(f"Invalid prepared arrays: {case['case_id']}")
            if not labeled.any():
                continue
            selected = np.flatnonzero(labeled)
            self.frames.extend(frames[selected])
            self.masks.extend(masks[selected])
            self.patient_ids.extend([case["patient_id"]] * len(selected))
            self.case_ids.extend([case["case_id"]] * len(selected))
        self.frames = np.asarray(self.frames, dtype=np.uint8)
        self.masks = np.asarray(self.masks, dtype=np.uint8)
        if not len(self.frames):
            raise ValueError(f"No expert-labeled frames in {manifest_path}")
        self.mean = float(self.frames.mean(dtype=np.float64) / 255.0)
        self.std = max(float(self.frames.std(dtype=np.float64) / 255.0), 1e-6)

    def set_normalization(self, mean: float, std: float):
        if std <= 0:
            raise ValueError("Normalization standard deviation must be positive")
        self.mean, self.std = float(mean), float(std)

    def __len__(self):
        return len(self.frames)

    def __getitem__(self, index):
        image = torch.from_numpy(self.frames[index].copy()).float()[None] / 255.0
        mask = torch.from_numpy(self.masks[index].copy()).float()[None]
        if self.augment and torch.rand(()) < 0.5:
            image = image.flip(-1)
            mask = mask.flip(-1)
        return (image - self.mean) / self.std, mask
