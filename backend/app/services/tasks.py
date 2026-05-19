"""后台 SQL 执行任务队列。

使用 SQLite 作为轻量级任务队列，支持：
- 异步提交 SQL 执行任务
- 查询任务状态
- 任务结果与缓存联动
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from sqlalchemy import text

from app.database import app_engine, business_engine
from app.services.cache import get_cached, set_cache
from app.services.chart import recommend_chart
from app.services.sql_safety import UnsafeSQLError, ensure_limit, validate_sql

logger = logging.getLogger(__name__)

TASK_TIMEOUT_SECONDS = 300


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


def _init_task_table() -> None:
    with app_engine.begin() as conn:
        conn.execute(
            text("""
                CREATE TABLE IF NOT EXISTS sql_tasks (
                    task_id TEXT PRIMARY KEY,
                    sql_text TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    result_json TEXT,
                    error TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    started_at DATETIME,
                    finished_at DATETIME,
                    expires_at DATETIME NOT NULL
                )
            """)
        )
        conn.execute(
            text("""
                CREATE INDEX IF NOT EXISTS idx_sql_tasks_status
                ON sql_tasks(status)
            """)
        )
        conn.execute(
            text("""
                CREATE INDEX IF NOT EXISTS idx_sql_tasks_expires
                ON sql_tasks(expires_at)
            """)
        )


def submit_task(sql: str, row_limit: int = 1000) -> str:
    """提交一个 SQL 执行任务，返回任务 ID。"""
    _init_task_table()

    # 安全校验
    validated = validate_sql(sql)
    limited = ensure_limit(validated, row_limit)

    # 先查缓存
    cached = get_cached(limited)
    if cached:
        task_id = f"cached-{uuid.uuid4().hex[:12]}"
        with app_engine.begin() as conn:
            conn.execute(
                text("""
                    INSERT INTO sql_tasks (task_id, sql_text, status, result_json, finished_at, expires_at)
                    VALUES (:task_id, :sql, 'success', :result, CURRENT_TIMESTAMP, :expires)
                """),
                {
                    "task_id": task_id,
                    "sql": limited,
                    "result": json.dumps(cached, ensure_ascii=False, default=str),
                    "expires": (datetime.utcnow() + timedelta(seconds=TASK_TIMEOUT_SECONDS)).isoformat(),
                },
            )
        return task_id

    task_id = f"task-{uuid.uuid4().hex[:12]}"
    expires = datetime.utcnow() + timedelta(seconds=TASK_TIMEOUT_SECONDS)

    with app_engine.begin() as conn:
        conn.execute(
            text("""
                INSERT INTO sql_tasks (task_id, sql_text, status, expires_at)
                VALUES (:task_id, :sql, 'pending', :expires)
            """),
            {"task_id": task_id, "sql": limited, "expires": expires.isoformat()},
        )

    # 立即执行（同步执行，但状态可追踪）
    _execute_task(task_id, limited)
    return task_id


def _execute_task(task_id: str, sql: str) -> None:
    """执行任务并更新状态。"""
    _init_task_table()
    with app_engine.begin() as conn:
        conn.execute(
            text("UPDATE sql_tasks SET status = 'running', started_at = CURRENT_TIMESTAMP WHERE task_id = :task_id"),
            {"task_id": task_id},
        )

    try:
        with business_engine.connect() as conn:
            cursor = conn.execute(text(sql))
            columns = list(cursor.keys())
            rows = [list(r) for r in cursor.fetchall()]

        result = {"columns": columns, "rows": rows, "row_count": len(rows)}
        chart = recommend_chart(columns, rows)

        # 写入缓存
        set_cache(sql, result, chart)

        with app_engine.begin() as conn:
            conn.execute(
                text("""
                    UPDATE sql_tasks
                    SET status = 'success', result_json = :result, finished_at = CURRENT_TIMESTAMP
                    WHERE task_id = :task_id
                """),
                {
                    "task_id": task_id,
                    "result": json.dumps(
                        {"result": result, "chart": chart},
                        ensure_ascii=False,
                        default=str,
                    ),
                },
            )
    except Exception as exc:  # noqa: BLE001
        logger.exception("任务执行失败: %s", task_id)
        with app_engine.begin() as conn:
            conn.execute(
                text("""
                    UPDATE sql_tasks
                    SET status = 'failed', error = :error, finished_at = CURRENT_TIMESTAMP
                    WHERE task_id = :task_id
                """),
                {"task_id": task_id, "error": str(exc)[:500]},
            )


def get_task(task_id: str) -> dict[str, Any] | None:
    """查询任务状态。"""
    _init_task_table()
    with app_engine.begin() as conn:
        row = conn.execute(
            text("SELECT * FROM sql_tasks WHERE task_id = :task_id"),
            {"task_id": task_id},
        ).mappings().fetchone()
    if not row:
        return None
    return {
        "task_id": row["task_id"],
        "status": row["status"],
        "result": json.loads(row["result_json"]) if row["result_json"] else None,
        "error": row["error"],
        "created_at": row["created_at"],
        "started_at": row["started_at"],
        "finished_at": row["finished_at"],
    }


def list_pending_tasks() -> list[dict[str, Any]]:
    """列出所有待处理任务。"""
    _init_task_table()
    with app_engine.begin() as conn:
        rows = conn.execute(
            text("SELECT task_id, sql_text, status, created_at FROM sql_tasks WHERE status IN ('pending', 'running')")
        ).mappings().all()
    return [
        {
            "task_id": r["task_id"],
            "sql_text": r["sql_text"],
            "status": r["status"],
            "created_at": r["created_at"],
        }
        for r in rows
    ]


def clear_expired_tasks() -> int:
    """清理过期任务。"""
    _init_task_table()
    with app_engine.begin() as conn:
        result = conn.execute(
            text("DELETE FROM sql_tasks WHERE expires_at <= CURRENT_TIMESTAMP")
        )
        return result.rowcount or 0
