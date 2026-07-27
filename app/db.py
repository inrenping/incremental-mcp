from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import text

from app.config import settings

Base = declarative_base()

engine = create_async_engine(
    settings.database_url,
    echo=settings.app_env == "development",
    future=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def get_db() -> AsyncSession:
    """获取数据库会话，用于 FastAPI Depends。"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db() -> None:
    """启动时验证数据库连接。"""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
            await conn.commit()
    except Exception as exc:
        import logging

        logging.getLogger(__name__).warning(f"Database connection check failed: {exc}")
        raise


async def close_db() -> None:
    """关闭数据库连接池。"""
    await engine.dispose()
