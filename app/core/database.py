"""Conexión asíncrona a PostgreSQL con SQLAlchemy."""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.database_url,
    echo=(settings.app_env == "development"),
    pool_size=5,
    max_overflow=10,
)

async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncSession:  # type: ignore[misc]
    """Dependency de FastAPI para inyectar una sesión de base de datos."""
    async with async_session_factory() as session:
        yield session
