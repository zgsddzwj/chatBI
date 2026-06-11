"""查询建议自动补全。

基于以下数据源生成查询建议：
1. 示例问题（预定义）
2. 热门查询（缓存统计）
3. 用户历史查询
4. 当前输入前缀匹配
5. 意图相关的模板
"""
from __future__ import annotations

import logging
from typing import Any

from app.database import app_engine
from app.services.cache_v2 import get_cache_stats
from app.services.intent_classifier import classify_intent, get_intent_suggestions

logger = logging.getLogger(__name__)

# 预定义的示例问题
SAMPLE_SUGGESTIONS = [
    "2024 年每个月的销售额是多少？",
    "销售额排名前 5 的商品是哪些？",
    "各地区的订单数量分布如何？",
    "不同商品品类的销售额对比",
    "2025 年第一季度的总销售额是多少？",
    "每个商品品牌的总营收和总销量",
    "最近 6 个月各地区的销售额趋势",
    "哪个会员等级的客户消费最多？",
    "按省份查看订单金额分布",
    "华东地区和华南地区的销售额对比",
    "2024年各季度的销售趋势",
    "销售额最高的品牌是哪个？",
    "男性和女性客户的消费对比",
    "按月份查看订单数量变化",
    "VIP会员的平均订单金额",
]

# 查询模板
QUERY_TEMPLATES = {
    "sales": [
        "{time}的销售额是多少？",
        "{time}销售额排名前{top}的{dim}是哪些？",
        "各{dim}的销售额分布",
        "{dim}的销售额对比",
    ],
    "orders": [
        "{time}的订单数量是多少？",
        "各{dim}的订单数量分布",
        "{time}订单数量排名前{top}的{dim}",
    ],
    "customers": [
        "各{dim}的客户数量",
        "{dim}的客户消费对比",
        "消费最多的{top}个客户",
    ],
    "trend": [
        "最近{time}的销售额趋势",
        "{time}各{dim}的销售变化",
        "同比/环比分析",
    ],
}

DIMENSIONS = ["地区", "品类", "品牌", "会员等级", "省份", "月份", "季度"]
TIME_RANGES = ["2024年", "2025年", "最近6个月", "最近3个月", "第一季度", "第二季度"]


def get_suggestions(
    prefix: str = "",
    conversation_id: int | None = None,
    limit: int = 8,
) -> list[dict[str, Any]]:
    """获取查询建议。
    
    综合多个来源生成建议列表。
    """
    suggestions: list[dict[str, Any]] = []
    seen: set[str] = set()
    
    def add(text: str, source: str, score: float = 1.0) -> None:
        if text in seen:
            return
        seen.add(text)
        suggestions.append({
            "text": text,
            "source": source,
            "score": score,
        })
    
    # 1. 前缀匹配（最高优先级）
    if prefix:
        prefix_lower = prefix.lower()
        for sample in SAMPLE_SUGGESTIONS:
            if prefix_lower in sample.lower():
                add(sample, "sample", score=2.0)
    
    # 2. 意图相关建议
    if prefix:
        intent_result = classify_intent(prefix)
        intent = intent_result["intent"]
        for suggestion in get_intent_suggestions(intent):
            # 将建议模板与实际输入结合
            combined = f"{prefix} - {suggestion}"
            add(combined, "intent", score=1.5)
    
    # 3. 热门查询
    try:
        stats = get_cache_stats()
        for q in stats.get("top_queries", [])[:5]:
            text = q["sql"]
            # 将 SQL 转换为自然语言（简化）
            if "sum" in text.lower() and "order_amount" in text.lower():
                text = "查看销售额统计"
            elif "count" in text.lower():
                text = "查看订单数量统计"
            add(text, "popular", score=1.2)
    except Exception:
        pass
    
    # 4. 用户历史查询（如果有 conversation_id）
    if conversation_id:
        try:
            history = _get_conversation_history(conversation_id)
            for h in history[:5]:
                add(h, "history", score=1.3)
        except Exception:
            pass
    
    # 5. 填充示例问题
    for sample in SAMPLE_SUGGESTIONS:
        add(sample, "sample", score=1.0)
    
    # 按分数排序并截断
    suggestions.sort(key=lambda x: x["score"], reverse=True)
    return suggestions[:limit]


def get_autocomplete(prefix: str, limit: int = 5) -> list[str]:
    """自动补全：返回匹配前缀的建议文本列表。"""
    if not prefix or len(prefix) < 2:
        return SAMPLE_SUGGESTIONS[:limit]
    
    prefix_lower = prefix.lower()
    matches = []
    
    # 匹配示例问题
    for sample in SAMPLE_SUGGESTIONS:
        if prefix_lower in sample.lower():
            matches.append(sample)
    
    # 匹配模板
    for category, templates in QUERY_TEMPLATES.items():
        for template in templates:
            if prefix_lower in template.lower():
                # 填充模板
                for dim in DIMENSIONS[:2]:
                    for time in TIME_RANGES[:2]:
                        filled = template.format(dim=dim, time=time, top="5")
                        if filled not in matches:
                            matches.append(filled)
    
    return matches[:limit]


def _get_conversation_history(conversation_id: int) -> list[str]:
    """获取对话历史中的用户问题。"""
    from sqlalchemy import text
    with app_engine.begin() as conn:
        rows = conn.execute(
            text("""
                SELECT content FROM messages
                WHERE conversation_id = :cid AND role = 'user'
                ORDER BY created_at DESC
                LIMIT 10
            """),
            {"cid": conversation_id},
        ).fetchall()
    return [r.content for r in rows if r.content]
