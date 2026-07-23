"""SQL 安全校验：只允许只读 SELECT，禁止任何写操作或多语句。

这是 ChatBI 中最容易被忽视的安全点 —— LLM 可能在 prompt 注入下生成
DROP / DELETE 之类的语句。哪怕业务库使用了只读账号，应用层也应做防御。
"""
from __future__ import annotations

import re

import sqlparse
from sqlparse.sql import Statement

DANGEROUS_KEYWORDS = {
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE",
    "CREATE", "REPLACE", "GRANT", "REVOKE", "ATTACH", "DETACH",
    "PRAGMA", "VACUUM", "REINDEX",
}

# 分号后跟内容视为多语句注入尝试
_SEMICOLON_PATTERN = re.compile(r";\s*\S", re.IGNORECASE)


class UnsafeSQLError(ValueError):
    """SQL 校验失败时抛出。"""


def _strip_comments(sql: str) -> str:
    return sqlparse.format(sql, strip_comments=True).strip()


def validate_sql(sql: str) -> str:
    """校验 SQL 是否安全，并返回规范化后的单条语句。

    规则:
    1. 必须是单条语句
    2. 必须是 SELECT 或 WITH 起头
    3. 不能包含写操作关键字
    """
    if not sql or not sql.strip():
        raise UnsafeSQLError("SQL 为空")

    cleaned = _strip_comments(sql).rstrip(";").strip()

    # 额外检测：分号后跟非空白内容（多语句注入尝试）
    if _SEMICOLON_PATTERN.search(cleaned):
        raise UnsafeSQLError("检测到分号后跟内容，疑似多语句注入")

    statements = [s for s in sqlparse.parse(cleaned) if str(s).strip()]
    if len(statements) != 1:
        raise UnsafeSQLError("只允许执行单条 SQL 语句")

    stmt: Statement = statements[0]
    first_token = next((t for t in stmt.tokens if not t.is_whitespace), None)
    if first_token is None:
        raise UnsafeSQLError("无法解析 SQL")

    keyword = first_token.normalized.upper()
    if keyword not in {"SELECT", "WITH"}:
        raise UnsafeSQLError(f"只允许 SELECT/WITH 查询，检测到: {keyword}")

    upper_sql = cleaned.upper()
    for kw in DANGEROUS_KEYWORDS:
        if re.search(rf"\b{kw}\b", upper_sql):
            raise UnsafeSQLError(f"检测到危险关键字: {kw}")

    return cleaned


def ensure_limit(sql: str, max_rows: int) -> str:
    """如果 SQL 没有 LIMIT，自动追加，避免一次拉回太多数据。"""
    upper = sql.upper()
    if " LIMIT " in upper:
        return sql
    return f"{sql} LIMIT {max_rows}"
