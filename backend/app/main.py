import logging
from contextlib import asynccontextmanager
from time import perf_counter

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .api import cases, reports
from .config import Settings
from .core import ServiceError
from .repositories import InMemoryReports
from .schemas import Health
from .services.uploads import LocalUploads, allowed_formats

logger = logging.getLogger("uvicorn.error")


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.settings = settings
        app.state.reports = InMemoryReports(settings)
        app.state.uploads = LocalUploads(settings)
        yield

    app = FastAPI(title="超声智能心脏功能评估系统", description="公开影像研究报表与去标识文件存档。研究基线 · 非临床验证", lifespan=lifespan)

    @app.middleware("http")
    async def log_request(request: Request, call_next):
        start = perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            route = getattr(request.scope.get("route"), "path", "unmatched")
            logger.exception("%s %s failed", request.method, route)
            response = JSONResponse({"detail": "服务暂时无法完成请求"}, status_code=500)
        route = getattr(request.scope.get("route"), "path", "unmatched")
        logger.info("%s %s %s %.1fms", request.method, route, response.status_code, (perf_counter() - start) * 1000)
        return response

    app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_methods=["GET", "POST"],
                       allow_headers=["Content-Type"])

    @app.exception_handler(ServiceError)
    async def service_error(_request: Request, exc: ServiceError):
        return JSONResponse({"detail": exc.detail}, status_code=exc.status)

    @app.exception_handler(RequestValidationError)
    async def validation_error(_request: Request, exc: RequestValidationError):
        fields = ", ".join(sorted({str(error["loc"][-1]) for error in exc.errors() if error["loc"]}))
        return JSONResponse({"detail": f"请求参数无效（{fields or '请检查格式'}）"}, status_code=422)

    @app.get("/api/health", response_model=Health, tags=["运行状态"])
    def health(request: Request):
        status = request.app.state.reports.status
        formats = allowed_formats(settings)
        return Health(status="ok" if all(value == "loaded" for value in status.values()) else "degraded",
                      reports=status, uploads_enabled=settings.uploads_enabled and bool(formats),
                      upload_max_bytes=settings.upload_max_bytes, upload_formats=formats)

    app.include_router(reports.router)
    app.include_router(cases.router)
    return app


app = create_app()
