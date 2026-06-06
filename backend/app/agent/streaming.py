"""LangGraph 流式执行与 SSE 适配。

将 LangGraph 的节点级流式输出转换为 SSE 事件流。
"""
from __future__ import annotations

import json
import logging
from typing import Any

from app.agent.graph import graph
from app.agent.state import ChatState

logger = logging.getLogger(__name__)

# 节点到中文步骤名的映射
_STEP_NAMES = {
    "extract_keywords": "提取关键词",
    "generate_sql": "生成 SQL",
    "execute_sql": "执行 SQL",
    "correct_sql": "修正 SQL",
    "summarize": "总结结果",
}


def _event(data: dict) -> str:
    """生成 SSE 事件。"""
    return f"data: {json.dumps(data, ensure_ascii=False, default=str)}\n\n"


def stream_agent(question: str, history: list[dict[str, str]] | None = None):
    """流式运行 Agent，逐节点推送进度。

    Yields SSE 事件：
    - {"type": "progress", "step": "...", "status": "running/success/error"}
    - {"type": "sql", "sql": "...", "explanation": "..."}
    - {"type": "data", "data": {...}}
    - {"type": "chart", "chart": {...}}
    - {"type": "summary", "summary": "..."}
    - {"type": "done"}
    - {"type": "error", "error": "..."}
    - {"type": "clarification", "clarification": "..."}
    """
    state = ChatState(
        question=question,
        history=history,
        keywords=[],
        schema_prompt="",
        sql="",
        explanation="",
        needs_clarification=False,
        clarification="",
        error=None,
        fixed_sql=None,
        data=None,
        chart=None,
        summary="",
        type="answer",
    )

    # 记录已完成的节点，避免重复推送
    completed_nodes = set()

    for node_name, node_state, _ in graph.stream(state, stream_mode="updates"):
        step_name = _STEP_NAMES.get(node_name, node_name)

        # 推送节点开始
        if node_name not in completed_nodes:
            yield _event({
                "type": "progress",
                "step": step_name,
                "status": "running",
                "node": node_name,
            })

        # 检查是否需要澄清
        if node_state.get("needs_clarification"):
            yield _event({
                "type": "progress",
                "step": step_name,
                "status": "success",
                "node": node_name,
            })
            yield _event({
                "type": "clarification",
                "clarification": node_state.get("clarification", ""),
            })
            return

        # 检查错误
        if node_state.get("error") and node_name != "execute_sql":
            # execute_sql 的错误会走 correct_sql 分支，不在这里中断
            yield _event({
                "type": "progress",
                "step": step_name,
                "status": "error",
                "node": node_name,
            })
            yield _event({
                "type": "error",
                "error": node_state["error"],
            })
            return

        # 推送节点完成
        yield _event({
            "type": "progress",
            "step": step_name,
            "status": "success",
            "node": node_name,
        })
        completed_nodes.add(node_name)

        # 推送阶段性结果
        if node_name == "generate_sql" and node_state.get("sql"):
            yield _event({
                "type": "sql",
                "sql": node_state["sql"],
                "explanation": node_state.get("explanation", ""),
            })

        if node_name == "execute_sql" and node_state.get("data"):
            yield _event({
                "type": "data",
                "data": node_state["data"],
            })
            if node_state.get("chart"):
                yield _event({
                    "type": "chart",
                    "chart": node_state["chart"],
                })

        if node_name == "summarize" and node_state.get("summary"):
            yield _event({
                "type": "summary",
                "summary": node_state["summary"],
            })

    yield _event({"type": "done"})
