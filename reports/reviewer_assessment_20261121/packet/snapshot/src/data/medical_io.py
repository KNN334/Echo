"""通用医疗影像、视频和 EchoNet 轮廓读取。"""
from pathlib import Path
import csv
import numpy as np
from ..utils.hash import sha256


def read_medical(path):
    """读取医疗影像帧及头信息中的物理间距和方向来源。"""
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

def read_video(path, sidecar=None):
    """解码视频帧并记录容器帧率、时间戳及文件校验值。"""
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
    """按官方轮廓点顺序生成 EchoNet 掩膜，直接采用 CSV 帧号而不平移编号。"""
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
