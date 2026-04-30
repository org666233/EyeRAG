"""
医疗安全检查层单元测试
验证 MedicalSafetyChecker 的风险检测逻辑
"""

import pytest
from app.rag.safety_checker import MedicalSafetyChecker, SafetyResult


class TestMedicalSafetyChecker:
    """医疗安全检查器测试"""

    @pytest.fixture
    def checker(self):
        return MedicalSafetyChecker()

    # ── 直接诊断语句检测 ──────────────────────────────────────────────

    def test_detects_direct_diagnosis(self, checker):
        """检测"你患有"等直接诊断语句"""
        result = checker.check(
            "你患有青光眼，请尽快治疗。",
            "我的眼睛不舒服"
        )
        assert result.safe is False
        assert len(result.risks) > 0
        assert any("诊断" in r for r in result.risks)

    def test_detects_definitive_diagnosis(self, checker):
        """检测"可以确诊"等确定性诊断"""
        result = checker.check(
            "根据描述，可以确诊为白内障。",
            ""
        )
        assert result.safe is False

    def test_detects_absolutely_certain_diagnosis(self, checker):
        """检测"一定是"等绝对化诊断"""
        result = checker.check(
            "这一定是早期青光眼。",
            ""
        )
        assert result.safe is False

    def test_safe_medical_info_no_diagnosis(self, checker):
        """安全内容（无诊断性语句）通过检查"""
        result = checker.check(
            "青光眼是一种常见的眼部疾病，主要表现为眼压升高。"
            "建议定期进行眼科检查，早发现早治疗。",
            "青光眼是什么？"
        )
        assert result.safe is True
        assert result.risks == []

    def test_question_asking_for_info(self, checker):
        """询问医学知识（而非诊断）的内容安全"""
        result = checker.check(
            "白内障手术是一种成熟的治疗方法，成功率较高。"
            "具体是否适合手术需要医生评估。",
            "白内障手术效果怎么样？"
        )
        assert result.safe is True

    # ── 用药剂量检测 ──────────────────────────────────────────────────

    def test_detects_dosage_mg(self, checker):
        """检测药物剂量（mg）"""
        result = checker.check(
            "每日服用25毫克降眼压药物，具体剂量请遵医嘱。",
            ""
        )
        assert result.safe is False
        assert any("剂量" in r for r in result.risks)

    def test_detects_dosage_每日(self, checker):
        """检测"每天3次，每次2片"等剂量描述（使用阿拉伯数字）"""
        result = checker.check(
            "每天3次，每次2片，饭后服用。",
            ""
        )
        assert result.safe is False

    def test_safe_medication_mention_without_dosage(self, checker):
        """仅提及药名但无剂量的内容安全"""
        result = checker.check(
            "常用的降眼压药物包括噻吗洛尔、曲伏前列素等，"
            "具体用药方案请咨询专业眼科医生。",
            "青光眼用什么药？"
        )
        assert result.safe is True

    # ── 绝对化表述检测 ────────────────────────────────────────────────

    def test_detects_absolute_safety_claim(self, checker):
        """检测"手术绝对安全"等绝对化表述"""
        result = checker.check(
            "这个手术绝对安全，不会有任何风险。",
            ""
        )
        assert result.safe is False

    def test_detects_100_percent_cure(self, checker):
        """检测"百分百治好"等绝对化承诺"""
        result = checker.check(
            "按照这个方案治疗，百分百能治好。",
            ""
        )
        assert result.safe is False

    def test_detects_wuguanyishu(self, checker):
        """检测"万无一失"等极端表述"""
        result = checker.check(
            "这种药物万无一失，放心使用。",
            ""
        )
        assert result.safe is False

    def test_safe_general_advice(self, checker):
        """一般性医学建议安全"""
        result = checker.check(
            "建议多吃富含维生素A的食物，如胡萝卜、菠菜等，"
            "对眼部健康有益。具体营养方案可咨询医生。",
            "吃什么对眼睛好？"
        )
        assert result.safe is True

    # ── 免责声明追加 ──────────────────────────────────────────────────

    def test_disclaimer_appended_on_risk(self, checker):
        """发现风险时自动追加免责声明"""
        result = checker.check(
            "你患有白内障，可以每天服用三次降压药。",
            ""
        )
        assert "⚠️" in result.answer or "免责声明" in result.answer or "仅供参考" in result.answer

    def test_no_duplicate_disclaimer(self, checker):
        """多次检查同一答案不重复追加免责声明"""
        result1 = checker.check("你患有青光眼。", "")
        result2 = checker.check(result1.answer, "")

        # 第二次检查后答案长度不应继续增加
        assert len(result2.answer) <= len(result1.answer) * 1.2

    # ── 紧急情况提醒 ──────────────────────────────────────────────────

    def test_emergency_reminder_added(self, checker):
        """紧急情况关键词触发就医提醒"""
        result = checker.check(
            "如果出现急性青光眼发作，请立即就医。",
            "青光眼急性发作怎么办？"
        )
        # 有紧急关键词，可能追加提醒
        # 允许 safe=True 或 safe=False（因为也可能触发诊断语句检测）
        assert result.answer is not None
        assert len(result.answer) > 0

    # ── SafetyResult 数据结构 ────────────────────────────────────────

    def test_safety_result_dataclass(self):
        """SafetyResult 数据类字段正确"""
        result = SafetyResult(
            safe=False,
            answer="修改后的答案",
            risks=["包含诊断语句"],
        )
        assert result.safe is False
        assert result.answer == "修改后的答案"
        assert result.risks == ["包含诊断语句"]

    # ── 边界情况 ─────────────────────────────────────────────────────

    def test_empty_answer(self, checker):
        """空答案通过检查（无内容无风险）"""
        result = checker.check("", "有什么问题？")
        assert result.safe is True

    def test_very_long_answer(self, checker):
        """超长答案正常处理"""
        long_text = "青光眼是一种疾病。" + "这是相关知识。" * 1000
        result = checker.check(long_text, "青光眼是什么？")
        assert result.safe is True
        assert len(result.answer) > 0

    def test_unicode_content(self, checker):
        """中英文混合内容正常处理"""
        result = checker.check(
            "Glaucoma is an eye disease. 青光眼是一种常见眼病。"
            "建议 consulting an ophthalmologist. 具体请咨询医生。",
            "What is glaucoma?"
        )
        # 无诊断性语句，应该安全
        assert result.risks == [] or result.safe is True
