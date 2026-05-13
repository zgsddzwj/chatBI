"""FastAPI 应用入口。"""
from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import chat, conversations, meta
from app.config import get_settings
from app.database import AppBase, app_engine

settings = get_settings()

logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)

app = FastAPI(
    title="ChatBI API",
    description="自然语言对话式 BI 后端",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _on_startup() -> None:
    from app import models  # noqa: F401
    AppBase.metadata.create_all(bind=app_engine)


@app.get("/health", tags=["system"])
def health() -> dict:
    return {"status": "ok"}


app.include_router(chat.router)
app.include_router(conversations.router)
app.include_router(meta.router)
