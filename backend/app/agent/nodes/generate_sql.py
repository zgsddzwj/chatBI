"""SQL 生成节点。"""
from __future__ import annotations

import logging
from typing import Any

from app.agent.state import ChatState
from app.prompt_loader import load_prompt
from app.services.hybrid_search import render_schema_prompt_hybrid
from app.services.sql_safety import UnsafeSQLError, ensure_limit, validate_sql

logger = logging.getLogger(__name__)


def generate_sql(state: ChatState) -> dict[str, Any]:
    """使用 LLM 生成 SQL。"""
    from app.services.llm import get_llm

    question = state["question"]
    history = state.get("history")

    llm = get_llm()

    # 构建用户 Prompt
    parts: list[str] = []
    parts.append("# 数据库 Schema\n")
    parts.append(render_schema_prompt_hybrid(question, top_k=3))
    if history:
        parts.append("\n# 最近的对话（用于理解上下文）")
        for h in history[-6:]:
            parts.append(f"{h['role']}: {h['content']}")
    parts.append("\n# 当前问题")
    parts.append(question)
    parts.append("\n请输出 JSON。")
    user_prompt = "\n".join(parts)

    system_prompt = load_prompt("sql_system")

    try:
        result = llm.chat_json(system_prompt, user_prompt, temperature=0.0)
    except ValueError as exc:
        logger.warning("SQL 生成失败: %s", exc)
        return {"error": str(exc), "needs_clarification": False}

    if not isinstance(result, dict):
        return {"error": "模型返回格式异常", "needs_clarification": False}

    if result.get("needs_clarification"):
        return {
            "needs_clarification": True,
            "clarification": result.get("clarification") or "你的问题信息不够，能否补充？",
            "type": "clarification",
        }

    sql = (result.get("sql") or "").strip()
    if not sql:
        return {"error": "模型未返回 SQL", "needs_clarification": False}

    try:
        validated = validate_sql(sql)
        from app.config import get_settings
        limited = ensure_limit(validated, get_settings().sql_row_limit)
    except UnsafeSQLError as exc:
        return {"error": f"SQL 不安全: {exc}", "needs_clarification": False}

    return {
        "sql": limited,
        "explanation": result.get("explanation", ""),
        "needs_clarification": False,
        "error": None,
    }
