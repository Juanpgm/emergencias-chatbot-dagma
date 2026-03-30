"""refactor_tipos_emergencia_y_tablas_especializadas

Revision ID: 24e6267fa7a5
Revises: aabee4bd2a9d
Create Date: 2026-03-29 16:48:04.029849

Cambios:
- Reemplaza el enum tipo_emergencia_enum por los 4 tipos DAGMA oficiales.
- Agrega columna 'area' a reportes_emergencia.
- Crea las 4 tablas especializadas por tipo de emergencia.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "24e6267fa7a5"
down_revision: Union[str, None] = "aabee4bd2a9d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Valores del enum anterior (para downgrade)
_TIPOS_ANTERIORES = (
    "incendio_forestal", "tala_ilegal", "contaminacion_agua", "contaminacion_aire",
    "vertimiento_residuos", "maltrato_animal", "ruido_excesivo",
    "invasion_zona_protegida", "derrumbe", "inundacion", "otro",
)

# Valores del enum nuevo
_TIPOS_NUEVOS = (
    "arbol_caido",
    "rescate_animales_silvestres",
    "tala_arboles",
    "contaminacion_fuente_hidrica",
)


def upgrade() -> None:
    # ── 1. Vaciar datos de prueba anteriores (cambia el enum) ──────────────────
    op.execute("TRUNCATE TABLE reportes_emergencia RESTART IDENTITY CASCADE")

    # ── 2. Eliminar columna tipo_de_emergencia (usa el enum viejo) ─────────────
    op.drop_column("reportes_emergencia", "tipo_de_emergencia")

    # ── 3. Eliminar enum viejo y crear el nuevo ────────────────────────────────
    op.execute("DROP TYPE IF EXISTS tipo_emergencia_enum")
    op.execute(
        "CREATE TYPE tipo_emergencia_enum AS ENUM ("
        + ", ".join(f"'{v}'" for v in _TIPOS_NUEVOS)
        + ")"
    )

    # ── 4. Agregar columna area y recrear tipo_de_emergencia ───────────────────
    op.add_column(
        "reportes_emergencia",
        sa.Column("area", sa.String(length=20), nullable=False, server_default="flora"),
    )
    # Quitar server_default una vez creada (no queremos default permanente)
    op.alter_column("reportes_emergencia", "area", server_default=None)

    op.add_column(
        "reportes_emergencia",
        sa.Column(
            "tipo_de_emergencia",
            sa.Enum(*_TIPOS_NUEVOS, name="tipo_emergencia_enum", create_constraint=True),
            nullable=False,
            server_default="arbol_caido",
        ),
    )
    op.alter_column("reportes_emergencia", "tipo_de_emergencia", server_default=None)

    # ── 5. Crear tablas especializadas ─────────────────────────────────────────
    op.create_table(
        "emergencias_flora_arbol_caido",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("reporte_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["reporte_id"], ["reportes_emergencia.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "emergencias_fauna_rescate_animales",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("reporte_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["reporte_id"], ["reportes_emergencia.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "emergencias_flora_ivc_tala_arboles",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("reporte_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["reporte_id"], ["reportes_emergencia.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "emergencias_hidrica_contaminacion",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("reporte_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["reporte_id"], ["reportes_emergencia.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    # Eliminar tablas especializadas
    op.drop_table("emergencias_hidrica_contaminacion")
    op.drop_table("emergencias_flora_ivc_tala_arboles")
    op.drop_table("emergencias_fauna_rescate_animales")
    op.drop_table("emergencias_flora_arbol_caido")

    # Revertir columnas en tabla maestra
    op.drop_column("reportes_emergencia", "tipo_de_emergencia")
    op.drop_column("reportes_emergencia", "area")

    op.execute("DROP TYPE IF EXISTS tipo_emergencia_enum")
    op.execute(
        "CREATE TYPE tipo_emergencia_enum AS ENUM ("
        + ", ".join(f"'{v}'" for v in _TIPOS_ANTERIORES)
        + ")"
    )

    op.add_column(
        "reportes_emergencia",
        sa.Column(
            "tipo_de_emergencia",
            sa.Enum(*_TIPOS_ANTERIORES, name="tipo_emergencia_enum", create_constraint=True),
            nullable=False,
            server_default="otro",
        ),
    )
    op.alter_column("reportes_emergencia", "tipo_de_emergencia", server_default=None)
