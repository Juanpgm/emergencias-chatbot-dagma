from __future__ import annotations

import asyncio
import logging
import sys

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from contextlib import asynccontextmanager

from fastapi import FastAPI

from shared.core.config import get_settings
from admin.app.routers import auth, gestion, profile, reportes

settings = get_settings()
logger = logging.getLogger(__name__)

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)


def _run_migrations() -> None:
    from alembic import command
    from alembic.config import Config

    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")


@asynccontextmanager
async def lifespan(application: FastAPI):
    logger.info("Ejecutando migraciones de base de datos...")
    try:
        await asyncio.to_thread(_run_migrations)
        application.state.migrations_ok = True
        logger.info("Migraciones completadas.")
    except Exception:
        application.state.migrations_ok = False
        logger.critical(
            "Error al ejecutar migraciones — el esquema puede estar incompleto y las "
            "lecturas pueden fallar. La app continua para permitir diagnostico via /health.",
            exc_info=True,
        )
    yield


app = FastAPI(
    title="DAGMA Admin API",
    description="API de administracion para el sistema de emergencias ambientales DAGMA.",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(auth.router)
app.include_router(profile.router)
app.include_router(reportes.router)
app.include_router(gestion.router)


@app.get("/health")
async def health_check():
    # Devuelve 200 siempre (para no tumbar el healthcheck del proveedor) pero expone
    # el estado degradado cuando las migraciones fallaron al arrancar.
    if getattr(app.state, "migrations_ok", True):
        return {"status": "healthy", "service": "admin"}
    return {"status": "degraded", "service": "admin", "db": "migrations_failed"}
