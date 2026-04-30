"""
嵌入模型封装
支持三种模式切换:
  1. 通用模型: sentence-transformers/all-MiniLM-L6-v2
  2. 中文 BioBERT: dmis-lab/biobert-base-chinese-v1.2
  3. 本地 BERT 模型: ./model (BGE 等)
"""

from typing import Optional, Any
import torch
import numpy as np
from app.config import get_settings
from app.utils.logger import logger

settings = get_settings()

# 全局嵌入模型实例
_embedding_model: Optional[Any] = None
_embedding_model_name: Optional[str] = None
_embedding_model_type: Optional[str] = None  # "sentence_transformers" or "bert"


def get_embedding_model():
    """
    获取嵌入模型全局单例（懒加载）。

    加载优先级:
      1. 本地 BERT 模型 (EMBEDDING_MODEL_PATH) - 最高优先级
      2. BioBERT 模型 (USE_BIOBERT=true)
      3. 通用模型 (默认)
    """
    global _embedding_model, _embedding_model_name, _embedding_model_type

    # 确定使用哪个模型
    if settings.embedding_model_path and settings.embedding_model_path.strip():
        model_path = settings.embedding_model_path.strip()
        model_name = model_path
        model_type = "bert"
    elif settings.use_biobert:
        model_name = settings.biobert_model_name
        model_type = "sentence_transformers"
    else:
        model_name = settings.embedding_model_name
        model_type = "sentence_transformers"

    # 如果模型没变，直接返回缓存
    if _embedding_model is not None and _embedding_model_name == model_name:
        return _embedding_model

    if model_type == "bert":
        # 使用 transformers 直接加载本地 BERT 模型
        logger.info(f"加载本地 BERT 模型: {model_name}")
        from transformers import BertTokenizer, AutoModel

        # 优先尝试 BertTokenizer（更稳定的慢速 tokenizer）
        # transformers 5.x 的 AutoTokenizer 可能因 tokenizers 库版本问题
        # 无法自动转换慢速 tokenizer 为 fast 版本
        try:
            tokenizer = BertTokenizer.from_pretrained(model_path)
        except Exception:
            from transformers import AutoTokenizer
            tokenizer = AutoTokenizer.from_pretrained(model_path, use_fast=False)
        model = AutoModel.from_pretrained(model_path)

        _embedding_model = {
            "tokenizer": tokenizer,
            "model": model,
            "hidden_size": model.config.hidden_size
        }
        logger.info(f"✅ 本地 BERT 模型加载完成 (维度: {_embedding_model['hidden_size']})")
    else:
        # 使用 sentence-transformers
        from sentence_transformers import SentenceTransformer

        logger.info(f"加载 SentenceTransformer 模型: {model_name} (类型: {model_type})")
        _embedding_model = SentenceTransformer(model_name)
        logger.info(f"✅ 模型加载完成 (维度: {_embedding_model.get_sentence_embedding_dimension()})")

    _embedding_model_name = model_name
    _embedding_model_type = model_type

    return _embedding_model


def _mean_pooling(model_output: Any, attention_mask: torch.Tensor) -> torch.Tensor:
    """Mean Pooling - 对 token embeddings 做平均"""
    token_embeddings = model_output[0]  # Shape: (batch_size, seq_len, hidden_size)
    input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
    return torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(input_mask_expanded.sum(1), min=1e-9)


def embed_texts(texts: list[str]) -> list[list[float]]:
    """将文本列表转换为嵌入向量列表"""
    model = get_embedding_model()
    total = len(texts)

    if total > 100:
        logger.info(f"开始向量化 {total} 个文本...")

    if _embedding_model_type == "bert":
        # 本地 BERT 模型
        tokenizer = model["tokenizer"]
        bert_model = model["model"]

        # 分批处理
        batch_size = 32
        all_embeddings = []
        processed = 0

        for i in range(0, total, batch_size):
            batch = texts[i:i + batch_size]
            encoded = tokenizer(batch, padding=True, truncation=True, max_length=512, return_tensors='pt')
            with torch.no_grad():
                outputs = bert_model(**encoded)
            embeddings = _mean_pooling(outputs, encoded['attention_mask'])
            embeddings = torch.nn.functional.normalize(embeddings, p=2, dim=1)
            all_embeddings.extend(embeddings.numpy())

            processed += len(batch)
            if processed % 500 == 0 or processed == total:
                logger.info(f"  向量化进度: {processed}/{total} ({100*processed//total}%)")

        return [e.tolist() for e in all_embeddings]
    else:
        # SentenceTransformer 模型
        embeddings = model.encode(texts, normalize_embeddings=True, show_progress_bar=True)
        logger.info(f"  向量化完成: {total} 个文本")
        return embeddings.tolist()


def embed_query(query: str) -> list[float]:
    """将单个查询转换为嵌入向量"""
    embeddings = embed_texts([query])
    return embeddings[0]


def get_current_model_info() -> dict:
    """获取当前加载模型的信息"""
    global _embedding_model, _embedding_model_name, _embedding_model_type

    if settings.embedding_model_path and settings.embedding_model_path.strip():
        model_type = "bert"
        model_name = settings.embedding_model_path.strip()
    elif settings.use_biobert:
        model_type = "sentence_transformers"
        model_name = settings.biobert_model_name
    else:
        model_type = "sentence_transformers"
        model_name = settings.embedding_model_name

    embedding_dim = None
    if _embedding_model is not None:
        if model_type == "bert":
            embedding_dim = _embedding_model["hidden_size"]
        else:
            embedding_dim = _embedding_model.get_sentence_embedding_dimension()

    return {
        "model_name": model_name,
        "model_type": model_type,
        "is_loaded": _embedding_model is not None,
        "embedding_dim": embedding_dim
    }
