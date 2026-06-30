from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

import bcrypt as _bcrypt_lib

from shared.schemas.emergencia import NivelGravedad, TipoEmergencia


class Base(DeclarativeBase):
    pass


class ReporteEmergencia(Base):
    __tablename__ = "reportes_emergencia"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre_reportante: Mapped[str | None] = mapped_column(String(255), nullable=True)
    telefono: Mapped[str | None] = mapped_column(String(30), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    whatsapp_from: Mapped[str] = mapped_column(String(50), nullable=False)
    direccion_hechos: Mapped[str | None] = mapped_column(String(500), nullable=True)
    direccion_persona: Mapped[str | None] = mapped_column(String(500), nullable=True)
    area: Mapped[str] = mapped_column(String(20), nullable=False)
    tipo_de_emergencia: Mapped[str] = mapped_column(
        Enum(TipoEmergencia, name="tipo_emergencia_enum", create_constraint=True),
        nullable=False,
    )
    descripcion_emergencia: Mapped[str] = mapped_column(Text, nullable=False)
    descripcion_detallada: Mapped[str] = mapped_column(Text, nullable=False)
    ubicacion_inferida: Mapped[str | None] = mapped_column(String(500), nullable=True)
    latitud: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitud: Mapped[float | None] = mapped_column(Float, nullable=True)
    nivel_de_gravedad: Mapped[str] = mapped_column(
        Enum(NivelGravedad, name="nivel_gravedad_enum", create_constraint=True),
        nullable=False,
    )
    requiere_atencion_inmediata: Mapped[bool] = mapped_column(Boolean, nullable=False)
    texto_original: Mapped[str | None] = mapped_column(Text, nullable=True)
    fuente: Mapped[str] = mapped_column(String(20), default="whatsapp")
    estado: Mapped[str] = mapped_column(String(20), nullable=False, default="informada")
    asignado_a: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    flora_arbol_caido: Mapped[list[EmergenciaFloraArbolCaido]] = relationship(
        back_populates="reporte", cascade="all, delete-orphan", passive_deletes=True
    )
    fauna_rescate: Mapped[list[EmergenciaFaunaRescate]] = relationship(
        back_populates="reporte", cascade="all, delete-orphan", passive_deletes=True
    )
    flora_ivc_tala: Mapped[list[EmergenciaFloraIVCTala]] = relationship(
        back_populates="reporte", cascade="all, delete-orphan", passive_deletes=True
    )
    hidrica_contaminacion: Mapped[list[EmergenciaHidricaContaminacion]] = relationship(
        back_populates="reporte", cascade="all, delete-orphan", passive_deletes=True
    )

    seguimientos: Mapped[list[ReporteSeguimiento]] = relationship(back_populates="reporte", cascade="all, delete-orphan")
    historial: Mapped[list[ReporteHistorial]] = relationship(back_populates="reporte", cascade="all, delete-orphan")


class ReporteSeguimiento(Base):
    __tablename__ = "reporte_seguimiento"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    reporte_id: Mapped[int] = mapped_column(Integer, ForeignKey("reportes_emergencia.id", ondelete="CASCADE"), nullable=False)
    usuario: Mapped[str] = mapped_column(String(100), nullable=False)
    mensaje: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    reporte: Mapped[ReporteEmergencia] = relationship(back_populates="seguimientos")


class ReporteHistorial(Base):
    __tablename__ = "reporte_historial"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    reporte_id: Mapped[int] = mapped_column(Integer, ForeignKey("reportes_emergencia.id", ondelete="CASCADE"), nullable=False)
    usuario: Mapped[str] = mapped_column(String(100), nullable=False)
    accion: Mapped[str] = mapped_column(String(50), nullable=False)
    campo: Mapped[str | None] = mapped_column(String(50), nullable=True)
    valor_anterior: Mapped[str | None] = mapped_column(String(255), nullable=True)
    valor_nuevo: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    reporte: Mapped[ReporteEmergencia] = relationship(back_populates="historial")


class EmergenciaFloraArbolCaido(Base):
    __tablename__ = "emergencias_flora_arbol_caido"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    reporte_id: Mapped[int] = mapped_column(Integer, ForeignKey("reportes_emergencia.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    reporte: Mapped[ReporteEmergencia] = relationship(back_populates="flora_arbol_caido")


class EmergenciaFaunaRescate(Base):
    __tablename__ = "emergencias_fauna_rescate_animales"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    reporte_id: Mapped[int] = mapped_column(Integer, ForeignKey("reportes_emergencia.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    reporte: Mapped[ReporteEmergencia] = relationship(back_populates="fauna_rescate")


class EmergenciaFloraIVCTala(Base):
    __tablename__ = "emergencias_flora_ivc_tala_arboles"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    reporte_id: Mapped[int] = mapped_column(Integer, ForeignKey("reportes_emergencia.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    reporte: Mapped[ReporteEmergencia] = relationship(back_populates="flora_ivc_tala")


class EmergenciaHidricaContaminacion(Base):
    __tablename__ = "emergencias_hidrica_contaminacion"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    reporte_id: Mapped[int] = mapped_column(Integer, ForeignKey("reportes_emergencia.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    reporte: Mapped[ReporteEmergencia] = relationship(back_populates="hidrica_contaminacion")


class AdminUser(Base):
    __tablename__ = "admin_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reset_token: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reset_token_expires: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    def set_password(self, password: str) -> None:
        self.password_hash = _bcrypt_lib.hashpw(password.encode(), _bcrypt_lib.gensalt()).decode()

    def verify_password(self, password: str) -> bool:
        if not self.password_hash:
            return False
        return _bcrypt_lib.checkpw(password.encode(), self.password_hash.encode())
