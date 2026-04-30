"""
检索历史记录数据模型
记录每次 RAG 检索的完整过程，便于用户回顾和系统分析
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Float, func
from sqlalchemy.orm import relationship
from app.database import Base


class SearchHistory(Base):
    """检索历史记录表"""
    __tablename__ = "search_histories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    # 原始问题
    question = Column(Text, nullable=False)
    # 最终回答
    answer = Column(Text, nullable=True)
    # 检索决策（proceed / retry / fallback）
    retrieval_decision = Column(String(20), nullable=True)
    # 检索决策原因
    decision_reason = Column(Text, nullable=True)
    # 引用的来源列表（JSON）
    sources = Column(JSON, nullable=True)
    # 检索到的文档块列表（JSON，用于详情展示）
    search_results = Column(JSON, nullable=True)
    # RRF 融合后 Top-K 文档数
    context_count = Column(Integer, nullable=True)
    # LLM 响应耗时（秒）
    response_time_ms = Column(Float, nullable=True)
    # 反馈（1=有用, 0=没用, null=未评价）
    rating = Column(Integer, nullable=True)
    # 是否收藏
    is_favorited = Column(Integer, nullable=False, default=0)
    # 会话 ID（关联到 Conversation）
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=True, index=True)
    # 创建时间
    created_at = Column(DateTime, server_default=func.now(), index=True)

    # 关系
    user = relationship("User", backref="search_histories")
    conversation = relationship("Conversation", backref="search_histories")

    def __repr__(self):
        return f"<SearchHistory(id={self.id}, user_id={self.user_id}, decision={self.retrieval_decision})>"
