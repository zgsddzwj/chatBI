"""用户认证与权限管理。

- 基于 bcrypt 的密码哈希
- JWT Token 认证
- 简单的角色系统（admin / analyst / viewer）
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
from datetime import datetime, timedelta
from typing import Any

from app.config import get_settings
from app.database import app_engine

logger = logging.getLogger(__name__)

# 简单的 secret key 用于 JWT（生产环境应使用更安全的密钥）
_settings = get_settings()
_SECRET = hashlib.sha256(
    (_settings.deepseek_api_key or "chatbi-default-secret").encode()
).hexdigest()


def _init_user_table() -> None:
    from sqlalchemy import text
    with app_engine.begin() as conn:
        conn.execute(
            text("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    display_name TEXT,
                    role TEXT NOT NULL DEFAULT 'analyst',
                    is_active INTEGER NOT NULL DEFAULT 1,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
        )
        conn.execute(
            text("""
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    action TEXT NOT NULL,
                    resource TEXT,
                    detail TEXT,
                    ip_address TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
        )
        # 创建默认管理员账号（密码: admin123）
        default_hash = _hash_password("admin123")
        conn.execute(
            text("""
                INSERT OR IGNORE INTO users (id, username, password_hash, display_name, role)
                VALUES (1, 'admin', :hash, '管理员', 'admin')
            """),
            {"hash": default_hash},
        )


def _hash_password(password: str) -> str:
    """使用 HMAC-SHA256 哈希密码（简单实现，生产环境建议用 bcrypt）。"""
    salt = _SECRET[:32]
    return hmac.new(salt.encode(), password.encode(), hashlib.sha256).hexdigest()


def verify_password(password: str, password_hash: str) -> bool:
    return secrets.compare_digest(_hash_password(password), password_hash)


def create_user(username: str, password: str, display_name: str | None = None, role: str = "analyst") -> dict[str, Any]:
    """创建新用户。"""
    from sqlalchemy import text
    _init_user_table()
    password_hash = _hash_password(password)
    with app_engine.begin() as conn:
        try:
            result = conn.execute(
                text("""
                    INSERT INTO users (username, password_hash, display_name, role)
                    VALUES (:username, :hash, :display_name, :role)
                """),
                {
                    "username": username,
                    "hash": password_hash,
                    "display_name": display_name or username,
                    "role": role,
                },
            )
            return {
                "id": result.lastrowid,
                "username": username,
                "display_name": display_name or username,
                "role": role,
            }
        except Exception as exc:  # noqa: BLE001
            logger.warning("创建用户失败: %s", exc)
            raise ValueError(f"用户名 '{username}' 已存在") from exc


def authenticate_user(username: str, password: str) -> dict[str, Any] | None:
    """验证用户密码。"""
    from sqlalchemy import text
    _init_user_table()
    with app_engine.begin() as conn:
        row = conn.execute(
            text("SELECT id, username, password_hash, display_name, role, is_active FROM users WHERE username = :username"),
            {"username": username},
        ).mappings().fetchone()
    if not row or not row["is_active"]:
        return None
    if not verify_password(password, row["password_hash"]):
        return None
    return {
        "id": row["id"],
        "username": row["username"],
        "display_name": row["display_name"],
        "role": row["role"],
    }


def get_user_by_id(user_id: int) -> dict[str, Any] | None:
    """根据 ID 获取用户信息。"""
    from sqlalchemy import text
    _init_user_table()
    with app_engine.begin() as conn:
        row = conn.execute(
            text("SELECT id, username, display_name, role, is_active FROM users WHERE id = :id"),
            {"id": user_id},
        ).mappings().fetchone()
    if not row or not row["is_active"]:
        return None
    return {
        "id": row["id"],
        "username": row["username"],
        "display_name": row["display_name"],
        "role": row["role"],
    }


def create_access_token(user_id: int, expires_minutes: int = 480) -> str:
    """创建 JWT Token（简化版，使用 HMAC）。"""
    import base64
    import json

    header = base64.urlsafe_b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode()).rstrip(b"=")
    now = datetime.utcnow()
    payload = base64.urlsafe_b64encode(json.dumps({
        "sub": str(user_id),
        "iat": now.timestamp(),
        "exp": (now + timedelta(minutes=expires_minutes)).timestamp(),
    }).encode()).rstrip(b"=")
    signature = base64.urlsafe_b64encode(
        hmac.new(_SECRET.encode(), f"{header.decode()}.{payload.decode()}".encode(), hashlib.sha256).digest()
    ).rstrip(b"=")
    return f"{header.decode()}.{payload.decode()}.{signature.decode()}"


def decode_access_token(token: str) -> dict[str, Any] | None:
    """解码并验证 JWT Token。"""
    import base64
    import json

    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        header, payload, signature = parts
        expected_sig = base64.urlsafe_b64encode(
            hmac.new(_SECRET.encode(), f"{header}.{payload}".encode(), hashlib.sha256).digest()
        ).rstrip(b"=")
        if not secrets.compare_digest(signature.encode(), expected_sig):
            return None
        payload_data = json.loads(base64.urlsafe_b64decode(payload + "=="))
        if datetime.utcnow().timestamp() > payload_data.get("exp", 0):
            return None
        return payload_data
    except Exception:  # noqa: BLE001
        return None


def require_role(user: dict[str, Any], allowed_roles: set[str]) -> None:
    """检查用户角色权限。"""
    if user.get("role") not in allowed_roles:
        raise PermissionError(f"需要角色: {allowed_roles}")


def log_audit(user_id: int | None, action: str, resource: str | None = None, detail: str | None = None, ip: str | None = None) -> None:
    """记录审计日志。"""
    from sqlalchemy import text
    _init_user_table()
    with app_engine.begin() as conn:
        conn.execute(
            text("""
                INSERT INTO audit_logs (user_id, action, resource, detail, ip_address)
                VALUES (:user_id, :action, :resource, :detail, :ip)
            """),
            {
                "user_id": user_id,
                "action": action,
                "resource": resource,
                "detail": detail,
                "ip": ip,
            },
        )


def list_audit_logs(limit: int = 100) -> list[dict[str, Any]]:
    """列出审计日志。"""
    from sqlalchemy import text
    _init_user_table()
    with app_engine.begin() as conn:
        rows = conn.execute(
            text("""
                SELECT a.id, a.user_id, u.username, a.action, a.resource, a.detail, a.ip_address, a.created_at
                FROM audit_logs a
                LEFT JOIN users u ON a.user_id = u.id
                ORDER BY a.created_at DESC
                LIMIT :limit
            """),
            {"limit": limit},
        ).mappings().all()
    return [
        {
            "id": r["id"],
            "user_id": r["user_id"],
            "username": r["username"],
            "action": r["action"],
            "resource": r["resource"],
            "detail": r["detail"],
            "ip_address": r["ip_address"],
            "created_at": r["created_at"],
        }
        for r in rows
    ]
