from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from shared.core.database import get_db
from shared.models.emergencia import ReporteSeguimiento
from tests.admin.helpers import make_session


@pytest.mark.asyncio
async def test_agregar_seguimiento_requiere_auth(client):
    response = await client.post("/reportes/1/seguimiento", json={"mensaje": "test"})
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_agregar_seguimiento_reporte_no_existe(client, app, auth_headers):
    async def _override():
        yield make_session(reporte_exists=False)
    app.dependency_overrides[get_db] = _override

    response = await client.post("/reportes/999/seguimiento", json={"mensaje": "test"}, headers=auth_headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_agregar_seguimiento_mensaje_vacio(client, auth_headers):
    response = await client.post("/reportes/1/seguimiento", json={"mensaje": ""}, headers=auth_headers)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_agregar_seguimiento_exitoso(client, app, auth_headers):
    async def _override():
        s = make_session(reporte_exists=True)
        s.add = lambda x: setattr(x, "id", 1)
        s.refresh = AsyncMock(side_effect=lambda obj: setattr(obj, "created_at", datetime(2024, 1, 1, tzinfo=timezone.utc)))
        yield s
    app.dependency_overrides[get_db] = _override

    response = await client.post("/reportes/1/seguimiento", json={"mensaje": "nota de prueba"}, headers=auth_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["mensaje"] == "nota de prueba"
    assert data["reporte_id"] == 1
    assert "id" in data
    assert "usuario" in data


@pytest.mark.asyncio
async def test_listar_seguimientos_requiere_auth(client):
    response = await client.get("/reportes/1/seguimiento")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_listar_seguimientos_reporte_no_existe(client, app, auth_headers):
    async def _override():
        yield make_session(reporte_exists=False)
    app.dependency_overrides[get_db] = _override

    response = await client.get("/reportes/999/seguimiento", headers=auth_headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_listar_seguimientos_exitoso(client, app, auth_headers):
    mock_seg = MagicMock(spec=ReporteSeguimiento)
    mock_seg.id = 1
    mock_seg.reporte_id = 1
    mock_seg.usuario = "admin"
    mock_seg.mensaje = "nota de prueba"
    mock_seg.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)

    async def _override():
        yield make_session(reporte_exists=True, scalar_list=[mock_seg])
    app.dependency_overrides[get_db] = _override

    response = await client.get("/reportes/1/seguimiento", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["mensaje"] == "nota de prueba"
    assert data[0]["usuario"] == "admin"


@pytest.mark.asyncio
async def test_listar_seguimientos_sin_resultados(client, app, auth_headers):
    async def _override():
        yield make_session(reporte_exists=True, scalar_list=[])
    app.dependency_overrides[get_db] = _override

    response = await client.get("/reportes/1/seguimiento", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 0
