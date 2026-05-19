"""后台 SQL 任务接口。"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.schemas import TaskCreateRequest, TaskResponse
from app.services.tasks import get_task, list_pending_tasks, submit_task

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.post("", response_model=TaskResponse)
def create_task(payload: TaskCreateRequest) -> TaskResponse:
    """提交 SQL 执行任务。"""
    try:
        task_id = submit_task(payload.sql, row_limit=payload.row_limit)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    task = get_task(task_id)
    if not task:
        raise HTTPException(status_code=500, detail="任务创建失败")
    return TaskResponse(
        task_id=task["task_id"],
        status=task["status"],
        result=task.get("result"),
        error=task.get("error"),
        created_at=task["created_at"],
        started_at=task.get("started_at"),
        finished_at=task.get("finished_at"),
    )


@router.get("/{task_id}", response_model=TaskResponse)
def read_task(task_id: str) -> TaskResponse:
    """查询任务状态。"""
    task = get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return TaskResponse(
        task_id=task["task_id"],
        status=task["status"],
        result=task.get("result"),
        error=task.get("error"),
        created_at=task["created_at"],
        started_at=task.get("started_at"),
        finished_at=task.get("finished_at"),
    )


@router.get("")
def list_tasks() -> list[dict]:
    """列出所有待处理任务。"""
    return list_pending_tasks()
