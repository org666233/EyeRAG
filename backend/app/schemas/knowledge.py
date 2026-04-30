"""
知识库 Pydantic Schemas
"""

from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class DocumentInfo(BaseModel):
    """文档信息响应"""
    file_name: str
    source: str
    file_type: str
    source_name: Optional[str] = ""
    url: Optional[str] = ""
    chunk_count: int
    view_count: int = 0
    hit_count: int = 0


class KnowledgeStats(BaseModel):
    """知识库统计"""
    total_chunks: int
    total_documents: int
    collection_name: str


class DocumentPreview(BaseModel):
    """文档预览响应"""
    file_name: str
    file_type: str
    source_name: Optional[str] = ""
    chunk_count: int
    view_count: int = 0
    hit_count: int = 0
    chunks: list[dict]
    total_chars: int


class KnowledgeStats(BaseModel):
    """知识库统计"""
    total_chunks: int
    total_documents: int
    collection_name: str


class IngestResponse(BaseModel):
    """文档导入响应"""
    file_name: str
    chunk_count: int
    message: str


class SearchRequest(BaseModel):
    """检索请求"""
    query: str
    top_k: int = 5


class SearchResult(BaseModel):
    """单个检索结果"""
    content: str
    metadata: dict
    score: float
    id: str


class SearchResponse(BaseModel):
    """检索响应"""
    query: str
    results: list[SearchResult]
    total: int
