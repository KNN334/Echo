from typing import Literal

from fastapi import APIRouter, Request, status
from pydantic import UUID4, BaseModel, ValidationError
from python_multipart.exceptions import MultipartParseError
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import UploadFile
from starlette.formparsers import MultiPartException, MultiPartParser
from starlette.requests import ClientDisconnect

from ..core import ServiceError
from ..schemas import InferenceRequest, InferenceResult, InferenceStatus, UploadResult
from ..services.uploads import allowed_formats

router = APIRouter(prefix="/api", tags=["上传与推理"])
DISABLED = "阶段一推理未启用，上传文件仅校验与存档"


class UploadForm(BaseModel):
    deidentified: Literal["true"]


class RequestTooLarge(MultiPartException):
    pass


async def limited_stream(request: Request, limit: int):
    size = 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > limit:
            raise RequestTooLarge("request exceeds size limit")
        yield chunk


@router.post("/upload", response_model=UploadResult, status_code=status.HTTP_201_CREATED, openapi_extra={
    "requestBody": {"required": True, "content": {"multipart/form-data": {"schema": {
        "type": "object", "required": ["file", "deidentified"], "properties": {
            "file": {"type": "string", "format": "binary"}, "deidentified": {"type": "boolean"},
        },
    }}}},
})
async def upload(request: Request):
    settings = request.app.state.settings
    if not settings.uploads_enabled or not allowed_formats(settings):
        raise ServiceError(403, "此环境未开启上传")
    origin = request.headers.get("origin")
    if origin and origin not in settings.cors_origins:
        raise ServiceError(403, "该前端来源未获准提交上传")
    if request.headers.get("content-type", "").split(";", 1)[0].strip().lower() != "multipart/form-data":
        raise ServiceError(415, "请使用 multipart/form-data 上传影像或压缩包")
    limit = settings.upload_max_bytes + 64 * 1024
    length = request.headers.get("content-length")
    if length is not None and (not length.isdecimal() or len(length) > 20 or int(length) > limit):
        raise ServiceError(413, "上传请求超过大小限制")
    parser = MultiPartParser(request.headers, limited_stream(request, limit), max_files=1, max_fields=1, max_part_size=32)
    try:
        form = await parser.parse()
    except RequestTooLarge as exc:
        raise ServiceError(413, "上传请求超过大小限制") from exc
    except (MultiPartException, MultipartParseError, ClientDisconnect) as exc:
        raise ServiceError(400, "上传请求不完整或格式无效") from exc
    try:
        file = form.get("file")
        if not isinstance(file, UploadFile):
            raise ServiceError(422, "未收到影像文件")
        try:
            UploadForm.model_validate({"deidentified": form.get("deidentified")})
        except ValidationError as exc:
            raise ServiceError(422, "请确认材料已去除患者身份信息") from exc
        return await run_in_threadpool(request.app.state.uploads.save, file)
    finally:
        await form.close()


@router.post("/inference/{case_id}", response_model=InferenceResult, responses={501: {"description": DISABLED}})
def inference(case_id: UUID4, options: InferenceRequest | None = None):
    if options and options.case_id is not None and options.case_id != case_id:
        raise ServiceError(422, "请求体和路径的病例 ID 不一致")
    raise ServiceError(501, DISABLED)


@router.get("/inference/{case_id}/status", response_model=InferenceStatus)
def inference_status(case_id: UUID4, request: Request):
    if not request.app.state.uploads.exists(case_id):
        raise ServiceError(404, "找不到该上传病例")
    return InferenceStatus(case_id=case_id, status="disabled", detail=DISABLED)
