"""对话导出与分享服务。

支持：
- 导出对话为 Markdown / JSON
- 生成只读分享链接（带过期时间）
"""
from __future__ import annotations

import hashlib
import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import text

from app.database import app_engine

logger = logging.getLogger(__name__)

SHARE_TTL_HOURS = 168  # 分享链接默认 7 天有效


def _init_share_table() -> None:
    with app_engine.begin() as conn:
        conn.execute(
            text("""
                CREATE TABLE IF NOT EXISTS share_links (
                    share_id TEXT PRIMARY KEY,
                    conversation_id INTEGER NOT NULL,
                    title TEXT,
                    content_json TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    expires_at DATETIME NOT NULL
                )
            """)
        )
        conn.execute(
            text("""
                CREATE INDEX IF NOT EXISTS idx_share_links_expires
                ON share_links(expires_at)
            """)
        )


def conversation_to_markdown(messages: list[dict[str, Any]], title: str = "对话记录") -> str:
    """将对话转换为 Markdown 格式。"""
    lines: list[str] = []
    lines.append(f"# {title}")
    lines.append("")
    lines.append(f"> 导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")

    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "")
        sql = msg.get("sql")
        summary = msg.get("summary")
        error = msg.get("error")

        if role == "user":
            lines.append("## 👤 用户")
            lines.append(content)
        elif role == "assistant":
            if error:
                lines.append("## 🤖 助手 (出错)")
                lines.append(f"**错误:** {error}")
            else:
                lines.append("## 🤖 助手")
                if summary:
                    lines.append(summary)
                elif content:
                    lines.append(content)
                if sql:
                    lines.append("")
                    lines.append("**SQL:**")
                    lines.append(f"```sql\n{sql}\n```")
        lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)


def conversation_to_json(messages: list[dict[str, Any]], title: str = "对话记录") -> str:
    """将对话转换为 JSON 格式。"""
    data = {
        "title": title,
        "exported_at": datetime.now().isoformat(),
        "messages": messages,
    }
    return json.dumps(data, ensure_ascii=False, indent=2, default=str)


def create_share_link(conversation_id: int, messages: list[dict[str, Any]], title: str | None = None) -> str:
    """创建分享链接，返回 share_id。"""
    _init_share_table()
    share_id = hashlib.sha256(f"{conversation_id}-{uuid.uuid4().hex}".encode()).hexdigest()[:16]
    expires = datetime.utcnow() + timedelta(hours=SHARE_TTL_HOURS)

    content = {
        "conversation_id": conversation_id,
        "title": title or f"对话 #{conversation_id}",
        "messages": messages,
        "created_at": datetime.now().isoformat(),
    }

    with app_engine.begin() as conn:
        conn.execute(
            text("""
                INSERT INTO share_links (share_id, conversation_id, title, content_json, expires_at)
                VALUES (:share_id, :conversation_id, :title, :content, :expires)
            """),
            {
                "share_id": share_id,
                "conversation_id": conversation_id,
                "title": content["title"],
                "content": json.dumps(content, ensure_ascii=False, default=str),
                "expires": expires.isoformat(),
            },
        )

    return share_id


def get_share_content(share_id: str) -> dict[str, Any] | None:
    """获取分享内容。"""
    _init_share_table()
    with app_engine.begin() as conn:
        row = conn.execute(
            text("""
                SELECT content_json FROM share_links
                WHERE share_id = :share_id AND expires_at > CURRENT_TIMESTAMP
            """),
            {"share_id": share_id},
        ).mappings().fetchone()

    if not row:
        return None

    try:
        return json.loads(row["content_json"])
    except json.JSONDecodeError:
        return None


def delete_share_link(share_id: str) -> bool:
    """删除分享链接。"""
    _init_share_table()
    with app_engine.begin() as conn:
        result = conn.execute(
            text("DELETE FROM share_links WHERE share_id = :share_id"),
            {"share_id": share_id},
        )
        return (result.rowcount or 0) > 0


def clear_expired_shares() -> int:
    """清理过期分享链接。"""
    _init_share_table()
    with app_engine.begin() as conn:
        result = conn.execute(
            text("DELETE FROM share_links WHERE expires_at <= CURRENT_TIMESTAMP")
        )
        return result.rowcount or 0
