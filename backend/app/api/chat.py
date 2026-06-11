"""对话接口（兼容层）。

旧版 /api/chat 和 /api/chat/stream 已迁移至 /api/query。
保留兼容路由，转发到新版 QueryService，避免前端改动。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from starlette.responses import StreamingResponse

from app.api.dependencies import get_query_service
from app.api.schemas.query_schema import QuerySchema
from app.services.intent_classifier import classify_intent, get_intent_suggestions
from app.services.query_service import QueryService

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("")
async def chat_compat(
    request: Request,
    query_service: QueryService = Depends(get_query_service),
):
    """兼容旧版 /api/chat，转发到新版 query 服务。"""
    body = await request.json()
    query_text = body.get("question", "")
    return StreamingResponse(
        query_service.query(query_text), media_type="text/event-stream"
    )


@router.post("/stream")
async def chat_stream_compat(
    request: Request,
    query_service: QueryService = Depends(get_query_service),
):
    """兼容旧版 /api/chat/stream，转发到新版 query 服务。"""
    body = await request.json()
    query_text = body.get("question", "")
    return StreamingResponse(
        query_service.query(query_text), media_type="text/event-stream"
    )


# ========== 意图识别接口 ==========

@router.post("/intent")
async def detect_intent(request: Request) -> dict:
    """识别用户查询意图。
    
    返回意图类型、置信度和建议。
    """
    body = await request.json()
    question = body.get("question", "")
    result = classify_intent(question)
    result["suggestions"] = get_intent_suggestions(result["intent"])
    return result
