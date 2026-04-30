"""
管理后台 API 路由
提供用户管理、检索分析可视化和系统级统计
"""

import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

from app.database import get_db
from app.models.user import User
from app.models.conversation import Conversation, Message
from app.models.feedback import Feedback
from app.models.search_history import SearchHistory
from app.models.favorite import Favorite
from app.rag.vector_store import get_vector_store
from app.services.auth import get_current_user
from app.config import get_settings

router = APIRouter(prefix="/admin", tags=["admin"])


def require_admin(user: User = Depends(get_current_user)):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return user


# ─────────────────────────────────────────────────────────────
# 用户管理
# ─────────────────────────────────────────────────────────────

@router.get("/users")
async def list_users(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    keyword: str = Query(default=""),
    user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
):
    """获取所有用户列表（管理员专用）"""
    base = select(User)
    if keyword:
        base = base.where(
            (User.username.ilike(f"%{keyword}%"))
            | (User.real_name.ilike(f"%{keyword}%"))
            | (User.email.ilike(f"%{keyword}%"))
        )

    count_q = select(func.count()).select_from(base.subquery())
    total = await session.scalar(count_q) or 0

    offset = (page - 1) * page_size
    result = await session.execute(
        base.order_by(desc(User.created_at)).offset(offset).limit(page_size)
    )
    users = result.scalars().all()

    # 查询每个用户的统计数据
    items = []
    for u in users:
        q_count = await session.scalar(
            select(func.count(Message.id))
            .join(Conversation, Message.conversation_id == Conversation.id)
            .where(Conversation.user_id == u.id, Message.role == "user")
        )
        fav_count = await session.scalar(
            select(func.count(Favorite.id)).where(Favorite.user_id == u.id)
        )
        fb_result = await session.execute(
            select(func.count(Feedback.id), func.sum(Feedback.rating))
            .where(Feedback.user_id == u.id)
        )
        fb_row = fb_result.one()
        helpful = int(fb_row[1] or 0)

        items.append({
            "id": u.id,
            "username": u.username,
            "real_name": u.real_name or "-",
            "email": u.email or "-",
            "role": u.role,
            "is_active": u.is_active,
            "created_at": u.created_at.isoformat() if u.created_at else None,
            "question_count": q_count or 0,
            "favorite_count": fav_count or 0,
            "feedback_helpful": helpful,
        })

    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.patch("/users/{user_id}/toggle-active")
async def toggle_user_active(
    user_id: int,
    user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
):
    """切换用户激活状态"""
    result = await session.execute(select(User).where(User.id == user_id))
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="用户不存在")
    if target.id == user.id:
        raise HTTPException(status_code=400, detail="不能操作自己")
    target.is_active = not target.is_active
    return {"id": target.id, "is_active": target.is_active}


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
):
    """删除用户（级联删除相关数据）"""
    result = await session.execute(select(User).where(User.id == user_id))
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="用户不存在")
    if target.id == user.id:
        raise HTTPException(status_code=400, detail="不能删除自己")
    await session.delete(target)
    return {"message": "用户已删除"}


@router.post("/users")
async def create_admin_user(
    payload: dict,
    user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
):
    """创建管理员用户（仅超级管理员可操作）"""
    from app.services.auth import hash_password

    existing = await session.execute(
        select(User).where(User.username == payload.get("username"))
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="用户名已存在")

    new_user = User(
        username=payload.get("username"),
        password_hash=hash_password(payload.get("password")),
        real_name=payload.get("real_name"),
        email=payload.get("email"),
        role="admin",
    )
    session.add(new_user)
    return {"id": new_user.id, "username": new_user.username, "role": new_user.role}


# ─────────────────────────────────────────────────────────────
# 系统级统计（全局，非当前用户）
# ─────────────────────────────────────────────────────────────

@router.get("/stats/overview")
async def admin_overview(
    user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
):
    """系统总览：全局统计"""
    user_count = await session.scalar(select(func.count(User.id)))
    question_count = await session.scalar(
        select(func.count(Message.id)).where(Message.role == "user")
    )
    conv_count = await session.scalar(select(func.count(Conversation.id)))
    history_count = await session.scalar(select(func.count(SearchHistory.id)))
    fav_count = await session.scalar(select(func.count(Favorite.id)))

    fb_result = await session.execute(
        select(func.count(Feedback.id), func.sum(Feedback.rating))
    )
    fb_row = fb_result.one()
    helpful = int(fb_row[1] or 0)
    fb_total = fb_row[0] or 0

    vs = get_vector_store()
    kb_stats = vs.get_stats()

    return {
        "total_users": user_count or 0,
        "total_questions": question_count or 0,
        "total_conversations": conv_count or 0,
        "total_searches": history_count or 0,
        "total_favorites": fav_count or 0,
        "feedback": {
            "total": fb_total,
            "helpful": helpful,
            "not_helpful": fb_total - helpful,
            "helpful_rate": round(helpful / fb_total * 100, 1) if fb_total > 0 else 0,
        },
        "knowledge_base": {
            "document_count": kb_stats.get("document_count", 0),
            "chunk_count": kb_stats.get("total_chunks", 0),
        },
    }


@router.get("/stats/decision-distribution")
async def retrieval_decision_distribution(
    days: int = Query(default=30, ge=1, le=365),
    user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
):
    """检索决策分布：统计各决策类型占比"""
    since = datetime.now() - timedelta(days=days)
    result = await session.execute(
        select(
            SearchHistory.retrieval_decision,
            func.count(SearchHistory.id).label("count"),
        )
        .where(SearchHistory.created_at >= since)
        .group_by(SearchHistory.retrieval_decision)
    )
    rows = result.all()

    total = sum(r.count for r in rows)
    items = []
    for r in rows:
        decision = r.retrieval_decision or "unknown"
        label_map = {"proceed": "正常检索", "retry": "二次检索", "fallback": "降级回答", "unknown": "未知"}
        items.append({
            "decision": decision,
            "label": label_map.get(decision, decision),
            "count": r.count,
            "percent": round(r.count / total * 100, 1) if total > 0 else 0,
        })
    return {"items": items, "total": total, "days": days}


@router.get("/stats/response-time")
async def response_time_trend(
    days: int = Query(default=7, ge=1, le=30),
    user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
):
    """响应耗时趋势：每日平均响应时间"""
    since = datetime.now() - timedelta(days=days)
    result = await session.execute(
        select(
            func.date(SearchHistory.created_at).label("day"),
            func.avg(SearchHistory.response_time_ms).label("avg_ms"),
            func.min(SearchHistory.response_time_ms).label("min_ms"),
            func.max(SearchHistory.response_time_ms).label("max_ms"),
            func.count(SearchHistory.id).label("count"),
        )
        .where(
            SearchHistory.created_at >= since,
            SearchHistory.response_time_ms.isnot(None),
        )
        .group_by(func.date(SearchHistory.created_at))
        .order_by(func.date(SearchHistory.created_at))
    )
    rows = result.all()
    return [
        {
            "date": str(r.day),
            "avg_ms": round(float(r.avg_ms or 0), 1),
            "min_ms": round(float(r.min_ms or 0), 1),
            "max_ms": round(float(r.max_ms or 0), 1),
            "count": r.count,
        }
        for r in rows
    ]


@router.get("/stats/feedback-trend")
async def feedback_trend(
    days: int = Query(default=7, ge=1, le=30),
    user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
):
    """反馈趋势：每日正负反馈数量"""
    since = datetime.now() - timedelta(days=days)
    result = await session.execute(
        select(
            func.date(Feedback.created_at).label("day"),
            func.sum(Feedback.rating).label("helpful"),
            func.count(Feedback.id).label("total"),
        )
        .where(Feedback.created_at >= since)
        .group_by(func.date(Feedback.created_at))
        .order_by(func.date(Feedback.created_at))
    )
    rows = result.all()
    return [
        {
            "date": str(r.day),
            "helpful": int(r.helpful or 0),
            "not_helpful": r.total - int(r.helpful or 0),
            "total": r.total,
            "helpful_rate": round(int(r.helpful or 0) / r.total * 100, 1) if r.total > 0 else 0,
        }
        for r in rows
    ]


@router.get("/stats/top-queries")
async def top_queries(
    limit: int = Query(default=20, ge=1, le=100),
    days: int = Query(default=30, ge=1, le=365),
    user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
):
    """Top 查询：最常被问的问题"""
    since = datetime.now() - timedelta(days=days)
    result = await session.execute(
        select(
            SearchHistory.question,
            func.count(SearchHistory.id).label("count"),
            func.avg(SearchHistory.response_time_ms).label("avg_ms"),
        )
        .where(SearchHistory.created_at >= since)
        .group_by(SearchHistory.question)
        .order_by(desc("count"))
        .limit(limit)
    )
    rows = result.all()
    return [
        {
            "question": r.question,
            "count": r.count,
            "avg_ms": round(float(r.avg_ms or 0), 1),
        }
        for r in rows
    ]


@router.get("/stats/decision-by-source")
async def decision_by_source(
    days: int = Query(default=30, ge=1, le=365),
    user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
):
    """各来源文档的检索决策分布：追踪哪些文档质量更高"""
    since = datetime.now() - timedelta(days=days)
    result = await session.execute(
        select(
            SearchHistory.sources,
            SearchHistory.retrieval_decision,
        )
        .where(
            SearchHistory.created_at >= since,
            SearchHistory.sources.isnot(None),
        )
    )
    rows = result.all()

    # 统计每个 source title 的决策分布
    source_stats = {}
    for row in rows:
        if not row.sources:
            continue
        for src in row.sources:
            title = src.get("title") or "未知来源"
            if title not in source_stats:
                source_stats[title] = {"proceed": 0, "retry": 0, "fallback": 0}
            decision = row.retrieval_decision or "unknown"
            if decision in source_stats[title]:
                source_stats[title][decision] += 1

    items = [
        {
            "source": title,
            "proceed": stats["proceed"],
            "retry": stats["retry"],
            "fallback": stats["fallback"],
            "total": sum(stats.values()),
        }
        for title, stats in sorted(source_stats.items(), key=lambda x: sum(x[1].values()), reverse=True)
        if sum(stats.values()) > 0
    ]
    return items[:20]


# ─────────────────────────────────────────────────────────────
# 模型配置管理
# ─────────────────────────────────────────────────────────────

@router.get("/model-config")
async def get_model_config(user: User = Depends(require_admin)):
    """获取当前模型配置及可用嵌入模型列表"""
    from app.rag.embeddings import get_current_model_info
    from app import runtime_config

    settings = get_settings()
    model_dir = Path("model")
    available_models: list[str] = []
    if model_dir.exists():
        available_models = sorted(d.name for d in model_dir.iterdir() if d.is_dir())

    model_info = await asyncio.to_thread(get_current_model_info)

    return {
        "llm_provider": settings.llm_provider,
        "llm_model_name": settings.llm_model_name,
        "minimax_model_name": settings.minimax_model_name,
        "embedding_model": model_info,
        "available_embedding_models": available_models,
        "chroma_collection": settings.chroma_collection_name,
        "overrides": runtime_config.get_all(),
    }


@router.post("/model-config")
async def update_model_config(payload: dict, user: User = Depends(require_admin)):
    """更新 LLM 配置（下次请求立即生效，无需重启）"""
    from app import runtime_config

    allowed = {"llm_provider", "llm_model_name", "minimax_model_name"}
    updates = {k: v for k, v in payload.items() if k in allowed}
    if not updates:
        raise HTTPException(status_code=400, detail="没有合法的配置项可更新")

    runtime_config.set_values(updates)
    return {"message": "LLM 配置已更新，下次请求生效", "applied": updates}
