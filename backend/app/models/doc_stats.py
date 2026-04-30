"""
文档热度统计数据模型
记录每个文档的浏览次数和被检索命中的次数
"""

from sqlalchemy import Column, Integer, String, DateTime, func
from sqlalchemy.orm import relationship
from app.database import Base


class DocStats(Base):
    """文档热度统计表"""
    __tablename__ = "doc_stats"

    id = Column(Integer, primary_key=True, autoincrement=True)
    file_name = Column(String(255), unique=True, nullable=False, index=True)
    view_count = Column(Integer, nullable=False, default=0)
    hit_count = Column(Integer, nullable=False, default=0)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<DocStats(file_name={self.file_name}, view={self.view_count}, hit={self.hit_count})>"
