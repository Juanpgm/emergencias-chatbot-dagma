"""Punto de entrada de la aplicación FastAPI."""

from __future__ import annotations

import asyncio
import logging
import sys

# asyncpg requiere SelectorEventLoop en Windows (incompatible con ProactorEventLoop)
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from shared.core.config import get_settings
from app.routers import chat_ui, reportes, test_chat, whatsapp

settings = get_settings()
logger = logging.getLogger(__name__)

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)


def _run_migrations() -> None:
    """Ejecuta migraciones Alembic al inicio (psycopg2 síncrono)."""
    from alembic import command
    from alembic.config import Config

    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")


@asynccontextmanager
async def lifespan(application: FastAPI):
    logger.info("Ejecutando migraciones de base de datos...")
    try:
        await asyncio.to_thread(_run_migrations)
        logger.info("Migraciones completadas.")
    except Exception:
        logger.exception("Error al ejecutar migraciones — la app continúa de todas formas.")
    yield


app = FastAPI(
    title="DAGMA Emergencias Bot",
    description="Backend para atención de emergencias ambientales vía WhatsApp.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["Content-Type"],
)

app.include_router(whatsapp.router)
app.include_router(reportes.router)
app.include_router(test_chat.router)
app.include_router(chat_ui.router)


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "dagma-emergencias-bot"}


