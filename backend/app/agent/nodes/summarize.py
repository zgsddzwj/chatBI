"""结果总结节点。"""
from __future__ import annotations

import logging
from typing import Any

from app.agent.state import ChatState
from app.prompt_loader import load_prompt
from app.services.llm import get_llm

logger = logging.getLogger(__name__)


def summarize(state: ChatState) -> dict[str, Any]:
    """根据查询结果生成自然语言总结。"""
    question = state["question"]
    sql = state.get("fixed_sql") or state["sql"]
    data = state["data"]

    if not data or data.get("row_count", 0) == 0:
        return {"summary": "未查询到匹配数据。", "type": "answer"}

    preview_rows = data["rows"][:20]
    user_msg = (
        f"用户问题: {question}\n\n"
        f"执行 SQL:\n{sql}\n\n"
        f"查询结果 (前 {len(preview_rows)} 行, 共 {data['row_count']} 行):\n"
        f"列: {data['columns']}\n"
        f"数据: {preview_rows}\n\n"
        "请用 2-4 句中文总结关键洞察。"
    )

    llm = get_llm()
    system_prompt = load_prompt("summary")

    try:
        summary = llm.chat_text(system_prompt, user_msg, temperature=0.3)
    except Exception:
        logger.exception("总结失败，使用兜底文案")
        summary = f"查询完成，共返回 {data['row_count']} 行结果。"

    if not summary:
        summary = f"查询完成，共返回 {data['row_count']} 行结果。"

    return {"summary": summary, "type": "answer"}
