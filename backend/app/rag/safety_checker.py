"""
医疗安全检查层
对生成答案进行内容安全审核，拦截诊断建议、用药剂量等敏感内容
"""

from __future__ import annotations
import re
from dataclasses import dataclass
from app.utils.logger import logger


@dataclass
class SafetyResult:
    safe: bool
    answer: str
    risks: list[str]


class MedicalSafetyChecker:
    """
    医疗安全检查器。

    检测以下风险类别：
    1. 直接诊断语句 —— 未经专业检查的诊断
    2. 用药剂量描述 —— 具体数字+药物单位
    3. 绝对化表述 —— 过度确定的医疗陈述
    4. 药物使用建议 —— 具体用药指导
    """

    # 具体药物名称列表（常见眼科用药）
    DRUG_PATTERNS = [
        r"(\d+(?:\.\d+)?)\s*(mg|milligram|毫克|克|g|ml|毫升|滴|单位)",
        r"(每天?|每日|每次?|一天)\s*\d+\s*(次|片|滴|mg|ml|毫升|毫克)",
        r"(服用|口服|滴入|滴用|注射)\s*[^\s。,，]{1,20}?\s*\d+",
        r"(遵医嘱|按说明书)\s*(服用|使用|剂量)",
    ]

    # 直接诊断句式
    DIAGNOSIS_PATTERNS = [
        r"你患有",
        r"可以确诊",
        r"确定是",
        r"必然是",
        r"一定是",
        r"你就是",
        r"属于.{0,6}（?:晚期|早期|中期）",
        r"(?:晚期|中期)\s*\w+",
    ]

    # 绝对化/过度确定性表述
    CERTAINTY_PATTERNS = [
        r"一定.{0,4}(?:会|能|能治好|痊愈)",
        r"肯定.{0,4}(?:会|能|治得好)",
        r"绝对.{0,4}(?:安全|有效|没问题)",
        r"百分百",
        r"100%\s*(?:安全|有效|治愈)",
        r"手术绝对安全",
        r"服药绝对安全",
        r"万无一失",
        r"包你治好",
        r"保证治好",
    ]

    # 需要立即就医的紧急情况（正向提醒，不是风险）
    EMERGENCY_KEYWORDS = [
        "急性", "急诊", "立即就医", "立刻去", "马上看医生",
        "紧急", "不要拖延", "不要耽搁",
    ]

    # 免责声明模板
    DISCLAIMER = (
        "\n\n---\n"
        "**⚠️ 医疗安全提示**：本回答仅供参考，不能替代专业眼科医生的诊断和治疗。\n"
        "如有视力急剧下降、眼部剧痛、急性眼压升高等紧急情况，"
        "请**立即前往医院眼科就诊**，切勿延误。\n"
        "任何用药方案请务必在专业医师指导下使用。"
    )

    def __init__(self):
        self._drug_re = [
            re.compile(p, re.IGNORECASE) for p in self.DRUG_PATTERNS
        ]
        self._diagnosis_re = [
            re.compile(p, re.IGNORECASE) for p in self.DIAGNOSIS_PATTERNS
        ]
        self._certainty_re = [
            re.compile(p, re.IGNORECASE) for p in self.CERTAINTY_PATTERNS
        ]
        self._emergency_re = re.compile(
            "|".join(k.replace(" ", r"\s*") for k in self.EMERGENCY_KEYWORDS),
            re.IGNORECASE
        )

    def check(self, answer: str, question: str = "") -> SafetyResult:
        """
        检查答案是否包含医疗安全风险内容。

        Args:
            answer: 待检查的答案文本
            question: 用户原始问题（用于判断是否为紧急情况）

        Returns:
            SafetyResult: 包含安全状态、过滤后答案和风险列表
        """
        risks = []
        full_text = answer + question

        # 1. 检查直接诊断句式
        for pattern in self._diagnosis_re:
            matches = pattern.findall(answer)
            if matches:
                risks.append(f"包含直接诊断表述：{'、'.join(str(m) for m in matches if m)}")

        # 2. 检查用药剂量描述
        for pattern_re in self._drug_re:
            matches = pattern_re.findall(answer)
            if matches:
                # 提取药物单位附近内容
                for m in matches:
                    if isinstance(m, tuple):
                        matched_text = "".join(str(x) for x in m if x).strip()
                    else:
                        matched_text = str(m)
                    if matched_text:
                        risks.append(f"包含用药剂量描述：{matched_text}")

        # 3. 检查绝对化表述
        for pattern_re in self._certainty_re:
            matches = pattern_re.findall(answer)
            if matches:
                risks.append(f"包含过度确定性表述：{matches[0]}")

        # 4. 特殊：手术/药物安全性绝对化
        if re.search(r"(?:手术|服药|用药).{0,20}(?:绝对|100%|一定|万无一失)", answer, re.IGNORECASE):
            risks.append("包含对治疗手段的绝对化安全陈述")

        # 如果发现风险，追加免责声明
        if risks:
            safe_answer = answer
            # 避免重复追加免责
            if self.DISCLAIMER.strip() not in safe_answer:
                safe_answer = safe_answer.rstrip() + self.DISCLAIMER
            logger.warning(f"医疗安全检查发现风险: {risks}")
            return SafetyResult(safe=False, answer=safe_answer, risks=risks)

        # 无风险：检查是否包含紧急情况关键词，如果是则追加积极提醒
        emergency_matches = self._emergency_re.findall(full_text)
        if emergency_matches:
            reminder = (
                "\n\n---\n"
                "**温馨提示**：如果出现剧烈眼痛、视力急剧下降、急性眼压升高等症状，"
                "请**立即前往医院眼科就诊**，不要延误。\n"
                "本系统仅提供健康科普，不能替代专业诊疗。"
            )
            if reminder.strip() not in answer:
                safe_answer = answer.rstrip() + reminder
                return SafetyResult(safe=True, answer=safe_answer, risks=[])

        return SafetyResult(safe=True, answer=answer, risks=[])


# 全局单例
_checker: MedicalSafetyChecker | None = None


def get_safety_checker() -> MedicalSafetyChecker:
    global _checker
    if _checker is None:
        _checker = MedicalSafetyChecker()
    return _checker
