"""t_sleep_nap 表 ORM 模型（与 blunt-serv 的 SleepNap 对齐，只读查询用）。"""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class SleepNap(Base):
    """用户小睡记录，对应表 `t_sleep_nap`。"""

    __tablename__ = "t_sleep_nap"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    daily_id: Mapped[int] = mapped_column(BigInteger, index=True)
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    duration_seconds: Mapped[int] = mapped_column(Integer)
    nap_feedback: Mapped[str | None] = mapped_column(String(128))
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
