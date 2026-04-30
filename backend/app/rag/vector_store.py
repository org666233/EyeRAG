"""
ChromaDB 向量存储封装
支持两种连接模式（由 .env 决定）:
  - HTTP 模式: CHROMA_HOST=localhost  → 连接 Docker 中的 ChromaDB 服务
  - 本地模式: CHROMA_HOST 未设置     → 使用本地 PersistentClient（开发备用）
"""

import time
import uuid
from typing import Optional
from pathlib import Path
from app.config import get_settings
from app.utils.logger import logger

# 全量扫描结果缓存，避免每次页面加载都扫描数万条记录
_CACHE_TTL = 60  # 秒
_stats_cache: Optional[dict] = None
_stats_cache_ts: float = 0
_docs_cache: Optional[list] = None
_docs_cache_ts: float = 0


def _invalidate_cache():
    global _stats_cache, _stats_cache_ts, _docs_cache, _docs_cache_ts
    _stats_cache = None
    _stats_cache_ts = 0
    _docs_cache = None
    _docs_cache_ts = 0

settings = get_settings()

_chroma_client = None
_collection = None


def get_chroma_client():
    """
    获取 ChromaDB 客户端（懒加载）。
    优先使用 HTTP 模式（Docker），降级使用本地持久化模式。
    """
    global _chroma_client
    if _chroma_client is not None:
        return _chroma_client

    import chromadb
    from chromadb.config import Settings as ChromaSettings

    if settings.chroma_host:
        # HTTP 模式：连接 Docker 中运行的 ChromaDB Server
        _chroma_client = chromadb.HttpClient(
            host=settings.chroma_host,
            port=settings.chroma_port,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        logger.info(f"✅ ChromaDB HTTP 客户端: {settings.chroma_host}:{settings.chroma_port}")
    else:
        # 本地持久化模式（fallback）
        persist_dir = Path(settings.chroma_persist_dir)
        persist_dir.mkdir(parents=True, exist_ok=True)
        _chroma_client = chromadb.PersistentClient(
            path=str(persist_dir),
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        logger.info(f"✅ ChromaDB 本地模式，路径: {persist_dir}")

    return _chroma_client


def get_collection():
    """获取 ophthalmology 向量 collection（不存在则创建）"""
    global _collection
    if _collection is not None:
        return _collection

    client = get_chroma_client()
    _collection = client.get_or_create_collection(
        name=settings.chroma_collection_name,
        metadata={"hnsw:space": "cosine"},
    )
    count = _collection.count()
    logger.info(f"✅ Collection '{settings.chroma_collection_name}' 就绪，当前 {count} 条记录")
    return _collection


class VectorStore:
    """向量存储操作类，封装 ChromaDB 的 CRUD 和检索操作。"""

    def __init__(self):
        self.collection = get_collection()

    def add_documents(self, chunks: list) -> int:
        """将 TextChunk 列表向量化并存入 ChromaDB。"""
        from app.rag.embeddings import embed_texts

        if not chunks:
            return 0

        texts = [c.content for c in chunks]
        metadatas = [c.metadata for c in chunks]
        ids = [str(uuid.uuid4()) for _ in chunks]

        logger.info(f"正在向量化 {len(texts)} 个文本块...")
        embeddings = embed_texts(texts)

        cleaned_metadatas = []
        for meta in metadatas:
            cleaned = {
                k: v if isinstance(v, (str, int, float, bool)) else str(v)
                for k, v in meta.items()
            }
            cleaned_metadatas.append(cleaned)

        self.collection.add(
            documents=texts,
            embeddings=embeddings,
            metadatas=cleaned_metadatas,
            ids=ids,
        )
        logger.info(f"✅ 成功存储 {len(chunks)} 个文本块")
        _invalidate_cache()
        return len(chunks)

    def search(
        self,
        query: str,
        top_k: int = 5,
        filter_metadata: Optional[dict] = None,
    ) -> list[dict]:
        """向量相似度检索。"""
        from app.rag.embeddings import embed_query

        query_embedding = embed_query(query)
        where = filter_metadata if filter_metadata else None

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k, max(1, self.collection.count())),
            where=where,
            include=["documents", "metadatas", "distances"],
        )

        documents = []
        if not results["documents"] or not results["documents"][0]:
            return documents

        for doc, meta, dist, doc_id in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
            results["ids"][0],
        ):
            similarity = 1.0 - dist
            documents.append({
                "content": doc,
                "metadata": meta,
                "score": round(similarity, 4),
                "id": doc_id,
            })

        documents.sort(key=lambda x: x["score"], reverse=True)
        return documents

    def delete_by_source(self, file_name: str) -> int:
        """按文件名删除所有相关向量"""
        results = self.collection.get(
            where={"file_name": file_name},
            include=["documents"],
        )
        ids = results.get("ids", [])
        if ids:
            self.collection.delete(ids=ids)
            logger.info(f"删除文件 {file_name} 的 {len(ids)} 个向量块")
            _invalidate_cache()
        return len(ids)

    def _scan_all_metadatas(self) -> list[dict]:
        """扫描全量 metadata，结果带 TTL 缓存，减少 ChromaDB HTTP 往返次数。"""
        global _docs_cache, _docs_cache_ts
        if _docs_cache is not None and (time.time() - _docs_cache_ts) < _CACHE_TTL:
            return _docs_cache

        all_metas = []
        batch_size = 10000  # 增大批次，减少 HTTP 往返（28k 条只需 3 次）
        offset = 0
        while True:
            results = self.collection.get(
                include=["metadatas"],
                limit=batch_size,
                offset=offset,
            )
            batch = results.get("metadatas") or []
            if not batch:
                break
            all_metas.extend(batch)
            if len(batch) < batch_size:
                break
            offset += batch_size

        _docs_cache = all_metas
        _docs_cache_ts = time.time()
        return all_metas

    def get_stats(self) -> dict:
        """获取向量库统计信息"""
        global _stats_cache, _stats_cache_ts
        if _stats_cache is not None and (time.time() - _stats_cache_ts) < _CACHE_TTL:
            return _stats_cache

        total = self.collection.count()
        all_metas = self._scan_all_metadatas()
        file_names = {(m.get("file_name", "unknown") if m else "unknown") for m in all_metas}

        result = {
            "total_chunks": total,
            "document_count": len(file_names),
            "total_documents": len(file_names),
            "collection_name": settings.chroma_collection_name,
        }
        _stats_cache = result
        _stats_cache_ts = time.time()
        return result

    def list_documents(self) -> list[dict]:
        """列出所有已入库的文档（按文件名去重）"""
        if self.collection.count() == 0:
            return []

        all_metas = self._scan_all_metadatas()
        docs_map = {}
        for meta in all_metas:
            fname = (meta.get("file_name", "unknown") if meta else "unknown")
            if fname not in docs_map:
                docs_map[fname] = {
                    "file_name": fname,
                    "source": meta.get("source", "") if meta else "",
                    "file_type": meta.get("file_type", "") if meta else "",
                    "source_name": meta.get("source_name", "") if meta else "",
                    "url": meta.get("url", "") if meta else "",
                    "chunk_count": 0,
                }
            docs_map[fname]["chunk_count"] += 1

        return sorted(docs_map.values(), key=lambda x: x["file_name"])


# 全局向量存储单例
_vector_store: Optional[VectorStore] = None


def get_vector_store() -> VectorStore:
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store
