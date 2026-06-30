from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_health_check(client):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "chatbot"


@pytest.mark.asyncio
async def test_webhook_verificacion_token_valido(client):
    response = await client.get(
        "/webhook/whatsapp",
        params={
            "hub.mode": "subscribe",
            "hub.challenge": "123456",
            "hub.verify_token": "dagma_verify_2024",
        },
    )
    assert response.status_code == 200
    assert response.text == "123456"


@pytest.mark.asyncio
async def test_webhook_verificacion_token_invalido(client):
    response = await client.get(
        "/webhook/whatsapp",
        params={
            "hub.mode": "subscribe",
            "hub.challenge": "123456",
            "hub.verify_token": "token_incorrecto",
        },
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_webhook_texto_valido(client, meta_text_payload, mock_extraccion, mock_reportes):
    response = await client.post("/webhook/whatsapp", json=meta_text_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["reporte_id"] == 42

    mock_extraccion.assert_called_once()
    mock_reportes.assert_called_once()


@pytest.mark.asyncio
async def test_webhook_mensaje_vacio(client):
    payload = {
        "object": "whatsapp_business_account",
        "entry": [{"changes": [{"value": {"messaging_product": "whatsapp", "messages": []}}]}],
    }
    response = await client.post("/webhook/whatsapp", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ignored"


@pytest.mark.asyncio
async def test_webhook_bienvenida(client):
    payload = {
        "object": "whatsapp_business_account",
        "entry": [{"changes": [{"value": {"messaging_product": "whatsapp",
            "contacts": [{"wa_id": "573001234567"}],
            "messages": [{"from": "573001234567", "id": "w1", "timestamp": "0",
                "type": "text", "text": {"body": ""}}]
        }}]}],
    }
    response = await client.post("/webhook/whatsapp", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "welcome"


@pytest.mark.asyncio
async def test_webhook_mensaje_vago(client):
    payload = {
        "object": "whatsapp_business_account",
        "entry": [{"changes": [{"value": {"messaging_product": "whatsapp",
            "contacts": [{"wa_id": "573001234567"}],
            "messages": [{"from": "573001234567", "id": "w1", "timestamp": "0",
                "type": "text", "text": {"body": "no se"}}]
        }}]}],
    }
    response = await client.post("/webhook/whatsapp", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ask_details"


@pytest.mark.asyncio
async def test_webhook_consulta_orientacion(client):
    payload = {
        "object": "whatsapp_business_account",
        "entry": [{"changes": [{"value": {"messaging_product": "whatsapp",
            "contacts": [{"wa_id": "573001234567"}],
            "messages": [{"from": "573001234567", "id": "w1", "timestamp": "0",
                "type": "text", "text": {"body": "que haces"}}]
        }}]}],
    }
    response = await client.post("/webhook/whatsapp", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "orientation"


@pytest.mark.asyncio
async def test_webhook_con_ubicacion_gps(client, mock_extraccion, mock_reportes):
    payload = {
        "object": "whatsapp_business_account",
        "entry": [{"changes": [{"value": {"messaging_product": "whatsapp",
            "contacts": [{"wa_id": "573001234567"}],
            "messages": [{"from": "573001234567", "id": "w1", "timestamp": "0",
                "type": "location",
                "location": {"latitude": 3.4516, "longitude": -76.5320}}]
        }}]}],
    }
    response = await client.post("/webhook/whatsapp", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"

    call_args = mock_extraccion.call_args
    assert call_args is not None
    texto = call_args[0][0]
    assert "3.4516" in texto


@pytest.mark.asyncio
async def test_webhook_sin_ubicacion_pide_ubicacion(client, mock_extraccion):
    mock_extraccion.return_value.ubicacion_inferida = None
    mock_extraccion.return_value.direccion_hechos = None
    mock_extraccion.return_value.latitud = None
    mock_extraccion.return_value.longitud = None

    payload = {
        "object": "whatsapp_business_account",
        "entry": [{"changes": [{"value": {"messaging_product": "whatsapp",
            "contacts": [{"wa_id": "573001234567"}],
            "messages": [{"from": "573001234567", "id": "w1", "timestamp": "0",
                "type": "text", "text": {"body": "Hay un arbol caido en la carrera 8 con calle 15"}}]
        }}]}],
    }
    response = await client.post("/webhook/whatsapp", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "awaiting_location"
