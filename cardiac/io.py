"""CAMUS NIfTI/MetaImage and external AVI; physical calibration is explicit."""
from pathlib import Path
import csv
import numpy as np
from .common import sha256


def read_medical(path):
    import SimpleITK as sitk
    image = sitk.ReadImage(str(path))
    data = sitk.GetArrayFromImage(image)
    if data.ndim == 2:
        data = data[None]
    if data.ndim != 3:
        raise ValueError(f"expected 2D/sequence medical image: {path}")
    return data, {"spacing_xy_mm": list(image.GetSpacing()[:2]),
                  "origin": list(image.GetOrigin()), "direction": list(image.GetDirection()),
                  "raw_spacing": list(image.GetSpacing()),
                  "source": {"spacing": "medical_image_header", "sha256": sha256(path)}}


def read_config(path):
    result = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                result[k.strip()] = v.strip()
    return result


def locate(folder, stem):
    for ext in (".nii.gz", ".mhd", ".nii"):
        p = folder / (stem + ext)
        if p.exists():
            return p
    return None


def read_camus(folder, view):
    folder = Path(folder)
    pid = folder.name
    cfg = read_config(folder / f"Info_{view}.cfg")
    stem = f"{pid}_{view}"
    # Do not invent a full heartbeat from ED->ES half sequences.
    seq = locate(folder, stem + "_sequence") or locate(folder, stem + "_half_sequence")
    if seq:
        frames, meta = read_medical(seq)
        sequence_type = "half_sequence" if "half_sequence" in seq.name else "sequence"
    else:
        pairs = [read_medical(locate(folder, stem + "_" + phase)) for phase in ("ED", "ES")]
        frames = np.concatenate([a[0] for a in pairs])
        meta = pairs[0][1]
        sequence_type = "sparse_ED_ES_not_contiguous"
    masks = np.zeros(frames.shape, np.uint8)
    labeled = np.zeros(len(frames), bool)
    phases = {}
    for fallback_index, phase in enumerate(("ED", "ES")):
        path = locate(folder, stem + "_" + phase + "_gt")
        if path is None:
            continue
        index = fallback_index if seq is None else int(cfg.get(phase, 0)) - 1
        if not 0 <= index < len(frames):
            raise ValueError(f"invalid {phase} index in {folder}/{view}")
        gt, gm = read_medical(path)
        if gt.shape[1:] != frames.shape[1:] or not np.allclose(gm["spacing_xy_mm"], meta["spacing_xy_mm"]):
            raise ValueError("CAMUS label image geometry mismatch")
        masks[index] = (gt[0] == 1).astype(np.uint8)
        labeled[index] = True
        phases[phase] = index
    # Only authoritative ED/ES expert labels used; do not treat interpolated half_sequence_gt as dense truth.
    fps = float(cfg["FrameRate"]) if "FrameRate" in cfg and seq else None
    meta.update(fps=fps, sequence_type=sequence_type, phases=phases,
                config=cfg, patient_id=pid, view=view,
                gt_scope="ED_ES_only", input_path=str(seq) if seq else str(folder))
    meta["source"]["fps"] = "Info.cfg:FrameRate" if fps else "missing"
    meta["source"]["config_sha256"] = sha256(folder / f"Info_{view}.cfg") if cfg else None
    return frames, masks, labeled, meta


def read_video(path, sidecar=None):
    import cv2
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise ValueError(f"cannot open {path}")
    fps = float(cap.get(cv2.CAP_PROP_FPS))
    frames, container_t = [], []
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        frames.append(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY))
        container_t.append(cap.get(cv2.CAP_PROP_POS_MSEC) / 1000)
    cap.release()
    if not frames:
        raise ValueError("empty video")
    meta = dict(sidecar or {})
    meta.setdefault("fps", fps if np.isfinite(fps) and fps > 0 else None)
    # Container decode times aren't proof of physiological acquisition timing.
    meta["container_timestamps_s"] = container_t
    meta.setdefault("source", {})["fps"] = "sidecar" if sidecar and "fps" in sidecar else "container_rate_not_acquisition_verified"
    meta["source"]["sha256"] = sha256(path)
    return np.asarray(frames), meta


def echonet_traces(csv_path, filename, n_frames, hw):
    """Official EchoNet tracing polygon order; no frame-number offset assumed."""
    from PIL import Image, ImageDraw
    grouped = {}
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            if Path(row["FileName"]).stem != Path(filename).stem:
                continue
            grouped.setdefault(int(row["Frame"]), []).append([float(row[k]) for k in ("X1", "Y1", "X2", "Y2")])
    masks = np.zeros((n_frames, *hw), np.uint8)
    labeled = np.zeros(n_frames, bool)
    for index, lines in grouped.items():
        if not 0 <= index < n_frames:
            raise ValueError("EchoNet tracing frame outside video")
        a = np.asarray(lines)
        if len(a) < 3:
            continue
        # EchoNet official adapter uses endpoints of all cross-sections except first long axis.
        polygon = np.concatenate([a[1:, :2], a[1:, 2:][::-1]])
        im = Image.new("L", (hw[1], hw[0]))
        ImageDraw.Draw(im).polygon([tuple(x) for x in polygon], fill=1)
        masks[index] = np.asarray(im)
        labeled[index] = True
    return masks, labeled
