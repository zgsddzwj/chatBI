"""数据库客户端管理器。

统一管理业务数据库和应用数据库的连接池。
"""
from __future__ import annotations

from sqlalchemy import Engine

from app.database import business_engine, app_engine


class DBClientManager:
    """数据库连接管理器。"""

    def __init__(self) -> None:
        self._business_engine: Engine | None = None
        self._app_engine: Engine | None = None

    def init(self) -> None:
        """初始化数据库连接。"""
        self._business_engine = business_engine
        self._app_engine = app_engine

    @property
    def business_engine(self) -> Engine:
        if self._business_engine is None:
            self.init()
        return self._business_engine

    @property
    def app_engine(self) -> Engine:
        if self._app_engine is None:
            self.init()
        return self._app_engine

    def close(self) -> None:
        """关闭数据库连接。"""
        if self._business_engine:
            self._business_engine.dispose()
            self._business_engine = None
        if self._app_engine:
            self._app_engine.dispose()
            self._app_engine = None


# 全局实例
db_client_manager = DBClientManager()
