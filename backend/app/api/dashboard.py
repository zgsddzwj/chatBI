"""仪表盘接口。"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

from app.schemas import CardCreate, DashboardCreate, DashboardOut
from app.services.auth import decode_access_token, get_user_by_id
from app.services.dashboard import (
    add_card_to_dashboard,
    create_card,
    create_dashboard,
    delete_card,
    delete_dashboard,
    get_dashboard,
    list_cards,
    list_dashboards,
    remove_card_from_dashboard,
)

router = APIRouter(prefix="/api/dashboards", tags=["dashboards"])


def _get_current_user_id(request: Request) -> int:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未登录")
    payload = decode_access_token(auth[7:])
    if not payload:
        raise HTTPException(status_code=401, detail="认证已过期")
    return int(payload["sub"])


@router.post("/cards")
def create_card_endpoint(payload: CardCreate, request: Request) -> dict[str, Any]:
    """收藏图表卡片。"""
    user_id = _get_current_user_id(request)
    card = create_card(
        user_id=user_id,
        title=payload.title,
        chart_type=payload.chart_type,
        chart=payload.chart,
        data=payload.data,
        sql=payload.sql,
    )
    return card


@router.get("/cards")
def list_cards_endpoint(request: Request) -> list[dict[str, Any]]:
    """列出用户的卡片。"""
    user_id = _get_current_user_id(request)
    return list_cards(user_id)


@router.delete("/cards/{card_id}")
def delete_card_endpoint(card_id: int, request: Request) -> dict:
    """删除卡片。"""
    user_id = _get_current_user_id(request)
    if not delete_card(card_id, user_id):
        raise HTTPException(status_code=404, detail="卡片不存在")
    return {"ok": True}


@router.post("", response_model=DashboardOut)
def create_dashboard_endpoint(payload: DashboardCreate, request: Request) -> DashboardOut:
    """创建仪表盘。"""
    user_id = _get_current_user_id(request)
    dashboard = create_dashboard(user_id, payload.name, payload.description)
    return DashboardOut(**dashboard)


@router.get("")
def list_dashboards_endpoint(request: Request) -> list[dict[str, Any]]:
    """列出仪表盘。"""
    user_id = _get_current_user_id(request)
    return list_dashboards(user_id)


@router.get("/{dashboard_id}")
def get_dashboard_endpoint(dashboard_id: int, request: Request) -> dict[str, Any]:
    """获取仪表盘详情。"""
    user_id = _get_current_user_id(request)
    dashboard = get_dashboard(dashboard_id, user_id)
    if not dashboard:
        raise HTTPException(status_code=404, detail="仪表盘不存在")
    return dashboard


@router.post("/{dashboard_id}/cards/{card_id}")
def add_card_endpoint(dashboard_id: int, card_id: int, request: Request) -> dict:
    """添加卡片到仪表盘。"""
    user_id = _get_current_user_id(request)
    if not add_card_to_dashboard(dashboard_id, card_id, user_id):
        raise HTTPException(status_code=400, detail="添加失败")
    return {"ok": True}


@router.delete("/{dashboard_id}/cards/{card_id}")
def remove_card_endpoint(dashboard_id: int, card_id: int, request: Request) -> dict:
    """从仪表盘移除卡片。"""
    user_id = _get_current_user_id(request)
    if not remove_card_from_dashboard(dashboard_id, card_id, user_id):
        raise HTTPException(status_code=400, detail="移除失败")
    return {"ok": True}


@router.delete("/{dashboard_id}")
def delete_dashboard_endpoint(dashboard_id: int, request: Request) -> dict:
    """删除仪表盘。"""
    user_id = _get_current_user_id(request)
    if not delete_dashboard(dashboard_id, user_id):
        raise HTTPException(status_code=404, detail="仪表盘不存在")
    return {"ok": True}
