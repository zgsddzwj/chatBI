"""LLM 客户端封装（带容错增强）。

特性：
1. 指数退避重试：网络错误自动重试，最多 3 次
2. 熔断保护：连续失败达到阈值后短路，避免雪崩
3. 超时控制：区分连接超时和读取超时
4. JSON 容错：自动修复 LLM 常见的 JSON 格式错误

DeepSeek 兼容 OpenAI SDK 协议，所以直接复用 openai 库，
只需要把 base_url 指向 DeepSeek。
后续要切换到 GPT-4 / Qwen 等只需改配置，无需改代码。
"""
from __future__ import annotations

import json
import logging
import re
import time
from typing import Any

from openai import APIConnectionError, APITimeoutError, OpenAI, RateLimitError

from app.config import get_settings

logger = logging.getLogger(__name__)

# ── 熔断器状态 ──────────────────────────────────────────────
_MAX_CONSECUTIVE_FAILURES = 5  # 连续失败阈值
_CIRCUIT_RESET_SECONDS = 60  # 熔断恢复冷却时间
_circuit: dict[str, Any] = {
    "failures": 0,
    "tripped": False,
    "tripped_at": 0.0,
}


def _circuit_allow() -> bool:
    """检查熔断器是否允许请求通过。"""
    if not _circuit["tripped"]:
        return True
    elapsed = time.monotonic() - _circuit["tripped_at"]
    if elapsed >= _CIRCUIT_RESET_SECONDS:
        logger.info("熔断器冷却结束，尝试半开恢复")
        _circuit["tripped"] = False
        _circuit["failures"] = 0
        return True
    return False


def _circuit_record_success() -> None:
    _circuit["failures"] = 0
    _circuit["tripped"] = False


def _circuit_record_failure() -> None:
    _circuit["failures"] += 1
    if _circuit["failures"] >= _MAX_CONSECUTIVE_FAILURES:
        _circuit["tripped"] = True
        _circuit["tripped_at"] = time.monotonic()
        logger.error("熔断器触发：连续失败 %d 次，短路 %ds", _circuit["failures"], _CIRCUIT_RESET_SECONDS)


def _retry_with_backoff(func, max_retries: int = 3, base_delay: float = 1.0):
    """指数退避重试包装器。

    仅对可重试的异常（超时、连接错误、限流）进行重试。
    """
    last_exc: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            return func()
        except (APITimeoutError, APIConnectionError, RateLimitError) as exc:
            last_exc = exc
            if attempt < max_retries:
                delay = base_delay * (2 ** attempt)
                logger.warning(
                    "LLM 调用失败（第 %d 次），%0.1fs 后重试: %s",
                    attempt + 1, delay, exc,
                )
                time.sleep(delay)
            else:
                logger.error("LLM 调用重试 %d 次后仍失败: %s", max_retries, exc)
        except Exception as exc:
            # 非网络类异常不重试
            raise
    raise last_exc  # type: ignore[misc]


def _repair_json(content: str) -> str:
    """尝试修复 LLM 返回的常见 JSON 格式问题。

    - 移除 markdown 代码块标记
    - 修复尾随逗号
    - 提取 JSON 主体
    """
    # 移除 markdown 代码块
    content = re.sub(r"^```(?:json)?\s*", "", content.strip())
    content = re.sub(r"\s*```$", "", content.strip())
    # 移除尾随逗号
    content = re.sub(r",\s*}", "}", content)
    content = re.sub(r",\s*]", "]", content)
    return content


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
        """让 LLM 返回 JSON 对象（带重试和容错）。"""
        if not _circuit_allow():
            raise RuntimeError("LLM 服务熔断中，请稍后重试")

        def _call() -> dict[str, Any]:
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
            except json.JSONDecodeError:
                # 尝试修复后重新解析
                repaired = _repair_json(content)
                try:
                    return json.loads(repaired)
                except json.JSONDecodeError as exc:
                    logger.error("LLM 返回的不是合法 JSON（修复后仍失败）: %s", content[:200])
                    raise ValueError(f"LLM 返回的不是合法 JSON: {exc}") from exc

        try:
            result = _retry_with_backoff(_call)
            _circuit_record_success()
            return result
        except Exception:
            _circuit_record_failure()
            raise

    def chat_text(self, system: str, user: str, temperature: float = 0.3) -> str:
        """让 LLM 返回文本（带重试和容错）。"""
        if not _circuit_allow():
            raise RuntimeError("LLM 服务熔断中，请稍后重试")

        def _call() -> str:
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

        try:
            result = _retry_with_backoff(_call)
            _circuit_record_success()
            return result
        except Exception:
            _circuit_record_failure()
            raise

    def get_circuit_status(self) -> dict[str, Any]:
        """获取熔断器状态（用于健康检查和调试）。"""
        return {
            "tripped": _circuit["tripped"],
            "failures": _circuit["failures"],
            "tripped_at": _circuit["tripped_at"],
            "threshold": _MAX_CONSECUTIVE_FAILURES,
            "reset_seconds": _CIRCUIT_RESET_SECONDS,
        }


_singleton: LLMClient | None = None


def get_llm() -> LLMClient:
    global _singleton
    if _singleton is None:
        _singleton = LLMClient()
    return _singleton
