"""本地冒烟测试，验证 FastAPI 应用结构及 JWT 中间件逻辑。"""

import jwt

from app.config import settings
from app.main import app
from app.auth import decode_token, get_user_id_from_payload


def test_app_routes_registered():
    """验证 FastAPI app 已加载且必要路由已注册。"""
    assert app.title == "Incremental MCP Server"
    routes = {r.path for r in app.routes}
    assert "/" in routes, "缺少根路由"
    assert "/health" in routes, "缺少健康检查路由"


def test_mcp_app_registered():
    """验证 MCP 子应用已挂载。"""
    from app.mcp_server import mcp_app, mcp
    assert mcp.name == "Incremental MCP Server"
    assert mcp_app is not None


def test_jwt_decode_valid():
    """验证 token 编解码正常。"""
    payload = {"sub": "user-123", "exp": 9999999999}
    token = jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)
    decoded = decode_token(token)
    assert decoded["sub"] == "user-123"


def test_jwt_decode_invalid():
    """验证无效 token 被拒绝。"""
    try:
        decode_token("invalid-token")
    except ValueError as e:
        assert "Invalid" in str(e)
    else:
        assert False, "应抛出 ValueError"


def test_get_user_id():
    """验证从 payload 提取 user_id。"""
    assert get_user_id_from_payload({"sub": "123"}) == "123"
    assert get_user_id_from_payload({"user_id": "456"}) == "456"
    assert get_user_id_from_payload({"id": "789"}) == "789"
    assert get_user_id_from_payload({}) is None


if __name__ == "__main__":
    test_app_routes_registered()
    test_mcp_app_registered()
    test_jwt_decode_valid()
    test_jwt_decode_invalid()
    test_get_user_id()
    print("all smoke tests passed")
