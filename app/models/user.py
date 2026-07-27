from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class User(Base):
    __tablename__ = "t_users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_name: Mapped[str | None] = mapped_column(String(255), unique=True)
    user_email: Mapped[str | None] = mapped_column(String(255), unique=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    active: Mapped[bool | None] = mapped_column(Boolean, default=False)
    vip: Mapped[bool | None] = mapped_column(Boolean, default=False)
    timezone: Mapped[str | None] = mapped_column(String, default="Asia/Shanghai")

    refresh_tokens: Mapped[list["UserRefreshToken"]] = relationship(
        back_populates="user"
    )
