from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from admin.app.core.auth import get_current_user, get_current_username
from shared.core.database import get_db
from shared.models.emergencia import (
    EmergenciaFaunaRescate,
    EmergenciaFloraArbolCaido,
    EmergenciaFloraIVCTala,
    EmergenciaHidricaContaminacion,
    ReporteEmergencia,
    ReporteSeguimiento,
    ReporteHistorial,
)
from shared.schemas.admin import (
    PaginacionCursor,
    ReporteDetailResponse,
    ReporteGestionResponse,
    CrearReporteRequest,
)
from shared.schemas.emergencia import TIPO_A_AREA

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reportes", tags=["Reportes"], dependencies=[Depends(get_current_user)])


async def _get_seg_counts(db: AsyncSession, reporte_ids: list[int]) -> dict[int, int]:
    """Devuelve un mapa {reporte_id: count} de seguimientos para los IDs dados."""
    if not reporte_ids:
        return {}
    result = await db.execute(
        select(ReporteSeguimiento.reporte_id, func.count(ReporteSeguimiento.id).label("cnt"))
        .where(ReporteSeguimiento.reporte_id.in_(reporte_ids))
        .group_by(ReporteSeguimiento.reporte_id)
    )
    return {row.reporte_id: row.cnt for row in result}


def _reporte_a_gestion(r: ReporteEmergencia, seg_count: int = 0) -> ReporteGestionResponse:
    return ReporteGestionResponse(
        id=r.id,
        whatsapp_from=r.whatsapp_from,
        area=r.area,
        tipo_de_emergencia=r.tipo_de_emergencia,
        descripcion_emergencia=r.descripcion_emergencia,
        descripcion_detallada=r.descripcion_detallada,
        nivel_de_gravedad=r.nivel_de_gravedad,
        requiere_atencion_inmediata=r.requiere_atencion_inmediata,
        direccion_hechos=r.direccion_hechos,
        ubicacion_inferida=r.ubicacion_inferida,
        latitud=r.latitud,
        longitud=r.longitud,
        texto_original=r.texto_original,
        nombre_reportante=r.nombre_reportante,
        telefono=r.telefono,
        email=r.email,
        estado=r.estado,
        asignado_a=r.asignado_a,
        seguimiento_count=seg_count,
        created_at=r.created_at.isoformat(),
    )


def _reporte_a_detail(r: ReporteEmergencia) -> ReporteDetailResponse:
    return ReporteDetailResponse(
        id=r.id,
        whatsapp_from=r.whatsapp_from,
        area=r.area,
        tipo_de_emergencia=r.tipo_de_emergencia,
        descripcion_emergencia=r.descripcion_emergencia,
        descripcion_detallada=r.descripcion_detallada,
        nivel_de_gravedad=r.nivel_de_gravedad,
        requiere_atencion_inmediata=r.requiere_atencion_inmediata,
        direccion_hechos=r.direccion_hechos,
        ubicacion_inferida=r.ubicacion_inferida,
        latitud=r.latitud,
        longitud=r.longitud,
        texto_original=r.texto_original,
        nombre_reportante=r.nombre_reportante,
        telefono=r.telefono,
        email=r.email,
        estado=r.estado,
        asignado_a=r.asignado_a,
        created_at=r.created_at.isoformat(),
    )


@router.get("/", response_model=PaginacionCursor)
async def listar_reportes(
    estado: str | None = None,
    asignado_a: str | None = None,
    cursor: int | None = None,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    query = select(ReporteEmergencia).order_by(ReporteEmergencia.created_at.desc()).limit(limit)
    if cursor is not None:
        query = query.where(ReporteEmergencia.id < cursor)
    if estado:
        estados = [e.strip() for e in estado.split(",")]
        query = query.where(ReporteEmergencia.estado.in_(estados))
    if asignado_a is not None:
        if asignado_a == "":
            query = query.where(ReporteEmergencia.asignado_a.is_(None))
        else:
            query = query.where(ReporteEmergencia.asignado_a == asignado_a)
    result = await db.execute(query)
    rows = result.scalars().all()
    seg_counts = await _get_seg_counts(db, [r.id for r in rows])
    items = [_reporte_a_gestion(r, seg_counts.get(r.id, 0)) for r in rows]
    next_cursor = rows[-1].id if len(rows) == limit else None
    return PaginacionCursor(items=items, next_cursor=next_cursor)


@router.get("/mis-tareas", response_model=PaginacionCursor)
async def mis_tareas(
    cursor: int | None = None,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    username: str = Depends(get_current_username),
):
    query = (
        select(ReporteEmergencia)
        .where(ReporteEmergencia.asignado_a == username)
        .order_by(ReporteEmergencia.created_at.desc())
        .limit(limit)
    )
    if cursor is not None:
        query = query.where(ReporteEmergencia.id < cursor)
    result = await db.execute(query)
    rows = result.scalars().all()
    seg_counts = await _get_seg_counts(db, [r.id for r in rows])
    items = [_reporte_a_gestion(r, seg_counts.get(r.id, 0)) for r in rows]
    next_cursor = rows[-1].id if len(rows) == limit else None
    return PaginacionCursor(items=items, next_cursor=next_cursor)


@router.post("/", response_model=ReporteGestionResponse, status_code=201)
async def crear_reporte(
    body: CrearReporteRequest,
    db: AsyncSession = Depends(get_db),
    username: str = Depends(get_current_username),
):
    area = body.area or TIPO_A_AREA.get(body.tipo_de_emergencia, "flora")

    reporte = ReporteEmergencia(
        estado="informada",
        whatsapp_from=body.whatsapp_from,
        area=area,
        tipo_de_emergencia=body.tipo_de_emergencia,
        descripcion_emergencia=body.descripcion_emergencia,
        descripcion_detallada=body.descripcion_detallada or body.descripcion_emergencia,
        nivel_de_gravedad=body.nivel_de_gravedad,
        requiere_atencion_inmediata=body.requiere_atencion_inmediata,
        direccion_hechos=body.direccion_hechos,
        ubicacion_inferida=body.ubicacion_inferida,
        latitud=body.latitud,
        longitud=body.longitud,
        nombre_reportante=body.nombre_reportante,
        telefono=body.telefono,
        email=body.email,
        fuente="admin",
    )
    db.add(reporte)
    await db.flush()

    hist = ReporteHistorial(
        reporte_id=reporte.id,
        usuario=username,
        accion="creado",
        campo=None,
        valor_anterior=None,
        valor_nuevo=None,
    )
    db.add(hist)

    await db.commit()
    await db.refresh(reporte)
    return _reporte_a_gestion(reporte)


@router.get("/{reporte_id}", response_model=ReporteDetailResponse)
async def detalle_reporte(reporte_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ReporteEmergencia).where(ReporteEmergencia.id == reporte_id))
    reporte = result.scalar_one_or_none()
    if not reporte:
        raise HTTPException(status_code=404, detail="Reporte no encontrado")
    return _reporte_a_detail(reporte)


@router.get(
    "/flora/arbol-caido",
    response_model=PaginacionCursor,
    summary="Flora — Arbol caido",
)
async def listar_arbol_caido(
    cursor: int | None = None,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(ReporteEmergencia)
        .join(EmergenciaFloraArbolCaido, EmergenciaFloraArbolCaido.reporte_id == ReporteEmergencia.id)
        .order_by(ReporteEmergencia.created_at.desc())
        .limit(limit)
    )
    if cursor is not None:
        query = query.where(ReporteEmergencia.id < cursor)
    result = await db.execute(query)
    rows = result.scalars().all()
    seg_counts = await _get_seg_counts(db, [r.id for r in rows])
    items = [_reporte_a_gestion(r, seg_counts.get(r.id, 0)) for r in rows]
    next_cursor = rows[-1].id if len(rows) == limit else None
    return PaginacionCursor(items=items, next_cursor=next_cursor)


@router.get(
    "/fauna/rescate-animales",
    response_model=PaginacionCursor,
    summary="Fauna — Rescate de animales silvestres",
)
async def listar_rescate_animales(
    cursor: int | None = None,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(ReporteEmergencia)
        .join(EmergenciaFaunaRescate, EmergenciaFaunaRescate.reporte_id == ReporteEmergencia.id)
        .order_by(ReporteEmergencia.created_at.desc())
        .limit(limit)
    )
    if cursor is not None:
        query = query.where(ReporteEmergencia.id < cursor)
    result = await db.execute(query)
    rows = result.scalars().all()
    seg_counts = await _get_seg_counts(db, [r.id for r in rows])
    items = [_reporte_a_gestion(r, seg_counts.get(r.id, 0)) for r in rows]
    next_cursor = rows[-1].id if len(rows) == limit else None
    return PaginacionCursor(items=items, next_cursor=next_cursor)


@router.get(
    "/flora-ivc/tala-arboles",
    response_model=PaginacionCursor,
    summary="Flora IVC — Tala de arboles",
)
async def listar_tala_arboles(
    cursor: int | None = None,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(ReporteEmergencia)
        .join(EmergenciaFloraIVCTala, EmergenciaFloraIVCTala.reporte_id == ReporteEmergencia.id)
        .order_by(ReporteEmergencia.created_at.desc())
        .limit(limit)
    )
    if cursor is not None:
        query = query.where(ReporteEmergencia.id < cursor)
    result = await db.execute(query)
    rows = result.scalars().all()
    seg_counts = await _get_seg_counts(db, [r.id for r in rows])
    items = [_reporte_a_gestion(r, seg_counts.get(r.id, 0)) for r in rows]
    next_cursor = rows[-1].id if len(rows) == limit else None
    return PaginacionCursor(items=items, next_cursor=next_cursor)


@router.get(
    "/hidrica/contaminacion",
    response_model=PaginacionCursor,
    summary="Hidrica — Contaminacion de fuente hidrica",
)
async def listar_contaminacion_hidrica(
    cursor: int | None = None,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(ReporteEmergencia)
        .join(
            EmergenciaHidricaContaminacion,
            EmergenciaHidricaContaminacion.reporte_id == ReporteEmergencia.id,
        )
        .order_by(ReporteEmergencia.created_at.desc())
        .limit(limit)
    )
    if cursor is not None:
        query = query.where(ReporteEmergencia.id < cursor)
    result = await db.execute(query)
    rows = result.scalars().all()
    seg_counts = await _get_seg_counts(db, [r.id for r in rows])
    items = [_reporte_a_gestion(r, seg_counts.get(r.id, 0)) for r in rows]
    next_cursor = rows[-1].id if len(rows) == limit else None
    return PaginacionCursor(items=items, next_cursor=next_cursor)
