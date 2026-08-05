"""心率数据相关的 MCP 工具：查询每日心率汇总与心率明细。"""

from datetime import date as date_type
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import select

from fastmcp.server.dependencies import get_http_headers

from app.auth import decode_token, get_user_id_from_payload
from app.db import SessionLocal
from app.models.heart_rate_daily import HeartRateDaily
from app.models.heart_rate_detail import HeartRateDetail
from app.models.user import User

DEFAULT_TIMEZONE = "Asia/Shanghai"
# 单次最多返回一个月（31 天）的每日汇总
MAX_HISTORY_DAYS = 31


def _current_user_id() -> str | None:
    """从当前请求的 Authorization header 中解析用户 ID（JWT sub 字段）。"""
    headers = get_http_headers(include_all=True)
    auth = headers.get("Authorization") or headers.get("authorization", "")
    if not auth.startswith("Bearer "):
        return None
    token = auth[7:]
    payload = decode_token(token)
    return get_user_id_from_payload(payload)


def _user_timezone(session, user_id: int) -> str:
    """获取用户的 IANA 时区，缺省用 Asia/Shanghai。"""
    user = session.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
    return user.timezone if user and user.timezone else DEFAULT_TIMEZONE


def get_heart_rate_history(
    days: int = 7,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict:
    """获取当前用户最近 N 天或指定日期范围的每日心率汇总（按日期倒序）。

    Args:
        days: 仅当未指定 start_date/end_date 时生效，返回最近多少天的记录，
            默认 7，范围 1-31。
        start_date: 起始日期（含），格式 YYYY-MM-DD，与 end_date 配合使用。
        end_date: 结束日期（含），格式 YYYY-MM-DD，缺省为当前用户时区的今天。

    指定日期范围时最多返回一个月（31 天）的数据，超出会截断到最近的 31 天。
    返回每条记录的 date、max_heart_rate、min_heart_rate、
    resting_heart_rate、last_seven_days_avg_resting_heart_rate。
    需要通过 Authorization: Bearer <JWT> 进行身份验证。
    """
    user_id = _current_user_id()
    if not user_id:
        return {"error": "无法识别当前用户，请检查 JWT"}

    with SessionLocal() as session:
        query = select(HeartRateDaily).where(HeartRateDaily.user_id == int(user_id))

        if start_date is not None or end_date is not None:
            # 日期范围模式：最多返回一个月（31 天），超出截断到最近 31 天
            tz = ZoneInfo(_user_timezone(session, int(user_id)))
            try:
                start = date_type.fromisoformat(start_date) if start_date else None
                end = date_type.fromisoformat(end_date) if end_date else None
            except ValueError:
                return {"error": "日期格式错误，请使用 YYYY-MM-DD 格式"}

            if end is None:
                end = datetime.now(tz).date()
            if start is None:
                start = end - timedelta(days=MAX_HISTORY_DAYS - 1)
            if start > end:
                return {
                    "error": f"start_date 不能晚于 end_date: {start_date} > {end_date}"
                }
            if (end - start).days >= MAX_HISTORY_DAYS:
                start = end - timedelta(days=MAX_HISTORY_DAYS - 1)

            query = query.where(
                HeartRateDaily.calendar_date >= start,
                HeartRateDaily.calendar_date <= end,
            )
            limit = None
        else:
            # 最近 N 天模式
            days = max(1, min(days, MAX_HISTORY_DAYS))
            limit = days

        result = session.execute(
            query.order_by(HeartRateDaily.calendar_date.desc()).limit(limit)
        )
        records = result.scalars().all()

    return {
        "status": "success",
        "data": [
            {
                "date": r.calendar_date.isoformat(),
                "max_heart_rate": r.max_heart_rate,
                "min_heart_rate": r.min_heart_rate,
                "resting_heart_rate": r.resting_heart_rate,
                "last_seven_days_avg_resting_heart_rate": r.last_seven_days_avg_resting_heart_rate,
            }
            for r in records
        ],
    }


def get_daily_heart_rate(date: str | None = None) -> dict:
    """获取当前用户指定日期的当天心率数据（汇总 + 明细）。

    Args:
        date: 日期，格式 YYYY-MM-DD，缺省为当前用户时区的今天。

    明细按用户时区计算当天的 UTC 起止范围，采样时间升序返回。
    需要通过 Authorization: Bearer <JWT> 进行身份验证。
    """
    user_id = _current_user_id()
    if not user_id:
        return {"error": "无法识别当前用户，请检查 JWT"}

    with SessionLocal() as session:
        tz = ZoneInfo(_user_timezone(session, int(user_id)))

        if date is None:
            date = datetime.now(tz).strftime("%Y-%m-%d")
        try:
            query_date = date_type.fromisoformat(date)
        except ValueError:
            return {"error": f"日期格式错误，请使用 YYYY-MM-DD 格式: {date}"}

        # 计算该日期在用户时区下的 UTC 起止时间
        start_of_day = datetime.combine(query_date, time.min, tzinfo=tz).astimezone(
            timezone.utc
        )
        end_of_day = datetime.combine(query_date, time.max, tzinfo=tz).astimezone(
            timezone.utc
        )

        # 明细按采样时间范围查询，并限定属于当前用户（通过 daily 表关联）
        details = (
            session.execute(
                select(HeartRateDetail)
                .join(HeartRateDaily, HeartRateDetail.daily_id == HeartRateDaily.id)
                .where(
                    HeartRateDaily.user_id == int(user_id),
                    HeartRateDetail.sample_time.between(start_of_day, end_of_day),
                )
                .order_by(HeartRateDetail.sample_time)
            )
            .scalars()
            .all()
        )

        daily = session.execute(
            select(HeartRateDaily).where(
                HeartRateDaily.user_id == int(user_id),
                HeartRateDaily.calendar_date == query_date,
            )
        ).scalar_one_or_none()

    return {
        "status": "success",
        "data": {
            "daily": (
                {
                    "id": daily.id,
                    "user_id": daily.user_id,
                    "date": daily.calendar_date.isoformat(),
                    "max_heart_rate": daily.max_heart_rate,
                    "min_heart_rate": daily.min_heart_rate,
                    "resting_heart_rate": daily.resting_heart_rate,
                    "last_seven_days_avg_resting_heart_rate": daily.last_seven_days_avg_resting_heart_rate,
                    "created_at": (
                        daily.created_at.isoformat() if daily.created_at else None
                    ),
                    "updated_at": (
                        daily.updated_at.isoformat() if daily.updated_at else None
                    ),
                }
                if daily
                else None
            ),
            "details": [
                {"sample_time": d.sample_time.isoformat(), "heart_rate": d.heart_rate}
                for d in details
            ],
        },
    }
