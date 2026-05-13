"""HTTP 层与中间件集成测试。"""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_ok() -> None:
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body.get("status") == "ok"
    assert body.get("service") == "chatbi-backend"


def test_ready_checks_app_database() -> None:
    r = client.get("/ready")
    assert r.status_code in (200, 503)
    data = r.json()
    assert "status" in data


def test_request_id_roundtrip() -> None:
    r = client.get("/health", headers={"X-Request-ID": "trace-abc-001"})
    assert r.status_code == 200
    assert r.headers.get("X-Request-ID") == "trace-abc-001"


def test_request_id_generated_when_missing() -> None:
    r = client.get("/health")
    assert r.status_code == 200
    assert r.headers.get("X-Request-ID")


def test_security_headers_present() -> None:
    r = client.get("/health")
    assert r.headers.get("X-Content-Type-Options") == "nosniff"
    assert r.headers.get("X-Frame-Options") == "DENY"


def test_chat_validation_error_status() -> None:
    r = client.post("/api/chat", json={})
    assert r.status_code == 422
