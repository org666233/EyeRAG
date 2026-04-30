"""
用户数据模型
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, func
from app.database import Base


class User(Base):
    """用户表"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    real_name = Column(String(100), nullable=True)
    email = Column(String(100), nullable=True, index=True)
    is_active = Column(Boolean, default=True)
    avatar = Column(String(255), nullable=True)
    role = Column(String(20), nullable=False, default="user")  # "user" / "admin"
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<User(id={self.id}, username={self.username})>"
