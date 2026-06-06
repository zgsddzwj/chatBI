from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine, Engine, event
from sqlalchemy.orm import sessionmaker, Session, declarative_base
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
    pool_kwargs: dict = {"pool_pre_ping": True}
    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
        connect_args["timeout"] = 30
        if url in {"sqlite://", "sqlite:///:memory:"}:
            pool_kwargs["poolclass"] = StaticPool
        if readonly:
            engine_url = _make_readonly_sqlite_url(url)
    elif readonly and url.startswith("postgresql"):
        connect_args["options"] = "-c default_transaction_read_only=on"

    engine = create_engine(engine_url, connect_args=connect_args, **pool_kwargs)

    if url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def _set_sqlite_pragmas(dbapi_conn, _connection_record) -> None:
            dbapi_conn.execute("PRAGMA journal_mode=WAL")
            if readonly:
                dbapi_conn.execute("PRAGMA query_only = ON")

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
    session = BusinessSessionLocal()
    try:
        yield session
    finally:
        session.close()


def get_app_db() -> Iterator[Session]:
    session = AppSessionLocal()
    try:
        yield session
    finally:
        session.close()
