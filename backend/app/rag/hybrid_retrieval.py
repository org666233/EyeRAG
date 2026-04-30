"""
混合检索策略
组合向量语义检索 + BM25关键词检索，提升召回质量
"""

import re
import math
from collections import defaultdict
from typing import Optional
from app.rag.vector_store import get_vector_store
from app.config import get_settings
from app.utils.logger import logger

settings = get_settings()


class BM25Retriever:
    """
    BM25 关键词检索（内存实现）。
    从 ChromaDB 加载所有文档构建倒排索引。
    """

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.doc_index = {}      # id -> text
        self.doc_meta = {}       # id -> metadata
        self.inverted = defaultdict(set)  # term -> set of doc ids
        self.doc_lengths = {}    # id -> word count
        self.avg_dl = 0
        self.N = 0
        self._built = False

    def build_index(self):
        """从 ChromaDB 加载文档并构建 BM25 索引"""
        vs = get_vector_store()
        total = vs.collection.count()
        if total == 0:
            return

        logger.info(f"BM25 构建索引: 加载 {total} 个文档块...")
        results = vs.collection.get(include=["documents", "metadatas"], limit=min(total, 10000))

        ids = results["ids"]
        docs = results["documents"]
        metas = results["metadatas"]

        total_length = 0
        for i, (doc_id, doc, meta) in enumerate(zip(ids, docs, metas)):
            if not doc:
                continue
            terms = self._tokenize(doc)
            self.doc_index[doc_id] = doc
            self.doc_meta[doc_id] = meta
            self.doc_lengths[doc_id] = len(terms)
            total_length += len(terms)
            for term in set(terms):
                self.inverted[term].add(doc_id)

        self.N = len(self.doc_index)
        self.avg_dl = total_length / self.N if self.N > 0 else 1
        self._built = True
        logger.info(f"BM25 索引构建完成: {self.N} 个文档, {len(self.inverted)} 个词项")

    def search(self, query: str, top_k: int = 10) -> list[dict]:
        if not self._built:
            self.build_index()
        if self.N == 0:
            return []

        query_terms = self._tokenize(query)
        scores = defaultdict(float)

        for term in query_terms:
            if term not in self.inverted:
                continue
            df = len(self.inverted[term])
            idf = math.log((self.N - df + 0.5) / (df + 0.5) + 1)
            for doc_id in self.inverted[term]:
                dl = self.doc_lengths[doc_id]
                tf = self._tokenize(self.doc_index[doc_id]).count(term)
                numerator = tf * (self.k1 + 1)
                denominator = tf + self.k1 * (1 - self.b + self.b * dl / self.avg_dl)
                scores[doc_id] += idf * (numerator / denominator)

        sorted_ids = sorted(scores, key=scores.get, reverse=True)[:top_k]
        return [{
            "content": self.doc_index[doc_id],
            "metadata": self.doc_meta[doc_id],
            "score": scores[doc_id],
            "retrieval_type": "bm25",
        } for doc_id in sorted_ids]

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        return re.findall(r'\w+', text.lower())


class HybridRetriever:
    """
    混合检索: 向量检索 + BM25
    使用 RRF (Reciprocal Rank Fusion) 融合排序
    """

    def __init__(self, vector_weight: float = 0.6, bm25_weight: float = 0.4):
        self.vector_weight = vector_weight
        self.bm25_weight = bm25_weight
        self.bm25 = BM25Retriever()
        self.vs = get_vector_store()

    def search(
        self,
        query: str,
        top_k: int = 5,
        rrf_k: int = 60,
        bm25_extra_query: str = "",
        vector_extra_query: str = "",
    ) -> list[dict]:
        """
        混合检索 + RRF 排序融合。
        bm25_extra_query:   可选的额外 BM25 查询词（如中文问题的英文翻译），双路 BM25 取最优分。
        vector_extra_query: 可选的额外向量查询词（同上），双路向量检索取最优分，
                            弥补 bge-m3 跨语言相似度约 25% 的系统性衰减。
        """
        # 向量检索（原始查询）
        vector_results = self.vs.search(query=query, top_k=top_k * 2)

        # 向量检索（英文翻译，命中英文文档；bge-m3 跨语言有系统性衰减，双路补偿）
        if vector_extra_query:
            vector_extra = self.vs.search(query=vector_extra_query, top_k=top_k * 2)
            vec_map: dict[str, dict] = {r["content"][:100]: r for r in vector_results}
            for r in vector_extra:
                key = r["content"][:100]
                if key not in vec_map or r["score"] > vec_map[key]["score"]:
                    vec_map[key] = r
            vector_results = sorted(vec_map.values(), key=lambda x: x["score"], reverse=True)[: top_k * 2]
            logger.debug(f"向量双语合并: 共 {len(vector_results)} 条候选")

        # BM25 检索（原始查询，主要命中中文文档）
        bm25_results = self.bm25.search(query=query, top_k=top_k * 2)

        # BM25 额外查询（英文翻译，主要命中英文文档）
        if bm25_extra_query:
            bm25_extra = self.bm25.search(query=bm25_extra_query, top_k=top_k * 2)
            # 合并两路 BM25：同一文档取最高分，避免双重计分
            bm25_map: dict[str, dict] = {r["content"][:100]: r for r in bm25_results}
            for r in bm25_extra:
                key = r["content"][:100]
                if key not in bm25_map or r["score"] > bm25_map[key]["score"]:
                    bm25_map[key] = r
            bm25_results = sorted(bm25_map.values(), key=lambda x: x["score"], reverse=True)[: top_k * 2]
            logger.debug(f"BM25 双语合并: 共 {len(bm25_results)} 条候选")

        # RRF 融合
        rrf_scores: dict[str, float] = defaultdict(float)
        doc_map: dict[str, dict] = {}

        for rank, r in enumerate(vector_results):
            key = r.get("content", "")[:100]
            rrf_scores[key] += self.vector_weight / (rrf_k + rank + 1)
            doc_map[key] = r

        for rank, r in enumerate(bm25_results):
            key = r.get("content", "")[:100]
            rrf_scores[key] += self.bm25_weight / (rrf_k + rank + 1)
            if key not in doc_map:
                doc_map[key] = r

        sorted_keys = sorted(rrf_scores, key=rrf_scores.get, reverse=True)[:top_k]

        results = []
        for key in sorted_keys:
            doc = doc_map[key].copy()
            doc["rrf_score"] = rrf_scores[key]
            doc["retrieval_type"] = "hybrid"
            results.append(doc)

        return results


# 全局单例
_hybrid: Optional[HybridRetriever] = None


def get_hybrid_retriever() -> HybridRetriever:
    global _hybrid
    if _hybrid is None:
        _hybrid = HybridRetriever()
    return _hybrid
