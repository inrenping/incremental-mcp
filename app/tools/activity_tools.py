"""跑步数据相关的 MCP 工具：获取最新跑步记录与历史跑步记录。"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select

from fastmcp.server.dependencies import get_http_headers

from app.auth import decode_token, get_user_id_from_payload
from app.db import SessionLocal
from app.models.main_activity import MainActivity

# 与 blunt-serv 后端一致：跑步相关的运动类型（key 与 name 都可能出现在 sport_type_raw 中）
RUNNING_TYPES = [
    "running",
    "treadmill_running",
    "trail_running",
    "track_running",
    "indoor_running",
    "100",
    "101",
    "102",
    "103",
]


def _current_user_id() -> str | None:
    """从当前请求的 Authorization header 中解析用户 ID（JWT sub 字段）。"""
    headers = get_http_headers(include_all=True)
    auth = headers.get("Authorization") or headers.get("authorization", "")
    if not auth.startswith("Bearer "):
        return None
    token = auth[7:]
    payload = decode_token(token)
    return get_user_id_from_payload(payload)


def _activity_to_dict(activity: MainActivity) -> dict:
    """将 ORM 对象转为可 JSON 序列化的 dict（时间转 ISO 格式、Decimal 转 float）。"""

    def _fmt(value):
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, Decimal):
            return float(value)
        return value

    return {
        col.name: _fmt(getattr(activity, col.name))
        for col in activity.__table__.columns
    }


def get_latest_run() -> dict:
    """获取当前用户最近一次跑步记录。

    返回最新一条跑步活动的完整数据（距离、时长、心率、配速、爬升等）。
    需要通过 Authorization: Bearer <JWT> 进行身份验证。
    """
    user_id = _current_user_id()
    if not user_id:
        return {"error": "无法识别当前用户，请检查 JWT"}

    with SessionLocal() as session:
        result = session.execute(
            select(MainActivity)
            .where(
                MainActivity.user_id == int(user_id),
                MainActivity.sport_type_raw.in_(RUNNING_TYPES),
            )
            .order_by(MainActivity.start_time_local.desc())
            .limit(1)
        )
        activity = result.scalar_one_or_none()
        if not activity:
            return {"status": "success", "data": None, "message": "未找到跑步记录"}

        return {"status": "success", "data": _activity_to_dict(activity)}


def get_run_history(
    limit: int = 10,
    offset: int = 0,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict:
    """分页查询当前用户的历史跑步记录（按本地开始时间倒序）。

    Args:
        limit: 每页条数，默认 10。
        offset: 跳过的条数，默认 0。
        start_date: 起始日期过滤（本地时间），格式 YYYY-MM-DD。
        end_date: 结束日期过滤（本地时间），格式 YYYY-MM-DD。

    需要通过 Authorization: Bearer <JWT> 进行身份验证。
    """
    user_id = _current_user_id()
    if not user_id:
        return {"error": "无法识别当前用户，请检查 JWT"}

    filters = [
        MainActivity.user_id == int(user_id),
        MainActivity.sport_type_raw.in_(RUNNING_TYPES),
    ]
    if start_date:
        filters.append(MainActivity.start_time_local >= start_date)
    if end_date:
        filters.append(MainActivity.start_time_local <= end_date)

    with SessionLocal() as session:
        total = (
            session.execute(
                select(func.count())
                .select_from(MainActivity)
                .where(*filters)
            ).scalar_one()
            or 0
        )
        result = session.execute(
            select(MainActivity)
            .where(*filters)
            .order_by(MainActivity.start_time_local.desc())
            .limit(limit)
            .offset(offset)
        )
        activities = result.scalars().all()

    return {
        "status": "success",
        "data": [_activity_to_dict(a) for a in activities],
        "total": total,
    }
