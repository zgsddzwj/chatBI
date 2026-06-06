"""FastAPI 应用入口。"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from starlette.middleware.gzip import GZipMiddleware

from app.api import auth, chat, conversations, dashboard, datasource, export, feedback, meta, tasks
from app.config import get_settings
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


@asynccontextmanager
async def lifespan(_app: FastAPI):
    from app import models  # noqa: F401
    from app.services.cache import clear_expired
    from app.services.hybrid_search import warmup

    AppBase.metadata.create_all(bind=app_engine)
    run_migrations()
    cleared = clear_expired()
    if cleared:
        logger.info("启动时清理过期缓存 %d 条", cleared)
    # 预热混合检索索引
    warmup()
    yield


app = FastAPI(
    title="ChatBI API",
    description="自然语言对话式 BI 后端",
    version="0.4.0",
    lifespan=lifespan,
)

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


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    if isinstance(exc, HTTPException):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
    logger.exception("未处理异常: %s %s", request.method, request.url.path)
    detail = "服务出现异常，请稍后重试" if settings.is_production else str(exc)
    return JSONResponse(status_code=500, content={"detail": detail})


@app.get("/health", tags=["system"])
def health() -> dict:
    """存活探针：仅表示进程可响应，不访问数据库。"""
    return {"status": "ok", "service": "chatbi-backend"}


@app.get("/ready", tags=["system"])
def ready() -> JSONResponse:
    """就绪探针：校验应用库可连接（编排系统可据此摘流）。"""
    try:
        with app_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001
        logger.exception("就绪检查失败: %s", exc)
        return JSONResponse(
            status_code=503,
            content={
                "status": "not_ready",
                "app_db": False,
                "error": str(exc) if not settings.is_production else "database unavailable",
            },
        )
    return JSONResponse(
        status_code=200,
        content={"status": "ready", "app_db": True},
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
