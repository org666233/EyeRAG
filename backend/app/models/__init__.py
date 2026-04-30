# 导入所有模型，确保 SQLAlchemy 元数据注册完整
from app.models.user import User
from app.models.conversation import Conversation, Message
from app.models.feedback import Feedback
from app.models.favorite import Favorite
from app.models.search_history import SearchHistory
from app.models.doc_stats import DocStats

__all__ = ["User", "Conversation", "Message", "Feedback", "Favorite", "SearchHistory", "DocStats"]
