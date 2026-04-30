#!/usr/bin/env python3
"""
眼科知识库向量数据库评估脚本
功能：
  1. 数据规模统计（块数、文档覆盖度、来源分布）
  2. 数据质量分析（块长度分布、内容重复检测、缺失字段检查）
  3. 检索质量评估（多维度查询得分、召回率、Top-K 准确性）
  4. 向量维度与模型信息
"""

import sys
import json
import statistics
from pathlib import Path

# 确保 backend 在路径中
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.rag.vector_store import get_vector_store
from app.rag.embeddings import embed_query, embed_texts
from app.config import get_settings

settings = get_settings()


def print_header(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def eval_scale(vs) -> dict:
    """评估数据规模"""
    print_header("📊 数据规模统计")

    stats = vs.get_stats()
    print(f"  Collection 名称 : {stats['collection_name']}")
    print(f"  总向量块数      : {stats['total_chunks']:,}")
    print(f"  覆盖文档数      : {stats['document_count']:,}")

    docs = vs.list_documents()
    if not docs:
        return {}

    # 按来源分组
    pmc_docs = [d for d in docs if d["source"] == "pmc"]
    wiki_docs = [d for d in docs if d["source"] == "wikipedia"]

    print(f"\n  来源分布:")
    print(f"    PMC 论文     : {len(pmc_docs):,} 篇文档")
    print(f"    Wikipedia    : {len(wiki_docs):,} 篇文档")

    # 每篇文档平均块数
    avg_chunks = stats["total_chunks"] / max(stats["document_count"], 1)
    print(f"\n  每文档平均块数  : {avg_chunks:.1f}")

    # 块数最多/最少的文档
    sorted_docs = sorted(docs, key=lambda x: x["chunk_count"], reverse=True)
    print(f"\n  块数最多的 5 篇文档:")
    for d in sorted_docs[:5]:
        print(f"    [{d['chunk_count']:4d}] {d['file_name'][:50]}")

    print(f"\n  块数最少的 5 篇文档:")
    for d in sorted_docs[-5:]:
        print(f"    [{d['chunk_count']:4d}] {d['file_name'][:50]}")

    return {
        "total_chunks": stats["total_chunks"],
        "document_count": stats["document_count"],
        "pmc_count": len(pmc_docs),
        "wiki_count": len(wiki_docs),
        "avg_chunks_per_doc": avg_chunks,
    }


def eval_quality(vs) -> dict:
    """评估数据质量"""
    print_header("🔍 数据质量分析")

    total = vs.collection.count()
    if total == 0:
        print("  集合为空，跳过质量分析")
        return {}

    # 抽样 1000 条（避免一次加载全部）
    sample_size = min(1000, total)
    results = vs.collection.get(include=["documents", "metadatas"], limit=total)

    docs = results.get("documents", [])
    metas = results.get("metadatas", [])

    # 随机抽样（固定种子保证可复现）
    import random
    random.seed(42)
    if len(docs) > sample_size:
        indices = random.sample(range(len(docs)), sample_size)
        docs = [docs[i] for i in indices]
        metas = [metas[i] for i in indices]

    # 1. 块长度分布
    lengths = [len(d) for d in docs]
    print(f"\n  文本块长度统计 (n={len(docs)}):")
    print(f"    平均长度  : {statistics.mean(lengths):.1f} 字符")
    print(f"    中位数    : {statistics.median(lengths):.1f} 字符")
    print(f"    最小长度  : {min(lengths)} 字符")
    print(f"    最大长度  : {max(lengths)} 字符")
    print(f"    标准差    : {statistics.stdev(lengths):.1f}")

    # 2. 过短块检测（< 50 字符可能是噪声）
    short_blocks = [d for d in docs if len(d) < 50]
    print(f"\n  过短块检测 (<50字符): {len(short_blocks)} / {len(docs)} "
          f"({100*len(short_blocks)/len(docs):.2f}%)")

    # 3. 缺失字段检查
    required_fields = ["file_name", "source"]
    print(f"\n  字段完整性检查:")
    for field in required_fields:
        missing = sum(1 for m in metas if not m.get(field))
        print(f"    {field:<15}: {missing}/{len(metas)} 缺失 "
              f"({100*missing/len(metas):.2f}%)")

    # 4. 内容重复检测（相似内容块）
    print(f"\n  内容重复检测 (前100条抽样):")
    sample_for_dedup = docs[:100]
    embeddings = embed_texts(sample_for_dedup)
    import numpy as np
    emb_matrix = np.array(embeddings)
    # 计算余弦相似度矩阵（已归一化）
    sim_matrix = np.dot(emb_matrix, emb_matrix.T)
    np.fill_diagonal(sim_matrix, 0)
    high_sim_pairs = np.sum(sim_matrix > 0.98)
    print(f"    高相似对 (>0.98): {high_sim_pairs} 对 (可能重复)")

    # 5. 唯一文档数 vs 总块数
    file_names = set(m.get("file_name") for m in metas)
    dup_rate = (len(docs) - len(file_names)) / max(len(docs), 1) * 100
    print(f"\n  文档去重率估算:")
    print(f"    唯一文件名: {len(file_names)}")
    print(f"    总记录数  : {len(docs)}")
    print(f"    重复率    : {dup_rate:.2f}%")

    return {
        "avg_length": statistics.mean(lengths),
        "median_length": statistics.median(lengths),
        "short_block_pct": 100 * len(short_blocks) / len(docs),
        "high_sim_pairs": int(high_sim_pairs),
        "unique_docs": len(file_names),
    }


def eval_retrieval(vs) -> dict:
    """评估检索质量"""
    print_header("🎯 检索质量评估")

    # 定义多维度测试查询
    test_queries = [
        # 眼病类
        ("What is glaucoma?", ["glaucoma", "optic nerve", "intraocular pressure"]),
        ("How to treat diabetic retinopathy?", ["diabetic retinopathy", "treatment", "anti-VEGF"]),
        ("Cataract surgery methods", ["cataract", "surgery", "phacoemulsification"]),
        ("Age-related macular degeneration", ["macular degeneration", "AMD", "drusen"]),
        ("Dry eye disease causes", ["dry eye", "tear film", "ocular surface"]),
        # 治疗方法类
        ("Anti-VEGF therapy for retinal diseases", ["anti-VEGF", "ranibizumab", "bevacizumab", "aflibercept"]),
        ("LASIK surgery procedure", ["LASIK", "refractive", "corneal flap"]),
        # 眼部结构类
        ("Retina anatomy and function", ["retina", "photoreceptor", "fovea"]),
        ("Optic nerve diseases", ["optic nerve", "papilledema", "neuritis"]),
        # 手术类
        ("Corneal transplant types", ["corneal transplant", "keratoplasty", "endothelial"]),
    ]

    scores = []
    recall_details = []

    for query, expected_keywords in test_queries:
        results = vs.search(query, top_k=5)
        if not results:
            print(f"\n  ⚠️  查询无结果: {query}")
            continue

        top_scores = [r["score"] for r in results]
        top_contents = " ".join([r["content"].lower() for r in results])

        # 计算召回率（关键词覆盖率）
        keywords_found = sum(1 for kw in expected_keywords if kw.lower() in top_contents)
        recall = keywords_found / len(expected_keywords)

        # 平均得分
        avg_score = statistics.mean(top_scores)

        scores.append(avg_score)
        recall_details.append({
            "query": query,
            "top1_score": top_scores[0],
            "avg_score": avg_score,
            "recall": recall,
            "keywords_found": f"{keywords_found}/{len(expected_keywords)}",
        })

        status = "✅" if avg_score > 0.75 else ("⚠️" if avg_score > 0.60 else "❌")
        print(f"\n  {status} 查询: {query[:40]}")
        print(f"      Top-1 得分: {top_scores[0]:.4f} | "
              f"平均得分: {avg_score:.4f} | "
              f"召回率: {recall:.2f} | "
              f"关键词: {keywords_found}/{len(expected_keywords)}")

    if not scores:
        return {}

    print(f"\n  ─── 汇总统计 ───")
    print(f"    查询总数      : {len(scores)}")
    print(f"    平均 Top-1 得分: {statistics.mean([r['top1_score'] for r in recall_details]):.4f}")
    print(f"    平均检索得分  : {statistics.mean(scores):.4f}")
    print(f"    得分标准差    : {statistics.stdev(scores):.4f}")
    print(f"    得分范围      : {min(scores):.4f} ~ {max(scores):.4f}")
    print(f"    高分查询率(>0.8): {sum(1 for s in scores if s > 0.8)}/{len(scores)}")
    print(f"    召回率均值    : {statistics.mean([r['recall'] for r in recall_details]):.2f}")

    return {
        "total_queries": len(scores),
        "avg_top1_score": statistics.mean([r["top1_score"] for r in recall_details]),
        "avg_score": statistics.mean(scores),
        "score_std": statistics.stdev(scores),
        "score_min": min(scores),
        "score_max": max(scores),
        "high_score_rate": sum(1 for s in scores if s > 0.8) / len(scores),
        "avg_recall": statistics.mean([r["recall"] for r in recall_details]),
    }


def eval_model_info() -> dict:
    """获取嵌入模型信息"""
    print_header("🤖 嵌入模型信息")

    from app.rag.embeddings import get_embedding_model
    model = get_embedding_model()

    model_name = settings.embedding_model_name
    custom_path = settings.embedding_model_path

    print(f"  模型名称      : {model_name}")
    print(f"  自定义路径    : {custom_path or '未配置 (使用通用模型)'}")

    # 测试向量维度
    test_vec = embed_query("test")
    dim = len(test_vec)
    print(f"  向量维度      : {dim}")

    return {
        "model_name": model_name,
        "custom_path": custom_path,
        "embedding_dim": dim,
    }


def main():
    print("""
    ╔══════════════════════════════════════════════════════╗
    ║     眼科知识库向量数据库评估报告                      ║
    ╚══════════════════════════════════════════════════════╝
    """)

    vs = get_vector_store()

    # 1. 规模评估
    scale = eval_scale(vs)

    # 2. 质量评估
    quality = eval_quality(vs)

    # 3. 检索评估
    retrieval = eval_retrieval(vs)

    # 4. 模型信息
    model_info = eval_model_info()

    # 最终汇总
    print_header("📋 评估总结")

    report = {
        "scale": scale,
        "quality": quality,
        "retrieval": retrieval,
        "model": model_info,
    }

    # 打印 JSON 摘要
    print(json.dumps(report, ensure_ascii=False, indent=2))

    # 健康度评分
    health_score = 0
    factors = []

    if retrieval.get("avg_score", 0) > 0.75:
        health_score += 40
        factors.append("检索得分优秀 (+40)")
    elif retrieval.get("avg_score", 0) > 0.60:
        health_score += 25
        factors.append("检索得分一般 (+25)")
    else:
        factors.append("检索得分偏低")

    if quality.get("short_block_pct", 100) < 5:
        health_score += 20
        factors.append("块长度质量良好 (+20)")
    elif quality.get("short_block_pct", 100) < 10:
        health_score += 10
        factors.append("存在少量过短块 (+10)")

    if quality.get("high_sim_pairs", 0) < 50:
        health_score += 20
        factors.append("内容重复率低 (+20)")

    if scale.get("total_chunks", 0) >= 10000:
        health_score += 20
        factors.append("数据规模充足 (+20)")

    print(f"\n  🏥 健康度评分: {health_score}/100")
    for f in factors:
        print(f"    {f}")

    print(f"\n{'='*60}")
    print("  评估完成")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
