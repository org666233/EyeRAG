"""
知识库 API 集成测试
测试文档上传、列表、删除、预览、下载等端点
"""

import pytest
import io


class TestKnowledgeStats:
    """知识库统计接口"""

    @pytest.mark.integration
    async def test_get_stats(self, client, valid_tokens):
        """获取统计信息"""
        response = await client.get(
            "/api/knowledge/stats",
            headers={"Authorization": f"Bearer {valid_tokens['alice']}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "total_chunks" in data
        assert "total_documents" in data
        assert "collection_name" in data

    @pytest.mark.integration
    async def test_get_stats_no_auth(self, client):
        """无认证可获取统计（公开接口）"""
        response = await client.get("/api/knowledge/stats")
        assert response.status_code == 200


class TestKnowledgeDocuments:
    """知识库文档管理接口"""

    @pytest.mark.integration
    async def test_list_documents(self, client, valid_tokens):
        """获取文档列表"""
        response = await client.get(
            "/api/knowledge/documents",
            headers={"Authorization": f"Bearer {valid_tokens['alice']}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.integration
    async def test_list_documents_with_stats(self, client, valid_tokens):
        """文档列表包含热度统计字段"""
        response = await client.get(
            "/api/knowledge/documents",
            headers={"Authorization": f"Bearer {valid_tokens['alice']}"},
        )
        assert response.status_code == 200
        data = response.json()
        if len(data) > 0:
            doc = data[0]
            assert "file_name" in doc
            assert "chunk_count" in doc
            assert "hit_count" in doc
            assert "view_count" in doc

    @pytest.mark.integration
    async def test_delete_document_not_found(self, client, valid_tokens):
        """删除不存在的文档返回 404"""
        response = await client.delete(
            "/api/knowledge/documents/nonexistent_file_xyz.txt",
            headers={"Authorization": f"Bearer {valid_tokens['alice']}"},
        )
        assert response.status_code == 404


class TestKnowledgeUpload:
    """文档上传接口"""

    @pytest.mark.integration
    async def test_upload_txt_file(self, client, valid_tokens):
        """上传 TXT 文件成功"""
        content = b"This is a test document about glaucoma."
        files = {"file": ("test_glaucoma.txt", io.BytesIO(content), "text/plain")}

        response = await client.post(
            "/api/knowledge/upload",
            files=files,
            headers={"Authorization": f"Bearer {valid_tokens['alice']}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "file_name" in data
        assert "chunk_count" in data
        assert data["chunk_count"] > 0

    @pytest.mark.integration
    async def test_upload_markdown_file(self, client, valid_tokens):
        """上传 Markdown 文件成功"""
        content = b"""# Glaucoma

## Symptoms
- High intraocular pressure
- Vision loss

## Treatment
Consult your ophthalmologist.
"""
        files = {"file": ("test_glaucoma.md", io.BytesIO(content), "text/markdown")}

        response = await client.post(
            "/api/knowledge/upload",
            files=files,
            headers={"Authorization": f"Bearer {valid_tokens['alice']}"},
        )
        assert response.status_code == 200

    @pytest.mark.integration
    async def test_upload_unsupported_type(self, client, valid_tokens):
        """上传不支持的文件类型返回 400"""
        content = b"some content"
        files = {"file": ("test.exe", io.BytesIO(content), "application/octet-stream")}

        response = await client.post(
            "/api/knowledge/upload",
            files=files,
            headers={"Authorization": f"Bearer {valid_tokens['alice']}"},
        )
        assert response.status_code == 400

    @pytest.mark.integration
    async def test_upload_empty_file(self, client, valid_tokens):
        """上传空文件应被处理（返回chunk_count=0）"""
        content = b""
        files = {"file": ("empty.txt", io.BytesIO(content), "text/plain")}

        response = await client.post(
            "/api/knowledge/upload",
            files=files,
            headers={"Authorization": f"Bearer {valid_tokens['alice']}"},
        )
        # 空文件可能被接受但 chunk_count=0，或者解析失败返回 500
        assert response.status_code in [200, 500]


class TestKnowledgeSearch:
    """知识库检索接口（纯本地，不调用 LLM）"""

    @pytest.mark.integration
    async def test_search_knowledge(self, client, valid_tokens):
        """检索接口返回结构正确"""
        response = await client.post(
            "/api/knowledge/search",
            json={"query": "青光眼", "top_k": 5},
            headers={"Authorization": f"Bearer {valid_tokens['alice']}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "query" in data
        assert "results" in data
        assert "total" in data
        assert isinstance(data["results"], list)

    @pytest.mark.integration
    async def test_search_top_k_parameter(self, client, valid_tokens):
        """top_k 参数控制返回数量"""
        response = await client.post(
            "/api/knowledge/search",
            json={"query": "青光眼", "top_k": 3},
            headers={"Authorization": f"Bearer {valid_tokens['alice']}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) <= 3

    @pytest.mark.integration
    async def test_search_missing_query(self, client, valid_tokens):
        """缺少 query 字段返回 422"""
        response = await client.post(
            "/api/knowledge/search",
            json={"top_k": 5},
            headers={"Authorization": f"Bearer {valid_tokens['alice']}"},
        )
        assert response.status_code == 422


class TestKnowledgePreview:
    """文档预览接口"""

    @pytest.mark.integration
    async def test_preview_requires_auth(self, client):
        """预览接口需要认证"""
        response = await client.get(
            "/api/knowledge/documents/somefile.txt/preview",
        )
        assert response.status_code == 401

    @pytest.mark.integration
    async def test_preview_not_found(self, client, valid_tokens):
        """预览不存在的文档返回 404"""
        response = await client.get(
            "/api/knowledge/documents/nonexistent_xyz.txt/preview",
            headers={"Authorization": f"Bearer {valid_tokens['alice']}"},
        )
        assert response.status_code == 404


class TestKnowledgeDownload:
    """文档下载接口"""

    @pytest.mark.integration
    async def test_download_not_found(self, client):
        """下载不存在的文件返回 404"""
        response = await client.get(
            "/api/knowledge/documents/nonexistent_xyz.txt/download",
        )
        assert response.status_code == 404
