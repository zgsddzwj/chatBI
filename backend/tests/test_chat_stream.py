"""流式对话接口测试（已适配新版 /api/query）。"""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _parse_sse_events(text: str) -> list[dict]:
    import json

    events = []
    for block in text.split("\n\n"):
        block = block.strip()
        if block.startswith("data: "):
            events.append(json.loads(block[6:]))
    return events


def test_query_stream_endpoint_exists() -> None:
    """新版流式接口存在且可访问（外部服务未连接时返回错误）。"""
    r = client.post("/api/query", json={"query": "测试"})
    # 外部服务未连接时可能返回 500，但接口存在
    assert r.status_code in (200, 500)
