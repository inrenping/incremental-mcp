from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class UserRefreshToken(Base):
    __tablename__ = "t_user_refresh_tokens"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("t_users.id", ondelete="CASCADE"))
    refresh_token: Mapped[str] = mapped_column(Text)
    expires_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_ip: Mapped[str | None] = mapped_column(String(45))
    user_agent: Mapped[str | None] = mapped_column(Text)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

    user: Mapped["User"] = relationship(back_populates="refresh_tokens")
