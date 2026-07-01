"""FastAPI 应用入口。"""
from __future__ import annotations

import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from starlette.middleware.gzip import GZipMiddleware

from app.api import auth, chat, conversations, dashboard, datasource, export, feedback, meta, tasks
from app.api.routers.query_router import query_router
from app.config import get_settings
from app.core.context import request_id_ctx_var
from app.core.lifespan import lifespan
from app.database import AppBase, app_engine
from app.middleware.http import RequestIdMiddleware, SecurityHeadersMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.migrations import run_migrations

settings = get_settings()

logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="ChatBI API",
    description="自然语言对话式 BI 后端",
    version="0.5.0",
    lifespan=lifespan,
)

@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id_ctx_var.set(str(uuid.uuid4()))
    response = await call_next(request)
    return response

app.add_middleware(RequestIdMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(GZipMiddleware, minimum_size=512)
app.add_middleware(
    RateLimitMiddleware,
    max_requests=settings.rate_limit_requests,
    window_seconds=settings.rate_limit_window_seconds,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["system"])
def health() -> dict:
    """存活探针：仅表示进程可响应，不访问数据库。"""
    return {"status": "ok", "service": "chatbi-backend", "version": "0.5.0"}


@app.get("/ready", tags=["system"])
def ready() -> JSONResponse:
    """就绪探针：校验应用库可连接（编排系统可据此摘流）。"""
    checks: dict[str, bool] = {}

    # 检查应用数据库
    try:
        with app_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        checks["app_db"] = True
    except Exception as exc:  # noqa: BLE001
        logger.exception("就绪检查失败: %s", exc)
        checks["app_db"] = False

    # 检查业务数据库（SQLite mock 数据）
    try:
        from app.database import business_engine
        with business_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        checks["business_db"] = True
    except Exception:  # noqa: BLE001
        checks["business_db"] = False

    # 检查向量索引
    try:
        from app.services.hybrid_search import _get_vector_index
        idx = _get_vector_index()
        checks["vector_index"] = len(idx.ids) > 0
    except Exception:  # noqa: BLE001
        checks["vector_index"] = False

    all_ok = all(checks.values())
    status_code = 200 if all_ok else 503
    status = "ready" if all_ok else "not_ready"

    return JSONResponse(
        status_code=status_code,
        content={
            "status": status,
            "checks": checks,
        },
    )


app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(conversations.router)
app.include_router(dashboard.router)
app.include_router(datasource.router)
app.include_router(export.router)
app.include_router(feedback.router)
app.include_router(meta.router)
app.include_router(tasks.router)
app.include_router(query_router)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    if isinstance(exc, HTTPException):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
    logger.exception("未处理异常: %s %s", request.method, request.url.path)
    detail = "服务出现异常，请稍后重试" if settings.is_production else str(exc)
    return JSONResponse(status_code=500, content={"detail": detail})
