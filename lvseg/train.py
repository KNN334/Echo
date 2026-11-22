"""Train a named conventional segmentation baseline on labeled frames only."""

from __future__ import annotations

import json
from pathlib import Path
import random
import time

import numpy as np
import torch
from torch.nn import functional as F
from torch.utils.data import DataLoader

from .data.dataset import LabeledFrames
from .models import build_model


def _loss(logits, target):
    bce = F.binary_cross_entropy_with_logits(logits, target)
    probability = logits.sigmoid()
    dimensions = (1, 2, 3)
    intersection = (probability * target).sum(dimensions)
    dice = (2.0 * intersection + 1.0) / (
        probability.sum(dimensions) + target.sum(dimensions) + 1.0)
    return bce + (1.0 - dice).mean()


def _validate(model, loader, device):
    model.eval()
    losses, dices = [], []
    with torch.inference_mode():
        for image, target in loader:
            image, target = image.to(device), target.to(device)
            logits = model(image)
            losses.append(float(_loss(logits, target).item()))
            prediction = logits.sigmoid() >= 0.5
            intersection = (prediction & (target >= 0.5)).sum(dim=(1, 2, 3)).float()
            denominator = prediction.sum(dim=(1, 2, 3)) + (target >= 0.5).sum(dim=(1, 2, 3))
            dices.extend(((2 * intersection + 1) / (denominator + 1)).cpu().tolist())
    return float(np.mean(losses)), float(np.mean(dices))


def train_model(model_name: str, train_manifest: str | Path, val_manifest: str | Path,
                output_dir: str | Path, *, config: dict, device: str = "auto",
                epochs: int | None = None, overwrite: bool = False) -> dict:
    if model_name not in config["training"]["models"]:
        raise ValueError(f"Model is not configured as a baseline: {model_name}")
    training = config["training"]
    epochs = int(epochs or training["epochs"])
    if epochs < 1:
        raise ValueError("epochs must be positive")
    output_dir = Path(output_dir)
    if output_dir.exists() and any(output_dir.iterdir()) and not overwrite:
        raise FileExistsError(f"Training output is not empty: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    seed = int(training["seed"])
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    if device == "auto":
        device = "cuda" if torch.cuda.is_available() else "cpu"
    torch.set_num_threads(2)

    train_set = LabeledFrames(train_manifest, augment=bool(training["horizontal_flip"]))
    val_set = LabeledFrames(val_manifest)
    train_patients = set(train_set.patient_ids)
    val_patients = set(val_set.patient_ids)
    if train_patients & val_patients:
        raise ValueError("Patient leakage between training and validation manifests")
    train_mean, train_std = train_set.mean, train_set.std
    val_set.set_normalization(train_mean, train_std)
    batch_size = int(training["batch_size"])
    loader_args = {"batch_size": batch_size, "num_workers": int(training["workers"]),
                   "pin_memory": device.startswith("cuda")}
    train_loader = DataLoader(train_set, shuffle=True, **loader_args)
    val_loader = DataLoader(val_set, shuffle=False, **loader_args)
    model = build_model(model_name, base_channels=int(training["base_channels"])).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=float(training["learning_rate"]),
                                  weight_decay=float(training["weight_decay"]))
    patience = int(training["early_stopping_patience"])
    best_loss, stale = float("inf"), 0
    history, started = [], time.time()
    run = {
        "model": model_name,
        "model_initialization": "random",
        "optimizer": "AdamW",
        "loss": "BCEWithLogits+soft_Dice",
        "input_channels": 1,
        "output_channels": 1,
        "train_patients": sorted(train_patients),
        "val_patients": sorted(val_patients),
        "train_frames": len(train_set),
        "val_frames": len(val_set),
        "normalization": {"mean_0_1": train_mean, "std_0_1": train_std,
                          "source": "training_labeled_frames_only"},
        "seed": seed,
        "device": device,
        "epochs_requested": epochs,
        "config": training,
    }
    (output_dir / "run.json").write_text(json.dumps(run, indent=2), encoding="utf-8")

    for epoch in range(1, epochs + 1):
        model.train()
        train_losses = []
        for image, target in train_loader:
            image, target = image.to(device), target.to(device)
            optimizer.zero_grad(set_to_none=True)
            loss = _loss(model(image), target)
            loss.backward()
            optimizer.step()
            train_losses.append(float(loss.item()))
        val_loss, val_dice = _validate(model, val_loader, device)
        row = {"epoch": epoch, "train_loss": float(np.mean(train_losses)),
               "val_loss": val_loss, "val_dice": val_dice,
               "elapsed_s": time.time() - started}
        history.append(row)
        (output_dir / "history.json").write_text(json.dumps(history, indent=2), encoding="utf-8")
        if val_loss < best_loss:
            best_loss, stale = val_loss, 0
            checkpoint = {
                "model": model_name,
                "model_config": {"in_channels": 1,
                                 "base_channels": int(training["base_channels"])},
                "state_dict": model.state_dict(),
                "normalization": {"mean": train_mean, "std": train_std},
                "best_epoch": epoch,
                "best_val_loss": val_loss,
                "run": run,
            }
            temp = output_dir / "best.pt.partial"
            torch.save(checkpoint, temp)
            temp.replace(output_dir / "best.pt")
        else:
            stale += 1
        print(f"{model_name} epoch {epoch}/{epochs}: train={row['train_loss']:.4f} "
              f"val={val_loss:.4f} val_dice={val_dice:.4f}", flush=True)
        if stale >= patience:
            break
    run.update({"epochs_completed": len(history), "best_val_loss": best_loss,
                "elapsed_s": time.time() - started})
    (output_dir / "run.json").write_text(json.dumps(run, indent=2), encoding="utf-8")
    return run
