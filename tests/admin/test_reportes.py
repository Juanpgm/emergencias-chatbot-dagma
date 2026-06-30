from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_listar_reportes_sin_auth(client):
    response = await client.get("/reportes/")
    assert response.status_code == 403


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
