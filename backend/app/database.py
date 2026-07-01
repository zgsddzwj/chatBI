"""数据库引擎与会话管理。

优化点：
1. SQLite：WAL 模式 + 增大 cache_size + mmap_size，提升读性能
2. PostgreSQL/MySQL：连接池大小可配置，自动回收闲置连接
3. 会话生命周期：异常时自动回滚，避免脏事务
4. 连接探活：pool_pre_ping 避免使用已断开的连接
"""
from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, declarative_base, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import get_settings

settings = get_settings()


def _make_readonly_sqlite_url(url: str) -> str:
    if "mode=ro" in url or "immutable=1" in url:
        return url
    separator = "&" if "?" in url else "?"
    return f"{url}{separator}mode=ro"


def _build_engine(url: str, *, readonly: bool = False) -> Engine:
    connect_args: dict = {}
    engine_url = url
    pool_kwargs: dict = {
        "pool_pre_ping": True,  # 连接前探活，避免使用已断开连接
    }

    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
        connect_args["timeout"] = 30  # SQLite 锁等待超时（秒）
        if url in {"sqlite://", "sqlite:///:memory:"}:
            pool_kwargs["poolclass"] = StaticPool
        else:
            # 文件型 SQLite 使用 StaticPool 避免多连接锁竞争
            pool_kwargs["poolclass"] = StaticPool
        if readonly:
            engine_url = _make_readonly_sqlite_url(url)
    elif readonly and url.startswith("postgresql"):
        connect_args["options"] = "-c default_transaction_read_only=on"
        # PostgreSQL/MySQL 连接池配置
        pool_kwargs["pool_size"] = 10
        pool_kwargs["max_overflow"] = 20
        pool_kwargs["pool_recycle"] = 3600  # 1小时回收连接
        pool_kwargs["pool_timeout"] = 30  # 获取连接超时
    elif url.startswith(("postgresql", "mysql")):
        pool_kwargs["pool_size"] = 10
        pool_kwargs["max_overflow"] = 20
        pool_kwargs["pool_recycle"] = 3600
        pool_kwargs["pool_timeout"] = 30

    engine = create_engine(engine_url, connect_args=connect_args, **pool_kwargs)

    if url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def _set_sqlite_pragmas(dbapi_conn, _connection_record) -> None:
            cursor = dbapi_conn.cursor()
            # WAL 模式：并发读不阻塞
            cursor.execute("PRAGMA journal_mode=WAL")
            # 增大缓存（单位 KB，-20000 ≈ 20MB）
            cursor.execute("PRAGMA cache_size=-20000")
            # 内存映射 IO，减少系统调用
            cursor.execute("PRAGMA mmap_size=268435456")  # 256MB
            # NORMAL 比 FULL 快，WAL 模式下足够安全
            cursor.execute("PRAGMA synchronous=NORMAL")
            # 临时表存内存
            cursor.execute("PRAGMA temp_store=MEMORY")
            if readonly:
                cursor.execute("PRAGMA query_only = ON")
            cursor.close()

    return engine


business_engine: Engine = _build_engine(
    settings.business_db_url,
    readonly=settings.business_db_readonly,
)
app_engine: Engine = _build_engine(settings.app_db_url)

BusinessSessionLocal = sessionmaker(bind=business_engine, autoflush=False, autocommit=False)
AppSessionLocal = sessionmaker(bind=app_engine, autoflush=False, autocommit=False)

AppBase = declarative_base()


@contextmanager
def business_session() -> Iterator[Session]:
    """业务数据库会话上下文管理器。

    自动回滚异常事务，确保连接归还连接池。
    """
    session = BusinessSessionLocal()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_app_db() -> Iterator[Session]:
    """应用数据库会话（FastAPI 依赖注入）。

    自动回滚异常事务，确保连接归还连接池。
    """
    session = AppSessionLocal()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
