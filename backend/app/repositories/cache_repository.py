"""缓存数据访问仓库。

封装对查询缓存的访问。
"""
from __future__ import annotations

from typing import Any

from app.services.cache import get_cached as _get_cached
from app.services.cache import set_cache as _set_cache


class CacheRepository:
    """查询缓存仓库。"""

    def get(self, sql: str) -> dict[str, Any] | None:
        """获取缓存的查询结果。"""
        return _get_cached(sql)

    def set(self, sql: str, result: dict[str, Any], chart: dict[str, Any] | None = None, ttl: int | None = None) -> None:
        """设置缓存。"""
        _set_cache(sql, result, chart, ttl)
