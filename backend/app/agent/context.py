"""Agent 运行时上下文定义。"""
from __future__ import annotations

from typing import TypedDict

from app.config import Settings
from app.services.llm import LLMClient


class ChatContext(TypedDict):
    """运行时上下文，通过 LangGraph 的 context 参数注入每个节点。

    注意：TypedDict 不能包含非序列化对象（如数据库连接），
    所以这里只放轻量级的配置和客户端。
    """

    llm: LLMClient
    settings: Settings
