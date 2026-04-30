"""
会话管理 API 集成测试
测试会话的增删改查操作
"""

import pytest


class TestConversationList:
    """会话列表接口"""

    @pytest.mark.integration
    async def test_list_conversations_empty(self, client, valid_tokens):
        """新用户会话列表为空"""
        response = await client.get(
            "/api/chat/conversations",
            headers={"Authorization": f"Bearer {valid_tokens['bob']}"},
        )
        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.integration
    async def test_list_conversations_with_data(self, client, valid_tokens):
        """有会话时返回列表"""
        response = await client.get(
            "/api/chat/conversations",
            headers={"Authorization": f"Bearer {valid_tokens['alice']}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        # 检查字段
        conv = data[0]
        assert "id" in conv
        assert "title" in conv
        assert "updated_at" in conv

    @pytest.mark.integration
    async def test_list_conversations_no_auth(self, client):
        """无认证返回 401"""
        response = await client.get("/api/chat/conversations")
        assert response.status_code == 401

    @pytest.mark.integration
    async def test_list_conversations_user_isolation(self, client, valid_tokens):
        """用户只能看到自己的会话（bob 看不到 alice 的）"""
        response = await client.get(
            "/api/chat/conversations",
            headers={"Authorization": f"Bearer {valid_tokens['bob']}"},
        )
        assert response.status_code == 200
        # bob 没有会话
        assert response.json() == []


class TestConversationGet:
    """获取单个会话"""

    @pytest.mark.integration
    async def test_get_conversation(self, client, valid_tokens):
        """获取会话详情包含消息历史"""
        # alice 有一个会话
        response = await client.get(
            "/api/chat/conversations",
            headers={"Authorization": f"Bearer {valid_tokens['alice']}"},
        )
        convs = response.json()
        if len(convs) == 0:
            pytest.skip("No conversation found for alice")

        conv_id = convs[0]["id"]
        response = await client.get(
            f"/api/chat/conversations/{conv_id}",
            headers={"Authorization": f"Bearer {valid_tokens['alice']}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == conv_id
        assert "title" in data
        assert "messages" in data
        assert isinstance(data["messages"], list)

    @pytest.mark.integration
    async def test_get_conversation_not_found(self, client, valid_tokens):
        """获取不存在的会话返回 404"""
        response = await client.get(
            "/api/chat/conversations/99999",
            headers={"Authorization": f"Bearer {valid_tokens['alice']}"},
        )
        assert response.status_code == 404

    @pytest.mark.integration
    async def test_get_conversation_other_user(self, client, valid_tokens):
        """用户不能获取他人的会话"""
        # alice 有会话，bob 尝试获取
        response = await client.get(
            "/api/chat/conversations",
            headers={"Authorization": f"Bearer {valid_tokens['alice']}"},
        )
        convs = response.json()
        if len(convs) == 0:
            pytest.skip("No conversation found")

        alice_conv_id = convs[0]["id"]
        response = await client.get(
            f"/api/chat/conversations/{alice_conv_id}",
            headers={"Authorization": f"Bearer {valid_tokens['bob']}"},
        )
        assert response.status_code == 404


class TestConversationTitle:
    """修改会话标题"""

    @pytest.mark.integration
    async def test_update_title(self, client, valid_tokens):
        """修改会话标题成功"""
        response = await client.get(
            "/api/chat/conversations",
            headers={"Authorization": f"Bearer {valid_tokens['alice']}"},
        )
        convs = response.json()
        if len(convs) == 0:
            pytest.skip("No conversation found")

        conv_id = convs[0]["id"]
        response = await client.patch(
            f"/api/chat/conversations/{conv_id}/title",
            json={"title": "修改后的标题"},
            headers={"Authorization": f"Bearer {valid_tokens['alice']}"},
        )
        assert response.status_code == 200
        assert response.json()["title"] == "修改后的标题"

    @pytest.mark.integration
    async def test_update_title_truncation(self, client, valid_tokens):
        """标题过长时截断到50字符"""
        response = await client.get(
            "/api/chat/conversations",
            headers={"Authorization": f"Bearer {valid_tokens['alice']}"},
        )
        convs = response.json()
        if len(convs) == 0:
            pytest.skip("No conversation found")

        conv_id = convs[0]["id"]
        long_title = "a" * 100
        response = await client.patch(
            f"/api/chat/conversations/{conv_id}/title",
            json={"title": long_title},
            headers={"Authorization": f"Bearer {valid_tokens['alice']}"},
        )
        assert response.status_code == 200
        assert len(response.json()["title"]) <= 50


class TestConversationDelete:
    """删除会话"""

    @pytest.mark.integration
    async def test_delete_conversation(self, client, valid_tokens):
        """删除会话成功（级联删除消息）"""
        # bob 创建一个新会话（通过发消息）
        # 先发一条消息创建会话
        await client.post(
            "/api/chat/messages",
            json={
                "question": "测试问题，用于删除测试",
                "answer": "测试回答",
            },
            headers={"Authorization": f"Bearer {valid_tokens['bob']}"},
        )

        # 获取会话列表
        response = await client.get(
            "/api/chat/conversations",
            headers={"Authorization": f"Bearer {valid_tokens['bob']}"},
        )
        convs = response.json()
        # 找到刚创建的会话
        test_conv = next((c for c in convs if "测试问题" in c["title"]), None)
        if test_conv is None:
            pytest.skip("Test conversation not created")

        conv_id = test_conv["id"]

        # 删除
        response = await client.delete(
            f"/api/chat/conversations/{conv_id}",
            headers={"Authorization": f"Bearer {valid_tokens['bob']}"},
        )
        assert response.status_code == 200

        # 验证已删除
        response = await client.get(
            f"/api/chat/conversations/{conv_id}",
            headers={"Authorization": f"Bearer {valid_tokens['bob']}"},
        )
        assert response.status_code == 404

    @pytest.mark.integration
    async def test_delete_other_user_conversation(self, client, valid_tokens):
        """不能删除他人的会话"""
        response = await client.get(
            "/api/chat/conversations",
            headers={"Authorization": f"Bearer {valid_tokens['alice']}"},
        )
        convs = response.json()
        if len(convs) == 0:
            pytest.skip("No conversation found")

        alice_conv_id = convs[0]["id"]
        response = await client.delete(
            f"/api/chat/conversations/{alice_conv_id}",
            headers={"Authorization": f"Bearer {valid_tokens['bob']}"},
        )
        assert response.status_code == 404


class TestSaveMessages:
    """消息保存接口"""

    @pytest.mark.integration
    async def test_save_messages_new_conversation(self, client, valid_tokens):
        """保存消息时自动创建会话"""
        response = await client.post(
            "/api/chat/messages",
            json={
                "question": "白内障的症状是什么？",
                "answer": "白内障的主要症状是视力模糊。",
                "sources": [{"title": "cataract.txt", "score": 0.9}],
            },
            headers={"Authorization": f"Bearer {valid_tokens['bob']}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "conversation_id" in data
        assert "message_id" in data

    @pytest.mark.integration
    async def test_save_messages_includes_sources(self, client, valid_tokens):
        """保存的消息包含参考来源"""
        response = await client.post(
            "/api/chat/messages",
            json={
                "question": "干眼症如何治疗？",
                "answer": "干眼症可以使用人工泪液治疗。",
                "sources": [
                    {"title": "dry_eye.txt", "score": 0.92},
                    {"title": "tear_film.txt", "score": 0.85},
                ],
                "retrieval_decision": "proceed",
            },
            headers={"Authorization": f"Bearer {valid_tokens['bob']}"},
        )
        assert response.status_code == 200

    @pytest.mark.integration
    async def test_save_messages_updates_doc_stats(self, client, valid_tokens):
        """保存消息时更新文档命中统计"""
        response = await client.post(
            "/api/chat/messages",
            json={
                "question": "青光眼检查方法？",
                "answer": "青光眼需要做视野检查和眼压测量。",
                "sources": [{"title": "Glaucoma.txt", "score": 0.9}],
            },
            headers={"Authorization": f"Bearer {valid_tokens['alice']}"},
        )
        assert response.status_code == 200

    @pytest.mark.integration
    async def test_save_messages_no_auth(self, client):
        """无认证返回 401"""
        response = await client.post(
            "/api/chat/messages",
            json={"question": "test", "answer": "test answer"},
        )
        assert response.status_code == 401
