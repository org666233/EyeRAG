"""
眼科医疗知识问答系统 - 配置管理
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
from functools import lru_cache


class Settings(BaseSettings):
    """应用全局配置，从 .env 文件读取"""

    # Application
    app_name: str = Field(default="眼科医疗知识问答系统", alias="APP_NAME")
    app_version: str = Field(default="1.0.0", alias="APP_VERSION")
    debug: bool = Field(default=True, alias="DEBUG")

    # Server
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8000, alias="PORT")

    # Database - MySQL
    database_url: str = Field(
        default="sqlite+aiosqlite:///./data/ophtha_qa.db",
        alias="DATABASE_URL"
    )

    # JWT Authentication
    jwt_secret_key: str = Field(
        default="dev-secret-key-change-in-production",
        alias="JWT_SECRET_KEY"
    )
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    jwt_expire_minutes: int = Field(default=1440, alias="JWT_EXPIRE_MINUTES")

    # LLM Provider 选择: "deepseek" 或 "minimax"
    llm_provider: str = Field(default="deepseek", alias="LLM_PROVIDER")

    # DeepSeek LLM API
    llm_api_key: str = Field(default="", alias="LLM_API_KEY")
    llm_api_base_url: str = Field(
        default="https://api.deepseek.com/v1",
        alias="LLM_API_BASE_URL"
    )
    llm_model_name: str = Field(default="deepseek-chat", alias="LLM_MODEL_NAME")

    # MiniMax LLM API（Anthropic SDK 兼容）
    minimax_api_key: str = Field(default="", alias="MINIMAX_API_KEY")
    minimax_api_base_url: str = Field(
        default="https://api.minimaxi.com/anthropic",
        alias="MINIMAX_API_BASE_URL"
    )
    minimax_model_name: str = Field(default="MiniMax-M2.7", alias="MINIMAX_MODEL_NAME")

    # Embedding Model
    embedding_model_name: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        alias="EMBEDDING_MODEL_NAME"
    )
    embedding_model_path: Optional[str] = Field(
        default=None,
        alias="EMBEDDING_MODEL_PATH"
    )
    # BioBERT 中文生物医学模型
    use_biobert: bool = Field(
        default=False,
        alias="USE_BIOBERT"
    )
    biobert_model_name: str = Field(
        default="dmis-lab/biobert-base-chinese-v1.2",
        alias="BIOBERT_MODEL_NAME"
    )

    # ChromaDB - 支持两种模式:
    #   HTTP 模式（推荐，Docker运行时）: 设置 CHROMA_HOST
    #   本地持久化模式（无Docker时）: 设置 CHROMA_PERSIST_DIR
    chroma_host: Optional[str] = Field(default=None, alias="CHROMA_HOST")
    chroma_port: int = Field(default=8011, alias="CHROMA_PORT")
    chroma_persist_dir: str = Field(default="./chroma_db", alias="CHROMA_PERSIST_DIR")
    chroma_collection_name: str = Field(
        default="ophthalmology_docs",
        alias="CHROMA_COLLECTION_NAME"
    )

    # RAG Settings
    chunk_size: int = Field(default=512, alias="CHUNK_SIZE")
    chunk_overlap: int = Field(default=50, alias="CHUNK_OVERLAP")
    retrieval_top_k: int = Field(default=5, alias="RETRIEVAL_TOP_K")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "populate_by_name": True,
        "extra": "ignore",
    }


@lru_cache()
def get_settings() -> Settings:
    """获取全局配置单例"""
    return Settings()
