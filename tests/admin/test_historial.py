from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from shared.core.database import get_db
from shared.models.emergencia import ReporteHistorial
from tests.admin.helpers import make_session


@pytest.mark.asyncio
async def test_listar_historial_requiere_auth(client):
    response = await client.get("/reportes/1/historial")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_listar_historial_reporte_no_existe(client, app, auth_headers):
    async def _override():
        yield make_session(reporte_exists=False)
    app.dependency_overrides[get_db] = _override

    response = await client.get("/reportes/999/historial", headers=auth_headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_listar_historial_exitoso(client, app, auth_headers):
    mock_hist = MagicMock(spec=ReporteHistorial)
    mock_hist.id = 1
    mock_hist.reporte_id = 1
    mock_hist.usuario = "admin"
    mock_hist.accion = "cambio_estado"
    mock_hist.campo = "estado"
    mock_hist.valor_anterior = "informada"
    mock_hist.valor_nuevo = "asignada"
    mock_hist.created_at = "2024-01-01T00:00:00"

    async def _override():
        yield make_session(reporte_exists=True, scalar_list=[mock_hist])
    app.dependency_overrides[get_db] = _override

    response = await client.get("/reportes/1/historial", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["accion"] == "cambio_estado"
    assert data[0]["valor_anterior"] == "informada"
    assert data[0]["valor_nuevo"] == "asignada"


@pytest.mark.asyncio
async def test_listar_historial_vacio(client, app, auth_headers):
    async def _override():
        yield make_session(reporte_exists=True, scalar_list=[])
    app.dependency_overrides[get_db] = _override

    response = await client.get("/reportes/1/historial", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 0
