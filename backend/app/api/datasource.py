"""数据源管理接口。"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.schemas import DataSourceCreate, DataSourceOut, DataSourceUpdate
from app.services.datasource import (
    create_source,
    delete_source,
    get_source,
    list_sources,
    test_connection,
    update_source,
)

router = APIRouter(prefix="/api/datasources", tags=["datasources"])


@router.get("", response_model=list[DataSourceOut])
def list_datasources() -> list[DataSourceOut]:
    """列出所有数据源。"""
    return [DataSourceOut(**s) for s in list_sources()]


@router.get("/{source_id}", response_model=DataSourceOut)
def get_datasource(source_id: int) -> DataSourceOut:
    """获取数据源详情。"""
    source = get_source(source_id)
    if not source:
        raise HTTPException(status_code=404, detail="数据源不存在")
    return DataSourceOut(**source)


@router.post("", response_model=DataSourceOut)
def create_datasource(payload: DataSourceCreate) -> DataSourceOut:
    """创建数据源。"""
    source = create_source(
        name=payload.name,
        db_type=payload.db_type,
        connection_url=payload.connection_url,
        description=payload.description,
        schema=payload.schema_config,
    )
    return DataSourceOut(**source)


@router.put("/{source_id}", response_model=DataSourceOut)
def update_datasource(source_id: int, payload: DataSourceUpdate) -> DataSourceOut:
    """更新数据源。"""
    updates = payload.model_dump(exclude_unset=True)
    source = update_source(source_id, **updates)
    if not source:
        raise HTTPException(status_code=404, detail="数据源不存在")
    return DataSourceOut(**source)


@router.delete("/{source_id}")
def delete_datasource(source_id: int) -> dict:
    """删除数据源。"""
    if not delete_source(source_id):
        raise HTTPException(status_code=400, detail="不能删除默认数据源或数据源不存在")
    return {"ok": True}


@router.post("/test-connection")
def test_datasource_connection(payload: DataSourceCreate) -> dict:
    """测试数据库连接。"""
    return test_connection(payload.connection_url)
