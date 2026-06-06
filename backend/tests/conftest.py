"""Pytest 公共配置。"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

TEST_DATA = Path(__file__).resolve().parent / "_test_data"
TEST_DATA.mkdir(exist_ok=True)

os.environ["APP_ENV"] = "local"
os.environ["JWT_SECRET"] = "test-jwt-secret-for-ci"
os.environ["ALLOW_PUBLIC_REGISTER"] = "true"
os.environ["APP_DB_URL"] = f"sqlite:///{TEST_DATA / 'app.db'}"
os.environ["BUSINESS_DB_URL"] = f"sqlite:///{TEST_DATA / 'business.db'}"

from app.config import get_settings  # noqa: E402
from app.database import AppBase, app_engine  # noqa: E402
from app.migrations import run_migrations  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _init_test_database() -> None:
    """确保测试库 schema 包含最新列。"""
    from app import models  # noqa: F401

    AppBase.metadata.create_all(bind=app_engine)
    run_migrations()


@pytest.fixture(autouse=True)
def _clear_settings_cache() -> None:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
