"""睡眠数据相关的 MCP 工具：查询每日睡眠汇总与单日睡眠详情。"""

from datetime import date as date_type
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import select

from fastmcp.server.dependencies import get_http_headers

from app.auth import decode_token, get_user_id_from_payload
from app.db import SessionLocal
from app.models.sleep_daily import SleepDaily
from app.models.sleep_detail import SleepDetail
from app.models.sleep_nap import SleepNap
from app.models.user import User

DEFAULT_TIMEZONE = "Asia/Shanghai"
# 与 get_heart_rate_history 一致：单次最多 31 天
MAX_HISTORY_DAYS = 31
# 佳明 sleepLevels.activityLevel 编码
LEVEL_NAMES = {0: "deep", 1: "light", 2: "rem", 3: "awake"}


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


def _iso(value):
    return value.isoformat() if value else None


def _daily_summary(r: SleepDaily) -> dict:
    """每日睡眠汇总序列化（不含 levels / naps）。"""
    return {
        "date": r.calendar_date.isoformat(),  # 佳明口径：起床那天
        "sleep_start_at": _iso(r.sleep_start_at),  # UTC
        "sleep_end_at": _iso(r.sleep_end_at),  # UTC
        "local_offset_minutes": r.local_offset_minutes,
        "sleep_time_seconds": r.sleep_time_seconds,
        "nap_time_seconds": r.nap_time_seconds,
        "deep_sleep_seconds": r.deep_sleep_seconds,
        "light_sleep_seconds": r.light_sleep_seconds,
        "rem_sleep_seconds": r.rem_sleep_seconds,
        "awake_sleep_seconds": r.awake_sleep_seconds,
        "unmeasurable_sleep_seconds": r.unmeasurable_sleep_seconds,
        "awake_count": r.awake_count,
        "sleep_score": r.sleep_score,
        "average_sp_o2_value": r.average_sp_o2_value,
        "lowest_sp_o2_value": r.lowest_sp_o2_value,
        "average_respiration_value": r.average_respiration_value,
        "avg_sleep_stress": r.avg_sleep_stress,
    }


def get_sleep_history(
    days: int = 7,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict:
    """获取当前用户最近 N 天或指定日期范围的每日睡眠汇总（按日期倒序）。

    注意日期口径：date = 佳明口径的「起床那天」。
    例如想查「10/2 晚上入睡、10/3 早上起床」这一觉，传 2026-10-03。

    Args:
        days: 仅当未指定 start_date/end_date 时生效，返回最近多少天的记录，
            默认 7，范围 1-31。
        start_date: 起始日期（含），格式 YYYY-MM-DD，与 end_date 配合使用。
        end_date: 结束日期（含），格式 YYYY-MM-DD，缺省为当前用户时区的今天。

    指定日期范围时最多返回一个月（31 天），超出会截断到最近的 31 天。
    只返回汇总字段，不含阶段片段和小睡；需要单日详情请调用 get_daily_sleep。
    缺失的日期不会补数据。需要通过 Authorization: Bearer <JWT> 进行身份验证。
    """
    user_id = _current_user_id()
    if not user_id:
        return {"error": "无法识别当前用户，请检查 JWT"}

    with SessionLocal() as session:
        query = select(SleepDaily).where(SleepDaily.user_id == int(user_id))

        if start_date is not None or end_date is not None:
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
                SleepDaily.calendar_date >= start,
                SleepDaily.calendar_date <= end,
            )
            limit = None
        else:
            days = max(1, min(days, MAX_HISTORY_DAYS))
            limit = days

        records = session.execute(
            query.order_by(SleepDaily.calendar_date.desc()).limit(limit)
        ).scalars().all()

    return {"status": "success", "data": [_daily_summary(r) for r in records]}


def get_daily_sleep(date: str | None = None) -> dict:
    """获取当前用户指定日期的睡眠数据（汇总 + 阶段片段 + 小睡）。

    注意日期口径：date = 佳明口径的「起床那天」。
    例如想查「10/2 晚上入睡、10/3 早上起床」这一觉，传 2026-10-03。

    Args:
        date: 日期，格式 YYYY-MM-DD，缺省为当前用户时区的今天。

    阶段片段 levels 的 activity_level: 0=深睡 1=浅睡 2=REM 3=清醒，
    同时附带可读的 level_name。所有时间字段均为 UTC ISO 格式。
    需要通过 Authorization: Bearer <JWT> 进行身份验证。
    """
    user_id = _current_user_id()
    if not user_id:
        return {"error": "无法识别当前用户，请检查 JWT"}

    with SessionLocal() as session:
        tz = ZoneInfo(_user_timezone(session, int(user_id)))

        if date is None:
            query_date = datetime.now(tz).date()
        else:
            try:
                query_date = date_type.fromisoformat(date)
            except ValueError:
                return {"error": f"日期格式错误，请使用 YYYY-MM-DD 格式: {date}"}

        daily = session.execute(
            select(SleepDaily).where(
                SleepDaily.user_id == int(user_id),
                SleepDaily.calendar_date == query_date,
            )
        ).scalar_one_or_none()

        if daily is None:
            return {"status": "success", "data": None, "message": "该日期无睡眠记录"}

        # 子表无 user_id，必须经 daily_id 关联主表来保证用户隔离
        levels = session.execute(
            select(SleepDetail)
            .where(SleepDetail.daily_id == daily.id)
            .order_by(SleepDetail.start_at)
        ).scalars().all()

        naps = session.execute(
            select(SleepNap)
            .where(SleepNap.daily_id == daily.id)
            .order_by(SleepNap.start_at)
        ).scalars().all()

    return {
        "status": "success",
        "data": {
            "daily": _daily_summary(daily),
            "levels": [
                {
                    "start_at": _iso(x.start_at),
                    "end_at": _iso(x.end_at),
                    "duration_seconds": x.duration_seconds,
                    "activity_level": x.activity_level,
                    "level_name": LEVEL_NAMES.get(x.activity_level, "unknown"),
                }
                for x in levels
            ],
            "naps": [
                {
                    "start_at": _iso(x.start_at),
                    "end_at": _iso(x.end_at),
                    "duration_seconds": x.duration_seconds,
                    "nap_feedback": x.nap_feedback,
                }
                for x in naps
            ],
        },
    }
