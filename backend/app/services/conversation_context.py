"""多轮对话上下文管理。

维护对话历史中的关键信息，用于：
1. 指代消解（如"那上个月呢" -> 继承上次的指标）
2. 意图继承（如"按地区分组" -> 继承上次的查询目标）
3. 时间范围推断（如"最近" -> 基于上次时间推算）
4. 过滤条件继承（如"只看华东" -> 继承上次的维度）
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ConversationContext:
    """对话上下文状态。"""
    # 当前聚焦的指标
    current_metric: str | None = None
    # 当前聚焦的维度
    current_dimension: str | None = None
    # 当前时间范围
    current_time_range: str | None = None
    # 当前过滤条件
    current_filters: list[str] = field(default_factory=list)
    # 上一条 SQL
    last_sql: str | None = None
    # 上一条查询意图
    last_intent: str | None = None
    # 历史提及的实体
    mentioned_entities: list[str] = field(default_factory=list)
    # 对话轮数
    turn_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "current_metric": self.current_metric,
            "current_dimension": self.current_dimension,
            "current_time_range": self.current_time_range,
            "current_filters": self.current_filters,
            "last_sql": self.last_sql,
            "last_intent": self.last_intent,
            "mentioned_entities": self.mentioned_entities,
            "turn_count": self.turn_count,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ConversationContext":
        return cls(
            current_metric=data.get("current_metric"),
            current_dimension=data.get("current_dimension"),
            current_time_range=data.get("current_time_range"),
            current_filters=data.get("current_filters", []),
            last_sql=data.get("last_sql"),
            last_intent=data.get("last_intent"),
            mentioned_entities=data.get("mentioned_entities", []),
            turn_count=data.get("turn_count", 0),
        )


# 上下文存储（内存中，可按需改为 Redis）
_context_store: dict[int, ConversationContext] = {}


def get_context(conversation_id: int) -> ConversationContext:
    """获取对话上下文，不存在则创建。"""
    if conversation_id not in _context_store:
        _context_store[conversation_id] = ConversationContext()
    return _context_store[conversation_id]


def update_context(
    conversation_id: int,
    question: str,
    sql: str | None = None,
    intent: str | None = None,
) -> ConversationContext:
    """根据新的用户输入更新上下文。"""
    ctx = get_context(conversation_id)
    ctx.turn_count += 1
    
    if sql:
        ctx.last_sql = sql
        # 从 SQL 中提取指标
        metrics = _extract_metrics(sql)
        if metrics:
            ctx.current_metric = metrics[0]
        # 从 SQL 中提取维度
        dims = _extract_dimensions(sql)
        if dims:
            ctx.current_dimension = dims[0]
        # 从 SQL 中提取时间范围
        time_range = _extract_time_range(sql)
        if time_range:
            ctx.current_time_range = time_range
        # 从 SQL 中提取过滤条件
        filters = _extract_filters(sql)
        if filters:
            ctx.current_filters = filters
    
    if intent:
        ctx.last_intent = intent
    
    # 提取问题中的实体
    entities = _extract_entities(question)
    ctx.mentioned_entities.extend(entities)
    ctx.mentioned_entities = list(set(ctx.mentioned_entities))[-10:]  # 保留最近10个
    
    return ctx


def clear_context(conversation_id: int) -> None:
    """清空对话上下文。"""
    _context_store.pop(conversation_id, None)


def expand_question(conversation_id: int, question: str) -> str:
    """基于上下文扩展用户问题（指代消解）。
    
    例如：
    - "那上个月呢" -> "2024年1月的销售额是多少"
    - "按地区分组" -> "按地区分组查看销售额"
    """
    ctx = get_context(conversation_id)
    if ctx.turn_count == 0:
        return question
    
    expanded = question
    
    # 指代消解
    pronouns = ["那", "这个", "那个", "它", "它们", "上次", "之前"]
    if any(p in expanded for p in pronouns) or expanded.endswith("呢"):
        # 继承指标
        if ctx.current_metric and ctx.current_metric not in expanded:
            expanded = f"{expanded}（{ctx.current_metric}）"
        # 继承维度
        if ctx.current_dimension and "按" not in expanded and "分组" not in expanded:
            if "分组" in expanded or "按" in expanded:
                pass
            else:
                expanded = f"{expanded}，按{ctx.current_dimension}分组"
    
    # 时间推断
    time_keywords = ["最近", "上个月", "上季度", "去年", "今年", "本月"]
    if any(kw in expanded for kw in time_keywords):
        if ctx.current_time_range and ctx.current_time_range not in expanded:
            # 简单替换，实际可更智能
            pass
    
    # 如果扩展后有变化，记录日志
    if expanded != question:
        logger.info("Question expanded: '%s' -> '%s'", question, expanded)
    
    return expanded


# ========== 实体提取辅助函数 ==========

METRIC_PATTERNS = [
    r"(?:sum|avg|count|max|min)\((\w+)\)",
    r"(\w+_amount)",
    r"(\w+_quantity)",
    r"(\w+_count)",
    r"(\w+_sales)",
    r"(\w+_revenue)",
]

DIMENSION_PATTERNS = [
    r"group\s+by\s+(\w+\.\w+)",
    r"group\s+by\s+(\w+)",
    r"join\s+dim_(\w+)",
]

TIME_PATTERNS = [
    r"year\s*=\s*(\d{4})",
    r"quarter\s*=\s*['\"]?(Q?\d)['\"]?",
    r"month\s*=\s*(\d{1,2})",
    r"date_id\s+between\s+(\d{8})\s+and\s+(\d{8})",
]

FILTER_PATTERNS = [
    r"where\s+(.+?)(?:group|order|limit|$)",
]

ENTITY_PATTERNS = [
    r"(?:dim|fact)_(\w+)",
    r"(\w+_name)",
    r"(\w+_level)",
    r"(\w+_category)",
]


def _extract_metrics(sql: str) -> list[str]:
    """从 SQL 中提取指标。"""
    metrics = []
    for pattern in METRIC_PATTERNS:
        for match in re.finditer(pattern, sql, re.IGNORECASE):
            metrics.append(match.group(1))
    return list(dict.fromkeys(metrics))  # 去重保序


def _extract_dimensions(sql: str) -> list[str]:
    """从 SQL 中提取维度。"""
    dims = []
    for pattern in DIMENSION_PATTERNS:
        for match in re.finditer(pattern, sql, re.IGNORECASE):
            dims.append(match.group(1).replace("dim_", ""))
    return list(dict.fromkeys(dims))


def _extract_time_range(sql: str) -> str | None:
    """从 SQL 中提取时间范围。"""
    for pattern in TIME_PATTERNS:
        match = re.search(pattern, sql, re.IGNORECASE)
        if match:
            return match.group(0)
    return None


def _extract_filters(sql: str) -> list[str]:
    """从 SQL 中提取过滤条件。"""
    filters = []
    for pattern in FILTER_PATTERNS:
        for match in re.finditer(pattern, sql, re.IGNORECASE):
            filters.append(match.group(1).strip())
    return filters


def _extract_entities(text: str) -> list[str]:
    """从文本中提取实体。"""
    entities = []
    for pattern in ENTITY_PATTERNS:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            entities.append(match.group(1))
    return list(dict.fromkeys(entities))
