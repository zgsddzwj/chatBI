"""结果总结节点（已废弃，新版工作流在 execute_sql 后直接结束）。

旧版节点，基于 ChatState（question/sql/data/chart 等字段）。
新版工作流（app.agent.graph）使用 DataAgentState，流式输出由 QueryService 处理，
不再单独设置 summarize 节点。
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


# 旧版 summarize 节点已废弃
# 新版如需总结功能，建议在 execute_sql 节点后通过 LLM 生成，或在前端展示原始数据
