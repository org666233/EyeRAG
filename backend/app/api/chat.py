"""
聊天 API 路由
功能: SSE 流式问答 + MySQL 持久化 + 用户鉴权 + 相关问题推荐
"""

import json
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.user import User
from app.models.conversation import Conversation, Message
from app.models.search_history import SearchHistory
from app.models.doc_stats import DocStats
from app.schemas.chat import ChatRequest, ChatResponse, SourceInfo
from app.rag.self_rag import get_self_rag_agent
from app.services.auth import get_current_user
from app.utils.logger import logger

router = APIRouter(prefix="/chat", tags=["chat"])


# ─────────────────────────────────────────────────────────────
# 核心问答接口
# ─────────────────────────────────────────────────────────────

@router.post("/completions")
async def chat_completions(
    request: ChatRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """
    核心问答接口（需登录）。
    stream=True  → SSE 流式响应
    stream=False → 完整 JSON 响应
    """
    self_rag = get_self_rag_agent()

    # 获取或新建会话
    conv = await _get_or_create_conversation(session, user.id, request.conversation_id, request.question)

    # 取最近 10 条消息作为多轮上下文
    result = await session.execute(
        select(Message)
        .where(Message.conversation_id == conv.id)
        .order_by(Message.created_at.desc())
        .limit(10)
    )
    recent_messages = list(reversed(result.scalars().all()))
    chat_history = [{"role": m.role, "content": m.content} for m in recent_messages]

    if request.stream:
        return await _stream_response(self_rag, request, conv, chat_history)
    else:
        return await _sync_response(self_rag, request, conv, chat_history, session)


# ─────────────────────────────────────────────────────────────
# 消息持久化接口（由前端流结束后显式调用，避免重复）
# ─────────────────────────────────────────────────────────────

@router.post("/messages")
async def save_messages(
    payload: dict,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """
    保存问答消息对（由前端在流式回答完成后显式调用）。
    同时写入 message 表、SearchHistory 表、DocStats（命中统计）。
    """
    import time
    t0 = time.time()

    conv_id = payload.get("conversation_id")
    question = payload.get("question", "")
    answer = payload.get("answer", "")
    sources = payload.get("sources", [])
    retrieval_decision = payload.get("retrieval_decision", "proceed")
    search_results = payload.get("search_results", [])
    context_count = payload.get("context_count", 0)
    response_time_ms = payload.get("response_time_ms", 0)

    # 获取会话
    conv = None
    if conv_id:
        result = await session.execute(
            select(Conversation).where(
                Conversation.id == conv_id,
                Conversation.user_id == user.id,
            )
        )
        conv = result.scalar_one_or_none()

    # 无会话时自动创建
    if not conv:
        conv = Conversation(
            user_id=user.id,
            title=question[:30].strip() or "新对话",
        )
        session.add(conv)
        await session.flush()

    # 写入消息
    user_msg = Message(conversation_id=conv.id, role="user", content=question)
    assistant_msg = Message(
        conversation_id=conv.id,
        role="assistant",
        content=answer,
        sources=sources,
    )
    session.add(user_msg)
    session.add(assistant_msg)
    conv.updated_at = datetime.now()

    # 写入检索历史
    history = SearchHistory(
        user_id=user.id,
        conversation_id=conv.id,
        question=question,
        answer=answer,
        retrieval_decision=retrieval_decision,
        sources=sources,
        search_results=search_results,
        context_count=context_count,
        response_time_ms=response_time_ms,
    )
    session.add(history)

    # 更新文档命中统计（DocStats）
    if sources:
        for src in sources:
            title = src.get("title", "")
            if not title or title == "未知来源":
                continue
            result = await session.execute(
                select(DocStats).where(DocStats.file_name == title)
            )
            stats = result.scalar_one_or_none()
            if not stats:
                stats = DocStats(file_name=title, view_count=0, hit_count=0)
                session.add(stats)
            stats.hit_count += 1

    await session.commit()
    return {"conversation_id": conv.id, "message_id": assistant_msg.id}


async def _get_or_create_conversation(
    session: AsyncSession,
    user_id: int,
    conv_id: Optional[int],
    question: str,
) -> Conversation:
    """获取已有会话或新建会话"""
    if conv_id:
        result = await session.execute(
            select(Conversation).where(
                Conversation.id == conv_id,
                Conversation.user_id == user_id,
            )
        )
        conv = result.scalar_one_or_none()
        if conv:
            return conv

    # 新建会话，以问题前 30 字为标题
    conv = Conversation(
        user_id=user_id,
        title=question[:30].strip() or "新对话",
    )
    session.add(conv)
    await session.flush()  # 获取自增 id
    return conv


async def _sync_response(pipeline, request: ChatRequest, conv: Conversation, chat_history: list, session: AsyncSession):
    """非流式响应"""
    import time
    t0 = time.time()
    result = await pipeline.query(
        question=request.question,
        top_k=request.top_k,
        chat_history=chat_history if chat_history else None,
    )

    # 持久化消息到 MySQL
    user_msg = Message(conversation_id=conv.id, role="user", content=request.question)
    assistant_msg = Message(
        conversation_id=conv.id,
        role="assistant",
        content=result["answer"],
        sources=result.get("sources", []),
    )
    session.add(user_msg)
    session.add(assistant_msg)
    conv.updated_at = datetime.now()
    await session.flush()

    # 记录检索历史
    history = SearchHistory(
        user_id=conv.user_id,
        conversation_id=conv.id,
        question=request.question,
        answer=result["answer"],
        retrieval_decision="proceed",
        sources=result.get("sources", []),
        context_count=result.get("context_count", 0),
        response_time_ms=round((time.time() - t0) * 1000, 1),
    )
    session.add(history)

    return ChatResponse(
        answer=result["answer"],
        sources=[SourceInfo(**s) for s in result.get("sources", [])],
        query=result["query"],
        conversation_id=conv.id,
        context_count=result.get("context_count", 0),
    )


async def _stream_response(pipeline, request: ChatRequest, conv: Conversation, chat_history: list):
    """SSE 流式响应（仅负责流式输出，数据持久化由前端显式调用 /chat/messages 接口）"""
    import time
    t0 = time.time()
    stream, sources, retrieval_decision, search_results = await pipeline.query_stream(
        question=request.question,
        top_k=request.top_k,
        chat_history=chat_history if chat_history else None,
    )

    conv_id = conv.id
    question = request.question

    async def event_generator():
        t_start = time.time()

        # 先推送来源信息、conversation_id 和检索决策
        sources_data = [SourceInfo(**s).model_dump() for s in sources]
        # 序列化 search_results（截断避免过大）
        sr_serializable = [
            {
                "content": (sr.get("content") or "")[:300],
                "metadata": sr.get("metadata", {}),
                "rrf_score": sr.get("rrf_score", 0),
                "retrieval_type": sr.get("retrieval_type", ""),
            }
            for sr in (search_results or [])
        ]
        sources_payload = json.dumps({
            "type": "sources",
            "sources": sources_data,
            "conversation_id": conv_id,
            "retrieval_decision": retrieval_decision,
            "search_results": sr_serializable,
            "context_count": len(sources),
        }, ensure_ascii=False)
        yield f"data: {sources_payload}\n\n"

        # 逐字流式推送回答
        full_answer = []
        async for chunk in stream:
            full_answer.append(chunk)
            content_payload = json.dumps(
                {"type": "content", "content": chunk}, ensure_ascii=False
            )
            yield f"data: {content_payload}\n\n"

        complete_answer = "".join(full_answer)
        response_ms = round((time.time() - t_start) * 1000, 1)

        # 生成相关问题推荐
        related = await _generate_related_questions(question, complete_answer)

        # done 事件携带完整元数据，前端据此调用 /messages 接口保存
        done_payload = json.dumps({
            "type": "done",
            "content": complete_answer,
            "response_time_ms": response_ms,
        }, ensure_ascii=False)
        yield f"data: {done_payload}\n\n"

        related_payload = json.dumps(
            {"type": "related", "questions": related}, ensure_ascii=False
        )
        yield f"data: {related_payload}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


async def _generate_related_questions(question: str, answer: str) -> list[str]:
    """调用 LLM 生成 3 个相关后续问题"""
    try:
        from app.rag.llm_client import generate
        prompt = [
            {
                "role": "system",
                "content": (
                    "你是眼科医学助手。根据用户的问题和回答，生成3个用户可能感兴趣的后续眼科问题。"
                    "只输出问题本身，每行一个，不要编号，不要任何其他内容。"
                ),
            },
            {
                "role": "user",
                "content": f"原问题: {question}\n\n回答摘要: {answer[:300]}",
            },
        ]
        raw = await generate(messages=prompt, temperature=0.7, max_tokens=200)
        questions = [q.strip() for q in raw.strip().split("\n") if q.strip()]
        return questions[:3]
    except Exception as e:
        logger.warning(f"生成相关问题失败: {e}")
        return []


# ─────────────────────────────────────────────────────────────
# 会话管理接口
# ─────────────────────────────────────────────────────────────

@router.get("/conversations")
async def list_conversations(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """获取当前用户的所有会话（按最近更新排序）"""
    result = await session.execute(
        select(Conversation)
        .where(Conversation.user_id == user.id)
        .order_by(Conversation.updated_at.desc())
    )
    convs = result.scalars().all()
    return [
        {
            "id": c.id,
            "title": c.title,
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "updated_at": c.updated_at.isoformat() if c.updated_at else None,
        }
        for c in convs
    ]


@router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """获取单个会话的完整消息记录"""
    result = await session.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == user.id,
        )
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="会话不存在")

    msg_result = await session.execute(
        select(Message)
        .where(Message.conversation_id == conv.id)
        .order_by(Message.created_at.asc())
    )
    messages = msg_result.scalars().all()

    return {
        "id": conv.id,
        "title": conv.title,
        "created_at": conv.created_at.isoformat() if conv.created_at else None,
        "messages": [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "sources": m.sources or [],
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in messages
        ],
    }


@router.patch("/conversations/{conversation_id}/title")
async def update_conversation_title(
    conversation_id: int,
    payload: dict,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """修改会话标题"""
    result = await session.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == user.id,
        )
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="会话不存在")
    conv.title = payload.get("title", conv.title)[:50]
    return {"id": conv.id, "title": conv.title}


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """删除会话（级联删除所有消息）"""
    result = await session.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == user.id,
        )
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="会话不存在")

    await session.delete(conv)
    return {"message": "会话已删除"}
