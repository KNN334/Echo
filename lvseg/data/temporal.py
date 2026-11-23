"""Real causal context, with supervision only at expert-labeled target frames."""

import json
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import Dataset


def causal_clip(frames, target, context_frames):
    start = max(0, target - context_frames + 1)
    available = frames[start:target + 1]
    clip = np.zeros((context_frames, *frames.shape[1:]), dtype=frames.dtype)
    clip[-len(available):] = available
    return clip, len(available)


class LabeledClips(Dataset):
    def __init__(self, manifest_path, *, context_frames=3, augment=False):
        if context_frames < 1:
            raise ValueError("context_frames must be positive")
        path = Path(manifest_path).resolve()
        manifest = json.loads(path.read_text(encoding="utf-8"))
        if manifest["split"] not in {"train", "val"}:
            raise ValueError("Model development accepts train/val only")
        self.root = (path.parent / manifest["dataset_root"]).resolve()
        self.context_frames, self.augment = context_frames, augment
        self.cases, self.samples, self.patient_ids = {}, [], []
        labeled_images = []
        for case in manifest["cases"]:
            if case["split"] != manifest["split"]:
                raise ValueError("Case split differs from manifest")
            case_id = case["case_id"]
            with np.load(self.root / f"{case_id}.npz", allow_pickle=False) as data:
                frames, masks, labeled = data["frames"], data["masks"], data["labeled"].astype(bool)
            metadata = json.loads((self.root / f"{case_id}.json").read_text(encoding="utf-8"))
            times = metadata.get("timestamps_s")
            if times is None or len(times) != len(frames) or not np.isfinite(times).all() or (
                    len(times) > 1 and np.any(np.diff(times) <= 0)):
                raise ValueError(f"Reliable acquisition ordering required: {case_id}")
            if frames.shape != masks.shape or labeled.shape != (len(frames),):
                raise ValueError(f"Invalid labeled cine: {case_id}")
            self.cases[case_id] = (frames, masks, metadata)
            for index in np.flatnonzero(labeled):
                self.samples.append((case_id, int(index), case["patient_id"]))
                self.patient_ids.append(case["patient_id"])
                labeled_images.append(frames[index])
        if not self.samples:
            raise ValueError("No expert-labeled targets")
        labeled_images = np.asarray(labeled_images)
        self.mean = float(labeled_images.mean(dtype=np.float64) / 255)
        self.std = max(float(labeled_images.std(dtype=np.float64) / 255), 1e-6)

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, index):
        case_id, target, _ = self.samples[index]
        frames, masks, _ = self.cases[case_id]
        clip, length = causal_clip(frames, target, self.context_frames)
        image = torch.from_numpy(clip.copy()).float()[:, None] / 255
        mask = torch.from_numpy(masks[target].copy()).float()[None]
        if self.augment and torch.rand(()) < 0.5:
            image, mask = image.flip(-1), mask.flip(-1)
        return (image - self.mean) / self.std, mask, length
