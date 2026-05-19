"""Schema 智能检索单元测试。"""
from __future__ import annotations

from app.services.schema_search import search_relevant_tables, render_schema_prompt_filtered


def test_search_users_question() -> None:
    tables = search_relevant_tables("各地区的用户数量分布如何？", top_k=3)
    names = [t["name"] for t in tables]
    assert "users" in names


def test_search_orders_question() -> None:
    tables = search_relevant_tables("2024 年每个月的销售额是多少？", top_k=3)
    names = [t["name"] for t in tables]
    assert "orders" in names


def test_search_products_question() -> None:
    tables = search_relevant_tables("销售额排名前 5 的商品是哪些？", top_k=3)
    names = [t["name"] for t in tables]
    assert "products" in names


def test_render_filtered_contains_relevant() -> None:
    prompt = render_schema_prompt_filtered("每个商品类别的总营收", top_k=2)
    assert "products" in prompt or "orders" in prompt
    assert "方言" in prompt


def test_empty_question_returns_all() -> None:
    tables = search_relevant_tables("", top_k=3)
    assert len(tables) >= 3
