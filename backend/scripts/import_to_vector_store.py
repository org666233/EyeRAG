#!/usr/bin/env python3
"""
眼科知识库数据导入脚本
功能：
  1. 检查现有向量库，避免重复导入
  2. 导入丁香园眼科疾病数据
  3. 导入寻医问药网眼科数据
  4. 导入 Wikipedia 眼科数据
  5. 统计导入结果
"""

import sys
import json
import re
import logging
from pathlib import Path
from dataclasses import dataclass

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(message)s')
logger = logging.getLogger(__name__)

# 添加 backend 到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.rag.vector_store import get_vector_store
from app.rag.embeddings import embed_texts

BASE_DIR = Path(__file__).parent.parent / "data" / "documents"
CHINESE_MEDICAL_DIR = BASE_DIR / "chinese_medical"
WIKI_DIR = BASE_DIR / "wikipedia"


@dataclass
class TextChunk:
    content: str
    metadata: dict


def get_existing_files(vs) -> set:
    """获取向量库中已存在的文件名（使用采样优化）"""
    existing = set()
    total = vs.collection.count()

    if total == 0:
        return existing

    # 批量获取 metadata 来提取文件名
    batch_size = 1000
    offset = 0
    seen = set()

    while offset < total:
        results = vs.collection.get(
            include=["metadatas"],
            limit=batch_size,
            offset=offset
        )

        if not results.get("metadatas"):
            break

        for meta in results["metadatas"]:
            fn = meta.get("file_name")
            if fn and fn not in seen:
                existing.add(fn)
                seen.add(fn)

        offset += batch_size

        # 每 5000 条输出一次进度
        if offset % 5000 == 0:
            logger.info(f"  已检查 {offset}/{total} 条记录...")

    return existing


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """将长文本分块"""
    if len(text) <= chunk_size:
        return [text] if text.strip() else []

    chunks = []
    start = 0
    text = text.strip()

    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]

        # 尝试在句号或换行处截断
        if end < len(text):
            last_period = max(
                chunk.rfind('。'),
                chunk.rfind('.\n'),
                chunk.rfind('\n'),
                chunk.rfind(' ')
            )
            if last_period > chunk_size * 0.5:
                chunk = chunk[:last_period + 1]
                end = start + len(chunk)

        chunks.append(chunk.strip())
        start = end - overlap

    return [c for c in chunks if c and len(c) > 20]


def import_dxy_jsonl(vs, existing_files: set) -> dict:
    """导入丁香园 JSONL 数据"""
    logger.info("\n" + "="*60)
    logger.info("导入丁香园眼科疾病数据")
    logger.info("="*60)

    jsonl_file = CHINESE_MEDICAL_DIR / "dxy_yanke_articles.jsonl"
    if not jsonl_file.exists():
        logger.warning(f"丁香园数据文件不存在: {jsonl_file}")
        return {"skipped": 0, "imported": 0}

    file_name = "dxy_yanke_articles.jsonl"
    if file_name in existing_files:
        logger.info(f"已存在，跳过: {file_name}")
        return {"skipped": 1, "imported": 0}

    chunks = []
    with open(jsonl_file, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            try:
                article = json.loads(line.strip())
                disease_id = article.get("id", f"unknown_{line_num}")
                title = article.get("title", "").replace("症状_病因_治疗方法_鉴别_专家咨询|丁香医生", "").strip()

                content = article.get("content", "")
                if not content or len(content) < 100:
                    continue

                # 清理内容
                content = re.sub(r'下载 App 请登录 注册.*?(?=丁香医生|$)', '', content)
                content = re.sub(r'丁香医生.*?审核.*?通过', '', content)
                content = re.sub(r'词条作者.*?团队', '', content)
                content = re.sub(r'审核专家.*?发布', '', content)
                content = re.sub(r'\s+', ' ', content).strip()

                if len(content) < 100:
                    continue

                # 分块
                text_chunks = chunk_text(content)

                for i, chunk in enumerate(text_chunks):
                    chunks.append(TextChunk(
                        content=f"【{title}】\n{chunk}",
                        metadata={
                            "file_name": file_name,
                            "source": "dxy",
                            "source_name": title,
                            "url": article.get("url", ""),
                            "disease_id": disease_id,
                            "chunk_index": i,
                            "file_type": "jsonl",
                        }
                    ))

            except json.JSONDecodeError as e:
                logger.warning(f"JSON 解析错误 (line {line_num}): {e}")
                continue

    if not chunks:
        logger.info("没有新内容需要导入")
        return {"skipped": 1, "imported": 0}

    # 导入
    chunk_objects = chunks
    texts = [c.content for c in chunk_objects]
    metadatas = [c.metadata for c in chunk_objects]

    logger.info(f"准备导入 {len(texts)} 个文本块...")

    # 批量向量化
    from app.rag.embeddings import embed_texts
    embeddings = embed_texts(texts)

    import uuid
    ids = [str(uuid.uuid4()) for _ in texts]

    vs.collection.add(
        documents=texts,
        embeddings=embeddings,
        metadatas=metadatas,
        ids=ids,
    )

    logger.info(f"✅ 丁香园导入成功: {len(chunks)} 个文本块")

    return {"skipped": 0, "imported": len(chunks)}


def import_xywy_txt(vs, existing_files: set) -> dict:
    """导入寻医问药网 TXT 数据"""
    logger.info("\n" + "="*60)
    logger.info("导入寻医问药网眼科数据")
    logger.info("="*60)

    txt_files = list(CHINESE_MEDICAL_DIR.glob("xywy_*.txt"))
    logger.info(f"找到 {len(txt_files)} 个 xywy 文件")

    total_chunks = 0
    skipped_files = 0

    for txt_file in txt_files:
        file_name = txt_file.name

        if file_name in existing_files:
            logger.info(f"已存在，跳过: {file_name}")
            skipped_files += 1
            continue

        try:
            content = txt_file.read_text(encoding='utf-8')
            if len(content) < 100:
                continue

            # 提取标题
            title = file_name.replace("xywy_", "").replace("_", " ").replace(".txt", "")
            match = re.search(r'_(\d+)_(.+)\.txt', file_name)
            if match:
                disease_id = match.group(1)
                title = match.group(2).replace("_", " ")

            # 分块
            text_chunks = chunk_text(content)

            if not text_chunks:
                continue

            chunks = []
            for i, chunk in enumerate(text_chunks):
                chunks.append(TextChunk(
                    content=f"【{title}】\n{chunk}",
                    metadata={
                        "file_name": file_name,
                        "source": "xywy",
                        "source_name": title,
                        "disease_id": disease_id if 'disease_id' in locals() else "",
                        "chunk_index": i,
                        "file_type": "txt",
                    }
                ))

            # 导入
            if chunks:
                texts = [c.content for c in chunks]
                metadatas = [c.metadata for c in chunks]

                from app.rag.embeddings import embed_texts
                embeddings = embed_texts(texts)

                import uuid
                ids = [str(uuid.uuid4()) for _ in texts]

                vs.collection.add(
                    documents=texts,
                    embeddings=embeddings,
                    metadatas=metadatas,
                    ids=ids,
                )

                total_chunks += len(chunks)
                logger.info(f"  ✅ {file_name}: {len(chunks)} 块")

        except Exception as e:
            logger.warning(f"导入失败 {file_name}: {e}")

    logger.info(f"✅ 寻医问药网导入完成: {total_chunks} 个文本块, {skipped_files} 个已跳过")

    return {"skipped": skipped_files, "imported": total_chunks}


def import_wiki_txt(vs, existing_files: set) -> dict:
    """导入 Wikipedia TXT 数据"""
    logger.info("\n" + "="*60)
    logger.info("导入 Wikipedia 眼科数据")
    logger.info("="*60)

    txt_files = list(WIKI_DIR.glob("*.txt"))
    logger.info(f"找到 {len(txt_files)} 个 wiki 文件")

    total_chunks = 0
    skipped_files = 0

    for txt_file in txt_files:
        file_name = txt_file.name

        if file_name in existing_files:
            logger.info(f"已存在，跳过: {file_name}")
            skipped_files += 1
            continue

        try:
            content = txt_file.read_text(encoding='utf-8')
            if len(content) < 100:
                continue

            # 提取标题
            title = file_name.replace(".txt", "").replace("_", " ")

            # 分块
            text_chunks = chunk_text(content)

            if not text_chunks:
                continue

            chunks = []
            for i, chunk in enumerate(text_chunks):
                chunks.append(TextChunk(
                    content=f"【{title}】\n{chunk}",
                    metadata={
                        "file_name": file_name,
                        "source": "wikipedia",
                        "source_name": title,
                        "chunk_index": i,
                        "file_type": "txt",
                    }
                ))

            # 导入
            if chunks:
                texts = [c.content for c in chunks]
                metadatas = [c.metadata for c in chunks]

                from app.rag.embeddings import embed_texts
                embeddings = embed_texts(texts)

                import uuid
                ids = [str(uuid.uuid4()) for _ in texts]

                vs.collection.add(
                    documents=texts,
                    embeddings=embeddings,
                    metadatas=metadatas,
                    ids=ids,
                )

                total_chunks += len(chunks)
                logger.info(f"  ✅ {file_name}: {len(chunks)} 块")

        except Exception as e:
            logger.warning(f"导入失败 {file_name}: {e}")

    logger.info(f"✅ Wikipedia 导入完成: {total_chunks} 个文本块, {skipped_files} 个已跳过")

    return {"skipped": skipped_files, "imported": total_chunks}


def main():
    logger.info("""
    ╔══════════════════════════════════════════════════════╗
    ║       眼科知识库数据导入脚本                          ║
    ╚══════════════════════════════════════════════════════╝
    """)

    vs = get_vector_store()

    # 检查现有数据
    existing_files = get_existing_files(vs)
    logger.info(f"向量库中已存在 {len(existing_files)} 个文档")

    # 统计导入结果
    total_imported = 0
    total_skipped = 0

    # 1. 丁香园数据
    dxy_result = import_dxy_jsonl(vs, existing_files)
    total_imported += dxy_result["imported"]
    total_skipped += dxy_result["skipped"]
    existing_files.add("dxy_yanke_articles.jsonl")

    # 2. 寻医问药网数据
    xywy_result = import_xywy_txt(vs, existing_files)
    total_imported += xywy_result["imported"]
    total_skipped += xywy_result["skipped"]

    # 3. Wikipedia 数据
    wiki_result = import_wiki_txt(vs, existing_files)
    total_imported += wiki_result["imported"]
    total_skipped += wiki_result["skipped"]

    # 最终统计
    logger.info("\n" + "="*60)
    logger.info("导入完成汇总")
    logger.info("="*60)
    logger.info(f"  本次新增文本块: {total_imported}")
    logger.info(f"  跳过的文档数  : {total_skipped}")
    logger.info(f"  当前向量库总量: {vs.collection.count()}")

    # 按来源统计
    all_docs = vs.list_documents()
    source_counts = {}
    for doc in all_docs:
        src = doc.get("source", "unknown")
        source_counts[src] = source_counts.get(src, 0) + 1

    logger.info(f"\n各来源文档数:")
    for src, count in sorted(source_counts.items()):
        logger.info(f"  {src}: {count}")


if __name__ == "__main__":
    main()
