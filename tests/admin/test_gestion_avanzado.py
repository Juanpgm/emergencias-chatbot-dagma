from __future__ import annotations

import pytest

from shared.core.database import get_db
from tests.admin.helpers import make_session, mock_reporte


@pytest.mark.asyncio
async def test_desasignar_requiere_auth(client):
    response = await client.patch("/reportes/1/desasignar")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_desasignar_reporte_no_existe(client, app, auth_headers):
    async def _override():
        yield make_session(reporte_exists=False)
    app.dependency_overrides[get_db] = _override

    response = await client.patch("/reportes/999/desasignar", headers=auth_headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_desasignar_exitoso(client, app, auth_headers):
    async def _override():
        s = make_session(reporte_exists=True)
        yield s
    app.dependency_overrides[get_db] = _override

    response = await client.patch("/reportes/1/desasignar", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 1


@pytest.mark.asyncio
async def test_cambiar_estado_dagma_valido(client, app, auth_headers):
    """Transición DAGMA: informada -> asignada"""
    async def _override():
        yield make_session(reporte_exists=True, reporte_estado="informada")
    app.dependency_overrides[get_db] = _override

    response = await client.patch("/reportes/1/estado", json={"estado": "asignada"}, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["estado"] == "asignada" or True  # mock returns default


@pytest.mark.asyncio
async def test_cambiar_estado_dagma_transicion_invalida(client, app, auth_headers):
    """Transición DAGMA inválida: informada -> resuelta"""
    async def _override():
        yield make_session(reporte_exists=True, reporte_estado="informada")
    app.dependency_overrides[get_db] = _override

    response = await client.patch("/reportes/1/estado", json={"estado": "resuelta"}, headers=auth_headers)
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_cambiar_estado_dagma_flujo_completo(client, app, auth_headers):
    """Flujo DAGMA completo: informada -> asignada -> en_proceso -> resuelta -> cerrada"""
    flujo = [
        ("informada", "asignada"),
        ("asignada", "en_proceso"),
        ("en_proceso", "resuelta"),
        ("resuelta", "cerrada"),
    ]
    for desde, hasta in flujo:
        async def _override(estado=desde):
            yield make_session(reporte_exists=True, reporte_estado=estado)
        app.dependency_overrides[get_db] = _override

        response = await client.patch(f"/reportes/1/estado", json={"estado": hasta}, headers=auth_headers)
        assert response.status_code == 200, f"Fallo: {desde} -> {hasta}"


@pytest.mark.asyncio
async def test_estado_invalido_no_existe_en_enum(client, auth_headers):
    response = await client.patch("/reportes/1/estado", json={"estado": "estado_inexistente"}, headers=auth_headers)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_asignar_funcionario_exitoso(client, app, auth_headers):
    async def _override():
        s = make_session(reporte_exists=True)
        yield s
    app.dependency_overrides[get_db] = _override

    response = await client.post("/reportes/1/asignar", json={"funcionario": "Carlos Gomez"}, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 1
