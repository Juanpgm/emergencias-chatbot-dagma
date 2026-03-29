"""Modelos SQLAlchemy para reportes de emergencia ambiental (DAGMA)."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.schemas.emergencia import NivelGravedad, TipoEmergencia


class Base(DeclarativeBase):
    pass


# ── Tabla maestra ──────────────────────────────────────────────────────────────

class ReporteEmergencia(Base):
    """Tabla maestra: recibe todos los reportes independientemente del tipo."""

    __tablename__ = "reportes_emergencia"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Datos del reportante
    nombre_reportante: Mapped[str | None] = mapped_column(String(255), nullable=True)
    telefono: Mapped[str | None] = mapped_column(String(30), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    whatsapp_from: Mapped[str] = mapped_column(String(50), nullable=False)

    # Direcciones
    direccion_hechos: Mapped[str | None] = mapped_column(String(500), nullable=True)
    direccion_persona: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Clasificación
    area: Mapped[str] = mapped_column(String(20), nullable=False)  # flora/fauna/flora_ivc/hidrica
    tipo_de_emergencia: Mapped[str] = mapped_column(
        Enum(TipoEmergencia, name="tipo_emergencia_enum", create_constraint=True),
        nullable=False,
    )
    descripcion_emergencia: Mapped[str] = mapped_column(Text, nullable=False)
    descripcion_detallada: Mapped[str] = mapped_column(Text, nullable=False)

    # Ubicación
    ubicacion_inferida: Mapped[str | None] = mapped_column(String(500), nullable=True)
    latitud: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitud: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Gravedad
    nivel_de_gravedad: Mapped[str] = mapped_column(
        Enum(NivelGravedad, name="nivel_gravedad_enum", create_constraint=True),
        nullable=False,
    )
    requiere_atencion_inmediata: Mapped[bool] = mapped_column(Boolean, nullable=False)

    # Metadatos
    texto_original: Mapped[str | None] = mapped_column(Text, nullable=True)
    fuente: Mapped[str] = mapped_column(String(20), default="whatsapp")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    # Relaciones hacia tablas especializadas
    flora_arbol_caido: Mapped[list[EmergenciaFloraArbolCaido]] = relationship(
        back_populates="reporte"
    )
    fauna_rescate: Mapped[list[EmergenciaFaunaRescate]] = relationship(
        back_populates="reporte"
    )
    flora_ivc_tala: Mapped[list[EmergenciaFloraIVCTala]] = relationship(
        back_populates="reporte"
    )
    hidrica_contaminacion: Mapped[list[EmergenciaHidricaContaminacion]] = relationship(
        back_populates="reporte"
    )


# ── Tablas especializadas por tipo ─────────────────────────────────────────────

class EmergenciaFloraArbolCaido(Base):
    """Flora: árbol caído que obstruye o representa peligro."""

    __tablename__ = "emergencias_flora_arbol_caido"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    reporte_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("reportes_emergencia.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    reporte: Mapped[ReporteEmergencia] = relationship(back_populates="flora_arbol_caido")


class EmergenciaFaunaRescate(Base):
    """Fauna: rescate de animales silvestres heridos o en peligro."""

    __tablename__ = "emergencias_fauna_rescate_animales"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    reporte_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("reportes_emergencia.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    reporte: Mapped[ReporteEmergencia] = relationship(back_populates="fauna_rescate")


class EmergenciaFloraIVCTala(Base):
    """Flora IVC: tala ilegal o no autorizada de árboles."""

    __tablename__ = "emergencias_flora_ivc_tala_arboles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    reporte_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("reportes_emergencia.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    reporte: Mapped[ReporteEmergencia] = relationship(back_populates="flora_ivc_tala")


class EmergenciaHidricaContaminacion(Base):
    """Hídrica: contaminación de ríos, quebradas, humedales u otras fuentes de agua."""

    __tablename__ = "emergencias_hidrica_contaminacion"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    reporte_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("reportes_emergencia.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    reporte: Mapped[ReporteEmergencia] = relationship(back_populates="hidrica_contaminacion")
