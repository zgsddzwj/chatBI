"""查询历史分析与推荐。

基于用户历史查询记录提供个性化推荐：
1. 查询频率分析
2. 查询模式识别
3. 个人偏好模型
4. 相似用户行为
5. 推荐相关查询
"""
from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import bindparam, text

from app.database import app_engine

logger = logging.getLogger(__name__)


def get_user_query_history(
    user_id: int,
    limit: int = 20,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """获取用户查询历史。"""
    with app_engine.begin() as conn:
        rows = conn.execute(
            text("""
                SELECT conversation_id, sql_text, query_intent, success, created_at
                FROM message_history
                WHERE user_id = :uid AND sql_text IS NOT NULL
                ORDER BY created_at DESC
                LIMIT :limit OFFSET :offset
            """),
            {"uid": user_id, "limit": limit, "offset": offset},
        ).fetchall()
    return [
        {
            "conversation_id": r.conversation_id,
            "sql": r.sql_text,
            "intent": r.query_intent,
            "success": r.success,
            "created_at": r.created_at,
        }
        for r in rows
    ]


def get_query_stats(user_id: int) -> dict[str, Any]:
    """获取用户查询统计。"""
    with app_engine.begin() as conn:
        total = conn.execute(
            text("SELECT COUNT(*) FROM message_history WHERE user_id = :uid"),
            {"uid": user_id},
        ).scalar() or 0
        
        success_rate = conn.execute(
            text("""
                SELECT 
                    100.0 * SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) / COUNT(*)
                FROM message_history 
                WHERE user_id = :uid
            """),
            {"uid": user_id},
        ).scalar() or 0
        
        top_intents = conn.execute(
            text("""
                SELECT query_intent, COUNT(*) as count
                FROM message_history
                WHERE user_id = :uid AND query_intent IS NOT NULL
                GROUP BY query_intent
                ORDER BY count DESC
                LIMIT 5
            """),
            {"uid": user_id},
        ).fetchall()
        
    return {
        "total_queries": total,
        "success_rate": round(float(success_rate), 2),
        "top_intents": [
            {"intent": r.query_intent, "count": r.count}
            for r in top_intents
        ],
    }


def get_query_recommendations(
    user_id: int,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """基于用户历史行为推荐查询。
    
    使用协同过滤：
    1. 找到查询模式相似的用户
    2. 推荐这些用户常用但当前用户未查过的查询
    """
    recommendations = []
    
    try:
        # 获取用户最近查询的意图集合
        recent_intents = []
        with app_engine.begin() as conn:
            rows = conn.execute(
                text("""
                    SELECT DISTINCT query_intent 
                    FROM message_history
                    WHERE user_id = :uid AND query_intent IS NOT NULL
                    ORDER BY created_at DESC
                    LIMIT 10
                """),
                {"uid": user_id},
            ).fetchall()
            recent_intents = [r.query_intent for r in rows]
        
        # 基于意图找到相似用户
        similar_users: set[int] = set()
        if recent_intents:
            with app_engine.begin() as conn:
                rows = conn.execute(
                    text("""
                        SELECT DISTINCT user_id
                        FROM message_history
                        WHERE query_intent IN :intents
                          AND user_id != :uid
                        GROUP BY user_id
                        HAVING COUNT(DISTINCT query_intent) >= 2
                        ORDER BY COUNT(*) DESC
                        LIMIT 10
                    """).bindparams(
                        bindparam("intents", recent_intents, expanding=True),
                        bindparam("uid", user_id),
                    ),
                ).fetchall()
                similar_users = {r.user_id for r in rows}

        # 批量获取所有相似用户的推荐查询（避免 N+1 查询）
        if similar_users:
            similar_uids = list(similar_users)
            with app_engine.begin() as conn:
                rows = conn.execute(
                    text("""
                        SELECT sql_text, user_id
                        FROM message_history
                        WHERE user_id IN :uids
                          AND success = 1
                        GROUP BY sql_text
                        ORDER BY COUNT(*) DESC
                        LIMIT 30
                    """).bindparams(
                        bindparam("uids", similar_uids, expanding=True),
                    ),
                ).fetchall()
                for r in rows:
                    try:
                        intent = classify_intent_from_sql(r.sql_text)
                    except Exception:
                        intent = "query"
                    recommendations.append({
                        "sql": r.sql_text,
                        "intent": intent,
                        "source": "similar_users",
                        "score": 0.8,
                    })
        
        # 去重并截断
        seen_sql = set()
        unique_recs = []
        for rec in recommendations:
            if rec["sql"] not in seen_sql:
                seen_sql.add(rec["sql"])
                unique_recs.append(rec)
            if len(unique_recs) >= limit:
                break
        
        return unique_recs
    
    except Exception as exc:
        logger.warning("Query recommendation failed for user %s: %s", user_id, exc)
        return []


def classify_intent_from_sql(sql: str) -> str:
    """从 SQL 中简单推断意图。"""
    sql_lower = sql.lower()
    if "count(" in sql_lower:
        return "count"
    if "sum(" in sql_lower or "avg(" in sql_lower:
        return "aggregate"
    if "group by" in sql_lower:
        return "breakdown"
    if "order by" in sql_lower and "limit" in sql_lower:
        return "topn"
    return "query"


def get_query_patterns(user_id: int) -> list[dict[str, Any]]:
    """分析用户查询模式。
    
    返回常见的查询模板和变异。
    """
    patterns = []
    try:
        with app_engine.begin() as conn:
            rows = conn.execute(
                text("""
                    SELECT sql_text, COUNT(*) as cnt
                    FROM message_history
                    WHERE user_id = :uid AND success = 1
                    GROUP BY sql_text
                    ORDER BY cnt DESC
                    LIMIT 5
                """),
                {"uid": user_id},
            ).fetchall()

            for r in rows:
                sql = r.sql_text
                pattern = _extract_pattern(sql)
                patterns.append({
                    "pattern": pattern,
                    "sql": sql,
                    "count": r.cnt,
                })

        patterns.sort(key=lambda x: x["count"], reverse=True)
        return patterns[:5]
    except Exception as exc:
        logger.warning("Pattern analysis failed for user %s: %s", user_id, exc)
        return []


def _extract_pattern(sql: str) -> str:
    """提取 SQL 模板（简化版）。"""
    # 替换常量为 ?
    pattern = ""
    in_string = False
    for c in sql:
        if c == "'" and not in_string:
            pattern += "'?'"
            in_string = True
        elif c == "'" and in_string:
            pattern += "'?'"
            in_string = False
        elif in_string:
            pass
        else:
            pattern += c
    return pattern.replace("  ", " ")
