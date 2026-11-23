"""t_sleep_detail 表 ORM 模型（与 blunt-serv 的 SleepDetail 对齐，只读查询用）。

无 user_id，靠 daily_id 关联 t_sleep_daily 实现用户隔离。
activity_level: 0=深睡 1=浅睡 2=REM 3=清醒。
"""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class SleepDetail(Base):
    """用户睡眠阶段片段，对应表 `t_sleep_detail`。"""

    __tablename__ = "t_sleep_detail"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    daily_id: Mapped[int] = mapped_column(BigInteger, index=True)
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    duration_seconds: Mapped[int] = mapped_column(Integer)
    activity_level: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
