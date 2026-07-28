from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.config import settings


def _normalize_psycopg2_url(url: str) -> str:
    """把 postgresql+asyncpg:// 统一转成 postgresql+psycopg2://（或保持原 postgresql://）。"""
    if url.startswith("postgresql+asyncpg://"):
        return "postgresql://" + url[len("postgresql+asyncpg://"):]
    return url


Base = declarative_base()

_engine = create_engine(
    _normalize_psycopg2_url(settings.database_url),
    echo=settings.app_env == "development",
    future=True,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    bind=_engine,
    class_=Session,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


@contextmanager
def get_db():
    """获取数据库会话（上下文管理器，同步版本）。"""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def init_db() -> None:
    """启动时验证数据库连接。"""
    try:
        with _engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            conn.commit()
    except Exception as exc:
        import logging

        logging.getLogger(__name__).warning(f"Database connection check failed: {exc}")
        raise


def close_db() -> None:
    """关闭数据库连接池。"""
    _engine.dispose()
