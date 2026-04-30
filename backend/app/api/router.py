"""
API 路由注册
"""

from fastapi import APIRouter
from app.api import knowledge as knowledge_router
from app.api import chat as chat_router
from app.api import auth as auth_router
from app.api import feedback as feedback_router
from app.api import favorites as favorites_router
from app.api import stats as stats_router
from app.api import search_history as search_history_router
from app.api import admin as admin_router

router = APIRouter(prefix="/api")

# 注册子路由
router.include_router(knowledge_router.router)
router.include_router(chat_router.router)
router.include_router(auth_router.router)
router.include_router(feedback_router.router)
router.include_router(favorites_router.router)
router.include_router(stats_router.router)
router.include_router(search_history_router.router)
router.include_router(admin_router.router)


@router.get("/health")
async def health_check():
    """健康检查端点"""
    from app.config import get_settings
    settings = get_settings()
    return {
        "status": "ok",
        "version": settings.app_version,
        "app_name": settings.app_name,
    }
