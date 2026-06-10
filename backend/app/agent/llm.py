"""LLM 客户端封装（带重试、降级、超时）。

增强点：
1. 自动重试：API 失败时自动重试 3 次（指数退避）
2. 超时控制：防止 LLM 调用阻塞
3. 降级策略：主模型失败时自动切换到备用模型
4. 错误包装：统一异常类型，便于上游处理
"""
from __future__ import annotations

import logging
import time
from typing import Any

from langchain.chat_models import init_chat_model

from app.conf.app_config import app_config

logger = logging.getLogger(__name__)

# 延迟初始化，避免在导入时就触发 API 调用
_llm = None
_llm_backup = None

# 重试配置
MAX_RETRIES = 3
RETRY_DELAY_BASE = 1.0  # 秒
LLM_TIMEOUT = 60  # 秒


def get_llm():
    """获取主 LLM 客户端（DeepSeek）。"""
    global _llm
    if _llm is None:
        _llm = init_chat_model(
            model=app_config.llm.model_name,
            model_provider="openai",
            api_key=app_config.llm.api_key or "missing",
            base_url=app_config.llm.base_url,
            temperature=0,
            timeout=LLM_TIMEOUT,
        )
    return _llm


def get_backup_llm():
    """获取备用 LLM 客户端（主模型失败时降级使用）。"""
    global _llm_backup
    if _llm_backup is None:
        # 备用：使用 OpenAI GPT-3.5（如果配置了 OPENAI_API_KEY）
        # 否则复用主模型配置
        import os

        openai_key = os.getenv("OPENAI_API_KEY", app_config.llm.api_key)
        openai_base = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        _llm_backup = init_chat_model(
            model="gpt-3.5-turbo",
            model_provider="openai",
            api_key=openai_key or "missing",
            base_url=openai_base,
            temperature=0,
            timeout=LLM_TIMEOUT,
        )
    return _llm_backup


def _with_retry(func, *args, **kwargs) -> Any:
    """带重试的 LLM 调用。

    策略：
    1. 先尝试主模型，失败则指数退避重试
    2. 主模型全部失败后，尝试备用模型
    3. 备用模型也失败，抛出统一异常
    """
    last_error = None

    # 尝试主模型（带重试）
    for attempt in range(MAX_RETRIES):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            last_error = e
            logger.warning(
                "LLM 调用失败 (attempt %d/%d): %s",
                attempt + 1,
                MAX_RETRIES,
                str(e)[:200],
            )
            if attempt < MAX_RETRIES - 1:
                delay = RETRY_DELAY_BASE * (2**attempt)
                logger.info("等待 %.1f 秒后重试...", delay)
                time.sleep(delay)

    # 主模型全部失败，尝试备用模型
    logger.warning("主模型全部失败，尝试备用模型...")
    try:
        backup_llm = get_backup_llm()
        # 动态调用备用模型的同名方法
        backup_func = getattr(backup_llm, func.__name__)
        return backup_func(*args, **kwargs)
    except Exception as e:
        logger.error("备用模型也失败: %s", str(e)[:200])
        raise LLMError(f"LLM 调用失败（主模型和备用模型均不可用）: {last_error}") from e


class LLMError(Exception):
    """LLM 调用失败的统一异常。"""

    pass


class ResilientLLM:
    """带容错能力的 LLM 代理。

    用法：
        from app.agent.llm import resilient_llm
        result = await resilient_llm.ainvoke(messages)
    """

    def __init__(self):
        self._llm = get_llm()

    def invoke(self, *args, **kwargs):
        return _with_retry(self._llm.invoke, *args, **kwargs)

    async def ainvoke(self, *args, **kwargs):
        # 异步重试
        last_error = None
        for attempt in range(MAX_RETRIES):
            try:
                return await self._llm.ainvoke(*args, **kwargs)
            except Exception as e:
                last_error = e
                logger.warning(
                    "LLM 异步调用失败 (attempt %d/%d): %s",
                    attempt + 1,
                    MAX_RETRIES,
                    str(e)[:200],
                )
                if attempt < MAX_RETRIES - 1:
                    delay = RETRY_DELAY_BASE * (2**attempt)
                    await __import__("asyncio").sleep(delay)

        # 尝试备用模型
        logger.warning("主模型异步调用全部失败，尝试备用模型...")
        try:
            backup_llm = get_backup_llm()
            return await backup_llm.ainvoke(*args, **kwargs)
        except Exception as e:
            raise LLMError(f"LLM 异步调用失败: {last_error}") from e


# 兼容旧代码直接引用 llm 的写法
class _LLMProxy:
    def __getattr__(self, name):
        return getattr(get_llm(), name)


llm = _LLMProxy()

# 带容错的 LLM 实例
resilient_llm = ResilientLLM()
