"""对话接口（已废弃，请使用 /api/query）。

旧版 NL2SQL 接口，基于 users/products/orders 表结构。
新版已迁移至 app.api.routers.query_router -> /api/query。
保留空路由避免 404，但不再处理业务逻辑。
"""
from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("")
async def chat_deprecated():
    return {"type": "error", "error": "该接口已废弃，请使用 /api/query"}


@router.post("/stream")
async def chat_stream_deprecated():
    return {"type": "error", "error": "该接口已废弃，请使用 /api/query"}
