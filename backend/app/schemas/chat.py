"""
聊天相关 Pydantic Schemas
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ChatRequest(BaseModel):
    """聊天请求"""
    question: str = Field(..., min_length=1, max_length=2000, description="用户问题")
    conversation_id: Optional[int] = Field(None, description="会话ID（整数），传入则为多轮对话")
    stream: bool = Field(default=True, description="是否使用流式响应")
    top_k: int = Field(default=5, ge=1, le=20, description="检索文档数量")


class SourceInfo(BaseModel):
    """引用来源"""
    title: str = ""
    source: str = ""
    url: str = ""
    score: float = 0.0


class ChatResponse(BaseModel):
    """聊天响应（非流式）"""
    answer: str
    sources: list[SourceInfo] = []
    query: str
    conversation_id: Optional[int] = None
    context_count: int = 0


class ConversationInfo(BaseModel):
    """会话信息"""
    id: int
    title: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class MessageInfo(BaseModel):
    """单条消息"""
    id: int
    role: str
    content: str
    created_at: Optional[datetime] = None
    sources: Optional[list[SourceInfo]] = None
