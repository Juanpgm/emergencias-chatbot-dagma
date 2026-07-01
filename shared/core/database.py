from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from shared.core.config import get_settings

settings = get_settings()

# SSL is handled by sslmode=require in the DATABASE_URL.
# Do not pass ssl in connect_args — it conflicts with asyncpg when sslmode is
# already in the URL and causes unhandled exceptions during connection.
engine = create_async_engine(
    settings.database_url,
    echo=(settings.app_env == "development"),
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=3600,
)

async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncSession:
    async with async_session_factory() as session:
        yield session
