"""对话接口。"""
from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import create_conversation, get_conversation_or_404, get_optional_user_id
from app.config import get_settings
from app.database import get_app_db
from app.models import Message
from app.schemas import ChatRequest, ChatResponse
from app.services.auth import log_audit
from app.services.nl2sql import NL2SQLError, get_nl2sql_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/chat", tags=["chat"])
settings = get_settings()


def _generic_error_message(exc: Exception) -> str:
    if settings.is_production:
        return "服务出现异常，请稍后重试"
    return str(exc)


@router.post("", response_model=ChatResponse)
def chat(payload: ChatRequest, request: Request, db: Session = Depends(get_app_db)) -> ChatResponse:
    user_id = get_optional_user_id(request)
    ip = request.client.host if request.client else None

    if payload.conversation_id:
        conversation = get_conversation_or_404(db, payload.conversation_id, user_id)
    else:
        title = payload.question[:30] + ("…" if len(payload.question) > 30 else "")
        conversation = create_conversation(db, title, user_id)

    user_msg = Message(
        conversation_id=conversation.id,
        role="user",
        content=payload.question,
    )
    db.add(user_msg)
    db.flush()

    history_payload = [h.model_dump() for h in payload.history]
    service = get_nl2sql_service()

    try:
        result = service.ask(payload.question, history=history_payload)
    except NL2SQLError as exc:
        logger.warning("NL2SQL 失败: %s", exc)
        log_audit(user_id, "chat_error", resource=f"conv:{conversation.id}", detail=str(exc)[:200], ip=ip)
        err_msg = Message(
            conversation_id=conversation.id,
            role="assistant",
            content="抱歉，我没能完成这次查询。",
            error=str(exc),
        )
        db.add(err_msg)
        db.commit()
        return ChatResponse(
            type="error",
            conversation_id=conversation.id,
            message_id=err_msg.id,
            error=str(exc),
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("处理对话时发生未预期错误")
        log_audit(user_id, "chat_error", resource=f"conv:{conversation.id}", detail=str(exc)[:200], ip=ip)
        err_msg = Message(
            conversation_id=conversation.id,
            role="assistant",
            content="抱歉，服务出现异常。",
            error=_generic_error_message(exc),
        )
        db.add(err_msg)
        db.commit()
        return ChatResponse(
            type="error",
            conversation_id=conversation.id,
            message_id=err_msg.id,
            error=_generic_error_message(exc),
        )

    if result["type"] == "clarification":
        assistant_msg = Message(
            conversation_id=conversation.id,
            role="assistant",
            content=result["clarification"],
        )
        db.add(assistant_msg)
        db.commit()
        return ChatResponse(
            type="clarification",
            conversation_id=conversation.id,
            message_id=assistant_msg.id,
            clarification=result["clarification"],
        )

    assistant_msg = Message(
        conversation_id=conversation.id,
        role="assistant",
        content=result["summary"],
        sql=result["sql"],
        result=result["data"],
        chart=result["chart"],
        summary=result["summary"],
    )
    db.add(assistant_msg)
    db.commit()

    log_audit(user_id, "chat", resource=f"conv:{conversation.id}", detail=f"sql={result['sql'][:100]}", ip=ip)

    return ChatResponse(
        type="answer",
        conversation_id=conversation.id,
        message_id=assistant_msg.id,
        sql=result["sql"],
        explanation=result.get("explanation", ""),
        data=result["data"],
        chart=result["chart"],
        summary=result["summary"],
    )


@router.post("/stream")
def chat_stream(
    payload: ChatRequest,
    request: Request,
    db: Session = Depends(get_app_db),
) -> StreamingResponse:
    """SSE 流式对话：逐阶段推送 thinking / sql / data / chart / summary。"""
    user_id = get_optional_user_id(request)
    ip = request.client.host if request.client else None

    def event(data: dict) -> str:
        return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

    def generate():
        if payload.conversation_id:
            try:
                conversation = get_conversation_or_404(db, payload.conversation_id, user_id)
            except HTTPException as exc:
                yield event({"type": "error", "error": exc.detail})
                return
        else:
            title = payload.question[:30] + ("…" if len(payload.question) > 30 else "")
            conversation = create_conversation(db, title, user_id)

        user_msg = Message(
            conversation_id=conversation.id,
            role="user",
            content=payload.question,
        )
        db.add(user_msg)
        db.flush()

        yield event({"type": "thinking", "conversation_id": conversation.id})

        history_payload = [h.model_dump() for h in payload.history]
        service = get_nl2sql_service()

        try:
            sql_result = service.generate_sql(payload.question, history=history_payload)
        except NL2SQLError as exc:
            logger.warning("NL2SQL 生成 SQL 失败: %s", exc)
            log_audit(user_id, "chat_error", resource=f"conv:{conversation.id}", detail=str(exc)[:200], ip=ip)
            err_msg = Message(
                conversation_id=conversation.id,
                role="assistant",
                content="抱歉，我没能完成这次查询。",
                error=str(exc),
            )
            db.add(err_msg)
            db.commit()
            yield event({"type": "error", "conversation_id": conversation.id, "error": str(exc)})
            return

        if sql_result.get("needs_clarification"):
            clarification = sql_result.get("clarification") or "你的问题信息不够，能否补充？"
            assistant_msg = Message(
                conversation_id=conversation.id,
                role="assistant",
                content=clarification,
            )
            db.add(assistant_msg)
            db.commit()
            yield event({"type": "clarification", "conversation_id": conversation.id, "clarification": clarification})
            return

        sql = sql_result["sql"]
        explanation = sql_result.get("explanation", "")
        yield event({"type": "sql", "conversation_id": conversation.id, "sql": sql, "explanation": explanation})

        try:
            data = service.execute_sql(sql, question=payload.question)
            fixed_sql = data.pop("fixed_sql", None)
            if fixed_sql:
                sql = fixed_sql
        except NL2SQLError as exc:
            logger.warning("SQL 执行失败: %s", exc)
            log_audit(user_id, "chat_error", resource=f"conv:{conversation.id}", detail=str(exc)[:200], ip=ip)
            err_msg = Message(
                conversation_id=conversation.id,
                role="assistant",
                content="SQL 执行失败。",
                error=str(exc),
            )
            db.add(err_msg)
            db.commit()
            yield event({"type": "error", "conversation_id": conversation.id, "error": str(exc)})
            return

        yield event({"type": "data", "conversation_id": conversation.id, "data": data})

        chart = service.recommend_chart(data["columns"], data["rows"])
        yield event({"type": "chart", "conversation_id": conversation.id, "chart": chart})

        if data["row_count"] > 0:
            summary = (service.summarize(payload.question, sql, data) or "").strip()
            if not summary:
                summary = f"查询完成，共返回 {data['row_count']} 行结果。"
        else:
            summary = "未查询到匹配数据。"

        for i in range(1, len(summary) + 1):
            chunk = summary[:i]
            yield event({"type": "summary_chunk", "conversation_id": conversation.id, "chunk": chunk, "done": i == len(summary)})

        assistant_msg = Message(
            conversation_id=conversation.id,
            role="assistant",
            content=summary,
            sql=sql,
            result=data,
            chart=chart,
            summary=summary,
        )
        db.add(assistant_msg)
        db.commit()

        log_audit(user_id, "chat_stream", resource=f"conv:{conversation.id}", detail=f"sql={sql[:100]}", ip=ip)
        yield event({"type": "done", "conversation_id": conversation.id, "message_id": assistant_msg.id})

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
