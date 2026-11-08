from pathlib import Path
import hashlib
import numpy as np
from .common import read_json, write_json
from .io import read_camus
from .preprocess import process


def make_splits(patients, output, seed=2026):
    """Stable patient-hash split; independent of file enumeration or download completeness."""
    splits = {}
    for pid in sorted(set(patients)):
        value = int(hashlib.sha256(f"{seed}:{pid}".encode()).hexdigest()[:8], 16) / 2**32
        splits[pid] = "train" if value < .7 else "val" if value < .85 else "test"
    write_json(output, {"protocol": "patient_sha256_70_15_15_custom_not_official", "seed": seed, "patients": splits})
    return splits


def prepare_camus(root, output, config, split_path, limit=None):
    root, output = Path(root), Path(output)
    folders = sorted(p for p in root.glob("patient*") if p.is_dir() and (p / ".download_complete.json").exists())
    if not folders:
        # Also accept data from a user's existing download.
        folders = sorted(p for p in root.glob("patient*") if p.is_dir())
    splits = read_json(split_path)["patients"] if Path(split_path).exists() else make_splits([f"patient{i:04}" for i in range(1, 501)], split_path)
    rows, failures = [], []
    for folder in folders[:limit] if limit else folders:
        if folder.name not in splits:
            raise ValueError("unknown patient; update reviewed split manifest")
        for view in ("2CH", "4CH"):
            try:
                frames, masks, labeled, source = read_camus(folder, view)
                setting = config.get("overrides", {}).get(f"{folder.name}_{view}", config.get("default", config))
                x, y, audit = process(frames, setting, source, masks)
                # Spatially transformed medical header remains in source; no inferred temporal units.
                output.mkdir(parents=True, exist_ok=True)
                key = f"{folder.name}_{view}"
                np.savez_compressed(output / (key + ".npz"), frames=x, masks=y, labeled=labeled)
                meta = {**source, "audit": audit, "preprocess_config": setting, "split": splits[folder.name]}
                write_json(output / (key + ".json"), meta)
                rows.append({"case_id": key, "patient_id": folder.name, "view": view, "split": splits[folder.name],
                             "frames": len(x), "labeled_frames": int(labeled.sum()), "issues": audit["issues"]})
            except Exception as e:
                failures.append({"case_id": f"{folder.name}_{view}", "error": str(e)})
    write_json(output / "manifest.json", {"cases": rows, "failures": failures})
    return {"cases": len(rows), "failures": failures}
