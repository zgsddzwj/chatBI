"""SQL 安全校验单元测试。"""
from __future__ import annotations

import pytest

from app.services.sql_safety import UnsafeSQLError, ensure_limit, validate_sql


def test_validate_simple_select() -> None:
    out = validate_sql("SELECT 1 AS n")
    assert "SELECT" in out.upper()


def test_validate_strips_trailing_semicolon() -> None:
    out = validate_sql("SELECT 1;")
    assert not out.rstrip().endswith(";")


def test_validate_rejects_empty() -> None:
    with pytest.raises(UnsafeSQLError, match="为空"):
        validate_sql("   ")


def test_validate_rejects_multiple_statements() -> None:
    with pytest.raises(UnsafeSQLError, match="单条"):
        validate_sql("SELECT 1; SELECT 2")


def test_validate_rejects_delete() -> None:
    with pytest.raises(UnsafeSQLError, match="DELETE"):
        validate_sql("DELETE FROM users WHERE 1=1")


def test_validate_rejects_insert() -> None:
    with pytest.raises(UnsafeSQLError):
        validate_sql("INSERT INTO users VALUES (1)")


def test_validate_rejects_non_select() -> None:
    with pytest.raises(UnsafeSQLError, match="SELECT"):
        validate_sql("UPDATE users SET x=1")


def test_ensure_limit_appends() -> None:
    assert "LIMIT 10" in ensure_limit("SELECT 1", 10).upper()


def test_ensure_limit_preserves_existing() -> None:
    sql = "SELECT 1 LIMIT 5"
    assert ensure_limit(sql, 999) == sql


def test_validate_allows_union_select() -> None:
    sql = "SELECT a FROM t1 UNION SELECT b FROM t2"
    out = validate_sql(sql)
    assert "UNION" in out.upper()


def test_validate_rejects_dangerous_in_subquery() -> None:
    with pytest.raises(UnsafeSQLError, match="DELETE"):
        validate_sql("SELECT * FROM (DELETE FROM users) AS x")


def test_validate_strips_comment_injection() -> None:
    out = validate_sql("SELECT 1 /* DROP TABLE users */ AS n")
    assert "DROP" not in out.upper() or "SELECT" in out.upper()


def test_validate_rejects_drop_in_select_list() -> None:
    with pytest.raises(UnsafeSQLError, match="单条"):
        validate_sql("SELECT 1; DROP TABLE users")
