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


# ========== 多轮对话上下文接口 ==========

@router.post("/context/expand")
async def expand_with_context(request: Request) -> dict:
    """基于上下文扩展用户问题（指代消解）。"""
    from app.services.conversation_context import expand_question, get_context
    
    body = await request.json()
    conversation_id = body.get("conversation_id", 0)
    question = body.get("question", "")
    expanded = expand_question(conversation_id, question)
    ctx = get_context(conversation_id)
    return {
        "original": question,
        "expanded": expanded,
        "context": ctx.to_dict(),
    }


@router.get("/context/{conversation_id}")
async def get_conversation_context(conversation_id: int) -> dict:
    """获取对话上下文。"""
    from app.services.conversation_context import get_context
    ctx = get_context(conversation_id)
    return ctx.to_dict()


@router.delete("/context/{conversation_id}")
async def clear_conversation_context(conversation_id: int) -> dict:
    """清空对话上下文。"""
    from app.services.conversation_context import clear_context
    clear_context(conversation_id)
    return {"message": "上下文已清空"}


# ========== 查询建议接口 ==========

@router.get("/suggestions")
async def get_query_suggestions(
    q: str = "",
    conversation_id: int | None = None,
    limit: int = 8,
) -> dict:
    """获取查询建议。
    
    基于输入前缀、意图、热门查询、历史记录生成建议。
    """
    from app.services.query_suggestions import get_suggestions
    suggestions = get_suggestions(prefix=q, conversation_id=conversation_id, limit=limit)
    return {"suggestions": suggestions}


@router.get("/autocomplete")
async def get_autocomplete(q: str = "", limit: int = 5) -> dict:
    """查询自动补全。
    
    返回匹配前缀的建议文本列表。
    """
    from app.services.query_suggestions import get_autocomplete
    results = get_autocomplete(prefix=q, limit=limit)
    return {"results": results}
