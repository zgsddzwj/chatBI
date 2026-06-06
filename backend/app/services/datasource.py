"""多数据源管理。

支持配置多个业务数据库连接，前端可在对话时切换数据源。
目前支持 SQLite，后续可扩展 PostgreSQL/MySQL。
"""
from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy import Engine, create_engine, text

from app.database import app_engine

logger = logging.getLogger(__name__)


def _init_datasource_table() -> None:
    with app_engine.begin() as conn:
        conn.execute(
            text("""
                CREATE TABLE IF NOT EXISTS data_sources (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    db_type TEXT NOT NULL DEFAULT 'sqlite',
                    connection_url TEXT NOT NULL,
                    description TEXT,
                    schema_json TEXT,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    is_default INTEGER NOT NULL DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
        )
        conn.execute(
            text("""
                CREATE UNIQUE INDEX IF NOT EXISTS idx_ds_default
                ON data_sources(is_default) WHERE is_default = 1
            """)
        )
        # 插入默认数据源（当前业务库）
        conn.execute(
            text("""
                INSERT OR IGNORE INTO data_sources (id, name, db_type, connection_url, description, is_default)
                VALUES (1, '默认业务库', 'sqlite', 'sqlite:///./data/business.db', '电商 Mock 数据', 1)
            """),
        )


def _get_engine(url: str) -> Engine:
    connect_args = {}
    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    return create_engine(url, connect_args=connect_args, pool_pre_ping=True)


# 引擎缓存
_engine_cache: dict[str, Engine] = {}


def get_engine_for_source(source_id: int) -> Engine | None:
    """获取数据源的 SQLAlchemy 引擎。"""
    _init_datasource_table()
    with app_engine.begin() as conn:
        row = conn.execute(
            text("SELECT connection_url FROM data_sources WHERE id = :id AND is_active = 1"),
            {"id": source_id},
        ).fetchone()
    if not row:
        return None
    url = row[0]
    if url not in _engine_cache:
        _engine_cache[url] = _get_engine(url)
    return _engine_cache[url]


def list_sources() -> list[dict[str, Any]]:
    """列出所有数据源。"""
    _init_datasource_table()
    with app_engine.begin() as conn:
        rows = conn.execute(
            text("SELECT id, name, db_type, description, is_default, is_active FROM data_sources ORDER BY id")
        ).mappings().all()
    return [
        {
            "id": r["id"],
            "name": r["name"],
            "db_type": r["db_type"],
            "description": r["description"],
            "is_default": bool(r["is_default"]),
            "is_active": bool(r["is_active"]),
        }
        for r in rows
    ]


def get_source(source_id: int) -> dict[str, Any] | None:
    """获取单个数据源详情。"""
    _init_datasource_table()
    with app_engine.begin() as conn:
        row = conn.execute(
            text("SELECT id, name, db_type, connection_url, description, schema_json, is_default, is_active FROM data_sources WHERE id = :id"),
            {"id": source_id},
        ).mappings().fetchone()
    if not row:
        return None
    return {
        "id": row["id"],
        "name": row["name"],
        "db_type": row["db_type"],
        "connection_url": row["connection_url"],
        "description": row["description"],
        "schema": json.loads(row["schema_json"]) if row["schema_json"] else None,
        "is_default": bool(row["is_default"]),
        "is_active": bool(row["is_active"]),
    }


def create_source(name: str, db_type: str, connection_url: str, description: str | None = None, schema: dict | None = None) -> dict[str, Any]:
    """创建新数据源。"""
    _init_datasource_table()
    with app_engine.begin() as conn:
        result = conn.execute(
            text("""
                INSERT INTO data_sources (name, db_type, connection_url, description, schema_json)
                VALUES (:name, :db_type, :url, :desc, :schema)
            """),
            {
                "name": name,
                "db_type": db_type,
                "url": connection_url,
                "desc": description,
                "schema": json.dumps(schema, ensure_ascii=False) if schema else None,
            },
        )
        return {
            "id": result.lastrowid,
            "name": name,
            "db_type": db_type,
            "description": description,
        }


def update_source(source_id: int, **kwargs: Any) -> dict[str, Any] | None:
    """更新数据源。"""
    _init_datasource_table()
    allowed = {"name", "db_type", "connection_url", "description", "schema_json", "is_active", "is_default"}
    updates = {k: v for k, v in kwargs.items() if k in allowed}
    if not updates:
        return get_source(source_id)

    if "schema" in kwargs:
        updates["schema_json"] = json.dumps(kwargs["schema"], ensure_ascii=False)
        del updates["schema"]

    set_clause = ", ".join(f"{k} = :{k}" for k in updates)
    updates["id"] = source_id

    with app_engine.begin() as conn:
        conn.execute(
            text(f"UPDATE data_sources SET {set_clause} WHERE id = :id"),
            updates,
        )
    return get_source(source_id)


def delete_source(source_id: int) -> bool:
    """删除数据源（不能删除默认源）。"""
    _init_datasource_table()
    with app_engine.begin() as conn:
        row = conn.execute(
            text("SELECT is_default FROM data_sources WHERE id = :id"),
            {"id": source_id},
        ).fetchone()
        if not row or row[0]:
            return False
        conn.execute(
            text("DELETE FROM data_sources WHERE id = :id"),
            {"id": source_id},
        )
    return True


def test_connection(url: str) -> dict[str, Any]:
    """测试数据库连接。"""
    try:
        engine = _get_engine(url)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"ok": True, "message": "连接成功"}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "message": str(exc)}
