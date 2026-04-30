"""
眼科医疗知识问答系统 - 数据库连接管理
"""

from __future__ import annotations
from typing import TYPE_CHECKING
from typing import Optional
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """SQLAlchemy 声明式基类"""
    pass


# ─── 懒加载引擎（避免测试时直接连接 MySQL）───────────────────────────────

_engine = None
_async_session = None


def _get_engine():
    """延迟创建数据库引擎（仅在首次调用时初始化）"""
    global _engine
    if _engine is None:
        from app.config import get_settings
        settings = get_settings()
        _engine = create_async_engine(
            settings.database_url,
            echo=settings.debug,
            future=True,
            pool_pre_ping=True,
            pool_recycle=3600,
        )
    return _engine


def _get_session_factory():
    """延迟创建会话工厂"""
    global _async_session
    if _async_session is None:
        _async_session = async_sessionmaker(
            _get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _async_session


# ─── 为测试提供的可覆盖入口 ────────────────────────────────────────────

_test_engine = None
_test_session_factory = None


def set_test_engine(engine):
    """测试时替换数据库引擎（由 conftest.py 调用）"""
    global _test_engine, _test_session_factory, _engine, _async_session
    _test_engine = engine
    _test_session_factory = None  # 强制重建


def set_test_session_factory(factory):
    """测试时替换会话工厂（由 conftest.py 调用）"""
    global _test_session_factory
    _test_session_factory = factory


async def get_db() -> AsyncSession:
    """FastAPI 依赖注入：获取数据库会话"""
    factory = _test_session_factory or _get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """初始化数据库：创建所有表"""
    async with _get_engine().begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    """关闭数据库连接"""
    if _test_engine:
        await _test_engine.dispose()
    else:
        engine = _get_engine()
        await engine.dispose()
        global _engine, _async_session
        _engine = None
        _async_session = None
