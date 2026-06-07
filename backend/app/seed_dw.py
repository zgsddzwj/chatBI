"""生成数据仓库（DW）mock 业务数据。

按文档要求创建 5 张表：
- dim_region   地区维度表
- dim_customer 客户维度表
- dim_product  商品维度表
- dim_date     时间维度表
- fact_order   订单事实表

运行: python -m app.seed_dw
幂等：如果数据已存在则跳过。
"""
from __future__ import annotations

import os
import random
from datetime import date, datetime, timedelta
from pathlib import Path

from sqlalchemy import text

from app.database import business_engine

random.seed(42)

# ---------- 维度数据定义 ----------
REGIONS = [
    ("R01", "北京", "华北", "中国"),
    ("R02", "上海", "华东", "中国"),
    ("R03", "广东", "华南", "中国"),
    ("R04", "四川", "西南", "中国"),
    ("R05", "陕西", "西北", "中国"),
    ("R06", "湖北", "华中", "中国"),
    ("R07", "辽宁", "东北", "中国"),
]

GENDERS = ["男", "女"]
MEMBER_LEVELS = ["普通会员", "银卡会员", "金卡会员", "钻石会员"]

CATEGORIES_PRODUCTS = [
    ("手机", [
        ("P001", "iPhone 15", "Apple"),
        ("P002", "华为 Mate60", "华为"),
        ("P003", "小米 14", "小米"),
        ("P004", "OPPO Find X7", "OPPO"),
    ]),
    ("电脑", [
        ("P005", "MacBook Pro 14", "Apple"),
        ("P006", "ThinkPad X1", "联想"),
        ("P007", "小米笔记本 Pro", "小米"),
        ("P008", "华为 MateBook", "华为"),
    ]),
    ("家电", [
        ("P009", "戴森吸尘器", "戴森"),
        ("P010", "美的空调", "美的"),
        ("P011", "海尔冰箱", "海尔"),
        ("P012", "小米电视 65", "小米"),
    ]),
    ("服饰", [
        ("P013", "优衣库羽绒服", "优衣库"),
        ("P014", "Nike 跑鞋", "Nike"),
        ("P015", "Adidas 卫衣", "Adidas"),
        ("P016", "ZARA 大衣", "ZARA"),
    ]),
]

FIRST_NAMES = ["张", "王", "李", "赵", "陈", "刘", "杨", "黄", "周", "吴", "徐", "孙", "马", "朱", "胡", "郭", "何", "高", "林", "罗"]
GIVEN_NAMES = ["伟", "芳", "娜", "敏", "静", "强", "磊", "军", "洋", "勇", "艳", "杰", "娟", "涛", "明", "超", "秀英", "霞", "平", "刚"]


def _check_seeded() -> bool:
    with business_engine.connect() as conn:
        try:
            row = conn.execute(text("SELECT COUNT(*) FROM fact_order")).scalar()
            return (row or 0) > 0
        except Exception:
            return False


def _ensure_data_dir() -> None:
    Path(os.getcwd(), "data").mkdir(parents=True, exist_ok=True)


def _create_dw_schema() -> None:
    ddl = [
        """
        CREATE TABLE IF NOT EXISTS dim_region (
            region_id TEXT PRIMARY KEY,
            province TEXT NOT NULL,
            region_name TEXT NOT NULL,
            country TEXT NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS dim_customer (
            customer_id TEXT PRIMARY KEY,
            customer_name TEXT NOT NULL,
            gender TEXT NOT NULL,
            member_level TEXT NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS dim_product (
            product_id TEXT PRIMARY KEY,
            product_name TEXT NOT NULL,
            category TEXT NOT NULL,
            brand TEXT NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS dim_date (
            date_id TEXT PRIMARY KEY,
            year INTEGER NOT NULL,
            quarter TEXT NOT NULL,
            month INTEGER NOT NULL,
            day INTEGER NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS fact_order (
            order_id TEXT PRIMARY KEY,
            customer_id TEXT NOT NULL,
            product_id TEXT NOT NULL,
            date_id TEXT NOT NULL,
            region_id TEXT NOT NULL,
            order_quantity INTEGER NOT NULL,
            order_amount REAL NOT NULL
        )
        """,
        "CREATE INDEX IF NOT EXISTS idx_fact_order_customer ON fact_order(customer_id)",
        "CREATE INDEX IF NOT EXISTS idx_fact_order_product ON fact_order(product_id)",
        "CREATE INDEX IF NOT EXISTS idx_fact_order_date ON fact_order(date_id)",
        "CREATE INDEX IF NOT EXISTS idx_fact_order_region ON fact_order(region_id)",
    ]
    with business_engine.begin() as conn:
        for stmt in ddl:
            conn.execute(text(stmt))


def _seed_dim_region() -> None:
    rows = [
        {"region_id": rid, "province": prov, "region_name": rname, "country": country}
        for rid, prov, rname, country in REGIONS
    ]
    with business_engine.begin() as conn:
        conn.execute(
            text("INSERT INTO dim_region (region_id, province, region_name, country) VALUES (:region_id, :province, :region_name, :country)"),
            rows,
        )
    print(f"[seed_dw] dim_region: {len(rows)} 条")


def _seed_dim_customer() -> int:
    rows = []
    for i in range(1, 201):
        rows.append({
            "customer_id": f"C{i:05d}",
            "customer_name": random.choice(FIRST_NAMES) + random.choice(GIVEN_NAMES),
            "gender": random.choice(GENDERS),
            "member_level": random.choice(MEMBER_LEVELS),
        })
    with business_engine.begin() as conn:
        conn.execute(
            text("INSERT INTO dim_customer (customer_id, customer_name, gender, member_level) VALUES (:customer_id, :customer_name, :gender, :member_level)"),
            rows,
        )
    print(f"[seed_dw] dim_customer: {len(rows)} 条")
    return len(rows)


def _seed_dim_product() -> int:
    rows = []
    for category, products in CATEGORIES_PRODUCTS:
        for pid, pname, brand in products:
            rows.append({
                "product_id": pid,
                "product_name": pname,
                "category": category,
                "brand": brand,
            })
    with business_engine.begin() as conn:
        conn.execute(
            text("INSERT INTO dim_product (product_id, product_name, category, brand) VALUES (:product_id, :product_name, :category, :brand)"),
            rows,
        )
    print(f"[seed_dw] dim_product: {len(rows)} 条")
    return len(rows)


def _seed_dim_date() -> int:
    rows = []
    start = date(2023, 1, 1)
    end = date(2025, 12, 31)
    cur = start
    while cur <= end:
        rows.append({
            "date_id": cur.strftime("%Y%m%d"),
            "year": cur.year,
            "quarter": f"Q{(cur.month - 1) // 3 + 1}",
            "month": cur.month,
            "day": cur.day,
        })
        cur += timedelta(days=1)
    with business_engine.begin() as conn:
        conn.execute(
            text("INSERT INTO dim_date (date_id, year, quarter, month, day) VALUES (:date_id, :year, :quarter, :month, :day)"),
            rows,
        )
    print(f"[seed_dw] dim_date: {len(rows)} 条")
    return len(rows)


def _seed_fact_order(customer_ids: list[str], product_ids: list[str], date_ids: list[str]) -> int:
    rows = []
    region_ids = [r[0] for r in REGIONS]
    for i in range(1, 5001):
        qty = random.choices([1, 2, 3, 4, 5], weights=[60, 20, 10, 6, 4])[0]
        unit_price = round(random.uniform(50, 15000), 2)
        rows.append({
            "order_id": f"O{i:08d}",
            "customer_id": random.choice(customer_ids),
            "product_id": random.choice(product_ids),
            "date_id": random.choice(date_ids),
            "region_id": random.choice(region_ids),
            "order_quantity": qty,
            "order_amount": round(unit_price * qty, 2),
        })
    with business_engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO fact_order (order_id, customer_id, product_id, date_id, region_id, order_quantity, order_amount) "
                "VALUES (:order_id, :customer_id, :product_id, :date_id, :region_id, :order_quantity, :order_amount)"
            ),
            rows,
        )
    print(f"[seed_dw] fact_order: {len(rows)} 条")
    return len(rows)


def main() -> None:
    _ensure_data_dir()
    _create_dw_schema()

    if _check_seeded():
        print("[seed_dw] 数据仓库已存在数据，跳过填充。")
        return

    _seed_dim_region()
    customer_count = _seed_dim_customer()
    product_count = _seed_dim_product()
    _seed_dim_date()

    # 获取ID列表用于生成订单
    with business_engine.connect() as conn:
        cids = [r[0] for r in conn.execute(text("SELECT customer_id FROM dim_customer")).fetchall()]
        pids = [r[0] for r in conn.execute(text("SELECT product_id FROM dim_product")).fetchall()]
        dids = [r[0] for r in conn.execute(text("SELECT date_id FROM dim_date WHERE year IN (2024, 2025)")).fetchall()]

    _seed_fact_order(cids, pids, dids)
    print("[seed_dw] 完成。")


if __name__ == "__main__":
    main()
