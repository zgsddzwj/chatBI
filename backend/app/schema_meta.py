"""业务数据库的元信息（schema 描述）。

⚠️ 已废弃：旧版 users/products/orders 表结构。
新版数仓表结构见 app.seed_dw 和 app.api.meta.get_schema。
保留此文件仅兼容旧引用，内容已更新为新版 5 张表。
"""
from __future__ import annotations

from typing import Any

BUSINESS_SCHEMA: dict[str, Any] = {
    "dialect": "sqlite",
    "tables": [
        {
            "name": "dim_region",
            "comment": "地区维度表",
            "columns": [
                {"name": "region_id", "type": "TEXT", "comment": "地区ID（主键）"},
                {"name": "province", "type": "TEXT", "comment": "省份"},
                {"name": "region_name", "type": "TEXT", "comment": "大区名称（华东、华南等）"},
                {"name": "country", "type": "TEXT", "comment": "国家"},
            ],
        },
        {
            "name": "dim_customer",
            "comment": "客户维度表",
            "columns": [
                {"name": "customer_id", "type": "TEXT", "comment": "客户ID（主键）"},
                {"name": "customer_name", "type": "TEXT", "comment": "客户姓名"},
                {"name": "gender", "type": "TEXT", "comment": "性别"},
                {"name": "member_level", "type": "TEXT", "comment": "会员等级"},
            ],
        },
        {
            "name": "dim_product",
            "comment": "商品维度表",
            "columns": [
                {"name": "product_id", "type": "TEXT", "comment": "商品ID（主键）"},
                {"name": "product_name", "type": "TEXT", "comment": "商品名称"},
                {"name": "category", "type": "TEXT", "comment": "商品品类"},
                {"name": "brand", "type": "TEXT", "comment": "品牌"},
            ],
        },
        {
            "name": "dim_date",
            "comment": "时间维度表",
            "columns": [
                {"name": "date_id", "type": "TEXT", "comment": "日期ID（主键，格式yyyyMMdd）"},
                {"name": "year", "type": "INTEGER", "comment": "年份"},
                {"name": "quarter", "type": "TEXT", "comment": "季度"},
                {"name": "month", "type": "INTEGER", "comment": "月份"},
                {"name": "day", "type": "INTEGER", "comment": "日"},
            ],
        },
        {
            "name": "fact_order",
            "comment": "订单事实表",
            "columns": [
                {"name": "order_id", "type": "TEXT", "comment": "订单ID（主键）"},
                {"name": "customer_id", "type": "TEXT", "comment": "客户ID，关联 dim_customer"},
                {"name": "product_id", "type": "TEXT", "comment": "商品ID，关联 dim_product"},
                {"name": "date_id", "type": "TEXT", "comment": "日期ID，关联 dim_date"},
                {"name": "region_id", "type": "TEXT", "comment": "地区ID，关联 dim_region"},
                {"name": "order_quantity", "type": "INTEGER", "comment": "购买数量"},
                {"name": "order_amount", "type": "REAL", "comment": "订单金额"},
            ],
        },
    ],
    "relations": [
        "fact_order.customer_id -> dim_customer.customer_id",
        "fact_order.product_id -> dim_product.product_id",
        "fact_order.date_id -> dim_date.date_id",
        "fact_order.region_id -> dim_region.region_id",
    ],
    "hints": [
        "时间范围筛选请使用 dim_date.date_id（格式 yyyyMMdd）或 dim_date.year/month",
        "金额相关分析请使用 fact_order.order_amount",
        "数量相关分析请使用 fact_order.order_quantity",
        "地区分析请使用 dim_region.region_name 或 dim_region.province",
        "客户分析请使用 dim_customer.member_level 或 dim_customer.gender",
        "商品分析请使用 dim_product.category 或 dim_product.brand",
    ],
}


def render_schema_prompt() -> str:
    """把 schema 渲染成喂给 LLM 的文本。（已适配新版数仓表）"""
    lines: list[str] = []
    lines.append(f"数据库方言: {BUSINESS_SCHEMA['dialect']}")
    lines.append("")
    lines.append("表结构:")
    for table in BUSINESS_SCHEMA["tables"]:
        lines.append(f"\n-- {table['comment']}")
        lines.append(f"TABLE {table['name']} (")
        col_lines = []
        for col in table["columns"]:
            col_lines.append(f"  {col['name']} {col['type']}  -- {col['comment']}")
        lines.append(",\n".join(col_lines))
        lines.append(")")
    lines.append("")
    lines.append("表关系:")
    for rel in BUSINESS_SCHEMA["relations"]:
        lines.append(f"  - {rel}")
    lines.append("")
    lines.append("业务提示:")
    for hint in BUSINESS_SCHEMA["hints"]:
        lines.append(f"  - {hint}")
    return "\n".join(lines)
