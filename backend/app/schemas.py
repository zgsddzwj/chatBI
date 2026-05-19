"""API 请求/响应模型。"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class HistoryMessage(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    conversation_id: int | None = None
    history: list[HistoryMessage] = Field(default_factory=list)


class ChatResponse(BaseModel):
    type: str  # answer / clarification / error
    conversation_id: int
    message_id: int
    sql: str | None = None
    explanation: str | None = None
    data: dict[str, Any] | None = None
    chart: dict[str, Any] | None = None
    summary: str | None = None
    clarification: str | None = None
    error: str | None = None


class MessageOut(BaseModel):
    id: int
    role: str
    content: str
    sql: str | None = None
    result: dict[str, Any] | None = None
    chart: dict[str, Any] | None = None
    summary: str | None = None
    error: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ConversationOut(BaseModel):
    id: int
    title: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ConversationDetail(ConversationOut):
    messages: list[MessageOut] = Field(default_factory=list)


class TableInfo(BaseModel):
    name: str
    comment: str
    columns: list[dict[str, str]]


class SchemaInfo(BaseModel):
    dialect: str
    tables: list[TableInfo]
    relations: list[str]
    hints: list[str]


class SampleQuestions(BaseModel):
    questions: list[str]


class TaskCreateRequest(BaseModel):
    sql: str = Field(..., min_length=1)
    row_limit: int = Field(default=1000, ge=1, le=50_000)


class TaskResponse(BaseModel):
    task_id: str
    status: str
    result: dict[str, Any] | None = None
    error: str | None = None
    created_at: datetime | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
