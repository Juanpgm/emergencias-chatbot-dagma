"""Conexión asíncrona a PostgreSQL con SQLAlchemy."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

settings = get_settings()

_connect_args: dict = {}

engine = create_async_engine(
    settings.database_url,
    echo=(settings.app_env == "development"),
    pool_size=5,
    max_overflow=10,
    connect_args=_connect_args,
)

async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncSession:  # type: ignore[misc]
    """Dependency de FastAPI para inyectar una sesión de base de datos."""
    async with async_session_factory() as session:
        yield session
