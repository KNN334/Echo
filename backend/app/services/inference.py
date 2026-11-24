import json
import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Lock
from uuid import UUID

from ..config import Settings
from ..core import ServiceError
from ..schemas import InferenceRequest, InferenceResult, InferenceStatus
from .uploads import LocalUploads

logger = logging.getLogger(__name__)
DISABLED = "服务器尚未启用 DRA-UNet 在线推理"
FORMATS = {".png", ".jpg", ".jpeg", ".avi", ".mp4"}


class InferenceJobs:
    def __init__(self, settings: Settings, uploads: LocalUploads):
        self.uploads = uploads
        self.formats = FORMATS.intersection(uploads.formats) if settings.uploads_enabled else set()
        self.expected = settings.inference_checkpoint is not None and bool(self.formats)
        self.segmenter = None
        if self.expected:
            try:
                from .segmenter import DraSegmenter

                self.segmenter = DraSegmenter(settings)
            except Exception:
                logger.exception("Failed to load the DRA-UNet inference service")
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="dra-inference") if self.segmenter else None
        self.lock = Lock()
        self.pending: dict[UUID, InferenceStatus] = {}

    @property
    def enabled(self) -> bool:
        return self.executor is not None

    def _directory(self, case_id: UUID) -> Path:
        if not self.uploads.exists(case_id):
            raise ServiceError(404, "找不到该上传病例")
        return self.uploads.case_dir(case_id)

    def _update(self, case_id: UUID, completed: int, total: int):
        with self.lock:
            self.pending[case_id] = InferenceStatus(case_id=case_id, status="processing",
                                                    completed_frames=completed, total_frames=total)

    def submit(self, case_id: UUID, options: InferenceRequest) -> InferenceStatus:
        if self.executor is None:
            raise ServiceError(501, DISABLED)
        directory = self._directory(case_id)
        path = next((path for path in directory.glob("original.*") if path.suffix in self.formats), None)
        if path is None:
            raise ServiceError(415, "这个存档的文件格式无法用于自动分割")
        with self.lock:
            prior = self.pending.get(case_id)
            if prior is not None:
                return prior
            if (directory / "result" / "manifest.json").is_file():
                return InferenceStatus(case_id=case_id, status="done")
            if len(self.pending) >= 2:
                raise ServiceError(429, "服务器推理队列已满，请稍后重试这个病例")
            (directory / "failure.json").unlink(missing_ok=True)
            job = InferenceStatus(case_id=case_id, status="queued")
            self.pending[case_id] = job
            self.executor.submit(self._run, case_id, path, directory, options.view)
            return job

    def _run(self, case_id: UUID, path: Path, directory: Path, view):
        detail = None
        try:
            with self.lock:
                self.pending[case_id] = InferenceStatus(case_id=case_id, status="processing")
            with TemporaryDirectory(dir=directory) as temporary:
                output = Path(temporary) / "result"
                output.mkdir()
                result = self.segmenter.segment(path, output, case_id, view,
                                                lambda completed, total: self._update(case_id, completed, total))
                (output / "manifest.json").write_text(result.model_dump_json(), encoding="utf-8")
                output.rename(directory / "result")
        except ServiceError as exc:
            detail = exc.detail
        except Exception:
            logger.exception("DRA-UNet job failed for case %s", case_id)
            detail = "分割未完成，请检查影像后重试"
        finally:
            with self.lock:
                try:
                    if detail:
                        (directory / "failure.json").write_text(json.dumps(detail, ensure_ascii=False), encoding="utf-8")
                except OSError:
                    logger.exception("Could not record failed inference for case %s", case_id)
                finally:
                    self.pending.pop(case_id, None)

    def status(self, case_id: UUID) -> InferenceStatus:
        directory = self._directory(case_id)
        with self.lock:
            if case_id in self.pending:
                return self.pending[case_id]
            if (directory / "result" / "manifest.json").is_file():
                return InferenceStatus(case_id=case_id, status="done")
            failure = directory / "failure.json"
            if failure.is_file():
                return InferenceStatus(case_id=case_id, status="failed", detail=json.loads(failure.read_text(encoding="utf-8")))
        if self.enabled:
            return InferenceStatus(case_id=case_id, status="ready", detail="影像已存档，可以重新提交分割")
        return InferenceStatus(case_id=case_id, status="disabled", detail=DISABLED)

    def result(self, case_id: UUID) -> InferenceResult:
        manifest = self._directory(case_id) / "result" / "manifest.json"
        if not manifest.is_file():
            raise ServiceError(404, "分割结果尚未生成")
        return InferenceResult.model_validate_json(manifest.read_bytes())

    def sheet(self, case_id: UUID, index: int) -> Path:
        path = self.uploads.case_dir(case_id) / "result" / f"sheet-{index}.webp"
        if index >= len(self.result(case_id).sheet_urls) or not path.is_file():
            raise ServiceError(404, "找不到该分割影像")
        return path

    def close(self):
        if self.executor is not None:
            self.executor.shutdown(wait=True)
