"""t_sleep_daily 表 ORM 模型（与 blunt-serv 的 SleepDaily 对齐，只读查询用）。

口径：calendar_date 采用佳明口径 = 起床那天
（10/2 23:30 睡到 10/3 07:00 记为 10/3），与佳明 App 保持一致。
"""

from datetime import date, datetime

from sqlalchemy import BigInteger, Boolean, Date, DateTime, Float, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class SleepDaily(Base):
    """用户每日睡眠汇总，对应表 `t_sleep_daily`。"""

    __tablename__ = "t_sleep_daily"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    calendar_date: Mapped[date] = mapped_column(Date, index=True)
    sleep_start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sleep_end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    local_offset_minutes: Mapped[int | None] = mapped_column(Integer)
    sleep_time_seconds: Mapped[int | None] = mapped_column(Integer)
    nap_time_seconds: Mapped[int | None] = mapped_column(Integer)
    deep_sleep_seconds: Mapped[int | None] = mapped_column(Integer)
    light_sleep_seconds: Mapped[int | None] = mapped_column(Integer)
    rem_sleep_seconds: Mapped[int | None] = mapped_column(Integer)
    awake_sleep_seconds: Mapped[int | None] = mapped_column(Integer)
    unmeasurable_sleep_seconds: Mapped[int | None] = mapped_column(Integer)
    awake_count: Mapped[int | None] = mapped_column(Integer)
    sleep_score: Mapped[int | None] = mapped_column(Integer)
    average_sp_o2_value: Mapped[float | None] = mapped_column(Float)
    lowest_sp_o2_value: Mapped[int | None] = mapped_column(Integer)
    average_respiration_value: Mapped[float | None] = mapped_column(Float)
    avg_sleep_stress: Mapped[float | None] = mapped_column(Float)
    sleep_window_confirmed: Mapped[bool | None] = mapped_column(Boolean)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
