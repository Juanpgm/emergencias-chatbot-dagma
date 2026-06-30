from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from admin.app.core.auth import get_current_user, get_current_username
from shared.core.database import get_db
from shared.models.emergencia import ReporteEmergencia, ReporteHistorial, ReporteSeguimiento
from shared.schemas.admin import (
    TRANSICIONES_ESTADO,
    AsignarRequest,
    CambioEstadoRequest,
    EstadoEmergencia,
    HistorialResponse,
    ReporteDetailResponse,
    SeguimientoRequest,
    SeguimientoResponse,
)

logger = logging.getLogger(__name__)

# Estados que ya superaron la asignación inicial — no se auto-avanza desde estos.
_ESTADOS_POST_ASIGNACION = {
    EstadoEmergencia.asignada.value,
    EstadoEmergencia.en_proceso.value,
    EstadoEmergencia.resuelta.value,
    EstadoEmergencia.cerrada.value,
    EstadoEmergencia.cancelada.value,
}

router = APIRouter(
    prefix="/reportes",
    tags=["Gestion"],
    dependencies=[Depends(get_current_user)],
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


@router.patch("/{reporte_id}/estado", response_model=ReporteDetailResponse)
async def cambiar_estado(
    reporte_id: int,
    body: CambioEstadoRequest,
    db: AsyncSession = Depends(get_db),
    username: str = Depends(get_current_username),
):
    result = await db.execute(select(ReporteEmergencia).where(ReporteEmergencia.id == reporte_id))
    reporte = result.scalar_one_or_none()
    if not reporte:
        raise HTTPException(status_code=404, detail="Reporte no encontrado")

    estado_actual = EstadoEmergencia(reporte.estado)
    estado_nuevo = body.estado

    transiciones_validas = TRANSICIONES_ESTADO.get(estado_actual.value, [])
    if estado_nuevo.value not in transiciones_validas:
        raise HTTPException(
            status_code=400,
            detail=f"No se puede cambiar de '{estado_actual.value}' a '{estado_nuevo.value}'",
        )

    old_val = reporte.estado
    await db.execute(
        update(ReporteEmergencia)
        .where(ReporteEmergencia.id == reporte_id)
        .values(estado=estado_nuevo.value)
    )

    db.add(ReporteHistorial(
        reporte_id=reporte_id,
        usuario=username,
        accion="cambio_estado",
        campo="estado",
        valor_anterior=old_val,
        valor_nuevo=estado_nuevo.value,
    ))
    await db.commit()

    result = await db.execute(select(ReporteEmergencia).where(ReporteEmergencia.id == reporte_id))
    reporte = result.scalar_one()
    return _reporte_a_detail(reporte)


@router.post("/{reporte_id}/asignar", response_model=ReporteDetailResponse)
async def asignar_funcionario(
    reporte_id: int,
    body: AsignarRequest,
    db: AsyncSession = Depends(get_db),
    username: str = Depends(get_current_username),
):
    result = await db.execute(select(ReporteEmergencia).where(ReporteEmergencia.id == reporte_id))
    reporte = result.scalar_one_or_none()
    if not reporte:
        raise HTTPException(status_code=404, detail="Reporte no encontrado")

    old_asignado = reporte.asignado_a
    old_estado = reporte.estado

    updates: dict = {"asignado_a": body.funcionario}
    if old_estado not in _ESTADOS_POST_ASIGNACION:
        updates["estado"] = EstadoEmergencia.asignada.value

    await db.execute(
        update(ReporteEmergencia)
        .where(ReporteEmergencia.id == reporte_id)
        .values(**updates)
    )

    db.add(ReporteHistorial(
        reporte_id=reporte_id,
        usuario=username,
        accion="asignado",
        campo="asignado_a",
        valor_anterior=old_asignado,
        valor_nuevo=body.funcionario,
    ))

    if "estado" in updates:
        db.add(ReporteHistorial(
            reporte_id=reporte_id,
            usuario=username,
            accion="cambio_estado",
            campo="estado",
            valor_anterior=old_estado,
            valor_nuevo="asignada",
        ))

    await db.commit()

    result = await db.execute(select(ReporteEmergencia).where(ReporteEmergencia.id == reporte_id))
    reporte = result.scalar_one()
    return _reporte_a_detail(reporte)


@router.patch("/{reporte_id}/desasignar", response_model=ReporteDetailResponse)
async def desasignar_funcionario(
    reporte_id: int,
    db: AsyncSession = Depends(get_db),
    username: str = Depends(get_current_username),
):
    result = await db.execute(select(ReporteEmergencia).where(ReporteEmergencia.id == reporte_id))
    reporte = result.scalar_one_or_none()
    if not reporte:
        raise HTTPException(status_code=404, detail="Reporte no encontrado")

    old_val = reporte.asignado_a
    await db.execute(
        update(ReporteEmergencia)
        .where(ReporteEmergencia.id == reporte_id)
        .values(asignado_a=None)
    )

    db.add(ReporteHistorial(
        reporte_id=reporte_id,
        usuario=username,
        accion="desasignado",
        campo="asignado_a",
        valor_anterior=old_val,
        valor_nuevo=None,
    ))
    await db.commit()

    result = await db.execute(select(ReporteEmergencia).where(ReporteEmergencia.id == reporte_id))
    reporte = result.scalar_one()
    return _reporte_a_detail(reporte)


@router.get("/{reporte_id}/historial", response_model=list[HistorialResponse])
async def listar_historial(
    reporte_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ReporteEmergencia).where(ReporteEmergencia.id == reporte_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Reporte no encontrado")

    rows = await db.execute(
        select(ReporteHistorial)
        .where(ReporteHistorial.reporte_id == reporte_id)
        .order_by(ReporteHistorial.created_at.desc())
    )
    return rows.scalars().all()


@router.post("/{reporte_id}/seguimiento", response_model=SeguimientoResponse, status_code=201)
async def agregar_seguimiento(
    reporte_id: int,
    body: SeguimientoRequest,
    db: AsyncSession = Depends(get_db),
    username: str = Depends(get_current_username),
):
    result = await db.execute(select(ReporteEmergencia).where(ReporteEmergencia.id == reporte_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Reporte no encontrado")

    seg = ReporteSeguimiento(
        reporte_id=reporte_id,
        usuario=username,
        mensaje=body.mensaje,
    )
    db.add(seg)

    db.add(ReporteHistorial(
        reporte_id=reporte_id,
        usuario=username,
        accion="seguimiento",
        campo=None,
        valor_anterior=None,
        valor_nuevo=None,
    ))
    await db.commit()
    await db.refresh(seg)

    return SeguimientoResponse(
        id=seg.id,
        reporte_id=seg.reporte_id,
        usuario=seg.usuario,
        mensaje=seg.mensaje,
        created_at=seg.created_at.isoformat(),
    )


@router.get("/{reporte_id}/seguimiento", response_model=list[SeguimientoResponse])
async def listar_seguimientos(
    reporte_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ReporteEmergencia).where(ReporteEmergencia.id == reporte_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Reporte no encontrado")

    rows = await db.execute(
        select(ReporteSeguimiento)
        .where(ReporteSeguimiento.reporte_id == reporte_id)
        .order_by(ReporteSeguimiento.created_at.asc())
    )
    seguimientos = rows.scalars().all()
    return [
        SeguimientoResponse(
            id=s.id,
            reporte_id=s.reporte_id,
            usuario=s.usuario,
            mensaje=s.mensaje,
            created_at=s.created_at.isoformat(),
        )
        for s in seguimientos
    ]
