"""LangGraph 流式执行与 SSE 适配（已废弃，请使用 app.services.query_service）。

旧版流式输出适配器，基于旧 graph（extract_keywords -> generate_sql -> execute_sql）。
新版已迁移至 app.agent.graph + app.services.query_service，使用 DataAgentState/DataAgentContext。
"""
from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


def _event(data: dict) -> str:
    """生成 SSE 事件。"""
    return f"data: {json.dumps(data, ensure_ascii=False, default=str)}\n\n"


# 旧版 stream_agent 已废弃，如需使用请迁移到 QueryService
# from app.services.query_service import QueryService
