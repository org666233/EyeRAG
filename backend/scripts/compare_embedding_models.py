#!/usr/bin/env python3
"""
模型对比测试脚本
用于对比通用模型 vs BioBERT 的检索效果
"""

import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.rag.vector_store import get_vector_store
from app.rag.embeddings import get_embedding_model, get_current_model_info
from sentence_transformers import SentenceTransformer


# 测试查询集
TEST_QUERIES = [
    # 疾病相关
    "青光眼的治疗方法",
    "白内障手术费用",
    "干眼症症状有哪些",
    "糖尿病视网膜病变",
    "年龄相关性黄斑变性",
    # 症状相关
    "眼睛干涩怎么办",
    "视力模糊原因",
    "眼压高怎么治疗",
    # 手术相关
    "LASIK手术后遗症",
    "白内障手术后注意事项",
    # 专业术语
    "眼压 IOP",
    "AMD 是什么",
    "抗VEGF治疗",
]


def load_model(model_name: str) -> SentenceTransformer:
    """加载指定模型"""
    print(f"   正在加载: {model_name}")
    start = time.time()
    model = SentenceTransformer(model_name)
    elapsed = time.time() - start
    print(f"   加载完成，耗时: {elapsed:.2f}s")
    return model, elapsed


def search_with_model(model: SentenceTransformer, query: str, top_k: int = 5) -> list[dict]:
    """使用指定模型进行检索"""
    vs = get_vector_store()
    query_embedding = model.encode([query], normalize_embeddings=True)

    results = vs.collection.query(
        query_embeddings=query_embedding.tolist(),
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    docs = []
    if results["documents"] and results["documents"][0]:
        for doc, meta, dist, doc_id in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
            results["ids"][0],
        ):
            docs.append({
                "content": doc[:100] + "...",
                "metadata": meta,
                "score": round(1.0 - dist, 4),
                "id": doc_id,
            })
    return docs


def main():
    print("""
    ╔══════════════════════════════════════════════════════╗
    ║          嵌入模型对比测试                           ║
    ╚══════════════════════════════════════════════════════╝
    """)

    vs = get_vector_store()
    total = vs.collection.count()
    print(f"向量库规模: {total:,} 个文本块\n")

    # 模型列表
    models = {
        "通用模型 (MiniLM)": "sentence-transformers/all-MiniLM-L6-v2",
        "中文 BioBERT": "dmis-lab/biobert-base-chinese-v1.2",
    }

    results_summary = {}

    for name, model_name in models.items():
        print(f"\n{'='*60}")
        print(f"测试模型: {name}")
        print(f"模型名称: {model_name}")
        print('='*60)

        try:
            model, load_time = load_model(model_name)
            dim = model.get_sentence_embedding_dimension()
            print(f"嵌入维度: {dim}")
            print(f"加载耗时: {load_time:.2f}s\n")

            query_times = []
            query_results = {}

            for query in TEST_QUERIES:
                start = time.time()
                results = search_with_model(model, query, top_k=5)
                elapsed = (time.time() - start) * 1000
                query_times.append(elapsed)

                # 记录 Top-1 结果用于对比
                top_score = results[0]["score"] if results else 0
                top_source = results[0]["metadata"].get("file_name", "unknown")[:40] if results else "N/A"

                query_results[query] = {
                    "top_score": top_score,
                    "top_source": top_source,
                    "elapsed_ms": elapsed,
                }

                print(f"  [{elapsed:6.1f}ms] {query}")
                print(f"            最佳匹配: {top_score:.4f} | {top_source}")

            avg_time = sum(query_times) / len(query_times)
            avg_top_score = sum(r["top_score"] for r in query_results.values()) / len(query_results)

            results_summary[name] = {
                "load_time": load_time,
                "dim": dim,
                "avg_query_time": avg_time,
                "avg_top_score": avg_top_score,
                "query_results": query_results,
            }

            print(f"\n  📊 平均查询时间: {avg_time:.1f}ms")
            print(f"  📊 平均 Top-1 得分: {avg_top_score:.4f}")

        except Exception as e:
            print(f"\n  ❌ 模型加载失败: {e}")
            continue

    # 对比汇总
    if len(results_summary) >= 2:
        print("\n" + "="*60)
        print("📊 模型对比汇总")
        print("="*60)

        print(f"\n{'指标':<25} {'通用模型':<15} {'BioBERT':<15} {'差异':<10}")
        print("-"*65)

        keys = list(results_summary.keys())
        r1, r2 = results_summary[keys[0]], results_summary[keys[1]]

        print(f"{'嵌入维度':<25} {r1['dim']:<15} {r2['dim']:<15} {r2['dim']-r1['dim']:+d}")
        print(f"{'加载时间(s)':<25} {r1['load_time']:<15.2f} {r2['load_time']:<15.2f} {r2['load_time']-r1['load_time']:+.2f}")
        print(f"{'平均查询时间(ms)':<25} {r1['avg_query_time']:<15.1f} {r2['avg_query_time']:<15.1f} {r2['avg_query_time']-r1['avg_query_time']:+.1f}")
        print(f"{'平均Top-1得分':<25} {r1['avg_top_score']:<15.4f} {r2['avg_top_score']:<15.4f} {r2['avg_top_score']-r1['avg_top_score']:+.4f}")

        # 检索结果一致性分析
        print("\n📋 检索结果差异分析:")
        different = 0
        same = 0
        for query in TEST_QUERIES:
            if query in r1["query_results"] and query in r2["query_results"]:
                if r1["query_results"][query]["top_source"] == r2["query_results"][query]["top_source"]:
                    same += 1
                else:
                    different += 1

        print(f"  Top-1 结果相同: {same} 个查询")
        print(f"  Top-1 结果不同: {different} 个查询")
        print(f"  结果一致率: {same/(same+different)*100:.1f}%")

    print("\n✅ 测试完成\n")


if __name__ == "__main__":
    main()
