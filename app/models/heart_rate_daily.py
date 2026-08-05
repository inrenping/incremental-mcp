"""t_heart_rate_daily 表 ORM 模型（与 blunt-serv 的 HeartRateDaily 对齐，只读查询用）。"""

from datetime import date, datetime

from sqlalchemy import BigInteger, Date, DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class HeartRateDaily(Base):
    """用户每日心率汇总，对应表 `t_heart_rate_daily`。"""

    __tablename__ = "t_heart_rate_daily"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    calendar_date: Mapped[date] = mapped_column(Date, index=True)
    max_heart_rate: Mapped[int | None] = mapped_column(Integer)
    min_heart_rate: Mapped[int | None] = mapped_column(Integer)
    resting_heart_rate: Mapped[int | None] = mapped_column(Integer)
    last_seven_days_avg_resting_heart_rate: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
