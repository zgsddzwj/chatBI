from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import sessionmaker, Session, declarative_base

from app.config import get_settings

settings = get_settings()


def _build_engine(url: str) -> Engine:
    connect_args = {}
    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    return create_engine(url, connect_args=connect_args, pool_pre_ping=True)


business_engine: Engine = _build_engine(settings.business_db_url)
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
