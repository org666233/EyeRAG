"""
用户认证 API 路由
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.user import User
from app.schemas.user import RegisterRequest, LoginRequest, TokenResponse, UserInfo
from app.services.auth import (
    hash_password, verify_password, create_access_token, get_current_user
)
from app.utils.logger import logger

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse)
async def register(req: RegisterRequest, session: AsyncSession = Depends(get_db)):
    """用户注册"""
    # 检查用户名是否存在
    result = await session.execute(select(User).where(User.username == req.username))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="用户名已存在")

    # 检查是否已有用户，第一个注册的用户自动成为管理员
    count_result = await session.execute(select(User.id))
    is_first_user = count_result.first() is None
    role = "admin" if is_first_user else "user"

    user = User(
        username=req.username,
        password_hash=hash_password(req.password),
        real_name=req.real_name,
        email=req.email,
        role=role,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)

    token = create_access_token({"sub": str(user.id)})
    logger.info(f"新用户注册: {user.username} (ID: {user.id}, role: {role})")

    return TokenResponse(
        access_token=token,
        user_id=user.id,
        username=user.username,
        role=user.role,
    )


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, session: AsyncSession = Depends(get_db)):
    """用户登录"""
    result = await session.execute(select(User).where(User.username == req.username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="账号已被禁用")

    token = create_access_token({"sub": str(user.id)})
    logger.info(f"用户登录: {user.username}")

    return TokenResponse(
        access_token=token,
        user_id=user.id,
        username=user.username,
        role=user.role,
    )


@router.get("/me", response_model=UserInfo)
async def get_me(user: User = Depends(get_current_user)):
    """获取当前用户信息"""
    return UserInfo.model_validate(user)
