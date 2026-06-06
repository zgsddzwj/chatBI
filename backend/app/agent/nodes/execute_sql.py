"""SQL 执行节点。"""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeoutError
from typing import Any

from sqlalchemy import text

from app.agent.state import ChatState
from app.config import get_settings
from app.database import business_engine
from app.services.cache import get_cached, set_cache
from app.services.chart import recommend_chart

logger = logging.getLogger(__name__)


def execute_sql(state: ChatState) -> dict[str, Any]:
    """执行 SQL 并推荐图表。"""
    sql = state.get("fixed_sql") or state["sql"]
    question = state["question"]

    # 先查缓存
    cached = get_cached(sql)
    if cached:
        logger.info("SQL 缓存命中: %s", sql[:80])
        return {
            "data": cached,
            "chart": cached.get("chart", recommend_chart(cached["columns"], cached["rows"])),
        }

    settings = get_settings()
    timeout = settings.sql_query_timeout_seconds

    def _run_query() -> dict[str, Any]:
        with business_engine.connect() as conn:
            cursor = conn.execute(text(sql))
            columns = list(cursor.keys())
            rows = [list(r) for r in cursor.fetchall()]
        return {"columns": columns, "rows": rows, "row_count": len(rows)}

    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(_run_query)
            result = future.result(timeout=timeout)
    except FuturesTimeoutError:
        return {"error": f"查询超时（>{timeout}s）"}
    except Exception as exc:
        return {"error": str(exc)}

    chart = recommend_chart(result["columns"], result["rows"])
    set_cache(sql, result, chart)

    return {
        "data": result,
        "chart": chart,
        "error": None,
    }
