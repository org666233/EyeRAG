"""
收藏夹 API
用户收藏问答对，方便日后快速查阅
"""

import json
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.user import User
from app.models.conversation import Message
from app.models.favorite import Favorite
from app.services.auth import get_current_user
from pydantic import BaseModel

router = APIRouter(prefix="/favorites", tags=["favorites"])


class FavoriteRequest(BaseModel):
    message_id: int   # 收藏的 assistant 消息 ID（含 question 上文）


@router.post("")
async def add_favorite(
    req: FavoriteRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """收藏一条 AI 回答（自动关联上一条用户问题）"""
    # 获取 assistant 消息
    msg_result = await session.execute(
        select(Message).where(Message.id == req.message_id, Message.role == "assistant")
    )
    msg = msg_result.scalar_one_or_none()
    if not msg:
        raise HTTPException(status_code=404, detail="消息不存在或不是 AI 回答")

    # 检查是否已收藏
    existing = await session.execute(
        select(Favorite).where(
            Favorite.user_id == user.id,
            Favorite.message_id == req.message_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="已收藏过这条回答")

    # 获取上一条用户问题（message_id - 1，同 conversation）
    question = ""
    prev_result = await session.execute(
        select(Message).where(
            Message.conversation_id == msg.conversation_id,
            Message.role == "user",
            Message.id < msg.id,
        ).order_by(Message.id.desc()).limit(1)
    )
    prev = prev_result.scalar_one_or_none()
    if prev:
        question = prev.content

    sources_str = json.dumps(msg.sources, ensure_ascii=False) if msg.sources else "[]"

    fav = Favorite(
        user_id=user.id,
        message_id=msg.id,
        question=question,
        answer=msg.content,
        sources=sources_str,
    )
    session.add(fav)
    return {"message": "收藏成功", "favorite_id": fav.id}


@router.get("")
async def list_favorites(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """获取当前用户的所有收藏"""
    result = await session.execute(
        select(Favorite)
        .where(Favorite.user_id == user.id)
        .order_by(Favorite.created_at.desc())
    )
    favs = result.scalars().all()
    return [
        {
            "id": f.id,
            "message_id": f.message_id,
            "question": f.question,
            "answer": f.answer,
            "sources": json.loads(f.sources) if f.sources else [],
            "created_at": f.created_at.isoformat() if f.created_at else None,
        }
        for f in favs
    ]


@router.delete("/{favorite_id}")
async def remove_favorite(
    favorite_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """取消收藏"""
    result = await session.execute(
        select(Favorite).where(
            Favorite.id == favorite_id,
            Favorite.user_id == user.id,
        )
    )
    fav = result.scalar_one_or_none()
    if not fav:
        raise HTTPException(status_code=404, detail="收藏不存在")
    await session.delete(fav)
    return {"message": "已取消收藏"}


@router.get("/check/{message_id}")
async def check_favorite(
    message_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """检查某条消息是否已收藏"""
    result = await session.execute(
        select(Favorite).where(
            Favorite.user_id == user.id,
            Favorite.message_id == message_id,
        )
    )
    fav = result.scalar_one_or_none()
    return {"favorited": fav is not None, "favorite_id": fav.id if fav else None}
