"""对话接口。"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_app_db
from app.models import Conversation, Message
from app.schemas import ChatRequest, ChatResponse
from app.services.nl2sql import NL2SQLError, get_nl2sql_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
def chat(payload: ChatRequest, db: Session = Depends(get_app_db)) -> ChatResponse:
    if payload.conversation_id:
        conversation = db.get(Conversation, payload.conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="会话不存在")
    else:
        title = payload.question[:30] + ("…" if len(payload.question) > 30 else "")
        conversation = Conversation(title=title)
        db.add(conversation)
        db.flush()

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
        err_msg = Message(
            conversation_id=conversation.id,
            role="assistant",
            content="抱歉，服务出现异常。",
            error=str(exc),
        )
        db.add(err_msg)
        db.commit()
        raise HTTPException(status_code=500, detail=str(exc)) from exc

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
