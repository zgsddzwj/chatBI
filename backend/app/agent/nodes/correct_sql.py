"""SQL 纠错节点。"""
from __future__ import annotations

import logging
from typing import Any

from app.agent.state import ChatState
from app.prompt_loader import load_prompt
from app.services.hybrid_search import render_schema_prompt_hybrid
from app.services.llm import get_llm
from app.services.sql_safety import UnsafeSQLError, ensure_limit, validate_sql

logger = logging.getLogger(__name__)


def correct_sql(state: ChatState) -> dict[str, Any]:
    """根据错误信息修正 SQL。"""
    question = state["question"]
    sql = state["sql"]
    error = state["error"]

    llm = get_llm()
    system_prompt = load_prompt("fix_sql")

    schema_prompt = render_schema_prompt_hybrid(question, top_k=3)
    user_msg = (
        f"# 数据库 Schema\n{schema_prompt}\n\n"
        f"# 用户问题\n{question}\n\n"
        f"# 原始 SQL（执行出错）\n{sql}\n\n"
        f"# 错误信息\n{error}\n\n"
        "请分析错误原因，输出修正后的 SQL JSON。"
    )

    try:
        result = llm.chat_json(system_prompt, user_msg, temperature=0.1)
    except Exception as exc:
        logger.warning("SQL 纠错 LLM 调用失败: %s", exc)
        return {"error": error, "fixed_sql": None}

    if not isinstance(result, dict):
        return {"error": error, "fixed_sql": None}

    if result.get("needs_clarification"):
        return {
            "needs_clarification": True,
            "clarification": result.get("clarification") or "SQL 错误无法自动修正。",
            "type": "clarification",
        }

    fixed = (result.get("sql") or "").strip()
    if not fixed:
        return {"error": error, "fixed_sql": None}

    try:
        validated = validate_sql(fixed)
        from app.config import get_settings
        limited = ensure_limit(validated, get_settings().sql_row_limit)
    except UnsafeSQLError:
        return {"error": error, "fixed_sql": None}

    logger.info("SQL 已修正: %s", limited[:100])
    return {
        "fixed_sql": limited,
        "error": None,
        "sql": limited,
    }
