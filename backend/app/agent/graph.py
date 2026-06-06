"""LangGraph 工作流定义。

工作流：
    START -> extract_keywords -> generate_sql -> validate_sql
                                      | 失败
                                      v
                                correct_sql --(重试)--> execute_sql -> summarize -> END
                                      | 仍失败
                                      v
                                    END (返回错误)
"""
from __future__ import annotations

import logging
from typing import Any

from langgraph.constants import START, END
from langgraph.graph import StateGraph

from app.agent.nodes.correct_sql import correct_sql
from app.agent.nodes.execute_sql import execute_sql
from app.agent.nodes.extract_keywords import extract_keywords
from app.agent.nodes.generate_sql import generate_sql
from app.agent.nodes.summarize import summarize
from app.agent.state import ChatState

logger = logging.getLogger(__name__)

# 构建工作流
graph_builder = StateGraph(state_schema=ChatState)

# 添加节点
graph_builder.add_node("extract_keywords", extract_keywords)
graph_builder.add_node("generate_sql", generate_sql)
graph_builder.add_node("correct_sql", correct_sql)
graph_builder.add_node("execute_sql", execute_sql)
graph_builder.add_node("summarize", summarize)

# 添加边
graph_builder.add_edge(START, "extract_keywords")
graph_builder.add_edge("extract_keywords", "generate_sql")
graph_builder.add_edge("generate_sql", "execute_sql")
graph_builder.add_edge("execute_sql", "summarize")
graph_builder.add_edge("summarize", END)

# 条件边：execute_sql 失败时走 correct_sql
graph_builder.add_conditional_edges(
    "execute_sql",
    lambda state: "correct_sql" if state.get("error") else "summarize",
    {"correct_sql": "correct_sql", "summarize": "summarize"},
)

# correct_sql 后重试 execute_sql
graph_builder.add_edge("correct_sql", "execute_sql")

# 编译图
graph = graph_builder.compile()


def run_agent(question: str, history: list[dict[str, str]] | None = None) -> dict[str, Any]:
    """运行完整的 Agent 工作流。

    Args:
        question: 用户问题
        history: 对话历史

    Returns:
        最终结果字典
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

    result = graph.invoke(state)

    # 处理 clarification
    if result.get("needs_clarification"):
        return {
            "type": "clarification",
            "clarification": result["clarification"],
        }

    # 处理错误
    if result.get("error"):
        return {
            "type": "error",
            "error": result["error"],
        }

    return {
        "type": "answer",
        "sql": result.get("fixed_sql") or result["sql"],
        "explanation": result.get("explanation", ""),
        "data": result["data"],
        "chart": result["chart"],
        "summary": result["summary"],
    }
