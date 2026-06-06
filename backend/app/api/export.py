"""导出与分享接口。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.api.deps import get_conversation_or_404, get_optional_user_id
from app.database import get_app_db
from app.services.export import (
    conversation_to_json,
    conversation_to_markdown,
    create_share_link,
    get_share_content,
)

router = APIRouter(prefix="/api/export", tags=["export"])


@router.get("/conversation/{conversation_id}/markdown")
def export_markdown(
    conversation_id: int,
    request: Request,
    db: Session = Depends(get_app_db),
) -> PlainTextResponse:
    """导出对话为 Markdown。"""
    user_id = get_optional_user_id(request)
    conv = get_conversation_or_404(db, conversation_id, user_id)

    messages = [
        {
            "role": m.role,
            "content": m.content,
            "sql": m.sql,
            "summary": m.summary,
            "error": m.error,
            "chart": m.chart,
            "result": m.result,
        }
        for m in sorted(conv.messages, key=lambda x: x.created_at)
    ]

    md = conversation_to_markdown(messages, title=conv.title)
    return PlainTextResponse(
        content=md,
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="chatbi-conversation-{conversation_id}.md"'},
    )


@router.get("/conversation/{conversation_id}/json")
def export_json(
    conversation_id: int,
    request: Request,
    db: Session = Depends(get_app_db),
) -> PlainTextResponse:
    """导出对话为 JSON。"""
    user_id = get_optional_user_id(request)
    conv = get_conversation_or_404(db, conversation_id, user_id)

    messages = [
        {
            "role": m.role,
            "content": m.content,
            "sql": m.sql,
            "summary": m.summary,
            "error": m.error,
            "chart": m.chart,
            "result": m.result,
        }
        for m in sorted(conv.messages, key=lambda x: x.created_at)
    ]

    json_str = conversation_to_json(messages, title=conv.title)
    return PlainTextResponse(
        content=json_str,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="chatbi-conversation-{conversation_id}.json"'},
    )


@router.post("/conversation/{conversation_id}/share")
def create_share(
    conversation_id: int,
    request: Request,
    db: Session = Depends(get_app_db),
) -> dict:
    """创建分享链接。"""
    user_id = get_optional_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="请先登录")

    conv = get_conversation_or_404(db, conversation_id, user_id)

    messages = [
        {
            "role": m.role,
            "content": m.content,
            "sql": m.sql,
            "summary": m.summary,
            "error": m.error,
            "chart": m.chart,
            "result": m.result,
        }
        for m in sorted(conv.messages, key=lambda x: x.created_at)
    ]

    share_id = create_share_link(conversation_id, messages, title=conv.title)
    return {
        "share_id": share_id,
        "url": f"/api/export/share/{share_id}",
        "expires_in_hours": 168,
    }


@router.get("/share/{share_id}")
def get_share(share_id: str) -> dict:
    """获取分享内容（公开访问，无需登录）。"""
    content = get_share_content(share_id)
    if not content:
        raise HTTPException(status_code=404, detail="分享链接不存在或已过期")
    return content
