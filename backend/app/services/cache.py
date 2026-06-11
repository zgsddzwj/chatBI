"""SQL 查询结果缓存。

已迁移到 cache_v2.py，保留此文件向后兼容。
"""
from __future__ import annotations

from app.services.cache_v2 import clear_expired, get_cached, set_cache

__all__ = ["get_cached", "set_cache", "clear_expired"]
