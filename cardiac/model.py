"""EchoNet's DeepLabV3-ResNet50, one logit; modern torchvision without implicit downloads."""
from pathlib import Path
import random
import time
import numpy as np
from .common import read_json, write_json, write_csv, provenance, sha256


def build_model():
    import torch
    import torchvision
    model = torchvision.models.segmentation.deeplabv3_resnet50(
        weights=None, weights_backbone=None, aux_loss=False)
    model.classifier[-1] = torch.nn.Conv2d(model.classifier[-1].in_channels, 1, kernel_size=1)
    return model


def load_checkpoint(path, device="cpu"):
    import torch
    model = build_model()
    # Official trusted EchoNet weights may contain numpy optimizer state; do not load untrusted pickle files.
    checkpoint = torch.load(path, map_location="cpu", weights_only=False)
    state = checkpoint.get("state_dict", checkpoint)
    state = {k.removeprefix("module."): v for k, v in state.items()}
    model.load_state_dict(state, strict=True)
    model.to(device).eval()
    return model, checkpoint


def normalize(frames, mean, std):
    import torch
    x = torch.from_numpy(frames.astype(np.float32))[:, None].repeat(1, 3, 1, 1)
    return (x - torch.tensor(mean, dtype=torch.float32)[None, :, None, None]) / torch.tensor(std, dtype=torch.float32)[None, :, None, None]


def predict(model, frames, mean, std, device, batch=16):
    import torch
    result = []
    with torch.inference_mode():
        for start in range(0, len(frames), batch):
            logits = model(normalize(frames[start:start+batch], mean, std).to(device))["out"]
            result.append(logits[:, 0].sigmoid().cpu().numpy())
    return np.concatenate(result)


def train(processed, output, epochs=30, batch=8, lr=1e-5, seed=2026, weights=None, device="cuda", max_cases=None):
    import torch
    torch.manual_seed(seed)
    random.seed(seed)
    np.random.seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    root, output = Path(processed), Path(output)
    output.mkdir(parents=True, exist_ok=True)
    entries = read_json(root / "manifest.json")["cases"]
    grouped = {split: [x for x in entries if x["split"] == split] for split in ("train", "val", "test")}
    if max_cases:
        grouped = {k: v[:max_cases] for k,v in grouped.items()}
    if not grouped["train"] or not grouped["val"]:
        raise ValueError("nonempty patient-independent training and validation sets required")

    def arrays(split):
        images, labels = [], []
        for row in grouped[split]:
            with np.load(root / (row["case_id"] + ".npz")) as d:
                images.extend(d["frames"][d["labeled"]])
                labels.extend(d["masks"][d["labeled"]])
        return np.asarray(images), np.asarray(labels)

    tx, ty = arrays("train")
    vx, vy = arrays("val")
    if not len(tx) or not len(vx):
        raise ValueError("no annotated train/validation frames")
    # Train-only normalization, never use test statistics. Grayscale repeated into RGB.
    mean, std = [float(tx.mean())]*3, [max(float(tx.std()), 1.)]*3
    model = load_checkpoint(weights, device)[0] if weights else build_model().to(device)
    optimizer = torch.optim.SGD(model.parameters(), lr=lr, momentum=.9, weight_decay=0)
    run = {**provenance(), "model": "echonet_deeplabv3_resnet50_one_logit", "mean": mean, "std": std,
           "normalization_unit": "uint8_0_255", "epochs": epochs, "batch_size": batch, "lr": lr, "seed": seed,
           "train_patients": sorted(set(x["patient_id"] for x in grouped["train"])),
           "val_patients": sorted(set(x["patient_id"] for x in grouped["val"])),
           "test_patients": sorted(set(x["patient_id"] for x in grouped["test"])),
           "input_manifest_sha256": sha256(root / "manifest.json"),
           "initial_weights_sha256": sha256(weights) if weights else None,
           "experiment_type": "smoke_training_not_final" if max_cases else "baseline_training",
           "torch_version": torch.__version__, "device": device}
    for x in ("train", "val"):
        if set(run[x + "_patients"]) & set(run["test_patients"]):
            raise ValueError("patient leakage")
    write_json(output / "run.json", run)
    history, best = [], float("inf")
    for epoch in range(epochs):
        model.train()
        # Freeze BN statistics to support small clinical batches; retain learnable affine weights.
        for module in model.modules():
            if isinstance(module, torch.nn.modules.batchnorm._BatchNorm):
                module.eval()
        losses = []
        order = np.random.permutation(len(tx))
        for start in range(0, len(tx), batch):
            idx = order[start:start+batch]
            x = normalize(tx[idx], mean, std).to(device)
            target = torch.from_numpy(ty[idx].astype(np.float32))[:, None].to(device)
            optimizer.zero_grad(set_to_none=True)
            logits = model(x)["out"]
            loss = torch.nn.functional.binary_cross_entropy_with_logits(logits, target)
            loss.backward()
            optimizer.step()
            losses.append(float(loss.item()))
        model.eval()
        vloss = []
        with torch.inference_mode():
            for start in range(0, len(vx), batch):
                y = torch.from_numpy(vy[start:start+batch].astype(np.float32))[:, None].to(device)
                logits = model(normalize(vx[start:start+batch], mean, std).to(device))["out"]
                vloss.append(float(torch.nn.functional.binary_cross_entropy_with_logits(logits, y).item()))
        row = {"epoch": epoch + 1, "train_bce": float(np.mean(losses)), "val_bce": float(np.mean(vloss))}
        history.append(row)
        write_csv(output / "training.csv", history)
        if row["val_bce"] < best:
            best = row["val_bce"]
            torch.save({"state_dict": model.state_dict(), "epoch": epoch+1, "mean": mean, "std": std, "run": run}, output / "best.pt")
        print(row, flush=True)
    return history
