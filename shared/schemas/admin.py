from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class EstadoEmergencia(str, Enum):
    informada = "informada"    # estado inicial
    asignada = "asignada"
    en_proceso = "en_proceso"
    resuelta = "resuelta"
    cerrada = "cerrada"        # terminal
    cancelada = "cancelada"    # terminal, desde cualquier no-terminal


TRANSICIONES_ESTADO: dict[str, list[str]] = {
    "informada":  ["asignada", "cancelada"],
    "asignada":   ["en_proceso", "informada", "cancelada"],
    "en_proceso": ["resuelta", "asignada", "cancelada"],
    "resuelta":   ["cerrada", "en_proceso"],
    "cerrada":    [],
    "cancelada":  [],
}


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class ReporteDetailResponse(BaseModel):
    id: int
    whatsapp_from: str
    area: str
    tipo_de_emergencia: str
    descripcion_emergencia: str
    descripcion_detallada: Optional[str] = None
    nivel_de_gravedad: str
    requiere_atencion_inmediata: bool
    direccion_hechos: Optional[str] = None
    ubicacion_inferida: Optional[str] = None
    latitud: Optional[float] = None
    longitud: Optional[float] = None
    texto_original: Optional[str] = None
    nombre_reportante: Optional[str] = None
    telefono: Optional[str] = None
    email: Optional[str] = None
    estado: str = "informada"
    asignado_a: Optional[str] = None
    created_at: str
    model_config = {"from_attributes": True}


class PaginacionCursor(BaseModel):
    items: list
    next_cursor: Optional[int] = None


class CambioEstadoRequest(BaseModel):
    estado: EstadoEmergencia


class AsignarRequest(BaseModel):
    funcionario: str = Field(..., min_length=1, description="Nombre del funcionario a asignar")


class DesasignarRequest(BaseModel):
    pass


class SeguimientoRequest(BaseModel):
    mensaje: str = Field(..., min_length=1, description="Texto del seguimiento")


class SeguimientoResponse(BaseModel):
    id: int
    reporte_id: int
    usuario: str
    mensaje: str
    created_at: str
    model_config = {"from_attributes": True}


class HistorialResponse(BaseModel):
    id: int
    reporte_id: int
    usuario: str
    accion: str
    campo: Optional[str] = None
    valor_anterior: Optional[str] = None
    valor_nuevo: Optional[str] = None
    created_at: str
    model_config = {"from_attributes": True}


class CrearReporteRequest(BaseModel):
    tipo_de_emergencia: str
    descripcion_emergencia: str
    descripcion_detallada: str = ""
    nivel_de_gravedad: str
    requiere_atencion_inmediata: bool = False
    direccion_hechos: Optional[str] = None
    ubicacion_inferida: Optional[str] = None
    latitud: Optional[float] = None
    longitud: Optional[float] = None
    nombre_reportante: Optional[str] = None
    telefono: Optional[str] = None
    email: Optional[str] = None
    whatsapp_from: str = "admin"
    area: Optional[str] = None


class ReporteGestionResponse(BaseModel):
    id: int
    whatsapp_from: str
    area: str
    tipo_de_emergencia: str
    descripcion_emergencia: str
    descripcion_detallada: Optional[str] = None
    nivel_de_gravedad: str
    requiere_atencion_inmediata: bool
    direccion_hechos: Optional[str] = None
    ubicacion_inferida: Optional[str] = None
    latitud: Optional[float] = None
    longitud: Optional[float] = None
    texto_original: Optional[str] = None
    nombre_reportante: Optional[str] = None
    telefono: Optional[str] = None
    email: Optional[str] = None
    estado: str = "informada"
    asignado_a: Optional[str] = None
    seguimiento_count: int = 0
    created_at: str
    model_config = {"from_attributes": True}


class ProfileResponse(BaseModel):
    username: str
    display_name: Optional[str] = None
    email: Optional[str] = None
    created_at: str


class ProfileUpdateRequest(BaseModel):
    display_name: Optional[str] = None
    email: Optional[str] = None


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=6)


class ForgotPasswordRequest(BaseModel):
    username: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=6)
