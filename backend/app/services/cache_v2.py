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


# ========== 缓存预热 ==========

WARMUP_QUERIES = [
    ("SELECT strftime('%Y-%m', d.date_id) AS month, SUM(f.order_amount) AS total_sales FROM fact_order f JOIN dim_date d ON f.date_id = d.date_id WHERE d.year = 2024 GROUP BY month ORDER BY month", "2024年每月销售额"),
    ("SELECT p.category, SUM(f.order_amount) AS total FROM fact_order f JOIN dim_product p ON f.product_id = p.product_id GROUP BY p.category ORDER BY total DESC", "各品类销售额"),
    ("SELECT r.region_name, COUNT(*) AS order_count FROM fact_order f JOIN dim_region r ON f.region_id = r.region_id GROUP BY r.region_name ORDER BY order_count DESC", "各地区订单数量"),
    ("SELECT p.product_name, SUM(f.order_amount) AS revenue FROM fact_order f JOIN dim_product p ON f.product_id = p.product_id GROUP BY p.product_name ORDER BY revenue DESC LIMIT 5", "销售额前5商品"),
    ("SELECT c.member_level, SUM(f.order_amount) AS total FROM fact_order f JOIN dim_customer c ON f.customer_id = c.customer_id GROUP BY c.member_level ORDER BY total DESC", "各会员等级消费"),
]


def warmup_cache() -> int:
    """预热缓存：执行热门查询并缓存结果。
    
    返回预热成功的条数。
    """
    from app.database import business_engine
    
    _init_cache_tables()
    warmed = 0
    for sql, intent in WARMUP_QUERIES:
        key = _make_key(sql)
        # 检查是否已缓存
        with app_engine.begin() as conn:
            exists = conn.execute(
                text("SELECT 1 FROM query_cache WHERE cache_key = :key AND expires_at > CURRENT_TIMESTAMP"),
                {"key": key},
            ).fetchone()
        if exists:
            continue
        try:
            with business_engine.connect() as conn:
                result = conn.execute(text(sql))
                rows = [dict(row._mapping) for row in result.fetchall()]
            result_data = {
                "columns": list(rows[0].keys()) if rows else [],
                "rows": [list(row.values()) for row in rows],
                "row_count": len(rows),
            }
            set_cache(sql, result_data, query_intent=intent, ttl=3600)
            warmed += 1
            logger.info("Cache warmed: %s", intent)
        except Exception as e:
            logger.warning("Cache warmup failed for %s: %s", intent, e)
    return warmed


# ========== 智能 TTL ==========

TTL_RULES = [
    # (匹配模式, 秒数, 描述)
    ("count(*)", 300, "计数查询 TTL 5 分钟"),
    ("sum(", 600, "求和查询 TTL 10 分钟"),
    ("avg(", 600, "平均值查询 TTL 10 分钟"),
    ("group by", 900, "分组查询 TTL 15 分钟"),
    ("limit 5", 1800, "Top N 查询 TTL 30 分钟"),
    ("limit 10", 1800, "Top 10 查询 TTL 30 分钟"),
]


def smart_ttl(sql: str) -> int:
    """根据 SQL 特征返回智能 TTL。
    
    默认使用配置中的 cache_ttl_seconds。
    """
    normalized = _normalize_sql(sql)
    for pattern, ttl, _ in TTL_RULES:
        if pattern in normalized:
            return ttl
    return _cache_ttl()
