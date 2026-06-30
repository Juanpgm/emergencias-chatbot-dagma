"""Utilities compartidas para tests del admin API."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from shared.models.emergencia import ReporteEmergencia


def mock_reporte(id: int = 1, estado: str = "informada") -> MagicMock:
    r = MagicMock(spec=ReporteEmergencia)
    r.id = id
    r.whatsapp_from = "test"
    r.area = "flora"
    r.tipo_de_emergencia = "arbol_caido"
    r.descripcion_emergencia = "test descripcion"
    r.descripcion_detallada = None
    r.nivel_de_gravedad = "baja"
    r.requiere_atencion_inmediata = False
    r.direccion_hechos = None
    r.ubicacion_inferida = None
    r.latitud = None
    r.longitud = None
    r.texto_original = None
    r.nombre_reportante = None
    r.telefono = None
    r.email = None
    r.estado = estado
    r.asignado_a = None
    r.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
    return r


def make_session(reporte_exists=True, scalar_list=None, reporte_estado="informada"):
    session = AsyncMock()
    execute_result = MagicMock()
    scalar_result = MagicMock()
    scalar_result.all.return_value = scalar_list or []
    execute_result.scalars.return_value = scalar_result
    execute_result.scalar_one_or_none = MagicMock(
        return_value=mock_reporte(estado=reporte_estado) if reporte_exists else None
    )
    execute_result.scalar_one = MagicMock(return_value=mock_reporte(estado=reporte_estado))
    session.execute.return_value = execute_result
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock(side_effect=lambda obj: setattr(obj, "created_at", datetime(2024, 1, 1, tzinfo=timezone.utc)))
    return session
