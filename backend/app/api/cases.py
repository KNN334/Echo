from typing import Annotated, Literal

from fastapi import APIRouter, Path, Request, Response, status
from fastapi.responses import FileResponse
from pydantic import UUID4, BaseModel, ValidationError
from python_multipart.exceptions import MultipartParseError
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import UploadFile
from starlette.formparsers import MultiPartException, MultiPartParser
from starlette.requests import ClientDisconnect

from ..core import ServiceError
from ..schemas import InferenceRequest, InferenceResult, InferenceStatus, UploadResult
from ..services.inference import DISABLED
from ..services.uploads import allowed_formats

router = APIRouter(prefix="/api", tags=["上传与推理"])
PRIVATE = {"Cache-Control": "private, no-store", "Referrer-Policy": "no-referrer"}


class UploadForm(BaseModel):
    deidentified: Literal["true"]


class RequestTooLarge(MultiPartException):
    pass


def check_origin(request: Request):
    origin = request.headers.get("origin")
    if origin and origin not in request.app.state.settings.cors_origins:
        raise ServiceError(403, "该前端来源未获准提交上传或推理")


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
async def upload(request: Request, response: Response, for_inference: bool = False):
    response.headers.update(PRIVATE)
    settings = request.app.state.settings
    if not settings.uploads_enabled or not allowed_formats(settings):
        raise ServiceError(403, "此环境未开启上传")
    check_origin(request)
    jobs = request.app.state.jobs
    if for_inference and not jobs.enabled:
        raise ServiceError(503, DISABLED)
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
        return await run_in_threadpool(request.app.state.uploads.save, file,
                                       inference_formats=jobs.formats if for_inference else None)
    finally:
        await form.close()


@router.post("/inference/{case_id}", response_model=InferenceStatus, status_code=202, responses={501: {"description": DISABLED}})
def inference(case_id: UUID4, request: Request, response: Response, options: InferenceRequest | None = None):
    response.headers.update(PRIVATE)
    check_origin(request)
    if options and options.case_id is not None and options.case_id != case_id:
        raise ServiceError(422, "请求体和路径的病例 ID 不一致")
    return request.app.state.jobs.submit(case_id, options or InferenceRequest())


@router.get("/inference/{case_id}/status", response_model=InferenceStatus)
def inference_status(case_id: UUID4, request: Request, response: Response):
    response.headers.update(PRIVATE)
    return request.app.state.jobs.status(case_id)


@router.get("/inference/{case_id}/result", response_model=InferenceResult)
def inference_result(case_id: UUID4, request: Request, response: Response):
    response.headers.update(PRIVATE)
    return request.app.state.jobs.result(case_id)


@router.get("/inference/{case_id}/sheets/{index}", response_class=FileResponse)
def inference_sheet(case_id: UUID4, index: Annotated[int, Path(ge=0)], request: Request):
    path = request.app.state.jobs.sheet(case_id, index)
    return FileResponse(path, media_type="image/webp", headers=PRIVATE)
