"""LLM 客户端封装。

DeepSeek 兼容 OpenAI SDK 协议，所以直接复用 openai 库，
只需要把 base_url 指向 DeepSeek。
后续要切换到 GPT-4 / Qwen 等只需改配置，无需改代码。
"""
from __future__ import annotations

import json
import logging
from typing import Any

from openai import OpenAI

from app.config import get_settings

logger = logging.getLogger(__name__)


class LLMClient:
    def __init__(self) -> None:
        settings = get_settings()
        if not settings.deepseek_api_key:
            logger.warning("DEEPSEEK_API_KEY 未配置，LLM 调用将失败。")
        self._client = OpenAI(
            api_key=settings.deepseek_api_key or "missing",
            base_url=settings.deepseek_base_url,
            timeout=settings.llm_timeout_seconds,
        )
        self._model = settings.deepseek_model

    def chat_json(self, system: str, user: str, temperature: float = 0.1) -> dict[str, Any]:
        """让 LLM 返回 JSON 对象。"""
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=temperature,
            response_format={"type": "json_object"},
        )
        if not response.choices:
            raise ValueError("LLM 未返回任何候选回复")
        content = (response.choices[0].message.content or "").strip() or "{}"
        try:
            return json.loads(content)
        except json.JSONDecodeError as exc:
            logger.error("LLM 返回的不是合法 JSON: %s", content)
            raise ValueError(f"LLM 返回的不是合法 JSON: {exc}") from exc

    def chat_text(self, system: str, user: str, temperature: float = 0.3) -> str:
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=temperature,
        )
        if not response.choices:
            return ""
        return (response.choices[0].message.content or "").strip()


_singleton: LLMClient | None = None


def get_llm() -> LLMClient:
    global _singleton
    if _singleton is None:
        _singleton = LLMClient()
    return _singleton
