"""t_heart_rate_detail 表 ORM 模型（与 blunt-serv 的 HeartRateDetail 对齐，只读查询用）。"""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class HeartRateDetail(Base):
    """用户心率采样明细，对应表 `t_heart_rate_detail`。"""

    __tablename__ = "t_heart_rate_detail"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    daily_id: Mapped[int] = mapped_column(BigInteger, index=True)
    sample_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    heart_rate: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
