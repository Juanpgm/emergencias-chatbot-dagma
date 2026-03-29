"""Punto de entrada de la aplicación FastAPI."""

from __future__ import annotations

import asyncio
import logging
import sys

# asyncpg requiere SelectorEventLoop en Windows (incompatible con ProactorEventLoop)
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from fastapi import FastAPI

from app.core.config import get_settings
from app.routers import reportes, whatsapp

settings = get_settings()

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)

app = FastAPI(
    title="DAGMA Emergencias Bot",
    description="Backend para atención de emergencias ambientales vía WhatsApp.",
    version="0.1.0",
)

app.include_router(whatsapp.router)
app.include_router(reportes.router)


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "dagma-emergencias-bot"}
