"""t_main_activity 表 ORM 模型（与 blunt-serv 的 MainActivity 对齐，只读查询用）。"""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    Float,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class MainActivity(Base):
    """统一运动活动汇总，对应表 `t_main_activity`。"""

    __tablename__ = "t_main_activity"

    __table_args__ = (
        # 与物理表一致：同一渠道下的原始活动ID唯一
        UniqueConstraint(
            "source_type", "activity_id", name="uq_main_act_source_origin"
        ),
        # 单列索引: 第三方连接ID
        Index("idx_main_activities_connect", "base_connect_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    base_connect_id: Mapped[int] = mapped_column(Integer)
    source_type: Mapped[str] = mapped_column(String(20))
    activity_id: Mapped[str] = mapped_column(String(64))
    activity_name: Mapped[str | None] = mapped_column(String(255))
    sport_type_raw: Mapped[str | None] = mapped_column(String(50))
    sport_mode_raw: Mapped[int | None] = mapped_column(Integer)
    start_time_gmt: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    start_time_local: Mapped[datetime | None] = mapped_column(DateTime(timezone=False))
    end_time_gmt: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    distance_meters: Mapped[float | None] = mapped_column(Numeric(12, 2))
    duration_seconds: Mapped[float | None] = mapped_column(Numeric(10, 2))
    moving_duration_seconds: Mapped[float | None] = mapped_column(Numeric(10, 2))
    calories: Mapped[float | None] = mapped_column(Numeric(10, 2))
    average_hr: Mapped[int | None] = mapped_column(Integer)
    max_hr: Mapped[int | None] = mapped_column(Integer)
    average_cadence: Mapped[int | None] = mapped_column(Integer)
    max_cadence: Mapped[int | None] = mapped_column(Integer)
    average_speed: Mapped[float | None] = mapped_column(Numeric(8, 3))
    max_speed: Mapped[float | None] = mapped_column(Numeric(8, 3))
    start_lat: Mapped[float | None] = mapped_column(Float)
    start_lon: Mapped[float | None] = mapped_column(Float)
    location_name: Mapped[str | None] = mapped_column(String(255))
    device_id: Mapped[str | None] = mapped_column(String(100))
    elevation_gain: Mapped[float | None] = mapped_column(Numeric(10, 2))
    elevation_loss: Mapped[float | None] = mapped_column(Numeric(10, 2))
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
