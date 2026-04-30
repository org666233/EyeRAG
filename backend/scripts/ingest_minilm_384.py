"""
MiniLM-384 向量库专用导入脚本
与标准 ingest.py 隔离，使用独立的 ChromaDB collection 和持久化目录。

模型: sentence-transformers/all-MiniLM-L6-v2  (384 维)
Collection: ophthalmology_docs_minilm_384
持久化目录: ./chroma_db_minilm_384

运行方式:
  cd backend && python scripts/ingest_minilm_384.py
  python scripts/ingest_minilm_384.py --dir data/documents --clear
"""

import sys
import os
import argparse
from pathlib import Path

# 强制设置独立存储路径（必须在导入 app 模块之前）
os.environ["CHROMA_PERSIST_DIR"] = "./chroma_db_minilm_384"

# 将 backend 目录加入 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))


def main():
    # 硬编码 MiniLM 模型（384 维），不依赖 .env
    MINI_LM_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
    MINI_LM_COLLECTION = "ophthalmology_docs_minilm_384"

    # 在导入 config 之前替换默认 collection 名称
    from app.config import get_settings
    settings = get_settings()
    settings.chroma_collection_name = MINI_LM_COLLECTION
    settings.embedding_model_name = MINI_LM_MODEL

    # 重置 vector_store 全局状态，确保使用新的 collection 配置
    import app.rag.vector_store as vs_module
    vs_module._chroma_client = None
    vs_module._collection = None
    vs_module._vector_store = None

    # 重置 embeddings 全局状态，确保加载 MiniLM
    import app.rag.embeddings as emb_module
    emb_module._embedding_model = None
    emb_module._embedding_model_name = None
    emb_module._embedding_model_type = None

    parser = argparse.ArgumentParser(
        description="眼科知识库导入脚本 (MiniLM-384 专用)"
    )
    parser.add_argument("--dir", default="data/documents", help="文档目录路径")
    parser.add_argument(
        "--strategy",
        choices=["recursive", "semantic"],
        default="recursive",
        help="分块策略",
    )
    parser.add_argument("--chunk-size", type=int, default=512, help="分块大小 (字符数)")
    parser.add_argument("--chunk-overlap", type=int, default=50, help="相邻块重叠字符数")
    parser.add_argument("--clear", action="store_true", help="导入前清空现有向量库")
    args = parser.parse_args()

    dir_path = Path(args.dir)
    if not dir_path.is_dir():
        print(f"  目录不存在: {dir_path}")
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"  眼科知识库导入工具 - MiniLM-384")
    print(f"{'='*60}")
    print(f"  Embedding 模型:  {MINI_LM_MODEL}  (384 维)")
    print(f"  Collection:      {MINI_LM_COLLECTION}")
    print(f"  持久化目录:      ./chroma_db_minilm_384")
    print(f"  文档目录:        {dir_path}")
    print(f"  分块策略:        {args.strategy}")
    print(f"  块大小:          {args.chunk_size} 字符")
    print(f"  重叠大小:        {args.chunk_overlap} 字符")
    print(f"{'='*60}\n")

    # 可选: 清空知识库
    if args.clear:
        confirm = input("  确认清空现有 MiniLM-384 知识库? (yes/no): ")
        if confirm.lower() == "yes":
            client = vs_module.get_chroma_client()
            try:
                client.delete_collection(MINI_LM_COLLECTION)
                print(f"  Collection '{MINI_LM_COLLECTION}' 已删除\n")
            except Exception:
                pass
            vs_module._collection = client.get_or_create_collection(
                name=MINI_LM_COLLECTION,
                metadata={"hnsw:space": "cosine"},
            )
            print(f"  Collection '{MINI_LM_COLLECTION}' 已重建\n")

    # 1. 加载文档
    print("[Step 1] 加载文档...")
    from app.rag.document_loader import DocumentLoader
    doc_loader = DocumentLoader()
    documents = doc_loader.load_directory(dir_path, recursive=True)

    if not documents:
        print("  未找到任何文档，请先运行 download_data.py 下载眼科数据")
        sys.exit(0)

    print(f"  共加载 {len(documents)} 个文档片段\n")

    # 2. 文本分块
    print(f"[Step 2] 文本分块 (策略: {args.strategy})...")
    from app.rag.text_splitter import RecursiveCharacterTextSplitter
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
    )
    chunks = splitter.split_documents(documents)
    print(f"  共生成 {len(chunks)} 个文本块\n")

    source_counts = {}
    for c in chunks:
        src = c.metadata.get("file_type", "unknown")
        source_counts[src] = source_counts.get(src, 0) + 1
    for src, count in source_counts.items():
        print(f"     {src}: {count} 块")

    # 3. 向量化并存入 ChromaDB
    print(f"\n[Step 3] 向量化存储 (这可能需要几分钟)...")
    from app.rag.vector_store import VectorStore
    vs = VectorStore()

    BATCH_SIZE = 100
    total_stored = 0
    for i in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[i:i + BATCH_SIZE]
        stored = vs.add_documents(batch)
        total_stored += stored
        progress = min(i + BATCH_SIZE, len(chunks))
        pct = progress / len(chunks) * 100
        print(f"  进度: [{progress}/{len(chunks)}] {pct:.1f}%", end="\r")

    print(f"\n  成功存储 {total_stored} 个向量块到 ChromaDB\n")

    # 4. 最终统计
    stats = vs.get_stats()
    print(f"{'='*60}")
    print(f"  导入完成!")
    print(f"   总文档数:    {stats['total_documents']}")
    print(f"   总向量块数:  {stats['total_chunks']}")
    print(f"   Collection: {stats['collection_name']}")
    print(f"   维度:        384  (MiniLM)")
    print(f"{'='*60}\n")

    # 5. 快速检索测试
    print("[Step 4] 检索测试...")
    test_queries = ["What is glaucoma?", "diabetic retinopathy treatment", "cataract surgery"]
    for q in test_queries:
        results = vs.search(q, top_k=2)
        if results:
            top = results[0]
            print(f"  Q: {q}")
            print(f"  A: {top['content'][:120].strip()}... (score={top['score']:.3f})")
            print()


if __name__ == "__main__":
    main()
