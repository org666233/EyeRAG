"""
RAGAs 启发式评估脚本 v2 - 基于 RAG 的眼科医疗知识问答系统
=============================================================
支持两种评估模式：
  --mode configs  对比检索配置 A/B/C/D/E（默认，使用已有 ChromaDB + 当前嵌入模型）
  --mode models   对比 ./model/ 目录下所有嵌入模型（纯向量检索，隔离嵌入质量）

检索配置说明（configs 模式）：
  Config A  纯向量检索（基线）
  Config B  混合检索（向量 + BM25 + RRF）
  Config C  混合检索 + 关键词重排序
  Config D  混合检索 + 重排序 + 双语翻译（生产配置，无 Self-RAG）
  Config E  混合检索 + 重排序 + 双语翻译 + Self-RAG 评估决策【消融实验】
            ↑ D vs E 的指标差值 = Self-RAG 自判断机制的量化增益

新特性：
  - 断点续传：每题完成后自动保存检查点，--resume <文件> 继续上次实验
  - 健壮重试：连续 3 题 LLM API 失败则停止并保存断点，下次可恢复
  - 多模型支持：遇到模型加载失败自动跳过，不卡死
  - MiniMax 裁判 LLM 启动校验

评估指标（与 RAGAs 框架一致）：
  Faithfulness      忠实度   ── LLM 提取答案陈述逐句判断是否有文档支撑
  Answer Relevancy  答案相关性 ── LLM 从答案反向生成问题，与原问题计算 cosine 相似度
  Context Precision 上下文精确率 ── LLM 判断每个检索块是否相关，结合排名计算 AP
  Context Recall    上下文召回率 ── LLM 判断标准答案的关键陈述是否被检索内容覆盖

运行方式：
  cd backend
  python scripts/evaluate_ragas.py                         # configs 模式，A+B+C，50 题
  python scripts/evaluate_ragas.py --limit 5               # 快速验证（5 题）
  python scripts/evaluate_ragas.py --config C              # 只跑 Config C
  python scripts/evaluate_ragas.py --config E              # 只跑 Config E（Self-RAG 消融）
  python scripts/evaluate_ragas.py --config E --limit 5    # E 快速验证（5 题）
  python scripts/evaluate_ragas.py --mode models           # 对比所有本地嵌入模型
  python scripts/evaluate_ragas.py --mode models --limit 10
  python scripts/evaluate_ragas.py --resume data/checkpoint_xxx.json
"""

import sys
import re
import json
import time
import asyncio
import argparse
import numpy as np
from datetime import datetime
from pathlib import Path
from typing import Optional, Callable, Awaitable

try:
    import wandb as _wandb
    _WANDB_AVAILABLE = True
except ImportError:
    _wandb = None
    _WANDB_AVAILABLE = False

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import get_settings
from app.rag.vector_store import get_vector_store, get_collection
from app.rag.hybrid_retrieval import get_hybrid_retriever
from app.rag.reranker import get_reranker
from app.rag.prompts import build_rag_messages
from app.rag.llm_client import generate
from app.rag.embeddings import embed_texts
from app.rag.self_rag import _translate_for_bm25, _is_chinese
from app.utils.logger import logger

settings = get_settings()

MAX_CONSECUTIVE_FAILURES = 3   # 连续失败多少题后停止实验
MAX_QUESTION_RETRIES     = 4   # 单题遇到 529 最多重试几次
OVERLOAD_WAIT_BASE       = 90  # 529 首次等待秒数，后续翻倍（90→180→360→720）
MAX_FORMAT_RETRIES       = 2   # 单指标 LLM 返回格式不符时最多重试次数


def _is_overloaded(exc: Exception) -> bool:
    """判断是否为 MiniMax/Anthropic 过载错误（529）"""
    if getattr(exc, "status_code", None) == 529:
        return True
    msg = str(exc)
    return "529" in msg and ("overloaded" in msg.lower() or "繁忙" in msg)


# ═══════════════════════════════════════════════════════════════════════════════
# 评估数据集（50 道眼科专业问题，8 大类）
# ═══════════════════════════════════════════════════════════════════════════════

EVAL_DATASET: list[dict] = [
    # ── 疾病认知 ──────────────────────────────────────────────────────────────
    {"question": "什么是青光眼？它有哪些类型？",
     "ground_truth": "青光眼是一种以视神经损害为特征的眼病，通常与眼压升高有关。主要类型包括开角型青光眼、闭角型青光眼和继发性青光眼。"},
    {"question": "糖尿病视网膜病变的分期是什么？",
     "ground_truth": "糖尿病视网膜病变分为非增殖期（NPDR）和增殖期（PDR）。非增殖期包括轻度、中度和重度，增殖期表现为新生血管形成。"},
    {"question": "白内障是怎么形成的？",
     "ground_truth": "白内障是晶状体蛋白质变性导致混浊，主要原因包括老化、紫外线损伤、代谢疾病、外伤等。"},
    {"question": "什么是黄斑变性？",
     "ground_truth": "黄斑变性（AMD）是影响视网膜黄斑区的退行性疾病，分为干性和湿性两种，是老年人视力丧失的主要原因。"},
    {"question": "角膜炎有哪些常见类型？",
     "ground_truth": "角膜炎主要包括细菌性角膜炎、病毒性角膜炎（如单疱病毒）、真菌性角膜炎和棘阿米巴角膜炎。"},
    {"question": "什么是干眼症？",
     "ground_truth": "干眼症是泪液分泌不足或泪膜不稳定导致的眼表疾病，症状包括眼干、异物感、视力波动。"},
    {"question": "视网膜脱离的症状有哪些？",
     "ground_truth": "视网膜脱离的症状包括突然出现飞蚊症、闪光感、视野缺损（如幕帘遮挡感）和视力下降。"},
    {"question": "什么是弱视？如何治疗？",
     "ground_truth": "弱视是视觉发育期由于异常视觉经验导致的单眼或双眼最佳矫正视力下降。治疗包括光学矫正、遮盖疗法和药物压抑。"},
    {"question": "翼状胬肉是什么？",
     "ground_truth": "翼状胬肉是结膜组织向角膜表面增生的三角形纤维血管组织，与紫外线照射和干燥环境有关。"},
    {"question": "什么是圆锥角膜？",
     "ground_truth": "圆锥角膜是角膜中央或旁中央进行性变薄、前突呈锥形的非炎症性疾病，导致不规则散光和视力下降。"},
    # ── 诊断方法 ──────────────────────────────────────────────────────────────
    {"question": "眼底检查能发现什么问题？",
     "ground_truth": "眼底检查可发现视网膜病变、黄斑变性、青光眼视神经损害、视网膜血管疾病、视网膜脱离等。"},
    {"question": "OCT 检查是什么？有什么用途？",
     "ground_truth": "OCT（光学相干断层扫描）是使用光干涉原理对视网膜进行断层成像的检查，可检测黄斑病变、青光眼视神经纤维层厚度等。"},
    {"question": "如何测量眼压？",
     "ground_truth": "测量眼压的方法包括 Goldmann 压平眼压计、非接触式气动眼压计（NCT）和手持式回弹式眼压计。"},
    {"question": "视野检查有什么作用？",
     "ground_truth": "视野检查用于检测视野缺损，对青光眼诊断和随访、视路疾病定位、视神经疾病评估很重要。"},
    {"question": "什么是角膜地形图检查？",
     "ground_truth": "角膜地形图是测量角膜前表面曲率分布的检查方法，用于屈光手术术前评估、角膜疾病诊断和隐形眼镜验配。"},
    {"question": "裂隙灯检查能看什么？",
     "ground_truth": "裂隙灯显微镜可检查眼睑、结膜、角膜、前房、虹膜、晶状体和前部玻璃体结构。"},
    {"question": "FFA 检查是什么？",
     "ground_truth": "FFA（荧光素眼底血管造影）是静脉注射荧光素后拍摄眼底血管影像的检查，用于诊断视网膜血管疾病。"},
    # ── 治疗方法 ──────────────────────────────────────────────────────────────
    {"question": "LASIK 手术的原理是什么？",
     "ground_truth": "LASIK 通过准分子激光切削角膜基质改变角膜曲率来矫正近视、远视和散光。"},
    {"question": "白内障手术是怎么做的？",
     "ground_truth": "白内障手术通常采用超声乳化术，通过小切口将混浊的晶状体乳化吸除，然后植入人工晶状体。"},
    {"question": "青光眼如何降眼压治疗？",
     "ground_truth": "青光眼降眼压治疗包括药物（前列腺素类、β 受体阻滞剂等）、激光治疗（SLT、LPI）和手术（小梁切除术、引流管植入）。"},
    {"question": "玻璃体切除术适用于什么？",
     "ground_truth": "玻璃体切除术适用于玻璃体出血、视网膜脱离、黄斑裂孔、黄斑前膜和增殖性糖尿病视网膜病变等。"},
    {"question": "抗 VEGF 治疗是什么？",
     "ground_truth": "抗 VEGF 治疗是通过玻璃体腔注射抗血管内皮生长因子药物来抑制异常血管生成，用于湿性 AMD、DME 等。"},
    {"question": "角膜移植有几种类型？",
     "ground_truth": "角膜移植主要包括穿透性角膜移植（PK）、板层角膜移植（LK）、内皮移植（DSAEK/DMEK）等。"},
    {"question": "PRK 和 LASIK 有什么区别？",
     "ground_truth": "PRK 直接在角膜上皮去除后切削角膜表面，LASIK 制作角膜瓣后切削基质。PRK 恢复慢但无瓣膜并发症。"},
    {"question": "ICL 植入手术是什么？",
     "ground_truth": "ICL（有晶体眼人工晶体植入术）是将人工晶体植入眼内虹膜与晶状体之间来矫正高度近视。"},
    # ── 眼科药物 ──────────────────────────────────────────────────────────────
    {"question": "常用的眼科抗炎药物有哪些？",
     "ground_truth": "常用眼科抗炎药包括皮质类固醇（如地塞米松、氟米龙）和非甾体抗炎药（如双氯芬酸、酮咯酸）。"},
    {"question": "散瞳药物有哪些？有什么作用？",
     "ground_truth": "常用散瞳药包括阿托品、环戊通、托吡卡胺，用于眼底检查、睫状肌麻痹验光和虹膜炎治疗。"},
    {"question": "人工泪液有哪些类型？",
     "ground_truth": "人工泪液按成分分为含防腐剂和不含防腐剂型，按黏度分为低黏度水溶液和高黏度凝胶型。"},
    # ── 眼部解剖 ──────────────────────────────────────────────────────────────
    {"question": "人眼的屈光系统包括哪些结构？",
     "ground_truth": "人眼的屈光系统包括角膜、前房房水、晶状体和玻璃体，其中角膜占总屈光力约 2/3。"},
    {"question": "视网膜有哪些重要的细胞层？",
     "ground_truth": "视网膜主要细胞层包括色素上皮层、光感受器层（视锥细胞和视杆细胞）、双极细胞层和神经节细胞层。"},
    {"question": "房水的循环路径是什么？",
     "ground_truth": "房水由睫状体产生，流入后房，经瞳孔进入前房，通过小梁网和 Schlemm 管排出眼外。"},
    {"question": "什么是泪膜？有几层？",
     "ground_truth": "泪膜覆盖在角膜和结膜表面，由外到内分为脂质层、水液层和黏蛋白层三层结构。"},
    # ── 儿童眼科 ──────────────────────────────────────────────────────────────
    {"question": "儿童近视防控的方法有哪些？",
     "ground_truth": "儿童近视防控方法包括增加户外活动、低浓度阿托品滴眼液、角膜塑形镜（OK 镜）和多焦点眼镜。"},
    {"question": "先天性白内障该怎么处理？",
     "ground_truth": "先天性白内障需早期手术治疗，术后进行光学矫正和弱视训练，以促进视觉发育。"},
    {"question": "斜视有哪些类型？",
     "ground_truth": "斜视分为共同性和非共同性（麻痹性），按方向分为内斜视、外斜视、上斜视和下斜视。"},
    # ── 眼科急症 ──────────────────────────────────────────────────────────────
    {"question": "化学性眼灼伤的紧急处理？",
     "ground_truth": "化学性眼灼伤应立即用大量清水持续冲洗至少 15-30 分钟，碱性灼伤比酸性灼伤更危险。"},
    {"question": "急性闭角型青光眼发作怎么办？",
     "ground_truth": "急性闭角型青光眼发作表现为剧烈眼痛、头痛、恶心、视力骤降，需紧急降眼压并行激光虹膜切开术。"},
    {"question": "眼外伤穿通伤如何处理？",
     "ground_truth": "眼外伤穿通伤应避免揉眼，用盾形保护罩保护伤眼，禁止加压包扎，尽快转运至眼科中心手术修复。"},
    # ── 眼科新技术 ────────────────────────────────────────────────────────────
    {"question": "飞秒激光在眼科有什么应用？",
     "ground_truth": "飞秒激光在眼科用于 LASIK 角膜瓣制作、白内障手术辅助、角膜移植切割和屈光手术。"},
    {"question": "什么是基因治疗在眼科的应用？",
     "ground_truth": "眼科基因治疗已用于遗传性视网膜营养不良（如 Luxturna 治疗 RPE65 基因突变相关的 Leber 先天性黑矇）。"},
    {"question": "人工智能在眼科诊断中的应用？",
     "ground_truth": "AI 在眼科用于糖尿病视网膜病变自动筛查、青光眼 OCT 影像分析、AMD 进展预测等。"},
    # ── 综合问题 ──────────────────────────────────────────────────────────────
    {"question": "高血压对眼睛有什么影响？",
     "ground_truth": "高血压可导致高血压性视网膜病变，表现为视网膜动脉变细、动静脉交叉征、棉絮斑和出血。"},
    {"question": "糖尿病患者应该多久做一次眼底检查？",
     "ground_truth": "1 型糖尿病发病 5 年后应每年检查，2 型糖尿病确诊时即应检查，之后至少每年一次。"},
    {"question": "长期使用电子设备对眼睛有什么影响？",
     "ground_truth": "长期使用电子设备可导致视疲劳、干眼症加重、近视进展加速，建议遵循 20-20-20 规则。"},
    {"question": "老花眼是怎么回事？",
     "ground_truth": "老花眼（老视）是随年龄增长晶状体弹性下降、调节能力减退导致的近距离视物困难，通常 40 岁后出现。"},
    {"question": "隐形眼镜使用不当会有什么风险？",
     "ground_truth": "隐形眼镜使用不当可导致角膜感染、角膜缺氧、巨乳头性结膜炎和角膜新生血管。"},
    {"question": "眼部过敏有哪些表现？如何治疗？",
     "ground_truth": "眼部过敏表现为眼痒、充血、流泪、眼睑水肿，治疗包括抗组胺药、肥大细胞稳定剂和冷敷。"},
    {"question": "什么是虹膜睫状体炎？",
     "ground_truth": "虹膜睫状体炎（前葡萄膜炎）是虹膜和睫状体的炎症，表现为充血、疼痛、畏光和瞳孔缩小。"},
    {"question": "结膜炎和角膜炎有什么区别？",
     "ground_truth": "结膜炎主要表现为充血分泌物多但视力不受影响，角膜炎影响视力且可伴角膜溃疡，更为严重。"},
]


# ═══════════════════════════════════════════════════════════════════════════════
# 工具函数
# ═══════════════════════════════════════════════════════════════════════════════

def _cosine_similarity(a: list[float], b: list[float]) -> float:
    va, vb = np.array(a), np.array(b)
    denom = np.linalg.norm(va) * np.linalg.norm(vb)
    if denom < 1e-9:
        return 0.0
    return float(np.dot(va, vb) / denom)


def _extract_json(text: str) -> Optional[dict]:
    # 先尝试直接解析
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass
    # 提取 markdown 代码块内容（```json ... ``` 或 ``` ... ```）
    md_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
    if md_match:
        try:
            return json.loads(md_match.group(1))
        except json.JSONDecodeError:
            pass
    # 贪婪匹配最外层 {...}（处理嵌套）
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return None


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


def _bar(score: float, width: int = 10) -> str:
    filled = round(_clamp(score) * width)
    return "█" * filled + "░" * (width - filled)


def _check_llm_provider():
    provider = settings.llm_provider.lower()
    if provider == "minimax":
        print(f"  ✅ 裁判 LLM: MiniMax ({settings.minimax_model_name})")
    else:
        print(f"  ⚠️  警告: LLM_PROVIDER={provider}（建议切换到 minimax）")
        print(f"      当前模型: {settings.llm_model_name}")


# ═══════════════════════════════════════════════════════════════════════════════
# 断点管理器
# ═══════════════════════════════════════════════════════════════════════════════

class CheckpointManager:
    """
    保存/加载评估检查点。每题结束后自动保存，支持断点续传。

    文件格式（data/checkpoint_<run_id>.json）：
      {
        "run_id": "...",
        "mode": "configs|models",
        "top_k": 5,
        "dataset_limit": 0,
        "completed_experiments": [...],   # 已完整跑完的实验名
        "partial_experiment": {           # 当前进行中的实验（若有）
            "name": "...",
            "records": [...]
        },
        "all_results": [...]              # 已完成实验的完整结果
      }
    """

    def __init__(self, path: Path):
        self.path = path
        self._data: dict = {}

    @classmethod
    def new(cls, run_id: str, mode: str, top_k: int, dataset_limit: int) -> "CheckpointManager":
        cp = cls(Path("data") / f"checkpoint_{run_id}.json")
        cp._data = {
            "run_id": run_id,
            "mode": mode,
            "top_k": top_k,
            "dataset_limit": dataset_limit,
            "completed_experiments": [],
            "partial_experiment": None,
            "all_results": [],
        }
        return cp

    @classmethod
    def load(cls, path: Path) -> "CheckpointManager":
        cp = cls(path)
        with open(path, "r", encoding="utf-8") as f:
            cp._data = json.load(f)
        print(f"  📂 加载检查点: {path}")
        print(f"     模式: {cp._data['mode']} | Top-K: {cp._data['top_k']}")
        completed = cp._data.get("completed_experiments", [])
        partial = cp._data.get("partial_experiment")
        if completed:
            print(f"     已完成实验: {', '.join(completed)}")
        if partial:
            done_count = len(partial.get("records", []))
            print(f"     续跑实验: {partial['name']} (已完成 {done_count} 题)")
        return cp

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)

    def is_completed(self, name: str) -> bool:
        return name in self._data.get("completed_experiments", [])

    def get_partial_records(self, name: str) -> list[dict]:
        p = self._data.get("partial_experiment")
        if p and p.get("name") == name:
            return list(p.get("records", []))
        return []

    def update_partial(self, name: str, records: list[dict]):
        self._data["partial_experiment"] = {"name": name, "records": records}
        self.save()

    def complete_experiment(self, name: str, result: dict):
        self._data.setdefault("completed_experiments", []).append(name)
        self._data["partial_experiment"] = None
        self._data.setdefault("all_results", []).append(result)
        self.save()

    @property
    def all_results(self) -> list[dict]:
        return self._data.get("all_results", [])

    @property
    def run_id(self) -> str:
        return self._data["run_id"]

    @property
    def mode(self) -> str:
        return self._data["mode"]

    @property
    def top_k(self) -> int:
        return self._data["top_k"]

    @property
    def dataset_limit(self) -> int:
        return self._data.get("dataset_limit", 0)


# ═══════════════════════════════════════════════════════════════════════════════
# RAGAs 四大指标实现
# ═══════════════════════════════════════════════════════════════════════════════

class MetricsCalculator:
    """
    RAGAs 启发的四指标计算器。
    使用项目配置的 LLM（MiniMax/DeepSeek）作为裁判，原理与 RAGAs 框架完全一致。
    """

    async def faithfulness(self, answer: str, contexts: list[str]) -> float:
        """LLM 提取答案陈述，逐条判断是否有文档支撑。score = 支撑数/总数"""
        if not answer.strip() or not contexts:
            return 0.0

        ctx_text = "\n".join(
            f"[文档{i+1}] {c[:400]}" for i, c in enumerate(contexts[:5])
        )
        prompt = f"""你是严格的医学评估专家。请完成以下任务：

【参考文档】
{ctx_text}

【AI 回答】
{answer[:800]}

【任务】
1. 从 AI 回答中提取 3-7 个核心陈述句（每句表达一个独立的事实主张）。
2. 对每个陈述，判断参考文档中是否有明确支撑（true=有支撑，false=文档中未提及或矛盾）。
3. 计算 score = 有支撑数 / 总陈述数，保留 2 位小数。

【输出格式】只输出如下 JSON，不要有任何其他内容：
{{"claims":[{{"claim":"陈述内容","supported":true}},{{"claim":"另一陈述","supported":false}}],"score":0.85}}"""

        try:
            raw = await generate([{"role": "user", "content": prompt}], temperature=0, max_tokens=2048)
            data = _extract_json(raw)
            if data and "score" in data:
                return _clamp(float(data["score"]))
            if data and "claims" in data:
                claims = data["claims"]
                if claims:
                    supported = sum(1 for c in claims if c.get("supported", False))
                    return _clamp(supported / len(claims))
            raise ValueError(f"Faithfulness: LLM 返回格式不符: {str(raw)[:80]}")
        except Exception as e:
            logger.warning(f"Faithfulness 计算异常: {e}")
            raise

    async def answer_relevancy(self, question: str, answer: str) -> float:
        """LLM 从回答反向生成 3 个问题，与原问题计算 cosine 相似度均值。"""
        if not answer.strip():
            return 0.0

        prompt = f"""你是一名语言学专家。请阅读以下医学问答回答，并生成 3 个最可能对应此回答的问题。

【回答】
{answer[:600]}

【要求】
- 生成的问题应该是有人看到这段回答后，最可能提出的问题
- 每个问题独立、具体、与眼科医学相关
- 不要重复问题

【输出格式】只输出如下 JSON，不要有任何其他内容：
{{"questions":["问题1","问题2","问题3"]}}"""

        try:
            raw = await generate([{"role": "user", "content": prompt}], temperature=0.3, max_tokens=1500)
            data = _extract_json(raw)
            if not data or "questions" not in data:
                return 0.5

            gen_questions = [q for q in data["questions"] if isinstance(q, str) and q.strip()]
            if not gen_questions:
                return 0.5

            all_texts = [question] + gen_questions
            embeddings = embed_texts(all_texts)
            q_emb = embeddings[0]
            sims = [_cosine_similarity(q_emb, embeddings[i+1]) for i in range(len(gen_questions))]
            return _clamp(float(np.mean(sims)))
        except Exception as e:
            logger.warning(f"Answer Relevancy 计算异常: {e}")
            raise

    async def context_precision(
        self, question: str, contexts: list[str], ground_truth: str
    ) -> float:
        """对 Top-K 检索文档逐一判断相关性，计算 Average Precision（考虑排名）。"""
        if not contexts:
            return 0.0

        relevance_flags: list[bool] = []
        for i, ctx in enumerate(contexts[:5]):
            prompt = f"""你是一名眼科医学专家评估员。

【用户问题】{question}
【标准参考答案要点】{ground_truth[:300]}
【待评估文档片段】{ctx[:500]}

请判断：该文档片段是否包含有助于回答上述问题的相关信息？
（判断标准：文档中有实质性内容可支撑回答，而非仅有表面词汇重叠）

只输出如下 JSON，不要有任何其他内容：
{{"relevant":true,"reason":"简要理由（15字以内）"}}"""

            try:
                raw = await generate([{"role": "user", "content": prompt}], temperature=0, max_tokens=1000)
                data = _extract_json(raw)
                is_relevant = bool(data.get("relevant", False)) if data else False
            except Exception as e:
                logger.warning(f"Context Precision 第{i+1}块判断异常: {e}")
                is_relevant = False

            relevance_flags.append(is_relevant)
            await asyncio.sleep(0.3)

        total_relevant = sum(relevance_flags)
        if total_relevant == 0:
            return 0.0

        ap_sum = 0.0
        running_relevant = 0
        for k, rel in enumerate(relevance_flags, 1):
            if rel:
                running_relevant += 1
                ap_sum += running_relevant / k
        return _clamp(ap_sum / total_relevant)

    async def context_recall(self, ground_truth: str, contexts: list[str]) -> float:
        """将标准答案拆分为关键陈述，判断检索文档对各陈述的覆盖情况。"""
        if not ground_truth.strip() or not contexts:
            return 0.0

        ctx_text = "\n".join(
            f"[文档{i+1}] {c[:400]}" for i, c in enumerate(contexts[:5])
        )
        prompt = f"""你是一名严格的医学评估专家。

【标准参考答案】
{ground_truth}

【检索文档内容】
{ctx_text}

【任务】
1. 将标准参考答案拆分为 3-5 个独立的关键事实陈述。
2. 判断每个陈述在检索文档中是否有对应的支撑内容（true=有覆盖，false=未覆盖）。
3. 计算 score = 被覆盖数 / 总陈述数，保留 2 位小数。

只输出如下 JSON，不要有任何其他内容：
{{"statements":[{{"statement":"陈述内容","covered":true}},{{"statement":"另一陈述","covered":false}}],"score":0.80}}"""

        try:
            raw = await generate([{"role": "user", "content": prompt}], temperature=0, max_tokens=2048)
            data = _extract_json(raw)
            if data and "score" in data:
                return _clamp(float(data["score"]))
            if data and "statements" in data:
                stmts = data["statements"]
                if stmts:
                    covered = sum(1 for s in stmts if s.get("covered", False))
                    return _clamp(covered / len(stmts))
            raise ValueError(f"Context Recall: LLM 返回格式不符: {str(raw)[:80]}")
        except Exception as e:
            logger.warning(f"Context Recall 计算异常: {e}")
            raise

    async def evaluate_one(
        self, question: str, answer: str, contexts: list[str], ground_truth: str,
    ) -> dict:
        """计算四项指标。

        - 格式错误（LLM 返回非 JSON）最多自动重试 MAX_FORMAT_RETRIES 次
        - 单项指标失败后记为 None，其余成功指标仍保留
        - 仅当所有指标均失败时才抛出异常
        """
        _metrics = [
            ("faithfulness",      lambda: self.faithfulness(answer, contexts)),
            ("answer_relevancy",  lambda: self.answer_relevancy(question, answer)),
            ("context_precision", lambda: self.context_precision(question, contexts, ground_truth)),
            ("context_recall",    lambda: self.context_recall(ground_truth, contexts)),
        ]
        results: dict[str, Optional[float]] = {}
        errors: list[str] = []

        for name, factory in _metrics:
            val: Optional[float] = None
            for attempt in range(MAX_FORMAT_RETRIES + 1):
                try:
                    val = round(await factory(), 4)
                    break
                except ValueError as exc:
                    err_str = str(exc)
                    if "LLM 返回格式不符" in err_str and attempt < MAX_FORMAT_RETRIES:
                        wait = 5 * (attempt + 1)
                        logger.warning(
                            f"{name} 格式错误，{wait}s 后重试"
                            f" ({attempt + 1}/{MAX_FORMAT_RETRIES}): {err_str[:60]}"
                        )
                        await asyncio.sleep(wait)
                    else:
                        logger.warning(f"{name} 最终失败（格式重试耗尽）: {err_str[:80]}")
                        errors.append(f"{name}: {err_str[:80]}")
                        break
                except Exception as exc:
                    logger.warning(f"{name} 计算异常: {exc}")
                    errors.append(f"{name}: {str(exc)[:80]}")
                    break
            results[name] = val

        if all(v is None for v in results.values()):
            raise ValueError("; ".join(errors) or "所有指标计算均失败")

        return results


# ═══════════════════════════════════════════════════════════════════════════════
# 检索配置（configs 模式）
# ═══════════════════════════════════════════════════════════════════════════════

class VectorOnlyConfig:
    name = "A_vector_only"
    description = "纯向量检索（基线）"

    def __init__(self):
        self._vs = get_vector_store()

    async def retrieve_and_answer(self, question: str, top_k: int) -> dict:
        results = self._vs.search(query=question, top_k=top_k)
        contexts = [r["content"] for r in results if r.get("content")]
        messages = build_rag_messages(question=question, search_results=results)
        answer = await generate(messages=messages, temperature=0.3)
        return {"answer": answer, "contexts": contexts}


class HybridConfig:
    name = "B_hybrid"
    description = "混合检索（向量 + BM25 + RRF）"

    def __init__(self):
        self._retriever = get_hybrid_retriever()

    async def retrieve_and_answer(self, question: str, top_k: int) -> dict:
        results = self._retriever.search(query=question, top_k=top_k)
        contexts = [r["content"] for r in results if r.get("content")]
        messages = build_rag_messages(question=question, search_results=results)
        answer = await generate(messages=messages, temperature=0.3)
        return {"answer": answer, "contexts": contexts}


class HybridRerankConfig:
    name = "C_hybrid_rerank"
    description = "混合检索 + 关键词重排序（完整系统）"

    def __init__(self):
        self._retriever = get_hybrid_retriever()
        self._reranker = get_reranker(use_cross_encoder=False)

    async def retrieve_and_answer(self, question: str, top_k: int) -> dict:
        candidates = self._retriever.search(query=question, top_k=top_k * 3)
        results = self._reranker.rerank(query=question, results=candidates, top_k=top_k)
        contexts = [r["content"] for r in results if r.get("content")]
        messages = build_rag_messages(question=question, search_results=results)
        answer = await generate(messages=messages, temperature=0.3)
        return {"answer": answer, "contexts": contexts}


class HybridRerankBilingualConfig:
    name = "D_hybrid_rerank_bilingual"
    description = "混合检索 + 重排序 + 双语翻译（当前生产配置，无 Self-RAG）"

    def __init__(self):
        self._retriever = get_hybrid_retriever()
        self._reranker = get_reranker(use_cross_encoder=False)

    async def retrieve_and_answer(self, question: str, top_k: int) -> dict:
        # 中文问题翻译为英文，双路补偿向量和 BM25 的跨语言衰减
        en_query = await _translate_for_bm25(question) if _is_chinese(question) else ""
        candidates = self._retriever.search(
            query=question, top_k=top_k * 3,
            bm25_extra_query=en_query,
            vector_extra_query=en_query,
        )
        results = self._reranker.rerank(query=question, results=candidates, top_k=top_k)
        contexts = [r["content"] for r in results if r.get("content")]
        messages = build_rag_messages(question=question, search_results=results)
        answer = await generate(messages=messages, temperature=0.3)
        return {"answer": answer, "contexts": contexts}


class SelfRagConfig:
    """
    配置 E：消融实验 —— 在配置 D（混合+重排序+双语翻译）的基础上
    增加 Self-RAG LLM 评估-决策层。

    与配置 D 的唯一差异：
      D：检索 → 重排序 → 直接生成（强制 proceed，跳过 LLM 评估）
      E：检索 → 重排序 → LLM 评估（proceed / retry / fallback）→ 生成

    通过 D vs E 的指标差值，量化 Self-RAG 自判断机制的实际增益。
    """
    name = "E_selfrag"
    description = "混合检索 + 重排序 + 双语翻译 + Self-RAG 评估决策（消融对比）"

    def __init__(self):
        # 延迟导入，避免在 configs 模式下不必要地初始化 SelfRAGAgent
        from app.rag.self_rag import SelfRAGAgent
        self._agent = SelfRAGAgent()

    async def retrieve_and_answer(self, question: str, top_k: int) -> dict:
        # 调用完整 Self-RAG 流程（含 LLM 评估-决策）
        stream, _sources, decision, search_results = await self._agent.query_stream(
            question=question,
            top_k=top_k,
            temperature=0.3,
        )
        # 收集流式输出
        chunks: list[str] = []
        async for chunk in stream:
            chunks.append(chunk)
        answer = "".join(chunks)

        # fallback 决策：LLM 未使用任何检索内容 → 如实记录空上下文
        # proceed / retry 决策：使用实际传入 LLM 的检索结果
        if decision == "fallback":
            contexts: list[str] = []
        else:
            contexts = [r["content"] for r in search_results if r.get("content")]

        return {"answer": answer, "contexts": contexts}


ALL_CONFIGS: dict[str, type] = {
    "A": VectorOnlyConfig,
    "B": HybridConfig,
    "C": HybridRerankConfig,
    "D": HybridRerankBilingualConfig,
    "E": SelfRagConfig,
}


# ═══════════════════════════════════════════════════════════════════════════════
# 本地嵌入模型检索器（models 模式）
# ═══════════════════════════════════════════════════════════════════════════════

# 模型名 → (ChromaDB 目录, collection 名称, 模型加载路径)
# 每个模型有自己独立的向量库，维度不同，不可混用
MODEL_EVAL_LIST: list[tuple[str, str, str, str]] = [
    # (display_name,          chroma_dir,              collection_name,                         model_path)
    ("all-MiniLM-L6-v2",
     "chroma_db_minilm_384",
     "ophthalmology_docs_minilm_384",
     "model/all-MiniLM-L6-v2/snapshots/c9745ed1d9f207416be6d2e6f8de32d1f16199bf"),

    ("bge-base-zh-v1.5",
     "chroma_db_bge_base_zh",
     "ophthalmology_docs_bge_base_zh",
     "model/bge-base-zh-v1.5"),

    ("bge-large-zh-v1.5",
     "chroma_db_bge_large_zh",
     "ophthalmology_docs_bge_large_zh",
     "model/bge-large-zh-v1.5"),

    ("bge-m3",
     "chroma_db_bge_m3",
     "ophthalmology_docs_bge_m3",
     "model/bge-m3"),

    ("text2vec-base-chinese",
     "chroma_db_text2vec",
     "ophthalmology_docs_text2vec",
     "model/text2vec-base-chinese"),

    # 跳过：gtr-t5-xl（向量库为空）、medbert-base-chinese（无独立向量库，Flax 模型）
]


class LocalModelRetriever:
    """
    使用本地嵌入模型 + 对应预建 ChromaDB 做纯向量检索。
    每个模型有自己的 ChromaDB，维度不同，不可混用。
    先尝试 SentenceTransformer，失败则 fallback 到 AutoModel（BERT 均值池化）。
    """

    def __init__(
        self,
        display_name: str,
        model_path: str,
        chroma_dir: str,
        collection_name: str,
    ):
        self.model_name   = display_name
        self.model_path   = Path(model_path)
        self.chroma_dir   = chroma_dir
        self.col_name     = collection_name
        self.name         = f"model_{display_name}"
        self.description  = f"嵌入模型: {display_name}"
        self._model       = None
        self._model_type: Optional[str] = None   # "st" or "bert"
        self._collection  = None

    def load_model(self) -> bool:
        """加载嵌入模型，成功返回 True。优先 SentenceTransformer，失败 fallback AutoModel。"""
        # 优先 SentenceTransformer
        try:
            from sentence_transformers import SentenceTransformer
            m = SentenceTransformer(str(self.model_path))
            dim = m.get_sentence_embedding_dimension()
            self._model = m
            self._model_type = "st"
            print(f"    ✅ SentenceTransformer: {self.model_name} (dim={dim})")
            return True
        except Exception as e1:
            logger.debug(f"ST 加载失败 [{self.model_name}]: {e1}")

        # Fallback: AutoModel + mean pooling
        try:
            from transformers import AutoTokenizer, AutoModel
            tok = AutoTokenizer.from_pretrained(str(self.model_path))
            mdl = AutoModel.from_pretrained(str(self.model_path))
            self._model = {"tokenizer": tok, "model": mdl}
            self._model_type = "bert"
            print(f"    ✅ AutoModel: {self.model_name} (dim={mdl.config.hidden_size})")
            return True
        except Exception as e2:
            print(f"    ❌ 模型加载失败 [{self.model_name}]: {e2}")
            return False

    def load_collection(self) -> bool:
        """打开该模型对应的 ChromaDB collection，成功返回 True。"""
        try:
            import chromadb
            from chromadb.config import Settings as CS
            client = chromadb.PersistentClient(
                path=self.chroma_dir,
                settings=CS(anonymized_telemetry=False),
            )
            self._collection = client.get_collection(self.col_name)
            cnt = self._collection.count()
            if cnt == 0:
                print(f"    ⚠️  ChromaDB {self.chroma_dir} 为空，跳过")
                return False
            print(f"    ✅ ChromaDB: {self.chroma_dir} ({cnt} 条)")
            return True
        except Exception as e:
            print(f"    ❌ ChromaDB 加载失败 [{self.chroma_dir}]: {e}")
            return False

    def _embed_query(self, query: str) -> list[float]:
        """用当前模型嵌入单条查询，返回归一化向量。"""
        if self._model_type == "st":
            return self._model.encode(
                [query], normalize_embeddings=True, show_progress_bar=False
            )[0].tolist()
        else:
            import torch
            tok = self._model["tokenizer"]
            mdl = self._model["model"]
            enc = tok([query], padding=True, truncation=True,
                      max_length=512, return_tensors="pt")
            with torch.no_grad():
                out = mdl(**enc)
            token_emb = out[0]
            mask = enc["attention_mask"].unsqueeze(-1).expand(token_emb.size()).float()
            pooled = torch.sum(token_emb * mask, 1) / torch.clamp(mask.sum(1), min=1e-9)
            normed = torch.nn.functional.normalize(pooled, p=2, dim=1)
            return normed[0].numpy().tolist()

    def search_raw(self, query: str, top_k: int) -> list[dict]:
        """用模型嵌入查询后，在对应 ChromaDB 中做向量检索。"""
        q_emb = self._embed_query(query)
        cnt   = self._collection.count()
        res   = self._collection.query(
            query_embeddings=[q_emb],
            n_results=min(top_k, cnt),
            include=["documents", "metadatas", "distances"],
        )
        docs: list[dict] = []
        if res["documents"] and res["documents"][0]:
            for doc, meta, dist in zip(
                res["documents"][0],
                res["metadatas"][0],
                res["distances"][0],
            ):
                docs.append({
                    "content":  doc,
                    "metadata": meta or {},
                    "score":    round(1.0 - dist, 4),
                })
        return docs

    async def retrieve_and_answer(self, question: str, top_k: int) -> dict:
        results  = self.search_raw(question, top_k)
        contexts = [r["content"] for r in results]
        messages = build_rag_messages(question=question, search_results=results)
        answer   = await generate(messages=messages, temperature=0.3)
        return {"answer": answer, "contexts": contexts}


def _get_model_eval_list(filter_name: Optional[str] = None) -> list[tuple[str, str, str, str]]:
    """返回 MODEL_EVAL_LIST，可按 display_name 过滤。"""
    if filter_name:
        return [e for e in MODEL_EVAL_LIST if e[0] == filter_name]
    return list(MODEL_EVAL_LIST)


# ═══════════════════════════════════════════════════════════════════════════════
# 通用评估主循环（含断点续传 + 连续失败检测）
# ═══════════════════════════════════════════════════════════════════════════════

async def evaluate_experiment(
    name: str,
    description: str,
    retrieve_fn: Callable[[str, int], Awaitable[dict]],
    dataset: list[dict],
    top_k: int,
    delay: float,
    calculator: MetricsCalculator,
    checkpoint: CheckpointManager,
    wb_run=None,
    wb_step_offset: int = 0,   # 全局 step 偏移，避免多实验 step 回退被 W&B 忽略
) -> Optional[dict]:
    """
    评估一个实验（config 或 model），支持断点续传。
    若连续 MAX_CONSECUTIVE_FAILURES 题 LLM 全部失败，停止并保存断点，返回 None。
    """
    existing = checkpoint.get_partial_records(name)
    # 只把有成功 scores 的题标为"已完成"；失败记录（429 / 格式错误）重新尝试
    completed_indices = {r["_idx"] for r in existing if "_idx" in r and r.get("scores") is not None}
    # 初始记录列表只保留成功条目，失败题将重新生成记录并追加
    records: list[dict] = [r for r in existing if r.get("scores") is not None]
    consecutive_failures = 0
    total = len(dataset)

    bar = "═" * 68
    print(f"\n{bar}")
    print(f"  实验: {description}  |  题数: {total}  |  Top-K: {top_k}")
    if existing:
        failed_indices = {r["_idx"] for r in existing if "_idx" in r and r.get("scores") is None}
        remaining = sorted(set(range(total)) - completed_indices)
        next_q = remaining[0] + 1 if remaining else total + 1
        msg = f"  断点续传: 已完成 {len(completed_indices)} 题，从第 {next_q} 题继续"
        if failed_indices:
            msg += f"（含重试 {len(failed_indices)} 道失败题）"
        print(msg)
    print(f"{bar}")

    for idx, item in enumerate(dataset):
        if idx in completed_indices:
            continue

        question     = item["question"]
        ground_truth = item["ground_truth"]
        print(f"\n  [{idx+1:2d}/{total}] {question[:55]}")
        t0 = time.time()
        error_msg: Optional[str] = None
        scores = None
        answer, contexts = "", []

        # 题目级重试：专门处理 529 过载，不计入 consecutive_failures
        for q_attempt in range(MAX_QUESTION_RETRIES + 1):
            try:
                ret = await retrieve_fn(question, top_k)
                answer   = ret["answer"]
                contexts = ret["contexts"] or ["（无检索结果）"]

                print("          → 计算指标中...", end="", flush=True)
                scores = await calculator.evaluate_one(question, answer, contexts, ground_truth)
                elapsed = time.time() - t0
                # 记录部分失败的指标名（供 checkpoint 存档）
                failed_metrics = [k for k, v in scores.items() if v is None]
                if failed_metrics:
                    error_msg = f"部分指标失败（重试后仍无效）: {', '.join(failed_metrics)}"
                def _fmt(v: Optional[float]) -> str:
                    return f"{v:.2f}" if v is not None else " N/A"
                print(
                    f" F={_fmt(scores['faithfulness'])}"
                    f" AR={_fmt(scores['answer_relevancy'])}"
                    f" CP={_fmt(scores['context_precision'])}"
                    f" CR={_fmt(scores['context_recall'])}"
                    f" ({elapsed:.1f}s)"
                )
                consecutive_failures = 0
                break  # 成功，退出重试循环

            except Exception as exc:
                if _is_overloaded(exc) and q_attempt < MAX_QUESTION_RETRIES:
                    wait = OVERLOAD_WAIT_BASE * (2 ** q_attempt)  # 90→180→360→720
                    print(f"\n  ⏳ MiniMax 过载 (529)，等待 {wait}s 后重试"
                          f" (第 {q_attempt+1}/{MAX_QUESTION_RETRIES} 次)...", flush=True)
                    await asyncio.sleep(wait)
                    continue  # 重试，不计入失败

                # 非 529 或重试耗尽
                elapsed = time.time() - t0
                error_msg = str(exc)
                logger.error(f"题目处理异常 [{question[:40]}]: {exc}")
                print(f" ❌ {error_msg[:80]}")
                if _is_overloaded(exc):
                    print(f"  ⚠️  529 重试 {MAX_QUESTION_RETRIES} 次后仍失败，API 持续过载")
                consecutive_failures += 1
                break

        record = {
            "_idx":          idx,
            "question":      question,
            "answer":        answer,
            "contexts":      contexts,
            "ground_truth":  ground_truth,
            "context_count": len(contexts),
            "response_time": round(elapsed, 2),
            "scores":        scores,
            "error":         error_msg,
        }
        records.append(record)
        checkpoint.update_partial(name, records)

        # ── W&B 逐题上报 ──────────────────────────────────────────────────
        if wb_run is not None:
            so_far = [r for r in records if r.get("scores")]

            def _run_avg(key: str) -> Optional[float]:
                vals = [r["scores"][key] for r in so_far if r["scores"].get(key) is not None]
                return round(sum(vals) / len(vals), 4) if vals else None

            log_data: dict = {
                f"{name}/question_no":   idx + 1,
                f"{name}/response_time": elapsed,
                f"{name}/failed":        int(scores is None),
                "progress/completed":    len(so_far),
                "progress/total":        total,
            }
            if scores:
                for m in ("faithfulness", "answer_relevancy", "context_precision", "context_recall"):
                    if scores.get(m) is not None:
                        log_data[f"{name}/{m}"] = scores[m]
                    avg = _run_avg(m)
                    if avg is not None:
                        log_data[f"{name}/avg_{m}"] = avg
            wb_run.log(log_data, step=wb_step_offset + idx)

        if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
            print(f"\n  ⛔ 连续 {consecutive_failures} 题 LLM 调用失败，停止并保存断点")
            print(f"  💾 检查点: {checkpoint.path}")
            print(f"  ▶  恢复命令: python scripts/evaluate_ragas.py --resume {checkpoint.path}")
            return None

        if idx < total - 1:
            await asyncio.sleep(delay)

    # 汇总：有任意指标成功的记录都计入
    valid = [r for r in records if r.get("scores") is not None]
    n = max(len(valid), 1)

    def _avg(key: str) -> float:
        """按指标逐一过滤 None，避免部分失败题目拉偏均值。"""
        vals = [
            r["scores"][key] for r in valid
            if r["scores"].get(key) is not None
        ]
        return round(sum(vals) / max(len(vals), 1), 4) if vals else 0.0

    avg_scores = {
        "faithfulness":      _avg("faithfulness"),
        "answer_relevancy":  _avg("answer_relevancy"),
        "context_precision": _avg("context_precision"),
        "context_recall":    _avg("context_recall"),
    }
    avg_rt  = round(sum(r["response_time"] for r in valid) / n, 2)
    avg_ctx = round(sum(r["context_count"]  for r in valid) / n, 1)

    # 去掉内部 _idx 字段
    clean_records = [{k: v for k, v in r.items() if k != "_idx"} for r in records]

    result = {
        "experiment_name":        name,
        "experiment_description": description,
        "total":                  len(records),
        "successful":             len(valid),
        "failed":                 len(records) - len(valid),
        "avg_response_time":      avg_rt,
        "avg_context_count":      avg_ctx,
        "avg_scores":             avg_scores,
        "records":                clean_records,
    }
    checkpoint.complete_experiment(name, result)

    print(f"\n  ── 实验 {name} 完成 ──")
    print(f"     成功/总计:          {len(valid)}/{len(records)}")
    for k, label in [
        ("faithfulness",      "Faithfulness     "),
        ("answer_relevancy",  "Answer Relevancy "),
        ("context_precision", "Context Precision"),
        ("context_recall",    "Context Recall   "),
    ]:
        print(f"     {label}:  {avg_scores[k]:.4f}")

    # ── W&B 实验汇总 ──────────────────────────────────────────────────────
    if wb_run is not None:
        cols = ["#", "问题", "Faithfulness", "Answer Relevancy",
                "Context Precision", "Context Recall", "响应时间(s)", "状态"]
        tbl = _wandb.Table(columns=cols)
        for r in records:
            s = r.get("scores") or {}
            if r.get("scores") is None:
                status = "❌ 全部失败"
            elif r.get("error"):
                status = f"⚠️ {r['error'][:40]}"
            else:
                status = "✅"
            tbl.add_data(
                r.get("_idx", 0) + 1,
                r["question"][:60],
                s.get("faithfulness"),
                s.get("answer_relevancy"),
                s.get("context_precision"),
                s.get("context_recall"),
                r.get("response_time"),
                status,
            )
        wb_run.log({
            f"{name}/details_table":          tbl,
            f"{name}/final_faithfulness":      avg_scores["faithfulness"],
            f"{name}/final_answer_relevancy":  avg_scores["answer_relevancy"],
            f"{name}/final_context_precision": avg_scores["context_precision"],
            f"{name}/final_context_recall":    avg_scores["context_recall"],
            f"{name}/success_rate":            round(len(valid) / max(len(records), 1), 4),
            f"{name}/avg_response_time":       avg_rt,
        })

    return result


# ═══════════════════════════════════════════════════════════════════════════════
# 报告生成
# ═══════════════════════════════════════════════════════════════════════════════

def generate_report(all_results: list[dict], mode: str, top_k: int, ts: str) -> str:
    lines: list[str] = []
    mode_label = "检索配置对比（Config A/B/C）" if mode == "configs" else "嵌入模型对比"
    judge_label = (
        f"MiniMax ({settings.minimax_model_name})"
        if settings.llm_provider.lower() == "minimax"
        else f"DeepSeek ({settings.llm_model_name})"
    )

    lines += [
        "# RAGAs 启发式评估报告",
        "",
        "> **项目**：基于 RAG 的眼科医疗知识问答系统  ",
        f"> **评估时间**：{ts}  ",
        f"> **评估模式**：{mode_label}  ",
        f"> **Top-K 检索数**：{top_k}  ",
        f"> **题目数**：{all_results[0]['total'] if all_results else 0} 题  ",
        f"> **裁判 LLM**：{judge_label}  ",
        "> **作者**：鞠明轩 · 云南大学软件学院软件工程 2022 级  ",
        "",
        "---",
        "",
        "## 一、评估指标说明",
        "",
        "| 指标 | 含义 | 计算方式 |",
        "|------|------|---------|",
        "| **Faithfulness** | 忠实度：回答中的陈述是否均有检索文档支撑 | LLM 提取答案陈述句，逐条判断是否有文档支持，计算比例 |",
        "| **Answer Relevancy** | 答案相关性：回答是否切题、无冗余 | LLM 从回答反向生成问题，与原问题计算 cosine 相似度均值 |",
        "| **Context Precision** | 上下文精确率：检索文档中相关文档的比例及排名 | LLM 逐块判断相关性，结合排名计算 Average Precision |",
        "| **Context Recall** | 上下文召回率：标准答案的知识点是否被检索内容覆盖 | LLM 拆分标准答案为关键陈述，逐句判断覆盖情况 |",
        "",
        "---",
        "",
    ]

    if mode == "configs":
        lines += [
            "## 二、实验配置说明",
            "",
            "| 配置 | 描述 | 关键技术 |",
            "|------|------|---------|",
            "| **Config A** | 纯向量检索（基线） | ChromaDB HNSW 近似最近邻 |",
            "| **Config B** | 混合检索 | 向量检索 + BM25 关键词检索 + RRF 排序融合 |",
            "| **Config C** | 混合检索 + 重排序 | Config B + 关键词覆盖率重排序 |",
            "| **Config D** | 混合检索 + 重排序 + 双语翻译（当前生产配置） | Config C + 中文查询翻译 + 双路向量/BM25检索 |",
            "",
            "---",
            "",
        ]
    else:
        lines += [
            "## 二、模型说明",
            "",
            "所有模型均使用纯向量检索（控制变量），对比嵌入质量对 RAG 性能的影响。",
            "",
            "| 模型 | 说明 |",
            "|------|------|",
        ]
        for r in all_results:
            lines.append(f"| **{r['experiment_name']}** | {r['experiment_description']} |")
        lines += ["", "---", ""]

    metric_keys   = ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]
    metric_labels = ["Faithfulness↑", "Answer Relevancy↑", "Context Precision↑", "Context Recall↑"]

    lines += [
        "## 三、核心评估结果",
        "",
        "### 3.1 RAGAs 指标汇总表",
        "",
        "| 实验 | " + " | ".join(metric_labels) + " | 平均响应时间 |",
        "|------|" + "|".join([":---:"] * len(metric_labels)) + "|:---:|",
    ]
    for r in all_results:
        s = r["avg_scores"]
        lines.append(
            f"| **{r['experiment_name']}** {r['experiment_description']} "
            + " | ".join(f"{s[k]:.4f}" for k in metric_keys)
            + f" | {r['avg_response_time']:.2f}s |"
        )

    lines += ["", "### 3.2 得分可视化（10 格进度条）", ""]
    for r in all_results:
        lines.append(f"**{r['experiment_name']} — {r['experiment_description']}**\n")
        lines.append("```")
        for key, label in zip(metric_keys, ["Faithfulness      ", "Answer Relevancy  ",
                                             "Context Precision ", "Context Recall    "]):
            score = r["avg_scores"][key]
            lines.append(f"  {label} {_bar(score)}  {score:.4f}")
        lines.append("```\n")

    # 提升幅度（相对第一个实验）
    if len(all_results) >= 2:
        base = all_results[0]["avg_scores"]
        base_name = all_results[0]["experiment_name"]
        lines += [
            f"### 3.3 相对基线（{base_name}）的提升幅度",
            "",
            "| 指标 | " + " | ".join(r["experiment_name"] for r in all_results[1:]) + " |",
            "|------|" + "|".join([":------:"] * (len(all_results) - 1)) + "|",
        ]
        for key, label in zip(metric_keys, ["Faithfulness", "Answer Relevancy",
                                             "Context Precision", "Context Recall"]):
            row = f"| {label} |"
            for r in all_results[1:]:
                delta = r["avg_scores"][key] - base[key]
                sign = "+" if delta >= 0 else ""
                row += f" {sign}{delta:.4f} |"
            lines.append(row)
        lines.append("")

    # 运行统计
    lines += [
        "---",
        "",
        "## 四、运行统计",
        "",
        "| 实验 | 总题数 | 成功 | 失败 | 平均上下文数 |",
        "|------|:------:|:----:|:----:|:----------:|",
    ]
    for r in all_results:
        lines.append(
            f"| **{r['experiment_name']}** | {r['total']} "
            f"| {r['successful']} | {r['failed']} "
            f"| {r['avg_context_count']} |"
        )

    # 逐题明细
    lines += ["", "---", "", "## 五、逐题明细", ""]
    for r in all_results:
        lines += [
            f"### {r['experiment_name']} — {r['experiment_description']}",
            "",
            "| # | 问题 | F | AR | CP | CR | 响应时间 |",
            "|---|------|:-:|:--:|:--:|:--:|:------:|",
        ]
        def _cell(v: Optional[float]) -> str:
            return f"{v:.2f}" if v is not None else "N/A"

        for i, rec in enumerate(r["records"], 1):
            s = rec.get("scores")
            if s is None:
                lines.append(f"| {i} | ❌ {rec['question'][:45]} | — | — | — | — | — |")
            else:
                lines.append(
                    f"| {i} | {rec['question'][:45]} "
                    f"| {_cell(s.get('faithfulness'))} "
                    f"| {_cell(s.get('answer_relevancy'))} "
                    f"| {_cell(s.get('context_precision'))} "
                    f"| {_cell(s.get('context_recall'))} "
                    f"| {rec['response_time']:.1f}s |"
                )
        lines.append("")

    lines += [
        "---",
        "",
        "## 六、方法说明",
        "",
        f"本评估采用 RAGAs 启发式方法，使用 {judge_label}（temperature=0）作为裁判 LLM：",
        "",
        "- **Faithfulness**：裁判 LLM 提取回答中的核心陈述，逐条判断是否在检索文档中有明确支撑",
        "- **Answer Relevancy**：裁判 LLM 从回答反向生成 3 个问题，与原始问题用项目嵌入模型计算 cosine 相似度均值",
        "- **Context Precision**：裁判 LLM 对 Top-K 检索块逐一判断相关性，结合排名位置计算 Average Precision",
        "- **Context Recall**：裁判 LLM 将标准答案拆解为关键陈述，判断检索内容对每条陈述的覆盖情况",
        "",
        f"*报告生成时间：{ts}*  ",
        "*作者：鞠明轩 · 云南大学软件学院软件工程 2022 级*",
    ]

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# 保存结果
# ═══════════════════════════════════════════════════════════════════════════════

def save_results(
    all_results: list[dict], mode: str, top_k: int, ts: str, run_id: str,
) -> tuple[Path, Path]:
    out_dir = Path("data")
    out_dir.mkdir(parents=True, exist_ok=True)

    judge = (
        f"MiniMax/{settings.minimax_model_name}"
        if settings.llm_provider.lower() == "minimax"
        else f"DeepSeek/{settings.llm_model_name}"
    )
    payload = {
        "meta": {
            "run_id":          run_id,
            "timestamp":       ts,
            "mode":            mode,
            "top_k":           top_k,
            "total_questions": all_results[0]["total"] if all_results else 0,
            "judge_llm":       judge,
            "method":          "RAGAs 启发式，LLM-as-Judge",
        },
        "summary": [
            {k: v for k, v in r.items() if k != "records"}
            for r in all_results
        ],
        "details": [
            {"experiment_name": r["experiment_name"], "records": r["records"]}
            for r in all_results
        ],
    }

    json_path = out_dir / f"ragas_results_{ts}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    md_path = out_dir / f"ragas_report_{ts}.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(generate_report(all_results, mode, top_k, ts))

    return json_path, md_path


# ═══════════════════════════════════════════════════════════════════════════════
# 评估专用日志文件
# ═══════════════════════════════════════════════════════════════════════════════

def _setup_eval_log(run_id: str) -> Path:
    """为本次评估添加独立的文件日志 sink，返回日志文件路径。

    日志路径：logs/evaluate_<run_id>.log
    级别：INFO（含 WARNING / ERROR），与应用日志分离，每次运行一份。
    """
    log_dir = Path("logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"evaluate_{run_id}.log"

    logger.add(
        str(log_path),
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        encoding="utf-8",
        enqueue=False,
    )
    return log_path


# ═══════════════════════════════════════════════════════════════════════════════
# CLI 参数
# ═══════════════════════════════════════════════════════════════════════════════

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="RAGAs 启发式评估脚本 v2 - 眼科 RAG 系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""示例：
  python scripts/evaluate_ragas.py                          # configs 模式 A+B+C 50题
  python scripts/evaluate_ragas.py --limit 5                # 快速验证 5 题
  python scripts/evaluate_ragas.py --config C               # 只跑 Config C
  python scripts/evaluate_ragas.py --mode models            # 对比所有本地模型
  python scripts/evaluate_ragas.py --mode models --limit 10 # 模型模式 10 题
  python scripts/evaluate_ragas.py --mode models --model bge-base-zh-v1.5
  python scripts/evaluate_ragas.py --resume data/checkpoint_xxx.json
""",
    )
    parser.add_argument("--mode", default="configs", choices=["configs", "models"],
                        help="评估模式（默认 configs = A/B/C 对比）")
    parser.add_argument("--config", default="all", choices=["A", "B", "C", "D", "E", "all"],
                        help="[configs 模式] 评估哪些配置（默认 all；E = Self-RAG 消融实验）")
    parser.add_argument("--model", default=None,
                        help="[models 模式] 只评估指定模型名（默认评估全部）")
    parser.add_argument("--model-dir", default="model",
                        help="[models 模式] 本地模型根目录（默认 ./model）")
    parser.add_argument("--limit", type=int, default=0,
                        help="只评估前 N 题（0 = 全部 50 题）")
    parser.add_argument("--top-k", type=int, default=10,
                        help="RAG 检索 Top-K 数量（默认 10，与生产环境 RETRIEVAL_TOP_K=10 保持一致）")
    parser.add_argument("--delay", type=float, default=2.0,
                        help="每题结束后等待秒数（默认 2.0，避免 API 限速）")
    parser.add_argument("--resume", default=None,
                        help="从指定检查点文件继续上次实验")
    parser.add_argument("--no-wandb", action="store_true",
                        help="禁用 W&B 实验追踪（默认启用，若已安装 wandb）")
    return parser.parse_args()


# ═══════════════════════════════════════════════════════════════════════════════
# 主入口
# ═══════════════════════════════════════════════════════════════════════════════

async def main() -> None:
    args = _parse_args()

    print("=" * 68)
    print("  RAGAs 启发式评估 v2 - 基于 RAG 的眼科医疗知识问答系统")
    print("=" * 68)
    _check_llm_provider()

    # ── 加载或新建检查点 ────────────────────────────────────────────────────
    if args.resume:
        resume_path = Path(args.resume)
        if not resume_path.exists():
            print(f"  ❌ 检查点文件不存在: {resume_path}")
            sys.exit(1)
        checkpoint = CheckpointManager.load(resume_path)
        mode    = checkpoint.mode
        top_k   = checkpoint.top_k
        limit   = checkpoint.dataset_limit
        run_id  = checkpoint.run_id
    else:
        ts     = datetime.now().strftime("%Y%m%d_%H%M%S")
        mode   = args.mode
        top_k  = args.top_k
        limit  = args.limit
        run_id = ts
        checkpoint = CheckpointManager.new(run_id, mode, top_k, limit)

    eval_log = _setup_eval_log(run_id)
    print(f"  评估日志  → {eval_log}")
    logger.info(f"评估开始 run_id={run_id} mode={mode} top_k={top_k} limit={limit}")

    # ── W&B 初始化 ──────────────────────────────────────────────────────
    wb_run = None
    if _WANDB_AVAILABLE and not args.no_wandb:
        provider = settings.llm_provider.lower()
        judge_label = (
            f"MiniMax/{settings.minimax_model_name}" if provider == "minimax"
            else f"DeepSeek/{settings.llm_model_name}"
        )
        dataset_size = len(EVAL_DATASET[:limit]) if limit > 0 else len(EVAL_DATASET)
        try:
            wb_run = _wandb.init(
                project="ophthalmology-rag-eval",
                name=run_id,
                id=run_id,
                resume="allow",
                config={
                    "mode":         mode,
                    "top_k":        top_k,
                    "limit":        limit or dataset_size,
                    "judge_llm":    judge_label,
                    "dataset_size": dataset_size,
                },
                tags=[mode, f"top_k_{top_k}", provider],
            )
            print(f"  W&B 追踪   → {wb_run.url}")
        except Exception as wb_err:
            print(f"  ⚠️  W&B 初始化失败，跳过追踪（评估正常继续）: {wb_err}")
            print(f"      提示: 运行 `wandb login --relogin` 重新登录后重试")
            wb_run = None
    elif not _WANDB_AVAILABLE and not args.no_wandb:
        print("  W&B 未安装，跳过追踪（pip install wandb 后重试）")

    dataset = EVAL_DATASET[:limit] if limit > 0 else EVAL_DATASET
    calculator = MetricsCalculator()
    all_results: list[dict] = list(checkpoint.all_results)

    print(f"  模式: {mode}  |  题数: {len(dataset)}  |  Top-K: {top_k}  |  延迟: {args.delay}s")
    print(f"  检查点: {checkpoint.path}")
    print("=" * 68)

    t_total = time.time()

    # ── configs 模式 ────────────────────────────────────────────────────────
    wb_global_step = 0  # 跨实验全局 step，保证 W&B 曲线单调递增
    if mode == "configs":
        if args.config != "all":
            config_keys = [args.config]
        elif args.resume:
            # --resume 时自动从 checkpoint 推断应该跑哪些配置：
            # 构建 "实验名 → 配置键" 的反向映射，找到 partial_experiment 对应的键，
            # 只保留从该键起往后的未完成配置，避免重跑已完成或无关的实验。
            _name_to_key = {}
            for _k, _cls in ALL_CONFIGS.items():
                try:
                    _name_to_key[_cls.name] = _k
                except AttributeError:
                    pass
            _partial = checkpoint._data.get("partial_experiment")
            _partial_key = None
            if _partial:
                _partial_key = _name_to_key.get(_partial.get("name"))
            _all_keys = list(ALL_CONFIGS.keys())
            if _partial_key and _partial_key in _all_keys:
                _start = _all_keys.index(_partial_key)
                config_keys = _all_keys[_start:]
                print(f"  🔍 自动推断续跑配置: {config_keys}（从 partial_experiment '{_partial_key}' 开始）")
            else:
                # 找不到 partial 时，跑所有未完成的
                config_keys = _all_keys
        else:
            config_keys = ["A", "B", "C"]
        for key in config_keys:
            cfg = ALL_CONFIGS[key]()
            if checkpoint.is_completed(cfg.name):
                print(f"\n  ⏭  跳过已完成实验: {cfg.name}")
                wb_global_step += len(dataset)
                continue
            result = await evaluate_experiment(
                name=cfg.name,
                description=cfg.description,
                retrieve_fn=cfg.retrieve_and_answer,
                dataset=dataset,
                top_k=top_k,
                delay=args.delay,
                calculator=calculator,
                checkpoint=checkpoint,
                wb_run=wb_run,
                wb_step_offset=wb_global_step,
            )
            wb_global_step += len(dataset)
            if result is None:
                print("\n  实验中断，已保存断点。退出。")
                return
            all_results.append(result)

    # ── models 模式 ─────────────────────────────────────────────────────────
    else:
        eval_list = _get_model_eval_list(filter_name=args.model)
        if not eval_list:
            print(f"  ❌ 未找到模型配置（--model={args.model}），退出。")
            print(f"  可用模型: {[e[0] for e in MODEL_EVAL_LIST]}")
            sys.exit(1)

        print(f"\n  待评估模型: {[e[0] for e in eval_list]}")
        print(f"  说明: 每个模型使用各自独立的 ChromaDB，纯向量检索（控制变量）")

        for display_name, chroma_dir, col_name, model_path in eval_list:
            retriever = LocalModelRetriever(display_name, model_path, chroma_dir, col_name)
            exp_name  = retriever.name

            if checkpoint.is_completed(exp_name):
                print(f"\n  ⏭  跳过已完成实验: {exp_name}")
                wb_global_step += len(dataset)
                continue

            print(f"\n  {'─' * 60}")
            print(f"  模型: {display_name}")
            print(f"  向量库: {chroma_dir} / {col_name}")

            if not retriever.load_model():
                print(f"  ⚠️  模型加载失败，跳过: {display_name}")
                wb_global_step += len(dataset)
                continue

            if not retriever.load_collection():
                print(f"  ⚠️  向量库加载失败，跳过: {display_name}")
                wb_global_step += len(dataset)
                continue

            result = await evaluate_experiment(
                name=exp_name,
                description=retriever.description,
                retrieve_fn=retriever.retrieve_and_answer,
                dataset=dataset,
                top_k=top_k,
                delay=args.delay,
                calculator=calculator,
                checkpoint=checkpoint,
                wb_run=wb_run,
                wb_step_offset=wb_global_step,
            )
            wb_global_step += len(dataset)
            if result is None:
                print("\n  实验中断，已保存断点。退出。")
                if wb_run is not None:
                    wb_run.finish(exit_code=1)
                return
            all_results.append(result)

    # ── 输出报告 ─────────────────────────────────────────────────────────────
    if not all_results:
        print("\n  没有可用的评估结果，退出。")
        if wb_run is not None:
            wb_run.finish(exit_code=1)
        return

    elapsed_min = (time.time() - t_total) / 60
    ts_out = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path, md_path = save_results(all_results, mode, top_k, ts_out, run_id)

    logger.info(
        f"评估完成 run_id={run_id} 耗时={elapsed_min:.1f}min "
        f"实验数={len(all_results)} "
        f"结果={json_path}"
    )

    # ── W&B 最终汇总：跨实验对比表 ──────────────────────────────────────
    if wb_run is not None:
        comp_cols = ["实验", "Faithfulness", "Answer Relevancy",
                     "Context Precision", "Context Recall", "成功率", "平均响应时间(s)"]
        comp_tbl = _wandb.Table(columns=comp_cols)
        for r in all_results:
            s = r["avg_scores"]
            comp_tbl.add_data(
                r["experiment_name"],
                s["faithfulness"],
                s["answer_relevancy"],
                s["context_precision"],
                s["context_recall"],
                round(r["successful"] / max(r["total"], 1), 4),
                r["avg_response_time"],
            )
        wb_run.log({
            "summary/comparison_table": comp_tbl,
            "summary/total_experiments": len(all_results),
            "summary/elapsed_minutes":   round(elapsed_min, 2),
        })
        wb_run.finish()
        print(f"  W&B 报告   → {wb_run.url}")

    print(f"\n{'═' * 68}")
    print(f"  全部评估完成！总耗时 {elapsed_min:.1f} 分钟")
    print(f"  原始数据  → {json_path}")
    print(f"  MD 报告   → {md_path}")
    print(f"  评估日志  → {eval_log}")
    print(f"{'═' * 68}\n")


if __name__ == "__main__":
    asyncio.run(main())
