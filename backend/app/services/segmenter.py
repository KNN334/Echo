from math import isfinite
from pathlib import Path
from time import perf_counter
from uuid import UUID

import cv2
import numpy as np
import onnxruntime as ort
from PIL import Image, ImageOps

from ..config import Settings
from ..core import ServiceError
from ..model_spec import CONTEXT_FRAMES, MODEL_HW, SOURCE_SHA256, sha256
from ..schemas import Atlas, InferenceResult

MAX_SOURCE_PIXELS = 4096 * 2160
ATLAS_COLUMNS = 4
ATLAS_ROWS = 4


def check_size(width: int, height: int):
    if width > 0 and height > 0 and width * height > MAX_SOURCE_PIXELS:
        raise ServiceError(422, "影像分辨率过高，请使用较小的导出尺寸")


def resized(frame: np.ndarray, size: tuple[int, int]) -> np.ndarray:
    return np.asarray(Image.fromarray(frame).resize(size, Image.Resampling.BILINEAR))


def prepare_frames(path: Path, max_frames: int):
    model_frames, preview_frames = [], []

    def append(gray: np.ndarray):
        height, width = gray.shape
        check_size(width, height)
        scale = min(1, 480 / width, 360 / height)
        preview_size = (max(1, round(width * scale)), max(1, round(height * scale)))
        if preview_frames and preview_frames[0].shape != preview_size[::-1]:
            raise ServiceError(422, "单段视频的帧尺寸应保持一致")
        preview_frames.append(resized(gray, preview_size))
        model_frames.append(resized(gray, MODEL_HW[::-1]))

    if path.suffix in {".png", ".jpg", ".jpeg"}:
        try:
            with Image.open(path) as image:
                check_size(*image.size)
                append(np.asarray(ImageOps.exif_transpose(image).convert("L")))
        except (OSError, Image.DecompressionBombError) as exc:
            raise ServiceError(422, "无法解码上传的图像") from exc
        return np.stack(model_frames), preview_frames, None

    # Use the file decoder in presentation order, including frames without labels.
    capture = cv2.VideoCapture(str(path), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    try:
        if not capture.isOpened():
            raise ServiceError(422, "无法解码该视频，请导出为 H.264 MP4 后重试")
        check_size(int(capture.get(cv2.CAP_PROP_FRAME_WIDTH)), int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT)))
        declared = capture.get(cv2.CAP_PROP_FRAME_COUNT)
        if declared > max_frames:
            raise ServiceError(422, f"视频超过 {max_frames} 帧，请截取较短的片段")
        fps = capture.get(cv2.CAP_PROP_FPS)
        while True:
            ok, frame = capture.read()
            if not ok:
                break
            if len(model_frames) == max_frames:
                raise ServiceError(422, f"视频超过 {max_frames} 帧，请截取较短的片段")
            append(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY))
    finally:
        capture.release()
    if not model_frames or (isfinite(declared) and declared > 0 and len(model_frames) < int(declared)):
        raise ServiceError(422, "无法完整解码该视频，请重新导出后再试")
    return np.stack(model_frames), preview_frames, float(fps) if isfinite(fps) and 0 < fps <= 240 else None


def write_sheets(directory: Path, case_id: UUID, previews, masks):
    height, width = previews[0].shape
    atlas = Atlas(columns=ATLAS_COLUMNS, rows=ATLAS_ROWS, width=2 * width, height=height)
    per_sheet = atlas.columns * atlas.rows
    urls = []
    for sheet, start in enumerate(range(0, len(previews), per_sheet)):
        grid = Image.new("RGB", (atlas.columns * atlas.width, atlas.rows * atlas.height))
        for offset, image in enumerate(previews[start:start + per_sheet]):
            x = (offset % atlas.columns) * atlas.width
            y = (offset // atlas.columns) * atlas.height
            original = Image.fromarray(image).convert("RGB")
            overlay = np.array(original)
            mask = cv2.resize(masks[start + offset].astype(np.uint8), (width, height), interpolation=cv2.INTER_NEAREST).astype(bool)
            overlay[mask] = np.rint(0.60 * overlay[mask] + 0.40 * np.array([45, 235, 100])).astype(np.uint8)
            grid.paste(original, (x, y))
            grid.paste(Image.fromarray(overlay), (x + width, y))
        grid.save(directory / f"sheet-{sheet}.webp", quality=86, method=3)
        urls.append(f"/api/inference/{case_id}/sheets/{sheet}")
    return atlas, urls


class DraSegmenter:
    def __init__(self, settings: Settings):
        path = settings.inference_checkpoint
        expected = settings.inference_sha256
        if path is None or (expected and sha256(path) != expected.lower()):
            raise ValueError("Private ONNX model SHA-256 mismatch")
        self.max_frames = settings.inference_max_frames
        cv2.setNumThreads(1)
        options = ort.SessionOptions()
        options.intra_op_num_threads = 1
        options.inter_op_num_threads = 1
        self.session = ort.InferenceSession(str(path), sess_options=options, providers=["CPUExecutionProvider"])
        metadata = self.session.get_modelmeta().custom_metadata_map
        if metadata.get("checkpoint_sha256") != SOURCE_SHA256:
            raise ValueError("Private ONNX model is not from the published DRA-UNet checkpoint")

    def predict(self, frames, progress):
        masks = np.empty(frames.shape, dtype=bool)
        clip = np.zeros((1, CONTEXT_FRAMES, 1, *MODEL_HW), dtype=np.uint8)
        for index in range(len(frames)):
            context = frames[max(0, index - CONTEXT_FRAMES + 1):index + 1]
            clip.fill(0)
            clip[0, -len(context):, 0] = context
            lengths = np.array([len(context)], dtype=np.int64)
            masks[index] = self.session.run(["mask"], {"clip": clip, "lengths": lengths})[0][0]
            progress(index + 1, len(frames))
        return masks

    def segment(self, path: Path, directory: Path, case_id: UUID, view, progress) -> InferenceResult:
        started = perf_counter()
        frames, previews, fps = prepare_frames(path, self.max_frames)
        progress(0, len(frames))
        masks = self.predict(frames, progress)
        atlas, urls = write_sheets(directory, case_id, previews, masks)
        nonempty = int(np.count_nonzero(masks.any(axis=(1, 2))))
        flags = []
        if nonempty < len(frames):
            flags.append("部分帧未得到左心室掩膜，请核对影像切面和图像质量" if nonempty else "所有帧的左心室掩膜均为空，请核对影像切面和图像质量")
        return InferenceResult(case_id=case_id, view=view, frames=len(frames), nonempty_masks=nonempty,
                               playback_fps=fps, atlas=atlas, sheet_urls=urls, quality_flags=flags,
                               elapsed_s=perf_counter() - started)
