"""
Self-RAG 自判断检索机制
通过 LLM 评估检索结果的相关性，按需触发二次检索或降级回答
"""

from typing import Optional, AsyncGenerator
from app.rag.hybrid_retrieval import get_hybrid_retriever
from app.rag.reranker import get_reranker
from app.rag.prompts import build_rag_messages, format_context
from app.rag.llm_client import generate
from app.rag.safety_checker import get_safety_checker
from app.config import get_settings
from app.utils.logger import logger

settings = get_settings()


# ── Self-RAG 评估 Prompt ─────────────────────────────────────────────────────

SELF_RAG_EVAL_PROMPT = """你是一个检索质量评估专家。请判断给定的参考资料是否足以回答用户的问题。

## 用户问题
{question}

## 参考资料
{context}

## 评估要求
请从以下两个维度进行评估：

1. **相关性**：参考资料中是否包含与问题主题直接相关的内容？（回答"是"或"否"并简要说明）
2. **完整性**：参考资料中的信息是否足够充分，能够支撑生成一个完整、有意义的回答？（回答"是"或"否"并简要说明）

## 输出格式
请严格按照以下 JSON 格式输出，不要包含任何其他内容：
{{
    "relevant": true或false,
    "relevant_reason": "简要说明相关性判断理由（1-2句话）",
    "sufficient": true或false,
    "sufficient_reason": "简要说明充分性判断理由（1-2句话）",
    "decision": "proceed或retry或fallback",
    "decision_reason": "解释决策理由（2-3句话）",
    "suggested_query": "如果选择retry，给出优化后的查询词（用中文，不超过20字）；否则填写null"
}}

判断标准：
- decision = "proceed"：参考资料相关且充分，可以直接进入答案生成阶段
- decision = "retry"：参考资料相关性不足，但主题方向正确，可以通过优化查询词进行二次检索
- decision = "fallback"：参考资料与问题完全不相关或严重不足，需要使用通用知识降级回答
"""

# 降级回答 Prompt（无参考资料时）
FALLBACK_PROMPT = """用户提出了一个眼科医学相关问题，但我们的知识库中没有找到直接相关的参考资料。

## 用户问题
{question}

## 回答要求
1. 明确告知用户：本次回答基于通用医学知识，知识库中暂未收录相关参考资料，内容仅供参考
2. 尽你所能基于通用眼科医学知识回答该问题
3. 使用通俗易懂的语言
4. 使用 Markdown 格式组织回答
5. 在回答末尾标注："⚠️ 本回答基于通用医学知识，知识库暂无相关参考资料，内容仅供参考。如有疑问请咨询专业眼科医生。"
6. 如果你对这个问题完全不了解，直接回答"抱歉，我对这个问题暂时没有足够的知识来回答，建议您咨询专业眼科医生或提供更具体的描述"
"""


def _is_chinese(text: str) -> bool:
    """判断文本是否以中文为主（中文字符占比超过 30%）"""
    chinese = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    return chinese / max(len(text), 1) > 0.3


async def _translate_for_bm25(query: str) -> str:
    """
    将中文查询轻量翻译为英文，仅用于 BM25 补充检索。
    使用极短 prompt 节省 token，翻译失败时静默返回空串。
    """
    try:
        result = await generate(
            messages=[{
                "role": "user",
                "content": (
                    "Translate the following ophthalmology question to English. "
                    "Output ONLY the English translation, nothing else.\n\n"
                    f"{query}"
                ),
            }],
            temperature=0,
            max_tokens=128,
        )
        translated = result.strip()
        logger.info(f"BM25 查询翻译: '{query[:40]}' → '{translated[:60]}'")
        return translated
    except Exception as e:
        logger.warning(f"BM25 查询翻译失败（跳过）: {e}")
        return ""


class SelfRAGAgent:
    """
    Self-RAG 自判断检索代理。

    工作流程：
    1. 初步检索：执行混合检索获取 Top-K 候选文档
    2. 评估阶段：调用 LLM 评估候选文档的相关性和充分性
    3. 决策分支：
       - proceed → 直接进入答案生成
       - retry → 使用优化查询词二次检索
       - fallback → 降级为无参考资料回答模式
    4. 答案生成后 → 通过医疗安全检查层
    """

    def __init__(self):
        self.retriever = get_hybrid_retriever()
        self.reranker = get_reranker(use_cross_encoder=False)
        self.safety_checker = get_safety_checker()
        self.top_k = settings.retrieval_top_k
        self.max_retries = 2  # 最多触发一次二次检索

    async def _evaluate_retrieval(
        self,
        question: str,
        search_results: list[dict],
    ) -> dict:
        """
        调用 LLM 评估检索结果质量。
        """
        context = format_context(search_results, max_chars=2000)
        if context == "（暂无相关参考资料）":
            return {
                "relevant": False,
                "sufficient": False,
                "decision": "fallback",
                "decision_reason": "知识库中无相关参考资料",
                "suggested_query": None,
            }

        prompt = SELF_RAG_EVAL_PROMPT.format(question=question, context=context)
        try:
            raw = await generate(
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=2048,
            )
            import json, re
            logger.debug(f"Self-RAG 评估原始返回({len(raw)}字符): {raw[:200]}")
            # 尝试提取 JSON
            json_match = re.search(r"\{[\s\S]*\}", raw)
            if json_match:
                result = json.loads(json_match.group())
                return {
                    "relevant": result.get("relevant", False),
                    "sufficient": result.get("sufficient", False),
                    "decision": result.get("decision", "proceed"),
                    "decision_reason": result.get("decision_reason", ""),
                    "suggested_query": result.get("suggested_query"),
                }
        except Exception as e:
            logger.warning(f"Self-RAG 评估失败: {e}，使用默认决策 proceed")

        # 评估失败时保守处理：有文档就用
        return {
            "relevant": True,
            "sufficient": True,
            "decision": "proceed",
            "decision_reason": "评估过程异常，使用默认决策",
            "suggested_query": None,
        }

    def _apply_safety_check(self, answer: str, question: str) -> tuple[str, bool]:
        """应用医疗安全检查，返回 (处理后答案, 是否安全)"""
        result = self.safety_checker.check(answer, question)
        return result.answer, result.safe

    async def query_stream(
        self,
        question: str,
        top_k: Optional[int] = None,
        chat_history: Optional[list[dict]] = None,
        temperature: float = 0.3,
    ) -> tuple["AsyncGenerator[str, None]", list[dict], str, list[dict]]:
        """
        Self-RAG 流式查询入口。

        Returns:
            (stream_generator, sources, retrieval_decision, search_results)
            stream_generator: LLM 流式生成器
            sources: 引用来源列表
            retrieval_decision: 检索决策（proceed / retry / fallback）
            search_results: 完整检索结果列表（用于详情页展示）
        """
        k = top_k or self.top_k
        logger.info(f"Self-RAG 查询: '{question[:60]}'")

        # Step 1: 初步混合检索（中文问题翻译为英文，双路补偿向量和 BM25 的跨语言衰减）
        en_query = await _translate_for_bm25(question) if _is_chinese(question) else ""
        candidates = self.retriever.search(
            query=question, top_k=k * 3,
            bm25_extra_query=en_query,
            vector_extra_query=en_query,
        )

        if not candidates:
            logger.warning("Self-RAG: 初次检索无结果，降级")
            decision = "fallback"
            search_results = []
            messages = self._build_fallback_messages(question)
        else:
            # Step 2: 重排序
            search_results = self.reranker.rerank(
                query=question, results=candidates, top_k=k
            )

            # Step 3: Self-RAG 评估
            evaluation = await self._evaluate_retrieval(question, search_results)
            decision = evaluation["decision"]
            logger.info(
                f"Self-RAG 评估决策: {decision} | "
                f"relevant={evaluation.get('relevant')} | "
                f"sufficient={evaluation.get('sufficient')} | "
                f"reason={evaluation.get('decision_reason', '')[:80]}"
            )

            if decision == "proceed":
                messages = build_rag_messages(
                    question=question,
                    search_results=search_results,
                    chat_history=chat_history,
                )
            elif decision == "retry":
                # 二次检索
                suggested = evaluation.get("suggested_query") or question
                logger.info(f"Self-RAG 二次检索，查询词: {suggested}")
                en_query2 = await _translate_for_bm25(suggested) if _is_chinese(suggested) else ""
                candidates2 = self.retriever.search(
                    query=suggested, top_k=k * 3,
                    bm25_extra_query=en_query2,
                    vector_extra_query=en_query2,
                )
                if candidates2:
                    search_results2 = self.reranker.rerank(
                        query=question, results=candidates2, top_k=k
                    )
                    search_results = search_results2
                messages = build_rag_messages(
                    question=question,
                    search_results=search_results,
                    chat_history=chat_history,
                )
            else:  # fallback
                messages = self._build_fallback_messages(question)

        # Step 4: 提取来源
        from app.rag.pipeline import RAGPipeline
        pipe = RAGPipeline.__new__(RAGPipeline)
        sources = pipe._extract_sources(search_results)

        # Step 5: 流式生成（嵌入安全检查）
        from app.rag.llm_client import generate_stream
        import asyncio

        raw_stream = generate_stream(messages=messages, temperature=temperature)

        async def safe_stream():
            raw_chunks = []
            async for chunk in raw_stream:
                raw_chunks.append(chunk)
                yield chunk
            raw_answer = "".join(raw_chunks)
            safe_answer, _ = self._apply_safety_check(raw_answer, question)
            if safe_answer != raw_answer:
                suffix = safe_answer[len(raw_answer):]
                for i in range(0, len(suffix), 10):
                    await asyncio.sleep(0)
                    yield suffix[i:i + 10]

        # 将 search_results 也一并返回（用于详情页）
        return safe_stream(), sources, decision, search_results

    async def query(
        self,
        question: str,
        top_k: Optional[int] = None,
        chat_history: Optional[list[dict]] = None,
        temperature: float = 0.3,
    ) -> dict:
        """
        非流式查询入口，内部复用 query_stream 收集完整回答。

        Returns:
            dict with keys: answer, sources, query, context_count
        """
        stream, sources, decision, search_results = await self.query_stream(
            question=question,
            top_k=top_k,
            chat_history=chat_history,
            temperature=temperature,
        )
        chunks = []
        async for chunk in stream:
            chunks.append(chunk)
        answer = "".join(chunks)
        return {
            "answer": answer,
            "sources": sources,
            "query": question,
            "context_count": len(sources),
            "retrieval_decision": decision,
        }

    def _build_fallback_messages(self, question: str) -> list[dict]:
        """构建降级回答的消息列表"""
        from app.rag.prompts import SYSTEM_PROMPT
        user_content = FALLBACK_PROMPT.format(question=question)
        return [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ]


# 全局单例
_self_rag: Optional[SelfRAGAgent] = None


def get_self_rag_agent() -> SelfRAGAgent:
    global _self_rag
    if _self_rag is None:
        _self_rag = SelfRAGAgent()
    return _self_rag
