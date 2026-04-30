#!/usr/bin/env python3
"""
向量数据库统计脚本 - 轻量版
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.rag.vector_store import get_vector_store
from app.config import get_settings

settings = get_settings()

def main():
    print("""
    ╔══════════════════════════════════════════════════════╗
    ║       眼科知识库向量数据库统计                       ║
    ╚══════════════════════════════════════════════════════╝
    """)

    vs = get_vector_store()

    # 基础统计
    total = vs.collection.count()
    print(f"\n📊 数据规模统计")
    print(f"  Collection 名称 : {settings.chroma_collection_name}")
    print(f"  总向量块数     : {total:,}")

    # 按来源统计
    print(f"\n📁 按来源统计文档数:")

    sources = {}
    batch_size = 1000
    offset = 0

    while offset < total:
        results = vs.collection.get(include=["metadatas"], limit=batch_size, offset=offset)
        if not results.get("metadatas"):
            break

        for meta in results["metadatas"]:
            src = meta.get("source", "unknown")
            fname = meta.get("file_name", "unknown")

            if src not in sources:
                sources[src] = {"files": set(), "chunks": 0}
            sources[src]["files"].add(fname)
            sources[src]["chunks"] += 1

        offset += batch_size

    for src, info in sorted(sources.items()):
        print(f"  {src:15}: {len(info['files']):4} 篇文档, {info['chunks']:6} 个文本块")

    print(f"\n  总计           : {sum(len(v['files']) for v in sources.values()):4} 篇文档, {total:,} 个文本块")

    # 文件类型分布
    print(f"\n📄 文件类型分布:")
    file_types = {}
    offset = 0
    while offset < total:
        results = vs.collection.get(include=["metadatas"], limit=batch_size, offset=offset)
        if not results.get("metadatas"):
            break
        for meta in results["metadatas"]:
            ft = meta.get("file_type", "unknown")
            file_types[ft] = file_types.get(ft, 0) + 1
        offset += batch_size

    for ft, count in sorted(file_types.items(), key=lambda x: -x[1]):
        print(f"  {ft:10}: {count:,}")

    print("\n✅ 统计完成\n")

if __name__ == "__main__":
    main()
