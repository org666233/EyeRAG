"""
BioBERT 嵌入模型微调
功能:
  1. 从 ChromaDB 向量库生成训练数据 (查询-文档对)
  2. 使用 SentenceTransformer 微调 BioBERT
  3. 保存微调模型供 RAG 管线使用

使用方式:
  cd backend && python scripts/finetune_embedding.py --epochs 3 --batch-size 16
  # 微调完成后，在 .env 中设置 EMBEDDING_MODEL_PATH=./models/biobert_finetuned
"""

import sys
import json
import random
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def generate_training_pairs(output_path: str = "data/training_pairs.json", num_queries: int = 200):
    """
    从知识库自动生成查询-正例文档对 (弱监督)。
    策略:
      - 从文档块中提取关键句作为 "查询"
      - 原文档块作为正例
    """
    from app.rag.vector_store import get_vector_store

    vs = get_vector_store()
    total = vs.collection.count()
    if total == 0:
        print("❌ 知识库为空，请先运行 ingest.py 导入文档")
        return

    print(f"[Step 1] 从知识库 ({total} 个向量块) 生成训练数据...")

    # 获取所有文档块
    results = vs.collection.get(include=["documents", "metadatas"], limit=min(total, 5000))
    documents = results["documents"]
    metadatas = results["metadatas"]

    pairs = []
    for i, doc in enumerate(documents):
        if not doc or len(doc) < 50:
            continue

        # 策略1: 取文档前30个词作为模拟查询
        words = doc.split()
        if len(words) > 10:
            query = " ".join(words[:min(15, len(words) // 3)])
            pairs.append({"query": query, "positive": doc, "source": metadatas[i].get("file_name", "")})

        # 策略2: 若包含标题/关键术语，提取为查询
        for keyword in ["is a", "refers to", "is defined as", "also known as"]:
            if keyword in doc.lower():
                idx = doc.lower().index(keyword)
                subject = doc[:idx].strip().split(".")[-1].strip()
                if 5 < len(subject) < 100:
                    query = f"What is {subject}?"
                    pairs.append({"query": query, "positive": doc, "source": metadatas[i].get("file_name", "")})
                break

        if len(pairs) >= num_queries:
            break

    random.shuffle(pairs)
    pairs = pairs[:num_queries]

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(pairs, f, ensure_ascii=False, indent=2)

    print(f"  ✅ 生成 {len(pairs)} 个训练对，保存到 {out}")
    return pairs


def finetune_biobert(
    training_data_path: str = "data/training_pairs.json",
    model_name: str = "dmis-lab/biobert-v1.1",
    output_dir: str = "models/biobert_finetuned",
    epochs: int = 3,
    batch_size: int = 16,
    warmup_ratio: float = 0.1,
):
    """
    微调 BioBERT 嵌入模型。
    使用 SentenceTransformer 的 MultipleNegativesRankingLoss。
    """
    from sentence_transformers import SentenceTransformer, InputExample, losses
    from torch.utils.data import DataLoader

    # 加载训练数据
    training_path = Path(training_data_path)
    if not training_path.exists():
        print("❌ 训练数据不存在，请先运行 generate_training_pairs()")
        return

    with open(training_path, "r", encoding="utf-8") as f:
        pairs = json.load(f)

    print(f"\n{'='*60}")
    print(f"BioBERT 嵌入模型微调")
    print(f"{'='*60}")
    print(f"  基础模型:   {model_name}")
    print(f"  训练样本:   {len(pairs)}")
    print(f"  Epochs:     {epochs}")
    print(f"  Batch size: {batch_size}")
    print(f"  输出目录:   {output_dir}")
    print(f"{'='*60}\n")

    # 加载基础模型
    print("[Step 1] 加载 BioBERT 基础模型...")
    model = SentenceTransformer(model_name)

    # 构建训练集
    print("[Step 2] 构建训练集...")
    train_examples = [
        InputExample(texts=[p["query"], p["positive"]])
        for p in pairs
    ]
    train_dataloader = DataLoader(train_examples, shuffle=True, batch_size=batch_size)

    # 使用 MultipleNegativesRankingLoss (对比学习)
    train_loss = losses.MultipleNegativesRankingLoss(model)

    warmup_steps = int(len(train_dataloader) * epochs * warmup_ratio)

    # 微调
    print("[Step 3] 开始微调训练...")
    model.fit(
        train_objectives=[(train_dataloader, train_loss)],
        epochs=epochs,
        warmup_steps=warmup_steps,
        output_path=output_dir,
        show_progress_bar=True,
    )

    print(f"\n✅ 微调完成！模型保存至 {output_dir}")
    print(f"   请在 .env 中设置: EMBEDDING_MODEL_PATH={output_dir}")


def evaluate_model(model_path: str = "models/biobert_finetuned"):
    """
    评估微调前后的检索质量对比。
    """
    from sentence_transformers import SentenceTransformer
    import numpy as np

    test_queries = [
        "What are the symptoms of glaucoma?",
        "How is diabetic retinopathy treated?",
        "What causes age-related macular degeneration?",
        "What is cataract surgery?",
        "How is dry eye syndrome diagnosed?",
    ]

    # 加载原始模型和微调模型
    original_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    finetuned_model = SentenceTransformer(model_path) if Path(model_path).exists() else None

    from app.rag.vector_store import get_vector_store
    vs = get_vector_store()

    print(f"\n{'='*60}")
    print("检索质量对比评估")
    print(f"{'='*60}\n")

    for q in test_queries:
        print(f"Q: {q}")

        # 原始模型检索
        orig_emb = original_model.encode([q], normalize_embeddings=True)[0].tolist()
        orig_results = vs.collection.query(
            query_embeddings=[orig_emb], n_results=3, include=["documents", "distances"]
        )
        orig_scores = [1 - d for d in orig_results["distances"][0]] if orig_results["distances"] else []
        print(f"  原始模型 Top-3 相似度: {[f'{s:.3f}' for s in orig_scores]}")

        # 微调模型检索
        if finetuned_model:
            ft_emb = finetuned_model.encode([q], normalize_embeddings=True)[0].tolist()
            ft_results = vs.collection.query(
                query_embeddings=[ft_emb], n_results=3, include=["documents", "distances"]
            )
            ft_scores = [1 - d for d in ft_results["distances"][0]] if ft_results["distances"] else []
            print(f"  微调模型 Top-3 相似度: {[f'{s:.3f}' for s in ft_scores]}")
        print()


def main():
    parser = argparse.ArgumentParser(description="BioBERT 嵌入模型微调工具")
    parser.add_argument("--step", choices=["data", "train", "eval", "all"], default="all")
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--num-queries", type=int, default=200)
    parser.add_argument("--base-model", default="dmis-lab/biobert-v1.1")
    parser.add_argument("--output", default="models/biobert_finetuned")
    args = parser.parse_args()

    if args.step in ("all", "data"):
        generate_training_pairs(num_queries=args.num_queries)

    if args.step in ("all", "train"):
        finetune_biobert(
            model_name=args.base_model,
            output_dir=args.output,
            epochs=args.epochs,
            batch_size=args.batch_size,
        )

    if args.step in ("all", "eval"):
        evaluate_model(args.output)


if __name__ == "__main__":
    main()
