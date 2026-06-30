from __future__ import annotations

import pytest

from shared.core.database import get_db
from tests.admin.helpers import make_session, mock_reporte


@pytest.mark.asyncio
async def test_cambiar_estado_requiere_auth(client):
    response = await client.patch("/reportes/1/estado", json={"estado": "asignada"})
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_asignar_funcionario_requiere_auth(client):
    response = await client.post("/reportes/1/asignar", json={"funcionario": "Juan Perez"})
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_cambiar_estado_reporte_no_existe(client, auth_headers):
    response = await client.patch("/reportes/999/estado", json={"estado": "asignada"}, headers=auth_headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_asignar_funcionario_reporte_no_existe(client, auth_headers):
    response = await client.post("/reportes/999/asignar", json={"funcionario": "Juan Perez"}, headers=auth_headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_cambiar_estado_estado_invalido(client, auth_headers):
    response = await client.patch("/reportes/1/estado", json={"estado": "inexistente"}, headers=auth_headers)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_asignar_funcionario_nombre_vacio(client, auth_headers):
    response = await client.post("/reportes/1/asignar", json={"funcionario": ""}, headers=auth_headers)
    assert response.status_code == 422


# --- Tests de la máquina de estados canónica ---

@pytest.mark.asyncio
async def test_transicion_valida_informada_a_asignada(client, app, auth_headers):
    """Transición válida: informada -> asignada debe retornar 200."""
    async def _override():
        yield make_session(reporte_exists=True, reporte_estado="informada")
    app.dependency_overrides[get_db] = _override

    response = await client.patch("/reportes/1/estado", json={"estado": "asignada"}, headers=auth_headers)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_transicion_invalida_informada_a_en_proceso(client, app, auth_headers):
    """Transición inválida: informada -> en_proceso (saltando asignada) debe devolver 400."""
    async def _override():
        yield make_session(reporte_exists=True, reporte_estado="informada")
    app.dependency_overrides[get_db] = _override

    response = await client.patch("/reportes/1/estado", json={"estado": "en_proceso"}, headers=auth_headers)
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_estados_terminales_no_permiten_transicion_cerrada(client, app, auth_headers):
    """Estado terminal cerrada -> cualquier estado debe devolver 400."""
    async def _override():
        yield make_session(reporte_exists=True, reporte_estado="cerrada")
    app.dependency_overrides[get_db] = _override

    response = await client.patch("/reportes/1/estado", json={"estado": "resuelta"}, headers=auth_headers)
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_estados_terminales_no_permiten_transicion_cancelada(client, app, auth_headers):
    """Estado terminal cancelada -> cualquier estado debe devolver 400."""
    async def _override():
        yield make_session(reporte_exists=True, reporte_estado="cancelada")
    app.dependency_overrides[get_db] = _override

    response = await client.patch("/reportes/1/estado", json={"estado": "informada"}, headers=auth_headers)
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_estado_de_siembra_inicial_es_informada(client, app, auth_headers):
    """El estado inicial de un reporte nuevo debe ser 'informada', no 'pendiente'."""
    from shared.models.emergencia import ReporteEmergencia
    reporte = ReporteEmergencia.__new__(ReporteEmergencia)
    # Verificar que el default del campo es "informada"
    default_val = ReporteEmergencia.estado.property.columns[0].default.arg
    assert default_val == "informada", f"Expected 'informada', got '{default_val}'"
