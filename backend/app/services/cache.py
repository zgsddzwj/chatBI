"""SQL 查询结果缓存。

基于 SQL 语句的规范化哈希做键，缓存查询结果和图表推荐，
避免重复执行相同的查询（尤其是 LLM 生成 SQL 后用户刷新页面时）。
"""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import text

from app.config import get_settings
from app.database import app_engine

logger = logging.getLogger(__name__)


def _cache_ttl() -> int:
    return get_settings().cache_ttl_seconds


def _init_cache_table() -> None:
    with app_engine.begin() as conn:
        conn.execute(
            text("""
                CREATE TABLE IF NOT EXISTS query_cache (
                    cache_key TEXT PRIMARY KEY,
                    sql_text TEXT NOT NULL,
                    result_json TEXT NOT NULL,
                    chart_json TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    expires_at DATETIME NOT NULL
                )
            """)
        )
        conn.execute(
            text("""
                CREATE INDEX IF NOT EXISTS idx_query_cache_expires
                ON query_cache(expires_at)
            """)
        )


def _normalize_sql(sql: str) -> str:
    """规范化 SQL 用于生成缓存键（去除多余空白、统一大小写）。"""
    return " ".join(sql.split()).lower().strip(";")


def _make_key(sql: str) -> str:
    normalized = _normalize_sql(sql)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:32]


def get_cached(sql: str) -> dict[str, Any] | None:
    """获取缓存的查询结果，若过期则返回 None。"""
    _init_cache_table()
    key = _make_key(sql)
    with app_engine.begin() as conn:
        row = conn.execute(
            text("""
                SELECT result_json, chart_json FROM query_cache
                WHERE cache_key = :key AND expires_at > CURRENT_TIMESTAMP
            """),
            {"key": key},
        ).fetchone()
    if not row:
        return None
    try:
        result = json.loads(row.result_json)
        if row.chart_json:
            result["chart"] = json.loads(row.chart_json)
        return result
    except json.JSONDecodeError:
        return None


def set_cache(sql: str, result: dict[str, Any], chart: dict[str, Any] | None = None, ttl: int | None = None) -> None:
    if ttl is None:
        ttl = _cache_ttl()
    """缓存查询结果。"""
    _init_cache_table()
    key = _make_key(sql)
    expires = datetime.utcnow() + timedelta(seconds=ttl)
    with app_engine.begin() as conn:
        conn.execute(
            text("""
                INSERT INTO query_cache (cache_key, sql_text, result_json, chart_json, expires_at)
                VALUES (:key, :sql, :result, :chart, :expires)
                ON CONFLICT(cache_key) DO UPDATE SET
                    sql_text = excluded.sql_text,
                    result_json = excluded.result_json,
                    chart_json = excluded.chart_json,
                    created_at = CURRENT_TIMESTAMP,
                    expires_at = excluded.expires_at
            """),
            {
                "key": key,
                "sql": sql,
                "result": json.dumps(result, ensure_ascii=False, default=str),
                "chart": json.dumps(chart, ensure_ascii=False, default=str) if chart else None,
                "expires": expires.isoformat(),
            },
        )


def clear_expired() -> int:
    """清理过期缓存，返回清理条数。"""
    _init_cache_table()
    with app_engine.begin() as conn:
        result = conn.execute(
            text("DELETE FROM query_cache WHERE expires_at <= CURRENT_TIMESTAMP")
        )
        return result.rowcount or 0
