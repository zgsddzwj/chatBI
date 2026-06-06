"""LLM 客户端管理器。

统一管理 LLM 客户端的初始化和关闭。
"""
from __future__ import annotations

from app.services.llm import LLMClient, get_llm


class LLMClientManager:
    """LLM 客户端管理器（当前为单例包装，未来可扩展为连接池）。"""

    def __init__(self) -> None:
        self._client: LLMClient | None = None

    def init(self) -> None:
        """初始化客户端。"""
        self._client = get_llm()

    @property
    def client(self) -> LLMClient:
        if self._client is None:
            self.init()
        return self._client

    def close(self) -> None:
        """关闭客户端（当前无状态，预留接口）。"""
        self._client = None


# 全局实例
llm_client_manager = LLMClientManager()
