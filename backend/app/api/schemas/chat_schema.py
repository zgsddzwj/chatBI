"""对话接口的 Pydantic 请求/响应模型。

将原来裸 request.json() 替换为类型安全的 Pydantic 模型，
FastAPI 自动完成校验和 422 错误响应。
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """对话请求。"""
    question: str = Field(..., min_length=1, max_length=5000, description="用户问题")
    conversation_id: int | None = Field(default=None, description="会话 ID")


class IntentRequest(BaseModel):
    """意图识别请求。"""
    question: str = Field(..., min_length=1, max_length=5000, description="用户问题")


class ContextExpandRequest(BaseModel):
    """上下文扩展请求。"""
    conversation_id: int = Field(..., ge=0, description="会话 ID")
    question: str = Field(..., min_length=1, max_length=5000, description="用户问题")


class SuggestionRequest(BaseModel):
    """查询建议查询参数。"""
    q: str = Field(default="", max_length=200, description="输入前缀")
    conversation_id: int | None = Field(default=None, description="会话 ID")
    limit: int = Field(default=8, ge=1, le=50, description="返回数量")


class AutocompleteRequest(BaseModel):
    """自动补全查询参数。"""
    q: str = Field(default="", max_length=200, description="输入前缀")
    limit: int = Field(default=5, ge=1, le=50, description="返回数量")


class HistoryRequest(BaseModel):
    """查询历史请求参数。"""
    user_id: int = Field(..., ge=1, description="用户 ID")
    limit: int = Field(default=20, ge=1, le=100, description="返回数量")
    offset: int = Field(default=0, ge=0, description="偏移量")
