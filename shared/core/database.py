from __future__ import annotations

import re
import ssl

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from shared.core.config import get_settings

settings = get_settings()


def _build_engine_args(url: str) -> tuple[str, dict]:
    """Strip psycopg2-style sslmode from URL and convert to asyncpg SSL context."""
    needs_ssl = bool(re.search(r"sslmode=(require|verify-ca|verify-full)", url))
    clean_url = re.sub(r"[?&]sslmode=[^&]*", "", url).rstrip("?&")

    connect_args: dict = {}
    if needs_ssl:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        connect_args["ssl"] = ctx

    return clean_url, connect_args


_db_url, _connect_args = _build_engine_args(settings.database_url)

engine = create_async_engine(
    _db_url,
    echo=(settings.app_env == "development"),
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=3600,
    connect_args=_connect_args,
)

async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncSession:
    async with async_session_factory() as session:
        yield session
