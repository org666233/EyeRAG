"""
嵌入模型评测脚本（论文级）

使用方法:
  python scripts/benchmark_embeddings.py

评测内容:
  - 指标: MRR, Recall@K, NDCG@K
  - 输出: benchmark_results.json, benchmark_results.csv, benchmark_results.tex
"""

import os, sys, time, json, shutil, tempfile, subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

# ─────────────────────────────────────────────
# 评测模型配置
# 每个模型可指定独立的 chroma_collection_name 和 chroma_persist_dir；
# 不指定则默认使用 .env 中的配置（对应 main chroma_db 目录）。
# 注意：必须与 scripts/ingest.py 中的 MODEL_CONFIGS 保持同步！
# ─────────────────────────────────────────────
MODELS = [
    {
        # ── 基线模型：all-MiniLM-L6-v2 384维（英文基线，体积小速度快）
        "id": "minilm-384",
        "name": "all-MiniLM-L6-v2",
        "desc": "MiniLM-L6 / 384维 / 英文通用基线，体积最小速度最快",
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
        # ── MedBERT 中文临床医学 BERT
        "id": "medbert-base-chinese",
        "name": "trueto/medbert-base-chinese",
        "desc": "MedBERT 中文临床医学 / 768维 / 医学领域 BERT，医学 NER/问答任务表现更优",
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
        # ── BGE-Base-ZH 中文通用旗舰向量模型
        "id": "bge-base-zh-v1.5",
        "name": "BAAI/bge-base-zh-v1.5",
        "desc": "BGE-Base-ZH / 768维 / 中文通用旗舰向量模型，MTEB 榜单领先",
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
        # ── BGE-Large-ZH 中文最强向量模型
        "id": "bge-large-zh-v1.5",
        "name": "BAAI/bge-large-zh-v1.5",
        "desc": "BGE-Large-ZH / 1024维 / 中文最强向量模型，检索精度最高",
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
        # ── BGE-M3 多语言旗舰模型（支持中英日韩等）
        "id": "bge-m3",
        "name": "BAAI/bge-m3",
        "desc": "BGE-M3 / 1024维 / 多语言旗舰模型，支持中英日韩等多语言",
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
        # ── Text2Vec 中文语义匹配专用模型
        "id": "text2vec-base-chinese",
        "name": "shibing624/text2vec-base-chinese",
        "desc": "Text2Vec / 768维 / 中文语义匹配专用模型，适合句子对匹配任务",
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
        # ── GTR-T5-XL 多任务大规模检索模型
        "id": "gpt-multitask",
        "name": "sentence-transformers/gtr-t5-xl",
        "desc": "GTR-XL / 768维 / OpenAI 多任务大规模检索模型，参数量大精度高",
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
# Ground Truth 测试集（query -> 相关文件名关键词）
# relevance: 2=高度相关, 1=相关, 0=不相关
# ─────────────────────────────────────────────
GROUND_TRUTH = [
    {
        "query": "How is primary open-angle glaucoma diagnosed?",
        "lang": "en",
        "relevant_files": {
            "Primary Open-Angle Glaucoma": 2,
            "glaucoma": 1,
        },
    },
    {
        "query": "What are the first-line medications for glaucoma?",
        "lang": "en",
        "relevant_files": {
            "Primary Open-Angle Glaucoma": 2,
            "glaucoma_medica": 2,
            "glaucoma": 1,
        },
    },
    {
        "query": "How to treat diabetic retinopathy?",
        "lang": "en",
        "relevant_files": {
            "Diabetic Retinopathy": 2,
            "diabetic_retinopathy": 1,
        },
    },
    {
        "query": "What are the stages of diabetic retinopathy?",
        "lang": "en",
        "relevant_files": {
            "Diabetic Retinopathy": 2,
            "diabetic_retinopathy": 1,
        },
    },
    {
        "query": "Anti-VEGF treatment for age-related macular degeneration",
        "lang": "en",
        "relevant_files": {
            "Age-Related Macular Degeneration": 2,
            "amd_PMC": 2,
            "amd": 1,
        },
    },
    {
        "query": "What is the difference between wet and dry AMD?",
        "lang": "en",
        "relevant_files": {
            "Age-Related Macular Degeneration": 2,
            "amd_PMC": 2,
        },
    },
    {
        "query": "Causes and symptoms of uveitis",
        "lang": "en",
        "relevant_files": {
            "uveitis": 2,
        },
    },
    {
        "query": "Treatment options for thyroid eye disease",
        "lang": "en",
        "relevant_files": {
            "thyroid_eye_dis": 2,
        },
    },
    {
        "query": "How is retinopathy of prematurity treated?",
        "lang": "en",
        "relevant_files": {
            "rop_PMC": 2,
            "Retinopathy of Prematurity": 2,
        },
    },
    {
        "query": "Management of amblyopia in children",
        "lang": "en",
        "relevant_files": {
            "amblyopia": 2,
        },
    },
    {
        "query": "Infectious keratitis diagnosis and treatment",
        "lang": "en",
        "relevant_files": {
            "keratitis": 2,
        },
    },
    {
        "query": "Keratoconus causes and treatments",
        "lang": "en",
        "relevant_files": {
            "keratoconus": 2,
        },
    },
    {
        "query": "Retinal vein occlusion clinical features",
        "lang": "en",
        "relevant_files": {
            "retinal_vein_oc": 2,
        },
    },
    {
        "query": "OCT angiography in retinal diseases",
        "lang": "en",
        "relevant_files": {
            "oct_PMC": 2,
        },
    },
    {
        "query": "Myopia control strategies in children",
        "lang": "en",
        "relevant_files": {
            "myopia": 2,
        },
    },
]

TOP_K = 10


# ─────────────────────────────────────────────
# 指标计算函数
# ─────────────────────────────────────────────
def dcg_at_k(relevances: list[int], k: int) -> float:
    """Discounted Cumulative Gain"""
    relevances = relevances[:k]
    return sum((2**rel - 1) / (i + 1) for i, rel in enumerate(relevances))


def ndcg_at_k(relevances: list[int], k: int) -> float:
    """Normalized DCG"""
    dcg = dcg_at_k(relevances, k)
    ideal = dcg_at_k(sorted(relevances, reverse=True), k)
    return dcg / ideal if ideal > 0 else 0.0


def recall_at_k(relevances: list[int], k: int) -> float:
    """Recall@K"""
    return sum(relevances[:k]) / sum(relevances) if sum(relevances) > 0 else 0.0


def mrr(relevances: list[int]) -> float:
    """Mean Reciprocal Rank"""
    for i, rel in enumerate(relevances, 1):
        if rel > 0:
            return 1.0 / i
    return 0.0


# ─────────────────────────────────────────────
# 在子进程中运行单个模型评测
# ─────────────────────────────────────────────
def run_model(model_cfg: dict, top_k: int) -> dict | None:
    backend_root = str(Path(__file__).parent.parent)

    # 构建子进程环境：从当前环境副本 + 当前模型专属配置覆盖
    child_env = os.environ.copy()
    child_env.update(model_cfg["env"])
    # 对于本地向量库模型，必须彻底移除 CHROMA_HOST（空字符串仍会被父进程值覆盖）
    if model_cfg["env"].get("CHROMA_HOST", "") == "":
        child_env.pop("CHROMA_HOST", None)

    gt_json = json.dumps(GROUND_TRUTH, ensure_ascii=False)

    script = f"""
import sys, time, json
sys.path.insert(0, {repr(backend_root)})

# settings 在模块级读取（已从 child_env 获得正确值），此处只需清除缓存和全局单例
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

from app.rag.vector_store import VectorStore
from app.rag.embeddings import get_current_model_info

# ── 指标函数 ──────────────────────────────────────
def dcg_at_k(relevances, k):
    relevances = relevances[:k]
    return sum((2**rel - 1) / (i + 1) for i, rel in enumerate(relevances))

def ndcg_at_k(relevances, k):
    dcg = dcg_at_k(relevances, k)
    ideal = dcg_at_k(sorted(relevances, reverse=True), k)
    return dcg / ideal if ideal > 0 else 0.0

def recall_at_k(relevances, k):
    return sum(relevances[:k]) / sum(relevances) if sum(relevances) > 0 else 0.0

def mrr(relevances):
    for i, rel in enumerate(relevances, 1):
        if rel > 0:
            return 1.0 / i
    return 0.0
# ─────────────────────────────────────────────────

ground_truth = {gt_json}

vs = VectorStore()

# 先执行一次检索，触发 embedding 模型实际加载
vs.search("warmup query", top_k=1)

info = get_current_model_info()

# 计算延迟
_t0 = time.perf_counter()
for _ in range(5):
    vs.search("diabetic retinopathy treatment", top_k=5)
_embed_ms = (time.perf_counter() - _t0) / 5 * 1000

results = {{}}
for item in ground_truth:
    q = item["query"]
    rel_keywords = item["relevant_files"]

    raw = vs.search(q, top_k={top_k})
    file_names = [r["metadata"].get("file_name", "") for r in raw]
    scores = [r["score"] for r in raw]

    # 按相关性等级构建 relevance list（用于指标计算）
    relevances = []
    for fn in file_names:
        rel_level = 0
        for kw, lvl in rel_keywords.items():
            if kw.lower() in fn.lower():
                rel_level = max(rel_level, lvl)
        relevances.append(rel_level)

    results[q] = {{
        "retrieved": file_names,
        "relevances": relevances,
        "scores": scores,
        "mrr": round(mrr(relevances), 4),
        "recall@5": round(recall_at_k(relevances, 5), 4),
        "recall@10": round(recall_at_k(relevances, 10), 4),
        "ndcg@5": round(ndcg_at_k(relevances, 5), 4),
        "ndcg@10": round(ndcg_at_k(relevances, 10), 4),
    }}

print("__RESULT_JSON__" + json.dumps({{
    "model_id": {json.dumps(model_cfg["id"])},
    "model_name": {json.dumps(model_cfg["name"])},
    "embedding_dim": info.get("embedding_dim"),
    "latency_ms": round(_embed_ms, 2),
    "query_results": results,
}}, ensure_ascii=False) + "__RESULT_JSON__")
"""

    tmp = tempfile.NamedTemporaryFile(mode="w", suffix="_bench.py", delete=False, encoding="utf-8")
    tmp.write(script)
    tmp.close()

    try:
        proc = subprocess.run(
            [sys.executable, tmp.name],
            capture_output=True, text=True,
            cwd=backend_root,
            env=child_env,
            timeout=600,
        )
        raw = proc.stdout
        if proc.returncode != 0:
            err_lines = proc.stderr.strip().splitlines()
            print(f"  进程错误 ({proc.returncode}): {err_lines[-1] if err_lines else ''}")
            if err_lines:
                print(f"    完整错误: {' | '.join(err_lines[-3:])}")
            return None

        marker = "__RESULT_JSON__"
        s = raw.find(marker) + len(marker)
        e = raw.rfind(marker)
        if s < len(marker) or e < 0:
            print(f"  解析失败: {raw[-200:]}")
            return None

        return json.loads(raw[s:e])

    except subprocess.TimeoutExpired:
        print("  超时（10分钟）")
        return None
    finally:
        os.unlink(tmp.name)


# ─────────────────────────────────────────────
# 输出格式化
# ─────────────────────────────────────────────
def save_json(results: list[dict], out_path: Path):
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)


def save_csv(results: list[dict], out_path: Path):
    import csv
    rows = []
    for r in results:
        row = {
            "model_id": r["model_id"],
            "model_name": r["model_name"],
            "embedding_dim": r.get("embedding_dim", ""),
            "latency_ms": r["latency_ms"],
            "MRR": r["metrics"]["mrr"],
            "Recall@5": r["metrics"]["recall@5"],
            "Recall@10": r["metrics"]["recall@10"],
            "NDCG@5": r["metrics"]["ndcg@5"],
            "NDCG@10": r["metrics"]["ndcg@10"],
        }
        rows.append(row)

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


def save_tex(results: list[dict], out_path: Path):
    header = r"""\begin{table}[htbp]
\centering
\caption{Embedding Model Retrieval Performance Comparison}
\label{tab:embedding-comparison}
\begin{tabular}{lrrrrrr}
\hline
\textbf{Model} & \textbf{Dim} & \textbf{MRR} & \textbf{R@5} & \textbf{R@10} & \textbf{N@5} & \textbf{N@10} \\ [2pt] \hline
"""
    lines = [header]
    for r in results:
        m = r["metrics"]
        lines.append(
            f"{r['model_name']} & {r.get('embedding_dim','?')} & "
            f"{m['mrr']:.4f} & {m['recall@5']:.4f} & {m['recall@10']:.4f} & "
            f"{m['ndcg@5']:.4f} & {m['ndcg@10']:.4f} \\\\"
        )
    lines.append("\\hline\n\\end{tabular}\n\\end{table}")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


# ─────────────────────────────────────────────
# 自动导入：若某模型的向量库目录不存在，自动调用 ingest.py
# ─────────────────────────────────────────────
def ensure_vectorstore(model_cfg: dict) -> bool:
    """
    检查模型对应的向量库是否存在且有数据。
    若不存在，运行 ingest.py 子进程完成导入。
    返回 True 表示向量库已就绪（或刚导入完成），False 表示失败。
    """
    base_dir = Path(__file__).parent.parent
    backend_root = str(base_dir)
    chroma_dir = resolve_chroma_dir(model_cfg["env"].get("CHROMA_PERSIST_DIR"))
    collection = model_cfg["env"].get("CHROMA_COLLECTION_NAME", "ophthalmology_docs")

    # 快速检查：若目录存在且 collection 非空，则认为已就绪
    if Path(chroma_dir).exists():
        try:
            child_env = _build_child_env(model_cfg["env"])
            tmp = tempfile.NamedTemporaryFile(mode="w", suffix="_check.py", delete=False, encoding="utf-8")
            tmp.write(f"""
import sys; sys.path.insert(0, {repr(backend_root)})
from app.rag.vector_store import VectorStore
vs = VectorStore()
stats = vs.get_stats()
print(stats.get('total_chunks', 0))
""")
            tmp.close()
            proc = subprocess.run(
                [sys.executable, tmp.name],
                capture_output=True, text=True,
                cwd=backend_root,
                env=child_env,
                timeout=60,
            )
            os.unlink(tmp.name)
            n = int(proc.stdout.strip().splitlines()[-1]) if proc.stdout.strip().splitlines() else 0
            if n > 0:
                return True
        except Exception:
            pass

    # 向量库不存在或为空，自动触发 ingest.py
    print(f"  ⚙️  向量库不存在，正在调用 ingest.py 为 {model_cfg['name']} 构建向量库...")
    print(f"     这可能需要几分钟（首次运行会下载模型）...")

    ingest_script = base_dir / "scripts" / "ingest.py"
    child_env = _build_child_env(model_cfg["env"])

    proc = subprocess.Popen(
        [
            sys.executable, str(ingest_script),
            "--dir", "data/documents",
            "--chunk-size", "512",
            "--chunk-overlap", "50",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        cwd=backend_root,
        env=child_env,
    )

    # 用线程实时读取输出（不打印细节，避免日志刷屏）
    def _stream():
        for _ in proc.stdout:
            pass  # 吞掉所有子进程输出，保持流不阻塞

    import threading, time as _time
    t_stream = threading.Thread(target=_stream, daemon=True)
    t_stream.start()

    # 主线程：显示简洁进度，取代逐行日志
    frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    elapsed = 0
    while proc.poll() is None:
        _time.sleep(2)
        elapsed += 2
        spinner = frames[(elapsed // 2) % len(frames)]
        print(f"  {spinner} 正在为该模型构建向量数据库... ({elapsed}s)", end="\r")

    t_stream.join(timeout=2)
    print(" " * 60, end="\r")

    if proc.returncode != 0:
        print(f"  ❌ ingest.py 失败")
        return False

    # 再次检查
    try:
        child_env2 = _build_child_env(model_cfg["env"])
        tmp2 = tempfile.NamedTemporaryFile(mode="w", suffix="_check2.py", delete=False, encoding="utf-8")
        tmp2.write(f"""
import sys; sys.path.insert(0, {repr(backend_root)})
from app.rag.vector_store import VectorStore
vs = VectorStore()
stats = vs.get_stats()
print(stats.get('total_chunks', 0))
""")
        tmp2.close()
        proc2 = subprocess.run(
            [sys.executable, tmp2.name],
            capture_output=True, text=True,
            cwd=backend_root,
            env=child_env2,
            timeout=60,
        )
        os.unlink(tmp2.name)
        n = int(proc2.stdout.strip().splitlines()[-1]) if proc2.stdout.strip().splitlines() else 0
        if n > 0:
            print(f"  ✅ 向量库导入完成（{n} 条向量）")
            return True
    except Exception:
        pass

    print(f"  ❌ 向量库导入后检查失败")
    return False


def resolve_chroma_dir(env_dir: str | None) -> str:
    """将相对路径转换为相对于 backend/ 的绝对路径"""
    if not env_dir:
        return str(Path(__file__).parent.parent / "chroma_db")
    p = Path(env_dir)
    if p.is_absolute():
        return env_dir
    return str((Path(__file__).parent.parent / p).resolve())


def _build_child_env(model_env: dict) -> dict:
    """从当前环境副本 + 模型专属配置，返回干净的子进程环境"""
    child_env = os.environ.copy()
    child_env.update(model_env)
    # 强制 tqdm 显示进度条（子进程管道非 TTY，tqdm 默认隐藏）
    child_env.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "0")
    child_env.setdefault("HF_HUB_ENABLE_HF_TRANSFER", "0")
    child_env.setdefault("COLUMNS", "200")
    if model_env.get("CHROMA_HOST", "") == "":
        child_env.pop("CHROMA_HOST", None)
    return child_env


# ─────────────────────────────────────────────
# 主函数
# ─────────────────────────────────────────────
def main():
    base_dir = Path(__file__).parent.parent
    out_dir = base_dir / "benchmark"
    out_dir.mkdir(exist_ok=True)

    print("=" * 70)
    print("  嵌入模型评测（MRR / Recall@K / NDCG@K）")
    print("=" * 70)
    print(f"  输出目录: {out_dir}")
    print(f"  模型数量: {len(MODELS)}")
    print(f"  测试 Query: {len(GROUND_TRUTH)} 条")
    print()
    print("  自动导入: 若向量库不存在将自动调用 ingest.py 构建向量库")
    print()

    all_results = []

    for i, m in enumerate(MODELS):
        chroma_dir = resolve_chroma_dir(m.get("env", {}).get("CHROMA_PERSIST_DIR"))
        print(f"[{i+1}/{len(MODELS)}] {m['name']} ({m['desc']})")

        # ── 自动导入检查 ────────────────────────────
        if not Path(chroma_dir).exists():
            ok = ensure_vectorstore(m)
            if not ok:
                print(f"  ❌ 向量库就绪失败，跳过\n")
                continue
        # ────────────────────────────────────────────

        t0 = time.perf_counter()
        res = run_model(m, TOP_K)
        elapsed = time.perf_counter() - t0

        if res is None:
            print(f"  ❌ 失败，跳过\n")
            continue

        # 汇总每个 query 的指标
        q_results = res.pop("query_results")
        per_query = {
            "mrr": [],
            "recall@5": [],
            "recall@10": [],
            "ndcg@5": [],
            "ndcg@10": [],
        }
        for q, qr in q_results.items():
            for k in per_query:
                per_query[k].append(qr[k])

        def avg(lst):
            return round(sum(lst) / len(lst), 4) if lst else 0.0

        res["metrics"] = {k: avg(v) for k, v in per_query.items()}
        res["metrics"]["_per_query"] = q_results
        res["elapsed_seconds"] = round(elapsed, 1)

        print(f"  ✅ 耗时 {elapsed:.0f}s  |  "
              f"MRR={res['metrics']['mrr']:.4f}  |  "
              f"R@5={res['metrics']['recall@5']:.4f}  |  "
              f"N@5={res['metrics']['ndcg@5']:.4f}  |  "
              f"延迟={res['latency_ms']:.1f}ms/查询\n")

        all_results.append(res)

    if not all_results:
        print("没有模型成功完成评测")
        return

    # 按 MRR 排序
    all_results.sort(key=lambda x: x["metrics"]["mrr"], reverse=True)

    # ── 输出文件 ────────────────────────────────────
    json_path = out_dir / "benchmark_results.json"
    csv_path = out_dir / "benchmark_results.csv"
    tex_path = out_dir / "benchmark_results.tex"

    save_json(all_results, json_path)
    save_csv(all_results, csv_path)
    save_tex(all_results, tex_path)

    # ── 打印汇总表 ──────────────────────────────────
    print("=" * 70)
    print("  评测结果汇总")
    print("=" * 70)
    print(f"{'Model':<35} {'Dim':>4} {'MRR':>8} {'R@5':>8} {'R@10':>8} {'N@5':>8} {'N@10':>8}")
    print("-" * 70)
    for r in all_results:
        m = r["metrics"]
        dim = str(r.get("embedding_dim", "?"))
        print(
            f"{r['model_name']:<35} {dim:>4} "
            f"{m['mrr']:>8.4f} {m['recall@5']:>8.4f} {m['recall@10']:>8.4f} "
            f"{m['ndcg@5']:>8.4f} {m['ndcg@10']:>8.4f}"
        )
    print("-" * 70)

    print(f"\n结果文件已保存:")
    print(f"  JSON: {json_path}")
    print(f"  CSV:  {csv_path}")
    print(f"  LaTeX: {tex_path}")
    print("\n说明:")
    print("  MRR    - 首个相关结果排名的倒数均值，越接近1越好")
    print("  R@K    - Top-K 结果中相关文档占比（召回率）")
    print("  N@K    - 归一化折损累计增益，综合考虑相关性和排序位置")


if __name__ == "__main__":
    main()
