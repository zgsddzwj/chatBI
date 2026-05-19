"""Schema 智能检索：基于关键词相似度选择最相关的表。

当业务库表很多时，把所有表结构都喂给 LLM 会超出上下文窗口，
而且无关表会干扰 SQL 生成准确率。

本模块通过简单的 TF-IDF 风格的关键词匹配，
从用户问题中提取关键词，与表名、字段名、注释做相似度匹配，
只返回最相关的表结构给 LLM。

未来可替换为真正的向量检索（pgvector / faiss）。
"""
from __future__ import annotations

import re
from typing import Any

from app.schema_meta import BUSINESS_SCHEMA


# 停用词
_STOP_WORDS = {
    "的", "是", "在", "有", "和", "与", "或", "了", "吗", "什么", "多少",
    "如何", "怎么", "哪个", "哪些", "为", "从", "到", "对", "关于",
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "must", "shall", "can", "need", "dare",
    "ought", "used", "to", "of", "in", "for", "on", "with", "at", "by",
    "from", "as", "into", "through", "during", "before", "after", "above",
    "below", "between", "under", "again", "further", "then", "once",
    "here", "there", "when", "where", "why", "how", "all", "each",
    "few", "more", "most", "other", "some", "such", "no", "nor", "not",
    "only", "own", "same", "so", "than", "too", "very", "just", "and",
    "but", "if", "or", "because", "until", "while", "what", "which",
    "who", "whom", "this", "that", "these", "those", "am", "it", "its",
}

# 业务关键词到表的映射
_KEYWORD_TABLE_MAP: dict[str, list[str]] = {
    "用户": ["users"],
    "客户": ["users"],
    "会员": ["users"],
    "注册": ["users"],
    "性别": ["users"],
    "年龄": ["users"],
    "地区": ["users", "orders"],
    "商品": ["products"],
    "产品": ["products"],
    "品类": ["products"],
    "类别": ["products"],
    "分类": ["products"],
    "价格": ["products", "orders"],
    "成本": ["products"],
    "利润": ["products", "orders"],
    "订单": ["orders"],
    "销售": ["orders", "products"],
    "销售额": ["orders"],
    "营收": ["orders"],
    "gmv": ["orders"],
    "金额": ["orders"],
    "购买": ["orders"],
    "下单": ["orders"],
    "支付": ["orders"],
    "发货": ["orders"],
    "完成": ["orders"],
    "退款": ["orders"],
    "退货": ["orders"],
    "渠道": ["orders"],
    "web": ["orders"],
    "app": ["orders"],
    "小程序": ["orders"],
    "时间": ["orders", "users"],
    "日期": ["orders", "users"],
    "月份": ["orders"],
    "年份": ["orders", "users"],
    "季度": ["orders"],
    "趋势": ["orders"],
}


def _tokenize(text: str) -> list[str]:
    """分词：提取中文词组和英文单词。"""
    # 提取中文连续字符
    chinese = re.findall(r"[\u4e00-\u9fff]+", text)
    # 提取英文单词
    english = re.findall(r"[a-zA-Z]+", text.lower())
    tokens: list[str] = []
    for c in chinese:
        # 简单分词：2-4 字词组
        for length in range(4, 1, -1):
            for i in range(len(c) - length + 1):
                token = c[i:i + length]
                if token not in _STOP_WORDS:
                    tokens.append(token)
        # 单字
        for ch in c:
            if ch not in _STOP_WORDS:
                tokens.append(ch)
    tokens.extend([w for w in english if w not in _STOP_WORDS and len(w) > 1])
    return tokens


def _score_table(question_tokens: set[str], table: dict[str, Any]) -> float:
    """计算表与问题的相关度分数。"""
    score = 0.0
    table_name = table["name"].lower()
    table_comment = table.get("comment", "")

    # 表名匹配
    for token in question_tokens:
        token_lower = token.lower()
        if token_lower == table_name:
            score += 10.0
        if token_lower in table_name:
            score += 5.0

    # 注释匹配
    for token in question_tokens:
        if token in table_comment:
            score += 3.0

    # 字段匹配
    for col in table.get("columns", []):
        col_name = col["name"].lower()
        col_comment = col.get("comment", "")
        for token in question_tokens:
            token_lower = token.lower()
            if token_lower == col_name:
                score += 4.0
            if token_lower in col_name:
                score += 2.0
            if token in col_comment:
                score += 1.5

    # 关键词映射表匹配
    for token in question_tokens:
        if token in _KEYWORD_TABLE_MAP:
            if table_name in [t.lower() for t in _KEYWORD_TABLE_MAP[token]]:
                score += 8.0

    return score


def search_relevant_tables(question: str, top_k: int = 3) -> list[dict[str, Any]]:
    """根据用户问题检索最相关的表。"""
    tokens = set(_tokenize(question))
    if not tokens:
        return BUSINESS_SCHEMA["tables"]

    scored = []
    for table in BUSINESS_SCHEMA["tables"]:
        score = _score_table(tokens, table)
        scored.append((score, table))

    scored.sort(key=lambda x: x[0], reverse=True)

    # 如果最高分太低，返回所有表
    if scored and scored[0][0] < 3.0:
        return BUSINESS_SCHEMA["tables"]

    # 取 top_k，但如果分数差距太大，只取高分的
    results = []
    for i, (score, table) in enumerate(scored[:top_k]):
        if score > 0:
            results.append(table)

    return results if results else BUSINESS_SCHEMA["tables"]


def render_schema_prompt_filtered(question: str, top_k: int = 3) -> str:
    """渲染过滤后的 schema 提示文本。"""
    tables = search_relevant_tables(question, top_k)

    lines: list[str] = []
    lines.append(f"数据库方言: {BUSINESS_SCHEMA['dialect']}")
    lines.append("")
    lines.append("表结构:")
    for table in tables:
        lines.append(f"\n-- {table['comment']}")
        lines.append(f"TABLE {table['name']} (")
        col_lines = []
        for col in table["columns"]:
            col_lines.append(f"  {col['name']} {col['type']}  -- {col['comment']}")
        lines.append(",\n".join(col_lines))
        lines.append(")")

    # 只包含相关表的关系
    relevant_names = {t["name"] for t in tables}
    lines.append("")
    lines.append("表关系:")
    for rel in BUSINESS_SCHEMA["relations"]:
        # 关系字符串格式: "orders.user_id -> users.id"
        parts = rel.split(" -> ")
        if len(parts) == 2:
            left_table = parts[0].split(".")[0]
            right_table = parts[1].split(".")[0]
            if left_table in relevant_names or right_table in relevant_names:
                lines.append(f"  - {rel}")

    lines.append("")
    lines.append("业务提示:")
    for hint in BUSINESS_SCHEMA["hints"]:
        lines.append(f"  - {hint}")

    return "\n".join(lines)
