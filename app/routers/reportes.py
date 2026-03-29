"""Router para consultar reportes de emergencia guardados."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.emergencia import (
    EmergenciaFaunaRescate,
    EmergenciaFloraArbolCaido,
    EmergenciaFloraIVCTala,
    EmergenciaHidricaContaminacion,
    ReporteEmergencia,
)
from app.schemas.emergencia import ReporteResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reportes", tags=["Reportes"])


def _reporte_a_response(r: ReporteEmergencia) -> ReporteResponse:
    """Convierte un ORM ReporteEmergencia a ReporteResponse."""
    return ReporteResponse(
        id=r.id,
        whatsapp_from=r.whatsapp_from,
        area=r.area,
        tipo_de_emergencia=r.tipo_de_emergencia,
        descripcion_emergencia=r.descripcion_emergencia,
        nivel_de_gravedad=r.nivel_de_gravedad,
        requiere_atencion_inmediata=r.requiere_atencion_inmediata,
        direccion_hechos=r.direccion_hechos,
        ubicacion_inferida=r.ubicacion_inferida,
        latitud=r.latitud,
        longitud=r.longitud,
        texto_original=r.texto_original,
        created_at=r.created_at.isoformat(),
    )


# ── Todos los reportes ─────────────────────────────────────────────────────────

@router.get("/", response_model=list[ReporteResponse], summary="Todos los reportes")
async def listar_reportes(
    limite: int = 20,
    db: AsyncSession = Depends(get_db),
):
    """Retorna los últimos reportes de la tabla maestra, ordenados por fecha descendente."""
    result = await db.execute(
        select(ReporteEmergencia)
        .order_by(ReporteEmergencia.created_at.desc())
        .limit(limite)
    )
    return [_reporte_a_response(r) for r in result.scalars().all()]


# ── Flora: árbol caído ─────────────────────────────────────────────────────────

@router.get(
    "/flora/arbol-caido",
    response_model=list[ReporteResponse],
    summary="Flora — Árbol caído",
)
async def listar_arbol_caido(
    limite: int = 20,
    db: AsyncSession = Depends(get_db),
):
    """Reportes de la tabla emergencias_flora_arbol_caido con datos del reporte maestro."""
    result = await db.execute(
        select(ReporteEmergencia)
        .join(EmergenciaFloraArbolCaido, EmergenciaFloraArbolCaido.reporte_id == ReporteEmergencia.id)
        .order_by(ReporteEmergencia.created_at.desc())
        .limit(limite)
    )
    return [_reporte_a_response(r) for r in result.scalars().all()]


# ── Fauna: rescate de animales ─────────────────────────────────────────────────

@router.get(
    "/fauna/rescate-animales",
    response_model=list[ReporteResponse],
    summary="Fauna — Rescate de animales silvestres",
)
async def listar_rescate_animales(
    limite: int = 20,
    db: AsyncSession = Depends(get_db),
):
    """Reportes de la tabla emergencias_fauna_rescate_animales con datos del reporte maestro."""
    result = await db.execute(
        select(ReporteEmergencia)
        .join(EmergenciaFaunaRescate, EmergenciaFaunaRescate.reporte_id == ReporteEmergencia.id)
        .order_by(ReporteEmergencia.created_at.desc())
        .limit(limite)
    )
    return [_reporte_a_response(r) for r in result.scalars().all()]


# ── Flora IVC: tala de árboles ─────────────────────────────────────────────────

@router.get(
    "/flora-ivc/tala-arboles",
    response_model=list[ReporteResponse],
    summary="Flora IVC — Tala de árboles",
)
async def listar_tala_arboles(
    limite: int = 20,
    db: AsyncSession = Depends(get_db),
):
    """Reportes de la tabla emergencias_flora_ivc_tala_arboles con datos del reporte maestro."""
    result = await db.execute(
        select(ReporteEmergencia)
        .join(EmergenciaFloraIVCTala, EmergenciaFloraIVCTala.reporte_id == ReporteEmergencia.id)
        .order_by(ReporteEmergencia.created_at.desc())
        .limit(limite)
    )
    return [_reporte_a_response(r) for r in result.scalars().all()]


# ── Hídrica: contaminación ─────────────────────────────────────────────────────

@router.get(
    "/hidrica/contaminacion",
    response_model=list[ReporteResponse],
    summary="Hídrica — Contaminación de fuente hídrica",
)
async def listar_contaminacion_hidrica(
    limite: int = 20,
    db: AsyncSession = Depends(get_db),
):
    """Reportes de la tabla emergencias_hidrica_contaminacion con datos del reporte maestro."""
    result = await db.execute(
        select(ReporteEmergencia)
        .join(
            EmergenciaHidricaContaminacion,
            EmergenciaHidricaContaminacion.reporte_id == ReporteEmergencia.id,
        )
        .order_by(ReporteEmergencia.created_at.desc())
        .limit(limite)
    )
    return [_reporte_a_response(r) for r in result.scalars().all()]
