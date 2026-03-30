"""remove_postgis_geom_column

Revision ID: cdcf3b874e67
Revises: 24e6267fa7a5
Create Date: 2026-03-29 18:38:15.783448
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = 'cdcf3b874e67'
down_revision: Union[str, None] = '24e6267fa7a5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Eliminar columna geom si existe (solo existe en entornos con PostGIS como Docker local)
    conn = op.get_bind()
    result = conn.execute(text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name='reportes_emergencia' AND column_name='geom'"
    ))
    if result.fetchone():
        op.drop_column("reportes_emergencia", "geom")


def downgrade() -> None:
    # No se restaura geom en downgrade (requeriría PostGIS instalado)
    pass
