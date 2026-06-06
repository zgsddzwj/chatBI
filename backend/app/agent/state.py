"""Agent 工作流状态定义。"""
from __future__ import annotations

from typing import TypedDict


class ChatState(TypedDict):
    """工作流状态，每个节点读写其中的字段。"""

    # 输入
    question: str
    history: list[dict[str, str]] | None

    # 中间状态
    keywords: list[str]
    schema_prompt: str

    # SQL 生成
    sql: str
    explanation: str
    needs_clarification: bool
    clarification: str

    # 验证/纠错
    error: str | None
    fixed_sql: str | None

    # 执行结果
    data: dict | None
    chart: dict | None
    summary: str

    # 输出类型
    type: str  # "answer" | "clarification" | "error"
