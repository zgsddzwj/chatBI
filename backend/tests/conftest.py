"""Pytest 公共配置。"""
from __future__ import annotations

import pytest

from app.config import get_settings


@pytest.fixture(autouse=True)
def _clear_settings_cache() -> None:
    """避免测试间污染单例配置。"""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
