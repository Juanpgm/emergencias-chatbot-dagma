from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_health_ok_por_defecto(app):
    """Sin fallos de migracion registrados, /health responde healthy."""
    app.state.migrations_ok = True
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "healthy"
    assert body["service"] == "admin"


@pytest.mark.asyncio
async def test_health_degradado_cuando_migraciones_fallan(app):
    """Si las migraciones fallaron al arrancar, /health lo expone como degradado."""
    app.state.migrations_ok = False
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.get("/health")
    finally:
        app.state.migrations_ok = True

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "degraded"
    assert body["db"] == "migrations_failed"
