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
    # No-op: la columna geom ya no se crea en la migración inicial,
    # por lo que no hay nada que eliminar.
    pass


def downgrade() -> None:
    # No se restaura geom en downgrade (requeriría PostGIS instalado)
    pass
