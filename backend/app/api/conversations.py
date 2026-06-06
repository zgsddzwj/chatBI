"""会话管理接口。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import desc, or_
from sqlalchemy.orm import Session

from app.api.deps import get_conversation_or_404, get_optional_user_id
from app.database import get_app_db
from app.models import Conversation
from app.schemas import ConversationDetail, ConversationOut

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


@router.get("", response_model=list[ConversationOut])
def list_conversations(request: Request, db: Session = Depends(get_app_db)) -> list[Conversation]:
    user_id = get_optional_user_id(request)
    query = db.query(Conversation)
    if user_id is not None:
        query = query.filter(Conversation.user_id == user_id)
    else:
        query = query.filter(Conversation.user_id.is_(None))
    return query.order_by(desc(Conversation.updated_at)).limit(50).all()


@router.get("/{conversation_id}", response_model=ConversationDetail)
def get_conversation(
    conversation_id: int,
    request: Request,
    db: Session = Depends(get_app_db),
) -> Conversation:
    user_id = get_optional_user_id(request)
    conv = get_conversation_or_404(db, conversation_id, user_id)
    conv.messages.sort(key=lambda m: m.created_at)
    return conv


@router.delete("/{conversation_id}")
def delete_conversation(
    conversation_id: int,
    request: Request,
    db: Session = Depends(get_app_db),
) -> dict:
    user_id = get_optional_user_id(request)
    conv = get_conversation_or_404(db, conversation_id, user_id)
    db.delete(conv)
    db.commit()
    return {"ok": True}
