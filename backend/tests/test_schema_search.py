"""Schema 智能检索单元测试（已适配新版数仓表 dim_* / fact_*）。"""
from __future__ import annotations

from app.services.schema_search import render_schema_prompt_filtered, search_relevant_tables


def test_search_users_question() -> None:
    tables = search_relevant_tables("各地区的用户数量分布如何？", top_k=3)
    names = [t["name"] for t in tables]
    # 新版 schema：用户相关 -> dim_customer / dim_region
    assert "dim_customer" in names or "dim_region" in names


def test_search_orders_question() -> None:
    tables = search_relevant_tables("2024 年每个月的销售额是多少？", top_k=3)
    names = [t["name"] for t in tables]
    # 新版 schema：订单/销售相关 -> fact_order
    assert "fact_order" in names


def test_search_products_question() -> None:
    tables = search_relevant_tables("销售额排名前 5 的商品是哪些？", top_k=3)
    names = [t["name"] for t in tables]
    # 新版 schema：商品相关 -> dim_product
    assert "dim_product" in names


def test_render_filtered_contains_relevant() -> None:
    prompt = render_schema_prompt_filtered("每个商品类别的总营收", top_k=2)
    # 新版 schema：商品/订单 -> dim_product / fact_order
    assert "dim_product" in prompt or "fact_order" in prompt
    assert "方言" in prompt


def test_empty_question_returns_all() -> None:
    tables = search_relevant_tables("", top_k=3)
    assert len(tables) >= 3
