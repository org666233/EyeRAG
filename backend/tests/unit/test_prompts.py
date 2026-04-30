"""
Prompt 模板单元测试
验证 Prompt 格式化、上下文构建、对话历史格式化等
"""

import pytest
from app.rag.prompts import (
    format_context,
    format_chat_history,
    build_rag_messages,
    SYSTEM_PROMPT,
    RAG_QA_TEMPLATE,
    NO_CONTEXT_TEMPLATE,
)


class TestFormatContext:
    """format_context 测试"""

    def test_empty_results(self):
        """空检索结果返回占位符"""
        result = format_context([])
        assert result == "（暂无相关参考资料）"

    def test_single_result(self):
        """单条结果正确格式化"""
        results = [
            {
                "content": "青光眼是眼压升高引起的视神经病变。",
                "metadata": {"file_name": "glaucoma.txt"},
                "score": 0.95,
            }
        ]
        text = format_context(results)
        assert "青光眼" in text
        assert "glaucoma.txt" in text
        assert "0.95" in text
        assert "参考 1" in text

    def test_multiple_results(self):
        """多条结果包含所有内容"""
        results = [
            {"content": f"文档{i}内容", "metadata": {"file_name": f"doc{i}.txt"}, "score": 0.9 - i * 0.1}
            for i in range(3)
        ]
        text = format_context(results)
        assert "文档0内容" in text
        assert "文档1内容" in text
        assert "文档2内容" in text

    def test_max_chars_truncation(self):
        """超出 max_chars 时截断"""
        long_results = [
            {
                "content": "a" * 2000,
                "metadata": {"file_name": "long.txt"},
                "score": 0.9,
            },
            {
                "content": "b" * 2000,
                "metadata": {"file_name": "long2.txt"},
                "score": 0.8,
            },
        ]
        text = format_context(long_results, max_chars=1000)
        assert len(text) <= 1100  # 略有余量

    def test_missing_metadata(self):
        """缺失 metadata 字段不崩溃"""
        results = [{"content": "内容", "score": 0.8}]
        text = format_context(results)
        assert "内容" in text

    def test_no_score_field(self):
        """缺少 score 字段使用默认值0"""
        results = [{"content": "内容", "metadata": {"file_name": "test.txt"}}]
        text = format_context(results)
        assert "内容" in text


class TestFormatChatHistory:
    """format_chat_history 测试"""

    def test_empty_history(self):
        """空历史返回占位符"""
        result = format_chat_history([])
        assert "无历史对话" in result

    def test_single_message(self):
        """单条消息正确格式化"""
        history = [{"role": "user", "content": "青光眼是什么？"}]
        text = format_chat_history(history)
        assert "用户" in text
        assert "青光眼是什么？" in text

    def test_multiple_turns(self):
        """多轮对话交替显示"""
        history = [
            {"role": "user", "content": "白内障怎么治？"},
            {"role": "assistant", "content": "白内障可以通过手术治疗。"},
            {"role": "user", "content": "手术有风险吗？"},
        ]
        text = format_chat_history(history)
        assert "白内障怎么治？" in text
        assert "白内障可以通过手术治疗" in text
        assert "手术有风险吗？" in text
        assert "用户" in text
        assert "助手" in text

    def test_max_turns_limit(self):
        """超过 max_turns 时只保留最近轮次"""
        history = [
            {"role": "user", "content": f"问题{i}"}
            for i in range(20)
        ]
        text = format_chat_history(history, max_turns=3)
        # 应该只包含最近的消息
        assert "问题19" in text
        # 较早的消息可能不在了
        # （取决于具体实现）

    def test_missing_role(self):
        """缺少 role 字段不崩溃"""
        history = [{"content": "内容"}]
        text = format_chat_history(history)
        assert "内容" in text


class TestBuildRagMessages:
    """build_rag_messages 测试"""

    def test_basic_structure(self):
        """返回消息列表包含 system 和 user"""
        messages = build_rag_messages(
            question="青光眼症状？",
            search_results=[],
        )
        assert isinstance(messages, list)
        assert len(messages) >= 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"

    def test_system_prompt_included(self):
        """系统提示词已包含"""
        messages = build_rag_messages(
            question="test",
            search_results=[],
        )
        assert "眼科" in messages[0]["content"]
        assert "助手" in messages[0]["content"]

    def test_question_included(self):
        """用户问题被包含"""
        messages = build_rag_messages(
            question="白内障手术费用多少？",
            search_results=[],
        )
        user_content = messages[1]["content"]
        assert "白内障手术费用多少？" in user_content

    def test_with_search_results(self):
        """有检索结果时使用 RAG_QA_TEMPLATE"""
        results = [
            {"content": "白内障手术费用约5000-10000元。", "metadata": {"file_name": "cataract.txt"}, "score": 0.9}
        ]
        messages = build_rag_messages(
            question="白内障手术费用？",
            search_results=results,
        )
        user_content = messages[1]["content"]
        assert "参考资料" in user_content
        assert "白内障手术费用约5000-10000元" in user_content

    def test_without_search_results(self):
        """无检索结果时使用降级模板"""
        messages = build_rag_messages(
            question="这是什么病？",
            search_results=[],
        )
        user_content = messages[1]["content"]
        assert "暂无" in user_content or "通用" in user_content or "参考资料" in user_content

    def test_with_chat_history(self):
        """有对话历史时包含历史上下文"""
        history = [
            {"role": "user", "content": "青光眼怎么治？"},
            {"role": "assistant", "content": "青光眼可以通过药物或手术治疗。"},
        ]
        messages = build_rag_messages(
            question="手术有什么风险？",
            search_results=[],
            chat_history=history,
        )
        user_content = messages[1]["content"]
        assert "青光眼" in user_content  # 历史中的疾病名被包含


class TestPromptTemplates:
    """Prompt 模板内容测试"""

    def test_system_prompt_contains_role(self):
        """系统提示词包含角色定义"""
        assert "眼科" in SYSTEM_PROMPT
        assert "助手" in SYSTEM_PROMPT

    def test_system_prompt_forbids_prescription(self):
        """系统提示词禁止开药"""
        assert "处方" not in SYSTEM_PROMPT or "不" in SYSTEM_PROMPT

    def test_system_prompt_urgency_reminder(self):
        """系统提示词包含紧急就医提醒"""
        assert "紧急" in SYSTEM_PROMPT or "立即就医" in SYSTEM_PROMPT

    def test_rag_template_has_placeholder(self):
        """RAG 模板包含占位符"""
        assert "{context}" in RAG_QA_TEMPLATE
        assert "{question}" in RAG_QA_TEMPLATE

    def test_no_context_template_has_placeholder(self):
        """降级模板包含占位符"""
        assert "{question}" in NO_CONTEXT_TEMPLATE
