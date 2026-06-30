from __future__ import annotations

import json
import logging
from typing import Any

import redis.asyncio as aioredis

from shared.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_pool: aioredis.Redis | None = None

REDIS_URL = settings.redis_url
CONVERSATION_TTL = 1800


def _safe_redis_url(url: str) -> str:
    """Redacta credenciales de la URL de Redis para logging seguro."""
    try:
        from urllib.parse import urlparse, urlunparse
        parsed = urlparse(url)
        if parsed.password:
            safe = parsed._replace(netloc=f"{parsed.hostname}:{parsed.port or 6379}")
            return urlunparse(safe)
    except Exception:
        pass
    return url.split("@")[-1] if "@" in url else url


async def init_redis():
    global _pool
    try:
        _pool = aioredis.from_url(REDIS_URL, decode_responses=True)
        await _pool.ping()
        logger.info("Redis connected: %s", _safe_redis_url(REDIS_URL))
    except Exception as e:
        logger.warning("Redis unavailable (%s), running stateless", e)
        _pool = None


async def close_redis():
    global _pool
    if _pool:
        await _pool.aclose()
        _pool = None
        logger.info("Redis connection closed")


def _key(wa_id: str) -> str:
    return f"conversacion:{wa_id}"


async def get_conversation(wa_id: str) -> dict[str, Any] | None:
    if not _pool:
        return None
    data = await _pool.get(_key(wa_id))
    if data:
        return json.loads(data)
    return None


async def set_conversation(wa_id: str, data: dict[str, Any]):
    if not _pool:
        return
    await _pool.setex(_key(wa_id), CONVERSATION_TTL, json.dumps(data, default=str))


async def delete_conversation(wa_id: str):
    if not _pool:
        return
    await _pool.delete(_key(wa_id))


def is_redis_available() -> bool:
    return _pool is not None
