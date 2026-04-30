"""
认证服务单元测试
验证密码哈希、JWT 编码/解码、用户认证逻辑
"""

import pytest
import time


class TestPasswordHashing:
    """密码哈希与校验"""

    def test_hash_password_returns_hash(self):
        """哈希后的密码应该是非明文的字符串"""
        from app.services.auth import hash_password

        hashed = hash_password("mySecretPassword123!")
        assert hashed != "mySecretPassword123!"
        assert len(hashed) > 20
        assert "$" in hashed  # bcrypt 格式包含 $

    def test_hash_password_different_each_time(self):
        """相同密码每次哈希结果不同（bcrypt 使用随机 salt）"""
        from app.services.auth import hash_password

        h1 = hash_password("samePassword")
        h2 = hash_password("samePassword")
        assert h1 != h2

    def test_verify_password_correct(self):
        """正确密码通过验证"""
        from app.services.auth import hash_password, verify_password

        password = "MySecurePassword999"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """错误密码拒绝验证"""
        from app.services.auth import hash_password, verify_password

        hashed = hash_password("correctPassword")
        assert verify_password("wrongPassword", hashed) is False

    def test_verify_password_empty(self):
        """空密码应拒绝"""
        from app.services.auth import hash_password, verify_password

        hashed = hash_password("realPassword")
        assert verify_password("", hashed) is False

    def test_hash_unicode_password(self):
        """Unicode 密码应正常处理"""
        from app.services.auth import hash_password, verify_password

        password = "我的密码🔐Password123"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True


class TestJWT:
    """JWT Token 生成与验证"""

    def test_create_access_token(self):
        """生成 JWT token"""
        from app.services.auth import create_access_token

        token = create_access_token({"sub": "123", "role": "user"})
        assert isinstance(token, str)
        assert len(token) > 50
        # JWT 由三部分组成，用 . 分隔
        assert token.count(".") == 2

    def test_decode_token_valid(self):
        """解码有效的 token"""
        from app.services.auth import create_access_token, decode_token

        data = {"sub": "456", "role": "admin"}
        token = create_access_token(data)
        payload = decode_token(token)

        assert payload["sub"] == "456"
        assert payload["role"] == "admin"
        assert "exp" in payload  # 包含过期时间

    def test_decode_token_invalid(self):
        """无效 token 抛出异常"""
        from app.services.auth import decode_token
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            decode_token("invalid.token.here")
        assert exc_info.value.status_code == 401

    def test_decode_token_tampered(self):
        """篡改后的 token 拒绝解析"""
        from app.services.auth import create_access_token, decode_token
        from fastapi import HTTPException

        token = create_access_token({"sub": "789"})
        # 篡改 payload 部分（第二位）
        parts = token.split(".")
        tampered = parts[0] + "X" + "." + parts[1] + "." + parts[2]

        with pytest.raises(HTTPException) as exc_info:
            decode_token(tampered)
        assert exc_info.value.status_code == 401

    def test_token_expiry(self):
        """已过期的 token 拒绝"""
        from app.services.auth import create_access_token, decode_token
        from fastapi import HTTPException
        from datetime import timedelta

        # 创建一个 0 秒后过期的 token（即已过期）
        token = create_access_token(
            {"sub": "expired_user"},
            expires_delta=timedelta(seconds=-1),
        )

        with pytest.raises(HTTPException) as exc_info:
            decode_token(token)
        assert exc_info.value.status_code == 401

    def test_token_missing_sub(self):
        """token payload 中缺少 sub 字段"""
        from app.services.auth import create_access_token, decode_token
        from fastapi import HTTPException

        # 手动构造没有 sub 的 payload
        import base64, json
        payload = base64.urlsafe_b64encode(
            json.dumps({"role": "user", "exp": 9999999999}).encode()
        ).decode().rstrip("=")
        header = base64.urlsafe_b64encode(
            json.dumps({"alg": "HS256", "typ": "JWT"}).encode()
        ).decode().rstrip("=")
        fake_token = f"{header}.{payload}.fake_signature"

        with pytest.raises(HTTPException) as exc_info:
            decode_token(fake_token)
        assert exc_info.value.status_code == 401
