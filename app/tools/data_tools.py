from sqlalchemy import func, select

from fastmcp.server.dependencies import get_http_headers

from app.auth import decode_token, get_user_id_from_payload
from app.db import AsyncSessionLocal
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


async def query_user_profile() -> dict:
    """获取当前登录用户的基本信息（用户名、邮箱、会员状态等）。

    需要通过 Authorization: Bearer <JWT> 进行身份验证。
    """
    user_id = _current_user_id()
    if not user_id:
        return {"error": "无法识别当前用户，请检查 JWT"}

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.id == int(user_id)))
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


async def query_active_users() -> list[dict]:
    """列出所有已激活的用户（仅返回 id、用户名、邮箱、会员状态）。

    需要通过 Authorization: Bearer <JWT> 进行身份验证。
    """
    user_id = _current_user_id()
    if not user_id:
        return [{"error": "请提供有效的 JWT"}]

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.active.is_(True)).order_by(User.id)
        )
        rows = result.scalars().all()
        return [
            {
                "id": u.id,
                "user_name": u.user_name,
                "user_email": u.user_email,
                "vip": u.vip,
            }
            for u in rows
        ]


async def query_db_stats() -> dict:
    """查询数据库统计信息（用户总数、激活用户数、VIP 用户数）。

    需要通过 Authorization: Bearer <JWT> 进行身份验证。
    """
    user_id = _current_user_id()
    if not user_id:
        return {"error": "请提供有效的 JWT"}

    async with AsyncSessionLocal() as session:
        total = await session.scalar(select(func.count(User.id)).select_from(User))
        active = await session.scalar(
            select(func.count(User.id)).select_from(User).where(User.active.is_(True))
        )
        vip = await session.scalar(
            select(func.count(User.id)).select_from(User).where(User.vip.is_(True))
        )
        return {
            "total_users": total,
            "active_users": active,
            "vip_users": vip,
        }
