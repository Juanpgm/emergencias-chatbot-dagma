"""Fixtures compartidos para tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import get_db
from app.main import app
from app.schemas.emergencia import DatosEmergencia, NivelGravedad, TipoEmergencia


async def _override_get_db():
    """Override de get_db para tests: devuelve un mock sin conectar a DB real."""
    yield AsyncMock()


@pytest.fixture
async def client():
    """Cliente HTTP asíncrono para tests de endpoints."""
    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
def datos_emergencia_mock() -> DatosEmergencia:
    """Datos de emergencia de ejemplo para tests."""
    return DatosEmergencia(
        nombre_reportante="Juan Pérez",
        telefono="+573001234567",
        email=None,
        direccion_hechos="Cerro de las Tres Cruces, Cali",
        direccion_persona=None,
        tipo_de_emergencia=TipoEmergencia.incendio_forestal,
        descripcion_emergencia="Incendio forestal activo en el cerro.",
        descripcion_detallada="Se reporta un incendio forestal activo en el cerro de las Tres Cruces, zona occidental de Cali.",
        ubicacion_inferida="Cerro de las Tres Cruces, Comuna 1, Cali",
        latitud=3.4516,
        longitud=-76.5320,
        nivel_de_gravedad=NivelGravedad.alta,
        requiere_atencion_inmediata=True,
    )


@pytest.fixture
def mock_extraccion(datos_emergencia_mock):
    """Mock del servicio de extracción LLM."""
    with patch(
        "app.routers.whatsapp.extraer_datos_emergencia",
        new_callable=AsyncMock,
        return_value=datos_emergencia_mock,
    ) as mock:
        yield mock


@pytest.fixture
def mock_guardar_reporte():
    """Mock del servicio de persistencia."""
    reporte_mock = MagicMock()
    reporte_mock.id = 42
    with patch(
        "app.routers.whatsapp.guardar_reporte",
        new_callable=AsyncMock,
        return_value=reporte_mock,
    ) as mock:
        yield mock


@pytest.fixture
def mock_transcripcion():
    """Mock del servicio de transcripción."""
    with patch(
        "app.routers.whatsapp.transcribir_audio",
        new_callable=AsyncMock,
        return_value="Hay un incendio en el cerro de las Tres Cruces",
    ) as mock:
        yield mock
