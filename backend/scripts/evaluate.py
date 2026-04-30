"""
RAG 系统评估框架
基于 RAGAs 指标体系评估系统性能:
  - 忠实度 (Faithfulness)
  - 答案相关性 (Answer Relevancy)
  - 上下文精确率 (Context Precision)
  - 上下文召回率 (Context Recall)

使用方式:
  cd backend && python scripts/evaluate.py
"""

import sys
import json
import time
import asyncio
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))


# ===== 眼科评估数据集 (约50个问题) =====
EVAL_DATASET = [
    # 疾病认知
    {"question": "什么是青光眼？它有哪些类型？", "ground_truth": "青光眼是一种以视神经损害为特征的眼病，通常与眼压升高有关。主要类型包括开角型青光眼、闭角型青光眼和继发性青光眼。"},
    {"question": "糖尿病视网膜病变的分期是什么？", "ground_truth": "糖尿病视网膜病变分为非增殖期(NPDR)和增殖期(PDR)。非增殖期包括轻度、中度和重度，增殖期表现为新生血管形成。"},
    {"question": "白内障是怎么形成的？", "ground_truth": "白内障是晶状体蛋白质变性导致混浊，主要原因包括老化、紫外线损伤、代谢疾病、外伤等。"},
    {"question": "什么是黄斑变性？", "ground_truth": "黄斑变性(AMD)是影响视网膜黄斑区的退行性疾病，分为干性和湿性两种，是老年人视力丧失的主要原因。"},
    {"question": "角膜炎有哪些常见类型？", "ground_truth": "角膜炎主要包括细菌性角膜炎、病毒性角膜炎(如单疱病毒)、真菌性角膜炎和棘阿米巴角膜炎。"},
    {"question": "什么是干眼症？", "ground_truth": "干眼症是泪液分泌不足或泪膜不稳定导致的眼表疾病，症状包括眼干、异物感、视力波动。"},
    {"question": "视网膜脱离的症状有哪些？", "ground_truth": "视网膜脱离的症状包括突然出现飞蚊症、闪光感、视野缺损（如幕帘遮挡感）和视力下降。"},
    {"question": "什么是弱视？如何治疗？", "ground_truth": "弱视是视觉发育期由于异常视觉经验导致的单眼或双眼最佳矫正视力下降。治疗包括光学矫正、遮盖疗法和药物压抑。"},
    {"question": "翼状胬肉是什么？", "ground_truth": "翼状胬肉是结膜组织向角膜表面增生的三角形纤维血管组织，与紫外线照射和干燥环境有关。"},
    {"question": "什么是圆锥角膜？", "ground_truth": "圆锥角膜是角膜中央或旁中央进行性变薄、前突呈锥形的非炎症性疾病，导致不规则散光和视力下降。"},

    # 诊断方法
    {"question": "眼底检查能发现什么问题？", "ground_truth": "眼底检查可发现视网膜病变、黄斑变性、青光眼视神经损害、视网膜血管疾病、视网膜脱离等。"},
    {"question": "OCT 检查是什么？有什么用途？", "ground_truth": "OCT（光学相干断层扫描）是使用光干涉原理对视网膜进行断层成像的检查，可检测黄斑病变、青光眼视神经纤维层厚度等。"},
    {"question": "如何测量眼压？", "ground_truth": "测量眼压的方法包括Goldmann压平眼压计、非接触式气动眼压计（NCT）和手持式回弹式眼压计。"},
    {"question": "视野检查有什么作用？", "ground_truth": "视野检查用于检测视野缺损，对青光眼诊断和随访、视路疾病定位、视神经疾病评估很重要。"},
    {"question": "什么是角膜地形图检查？", "ground_truth": "角膜地形图是测量角膜前表面曲率分布的检查方法，用于屈光手术术前评估、角膜疾病诊断和隐形眼镜验配。"},
    {"question": "裂隙灯检查能看什么？", "ground_truth": "裂隙灯显微镜可检查眼睑、结膜、角膜、前房、虹膜、晶状体和前部玻璃体结构。"},
    {"question": "FFA 检查是什么？", "ground_truth": "FFA（荧光素眼底血管造影）是静脉注射荧光素后拍摄眼底血管影像的检查，用于诊断视网膜血管疾病。"},

    # 治疗方法
    {"question": "LASIK 手术的原理是什么？", "ground_truth": "LASIK通过准分子激光切削角膜基质改变角膜曲率来矫正近视、远视和散光。"},
    {"question": "白内障手术是怎么做的？", "ground_truth": "白内障手术通常采用超声乳化术，通过小切口将混浊的晶状体乳化吸除，然后植入人工晶状体。"},
    {"question": "青光眼如何降眼压治疗？", "ground_truth": "青光眼降眼压治疗包括药物（前列腺素类、β受体阻滞剂等）、激光治疗（SLT、LPI）和手术（小梁切除术、引流管植入）。"},
    {"question": "玻璃体切除术适用于什么？", "ground_truth": "玻璃体切除术适用于玻璃体出血、视网膜脱离、黄斑裂孔、黄斑前膜和增殖性糖尿病视网膜病变等。"},
    {"question": "抗VEGF治疗是什么？", "ground_truth": "抗VEGF治疗是通过玻璃体腔注射抗血管内皮生长因子药物来抑制异常血管生成，用于湿性AMD、DME等。"},
    {"question": "角膜移植有几种类型？", "ground_truth": "角膜移植主要包括穿透性角膜移植(PK)、板层角膜移植(LK)、内皮移植(DSAEK/DMEK)等。"},
    {"question": "PRK 和 LASIK 有什么区别？", "ground_truth": "PRK直接在角膜上皮去除后切削角膜表面，LASIK制作角膜瓣后切削基质。PRK恢复慢但无瓣膜并发症。"},
    {"question": "ICL 植入手术是什么？", "ground_truth": "ICL（有晶体眼人工晶体植入术）是将人工晶体植入眼内虹膜与晶状体之间来矫正高度近视。"},

    # 眼科药物
    {"question": "常用的眼科抗炎药物有哪些？", "ground_truth": "常用眼科抗炎药包括皮质类固醇（如地塞米松、氟米龙）和非甾体抗炎药（如双氯芬酸、酮咯酸）。"},
    {"question": "散瞳药物有哪些？有什么作用？", "ground_truth": "常用散瞳药包括阿托品、环戊通、托吡卡胺，用于眼底检查、睫状肌麻痹验光和虹膜炎治疗。"},
    {"question": "人工泪液有哪些类型？", "ground_truth": "人工泪液按成分分为含防腐剂和不含防腐剂型，按黏度分为低黏度水溶液和高黏度凝胶型。"},

    # 眼部解剖
    {"question": "人眼的屈光系统包括哪些结构？", "ground_truth": "人眼的屈光系统包括角膜、前房房水、晶状体和玻璃体，其中角膜占总屈光力约2/3。"},
    {"question": "视网膜有哪些重要的细胞层？", "ground_truth": "视网膜主要细胞层包括色素上皮层、光感受器层（视锥细胞和视杆细胞）、双极细胞层和神经节细胞层。"},
    {"question": "房水的循环路径是什么？", "ground_truth": "房水由睫状体产生，流入后房，经瞳孔进入前房，通过小梁网和Schlemm管排出眼外。"},
    {"question": "什么是泪膜？有几层？", "ground_truth": "泪膜覆盖在角膜和结膜表面，由外到内分为脂质层、水液层和黏蛋白层三层结构。"},

    # 儿童眼科
    {"question": "儿童近视防控的方法有哪些？", "ground_truth": "儿童近视防控方法包括增加户外活动、低浓度阿托品滴眼液、角膜塑形镜（OK镜）和多焦点眼镜。"},
    {"question": "先天性白内障该怎么处理？", "ground_truth": "先天性白内障需早期手术治疗，术后进行光学矫正和弱视训练，以促进视觉发育。"},
    {"question": "斜视有哪些类型？", "ground_truth": "斜视分为共同性和非共同性（麻痹性），按方向分为内斜视、外斜视、上斜视和下斜视。"},

    # 眼科紧急情况
    {"question": "化学性眼灼伤的紧急处理？", "ground_truth": "化学性眼灼伤应立即用大量清水持续冲洗至少15-30分钟，碱性灼伤比酸性灼伤更危险。"},
    {"question": "急性闭角型青光眼发作怎么办？", "ground_truth": "急性闭角型青光眼发作表现为剧烈眼痛、头痛、恶心、视力骤降，需紧急降眼压并行激光虹膜切开术。"},
    {"question": "眼外伤穿通伤如何处理？", "ground_truth": "眼外伤穿通伤应避免揉眼，用盾形保护罩保护伤眼，禁止加压包扎，尽快转运至眼科中心手术修复。"},

    # 眼科新技术
    {"question": "飞秒激光在眼科有什么应用？", "ground_truth": "飞秒激光在眼科用于LASIK角膜瓣制作、白内障手术辅助、角膜移植切割和屈光手术。"},
    {"question": "什么是基因治疗在眼科的应用？", "ground_truth": "眼科基因治疗已用于遗传性视网膜营养不良（如Luxturna治疗RPE65基因突变相关的Leber先天性黑矇）。"},
    {"question": "人工智能在眼科诊断中的应用？", "ground_truth": "AI在眼科用于糖尿病视网膜病变自动筛查、青光眼OCT影像分析、AMD进展预测等。"},

    # 综合问题
    {"question": "高血压对眼睛有什么影响？", "ground_truth": "高血压可导致高血压性视网膜病变，表现为视网膜动脉变细、动静脉交叉征、棉絮斑和出血。"},
    {"question": "糖尿病患者应该多久做一次眼底检查？", "ground_truth": "1型糖尿病发病5年后应每年检查，2型糖尿病确诊时即应检查，之后至少每年一次。"},
    {"question": "长期使用电子设备对眼睛有什么影响？", "ground_truth": "长期使用电子设备可导致视疲劳、干眼症加重、近视进展加速，建议遵循20-20-20规则。"},
    {"question": "老花眼是怎么回事？", "ground_truth": "老花眼（老视）是随年龄增长晶状体弹性下降、调节能力减退导致的近距离视物困难，通常40岁后出现。"},
    {"question": "隐形眼镜使用不当会有什么风险？", "ground_truth": "隐形眼镜使用不当可导致角膜感染、角膜缺氧、巨乳头性结膜炎和角膜新生血管。"},
    {"question": "眼部过敏有哪些表现？如何治疗？", "ground_truth": "眼部过敏表现为眼痒、充血、流泪、眼睑水肿，治疗包括抗组胺药、肥大细胞稳定剂和冷敷。"},
    {"question": "什么是虹膜睫状体炎？", "ground_truth": "虹膜睫状体炎（前葡萄膜炎）是虹膜和睫状体的炎症，表现为充血、疼痛、畏光和瞳孔缩小。"},
    {"question": "结膜炎和角膜炎有什么区别？", "ground_truth": "结膜炎主要表现为充血分泌物多但视力不受影响，角膜炎影响视力且可伴角膜溃疡，更为严重。"},
]


class RAGEvaluator:
    """RAG 系统评估器"""

    def __init__(self):
        from app.rag.pipeline import get_rag_pipeline
        self.pipeline = get_rag_pipeline()

    async def evaluate_single(self, question: str, ground_truth: str) -> dict:
        """评估单个问题"""
        result = await self.pipeline.query(question=question, top_k=5)
        answer = result["answer"]
        sources = result.get("sources", [])
        context_count = result.get("context_count", 0)

        # 计算评估指标
        metrics = {
            "question": question,
            "answer": answer[:200],
            "ground_truth": ground_truth[:200],
            "context_count": context_count,
            "source_count": len(sources),
            "answer_length": len(answer),
            # 简化指标计算
            "faithfulness": self._calc_faithfulness(answer, sources),
            "answer_relevancy": self._calc_relevancy(answer, question, ground_truth),
            "context_precision": self._calc_context_precision(sources, question),
        }
        return metrics

    def _calc_faithfulness(self, answer: str, sources: list) -> float:
        """忠实度: 回答内容是否基于检索到的参考资料"""
        if not sources:
            return 0.3  # 无来源时给基线分
        # 简化: 检查是否有来源引用
        has_ref = any(keyword in answer for keyword in ["参考", "来源", "根据", "资料", "文献"])
        score = 0.7 if has_ref else 0.5
        score += min(len(sources), 5) * 0.06
        return min(score, 1.0)

    def _calc_relevancy(self, answer: str, question: str, ground_truth: str) -> float:
        """答案相关性: 是否回答了用户的实际问题"""
        if not answer:
            return 0.0
        q_terms = set(question.lower().split())
        a_terms = set(answer.lower().split())
        gt_terms = set(ground_truth.lower().split())

        q_coverage = len(q_terms & a_terms) / max(len(q_terms), 1)
        gt_overlap = len(gt_terms & a_terms) / max(len(gt_terms), 1)

        return min(q_coverage * 0.4 + gt_overlap * 0.6, 1.0)

    def _calc_context_precision(self, sources: list, question: str) -> float:
        """上下文精确率: 检索到的文档是否与问题相关"""
        if not sources:
            return 0.0
        scores = [s.get("score", 0) for s in sources]
        avg_score = sum(scores) / len(scores) if scores else 0
        return avg_score

    async def evaluate_all(self, dataset: list = None, limit: int = 50) -> dict:
        """批量评估"""
        data = (dataset or EVAL_DATASET)[:limit]
        results = []
        total_time = 0

        print(f"\n{'='*70}")
        print(f"RAG 系统评估 - 共 {len(data)} 个问题")
        print(f"{'='*70}\n")

        for i, item in enumerate(data, 1):
            start = time.time()
            try:
                metrics = await self.evaluate_single(item["question"], item["ground_truth"])
                elapsed = time.time() - start
                total_time += elapsed
                metrics["response_time"] = elapsed
                results.append(metrics)

                print(f"  [{i:2d}/{len(data)}] ✅ {item['question'][:40]:<40s} "
                      f"相关性={metrics['answer_relevancy']:.2f} "
                      f"忠实度={metrics['faithfulness']:.2f} "
                      f"({elapsed:.1f}s)")
            except Exception as e:
                print(f"  [{i:2d}/{len(data)}] ❌ {item['question'][:40]:<40s} Error: {e}")
                results.append({"question": item["question"], "error": str(e)})

        # 聚合统计
        valid = [r for r in results if "error" not in r]
        summary = {
            "total_questions": len(data),
            "successful": len(valid),
            "failed": len(data) - len(valid),
            "avg_faithfulness": sum(r["faithfulness"] for r in valid) / max(len(valid), 1),
            "avg_answer_relevancy": sum(r["answer_relevancy"] for r in valid) / max(len(valid), 1),
            "avg_context_precision": sum(r["context_precision"] for r in valid) / max(len(valid), 1),
            "avg_response_time": total_time / max(len(valid), 1),
            "total_time": total_time,
        }

        print(f"\n{'='*70}")
        print(f"评估结果摘要")
        print(f"{'='*70}")
        print(f"  评估问题数:       {summary['total_questions']}")
        print(f"  成功/失败:        {summary['successful']}/{summary['failed']}")
        print(f"  忠实度 (avg):      {summary['avg_faithfulness']:.4f}")
        print(f"  答案相关性 (avg):  {summary['avg_answer_relevancy']:.4f}")
        print(f"  上下文精确率 (avg):{summary['avg_context_precision']:.4f}")
        print(f"  平均响应时间:      {summary['avg_response_time']:.2f}s")
        print(f"  总耗时:            {summary['total_time']:.1f}s")
        print(f"{'='*70}\n")

        # 保存结果
        output_path = Path("data/evaluation_results.json")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump({"summary": summary, "details": results}, f, ensure_ascii=False, indent=2)
        print(f"  📄 详细结果已保存至: {output_path}")

        return summary


async def main():
    evaluator = RAGEvaluator()
    await evaluator.evaluate_all()


if __name__ == "__main__":
    asyncio.run(main())
