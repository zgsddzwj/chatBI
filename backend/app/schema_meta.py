"""业务数据库的元信息（schema 描述）。

这是 NL2SQL 的关键：把表结构、字段含义和示例值喂给 LLM，
让它能准确地把自然语言翻译成 SQL。
真实项目中可以把这部分迁到数据库或向量库管理。
"""

BUSINESS_SCHEMA = {
    "dialect": "sqlite",
    "tables": [
        {
            "name": "users",
            "comment": "用户表",
            "columns": [
                {"name": "id", "type": "INTEGER", "comment": "用户ID（主键）"},
                {"name": "name", "type": "TEXT", "comment": "用户姓名"},
                {"name": "gender", "type": "TEXT", "comment": "性别，枚举：male/female"},
                {"name": "age", "type": "INTEGER", "comment": "年龄"},
                {"name": "region", "type": "TEXT", "comment": "所在地区，例如：华东、华北、华南、西南、西北、华中、东北"},
                {"name": "registered_at", "type": "DATE", "comment": "注册日期"},
            ],
        },
        {
            "name": "products",
            "comment": "商品表",
            "columns": [
                {"name": "id", "type": "INTEGER", "comment": "商品ID（主键）"},
                {"name": "name", "type": "TEXT", "comment": "商品名称"},
                {"name": "category", "type": "TEXT", "comment": "商品分类，例如：手机、电脑、家电、服饰、食品、图书"},
                {"name": "price", "type": "REAL", "comment": "商品单价（元）"},
                {"name": "cost", "type": "REAL", "comment": "商品成本（元）"},
            ],
        },
        {
            "name": "orders",
            "comment": "订单表",
            "columns": [
                {"name": "id", "type": "INTEGER", "comment": "订单ID（主键）"},
                {"name": "user_id", "type": "INTEGER", "comment": "下单用户ID，关联 users.id"},
                {"name": "product_id", "type": "INTEGER", "comment": "商品ID，关联 products.id"},
                {"name": "quantity", "type": "INTEGER", "comment": "购买数量"},
                {"name": "amount", "type": "REAL", "comment": "订单总金额（元）= quantity * price"},
                {"name": "status", "type": "TEXT", "comment": "订单状态，枚举：paid（已支付）/shipped（已发货）/completed（已完成）/refunded（已退款）"},
                {"name": "channel", "type": "TEXT", "comment": "下单渠道，枚举：web/app/mini_program"},
                {"name": "created_at", "type": "DATETIME", "comment": "下单时间"},
            ],
        },
    ],
    "relations": [
        "orders.user_id -> users.id",
        "orders.product_id -> products.id",
    ],
    "hints": [
        "时间范围筛选请使用 created_at（订单）或 registered_at（用户）",
        "金额相关分析（销售额/营收）请使用 orders.amount",
        "利润 = orders.amount - products.cost * orders.quantity",
        "已完成的有效订单状态为 paid、shipped、completed（排除 refunded）",
        "日期函数请使用 SQLite 语法，例如 strftime('%Y-%m', created_at)",
    ],
}


def render_schema_prompt() -> str:
    """把 schema 渲染成喂给 LLM 的文本。"""
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
