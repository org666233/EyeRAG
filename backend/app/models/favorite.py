"""
收藏夹数据模型
用户收藏的问答对，方便日后查阅
"""

from sqlalchemy import Column, Integer, Text, DateTime, ForeignKey, func
from app.database import Base


class Favorite(Base):
    """收藏夹表"""
    __tablename__ = "favorites"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    message_id = Column(Integer, ForeignKey("messages.id"), nullable=False)
    question = Column(Text, nullable=False)   # 冗余存储，方便展示无需 join
    answer = Column(Text, nullable=False)
    sources = Column(Text, nullable=True)     # JSON 字符串
    created_at = Column(DateTime, server_default=func.now())

    def __repr__(self):
        return f"<Favorite(id={self.id}, user_id={self.user_id})>"
