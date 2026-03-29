"""Esquemas Pydantic para la extracción de datos de emergencia."""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ── Enums ──────────────────────────────────────────────────────────────────────

class NivelGravedad(str, Enum):
    alta = "alta"
    media = "media"
    baja = "baja"


class TipoEmergencia(str, Enum):
    """Tipos de emergencia ambiental gestionados por DAGMA."""

    arbol_caido = "arbol_caido"                            # Flora: árbol caído
    rescate_animales_silvestres = "rescate_animales_silvestres"  # Fauna: rescate
    tala_arboles = "tala_arboles"                          # Flora IVC: tala ilegal
    contaminacion_fuente_hidrica = "contaminacion_fuente_hidrica"  # Hídrica


class AreaEmergencia(str, Enum):
    """Área temática que agrupa los tipos de emergencia."""

    flora = "flora"
    fauna = "fauna"
    flora_ivc = "flora_ivc"
    hidrica = "hidrica"


# Mapeo tipo → área (usado en la capa de servicios)
TIPO_A_AREA: dict[TipoEmergencia, AreaEmergencia] = {
    TipoEmergencia.arbol_caido: AreaEmergencia.flora,
    TipoEmergencia.rescate_animales_silvestres: AreaEmergencia.fauna,
    TipoEmergencia.tala_arboles: AreaEmergencia.flora_ivc,
    TipoEmergencia.contaminacion_fuente_hidrica: AreaEmergencia.hidrica,
}


# ── Modelo principal de datos extraídos ────────────────────────────────────────

class DatosEmergencia(BaseModel):
    """Datos estructurados extraídos del reporte de emergencia."""

    nombre_reportante: Optional[str] = Field(
        None, description="Nombre completo de la persona que reporta."
    )
    telefono: Optional[str] = Field(
        None, description="Número de teléfono de contacto."
    )
    email: Optional[str] = Field(
        None, description="Correo electrónico de contacto."
    )
    direccion_hechos: Optional[str] = Field(
        None, description="Dirección donde ocurrieron los hechos."
    )
    direccion_persona: Optional[str] = Field(
        None, description="Dirección de residencia de quien reporta."
    )
    tipo_de_emergencia: TipoEmergencia = Field(
        ...,
        description=(
            "Tipo de emergencia ambiental. Valores posibles: "
            "arbol_caido (árbol caído que obstruye o representa peligro), "
            "rescate_animales_silvestres (animal silvestre herido, atrapado o en peligro), "
            "tala_arboles (tala ilegal o no autorizada de árboles), "
            "contaminacion_fuente_hidrica (contaminación de ríos, quebradas, humedales u otras fuentes de agua)."
        ),
    )
    descripcion_emergencia: str = Field(
        ..., description="Descripción breve del incidente (máx. 2 oraciones)."
    )
    descripcion_detallada: str = Field(
        ..., description="Resumen ampliado con contexto adicional inferido."
    )
    ubicacion_inferida: Optional[str] = Field(
        None,
        description="Ubicación inferida a partir del mensaje (barrio, comuna, punto de referencia).",
    )
    latitud: Optional[float] = Field(None, description="Latitud GPS si fue proporcionada.")
    longitud: Optional[float] = Field(None, description="Longitud GPS si fue proporcionada.")
    nivel_de_gravedad: NivelGravedad = Field(
        ..., description="Nivel de gravedad: alta, media o baja."
    )
    requiere_atencion_inmediata: bool = Field(
        ..., description="True si la situación requiere atención inmediata."
    )


# ── Payload entrante de WhatsApp ───────────────────────────────────────────────

class WhatsAppMessage(BaseModel):
    """Estructura simplificada de un mensaje entrante de WhatsApp / Twilio."""

    message_sid: Optional[str] = Field(None, alias="MessageSid")
    from_number: str = Field(
        ..., alias="From", description="Número del remitente (ej. whatsapp:+573001234567)."
    )
    to_number: Optional[str] = Field(None, alias="To")
    body: Optional[str] = Field(None, alias="Body", description="Texto del mensaje.")
    num_media: int = Field(0, alias="NumMedia")
    media_url_0: Optional[str] = Field(None, alias="MediaUrl0")
    media_content_type_0: Optional[str] = Field(None, alias="MediaContentType0")
    latitude: Optional[float] = Field(None, alias="Latitude")
    longitude: Optional[float] = Field(None, alias="Longitude")

    model_config = {"populate_by_name": True}


# ── Respuesta del webhook ──────────────────────────────────────────────────────

class WebhookResponse(BaseModel):
    status: str = "ok"
    message: str = ""
    reporte_id: Optional[int] = None
    area: Optional[str] = None
    tipo: Optional[str] = None


# ── Respuesta de reporte guardado ──────────────────────────────────────────────

class ReporteResponse(BaseModel):
    """Representación de un reporte guardado en la base de datos."""

    id: int
    whatsapp_from: str
    area: str
    tipo_de_emergencia: TipoEmergencia
    descripcion_emergencia: str
    nivel_de_gravedad: NivelGravedad
    requiere_atencion_inmediata: bool
    direccion_hechos: Optional[str] = None
    ubicacion_inferida: Optional[str] = None
    latitud: Optional[float] = None
    longitud: Optional[float] = None
    texto_original: Optional[str] = None
    created_at: str

    model_config = {"from_attributes": True}
