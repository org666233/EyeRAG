"""
知识库批量导入脚本
运行方式:
  cd backend && python scripts/ingest.py
  python scripts/ingest.py --dir data/documents --strategy recursive
  python scripts/ingest.py --dir data/documents --chunk-size 512 --overlap 50

多模型支持:
  每个模型需要单独的向量库存放目录，通过环境变量配置:
    CHROMA_PERSIST_DIR=chroma_db_modelname
    CHROMA_COLLECTION_NAME=collection_name
    EMBEDDING_MODEL_NAME=model/path
    USE_BIOBERT=false
"""

import sys
import os
import argparse
import json
import tempfile
import subprocess
from pathlib import Path

# 将 backend 目录加入 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))


def resolve_documents_dir(arg_dir: str) -> Path:
    """支持相对路径和绝对路径，相对路径相对于 backend/"""
    p = Path(arg_dir)
    if p.is_absolute():
        return p
    return (Path(__file__).parent.parent / p).resolve()


def resolve_chroma_dir(env_dir: str | None) -> str:
    """将相对路径转换为相对于 backend/ 的绝对路径"""
    if not env_dir:
        return "chroma_db"
    p = Path(env_dir)
    if p.is_absolute():
        return env_dir
    return str((Path(__file__).parent.parent / p).resolve())


# ─────────────────────────────────────────────
# 评测模型配置（与 benchmark_embeddings.py 保持同步）
# ─────────────────────────────────────────────
MODEL_CONFIGS = [
    {
        "id": "minilm-384",
        "name": "all-MiniLM-L6-v2",
        "desc": "MiniLM-L6 / 384维 / 英文通用基线",
        "env": {
            "EMBEDDING_MODEL_NAME": "sentence-transformers/all-MiniLM-L6-v2",
            "EMBEDDING_MODEL_PATH": "",
            "USE_BIOBERT": "false",
            "CHROMA_HOST": "",
            "CHROMA_PERSIST_DIR": "chroma_db_minilm_384",
            "CHROMA_COLLECTION_NAME": "ophthalmology_docs_minilm_384",
        },
    },
    {
        "id": "medbert-base-chinese",
        "name": "trueto/medbert-base-chinese",
        "desc": "MedBERT 中文临床医学 / 768维 / 医学领域 BERT",
        "env": {
            "EMBEDDING_MODEL_NAME": "trueto/medbert-base-chinese",
            "EMBEDDING_MODEL_PATH": "",
            "USE_BIOBERT": "false",
            "CHROMA_HOST": "",
            "CHROMA_PERSIST_DIR": "chroma_db",
            "CHROMA_COLLECTION_NAME": "ophthalmology_docs",
        },
    },
    {
        "id": "bge-base-zh-v1.5",
        "name": "BAAI/bge-base-zh-v1.5",
        "desc": "BGE-Base-ZH / 768维 / 中文通用旗舰向量模型",
        "env": {
            "EMBEDDING_MODEL_NAME": "BAAI/bge-base-zh-v1.5",
            "EMBEDDING_MODEL_PATH": "./model/bge-base-zh-v1.5",
            "USE_BIOBERT": "false",
            "CHROMA_HOST": "",
            "CHROMA_PERSIST_DIR": "chroma_db_bge_base_zh",
            "CHROMA_COLLECTION_NAME": "ophthalmology_docs_bge_base_zh",
        },
    },
    {
        "id": "bge-large-zh-v1.5",
        "name": "BAAI/bge-large-zh-v1.5",
        "desc": "BGE-Large-ZH / 1024维 / 中文通用最强向量模型",
        "env": {
            "EMBEDDING_MODEL_NAME": "BAAI/bge-large-zh-v1.5",
            "EMBEDDING_MODEL_PATH": "./model/bge-large-zh-v1.5",
            "USE_BIOBERT": "false",
            "CHROMA_HOST": "",
            "CHROMA_PERSIST_DIR": "chroma_db_bge_large_zh",
            "CHROMA_COLLECTION_NAME": "ophthalmology_docs_bge_large_zh",
        },
    },
    {
        "id": "bge-m3",
        "name": "BAAI/bge-m3",
        "desc": "BGE-M3 / 1024维 / 多语言（支持中英日韩等）旗舰模型",
        "env": {
            "EMBEDDING_MODEL_NAME": "BAAI/bge-m3",
            "EMBEDDING_MODEL_PATH": "./model/bge-m3",
            "USE_BIOBERT": "false",
            "CHROMA_HOST": "",
            "CHROMA_PERSIST_DIR": "chroma_db_bge_m3",
            "CHROMA_COLLECTION_NAME": "ophthalmology_docs_bge_m3",
        },
    },
    {
        "id": "text2vec-base-chinese",
        "name": "shibing624/text2vec-base-chinese",
        "desc": "Text2Vec / 768维 / 中文语义匹配专用模型",
        "env": {
            "EMBEDDING_MODEL_NAME": "shibing624/text2vec-base-chinese",
            "EMBEDDING_MODEL_PATH": "./model/text2vec-base-chinese",
            "USE_BIOBERT": "false",
            "CHROMA_HOST": "",
            "CHROMA_PERSIST_DIR": "chroma_db_text2vec",
            "CHROMA_COLLECTION_NAME": "ophthalmology_docs_text2vec",
        },
    },
    {
        "id": "gpt-multitask",
        "name": "sentence-transformers/gtr-t5-xl",
        "desc": "GTR-XL / 768维 / OpenAI 多任务检索大规模模型",
        "env": {
            "EMBEDDING_MODEL_NAME": "sentence-transformers/gtr-t5-xl",
            "EMBEDDING_MODEL_PATH": "./model/gtr-t5-xl",
            "USE_BIOBERT": "false",
            "CHROMA_HOST": "",
            "CHROMA_PERSIST_DIR": "chroma_db_gpt_multitask",
            "CHROMA_COLLECTION_NAME": "ophthalmology_docs_gpt_multitask",
        },
    },
]


# ─────────────────────────────────────────────
# 工具函数
# ─────────────────────────────────────────────
def _build_child_env(model_env: dict) -> dict:
    """从当前环境副本 + 模型专属配置，返回干净的子进程环境"""
    child_env = os.environ.copy()
    child_env.update(model_env)
    # 空字符串覆盖时确保 CHROMA_HOST 被删除而非保留空值
    if model_env.get("CHROMA_HOST", "") == "":
        child_env.pop("CHROMA_HOST", None)
    return child_env


def _clear_module_caches():
    """清除 embedding / vector_store 模块的全局缓存，强制重新加载"""
    from app.config import get_settings
    get_settings.cache_clear()

    import app.rag.embeddings as emb_mod
    emb_mod._embedding_model = None
    emb_mod._embedding_model_name = None
    emb_mod._embedding_model_type = None

    import app.rag.vector_store as vs_mod
    vs_mod._chroma_client = None
    vs_mod._collection = None
    vs_mod._vector_store = None


def _ingest_single_model(
    model_cfg: dict,
    doc_dir: Path,
    chunk_size: int,
    chunk_overlap: int,
    clear_before: bool,
) -> bool:
    """
    在子进程中为单个模型执行完整的导入流程。
    返回 True 表示成功，False 表示失败。
    """
    backend_root = str(Path(__file__).parent.parent)
    child_env = _build_child_env(model_cfg["env"])

    chroma_dir_abs = resolve_chroma_dir(model_cfg["env"].get("CHROMA_PERSIST_DIR"))
    collection = model_cfg["env"].get("CHROMA_COLLECTION_NAME", "ophthalmology_docs")
    doc_dir_abs = str(doc_dir.resolve())

    script = f"""
import sys, time, json
sys.path.insert(0, {repr(backend_root)}

# 清除模块缓存
from app.config import get_settings
get_settings.cache_clear()

import app.rag.embeddings as _emb
_emb._embedding_model = None
_emb._embedding_model_name = None
_emb._embedding_model_type = None

import app.rag.vector_store as _vs
_vs._chroma_client = None
_vs._collection = None
_vs._vector_store = None

from app.utils.logger import logger
from app.rag.document_loader import DocumentLoader
from app.rag.text_splitter import RecursiveCharacterTextSplitter
from app.rag.vector_store import VectorStore
from app.config import get_settings
from pathlib import Path

settings = get_settings()
doc_dir = Path({repr(doc_dir_abs)})

# ── 加载文档 ──────────────────────────────────────
loader = DocumentLoader()
documents = loader.load_directory(doc_dir, recursive=True)
if not documents:
    print("__RESULT_JSON__" + json.dumps({{"ok": False, "error": "no documents found"}}, ensure_ascii=False) + "__RESULT_JSON__")
    sys.exit(0)

# ── 文本分块 ──────────────────────────────────────
splitter = RecursiveCharacterTextSplitter(
    chunk_size={chunk_size},
    chunk_overlap={chunk_overlap},
)
chunks = splitter.split_documents(documents)

# ── 清空（可选）────────────────────────────────────
if {str(clear_before).lower()}:
    from app.rag.vector_store import get_chroma_client
    client = get_chroma_client()
    try:
        client.delete_collection({repr(collection)})
    except Exception:
        pass

# ── 存入向量库 ─────────────────────────────────────
vs = VectorStore()
# 预热（触发模型加载）
vs.search("warmup", top_k=1)

BATCH_SIZE = 100
total_stored = 0
for i in range(0, len(chunks), BATCH_SIZE):
    batch = chunks[i:i + BATCH_SIZE]
    stored = vs.add_documents(batch)
    total_stored += stored

stats = vs.get_stats()
print("__RESULT_JSON__" + json.dumps({{
    "ok": True,
    "model_id": {json.dumps(model_cfg["id"])},
    "model_name": {json.dumps(model_cfg["name"])},
    "total_chunks": len(chunks),
    "stored_vectors": total_stored,
    "collection": stats.get("collection_name", ""),
}}, ensure_ascii=False) + "__RESULT_JSON__")
"""

    tmp = tempfile.NamedTemporaryFile(mode="w", suffix="_ingest.py", delete=False, encoding="utf-8")
    tmp.write(script)
    tmp.close()

    try:
        proc = subprocess.run(
            [sys.executable, tmp.name],
            capture_output=True, text=True,
            cwd=backend_root,
            env=child_env,
            timeout=3600,          # 最多等待 1 小时（首次下载模型）
        )
        raw = proc.stdout
        if proc.returncode != 0:
            print(f"    进程错误 ({proc.returncode}): {proc.stderr.strip().splitlines()[-1] if proc.stderr.strip().splitlines() else ''}")
            return False

        marker = "__RESULT_JSON__"
        s = raw.find(marker) + len(marker)
        e = raw.rfind(marker)
        if s < len(marker) or e < 0:
            print(f"    解析失败，原始输出: {raw[-300:]}")
            return False

        result = json.loads(raw[s:e])
        if not result.get("ok"):
            print(f"    导入失败: {result.get('error', 'unknown')}")
            return False

        print(f"    ✅ 文档加载 {result['total_chunks']} 块 → "
              f"向量库存储 {result['stored_vectors']} 条 "
              f"(collection={result['collection']})")
        return True

    except subprocess.TimeoutExpired:
        print(f"    ⏰ 超时（1小时），模型 {model_cfg['name']} 导入中断")
        return False
    finally:
        os.unlink(tmp.name)


# ─────────────────────────────────────────────
# CLI 入口
# ─────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="眼科知识库文档导入脚本（支持多模型向量库并行导入）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 单模型导入（使用当前环境变量配置的模型）
  python scripts/ingest.py

  # 单模型导入（显式指定文档目录和分块参数）
  python scripts/ingest.py --dir data/documents --chunk-size 512 --overlap 50

  # 多模型并行导入（遍历全部 MODEL_CONFIGS，为每个模型构建独立向量库）
  python scripts/ingest.py --all-models

  # 仅导入特定模型
  python scripts/ingest.py --all-models --model-ids minilm-384 bge-base-zh-v1.5
"""
    )
    parser.add_argument("--dir", default="data/documents", help="文档目录路径（相对于 backend/）")
    parser.add_argument(
        "--strategy", choices=["recursive", "semantic"],
        default="recursive", help="分块策略"
    )
    parser.add_argument("--chunk-size", type=int, default=512, help="分块大小（字符数）")
    parser.add_argument("--chunk-overlap", type=int, default=50, help="相邻块重叠字符数")
    parser.add_argument("--clear", action="store_true", help="导入前清空现有向量库")

    # ── 多模型选项 ──────────────────────────────────
    parser.add_argument(
        "--all-models", action="store_true",
        help="遍历 MODEL_CONFIGS 中的全部模型，分别为每个模型构建独立向量库"
    )
    parser.add_argument(
        "--model-ids", nargs="+",
        help="配合 --all-models 使用：只导入指定 id 的模型（如 minilm-384 bge-base-zh-v1.5）"
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="配合 --all-models 使用：若向量库目录已存在则跳过该模型"
    )

    args = parser.parse_args()

    # ── 文档目录解析 ─────────────────────────────────
    doc_dir = resolve_documents_dir(args.dir)
    if not doc_dir.is_dir():
        print(f"❌ 文档目录不存在: {doc_dir}")
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"  眼科知识库导入工具  (chunk={args.chunk_size}, overlap={args.chunk_overlap})")
    print(f"{'='*60}")
    print(f"  文档目录: {doc_dir}")
    print(f"  分块策略: {args.strategy}")
    print(f"  块大小:   {args.chunk_size} 字符")
    print(f"  重叠大小: {args.chunk_overlap} 字符")
    print(f"{'='*60}\n")

    # ════════════════════════════════════════════════
    # 多模型导入模式
    # ════════════════════════════════════════════════
    if args.all_models:
        # 筛选目标模型
        if args.model_ids:
            target_models = [m for m in MODEL_CONFIGS if m["id"] in args.model_ids]
            if not target_models:
                print(f"❌ 未找到匹配的模型 id: {args.model_ids}")
                print(f"   可用 id: {[m['id'] for m in MODEL_CONFIGS]}")
                sys.exit(1)
        else:
            target_models = MODEL_CONFIGS

        print(f"多模型导入模式：{len(target_models)} 个模型")
        print("-" * 60)

        total_ok, total_fail = 0, 0
        for i, m in enumerate(target_models):
            print(f"\n[{i+1}/{len(target_models)}] {m['name']}  ({m['desc']})")
            print(f"  向量库目录: {resolve_chroma_dir(m['env'].get('CHROMA_PERSIST_DIR'))}")
            print(f"  Collection: {m['env'].get('CHROMA_COLLECTION_NAME')}")

            chroma_dir_abs = resolve_chroma_dir(m["env"].get("CHROMA_PERSIST_DIR"))
            if args.skip_existing and Path(chroma_dir_abs).exists():
                # 快速检查 collection 是否非空
                try:
                    import app.rag.vector_store as vs_mod
                    vs_mod._chroma_client = None
                    vs_mod._collection = None
                    vs_mod._vector_store = None
                    child_env = _build_child_env(m["env"])
                    tmp2 = tempfile.NamedTemporaryFile(
                        mode="w", suffix="_check.py", delete=False
                    )
                    tmp2.write(f"""
import sys; sys.path.insert(0, {repr(str(Path(__file__).parent.parent))})
from app.rag.vector_store import VectorStore
vs = VectorStore()
stats = vs.get_stats()
print(stats.get('total_chunks', 0))
""")
                    tmp2.close()
                    proc = subprocess.run(
                        [sys.executable, tmp2.name],
                        capture_output=True, text=True,
                        cwd=str(Path(__file__).parent.parent),
                        env=child_env, timeout=60,
                    )
                    n = int(proc.stdout.strip().splitlines()[-1]) if proc.stdout.strip() else 0
                    os.unlink(tmp2.name)
                    if n > 0:
                        print(f"  ⏭️  已存在 {n} 条向量，跳过（使用 --skip-existing）")
                        total_ok += 1
                        continue
                except Exception:
                    pass

            ok = _ingest_single_model(
                model_cfg=m,
                doc_dir=doc_dir,
                chunk_size=args.chunk_size,
                chunk_overlap=args.chunk_overlap,
                clear_before=args.clear,
            )
            if ok:
                total_ok += 1
            else:
                total_fail += 1

        print(f"\n{'='*60}")
        print(f"✅ 多模型导入完成: {total_ok} 成功 / {total_fail} 失败")
        print(f"{'='*60}\n")
        return

    # ════════════════════════════════════════════════
    # 单模型导入（原有逻辑，使用当前进程环境）
    # ════════════════════════════════════════════════
    from app.utils.logger import logger
    from app.rag.document_loader import DocumentLoader
    from app.rag.text_splitter import RecursiveCharacterTextSplitter
    from app.rag.vector_store import VectorStore
    from app.config import get_settings
    settings = get_settings()

    if args.clear:
        confirm = input("⚠️  确认清空现有知识库? (yes/no): ")
        if confirm.lower() == "yes":
            from app.rag.vector_store import get_chroma_client
            client = get_chroma_client()
            col_name = settings.chroma_collection_name
            try:
                client.delete_collection(col_name)
                print(f"✅ Collection '{col_name}' 已删除\n")
            except Exception:
                pass
            import app.rag.vector_store as vs_module
            vs_module._collection = client.get_or_create_collection(
                name=col_name,
                metadata={"hnsw:space": "cosine"},
            )
            print(f"✅ Collection '{col_name}' 已重建\n")

    print("[Step 1] 加载文档...")
    doc_loader = DocumentLoader()
    documents = doc_loader.load_directory(doc_dir, recursive=True)
    if not documents:
        print("❌ 未找到任何文档，请先运行 download_data.py 下载眼科数据")
        sys.exit(0)
    print(f"  → 共加载 {len(documents)} 个文档片段\n")

    print(f"[Step 2] 文本分块 (策略: {args.strategy})...")
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
    )
    chunks = splitter.split_documents(documents)
    print(f"  → 共生成 {len(chunks)} 个文本块\n")

    source_counts = {}
    for c in chunks:
        src = c.metadata.get("file_type", "unknown")
        source_counts[src] = source_counts.get(src, 0) + 1
    for src, count in source_counts.items():
        print(f"     {src}: {count} 块")

    print(f"\n[Step 3] 向量化存储 (这可能需要几分钟)...")
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

    print(f"\n  → 成功存储 {total_stored} 个向量块到 ChromaDB\n")

    stats = vs.get_stats()
    print(f"{'='*60}")
    print(f"✅ 导入完成!")
    print(f"   总文档数:    {stats['total_documents']}")
    print(f"   总向量块数:  {stats['total_chunks']}")
    print(f"   Collection: {stats['collection_name']}")
    print(f"{'='*60}\n")

    print("[Step 4] 检索测试...")
    test_queries = [
        "What is glaucoma?",
        "diabetic retinopathy treatment",
        "cataract surgery"
    ]
    for q in test_queries:
        results = vs.search(q, top_k=2)
        if results:
            top = results[0]
            print(f"  Q: {q}")
            print(f"  A: {top['content'][:120].strip()}... (score={top['score']:.3f})")
            print()


if __name__ == "__main__":
    main()
