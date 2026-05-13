"""根据查询结果智能推荐图表类型。

策略（启发式，简单可靠）:
- 0 行    -> 空
- 1 行 1 列且值为数字 -> KPI 卡片；否则（如闲聊返回的长文本字面量）-> 表格，避免大字号展示整段话
- 1 列   -> 表格
- 2 列 (类别 + 数值) -> 行数 <= 8 走 pie/donut；否则 bar
- 时间维度 + 数值     -> line
- 多列                -> table
"""
from __future__ import annotations

import re
from typing import Any

DATE_HEADER_PATTERN = re.compile(r"(date|time|day|month|year|created|registered|周|月|年|日|时)", re.IGNORECASE)


def _is_number(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    return isinstance(value, (int, float))


def _column_is_numeric(rows: list[list[Any]], idx: int) -> bool:
    for row in rows:
        if row[idx] is None:
            continue
        if not _is_number(row[idx]):
            return False
    return True


def _column_is_date_like(name: str, rows: list[list[Any]], idx: int) -> bool:
    if DATE_HEADER_PATTERN.search(name or ""):
        return True
    sample = next((row[idx] for row in rows if row[idx] is not None), None)
    if isinstance(sample, str) and re.match(r"^\d{4}[-/]\d{1,2}", sample):
        return True
    return False


def recommend_chart(columns: list[str], rows: list[list[Any]]) -> dict[str, Any]:
    if not rows:
        return {"type": "empty"}

    n_cols = len(columns)
    n_rows = len(rows)

    if n_rows == 1 and n_cols == 1:
        cell = rows[0][0]
        if _is_number(cell):
            return {"type": "kpi", "label": columns[0], "value": cell}
        return {"type": "table"}

    if n_cols == 1:
        return {"type": "table"}

    if n_cols == 2:
        cat_idx, val_idx = 0, 1
        if _column_is_numeric(rows, 0) and not _column_is_numeric(rows, 1):
            cat_idx, val_idx = 1, 0
        if not _column_is_numeric(rows, val_idx):
            return {"type": "table"}

        x_name = columns[cat_idx]
        y_name = columns[val_idx]
        x_data = [row[cat_idx] for row in rows]
        y_data = [row[val_idx] for row in rows]

        if _column_is_date_like(x_name, rows, cat_idx):
            return {
                "type": "line",
                "x": x_data,
                "series": [{"name": y_name, "data": y_data}],
                "x_label": x_name,
                "y_label": y_name,
            }

        if n_rows <= 8:
            return {
                "type": "pie",
                "data": [{"name": str(x), "value": y} for x, y in zip(x_data, y_data)],
                "label": y_name,
            }

        return {
            "type": "bar",
            "x": [str(x) for x in x_data],
            "series": [{"name": y_name, "data": y_data}],
            "x_label": x_name,
            "y_label": y_name,
        }

    if n_cols >= 3:
        numeric_indices = [i for i in range(n_cols) if _column_is_numeric(rows, i)]
        non_numeric_indices = [i for i in range(n_cols) if i not in numeric_indices]
        if len(non_numeric_indices) == 1 and len(numeric_indices) >= 2:
            cat_idx = non_numeric_indices[0]
            x_data = [str(row[cat_idx]) for row in rows]
            chart_type = "line" if _column_is_date_like(columns[cat_idx], rows, cat_idx) else "bar"
            return {
                "type": chart_type,
                "x": x_data,
                "series": [
                    {"name": columns[i], "data": [row[i] for row in rows]}
                    for i in numeric_indices
                ],
                "x_label": columns[cat_idx],
            }

    return {"type": "table"}
