"""MySQL 客户端管理器。

本项目使用 SQLAlchemy 管理数据库读写。
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from app.conf.app_config import DBConfig, app_config


class MysqlClientManager:
    def __init__(self, db_config: DBConfig):
        self.db_config = db_config
        self.engine: Optional[AsyncEngine] = None
        self.session_factory = None

    def _get_url(self):
        return f"mysql+asyncmy://{self.db_config.user}:{self.db_config.password}@{self.db_config.host}:{self.db_config.port}/{self.db_config.database}?charset=utf8mb4"

    def init(self):
        self.engine = create_async_engine(
            url=self._get_url(),
            pool_size=10,
            pool_pre_ping=True,
        )
        self.session_factory = async_sessionmaker(
            self.engine,
            autoflush=True,
            expire_on_commit=False,
            autobegin=True,
        )

    async def close(self):
        if self.engine:
            await self.engine.dispose()


dw_mysql_client_manager = MysqlClientManager(app_config.db_dw)
meta_mysql_client_manager = MysqlClientManager(app_config.db_meta)
