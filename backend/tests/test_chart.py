"""图表推荐逻辑单元测试。"""
from __future__ import annotations

from app.services.chart import recommend_chart


def test_empty_rows() -> None:
    assert recommend_chart(["a"], []) == {"type": "empty"}


def test_kpi_numeric_1x1() -> None:
    spec = recommend_chart(["total"], [[128800.5]])
    assert spec["type"] == "kpi"
    assert spec["label"] == "total"
    assert spec["value"] == 128800.5


def test_string_1x1_is_table_not_kpi() -> None:
    """闲聊类字面量查询不应走 KPI 大字展示路径。"""
    spec = recommend_chart(["message"], [["这是一段较长的说明文字，而不是指标。"]])
    assert spec["type"] == "table"


def test_single_column_many_rows_table() -> None:
    spec = recommend_chart(["x"], [[1], [2], [3]])
    assert spec["type"] == "table"


def test_two_columns_small_pie_or_bar() -> None:
    spec = recommend_chart(
        ["region", "cnt"],
        [["华东", 10], ["华北", 20]],
    )
    assert spec["type"] in ("pie", "bar", "line")
