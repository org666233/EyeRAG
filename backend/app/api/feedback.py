"""
答案反馈 API
用户对 AI 回答进行 👍/👎 评价，支持附带文字说明
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.models.user import User
from app.models.conversation import Message
from app.models.feedback import Feedback
from app.services.auth import get_current_user
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/feedback", tags=["feedback"])


class FeedbackRequest(BaseModel):
    message_id: int
    rating: int          # 1=有用, 0=没用
    comment: Optional[str] = None


@router.post("")
async def submit_feedback(
    req: FeedbackRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """提交对某条 AI 回答的评价（每条消息只能评价一次，可覆盖）"""
    if req.rating not in (0, 1):
        raise HTTPException(status_code=400, detail="rating 只能是 0（没用）或 1（有用）")

    # 验证消息存在
    msg_result = await session.execute(select(Message).where(Message.id == req.message_id))
    if not msg_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="消息不存在")

    # 若已有评价则覆盖
    existing = await session.execute(
        select(Feedback).where(
            Feedback.user_id == user.id,
            Feedback.message_id == req.message_id,
        )
    )
    fb = existing.scalar_one_or_none()
    if fb:
        fb.rating = req.rating
        fb.comment = req.comment
    else:
        fb = Feedback(
            user_id=user.id,
            message_id=req.message_id,
            rating=req.rating,
            comment=req.comment,
        )
        session.add(fb)

    return {"message": "反馈已记录", "rating": req.rating}


@router.get("/message/{message_id}")
async def get_message_feedback(
    message_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """获取当前用户对某条消息的评价状态"""
    result = await session.execute(
        select(Feedback).where(
            Feedback.user_id == user.id,
            Feedback.message_id == message_id,
        )
    )
    fb = result.scalar_one_or_none()
    if not fb:
        return {"rated": False, "rating": None}
    return {"rated": True, "rating": fb.rating, "comment": fb.comment}


@router.get("/stats")
async def get_feedback_stats(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """获取系统整体反馈统计（当前用户维度）"""
    result = await session.execute(
        select(
            func.count(Feedback.id).label("total"),
            func.sum(Feedback.rating).label("helpful"),
        ).where(Feedback.user_id == user.id)
    )
    row = result.one()
    total = row.total or 0
    helpful = int(row.helpful or 0)
    return {
        "total": total,
        "helpful": helpful,
        "not_helpful": total - helpful,
        "helpful_rate": round(helpful / total * 100, 1) if total > 0 else 0,
    }
