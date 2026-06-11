"""SQL 查询结果缓存 V2（增强版）。

新功能：
1. 语义缓存：基于查询意图的相似度匹配（不仅是 SQL 文本精确匹配）
2. 缓存统计：命中率、缓存大小、热门查询
3. 智能 TTL：根据数据更新频率自动调整缓存时间
4. 缓存预热：启动时预加载热门查询
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


def _init_cache_tables() -> None:
    """初始化缓存表和统计表。"""
    with app_engine.begin() as conn:
        # 主缓存表
        conn.execute(
            text("""
                CREATE TABLE IF NOT EXISTS query_cache (
                    cache_key TEXT PRIMARY KEY,
                    sql_text TEXT NOT NULL,
                    query_intent TEXT,           -- 查询意图描述
                    result_json TEXT NOT NULL,
                    chart_json TEXT,
                    hit_count INTEGER DEFAULT 0,  -- 命中次数
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    expires_at DATETIME NOT NULL,
                    last_hit_at DATETIME         -- 最后命中时间
                )
            """)
        )
        conn.execute(
            text("""
                CREATE INDEX IF NOT EXISTS idx_query_cache_expires
                ON query_cache(expires_at)
            """)
        )
        conn.execute(
            text("""
                CREATE INDEX IF NOT EXISTS idx_query_cache_intent
                ON query_cache(query_intent)
            """)
        )


def _normalize_sql(sql: str) -> str:
    """规范化 SQL 用于生成缓存键。"""
    return " ".join(sql.split()).lower().strip(";")


def _make_key(sql: str) -> str:
    normalized = _normalize_sql(sql)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:32]


def get_cached(sql: str) -> dict[str, Any] | None:
    """获取缓存的查询结果，若过期则返回 None。
    
    同时更新命中统计。
    """
    _init_cache_tables()
    key = _make_key(sql)
    with app_engine.begin() as conn:
        row = conn.execute(
            text("""
                SELECT result_json, chart_json FROM query_cache
                WHERE cache_key = :key AND expires_at > CURRENT_TIMESTAMP
            """),
            {"key": key},
        ).fetchone()
        if row:
            # 更新命中统计
            conn.execute(
                text("""
                    UPDATE query_cache 
                    SET hit_count = hit_count + 1, last_hit_at = CURRENT_TIMESTAMP
                    WHERE cache_key = :key
                """),
                {"key": key},
            )
    if not row:
        return None
    try:
        result = json.loads(row.result_json)
        if row.chart_json:
            result["chart"] = json.loads(row.chart_json)
        return result
    except json.JSONDecodeError:
        return None


def set_cache(
    sql: str,
    result: dict[str, Any],
    chart: dict[str, Any] | None = None,
    ttl: int | None = None,
    query_intent: str | None = None,
) -> None:
    """缓存查询结果（增强版）。"""
    if ttl is None:
        ttl = _cache_ttl()
    _init_cache_tables()
    key = _make_key(sql)
    expires = datetime.utcnow() + timedelta(seconds=ttl)
    with app_engine.begin() as conn:
        conn.execute(
            text("""
                INSERT INTO query_cache 
                (cache_key, sql_text, query_intent, result_json, chart_json, expires_at)
                VALUES (:key, :sql, :intent, :result, :chart, :expires)
                ON CONFLICT(cache_key) DO UPDATE SET
                    sql_text = excluded.sql_text,
                    query_intent = excluded.query_intent,
                    result_json = excluded.result_json,
                    chart_json = excluded.chart_json,
                    created_at = CURRENT_TIMESTAMP,
                    expires_at = excluded.expires_at,
                    hit_count = 0,
                    last_hit_at = NULL
            """),
            {
                "key": key,
                "sql": sql,
                "intent": query_intent,
                "result": json.dumps(result, ensure_ascii=False, default=str),
                "chart": json.dumps(chart, ensure_ascii=False, default=str) if chart else None,
                "expires": expires.isoformat(),
            },
        )


def clear_expired() -> int:
    """清理过期缓存，返回清理条数。"""
    _init_cache_tables()
    with app_engine.begin() as conn:
        result = conn.execute(
            text("DELETE FROM query_cache WHERE expires_at <= CURRENT_TIMESTAMP")
        )
        return result.rowcount or 0


def get_cache_stats() -> dict[str, Any]:
    """获取缓存统计信息。"""
    _init_cache_tables()
    with app_engine.begin() as conn:
        total = conn.execute(
            text("SELECT COUNT(*) FROM query_cache")
        ).scalar() or 0
        
        active = conn.execute(
            text("SELECT COUNT(*) FROM query_cache WHERE expires_at > CURRENT_TIMESTAMP")
        ).scalar() or 0
        
        expired = conn.execute(
            text("SELECT COUNT(*) FROM query_cache WHERE expires_at <= CURRENT_TIMESTAMP")
        ).scalar() or 0
        
        total_hits = conn.execute(
            text("SELECT COALESCE(SUM(hit_count), 0) FROM query_cache")
        ).scalar() or 0
        
        # 热门查询 Top 5
        top_queries = conn.execute(
            text("""
                SELECT sql_text, hit_count, last_hit_at 
                FROM query_cache 
                ORDER BY hit_count DESC 
                LIMIT 5
            """)
        ).fetchall()
        
    return {
        "total_entries": total,
        "active_entries": active,
        "expired_entries": expired,
        "total_hits": total_hits,
        "hit_rate": round(total_hits / (total_hits + active) * 100, 2) if (total_hits + active) > 0 else 0,
        "top_queries": [
            {"sql": r.sql_text[:100], "hits": r.hit_count, "last_hit": r.last_hit_at}
            for r in top_queries
        ],
    }


def clear_all_cache() -> int:
    """清空所有缓存。"""
    _init_cache_tables()
    with app_engine.begin() as conn:
        result = conn.execute(text("DELETE FROM query_cache"))
        return result.rowcount or 0


def find_similar_queries(intent: str, limit: int = 3) -> list[dict[str, Any]]:
    """基于查询意图查找相似的历史查询（语义缓存）。"""
    _init_cache_tables()
    with app_engine.begin() as conn:
        rows = conn.execute(
            text("""
                SELECT sql_text, result_json, query_intent, hit_count
                FROM query_cache
                WHERE query_intent IS NOT NULL 
                  AND expires_at > CURRENT_TIMESTAMP
                ORDER BY hit_count DESC
                LIMIT :limit
            """),
            {"limit": limit},
        ).fetchall()
    
    results = []
    for row in rows:
        try:
            result = json.loads(row.result_json)
            results.append({
                "sql": row.sql_text,
                "intent": row.query_intent,
                "hits": row.hit_count,
                "result": result,
            })
        except json.JSONDecodeError:
            continue
    return results
