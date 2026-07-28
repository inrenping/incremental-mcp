from sqlalchemy import select

from fastmcp.server.dependencies import get_http_headers

from app.auth import decode_token, get_user_id_from_payload
from app.db import SessionLocal
from app.models.user import User


def _current_user_id() -> str | None:
    """从当前请求的 Authorization header 中解析用户 ID（JWT sub 字段）。"""
    headers = get_http_headers(include_all=True)
    auth = headers.get("Authorization") or headers.get("authorization", "")
    if not auth.startswith("Bearer "):
        return None
    token = auth[7:]
    payload = decode_token(token)
    return get_user_id_from_payload(payload)


def query_user_profile() -> dict:
    """获取当前登录用户的基本信息（用户名、邮箱、会员状态等）。

    需要通过 Authorization: Bearer <JWT> 进行身份验证。
    """
    user_id = _current_user_id()
    if not user_id:
        return {"error": "无法识别当前用户，请检查 JWT"}

    with SessionLocal() as session:
        result = session.execute(select(User).where(User.id == int(user_id)))
        user = result.scalar_one_or_none()
        if not user:
            return {"message": "未找到该用户", "user_id": user_id}

        return {
            "id": user.id,
            "user_name": user.user_name,
            "user_email": user.user_email,
            "active": user.active,
            "vip": user.vip,
            "timezone": user.timezone,
            "created_at": user.created_at.isoformat() if user.created_at else None,
        }
