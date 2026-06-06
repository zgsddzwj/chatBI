"""轻量级数据库迁移（SQLite 兼容）。"""
from __future__ import annotations

import logging

from sqlalchemy import inspect, text

from app.database import app_engine

logger = logging.getLogger(__name__)


def run_migrations() -> None:
    """执行增量 schema 变更。"""
    inspector = inspect(app_engine)
    if "conversations" not in inspector.get_table_names():
        return

    columns = {col["name"] for col in inspector.get_columns("conversations")}
    if "user_id" not in columns:
        with app_engine.begin() as conn:
            conn.execute(text("ALTER TABLE conversations ADD COLUMN user_id INTEGER"))
        logger.info("已添加 conversations.user_id 列")
