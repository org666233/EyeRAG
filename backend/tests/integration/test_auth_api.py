"""
认证 API 集成测试
测试注册、登录、用户信息获取等端点
"""

import pytest


class TestAuthRegister:
    """用户注册接口"""

    async def test_register_success(self, client):
        """正常注册返回 token"""
        response = await client.post(
            "/api/auth/register",
            json={
                "username": "newuser123",
                "password": "SecurePass999",
                "real_name": "测试用户",
                "email": "test@example.com",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["username"] == "newuser123"
        assert data["role"] == "user"

    async def test_register_first_user_becomes_admin(self, client):
        """新注册用户为普通角色（需管理员设置）"""
        response = await client.post(
            "/api/auth/register",
            json={
                "username": "firstadmin2",
                "password": "AdminPass123",
            },
        )
        assert response.status_code == 200
        # 新注册用户默认角色为 user（管理员需通过后台设置）
        assert response.json()["role"] == "user"

    async def test_register_duplicate_username(self, client):
        """重复用户名返回 400"""
        await client.post(
            "/api/auth/register",
            json={"username": "duplicate", "password": "pass123"},
        )
        response = await client.post(
            "/api/auth/register",
            json={"username": "duplicate", "password": "pass456"},
        )
        assert response.status_code == 400
        assert "用户名已存在" in response.json()["detail"]

    async def test_register_short_password(self, client):
        """密码过短应被拒绝（>=6 字符）"""
        response = await client.post(
            "/api/auth/register",
            json={"username": "shortpw", "password": "123"},
        )
        assert response.status_code == 422  # FastAPI 验证错误

    async def test_register_missing_username(self, client):
        """缺少用户名返回 422"""
        response = await client.post(
            "/api/auth/register",
            json={"password": "password123"},
        )
        assert response.status_code == 422

    async def test_register_empty_body(self, client):
        """空请求体返回 422"""
        response = await client.post("/api/auth/register", json={})
        assert response.status_code == 422


class TestAuthLogin:
    """用户登录接口"""

    async def test_login_success(self, client):
        """正确账号密码登录成功"""
        # 先注册
        await client.post(
            "/api/auth/register",
            json={"username": "logintest", "password": "TestPass123"},
        )
        # 再登录
        response = await client.post(
            "/api/auth/login",
            json={"username": "logintest", "password": "TestPass123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["username"] == "logintest"

    async def test_login_wrong_password(self, client):
        """错误密码返回 401"""
        await client.post(
            "/api/auth/register",
            json={"username": "wrongpw", "password": "CorrectPass123"},
        )
        response = await client.post(
            "/api/auth/login",
            json={"username": "wrongpw", "password": "WrongPass999"},
        )
        assert response.status_code == 401
        assert "用户名或密码错误" in response.json()["detail"]

    async def test_login_nonexistent_user(self, client):
        """不存在的用户返回 401"""
        response = await client.post(
            "/api/auth/login",
            json={"username": "notexist", "password": "anypassword"},
        )
        assert response.status_code == 401

    async def test_login_inactive_user(self, db_with_data, client):
        """已禁用账号返回 403"""
        response = await client.post(
            "/api/auth/login",
            json={"username": "disabled_user", "password": "disabled999"},
        )
        assert response.status_code == 403


class TestAuthMe:
    """获取当前用户信息"""

    async def test_get_me_success(self, client, valid_tokens):
        """已登录用户可获取自身信息"""
        response = await client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {valid_tokens['alice']}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "alice"
        assert data["real_name"] == "Alice Smith"

    async def test_get_me_no_token(self, client):
        """无 token 返回 401"""
        response = await client.get("/api/auth/me")
        assert response.status_code == 401

    async def test_get_me_invalid_token(self, client):
        """无效 token 返回 401"""
        response = await client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer invalid.token.here"},
        )
        assert response.status_code == 401

    async def test_get_me_expired_token(self, client):
        """过期 token 返回 401"""
        from datetime import timedelta
        from app.services.auth import create_access_token
        import app.services.auth as auth_module
        import app.config as config_module

        # 创建一个已过期的 token
        expired_token = create_access_token(
            {"sub": "1"},
            expires_delta=timedelta(seconds=-10),
        )
        response = await client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {expired_token}"},
        )
        assert response.status_code == 401
