"""用户认证与审计日志接口。"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

from app.schemas import LoginRequest, LoginResponse, UserCreateRequest, UserOut, AuditLogOut
from app.services.auth import (
    authenticate_user,
    create_access_token,
    create_user,
    decode_access_token,
    get_user_by_id,
    list_audit_logs,
    log_audit,
    require_role,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


def get_current_user(request: Request) -> dict[str, Any]:
    """从请求头获取当前用户。"""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未提供认证令牌")
    token = auth[7:]
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="认证令牌无效或已过期")
    user_id = int(payload["sub"])
    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在或已禁用")
    return user


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, request: Request) -> LoginResponse:
    """用户登录。"""
    user = authenticate_user(payload.username, payload.password)
    if not user:
        log_audit(None, "login_failed", detail=f"username={payload.username}", ip=request.client.host if request.client else None)
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    token = create_access_token(user["id"])
    log_audit(user["id"], "login", ip=request.client.host if request.client else None)
    return LoginResponse(
        access_token=token,
        token_type="bearer",
        user=UserOut(id=user["id"], username=user["username"], display_name=user["display_name"], role=user["role"]),
    )


@router.post("/register", response_model=UserOut)
def register(payload: UserCreateRequest, request: Request) -> UserOut:
    """用户注册（默认角色 analyst）。"""
    try:
        user = create_user(
            username=payload.username,
            password=payload.password,
            display_name=payload.display_name,
            role="analyst",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    log_audit(user["id"], "register", detail=f"username={payload.username}", ip=request.client.host if request.client else None)
    return UserOut(id=user["id"], username=user["username"], display_name=user["display_name"], role=user["role"])


@router.get("/me", response_model=UserOut)
def me(current_user: dict[str, Any] = Depends(get_current_user)) -> UserOut:
    """获取当前用户信息。"""
    return UserOut(
        id=current_user["id"],
        username=current_user["username"],
        display_name=current_user["display_name"],
        role=current_user["role"],
    )


@router.get("/audit", response_model=list[AuditLogOut])
def audit_logs(
    current_user: dict[str, Any] = Depends(get_current_user),
    limit: int = 100,
) -> list[AuditLogOut]:
    """查询审计日志（仅管理员）。"""
    try:
        require_role(current_user, {"admin"})
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    logs = list_audit_logs(limit=limit)
    return [
        AuditLogOut(
            id=log["id"],
            user_id=log["user_id"],
            username=log["username"],
            action=log["action"],
            resource=log["resource"],
            detail=log["detail"],
            ip_address=log["ip_address"],
            created_at=log["created_at"],
        )
        for log in logs
    ]
