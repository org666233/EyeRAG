"""
重排序模块 (Reranker)
对初步检索结果进行二次精排，提升结果相关性
支持:
  1. 基于 CrossEncoder 的神经重排序
  2. 轻量级关键词+位置启发式重排序 (无需额外模型)
"""

from typing import Optional
from app.utils.logger import logger


class KeywordReranker:
    """
    轻量级关键词重排序器（不依赖额外模型）。
    综合考虑:
      - 查询词覆盖率
      - 关键词位置
      - 文档长度适中度
    """

    def rerank(self, query: str, results: list[dict], top_k: int = 5) -> list[dict]:
        if not results:
            return []

        query_terms = set(query.lower().split())

        scored = []
        for r in results:
            content = r.get("content", "").lower()
            original_score = r.get("score", r.get("rrf_score", 0))

            # 因子1: 查询词覆盖率
            coverage = sum(1 for t in query_terms if t in content) / max(len(query_terms), 1)

            # 因子2: 查询词出现位置（越靠前越好）
            position_score = 0
            for t in query_terms:
                pos = content.find(t)
                if pos >= 0:
                    position_score += 1.0 / (1 + pos / 100)

            # 因子3: 长度适中度（太短或太长都不好）
            length = len(content)
            length_score = 1.0 if 100 <= length <= 800 else 0.7

            # 综合得分
            rerank_score = (
                original_score * 0.5 +
                coverage * 0.25 +
                position_score * 0.15 +
                length_score * 0.1
            )

            entry = r.copy()
            entry["rerank_score"] = rerank_score
            scored.append(entry)

        scored.sort(key=lambda x: x["rerank_score"], reverse=True)
        return scored[:top_k]


class CrossEncoderReranker:
    """
    基于 CrossEncoder 的神经重排序器。
    使用 cross-encoder/ms-marco-MiniLM-L-6-v2 等模型。
    """

    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        self.model_name = model_name
        self._model = None

    def _load_model(self):
        if self._model is None:
            try:
                from sentence_transformers import CrossEncoder
                logger.info(f"加载 CrossEncoder 重排序模型: {self.model_name}")
                self._model = CrossEncoder(self.model_name)
            except ImportError:
                logger.warning("CrossEncoder 不可用，降级使用关键词重排序")
                return False
        return True

    def rerank(self, query: str, results: list[dict], top_k: int = 5) -> list[dict]:
        if not results:
            return []

        if not self._load_model():
            return KeywordReranker().rerank(query, results, top_k)

        pairs = [(query, r.get("content", "")) for r in results]
        scores = self._model.predict(pairs)

        for i, r in enumerate(results):
            r["rerank_score"] = float(scores[i])

        results.sort(key=lambda x: x["rerank_score"], reverse=True)
        return results[:top_k]


def get_reranker(use_cross_encoder: bool = False):
    """获取重排序器实例"""
    if use_cross_encoder:
        return CrossEncoderReranker()
    return KeywordReranker()
