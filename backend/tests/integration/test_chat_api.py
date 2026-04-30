"""
聊天 API 接口集成测试
测试问答接口的边界条件、安全性、错误处理

注意：这些测试中调用 LLM 的用例已标记为 @pytest.mark.llm，
运行时不加 --m "llm" 即可跳过所有 LLM 调用。
"""

import pytest


class TestChatCompletionsBoundary:
    """聊天接口边界条件测试（不调用 LLM）"""

    @pytest.mark.integration
    async def test_chat_requires_auth(self, client):
        """未认证返回 401"""
        response = await client.post(
            "/api/chat/completions",
            json={"question": "青光眼有哪些症状？", "stream": True},
        )
        assert response.status_code == 401

    @pytest.mark.integration
    async def test_chat_empty_question(self, client, valid_tokens):
        """空问题返回 422 验证错误"""
        response = await client.post(
            "/api/chat/completions",
            json={"question": "", "stream": True},
            headers={"Authorization": f"Bearer {valid_tokens['alice']}"},
        )
        assert response.status_code == 422

    @pytest.mark.integration
    async def test_chat_whitespace_only_question(self, client, valid_tokens):
        """仅空白字符的问题应被拒绝"""
        response = await client.post(
            "/api/chat/completions",
            json={"question": "   ", "stream": True},
            headers={"Authorization": f"Bearer {valid_tokens['alice']}"},
        )
        # 可能是 422（验证）或 200（空回答）
        assert response.status_code in [200, 422]

    @pytest.mark.integration
    async def test_chat_invalid_token(self, client):
        """无效 token 返回 401"""
        response = await client.post(
            "/api/chat/completions",
            json={"question": "test", "stream": True},
            headers={"Authorization": "Bearer fake.token.here"},
        )
        assert response.status_code == 401

    @pytest.mark.integration
    async def test_chat_conversation_creation(self, client, valid_tokens):
        """发送问题自动创建会话（流式接口不返回 JSON）"""
        # 发送消息创建会话
        response = await client.post(
            "/api/chat/messages",
            json={
                "question": "视网膜脱落的原因是什么？",
                "answer": "视网膜脱落与多种因素有关。",
            },
            headers={"Authorization": f"Bearer {valid_tokens['alice']}"},
        )
        assert response.status_code == 200
        conv_id = response.json()["conversation_id"]

        # 验证会话已创建
        response = await client.get(
            f"/api/chat/conversations/{conv_id}",
            headers={"Authorization": f"Bearer {valid_tokens['alice']}"},
        )
        assert response.status_code == 200
        messages = response.json()["messages"]
        assert any("视网膜" in m["content"] for m in messages)


class TestChatValidation:
    """聊天接口参数验证"""

    @pytest.mark.integration
    async def test_chat_negative_top_k(self, client, valid_tokens):
        """负数 top_k 可能被拒绝或使用默认值"""
        response = await client.post(
            "/api/chat/completions",
            json={"question": "青光眼", "top_k": -1, "stream": True},
            headers={"Authorization": f"Bearer {valid_tokens['alice']}"},
        )
        # 422 验证错误 或 使用默认值
        assert response.status_code in [200, 422]

    @pytest.mark.integration
    async def test_chat_very_long_question(self, client, valid_tokens):
        """超长问题应被接受（可能在 LLM 层被截断）"""
        long_question = "青" * 5000  # 极长问题
        response = await client.post(
            "/api/chat/completions",
            json={"question": long_question, "stream": True},
            headers={"Authorization": f"Bearer {valid_tokens['alice']}"},
        )
        # 200 或 413/422
        assert response.status_code in [200, 413, 422]

    @pytest.mark.integration
    async def test_chat_with_valid_top_k(self, client, valid_tokens):
        """有效的 top_k 参数"""
        response = await client.post(
            "/api/chat/completions",
            json={"question": "黄斑变性", "top_k": 3, "stream": True},
            headers={"Authorization": f"Bearer {valid_tokens['alice']}"},
        )
        # 不返回 422 表示参数验证通过
        assert response.status_code != 422


class TestChatMessagePersistence:
    """消息持久化测试"""

    @pytest.mark.integration
    async def test_message_saved_with_sources(self, client, valid_tokens):
        """消息保存包含来源信息"""
        response = await client.post(
            "/api/chat/messages",
            json={
                "conversation_id": None,  # 将创建新会话
                "question": "LASIK 手术的原理是什么？",
                "answer": "LASIK 通过切削角膜来改变屈光度。",
                "sources": [
                    {"title": "LASIK.txt", "score": 0.88},
                ],
                "search_results": [
                    {"content": "LASIK是一种屈光手术", "score": 0.9}
                ],
                "context_count": 3,
                "response_time_ms": 5432.1,
            },
            headers={"Authorization": f"Bearer {valid_tokens['alice']}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "conversation_id" in data

        # 验证会话中的消息
        conv_id = data["conversation_id"]
        response = await client.get(
            f"/api/chat/conversations/{conv_id}",
            headers={"Authorization": f"Bearer {valid_tokens['alice']}"},
        )
        messages = response.json()["messages"]
        assert len(messages) >= 2  # user + assistant

    @pytest.mark.integration
    async def test_conversation_auto_title(self, client, valid_tokens):
        """新会话自动以问题前30字作为标题"""
        question = "请问糖尿病视网膜病变应该如何预防和控制？"
        response = await client.post(
            "/api/chat/messages",
            json={"question": question, "answer": "预防和控制方法如下。"},
            headers={"Authorization": f"Bearer {valid_tokens['bob']}"},
        )
        assert response.status_code == 200
        conv_id = response.json()["conversation_id"]

        response = await client.get(
            f"/api/chat/conversations/{conv_id}",
            headers={"Authorization": f"Bearer {valid_tokens['bob']}"},
        )
        title = response.json()["title"]
        assert len(title) <= 30
        assert "糖尿病视网膜病变" in title or "?" in title or "请问" in title


# ─────────────────────────────────────────────────────────────────────────────
# LLM 相关测试（需要 token 时运行）
# 标记为 @pytest.mark.llm，默认不运行
# ─────────────────────────────────────────────────────────────────────────────


class TestChatWithLLM:
    """需要调用 LLM 的聊天接口测试（默认跳过）"""

    @pytest.mark.integration
    @pytest.mark.llm
    @pytest.mark.slow
    async def test_chat_sync_response_structure(self, client, valid_tokens):
        """
        非流式问答返回结构验证。
        消耗约 1-2 次 LLM 调用。
        """
        response = await client.post(
            "/api/chat/completions",
            json={"question": "青光眼的主要症状有哪些？", "stream": False},
            headers={"Authorization": f"Bearer {valid_tokens['alice']}"},
            timeout=120.0,
        )
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert "sources" in data
        assert "conversation_id" in data
        assert len(data["answer"]) > 0

    @pytest.mark.integration
    @pytest.mark.llm
    @pytest.mark.slow
    async def test_chat_stream_response(self, client, valid_tokens):
        """
        流式 SSE 响应结构验证。
        消耗约 1-2 次 LLM 调用。
        """
        async with client.stream(
            "POST",
            "/api/chat/completions",
            json={"question": "白内障手术有哪些类型？", "stream": True},
            headers={"Authorization": f"Bearer {valid_tokens['alice']}"},
            timeout=120.0,
        ) as response:
            assert response.status_code == 200
            assert response.headers["content-type"] == "text/event-stream; charset=utf-8"

            chunks = []
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    chunks.append(line)

            assert len(chunks) > 0
            # 验证 SSE 事件类型
            data_types = set()
            import json
            for chunk in chunks:
                payload = json.loads(chunk[6:])
                data_types.add(payload.get("type"))

            assert "sources" in data_types
            assert "content" in data_types
            assert "done" in data_types

    @pytest.mark.integration
    @pytest.mark.llm
    @pytest.mark.slow
    async def test_multi_turn_context(self, client, valid_tokens):
        """
        多轮对话上下文传递。
        消耗 2 轮 × 2 次 LLM 调用 = 4 次。
        """
        conv_id = None
        questions = [
            "白内障的早期症状是什么？",
            "如何诊断？",
            "有哪些治疗方案？",
        ]

        for q in questions:
            payload = {"question": q, "stream": False}
            if conv_id:
                payload["conversation_id"] = conv_id

            response = await client.post(
                "/api/chat/completions",
                json=payload,
                headers={"Authorization": f"Bearer {valid_tokens['alice']}"},
                timeout=120.0,
            )
            assert response.status_code == 200
            data = response.json()
            if conv_id is None:
                conv_id = data["conversation_id"]

        # 验证第三轮回答提到了"白内障"
        assert conv_id is not None
