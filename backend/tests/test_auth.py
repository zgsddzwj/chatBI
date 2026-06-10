"""认证与会话隔离测试。"""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.services.auth import _hash_password

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


def test_conversation_isolation() -> None:
    """会话隔离测试：用户只能访问自己的会话。"""
    import time

    suffix = str(int(time.time() * 1000))

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

    # 创建两个会话
    r_a = client.post(
        "/api/conversations",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert r_a.status_code == 200
    id_a = r_a.json()["id"]

    r_b = client.post(
        "/api/conversations",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert r_b.status_code == 200
    id_b = r_b.json()["id"]

    # 用户 A 不能访问用户 B 的会话
    r = client.get(f"/api/conversations/{id_b}", headers={"Authorization": f"Bearer {token_a}"})
    assert r.status_code == 403

    # 用户 B 不能访问用户 A 的会话
    r = client.get(f"/api/conversations/{id_a}", headers={"Authorization": f"Bearer {token_b}"})
    assert r.status_code == 403

    # 用户 A 可以访问自己的会话
    r = client.get(f"/api/conversations/{id_a}", headers={"Authorization": f"Bearer {token_a}"})
    assert r.status_code == 200


def test_bcrypt_password_hash() -> None:
    hashed = _hash_password("testpass")
    assert hashed.startswith("$")
