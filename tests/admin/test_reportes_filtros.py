from __future__ import annotations

import pytest

from shared.core.database import get_db
from tests.admin.helpers import make_session, mock_reporte


@pytest.mark.asyncio
async def test_reportes_filtro_estado(client, app, auth_headers):
    async def _override():
        s = make_session(reporte_exists=True)
        yield s
    app.dependency_overrides[get_db] = _override

    response = await client.get("/reportes/?estado=informada", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data


@pytest.mark.asyncio
async def test_reportes_filtro_asignado(client, app, auth_headers):
    async def _override():
        s = make_session(reporte_exists=True)
        yield s
    app.dependency_overrides[get_db] = _override

    response = await client.get("/reportes/?asignado_a=Juan", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data


@pytest.mark.asyncio
async def test_reportes_filtro_sin_asignar(client, app, auth_headers):
    async def _override():
        s = make_session(reporte_exists=True)
        yield s
    app.dependency_overrides[get_db] = _override

    response = await client.get("/reportes/?asignado_a=", headers=auth_headers)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_reportes_multiples_estados(client, app, auth_headers):
    async def _override():
        s = make_session(reporte_exists=True)
        yield s
    app.dependency_overrides[get_db] = _override

    response = await client.get("/reportes/?estado=informada,asignada", headers=auth_headers)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_mis_tareas_requiere_auth(client):
    response = await client.get("/reportes/mis-tareas")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_mis_tareas_exitoso(client, app, auth_headers):
    async def _override():
        s = make_session(reporte_exists=True)
        yield s
    app.dependency_overrides[get_db] = _override

    response = await client.get("/reportes/mis-tareas", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
