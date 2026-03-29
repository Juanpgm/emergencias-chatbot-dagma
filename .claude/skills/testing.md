# SKILL: Testing para DAGMA Bot

## Cuándo usar

Cuando necesites crear o ejecutar tests.

## Setup

```python
# tests/conftest.py
import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app

@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
```

## Test de endpoint

```python
@pytest.mark.asyncio
async def test_webhook_texto(client, mock_extraccion, mock_db):
    response = await client.post(
        "/webhook/whatsapp",
        data={
            "From": "whatsapp:+573001234567",
            "Body": "Hay un incendio en el cerro de las Tres Cruces",
            "NumMedia": "0",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["reporte_id"] is not None
```

## Mocking

```python
from unittest.mock import AsyncMock, patch

@pytest.fixture
def mock_extraccion():
    datos = DatosEmergencia(
        tipo_de_emergencia="incendio_forestal",
        descripcion_emergencia="Incendio en cerro",
        descripcion_detallada="Incendio forestal activo",
        nivel_de_gravedad="alta",
        requiere_atencion_inmediata=True,
    )
    with patch("app.services.extraccion.extraer_datos_emergencia",
               new_callable=AsyncMock, return_value=datos) as mock:
        yield mock
```

## Ejecutar

```bash
pytest tests/ -v
pytest tests/ -v -k "test_webhook"
pytest tests/ --cov=app --cov-report=term-missing
```
