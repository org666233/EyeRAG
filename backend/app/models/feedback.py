"""
答案反馈数据模型
用户对 AI 回答的满意度评价（👍/👎）及文字评论
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, func
from app.database import Base


class Feedback(Base):
    """答案反馈表"""
    __tablename__ = "feedbacks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    message_id = Column(Integer, ForeignKey("messages.id"), nullable=False, index=True)
    rating = Column(Integer, nullable=False)   # 1 = 👍 有用, 0 = 👎 没用
    comment = Column(Text, nullable=True)       # 可选的文字评论
    created_at = Column(DateTime, server_default=func.now())

    def __repr__(self):
        return f"<Feedback(id={self.id}, rating={self.rating})>"
