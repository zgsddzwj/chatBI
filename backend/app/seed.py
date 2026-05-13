"""生成 mock 业务数据。

运行: python -m app.seed
幂等：如果数据已存在则跳过。
"""
from __future__ import annotations

import os
import random
from datetime import date, datetime, timedelta
from pathlib import Path

from sqlalchemy import text

from app.database import business_engine, app_engine, AppBase

random.seed(42)


REGIONS = ["华东", "华北", "华南", "西南", "西北", "华中", "东北"]
CATEGORIES_PRODUCTS = {
    "手机": [("iPhone 15", 6999, 4500), ("华为 Mate60", 6499, 4200), ("小米 14", 3999, 2600), ("OPPO Find X7", 4999, 3200)],
    "电脑": [("MacBook Pro 14", 14999, 9800), ("ThinkPad X1", 12999, 8500), ("小米笔记本 Pro", 6499, 4300), ("华为 MateBook", 7999, 5200)],
    "家电": [("戴森吸尘器", 3999, 1800), ("美的空调", 3299, 2100), ("海尔冰箱", 4599, 2900), ("小米电视 65", 3499, 2200)],
    "服饰": [("优衣库羽绒服", 599, 220), ("Nike 跑鞋", 899, 350), ("Adidas 卫衣", 499, 180), ("ZARA 大衣", 1299, 500)],
    "食品": [("三只松鼠坚果礼盒", 199, 80), ("良品铺子零食大礼包", 159, 65), ("茅台 500ml", 2899, 1200), ("褚橙 5kg", 99, 40)],
    "图书": [("Python 编程从入门到实践", 89, 30), ("深度学习", 168, 60), ("三体全集", 158, 55), ("人类简史", 68, 25)],
}
ORDER_STATUS = ["paid", "shipped", "completed", "completed", "completed", "refunded"]
CHANNELS = ["web", "app", "app", "app", "mini_program"]

FIRST_NAMES = ["张", "王", "李", "赵", "陈", "刘", "杨", "黄", "周", "吴", "徐", "孙", "马", "朱", "胡", "郭", "何", "高", "林", "罗"]
GIVEN_NAMES = ["伟", "芳", "娜", "敏", "静", "强", "磊", "军", "洋", "勇", "艳", "杰", "娟", "涛", "明", "超", "秀英", "霞", "平", "刚"]


def _check_seeded(engine) -> bool:
    with engine.connect() as conn:
        try:
            row = conn.execute(text("SELECT COUNT(*) FROM orders")).scalar()
            return (row or 0) > 0
        except Exception:
            return False


def _ensure_data_dir() -> None:
    Path(os.getcwd(), "data").mkdir(parents=True, exist_ok=True)


def _create_business_schema() -> None:
    ddl = [
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            gender TEXT NOT NULL,
            age INTEGER NOT NULL,
            region TEXT NOT NULL,
            registered_at DATE NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            price REAL NOT NULL,
            cost REAL NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            amount REAL NOT NULL,
            status TEXT NOT NULL,
            channel TEXT NOT NULL,
            created_at DATETIME NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (product_id) REFERENCES products(id)
        )
        """,
        "CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders(created_at)",
        "CREATE INDEX IF NOT EXISTS idx_orders_user_id ON orders(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_orders_product_id ON orders(product_id)",
    ]
    with business_engine.begin() as conn:
        for stmt in ddl:
            conn.execute(text(stmt))


def _seed_business_data() -> None:
    users: list[dict] = []
    for i in range(1, 201):
        users.append({
            "id": i,
            "name": random.choice(FIRST_NAMES) + random.choice(GIVEN_NAMES),
            "gender": random.choice(["male", "female"]),
            "age": random.randint(18, 60),
            "region": random.choice(REGIONS),
            "registered_at": (date(2023, 1, 1) + timedelta(days=random.randint(0, 600))).isoformat(),
        })

    products: list[dict] = []
    pid = 1
    for category, items in CATEGORIES_PRODUCTS.items():
        for name, price, cost in items:
            products.append({
                "id": pid,
                "name": name,
                "category": category,
                "price": float(price),
                "cost": float(cost),
            })
            pid += 1

    orders: list[dict] = []
    start = datetime(2024, 1, 1)
    end = datetime(2025, 12, 31)
    total_seconds = int((end - start).total_seconds())
    for oid in range(1, 3001):
        user = random.choice(users)
        product = random.choice(products)
        qty = random.choices([1, 2, 3, 4, 5], weights=[60, 20, 10, 6, 4])[0]
        created = start + timedelta(seconds=random.randint(0, total_seconds))
        orders.append({
            "id": oid,
            "user_id": user["id"],
            "product_id": product["id"],
            "quantity": qty,
            "amount": round(product["price"] * qty, 2),
            "status": random.choice(ORDER_STATUS),
            "channel": random.choice(CHANNELS),
            "created_at": created.isoformat(sep=" "),
        })

    with business_engine.begin() as conn:
        conn.execute(
            text("""INSERT INTO users (id, name, gender, age, region, registered_at)
                    VALUES (:id, :name, :gender, :age, :region, :registered_at)"""),
            users,
        )
        conn.execute(
            text("""INSERT INTO products (id, name, category, price, cost)
                    VALUES (:id, :name, :category, :price, :cost)"""),
            products,
        )
        conn.execute(
            text("""INSERT INTO orders (id, user_id, product_id, quantity, amount, status, channel, created_at)
                    VALUES (:id, :user_id, :product_id, :quantity, :amount, :status, :channel, :created_at)"""),
            orders,
        )

    print(f"[seed] 已写入 {len(users)} 个用户, {len(products)} 个商品, {len(orders)} 条订单")


def _create_app_schema() -> None:
    from app import models  # noqa: F401  确保 model 被注册到 metadata
    AppBase.metadata.create_all(bind=app_engine)


def main() -> None:
    _ensure_data_dir()
    _create_business_schema()
    _create_app_schema()

    if _check_seeded(business_engine):
        print("[seed] 业务库已存在数据，跳过填充。")
        return

    _seed_business_data()
    print("[seed] 完成。")


if __name__ == "__main__":
    main()
