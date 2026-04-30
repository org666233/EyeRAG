"""
检索历史 API 路由
提供检索历史记录的管理接口
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete

from app.database import get_db
from app.models.user import User
from app.models.search_history import SearchHistory
from app.models.conversation import Message
from app.schemas.search_history import (
    SearchHistoryInfo, SearchHistoryListResponse, SearchHistoryDetailResponse
)
from app.services.auth import get_current_user

router = APIRouter(prefix="/search-history", tags=["search-history"])


@router.get("", response_model=SearchHistoryListResponse)
async def list_search_history(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    keyword: str = Query(default="", description="按问题关键词搜索"),
    decision: str = Query(default="", description="按检索决策过滤: proceed/retry/fallback"),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """
    获取当前用户的检索历史列表（分页）。
    支持按关键词模糊搜索和按检索决策过滤。
    """
    # 构建基础查询
    base_q = select(SearchHistory).where(SearchHistory.user_id == user.id)

    if keyword:
        base_q = base_q.where(SearchHistory.question.ilike(f"%{keyword}%"))
    if decision:
        base_q = base_q.where(SearchHistory.retrieval_decision == decision)

    # 总数
    count_q = select(func.count()).select_from(base_q.subquery())
    total = await session.scalar(count_q) or 0

    # 分页查询（按时间倒序）
    offset = (page - 1) * page_size
    query = (
        base_q
        .order_by(SearchHistory.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    result = await session.execute(query)
    records = result.scalars().all()

    items = [
        SearchHistoryInfo(
            id=r.id,
            question=r.question,
            answer=r.answer,
            retrieval_decision=r.retrieval_decision,
            decision_reason=r.decision_reason,
            sources=r.sources,
            context_count=r.context_count,
            response_time_ms=r.response_time_ms,
            rating=r.rating,
            is_favorited=r.is_favorited,
            created_at=r.created_at.isoformat() if r.created_at else None,
        )
        for r in records
    ]

    return SearchHistoryListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{record_id}", response_model=SearchHistoryDetailResponse)
async def get_search_history_detail(
    record_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """获取单条检索历史的完整详情（包括搜索结果内容）"""
    result = await session.execute(
        select(SearchHistory).where(
            SearchHistory.id == record_id,
            SearchHistory.user_id == user.id,
        )
    )
    r = result.scalar_one_or_none()
    if not r:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="记录不存在")

    return SearchHistoryDetailResponse(
        id=r.id,
        question=r.question,
        answer=r.answer,
        retrieval_decision=r.retrieval_decision,
        decision_reason=r.decision_reason,
        sources=r.sources,
        search_results=r.search_results,
        context_count=r.context_count,
        response_time_ms=r.response_time_ms,
        rating=r.rating,
        is_favorited=r.is_favorited,
        created_at=r.created_at.isoformat() if r.created_at else None,
    )


@router.delete("/{record_id}")
async def delete_search_history_record(
    record_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """删除单条检索历史记录"""
    result = await session.execute(
        select(SearchHistory).where(
            SearchHistory.id == record_id,
            SearchHistory.user_id == user.id,
        )
    )
    r = result.scalar_one_or_none()
    if not r:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="记录不存在")

    await session.delete(r)
    return {"message": "删除成功"}


@router.delete("")
async def clear_search_history(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """清空当前用户的所有检索历史记录"""
    await session.execute(
        delete(SearchHistory).where(SearchHistory.user_id == user.id)
    )
    return {"message": "已清空所有检索历史"}
