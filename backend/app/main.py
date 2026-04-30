"""
眼科医疗知识问答系统 - FastAPI 应用入口
"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings
from app.database import init_db, close_db
from app.api.router import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    from app.utils.logger import logger
    # 导入所有 Model，确保 metadata 完整后再 create_all
    import app.models  # noqa: F401

    settings = get_settings()
    logger.info(f"🚀 启动 {settings.app_name} v{settings.app_version}")

    # 确保数据目录存在
    os.makedirs("data", exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    os.makedirs("chroma_db", exist_ok=True)
    os.makedirs("data/documents", exist_ok=True)

    # 初始化数据库（自动建表）
    await init_db()
    logger.info("✅ 数据库初始化完成")

    yield

    # 关闭时
    await close_db()
    logger.info("🛑 应用已关闭")


def create_app() -> FastAPI:
    """创建 FastAPI 应用实例"""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="基于RAG (Retrieval-Augmented Generation) 的眼科医疗知识智能问答系统",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # CORS 中间件
    # Flutter Web 开发服务器端口随机分配，debug 模式允许所有来源
    # 注意：allow_origins=["*"] 时 allow_credentials 必须为 False（浏览器规范）
    # JWT 通过 Authorization header 传递，不依赖 Cookie，所以不影响认证
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.debug else [
            "http://localhost:5173",
            "http://localhost:3000",
            "http://127.0.0.1:5173",
            "http://127.0.0.1:3000",
        ],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 注册路由
    app.include_router(router)

    return app


app = create_app()
