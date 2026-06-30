from __future__ import annotations

import asyncio
import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI

from shared.core.config import get_settings

settings = get_settings()

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Chatbot service starting (env=%s)", settings.app_env)
    from chatbot.app.core.redis import init_redis, close_redis
    await init_redis()
    yield
    await close_redis()
    logger.info("Chatbot service stopped")


app = FastAPI(
    title="DAGMA Chatbot API",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "chatbot", "env": settings.app_env}


from chatbot.app.routers import whatsapp
app.include_router(whatsapp.router)
