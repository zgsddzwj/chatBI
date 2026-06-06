"""LLM 关键词扩展服务。

在混合检索前，先用 LLM 扩展用户问题的同义词和相关概念，
解决语义相同但字面不同的问题（如"销售额"和"营收"）。
"""
from __future__ import annotations

import json
import logging
from typing import Any

from app.prompt_loader import load_prompt
from app.services.llm import get_llm

logger = logging.getLogger(__name__)

# 缓存扩展结果，避免重复调用 LLM
_expand_cache: dict[str, list[str]] = {}


def expand_keywords(question: str, use_cache: bool = True) -> list[str]:
    """使用 LLM 扩展用户问题的关键词。

    Args:
        question: 用户原始问题
        use_cache: 是否使用缓存

    Returns:
        扩展后的关键词列表（包含原始问题本身）
    """
    if use_cache and question in _expand_cache:
        return _expand_cache[question]

    llm = get_llm()
    prompt_template = load_prompt("extend_keywords")
    # 替换模板变量
    user_msg = prompt_template.replace("{query}", question)

    try:
        result = llm.chat_json(
            system="你是一个关键词扩展助手。请只输出 JSON，不要其他内容。",
            user=user_msg,
            temperature=0.1,
        )
    except Exception as exc:
        logger.warning("关键词扩展 LLM 调用失败: %s", exc)
        return [question]

    if not isinstance(result, dict):
        logger.warning("关键词扩展返回格式异常")
        return [question]

    keywords = result.get("keywords", [])
    if not isinstance(keywords, list):
        logger.warning("关键词扩展返回的 keywords 不是列表")
        return [question]

    # 去重并保留原始问题
    expanded = list(dict.fromkeys([question] + [str(k) for k in keywords]))

    if use_cache:
        _expand_cache[question] = expanded

    logger.info("关键词扩展: '%s' -> %s", question, expanded)
    return expanded


def clear_expand_cache() -> None:
    """清空关键词扩展缓存。"""
    global _expand_cache
    _expand_cache = {}
