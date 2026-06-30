"""Tests para el endpoint de WhatsApp webhook."""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_health_check(client):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


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
async def test_webhook_texto_valido(client, mock_extraccion, mock_guardar_reporte):
    response = await client.post(
        "/webhook/whatsapp",
        data={
            "From": "whatsapp:+573001234567",
            "Body": "Hay un árbol caído en el cerro de las Tres Cruces",
            "NumMedia": "0",
        },
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/xml"
    body = response.text
    assert "<Response>" in body
    assert "<Message>" in body
    assert "Reporte #42" in body

    mock_extraccion.assert_called_once()
    mock_guardar_reporte.assert_called_once()


@pytest.mark.asyncio
async def test_webhook_audio(
    client, mock_transcripcion, mock_extraccion, mock_guardar_reporte
):
    response = await client.post(
        "/webhook/whatsapp",
        data={
            "From": "whatsapp:+573001234567",
            "Body": "",
            "NumMedia": "1",
            "MediaUrl0": "https://api.twilio.com/audio/test.ogg",
            "MediaContentType0": "audio/ogg",
        },
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/xml"
    body = response.text
    assert "<Response>" in body

    mock_transcripcion.assert_called_once_with("https://api.twilio.com/audio/test.ogg")
    mock_extraccion.assert_called_once()


@pytest.mark.asyncio
async def test_webhook_mensaje_vacio(client):
    response = await client.post(
        "/webhook/whatsapp",
        data={
            "From": "whatsapp:+573001234567",
            "NumMedia": "0",
        },
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/xml"
    body = response.text
    assert "Hola" in body
    assert "asistente de emergencias" in body


@pytest.mark.asyncio
async def test_webhook_con_ubicacion(client, mock_extraccion, mock_guardar_reporte):
    response = await client.post(
        "/webhook/whatsapp",
        data={
            "From": "whatsapp:+573001234567",
            "Body": "Hay tala ilegal en el cerro de las Tres Cruces, varias personas cortando árboles",
            "NumMedia": "0",
            "Latitude": "3.4516",
            "Longitude": "-76.5320",
        },
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/xml"

    # Verificar que se pasaron las coordenadas al LLM
    call_args = mock_extraccion.call_args
    texto_enviado = call_args[0][0]
    assert "3.4516" in texto_enviado
    assert "-76.532" in texto_enviado
