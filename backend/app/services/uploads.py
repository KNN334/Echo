import json
import logging
import shutil
from datetime import datetime, timezone
from pathlib import Path, PureWindowsPath
from tempfile import TemporaryDirectory
from uuid import UUID, uuid4
from zipfile import is_zipfile

from starlette.datastructures import UploadFile

from ..config import Settings
from ..core import ServiceError
from ..schemas import UploadResult

logger = logging.getLogger(__name__)
SUPPORTED_FORMATS = {".png", ".jpg", ".jpeg", ".avi", ".mp4", ".zip"}


def allowed_formats(settings: Settings) -> list[str]:
    return sorted(SUPPORTED_FORMATS.intersection(ext.lower() for ext in settings.upload_formats))


def valid_header(extension: str, upload: UploadFile) -> bool:
    prefix = upload.file.read(16)
    upload.file.seek(0)
    if extension == ".zip":
        result = is_zipfile(upload.file)
        upload.file.seek(0)
        return result
    return {
        ".png": prefix.startswith(b"\x89PNG\r\n\x1a\n") and prefix[12:16] == b"IHDR",
        ".jpg": prefix.startswith(b"\xff\xd8\xff"),
        ".jpeg": prefix.startswith(b"\xff\xd8\xff"),
        ".avi": prefix.startswith(b"RIFF") and prefix[8:12] == b"AVI ",
        ".mp4": prefix[4:8] == b"ftyp",
    }[extension]


class LocalUploads:
    def __init__(self, settings: Settings):
        self.directory = settings.upload_dir
        self.max_bytes = settings.upload_max_bytes
        self.formats = allowed_formats(settings)

    def save(self, upload: UploadFile) -> UploadResult:
        name = upload.filename or ""
        if not name or len(name) > 255 or PureWindowsPath(name).name != name or any(
            char in '/\\:<>",|?*' or ord(char) < 32 for char in name
        ):
            raise ServiceError(400, "文件名无效，请使用不含路径的去标识文件名")
        extension = Path(name).suffix.lower()
        if extension not in self.formats:
            raise ServiceError(415, "不支持此文件格式")
        size = upload.size or 0
        if size == 0:
            raise ServiceError(400, "上传文件为空")
        if size > self.max_bytes:
            raise ServiceError(413, "文件超过上传大小限制")
        if not valid_header(extension, upload):
            raise ServiceError(415, "文件内容与扩展名不符或格式无效")

        case_id = uuid4()
        result = UploadResult(case_id=case_id, size_bytes=size)
        filename = f"original{extension}"
        metadata = {**result.model_dump(mode="json"), "filename": filename,
                    "uploaded_at": datetime.now(timezone.utc).isoformat(), "deidentified_attestation": True}
        try:
            self.directory.mkdir(parents=True, exist_ok=True)
            with TemporaryDirectory(dir=self.directory) as temporary:
                pending = Path(temporary) / "case"
                pending.mkdir()
                with (pending / filename).open("xb") as output:
                    shutil.copyfileobj(upload.file, output)
                (pending / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
                pending.rename(self.directory / str(case_id))
        except OSError as exc:
            logger.error("Upload storage failed for case %s (%s)", case_id, type(exc).__name__)
            raise ServiceError(503, "上传存储暂不可用") from exc
        logger.info("Saved upload %s (%s bytes)", case_id, size)
        return result

    def exists(self, case_id: UUID) -> bool:
        return (self.directory / str(case_id) / "metadata.json").is_file()
