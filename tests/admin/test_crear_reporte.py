from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from shared.core.database import get_db
from tests.admin.helpers import make_session


@pytest.mark.asyncio
async def test_crear_reporte_requiere_auth(client):
    body = {
        "tipo_de_emergencia": "arbol_caido",
        "descripcion_emergencia": "test",
        "nivel_de_gravedad": "baja",
    }
    response = await client.post("/reportes/", json=body)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_crear_reporte_campos_obligatorios(client, auth_headers):
    response = await client.post("/reportes/", json={}, headers=auth_headers)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_crear_reporte_exitoso(client, app, auth_headers):
    async def _override():
        s = make_session(reporte_exists=True)
        s.add = lambda x: setattr(x, "id", 1)
        s.flush = AsyncMock(side_effect=lambda: None)
        yield s
    app.dependency_overrides[get_db] = _override

    body = {
        "tipo_de_emergencia": "arbol_caido",
        "descripcion_emergencia": "Arbol caido en la via",
        "nivel_de_gravedad": "alta",
        "direccion_hechos": "Calle 5 # 10-20",
        "barrio": "Centro",
        "nombre_reportante": "Juan Perez",
        "telefono": "3001234567",
        "requiere_atencion_inmediata": True,
    }
    response = await client.post("/reportes/", json=body, headers=auth_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["tipo_de_emergencia"] == "arbol_caido"
    assert data["nivel_de_gravedad"] == "alta"
    assert "id" in data


@pytest.mark.asyncio
async def test_crear_reporte_solo_obligatorios(client, app, auth_headers):
    async def _override():
        s = make_session(reporte_exists=True)
        s.add = lambda x: setattr(x, "id", 1)
        s.flush = AsyncMock(side_effect=lambda: None)
        yield s
    app.dependency_overrides[get_db] = _override

    body = {
        "tipo_de_emergencia": "arbol_caido",
        "descripcion_emergencia": "Arbol caido",
        "nivel_de_gravedad": "baja",
    }
    response = await client.post("/reportes/", json=body, headers=auth_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["tipo_de_emergencia"] == "arbol_caido"
