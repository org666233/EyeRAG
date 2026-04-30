"""
请求/响应 Schema - 通用
"""

from pydantic import BaseModel
from datetime import datetime


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str = "ok"
    version: str
    app_name: str


class ErrorResponse(BaseModel):
    """错误响应"""
    detail: str
    code: int = 400
