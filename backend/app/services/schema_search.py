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

import jieba.analyse

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

# 业务关键词到表的映射（已适配新版数仓表 dim_* / fact_*）
_KEYWORD_TABLE_MAP: dict[str, list[str]] = {
    "用户": ["dim_customer"],
    "客户": ["dim_customer"],
    "会员": ["dim_customer"],
    "注册": ["dim_customer"],
    "性别": ["dim_customer"],
    "年龄": ["dim_customer"],
    "地区": ["dim_region", "fact_order"],
    "省份": ["dim_region"],
    "城市": ["dim_region"],
    "商品": ["dim_product"],
    "产品": ["dim_product"],
    "品类": ["dim_product"],
    "类别": ["dim_product"],
    "分类": ["dim_product"],
    "品牌": ["dim_product"],
    "价格": ["dim_product", "fact_order"],
    "成本": ["dim_product"],
    "利润": ["dim_product", "fact_order"],
    "订单": ["fact_order"],
    "销售": ["fact_order", "dim_product"],
    "销售额": ["fact_order"],
    "营收": ["fact_order"],
    "gmv": ["fact_order"],
    "金额": ["fact_order"],
    "购买": ["fact_order"],
    "下单": ["fact_order"],
    "支付": ["fact_order"],
    "发货": ["fact_order"],
    "完成": ["fact_order"],
    "退款": ["fact_order"],
    "退货": ["fact_order"],
    "渠道": ["fact_order"],
    "web": ["fact_order"],
    "app": ["fact_order"],
    "小程序": ["fact_order"],
    "时间": ["dim_date", "fact_order"],
    "日期": ["dim_date", "fact_order"],
    "月份": ["dim_date"],
    "年份": ["dim_date"],
    "季度": ["dim_date"],
    "趋势": ["fact_order"],
    "数量": ["fact_order"],
    "销量": ["fact_order"],
}


# jieba 分词允许的词性
# n: 名词, nr: 人名, ns: 地名, nt: 机构团体名, nz: 其他专有名词
# v: 动词, vn: 名动词, a: 形容词, an: 名形词
# eng: 英文, i: 成语, l: 常用固定短语
_JIEBA_ALLOW_POS = (
    "n", "nr", "ns", "nt", "nz", "v", "vn", "a", "an", "eng", "i", "l"
)


def _tokenize(text: str) -> list[str]:
    """分词：使用 jieba 提取中文关键词 + 英文单词。

    相比原版的简单滑动窗口分词，jieba 能更准确地识别中文词组边界，
    例如"销售额"会被识别为一个词而非"销售"+"额"。
    """
    tokens: list[str] = []

    # 使用 jieba 提取关键词（基于 TF-IDF）
    keywords = jieba.analyse.extract_tags(text, allowPOS=_JIEBA_ALLOW_POS)
    tokens.extend([kw for kw in keywords if kw not in _STOP_WORDS])

    # 提取英文单词
    english = re.findall(r"[a-zA-Z]+", text.lower())
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
        # 关系字符串格式: "fact_order.customer_id -> dim_customer.customer_id"
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
