"""自然语言查询意图识别。

将用户输入分类为不同的查询意图，以便：
1. 路由到不同的处理流程
2. 提供针对性的查询建议
3. 优化多轮对话体验

支持的意图类型：
- query: 数据查询（默认）
- compare: 对比分析
- trend: 趋势分析
- breakdown: 下钻/维度拆解
- topn: Top N 排名
- clarification: 需要澄清/确认
- greeting: 问候/闲聊
- help: 帮助请求
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any

from app.config import get_settings
from app.services.llm import llm

logger = logging.getLogger(__name__)

INTENT_TYPES = [
    "query",          # 普通数据查询
    "compare",        # 对比分析（A vs B）
    "trend",          # 趋势分析（时间序列）
    "breakdown",      # 下钻/维度拆解
    "topn",           # Top N 排名
    "clarification",  # 需要澄清
    "greeting",       # 问候
    "help",           # 帮助
]

# 简单规则匹配（快速路径）
RULE_PATTERNS = {
    "greeting": [
        r"^(你好|您好|嗨|hello|hi|hey)",
        r"^(早上好|下午好|晚上好)",
    ],
    "help": [
        r"^(帮助|help|怎么用|如何使用|说明|文档)",
        r"^(你能做什么|你可以做什么|功能)",
    ],
    "compare": [
        r"(对比|比较|vs|versus|和.*相比|与.*相比|差异|区别)",
        r"(哪个更|哪个最|A和B|A与B)",
    ],
    "trend": [
        r"(趋势|变化|走势|增长|下降|同比|环比|over time)",
        r"(最近.*个月|最近.*年|过去.*时间|每月|每年|每季度)",
    ],
    "breakdown": [
        r"(按.*分组|按.*分类|各.*的|每个.*的|分别|拆解)",
        r"(维度|分布|占比|构成)",
    ],
    "topn": [
        r"(前\d+|top\s*\d+|排名|最多|最少|最大|最小|最好|最差)",
    ],
    "clarification": [
        r"^(什么|哪个|哪里|什么时候|为什么|怎么)",
        r"^(能否|可以|请|能否帮忙)",
    ],
}


def _rule_classify(question: str) -> str | None:
    """基于规则快速分类。"""
    q = question.lower().strip()
    for intent, patterns in RULE_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, q, re.IGNORECASE):
                return intent
    return None


INTENT_CLASSIFICATION_PROMPT = """你是一个查询意图分类专家。请分析用户的自然语言查询，将其分类为以下意图之一：

- query: 普通数据查询（如"销售额是多少"）
- compare: 对比分析（如"A和B的销售额对比"）
- trend: 趋势分析（如"最近一年的销售趋势"）
- breakdown: 下钻/维度拆解（如"按地区查看销售额"）
- topn: Top N 排名（如"销售额前10的商品"）
- clarification: 需要澄清或确认（如"你是什么意思"）
- greeting: 问候或闲聊（如"你好"）
- help: 帮助请求（如"你能做什么"）

请只返回 JSON 格式，不要其他解释：
{"intent": "意图类型", "confidence": 0.0-1.0, "entities": ["提取的关键实体"]}

用户查询：{question}
"""


def classify_intent(question: str) -> dict[str, Any]:
    """识别用户查询意图。
    
    先使用规则匹配，若置信度不高则调用 LLM。
    """
    # 快速规则匹配
    rule_intent = _rule_classify(question)
    if rule_intent:
        return {
            "intent": rule_intent,
            "confidence": 0.85,
            "entities": [],
            "method": "rule",
        }
    
    # LLM 分类
    try:
        prompt = INTENT_CLASSIFICATION_PROMPT.format(question=question)
        response = llm.complete(prompt, temperature=0.1)
        content = response.strip()
        # 提取 JSON
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
        result = json.loads(content.strip())
        intent = result.get("intent", "query")
        if intent not in INTENT_TYPES:
            intent = "query"
        return {
            "intent": intent,
            "confidence": result.get("confidence", 0.7),
            "entities": result.get("entities", []),
            "method": "llm",
        }
    except Exception as e:
        logger.warning("Intent classification failed: %s", e)
        return {
            "intent": "query",
            "confidence": 0.5,
            "entities": [],
            "method": "fallback",
        }


def get_intent_suggestions(intent: str) -> list[str]:
    """根据意图类型返回建议的后续查询模板。"""
    suggestions = {
        "query": [
            "具体查看哪个时间范围？",
            "需要按什么维度分组？",
            "是否需要对比其他指标？",
        ],
        "compare": [
            "需要对比哪些维度？",
            "时间范围是？",
            "是否需要趋势对比？",
        ],
        "trend": [
            "时间粒度是月/季/年？",
            "是否需要同比/环比？",
            "需要预测未来趋势吗？",
        ],
        "breakdown": [
            "按哪个维度拆解？",
            "是否需要多级下钻？",
            "时间范围是？",
        ],
        "topn": [
            "Top 多少？",
            "按什么指标排序？",
            "是否需要过滤条件？",
        ],
        "clarification": [
            "请提供更多细节",
            "您想查看哪个指标？",
            "时间范围是什么？",
        ],
        "greeting": [
            "请问有什么可以帮您的？",
            "您想查询什么数据？",
            "可以输入自然语言查询",
        ],
        "help": [
            "直接输入问题如'销售额是多少'",
            "支持对比、趋势、排名等分析",
            "可以保存查询到仪表盘",
        ],
    }
    return suggestions.get(intent, suggestions["query"])
