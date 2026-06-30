"""canonical_estados_backfill

Revision ID: e853e398199d
Revises: 5e9056de68eb
Create Date: 2026-06-22 23:45:09.476404
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e853e398199d'
down_revision: Union[str, None] = '5e9056de68eb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("UPDATE reportes_emergencia SET estado='informada' WHERE estado IN ('pendiente', 'en_curso')")
    op.execute("UPDATE reportes_emergencia SET estado='resuelta'  WHERE estado='resuelto'")
    op.execute("UPDATE reportes_emergencia SET estado='cancelada' WHERE estado='cancelado'")


def downgrade() -> None:
    op.execute("UPDATE reportes_emergencia SET estado='pendiente' WHERE estado='informada'")
    op.execute("UPDATE reportes_emergencia SET estado='en_curso'  WHERE estado IN ('asignada', 'en_proceso')")
    op.execute("UPDATE reportes_emergencia SET estado='resuelto'  WHERE estado='resuelta'")
    op.execute("UPDATE reportes_emergencia SET estado='cancelado' WHERE estado='cancelada'")
