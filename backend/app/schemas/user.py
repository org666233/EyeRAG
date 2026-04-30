"""
用户认证 Pydantic Schemas
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6, max_length=100)
    real_name: Optional[str] = None
    email: Optional[str] = None


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    username: str
    role: str = "user"


class UserInfo(BaseModel):
    id: int
    username: str
    real_name: Optional[str] = None
    email: Optional[str] = None
    is_active: bool
    role: str = "user"
    created_at: datetime

    class Config:
        from_attributes = True
