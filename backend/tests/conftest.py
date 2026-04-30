"""
pytest 全局配置和共享 Fixtures
为所有测试提供数据库，会话、测试客户端等基础设施。
"""

import asyncio
import os
import sys
from pathlib import Path

import pytest
from httpx import AsyncClient, ASGITransport

# 将 backend 根目录加入 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

# ─────────────────────────────────────────────────────────────────────────────
# 测试环境变量（覆盖 .env，避免连接真实数据库）
# ─────────────────────────────────────────────────────────────────────────────
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-for-testing-only")
# 注意：不覆盖 DATABASE_URL，让 get_settings() 读取 .env
# test_db fixture 会独立创建测试引擎


# ─────────────────────────────────────────────────────────────────────────────
# 测试配置常量
# ─────────────────────────────────────────────────────────────────────────────
TEST_JWT_SECRET = "test-jwt-secret-for-testing-only"


# ─────────────────────────────────────────────────────────────────────────────
# 事件循环 Fixture
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def event_loop():
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


# ─────────────────────────────────────────────────────────────────────────────
# 数据库 Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="function")
async def test_db(event_loop):
    """独立的测试数据库会话"""
    import tempfile, os
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
    from sqlalchemy.pool import StaticPool
    from app.database import Base
    # 重要：必须在此处导入所有模型，否则 create_all 看不到表定义
    from app.models.user import User
    from app.models.conversation import Conversation, Message

    _tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    _tmp.close()
    _tmp_path = _tmp.name

    test_engine = create_async_engine(
        f"sqlite+aiosqlite:///{_tmp_path}",
        echo=False,
        future=True,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )

    # 创建所有表
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )

    async with session_factory() as session:
        yield session
        await session.rollback()

    await test_engine.dispose()
    try:
        os.unlink(_tmp_path)
    except OSError:
        pass


@pytest.fixture(scope="function")
async def db_with_data(test_db):
    """预置数据的数据库会话"""
    from app.models.user import User
    from app.models.conversation import Conversation, Message
    from app.services.auth import hash_password

    user_a = User(
        username="alice", password_hash=hash_password("password123"),
        real_name="Alice Smith", email="alice@test.com", role="user", is_active=True,
    )
    user_b = User(
        username="bob", password_hash=hash_password("password456"),
        real_name="Bob Jones", email="bob@test.com", role="user", is_active=True,
    )
    admin = User(
        username="admin", password_hash=hash_password("admin123"),
        real_name="Admin User", email="admin@test.com", role="admin", is_active=True,
    )
    disabled = User(
        username="disabled_user", password_hash=hash_password("disabled999"),
        real_name="Disabled User", email="disabled@test.com", role="user", is_active=False,
    )
    test_db.add_all([user_a, user_b, admin, disabled])
    await test_db.flush()

    conv = Conversation(user_id=user_a.id, title="青光眼相关问题")
    test_db.add(conv)
    await test_db.flush()

    msg1 = Message(conversation_id=conv.id, role="user", content="青光眼有哪些症状？")
    msg2 = Message(
        conversation_id=conv.id, role="assistant",
        content="青光眼的主要症状包括视野缺损和眼压升高。",
        sources=[{"title": "Glaucoma.txt", "score": 0.85}],
    )
    test_db.add_all([msg1, msg2])
    await test_db.commit()

    class Data:
        pass

    d = Data()
    d.user_a = user_a
    d.user_b = user_b
    d.admin = admin
    d.disabled = disabled
    d.conversation = conv
    d.message_1 = msg1
    d.message_2 = msg2
    d.session = test_db
    return d


# ─────────────────────────────────────────────────────────────────────────────
# Token Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
async def valid_tokens(db_with_data):
    """生成各角色的有效 JWT token"""
    from app.services.auth import create_access_token
    from app.config import get_settings

    settings = get_settings()
    original = settings.jwt_secret_key
    settings.jwt_secret_key = TEST_JWT_SECRET

    tokens = {
        "alice": create_access_token({"sub": str(db_with_data.user_a.id)}),
        "bob": create_access_token({"sub": str(db_with_data.user_b.id)}),
        "admin": create_access_token({"sub": str(db_with_data.admin.id)}),
    }

    settings.jwt_secret_key = original
    return tokens


# ─────────────────────────────────────────────────────────────────────────────
# FastAPI Test Client
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="function")
async def client(db_with_data):
    """FastAPI 异步测试客户端"""
    from app.main import app
    from app.database import get_db

    # Mock SelfRAGAgent，避免真实加载 ChromaDB 和 LLM
    async def mock_stream():
        for char in "这是模拟的回答内容":
            yield char

    class MockSelfRAG:
        async def query_stream(self, *args, **kwargs):
            return mock_stream(), [
                {"title": "test.txt", "score": 0.9, "content": "测试检索结果"}
            ], "proceed", []

        async def query(self, *args, **kwargs):
            return {
                "answer": "这是模拟的回答内容",
                "sources": [{"title": "test.txt", "score": 0.9}],
                "sources_formatted": [],
                "context_count": 1,
            }

    import app.api.chat as chat_module
    import app.rag.self_rag as selfrag_module
    # 保存原始函数
    original_fn = selfrag_module.get_self_rag_agent
    # 替换 chat.py 中的引用（chat.py 已导入了该函数）
    chat_module.get_self_rag_agent = lambda: MockSelfRAG()

    async def _override_get_db():
        yield db_with_data.session

    app.dependency_overrides[get_db] = _override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    # 恢复原始函数
    chat_module.get_self_rag_agent = original_fn
    app.dependency_overrides.clear()


# ─────────────────────────────────────────────────────────────────────────────
# Mock Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_vector_store():
    """Mock VectorStore"""
    class MockVS:
        def __init__(self):
            self.collection = type(
                "M", (), {
                    "count": lambda self: 100,
                    "get": lambda *a, **k: {"ids": [], "documents": [], "metadatas": []},
                    "query": lambda *a, **k: {
                        "ids": [[f"id-{i}" for i in range(5)]],
                        "documents": [["模拟文档内容"] * 5],
                        "metadatas": [[{"file_name": "test.txt"}] * 5],
                        "distances": [[0.1 * i for i in range(5)]],
                    },
                }
            )()
            self._added_chunks = []

        def search(self, query, top_k=5, filter_metadata=None):
            return [
                {"content": f"关于青光眼 {i}", "metadata": {"file_name": "test.txt"},
                 "score": round(0.9 - i * 0.1, 4), "id": f"mock-{i}"}
                for i in range(min(top_k, 5))
            ]

        def add_documents(self, chunks):
            self._added_chunks.extend(chunks)
            return len(chunks)

        def delete_by_source(self, file_name):
            return 0

        def get_stats(self):
            return {"total_chunks": 100, "document_count": 5,
                    "total_documents": 5, "collection_name": "test"}

        def list_documents(self):
            return [{"file_name": "test.txt", "source": "pmc",
                     "file_type": "txt", "chunk_count": 20}]

    return MockVS()
