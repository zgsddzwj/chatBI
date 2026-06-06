"""SQL 纠错与重试服务。

当 LLM 生成的 SQL 执行失败时，将错误信息反馈给 LLM，让它修正 SQL 并重试。
支持最多 2 次重试，避免无限循环消耗 Token。
"""
from __future__ import annotations

import logging
from typing import Any

from app.services.llm import get_llm
from app.services.sql_safety import UnsafeSQLError, ensure_limit, validate_sql
from app.prompt_loader import load_prompt

logger = logging.getLogger(__name__)

MAX_RETRIES = 2


def _get_fix_system_prompt() -> str:
    """加载 SQL 纠错系统 Prompt。"""
    return load_prompt("fix_sql")


def _build_fix_prompt(question: str, original_sql: str, error_message: str, schema_prompt: str) -> str:
    """构建纠错 prompt。"""
    return (
        f"# 数据库 Schema\n{schema_prompt}\n\n"
        f"# 用户问题\n{question}\n\n"
        f"# 原始 SQL（执行出错）\n{original_sql}\n\n"
        f"# 错误信息\n{error_message}\n\n"
        "请分析错误原因，输出修正后的 SQL JSON。"
    )


def try_fix_sql(question: str, original_sql: str, error_message: str, schema_prompt: str, row_limit: int = 1000) -> dict[str, Any] | None:
    """尝试修正 SQL，返回修正结果或 None（如果无法修正）。"""
    llm = get_llm()
    prompt = _build_fix_prompt(question, original_sql, error_message, schema_prompt)

    try:
        result = llm.chat_json(_get_fix_system_prompt(), prompt, temperature=0.1)
    except Exception as exc:  # noqa: BLE001
        logger.warning("SQL 纠错 LLM 调用失败: %s", exc)
        return None

    if not isinstance(result, dict):
        logger.warning("SQL 纠错 LLM 返回格式异常")
        return None

    if result.get("needs_clarification"):
        return {
            "needs_clarification": True,
            "clarification": result.get("clarification") or "SQL 错误无法自动修正，请检查问题描述。",
        }

    sql = (result.get("sql") or "").strip()
    if not sql:
        return None

    try:
        validated = validate_sql(sql)
        limited = ensure_limit(validated, row_limit)
    except UnsafeSQLError as exc:
        logger.warning("修正后的 SQL 仍不安全: %s", exc)
        return None

    return {
        "needs_clarification": False,
        "sql": limited,
        "explanation": result.get("explanation", ""),
    }
