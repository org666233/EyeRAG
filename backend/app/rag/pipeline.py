"""
RAG 管线核心（升级版）
完整链路: 用户问题 → 混合检索（向量+BM25+RRF） → 关键词重排序 → Prompt增强 → LLM生成 → 带源引用的回答
"""

import asyncio
from typing import AsyncGenerator, Optional
from app.rag.hybrid_retrieval import get_hybrid_retriever
from app.rag.reranker import get_reranker
from app.rag.prompts import build_rag_messages
from app.rag.llm_client import generate, generate_stream
from app.rag.safety_checker import get_safety_checker
from app.config import get_settings
from app.utils.logger import logger

settings = get_settings()


class RAGPipeline:
    """
    RAG (Retrieval-Augmented Generation) 管线。
    核心流程:
      1. 接收用户查询
      2. 混合检索（向量语义 + BM25 关键词，RRF 融合）
      3. 关键词重排序，精选最相关 Top-K
      4. 构建增强 Prompt（含检索上下文）
      5. 调用 LLM 生成回答
      6. 返回回答 + 引用来源
    """

    def __init__(self):
        self.retriever = get_hybrid_retriever()
        self.reranker = get_reranker(use_cross_encoder=False)
        self.safety_checker = get_safety_checker()
        self.top_k = settings.retrieval_top_k

    async def query(
        self,
        question: str,
        top_k: Optional[int] = None,
        chat_history: Optional[list[dict]] = None,
        temperature: float = 0.3,
    ) -> dict:
        """
        完整 RAG 查询（同步生成）。
        返回: {"answer": str, "sources": list, "query": str, "context_count": int}
        """
        k = top_k or self.top_k

        # Step 1: 混合检索（向量 + BM25，初检 2k 个候选）
        logger.info(f"RAG 查询: '{question[:60]}' (top_k={k})")
        candidates = self.retriever.search(query=question, top_k=k * 3)
        logger.info(f"混合检索候选: {len(candidates)} 个")

        # Step 2: 重排序，精选 top_k
        search_results = self.reranker.rerank(query=question, results=candidates, top_k=k)
        logger.info(f"重排序后: {len(search_results)} 个文档块")

        # Step 3: 构建 Prompt
        messages = build_rag_messages(
            question=question,
            search_results=search_results,
            chat_history=chat_history,
        )

        # Step 4: LLM 生成
        answer = await generate(messages=messages, temperature=temperature)

        # Step 5: 提取引用来源
        sources = self._extract_sources(search_results)

        return {
            "query": question,
            "answer": answer,
            "sources": sources,
            "context_count": len(search_results),
        }

    async def query_stream(
        self,
        question: str,
        top_k: Optional[int] = None,
        chat_history: Optional[list[dict]] = None,
        temperature: float = 0.3,
    ) -> tuple[AsyncGenerator[str, None], list[dict], str]:
        """
        流式 RAG 查询（SSE 用）。
        返回: (text_stream, sources, retrieval_decision)
        """
        k = top_k or self.top_k

        # Step 1: 混合检索
        logger.info(f"RAG 流式查询: '{question[:60]}'")
        candidates = self.retriever.search(query=question, top_k=k * 3)

        # Step 2: 重排序
        search_results = self.reranker.rerank(query=question, results=candidates, top_k=k)

        # Step 3: 构建 Prompt
        messages = build_rag_messages(
            question=question,
            search_results=search_results,
            chat_history=chat_history,
        )

        # Step 4: 提取来源
        sources = self._extract_sources(search_results)

        # Step 5: 流式生成，同时进行安全检查
        async def safe_stream():
            raw_chunks = []
            async for chunk in generate_stream(messages=messages, temperature=temperature):
                raw_chunks.append(chunk)
                yield chunk
            # 完成后对完整答案进行安全检查
            raw_answer = "".join(raw_chunks)
            safe_answer, safe_flag = self._apply_safety_check(raw_answer, question)
            # 如果安全检查追加了内容（免责声明），将新增部分也流式输出
            if safe_answer != raw_answer:
                suffix = safe_answer[len(raw_answer):]
                for i in range(0, len(suffix), 10):
                    await asyncio.sleep(0)
                    yield suffix[i:i + 10]

        return safe_stream(), sources, "proceed"

    def _extract_sources(self, search_results: list[dict]) -> list[dict]:
        """从检索结果提取去重后的引用来源。"""
        seen = set()
        sources = []
        for r in search_results:
            meta = r.get("metadata", {})
            title = meta.get("title") or meta.get("file_name", "未知来源")
            if title in seen:
                continue
            seen.add(title)
            sources.append({
                "title": title,
                "source": meta.get("source_name", meta.get("source", "")),
                "url": meta.get("url", ""),
                "score": r.get("rerank_score", r.get("rrf_score", r.get("score", 0))),
            })
        return sources

    def _apply_safety_check(self, answer: str, question: str) -> tuple[str, bool]:
        """对答案应用医疗安全检查，返回 (处理后答案, 是否安全)"""
        result = self.safety_checker.check(answer, question)
        return result.answer, result.safe


# 全局管线单例
_pipeline: Optional[RAGPipeline] = None


def get_rag_pipeline() -> RAGPipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = RAGPipeline()
    return _pipeline
