"""Servicio de persistencia: guarda reportes en la tabla maestra y en la tabla por tipo."""

from __future__ import annotations

import logging

from geoalchemy2.shape import from_shape
from shapely.geometry import Point
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.emergencia import (
    EmergenciaFaunaRescate,
    EmergenciaFloraArbolCaido,
    EmergenciaFloraIVCTala,
    EmergenciaHidricaContaminacion,
    ReporteEmergencia,
)
from app.schemas.emergencia import DatosEmergencia, TipoEmergencia, TIPO_A_AREA

logger = logging.getLogger(__name__)


async def guardar_reporte(
    db: AsyncSession,
    datos: DatosEmergencia,
    whatsapp_from: str,
    texto_original: str | None = None,
) -> ReporteEmergencia:
    """Persiste un reporte en la tabla maestra y en la tabla especializada por tipo.

    Flujo:
    1. Inserta en ``reportes_emergencia`` (tabla maestra).
    2. Según el tipo, inserta también en la tabla especializada correspondiente.
    3. Hace commit único al final.
    """
    area = TIPO_A_AREA[datos.tipo_de_emergencia].value

    geom = None
    if datos.latitud is not None and datos.longitud is not None:
        geom = from_shape(Point(datos.longitud, datos.latitud), srid=4326)

    # ── 1. Tabla maestra ───────────────────────────────────────────────────────
    reporte = ReporteEmergencia(
        nombre_reportante=datos.nombre_reportante,
        telefono=datos.telefono,
        email=datos.email,
        whatsapp_from=whatsapp_from,
        direccion_hechos=datos.direccion_hechos,
        direccion_persona=datos.direccion_persona,
        area=area,
        tipo_de_emergencia=datos.tipo_de_emergencia,
        descripcion_emergencia=datos.descripcion_emergencia,
        descripcion_detallada=datos.descripcion_detallada,
        ubicacion_inferida=datos.ubicacion_inferida,
        latitud=datos.latitud,
        longitud=datos.longitud,
        geom=geom,
        nivel_de_gravedad=datos.nivel_de_gravedad,
        requiere_atencion_inmediata=datos.requiere_atencion_inmediata,
        texto_original=texto_original,
        fuente="whatsapp",
    )

    db.add(reporte)
    await db.flush()  # obtiene reporte.id sin hacer commit todavía

    # ── 2. Tabla especializada ─────────────────────────────────────────────────
    especializada = _crear_registro_especializado(datos.tipo_de_emergencia, reporte.id)
    db.add(especializada)

    await db.commit()
    await db.refresh(reporte)

    logger.info(
        "Reporte #%d guardado — area=%s, tipo=%s",
        reporte.id,
        area,
        datos.tipo_de_emergencia.value,
    )
    return reporte


def _crear_registro_especializado(
    tipo: TipoEmergencia,
    reporte_id: int,
) -> (
    EmergenciaFloraArbolCaido
    | EmergenciaFaunaRescate
    | EmergenciaFloraIVCTala
    | EmergenciaHidricaContaminacion
):
    """Instancia el modelo especializado correspondiente al tipo de emergencia."""
    if tipo == TipoEmergencia.arbol_caido:
        return EmergenciaFloraArbolCaido(reporte_id=reporte_id)
    if tipo == TipoEmergencia.rescate_animales_silvestres:
        return EmergenciaFaunaRescate(reporte_id=reporte_id)
    if tipo == TipoEmergencia.tala_arboles:
        return EmergenciaFloraIVCTala(reporte_id=reporte_id)
    # contaminacion_fuente_hidrica (y cualquier valor futuro como fallback)
    return EmergenciaHidricaContaminacion(reporte_id=reporte_id)
