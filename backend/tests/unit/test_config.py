"""
配置模块单元测试
验证配置加载、环境变量解析、默认值等

使用环境变量隔离测试，不依赖 .env 文件。
"""

import pytest
import os


class TestSettingsDefaults:
    """测试配置默认值（通过环境变量覆盖）"""

    def test_default_values_from_env(self):
        """测试 Settings 从环境变量读取配置"""
        # 保存原环境变量
        orig = os.environ.get("JWT_SECRET_KEY")

        try:
            os.environ["JWT_SECRET_KEY"] = "custom-test-key"
            os.environ["JWT_ALGORITHM"] = "HS512"
            os.environ["JWT_EXPIRE_MINUTES"] = "120"
            os.environ["RETRIEVAL_TOP_K"] = "7"

            # 清除缓存
            from app.config import get_settings
            get_settings.cache_clear()

            from app.config import Settings
            s = Settings()

            assert s.jwt_secret_key == "custom-test-key"
            assert s.jwt_algorithm == "HS512"
            assert s.jwt_expire_minutes == 120
            assert s.retrieval_top_k == 7
        finally:
            if orig is None:
                os.environ.pop("JWT_SECRET_KEY", None)
            else:
                os.environ["JWT_SECRET_KEY"] = orig
            os.environ.pop("JWT_ALGORITHM", None)
            os.environ.pop("JWT_EXPIRE_MINUTES", None)
            os.environ.pop("RETRIEVAL_TOP_K", None)
            from app.config import get_settings
            get_settings.cache_clear()

    def test_chroma_http_mode(self):
        """测试 ChromaDB HTTP 模式配置"""
        orig_host = os.environ.get("CHROMA_HOST")
        orig_port = os.environ.get("CHROMA_PORT")

        try:
            os.environ["CHROMA_HOST"] = "192.168.1.100"
            os.environ["CHROMA_PORT"] = "8080"
            os.environ["CHROMA_COLLECTION_NAME"] = "my_custom_collection"

            from app.config import get_settings
            get_settings.cache_clear()

            from app.config import Settings
            s = Settings()

            assert s.chroma_host == "192.168.1.100"
            assert s.chroma_port == 8080
            assert s.chroma_collection_name == "my_custom_collection"
        finally:
            if orig_host is None:
                os.environ.pop("CHROMA_HOST", None)
            else:
                os.environ["CHROMA_HOST"] = orig_host
            if orig_port is None:
                os.environ.pop("CHROMA_PORT", None)
            else:
                os.environ["CHROMA_PORT"] = orig_port
            os.environ.pop("CHROMA_COLLECTION_NAME", None)
            from app.config import get_settings
            get_settings.cache_clear()

    def test_llm_provider_deepseek(self):
        """测试 DeepSeek LLM 配置"""
        orig = os.environ.get("LLM_PROVIDER")

        try:
            os.environ["LLM_PROVIDER"] = "deepseek"
            os.environ["LLM_API_KEY"] = "sk-test-deepseek"

            from app.config import get_settings
            get_settings.cache_clear()

            from app.config import Settings
            s = Settings()

            assert s.llm_provider == "deepseek"
            assert s.llm_api_key == "sk-test-deepseek"
            assert "deepseek" in s.llm_api_base_url
        finally:
            if orig is None:
                os.environ.pop("LLM_PROVIDER", None)
            else:
                os.environ["LLM_PROVIDER"] = orig
            os.environ.pop("LLM_API_KEY", None)
            from app.config import get_settings
            get_settings.cache_clear()

    def test_llm_provider_minimax(self):
        """测试 MiniMax LLM 配置"""
        orig = os.environ.get("LLM_PROVIDER")

        try:
            os.environ["LLM_PROVIDER"] = "minimax"
            os.environ["MINIMAX_API_KEY"] = "minimax-test-key"

            from app.config import get_settings
            get_settings.cache_clear()

            from app.config import Settings
            s = Settings()

            assert s.llm_provider == "minimax"
            assert s.minimax_api_key == "minimax-test-key"
        finally:
            if orig is None:
                os.environ.pop("LLM_PROVIDER", None)
            else:
                os.environ["LLM_PROVIDER"] = orig
            os.environ.pop("MINIMAX_API_KEY", None)
            from app.config import get_settings
            get_settings.cache_clear()

    def test_embedding_biobert(self):
        """测试 BioBERT 嵌入模型配置"""
        orig_name = os.environ.get("EMBEDDING_MODEL_NAME")
        orig_biobert = os.environ.get("USE_BIOBERT")

        try:
            os.environ["USE_BIOBERT"] = "true"
            os.environ["EMBEDDING_MODEL_NAME"] = "dmis-lab/biobert-base-chinese-v1.2"

            from app.config import get_settings
            get_settings.cache_clear()

            from app.config import Settings
            s = Settings()

            assert s.use_biobert is True
            assert "biobert" in s.biobert_model_name
        finally:
            if orig_name is None:
                os.environ.pop("EMBEDDING_MODEL_NAME", None)
            else:
                os.environ["EMBEDDING_MODEL_NAME"] = orig_name
            if orig_biobert is None:
                os.environ.pop("USE_BIOBERT", None)
            else:
                os.environ["USE_BIOBERT"] = orig_biobert
            from app.config import get_settings
            get_settings.cache_clear()

    def test_rag_config(self):
        """测试 RAG 相关配置"""
        orig_size = os.environ.get("CHUNK_SIZE")
        orig_overlap = os.environ.get("CHUNK_OVERLAP")

        try:
            os.environ["CHUNK_SIZE"] = "1024"
            os.environ["CHUNK_OVERLAP"] = "128"

            from app.config import get_settings
            get_settings.cache_clear()

            from app.config import Settings
            s = Settings()

            assert s.chunk_size == 1024
            assert s.chunk_overlap == 128
        finally:
            if orig_size is None:
                os.environ.pop("CHUNK_SIZE", None)
            else:
                os.environ["CHUNK_SIZE"] = orig_size
            if orig_overlap is None:
                os.environ.pop("CHUNK_OVERLAP", None)
            else:
                os.environ["CHUNK_OVERLAP"] = orig_overlap
            from app.config import get_settings
            get_settings.cache_clear()

    def test_get_settings_singleton(self):
        """测试 get_settings 使用 LRU 缓存"""
        from app.config import get_settings

        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2  # 同一对象

        get_settings.cache_clear()
        s3 = get_settings()
        assert s1 is not s3  # 缓存清除后新建


class TestSettingsValidation:
    """配置值类型验证"""

    def test_retrieval_top_k_positive(self):
        """RETRIEVAL_TOP_K 应为正整数"""
        from app.config import Settings

        s = Settings()
        assert isinstance(s.retrieval_top_k, int)
        assert s.retrieval_top_k > 0

    def test_jwt_expire_positive(self):
        """JWT_EXPIRE_MINUTES 应为正数"""
        from app.config import Settings

        s = Settings()
        assert isinstance(s.jwt_expire_minutes, int)
        assert s.jwt_expire_minutes > 0

    def test_database_url_format(self):
        """DATABASE_URL 应包含数据库类型"""
        from app.config import Settings

        s = Settings()
        # 应为 mysql+aiomysql 或 sqlite+aiosqlite
        assert "mysql" in s.database_url or "sqlite" in s.database_url

    def test_app_name_and_version(self):
        """应用名称和版本应正确"""
        from app.config import Settings

        s = Settings()
        assert len(s.app_name) > 0
        assert len(s.app_version) > 0
