"""
文本分块策略实现
支持:
  1. 递归字符分块 (RecursiveCharacterTextSplitter) - 高效，速度快
  2. 语义分块 (SemanticTextSplitter) - 按句子嵌入相似度切分，quality更高
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Optional
from dataclasses import dataclass, field
from app.rag.document_loader import Document
from app.utils.logger import logger


class SplitStrategy(str, Enum):
    RECURSIVE = "recursive"   # 递归字符分块 (V0.2 默认)
    SEMANTIC = "semantic"     # 语义分块 (V0.8 引入)


@dataclass
class TextChunk:
    """文本块数据类"""
    content: str
    metadata: dict = field(default_factory=dict)
    chunk_index: int = 0

    def to_document(self) -> Document:
        """转换为 Document 以兼容向量存储"""
        return Document(page_content=self.content, metadata=self.metadata)


class RecursiveCharacterTextSplitter:
    """
    递归字符文本分块器。
    优先按段落 → 换行 → 句子 → 词 的顺序切分，保留语义完整性。
    """

    DEFAULT_SEPARATORS = [
        "\n\n\n",   # 多空行（章节分隔）
        "\n\n",     # 段落
        "\n",       # 换行
        ". ",       # 英文句子
        "。",       # 中文句子
        " ",        # 空格
        "",         # 字符
    ]

    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        separators: Optional[list[str]] = None,
        length_function=len,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators or self.DEFAULT_SEPARATORS
        self.length_function = length_function

    def split_text(self, text: str) -> list[str]:
        """将文本切分为字符串列表"""
        return self._split_recursive(text, self.separators)

    def split_document(self, document: Document) -> list[TextChunk]:
        """切分单个 Document，为每个块附加元数据"""
        chunks_text = self.split_text(document.page_content)
        chunks = []
        for i, chunk_text in enumerate(chunks_text):
            if not chunk_text.strip():
                continue
            meta = {**document.metadata, "chunk_index": i, "chunk_total": len(chunks_text)}
            chunks.append(TextChunk(content=chunk_text, metadata=meta, chunk_index=i))
        return chunks

    def split_documents(self, documents: list[Document]) -> list[TextChunk]:
        """批量切分文档列表"""
        all_chunks = []
        for doc in documents:
            chunks = self.split_document(doc)
            all_chunks.extend(chunks)
        logger.info(
            f"递归字符分块: {len(documents)} 个文档 → {len(all_chunks)} 个分块 "
            f"(chunk_size={self.chunk_size}, overlap={self.chunk_overlap})"
        )
        return all_chunks

    def _split_recursive(self, text: str, separators: list[str]) -> list[str]:
        """递归地尝试分隔符，直到所有块满足 chunk_size 限制"""
        final_chunks = []

        # 找到适用的分隔符
        separator = separators[-1]
        for sep in separators:
            if sep == "":
                separator = sep
                break
            if sep in text:
                separator = sep
                break

        splits = self._split_by_separator(text, separator)

        good_splits = []
        for s in splits:
            if self.length_function(s) < self.chunk_size:
                good_splits.append(s)
            else:
                # 当前块太大，用剩余分隔符继续切
                if good_splits:
                    final_chunks.extend(self._merge_splits(good_splits, separator))
                    good_splits = []
                remaining_seps = separators[separators.index(separator) + 1:] if separator in separators else [""]
                if remaining_seps:
                    sub_chunks = self._split_recursive(s, remaining_seps)
                    final_chunks.extend(sub_chunks)
                else:
                    final_chunks.append(s)

        if good_splits:
            final_chunks.extend(self._merge_splits(good_splits, separator))

        return final_chunks

    def _split_by_separator(self, text: str, separator: str) -> list[str]:
        if separator:
            parts = text.split(separator)
        else:
            parts = list(text)
        return [p for p in parts if p]

    def _merge_splits(self, splits: list[str], separator: str) -> list[str]:
        """合并小块，确保每个块不超过 chunk_size，相邻块保留 overlap"""
        merged = []
        current_pieces = []
        current_len = 0
        sep_len = self.length_function(separator)

        for split in splits:
            split_len = self.length_function(split)
            if current_len + split_len + (sep_len if current_pieces else 0) > self.chunk_size:
                if current_pieces:
                    merged.append(separator.join(current_pieces))
                    # 保留 overlap
                    while current_pieces and current_len > self.chunk_overlap:
                        removed = current_pieces.pop(0)
                        current_len -= self.length_function(removed) + sep_len
                current_pieces.append(split)
                current_len = split_len
            else:
                current_pieces.append(split)
                current_len += split_len + (sep_len if len(current_pieces) > 1 else 0)

        if current_pieces:
            merged.append(separator.join(current_pieces))

        return merged


class SemanticTextSplitter:
    """
    语义分块器。
    通过计算相邻句子嵌入的余弦相似度来确定分割点。
    语义相似度低的位置（话题转换处）作为分割边界。
    需要嵌入模型支持，V0.3+ 后使用。
    """

    def __init__(
        self,
        embedding_model=None,
        chunk_size: int = 512,
        breakpoint_threshold: float = 0.3,  # 相似度低于此值时切割
    ):
        self.embedding_model = embedding_model
        self.chunk_size = chunk_size
        self.breakpoint_threshold = breakpoint_threshold

    def split_document(self, document: Document, embedding_model=None) -> list[TextChunk]:
        """语义分块 - 需要传入嵌入模型"""
        model = embedding_model or self.embedding_model
        if model is None:
            logger.warning("SemanticTextSplitter 未配置嵌入模型，回退到句子分块")
            return self._fallback_sentence_split(document)

        import numpy as np

        # 1. 句子分割
        sentences = self._split_to_sentences(document.page_content)
        if len(sentences) <= 1:
            return [TextChunk(content=document.page_content, metadata=document.metadata, chunk_index=0)]

        # 2. 计算句子嵌入
        embeddings = model.encode(sentences)

        # 3. 计算相邻句子余弦相似度
        similarities = []
        for i in range(len(embeddings) - 1):
            sim = self._cosine_similarity(embeddings[i], embeddings[i + 1])
            similarities.append(sim)

        # 4. 找到分割点（相似度突降处）
        breakpoints = [i + 1 for i, sim in enumerate(similarities) if sim < self.breakpoint_threshold]

        # 5. 按分割点合并句子为块
        chunks = []
        prev_idx = 0
        for bp in breakpoints + [len(sentences)]:
            chunk_text = " ".join(sentences[prev_idx:bp]).strip()
            if chunk_text:
                meta = {**document.metadata, "chunk_index": len(chunks)}
                chunks.append(TextChunk(content=chunk_text, metadata=meta, chunk_index=len(chunks)))
            prev_idx = bp

        logger.info(f"语义分块: {len(sentences)} 个句子 → {len(chunks)} 个块 (threshold={self.breakpoint_threshold})")
        return chunks

    def _split_to_sentences(self, text: str) -> list[str]:
        """简单的句子分割（英文 + 中文）"""
        # 按句号、问号、感叹号切分
        sentences = re.split(r'(?<=[.!?])\s+|(?<=[。！？])', text)
        return [s.strip() for s in sentences if s.strip()]

    def _cosine_similarity(self, a, b) -> float:
        import numpy as np
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))

    def _fallback_sentence_split(self, document: Document) -> list[TextChunk]:
        """无嵌入模型时回退到基于句子数的简单分块"""
        sentences = self._split_to_sentences(document.page_content)
        chunks = []
        batch = []
        batch_len = 0
        for sent in sentences:
            batch.append(sent)
            batch_len += len(sent)
            if batch_len >= self.chunk_size:
                meta = {**document.metadata, "chunk_index": len(chunks)}
                chunks.append(TextChunk(content=" ".join(batch), metadata=meta, chunk_index=len(chunks)))
                batch = []
                batch_len = 0
        if batch:
            meta = {**document.metadata, "chunk_index": len(chunks)}
            chunks.append(TextChunk(content=" ".join(batch), metadata=meta, chunk_index=len(chunks)))
        return chunks


def get_splitter(strategy: SplitStrategy = SplitStrategy.RECURSIVE, **kwargs) -> RecursiveCharacterTextSplitter | SemanticTextSplitter:
    """工厂函数：按策略返回对应分块器"""
    if strategy == SplitStrategy.RECURSIVE:
        return RecursiveCharacterTextSplitter(**kwargs)
    elif strategy == SplitStrategy.SEMANTIC:
        return SemanticTextSplitter(**kwargs)
    else:
        raise ValueError(f"未知分块策略: {strategy}")
