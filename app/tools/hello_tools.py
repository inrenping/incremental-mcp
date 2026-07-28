"""Hello world 示例工具，演示 MCP tool 的基本写法。"""

from sqlalchemy import select

from fastmcp.server.dependencies import get_http_headers

from app.auth import decode_token, get_user_id_from_payload
from app.db import AsyncSessionLocal
from app.models.user import User


def _current_user_name() -> str | None:
    """从当前请求的 Authorization header 中解析 JWT，获取用户 ID。"""
    headers = get_http_headers(include_all=True)
    auth = headers.get("Authorization") or headers.get("authorization", "")
    if not auth.startswith("Bearer "):
        return None
    token = auth[7:]
    payload = decode_token(token)
    return get_user_id_from_payload(payload)


async def say_hello() -> dict:
    """根据当前用户的 JWT token 获取用户名并打招呼。

    需要通过 Authorization: Bearer <JWT> 进行身份验证。
    """
    user_id = _current_user_name()
    if not user_id:
        return {"error": "无法识别当前用户，请检查 JWT"}

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.id == int(user_id)))
        user = result.scalar_one_or_none()
        if not user:
            return {"message": "未找到该用户", "user_id": user_id}

        return {
            "message": f"Hello, {user.user_name}!",
            "user_id": user.id,
            "user_name": user.user_name,
            "user_email": user.user_email,
        }


async def server_info() -> dict:
    """返回服务器基本信息。"""
    return {
        "service": "Incremental MCP Server",
        "version": "0.1.0",
        "description": "为 i.incremental.icu 提供的 MCP 服务",
    }
