"""流式对话接口测试。"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

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


@patch("app.api.chat.get_nl2sql_service")
def test_stream_returns_event_sequence(mock_get_service) -> None:
    service = MagicMock()
    mock_get_service.return_value = service
    service.generate_sql.return_value = {
        "needs_clarification": False,
        "sql": "SELECT 1 AS n",
        "explanation": "test",
    }
    service.execute_sql.return_value = {"columns": ["n"], "rows": [[1]], "row_count": 1}
    service.recommend_chart.return_value = {"type": "kpi", "title": "n", "value": 1}
    service.summarize.return_value = "结果为 1。"

    r = client.post("/api/chat/stream", json={"question": "测试问题"})
    assert r.status_code == 200
    events = _parse_sse_events(r.text)
    types = [e["type"] for e in events]
    assert "thinking" in types
    assert "sql" in types
    assert "data" in types
    assert "chart" in types
    assert "done" in types
