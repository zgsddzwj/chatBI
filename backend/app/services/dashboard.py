"""仪表盘服务：收藏对话中的图表，组合成仪表盘卡片。

支持：
- 收藏消息中的图表（创建卡片）
- 管理仪表盘（创建、更新、删除）
- 将卡片添加到仪表盘
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlalchemy import text

from app.database import app_engine


def _init_dashboard_tables() -> None:
    with app_engine.begin() as conn:
        conn.execute(
            text("""
                CREATE TABLE IF NOT EXISTS dashboard_cards (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    chart_type TEXT NOT NULL,
                    chart_json TEXT NOT NULL,
                    data_json TEXT,
                    sql_text TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
        )
        conn.execute(
            text("""
                CREATE TABLE IF NOT EXISTS dashboards (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT,
                    layout_json TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
        )
        conn.execute(
            text("""
                CREATE TABLE IF NOT EXISTS dashboard_card_links (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    dashboard_id INTEGER NOT NULL,
                    card_id INTEGER NOT NULL,
                    position_x INTEGER DEFAULT 0,
                    position_y INTEGER DEFAULT 0,
                    width INTEGER DEFAULT 6,
                    height INTEGER DEFAULT 4,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
        )


def create_card(user_id: int, title: str, chart_type: str, chart: dict[str, Any], data: dict[str, Any] | None = None, sql: str | None = None) -> dict[str, Any]:
    """创建收藏卡片。"""
    _init_dashboard_tables()
    with app_engine.begin() as conn:
        result = conn.execute(
            text("""
                INSERT INTO dashboard_cards (user_id, title, chart_type, chart_json, data_json, sql_text)
                VALUES (:user_id, :title, :chart_type, :chart, :data, :sql)
            """),
            {
                "user_id": user_id,
                "title": title,
                "chart_type": chart_type,
                "chart": json.dumps(chart, ensure_ascii=False, default=str),
                "data": json.dumps(data, ensure_ascii=False, default=str) if data else None,
                "sql": sql,
            },
        )
        return {
            "id": result.lastrowid,
            "user_id": user_id,
            "title": title,
            "chart_type": chart_type,
            "chart": chart,
            "data": data,
            "sql": sql,
        }


def list_cards(user_id: int) -> list[dict[str, Any]]:
    """列出用户的所有卡片。"""
    _init_dashboard_tables()
    with app_engine.begin() as conn:
        rows = conn.execute(
            text("SELECT * FROM dashboard_cards WHERE user_id = :user_id ORDER BY created_at DESC"),
            {"user_id": user_id},
        ).mappings().all()
    return [
        {
            "id": r["id"],
            "user_id": r["user_id"],
            "title": r["title"],
            "chart_type": r["chart_type"],
            "chart": json.loads(r["chart_json"]) if r["chart_json"] else None,
            "data": json.loads(r["data_json"]) if r["data_json"] else None,
            "sql": r["sql_text"],
            "created_at": r["created_at"],
        }
        for r in rows
    ]


def delete_card(card_id: int, user_id: int) -> bool:
    """删除卡片。"""
    _init_dashboard_tables()
    with app_engine.begin() as conn:
        result = conn.execute(
            text("DELETE FROM dashboard_cards WHERE id = :id AND user_id = :user_id"),
            {"id": card_id, "user_id": user_id},
        )
        return (result.rowcount or 0) > 0


def create_dashboard(user_id: int, name: str, description: str | None = None) -> dict[str, Any]:
    """创建仪表盘。"""
    _init_dashboard_tables()
    with app_engine.begin() as conn:
        result = conn.execute(
            text("""
                INSERT INTO dashboards (user_id, name, description)
                VALUES (:user_id, :name, :desc)
            """),
            {"user_id": user_id, "name": name, "desc": description},
        )
        return {
            "id": result.lastrowid,
            "user_id": user_id,
            "name": name,
            "description": description,
            "cards": [],
        }


def list_dashboards(user_id: int) -> list[dict[str, Any]]:
    """列出用户的仪表盘。"""
    _init_dashboard_tables()
    with app_engine.begin() as conn:
        rows = conn.execute(
            text("SELECT * FROM dashboards WHERE user_id = :user_id ORDER BY updated_at DESC"),
            {"user_id": user_id},
        ).mappings().all()
    return [
        {
            "id": r["id"],
            "user_id": r["user_id"],
            "name": r["name"],
            "description": r["description"],
            "created_at": r["created_at"],
            "updated_at": r["updated_at"],
        }
        for r in rows
    ]


def get_dashboard(dashboard_id: int, user_id: int) -> dict[str, Any] | None:
    """获取仪表盘详情（包含卡片）。"""
    _init_dashboard_tables()
    with app_engine.begin() as conn:
        row = conn.execute(
            text("SELECT * FROM dashboards WHERE id = :id AND user_id = :user_id"),
            {"id": dashboard_id, "user_id": user_id},
        ).mappings().fetchone()
        if not row:
            return None

        cards = conn.execute(
            text("""
                SELECT c.*, l.position_x, l.position_y, l.width, l.height
                FROM dashboard_cards c
                JOIN dashboard_card_links l ON c.id = l.card_id
                WHERE l.dashboard_id = :dashboard_id
                ORDER BY l.position_y, l.position_x
            """),
            {"dashboard_id": dashboard_id},
        ).mappings().all()

    return {
        "id": row["id"],
        "user_id": row["user_id"],
        "name": row["name"],
        "description": row["description"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "cards": [
            {
                "id": c["id"],
                "title": c["title"],
                "chart_type": c["chart_type"],
                "chart": json.loads(c["chart_json"]) if c["chart_json"] else None,
                "data": json.loads(c["data_json"]) if c["data_json"] else None,
                "sql": c["sql_text"],
                "position_x": c["position_x"],
                "position_y": c["position_y"],
                "width": c["width"],
                "height": c["height"],
            }
            for c in cards
        ],
    }


def add_card_to_dashboard(dashboard_id: int, card_id: int, user_id: int, x: int = 0, y: int = 0, w: int = 6, h: int = 4) -> bool:
    """将卡片添加到仪表盘。"""
    _init_dashboard_tables()
    with app_engine.begin() as conn:
        # 验证仪表盘归属
        row = conn.execute(
            text("SELECT id FROM dashboards WHERE id = :id AND user_id = :user_id"),
            {"id": dashboard_id, "user_id": user_id},
        ).fetchone()
        if not row:
            return False
        conn.execute(
            text("""
                INSERT INTO dashboard_card_links (dashboard_id, card_id, position_x, position_y, width, height)
                VALUES (:dashboard_id, :card_id, :x, :y, :w, :h)
            """),
            {"dashboard_id": dashboard_id, "card_id": card_id, "x": x, "y": y, "w": w, "h": h},
        )
        conn.execute(
            text("UPDATE dashboards SET updated_at = CURRENT_TIMESTAMP WHERE id = :id"),
            {"id": dashboard_id},
        )
    return True


def remove_card_from_dashboard(dashboard_id: int, card_id: int, user_id: int) -> bool:
    """从仪表盘移除卡片。"""
    _init_dashboard_tables()
    with app_engine.begin() as conn:
        row = conn.execute(
            text("SELECT id FROM dashboards WHERE id = :id AND user_id = :user_id"),
            {"id": dashboard_id, "user_id": user_id},
        ).fetchone()
        if not row:
            return False
        conn.execute(
            text("DELETE FROM dashboard_card_links WHERE dashboard_id = :dashboard_id AND card_id = :card_id"),
            {"dashboard_id": dashboard_id, "card_id": card_id},
        )
    return True


def delete_dashboard(dashboard_id: int, user_id: int) -> bool:
    """删除仪表盘。"""
    _init_dashboard_tables()
    with app_engine.begin() as conn:
        row = conn.execute(
            text("SELECT id FROM dashboards WHERE id = :id AND user_id = :user_id"),
            {"id": dashboard_id, "user_id": user_id},
        ).fetchone()
        if not row:
            return False
        conn.execute(
            text("DELETE FROM dashboard_card_links WHERE dashboard_id = :id"),
            {"id": dashboard_id},
        )
        conn.execute(
            text("DELETE FROM dashboards WHERE id = :id"),
            {"id": dashboard_id},
        )
    return True
