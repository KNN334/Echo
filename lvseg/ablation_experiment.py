"""Training and patient-level validation for the fixed module ablation."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import random
import time

import numpy as np
from PIL import Image
import torch
from torch.utils.data import DataLoader

from .data.temporal import causal_clip
from .evaluate import _write_csv
from .losses import segmentation_boundary_loss
from .metrics.cycles import bland_altman
from .metrics.segmentation import overlap_metrics
from .metrics.volume import simpson_single_plane
from .models import build_model
from .train import _loss


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save_json(path, data):
    path = Path(path)
    temporary = path.with_suffix(path.suffix + ".partial")
    temporary.write_text(json.dumps(data, indent=2), encoding="utf-8")
    temporary.replace(path)


def validate_loss(model, loader, device, amp):
    model.eval()
    total, count = 0.0, 0
    with torch.inference_mode():
        for images, target, lengths in loader:
            images, target, lengths = images.to(device), target.to(device), lengths.to(device)
            with torch.autocast(device_type=device.split(":")[0], enabled=amp):
                logits = model(images, lengths)
                loss = _loss(logits, target)
            total += float(loss) * len(target)
            count += len(target)
    return total / count


def train_variant(variant, options, seed, config, train_set, val_set, output, device):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    training = config["training"]
    run_config = {"variant": variant, "options": options, "seed": seed,
                  "training": training}
    complete = output / "complete.json"
    if complete.is_file():
        previous = json.loads(complete.read_text(encoding="utf-8"))
        if previous["run_config"] != run_config:
            raise ValueError(f"Completed experiment configuration changed: {output}")
        if previous["checkpoint_sha256"] != sha256(output / "best.pt"):
            raise ValueError(f"Completed checkpoint changed: {output}")
        return previous
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if device.startswith("cuda"):
        torch.cuda.manual_seed_all(seed)
    model_config = {"base_channels": training["base_channels"], "in_channels": 1,
                    "ablation": {**options, "context_frames": training["context_frames"]}}
    model = build_model("LV-Ablation", **model_config).to(device)
    amp = bool(training["amp"] and device.startswith("cuda"))
    optimizer = torch.optim.AdamW(model.parameters(), lr=training["learning_rate"],
                                  weight_decay=training["weight_decay"])
    scaler = torch.amp.GradScaler("cuda", enabled=amp)
    # Architecture initialization cannot alter the paired sample/augmentation streams.
    torch.manual_seed(seed + 10000)
    generator = torch.Generator().manual_seed(seed + 20000)
    loader_options = {"batch_size": training["batch_size"], "num_workers": training["workers"],
                      "pin_memory": device.startswith("cuda")}
    train_loader = DataLoader(train_set, shuffle=True, generator=generator, **loader_options)
    val_loader = DataLoader(val_set, shuffle=False, **loader_options)
    metadata = {"model": "LV-Ablation", "variant": variant, "seed": seed,
                "train_patients": sorted(set(train_set.patient_ids)),
                "val_patients": sorted(set(val_set.patient_ids)),
                "train_targets": len(train_set), "val_targets": len(val_set),
                "normalization": {"mean": train_set.mean, "std": train_set.std,
                                  "source": "training_labeled_frames_only"},
                "parameter_count": sum(parameter.numel() for parameter in model.parameters()),
                "torch_version": torch.__version__, "device": device, "amp": amp,
                "gpu": torch.cuda.get_device_name(0) if device.startswith("cuda") else None,
                "checkpoint_selection": "minimum_validation_segmentation_BCE_plus_Dice",
                "run_config": run_config}
    save_json(output / "run.json", metadata)
    resume_path = output / "resume.pt"
    if resume_path.is_file():
        resume = torch.load(resume_path, map_location="cpu", weights_only=False)
        if resume["run_config"] != run_config:
            raise ValueError(f"Incomplete experiment configuration changed: {output}")
        model.load_state_dict(resume["model"])
        optimizer.load_state_dict(resume["optimizer"])
        scaler.load_state_dict(resume["scaler"])
        generator.set_state(resume["loader_rng"])
        torch.set_rng_state(resume["torch_rng"].cpu())
        if device.startswith("cuda"):
            torch.cuda.set_rng_state_all(resume["cuda_rng"])
        history = resume["history"]
        best, stale = resume["best_loss"], resume["stale"]
        first_epoch, elapsed_before = resume["next_epoch"], resume["elapsed_s"]
    else:
        history = []
        best, stale = float("inf"), 0
        first_epoch, elapsed_before = 1, 0.0
    started = time.time()
    for epoch in range(first_epoch, training["epochs"] + 1):
        model.train()
        loss_sum = 0.0
        components_sum = {}
        epoch_started = time.time()
        for images, target, lengths in train_loader:
            images, target, lengths = images.to(device), target.to(device), lengths.to(device)
            optimizer.zero_grad(set_to_none=True)
            with torch.autocast(device_type=device.split(":")[0], enabled=amp):
                logits, edge_logits = model.forward_with_aux(images, lengths)
                loss, parts = segmentation_boundary_loss(
                    logits, target, edge_logits, edge_weight=training["edge_weight"],
                    sobel_weight=training["sobel_weight"])
            if not torch.isfinite(loss):
                raise FloatingPointError(f"Nonfinite loss in {variant} / {seed}")
            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()
            loss_sum += float(loss.detach()) * len(target)
            for key, value in parts.items():
                components_sum[key] = components_sum.get(key, 0) + float(value) * len(target)
        validation = validate_loss(model, val_loader, device, amp)
        row = {"epoch": epoch, "train_loss": loss_sum / len(train_set),
               "validation_segmentation_loss": validation,
               "train_components": {key: value / len(train_set) for key, value in components_sum.items()},
               "epoch_seconds": time.time() - epoch_started,
               "elapsed_s": time.time() - started}
        history.append(row)
        save_json(output / "history.json", history)
        if validation < best:
            best, stale = validation, 0
            torch.save({"model": "LV-Ablation", "model_config": model_config,
                        "state_dict": model.state_dict(), "normalization": metadata["normalization"],
                        "best_epoch": epoch, "best_val_loss": validation, "run": metadata},
                       output / "best.pt.partial")
            (output / "best.pt.partial").replace(output / "best.pt")
        else:
            stale += 1
        torch.save({"run_config": run_config, "model": model.state_dict(),
                    "optimizer": optimizer.state_dict(), "scaler": scaler.state_dict(),
                    "loader_rng": generator.get_state(), "torch_rng": torch.get_rng_state(),
                    "cuda_rng": torch.cuda.get_rng_state_all() if device.startswith("cuda") else [],
                    "history": history, "best_loss": best, "stale": stale,
                    "next_epoch": epoch + 1,
                    "elapsed_s": elapsed_before + time.time() - started},
                   output / "resume.pt.partial")
        (output / "resume.pt.partial").replace(resume_path)
        print(f"{variant} seed={seed} epoch={epoch}/{training['epochs']} "
              f"train={row['train_loss']:.4f} val={validation:.4f} "
              f"seconds={row['epoch_seconds']:.1f}", flush=True)
        if stale >= training["early_stopping_patience"]:
            break
    metadata.update({"epochs_completed": len(history), "best_val_loss": best,
                     "elapsed_s": elapsed_before + time.time() - started,
                     "checkpoint_sha256": sha256(output / "best.pt")})
    save_json(output / "run.json", metadata)
    save_json(complete, metadata)
    return metadata


def evaluate_validation(checkpoint_path, dataset, output, config, device, *, noise_sigma=0.0):
    """Labels are consulted only after prediction of their target image."""
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    summary_path = output / "summary.json"
    digest = sha256(checkpoint_path)
    if summary_path.is_file():
        saved = json.loads(summary_path.read_text(encoding="utf-8"))
        if saved["checkpoint_sha256"] == digest and saved["noise_sigma"] == noise_sigma:
            return saved
        raise ValueError(f"Validation cache mismatch: {output}")
    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    assert set(dataset.patient_ids) == set(checkpoint["run"]["val_patients"])
    assert not set(dataset.patient_ids) & set(checkpoint["run"]["train_patients"])
    model = build_model(checkpoint["model"], **checkpoint["model_config"]).to(device).eval()
    model.load_state_dict(checkpoint["state_dict"])
    mean, std = checkpoint["normalization"]["mean"], checkpoint["normalization"]["std"]
    rows = []
    pairs = {}
    case_samples = {}
    for case_id, index, patient in dataset.samples:
        case_samples.setdefault(case_id, []).append((index, patient))
    started = time.time()
    with torch.inference_mode():
        for case_id, samples in case_samples.items():
            frames, _, metadata = dataset.cases[case_id]
            if noise_sigma:
                case_seed = int(hashlib.sha256(case_id.encode()).hexdigest()[:8], 16)
                rng = np.random.default_rng(config["evaluation"]["noise_seed"] + case_seed)
                frames = np.clip(frames.astype(np.float32) / 255 * (
                    1 + noise_sigma * rng.standard_normal(frames.shape)), 0, 1) * 255
                frames = frames.astype(np.float32)
            with np.load(dataset.root / f"{case_id}.npz", allow_pickle=False) as data:
                references = dict(zip(data["original_gt_indices"], data["original_gt"]))
            for index, patient in samples:
                clip, length = causal_clip(frames, index, model.context_frames)
                images = torch.from_numpy(clip.copy()).float()[None, :, None].to(device) / 255
                logits = model((images - mean) / std, torch.tensor([length], device=device))
                mask = (logits.sigmoid()[0, 0] >= config["evaluation"]["threshold"]).cpu().numpy()
                height, width = metadata["original_hw"]
                mask = np.asarray(Image.fromarray(mask.astype(np.uint8)).resize(
                    (width, height), Image.Resampling.NEAREST), dtype=bool)
                reference = references[index].astype(bool)
                spacing = metadata.get("spacing_xy_mm")
                scores = overlap_metrics(mask, reference, spacing)
                volume = simpson_single_plane(mask, spacing) if spacing else None
                reference_volume = simpson_single_plane(reference, spacing) if spacing else None
                row = {"patient_id": patient, "case_id": case_id, "frame": index,
                       "view": metadata["view"], "context_length": length, **scores,
                       "volume_ml": volume, "expert_mask_volume_ml": reference_volume,
                       "volume_absolute_error_ml": abs(volume - reference_volume)
                       if volume is not None and reference_volume is not None else None}
                rows.append(row)
                if volume is not None and reference_volume is not None:
                    pair = pairs.setdefault((patient, metadata["view"]), [[], []])
                    pair[0].append(volume)
                    pair[1].append(reference_volume)
    metrics = ("dice", "miou", "precision", "recall", "hd95", "asd", "volume_absolute_error_ml")
    by_patient = {}
    for row in rows:
        patient = by_patient.setdefault(row["patient_id"], {key: [] for key in metrics})
        for key in metrics:
            if row[key] is not None and np.isfinite(row[key]):
                patient[key].append(row[key])
    patient_rows = [{"patient_id": patient, **{key: float(np.mean(values)) if values else None
                                             for key, values in scores.items()}}
                    for patient, scores in sorted(by_patient.items())]
    summary = {"split": "val", "patients": len(by_patient), "labeled_frames": len(rows),
               "checkpoint_sha256": digest, "noise_sigma": noise_sigma,
               "parameter_count": checkpoint["run"]["parameter_count"],
               "best_epoch": checkpoint["best_epoch"], "elapsed_s": time.time() - started,
               "context_lengths": {str(length): sum(row["context_length"] == length for row in rows)
                                   for length in range(1, model.context_frames + 1)},
               "metrics": {key: float(np.mean([row[key] for row in patient_rows if row[key] is not None]))
                           for key in metrics},
               "volume_bland_altman_by_patient_view": {view: bland_altman(
                   [float(np.mean(values[0])) for (patient, v), values in pairs.items() if v == view],
                   [float(np.mean(values[1])) for (patient, v), values in pairs.items() if v == view])
                   for view in ("2CH", "4CH")}}
    _write_csv(output / "labeled_frame_metrics.csv", rows)
    _write_csv(output / "patient_metrics.csv", patient_rows)
    save_json(summary_path, summary)
    return summary
