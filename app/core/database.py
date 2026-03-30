"""Conexión asíncrona a PostgreSQL con SQLAlchemy."""

from __future__ import annotations

import ssl

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

settings = get_settings()

# asyncpg requiere ssl en connect_args para conexiones externas de Railway
_connect_args: dict = {}
if "rlwy.net" in settings.database_url:
    _ssl_ctx = ssl.create_default_context()
    _ssl_ctx.check_hostname = False
    _ssl_ctx.verify_mode = ssl.CERT_NONE
    _connect_args["ssl"] = _ssl_ctx

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
