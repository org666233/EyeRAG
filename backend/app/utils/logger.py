"""
眼科医疗知识问答系统 - 日志工具
"""

import sys
from loguru import logger
from app.config import get_settings

settings = get_settings()

# 移除默认 handler
logger.remove()

# 控制台输出
logger.add(
    sys.stdout,
    level="DEBUG" if settings.debug else "INFO",
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    colorize=True,
)

# 文件输出
logger.add(
    "logs/app_{time:YYYY-MM-DD}.log",
    level="INFO",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    rotation="00:00",       # 每天轮转
    retention="7 days",     # 保留 7 天
    compression="zip",      # 压缩旧日志
    encoding="utf-8",
)
