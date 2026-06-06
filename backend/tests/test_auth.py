"""认证与会话隔离测试。"""
from __future__ import annotations

from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.services.auth import _hash_password
from app.services.nl2sql import NL2SQLError

client = TestClient(app)


def test_register_and_login() -> None:
    import time

    username = f"alice_{int(time.time() * 1000)}"
    r = client.post("/api/auth/register", json={"username": username, "password": "secret12"})
    assert r.status_code == 200
    r = client.post("/api/auth/login", json={"username": username, "password": "secret12"})
    assert r.status_code == 200
    body = r.json()
    assert body["access_token"]
    assert body["user"]["username"] == username


def test_me_requires_token() -> None:
    r = client.get("/api/auth/me")
    assert r.status_code == 401


@patch("app.api.chat.log_audit")
@patch("app.api.chat.get_nl2sql_service")
def test_conversation_isolation(mock_get_service, _mock_audit) -> None:
    import time

    suffix = str(int(time.time() * 1000))
    mock_get_service.return_value.ask.side_effect = NL2SQLError("测试错误")

    for name in (f"user_a_{suffix}", f"user_b_{suffix}"):
        r = client.post("/api/auth/register", json={"username": name, "password": "password12"})
        assert r.status_code == 200

    login_a = client.post(
        "/api/auth/login",
        json={"username": f"user_a_{suffix}", "password": "password12"},
    ).json()
    login_b = client.post(
        "/api/auth/login",
        json={"username": f"user_b_{suffix}", "password": "password12"},
    ).json()
    token_a = login_a["access_token"]
    token_b = login_b["access_token"]

    r_a = client.post(
        "/api/chat",
        json={"question": "A 的问题"},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    r_b = client.post(
        "/api/chat",
        json={"question": "B 的问题"},
        headers={"Authorization": f"Bearer {token_b}"},
    )
    id_a = r_a.json()["conversation_id"]
    id_b = r_b.json()["conversation_id"]

    r = client.get(f"/api/conversations/{id_b}", headers={"Authorization": f"Bearer {token_a}"})
    assert r.status_code == 403

    r = client.get(f"/api/conversations/{id_a}", headers={"Authorization": f"Bearer {token_b}"})
    assert r.status_code == 403

    r = client.get(f"/api/conversations/{id_a}", headers={"Authorization": f"Bearer {token_a}"})
    assert r.status_code == 200


def test_bcrypt_password_hash() -> None:
    hashed = _hash_password("testpass")
    assert hashed.startswith("$2")
