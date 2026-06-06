"""关键词提取节点。"""
from __future__ import annotations

import logging

from app.agent.state import ChatState
from app.services.keyword_expand import expand_keywords

logger = logging.getLogger(__name__)


def extract_keywords(state: ChatState) -> dict:
    """提取并扩展用户问题的关键词。"""
    question = state["question"]
    keywords = expand_keywords(question)
    logger.info("关键词提取: %s -> %s", question, keywords)
    return {"keywords": keywords}
