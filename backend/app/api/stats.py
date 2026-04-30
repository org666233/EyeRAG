"""
系统统计看板 API
提供: 问答量、反馈分布、知识库状态、近 7 天趋势
"""

from datetime import datetime, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.models.user import User
from app.models.conversation import Conversation, Message
from app.models.feedback import Feedback
from app.models.favorite import Favorite
from app.services.auth import get_current_user
from app.rag.vector_store import get_vector_store

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/overview")
async def get_overview(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """系统概览：当前用户维度的核心指标"""
    # 会话总数
    conv_count = await session.scalar(
        select(func.count(Conversation.id)).where(Conversation.user_id == user.id)
    )

    # 消息总数（用户发问数）
    question_count = await session.scalar(
        select(func.count(Message.id))
        .join(Conversation, Message.conversation_id == Conversation.id)
        .where(Conversation.user_id == user.id, Message.role == "user")
    )

    # 收藏数
    fav_count = await session.scalar(
        select(func.count(Favorite.id)).where(Favorite.user_id == user.id)
    )

    # 反馈统计
    fb_result = await session.execute(
        select(
            func.count(Feedback.id).label("total"),
            func.sum(Feedback.rating).label("helpful"),
        ).where(Feedback.user_id == user.id)
    )
    fb_row = fb_result.one()
    fb_total = fb_row.total or 0
    fb_helpful = int(fb_row.helpful or 0)

    # 知识库状态
    vs = get_vector_store()
    kb_stats = vs.get_stats()

    return {
        "conversations": conv_count or 0,
        "questions": question_count or 0,
        "favorites": fav_count or 0,
        "feedback": {
            "total": fb_total,
            "helpful": fb_helpful,
            "not_helpful": fb_total - fb_helpful,
            "helpful_rate": round(fb_helpful / fb_total * 100, 1) if fb_total > 0 else 0,
        },
        "knowledge_base": {
            "document_count": kb_stats.get("document_count", 0),
            "chunk_count": kb_stats.get("total_chunks", 0),
        },
    }


@router.get("/trend")
async def get_trend(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """近 7 天每日问答量趋势"""
    today = datetime.now().date()
    trend = []

    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        day_start = datetime(day.year, day.month, day.day)
        day_end = day_start + timedelta(days=1)

        count = await session.scalar(
            select(func.count(Message.id))
            .join(Conversation, Message.conversation_id == Conversation.id)
            .where(
                Conversation.user_id == user.id,
                Message.role == "user",
                Message.created_at >= day_start,
                Message.created_at < day_end,
            )
        )
        trend.append({
            "date": day.strftime("%m-%d"),
            "questions": count or 0,
        })

    return trend


@router.get("/global")
async def get_global_stats(
    session: AsyncSession = Depends(get_db),
):
    """全局统计（无需登录，用于首页展示）"""
    user_count = await session.scalar(select(func.count(User.id)))
    question_count = await session.scalar(
        select(func.count(Message.id)).where(Message.role == "user")
    )
    vs = get_vector_store()
    kb_stats = vs.get_stats()

    return {
        "users": user_count or 0,
        "total_questions": question_count or 0,
        "knowledge_chunks": kb_stats.get("total_chunks", 0),
    }
