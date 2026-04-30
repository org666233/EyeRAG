"""
检索历史相关 Pydantic Schemas
"""

from pydantic import BaseModel, Field
from typing import Optional


class SearchHistoryInfo(BaseModel):
    """检索历史记录"""
    id: int
    question: str
    answer: Optional[str] = None
    retrieval_decision: Optional[str] = None
    decision_reason: Optional[str] = None
    sources: Optional[list] = None
    context_count: Optional[int] = None
    response_time_ms: Optional[float] = None
    rating: Optional[int] = None
    is_favorited: int = 0
    created_at: Optional[str] = None


class SearchHistoryListResponse(BaseModel):
    """检索历史列表响应"""
    items: list[SearchHistoryInfo]
    total: int
    page: int
    page_size: int


class SearchHistoryDetailResponse(BaseModel):
    """检索历史详情响应"""
    id: int
    question: str
    answer: Optional[str] = None
    retrieval_decision: Optional[str] = None
    decision_reason: Optional[str] = None
    sources: Optional[list] = None
    search_results: Optional[list] = None
    context_count: Optional[int] = None
    response_time_ms: Optional[float] = None
    rating: Optional[int] = None
    is_favorited: int = 0
    created_at: Optional[str] = None
