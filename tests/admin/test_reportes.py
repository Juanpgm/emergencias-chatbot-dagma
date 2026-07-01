from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.exc import SQLAlchemyError

from shared.core.database import get_db


@pytest.mark.asyncio
async def test_listar_reportes_sin_auth(client):
    response = await client.get("/reportes/")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_listar_reportes_error_db_devuelve_503(app, auth_headers):
    """Un fallo de base de datos debe devolver 503 con mensaje generico, no un 500 crudo."""

    async def _override_error_db():
        session = AsyncMock()
        session.execute.side_effect = SQLAlchemyError("conexion caida")
        yield session

    app.dependency_overrides[get_db] = _override_error_db
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.get("/reportes/", headers=auth_headers)
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json()["detail"] == "Error al consultar la base de datos"


@pytest.mark.asyncio
async def test_listar_reportes_con_auth(client, auth_headers):
    response = await client.get("/reportes/", headers=auth_headers)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_detalle_reporte_no_existe(client, auth_headers):
    response = await client.get("/reportes/999", headers=auth_headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_listar_reportes_con_cursor(client, auth_headers):
    response = await client.get("/reportes/?cursor=50&limit=20", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data


@pytest.mark.asyncio
async def test_detalle_reporte_requiere_auth(client):
    response = await client.get("/reportes/1")
    assert response.status_code == 403
