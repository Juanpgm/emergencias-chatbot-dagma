"""Tests para los esquemas Pydantic."""

from __future__ import annotations

import pytest

from app.schemas.emergencia import (
    DatosEmergencia,
    NivelGravedad,
    TipoEmergencia,
    WhatsAppMessage,
)


def test_datos_emergencia_campos_minimos():
    datos = DatosEmergencia(
        tipo_de_emergencia=TipoEmergencia.incendio_forestal,
        descripcion_emergencia="Incendio activo",
        descripcion_detallada="Incendio forestal activo en zona urbana",
        nivel_de_gravedad=NivelGravedad.alta,
        requiere_atencion_inmediata=True,
    )
    assert datos.tipo_de_emergencia == TipoEmergencia.incendio_forestal
    assert datos.nombre_reportante is None
    assert datos.latitud is None


def test_datos_emergencia_todos_los_campos():
    datos = DatosEmergencia(
        nombre_reportante="María García",
        telefono="+573009876543",
        email="maria@example.com",
        direccion_hechos="Calle 5 # 23-10, Cali",
        direccion_persona="Carrera 100 # 11-30",
        tipo_de_emergencia=TipoEmergencia.contaminacion_agua,
        descripcion_emergencia="Vertimiento en el río Cali",
        descripcion_detallada="Se observa vertimiento de sustancia color oscuro en el río Cali, a la altura del puente Ortiz.",
        ubicacion_inferida="Puente Ortiz, Centro, Cali",
        latitud=3.4516,
        longitud=-76.5320,
        nivel_de_gravedad=NivelGravedad.media,
        requiere_atencion_inmediata=False,
    )
    assert datos.email == "maria@example.com"
    assert datos.latitud == 3.4516


def test_whatsapp_message_parsing():
    msg = WhatsAppMessage(
        From="whatsapp:+573001234567",
        Body="Hay un incendio",
        NumMedia=0,
    )
    assert msg.from_number == "whatsapp:+573001234567"
    assert msg.body == "Hay un incendio"
    assert msg.num_media == 0


def test_whatsapp_message_con_media():
    msg = WhatsAppMessage(
        From="whatsapp:+573001234567",
        NumMedia=1,
        MediaUrl0="https://api.twilio.com/test.ogg",
        MediaContentType0="audio/ogg",
    )
    assert msg.num_media == 1
    assert msg.media_url_0 == "https://api.twilio.com/test.ogg"


def test_nivel_gravedad_valores():
    assert NivelGravedad.alta.value == "alta"
    assert NivelGravedad.media.value == "media"
    assert NivelGravedad.baja.value == "baja"


def test_tipo_emergencia_valores():
    assert len(TipoEmergencia) == 11
    assert TipoEmergencia.incendio_forestal.value == "incendio_forestal"
    assert TipoEmergencia.otro.value == "otro"
