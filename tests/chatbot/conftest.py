from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from shared.core.database import get_db
from shared.schemas.emergencia import DatosEmergencia, NivelGravedad, TipoEmergencia


async def _override_get_db():
    yield AsyncMock()


@pytest.fixture(autouse=True)
def _mock_redis():
    with (
        patch("chatbot.app.core.redis._pool", None),
        patch("chatbot.app.routers.whatsapp.get_conversation", new_callable=AsyncMock, return_value=None),
        patch("chatbot.app.routers.whatsapp.set_conversation", new_callable=AsyncMock),
        patch("chatbot.app.routers.whatsapp.delete_conversation", new_callable=AsyncMock),
    ):
        yield


@pytest.fixture(autouse=True)
def _mock_meta_api():
    with patch("chatbot.app.routers.whatsapp._enviar_mensaje_whatsapp", new_callable=AsyncMock):
        yield


@pytest.fixture
def app():
    from chatbot.app.main import app as chatbot_app
    return chatbot_app


@pytest.fixture
async def client(app):
    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
def mock_reportes():
    from chatbot.app.services.persistencia import guardar_reporte
    with patch("chatbot.app.routers.whatsapp.guardar_reporte", new_callable=AsyncMock) as mock:
        reporte_mock = MagicMock()
        reporte_mock.id = 42
        mock.return_value = reporte_mock
        yield mock


@pytest.fixture
def mock_extraccion():
    with patch("chatbot.app.routers.whatsapp.extraer_datos_emergencia", new_callable=AsyncMock) as mock:
        mock.return_value = DatosEmergencia(
            nombre_reportante="Juan Perez",
            telefono="+573001234567",
            tipo_de_emergencia=TipoEmergencia.arbol_caido,
            descripcion_emergencia="Arbol caido obstruyendo la via.",
            descripcion_detallada="Se reporta un arbol de gran tamano caido en el cerro de las Tres Cruces.",
            ubicacion_inferida="Cerro de las Tres Cruces, Comuna 1, Cali",
            latitud=3.4516,
            longitud=-76.5320,
            nivel_de_gravedad=NivelGravedad.alta,
            requiere_atencion_inmediata=True,
        )
        yield mock


@pytest.fixture
def meta_audio_payload():
    return {
        "object": "whatsapp_business_account",
        "entry": [{
            "changes": [{
                "value": {
                    "messaging_product": "whatsapp",
                    "contacts": [{"profile": {"name": "Juan"}, "wa_id": "573001234567"}],
                    "messages": [{
                        "from": "573001234567",
                        "id": "wamid.ABC123",
                        "timestamp": "1718467200",
                        "type": "audio",
                        "audio": {"id": "media_id_123"},
                    }]
                }
            }]
        }]
    }


@pytest.fixture
def meta_text_payload():
    return {
        "object": "whatsapp_business_account",
        "entry": [{
            "changes": [{
                "value": {
                    "messaging_product": "whatsapp",
                    "contacts": [{"profile": {"name": "Juan"}, "wa_id": "573001234567"}],
                    "messages": [{
                        "from": "573001234567",
                        "id": "wamid.ABC456",
                        "timestamp": "1718467200",
                        "type": "text",
                        "text": {"body": "Hay un arbol caido en la carrera 8 con calle 15, barrio Granada, esta bloqueando todo el paso"},
                    }]
                }
            }]
        }]
    }
