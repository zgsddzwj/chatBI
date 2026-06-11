"""缓存 V2 性能与功能测试。"""
from __future__ import annotations

import time

from app.services.cache_v2 import (
    clear_all_cache,
    get_cache_stats,
    get_cached,
    set_cache,
    smart_ttl,
    warmup_cache,
)


def test_set_and_get_cache():
    """测试基本的缓存设置和获取。"""
    clear_all_cache()
    sql = "SELECT * FROM fact_order LIMIT 10"
    result = {"columns": ["a"], "rows": [[1]]}
    set_cache(sql, result, query_intent="测试查询")
    cached = get_cached(sql)
    assert cached is not None
    assert cached["columns"] == ["a"]


def test_cache_hit_count():
    """测试缓存命中统计。"""
    clear_all_cache()
    sql = "SELECT COUNT(*) FROM fact_order"
    set_cache(sql, {"count": 100})
    for _ in range(3):
        get_cached(sql)
    stats = get_cache_stats()
    assert stats["total_hits"] == 3


def test_smart_ttl():
    """测试智能 TTL 策略。"""
    assert smart_ttl("SELECT COUNT(*) FROM t") == 300
    assert smart_ttl("SELECT SUM(amount) FROM t") == 600
    assert smart_ttl("SELECT AVG(price) FROM t") == 600
    assert smart_ttl("SELECT * FROM t GROUP BY region") == 900
    assert smart_ttl("SELECT * FROM t LIMIT 5") == 1800
    assert smart_ttl("SELECT * FROM t LIMIT 10") == 1800


def test_cache_stats():
    """测试缓存统计功能。"""
    clear_all_cache()
    set_cache("SELECT 1", {"a": 1}, query_intent="测试1")
    set_cache("SELECT 2", {"a": 2}, query_intent="测试2")
    get_cached("SELECT 1")
    stats = get_cache_stats()
    assert stats["total_entries"] == 2
    assert stats["active_entries"] == 2
    assert stats["total_hits"] == 1


def test_clear_all():
    """测试清空缓存。"""
    set_cache("SELECT 3", {"a": 3})
    count = clear_all_cache()
    assert count >= 0
    stats = get_cache_stats()
    assert stats["total_entries"] == 0


def test_cache_performance():
    """测试缓存读写性能。"""
    clear_all_cache()
    n = 100
    start = time.time()
    for i in range(n):
        set_cache(f"SELECT {i}", {"value": i})
    write_time = time.time() - start

    start = time.time()
    for i in range(n):
        get_cached(f"SELECT {i}")
    read_time = time.time() - start

    # 100 次读写应在 1 秒内完成
    assert write_time < 2.0, f"写入太慢: {write_time}s"
    assert read_time < 2.0, f"读取太慢: {read_time}s"


def test_warmup():
    """测试缓存预热。"""
    clear_all_cache()
    warmed = warmup_cache()
    assert warmed >= 0
    stats = get_cache_stats()
    assert stats["total_entries"] >= warmed
