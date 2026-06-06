"""API 公共依赖：认证与会话权限。"""
from __future__ import annotations

from typing import Any

from fastapi import HTTPException, Request
from sqlalchemy.orm import Session

from app.models import Conversation
from app.services.auth import decode_access_token


def get_optional_user_id(request: Request) -> int | None:
    """从请求头提取用户 ID（可选）。"""
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        payload = decode_access_token(auth[7:])
        if payload:
            return int(payload["sub"])
    return None


def check_conversation_access(conversation: Conversation, user_id: int | None) -> None:
    """校验当前用户是否有权访问该会话。"""
    owner_id = conversation.user_id
    if owner_id is None:
        return
    if user_id is None:
        raise HTTPException(status_code=401, detail="请先登录以访问该会话")
    if owner_id != user_id:
        raise HTTPException(status_code=403, detail="无权访问该会话")


def get_conversation_or_404(
    db: Session,
    conversation_id: int,
    user_id: int | None,
) -> Conversation:
    """获取会话并校验访问权限。"""
    conversation = db.get(Conversation, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="会话不存在")
    check_conversation_access(conversation, user_id)
    return conversation


def create_conversation(db: Session, title: str, user_id: int | None) -> Conversation:
    """创建新会话并绑定用户（若已登录）。"""
    conversation = Conversation(title=title, user_id=user_id)
    db.add(conversation)
    db.flush()
    return conversation
