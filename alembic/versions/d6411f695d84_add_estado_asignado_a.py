"""add_estado_asignado_a

Revision ID: d6411f695d84
Revises: cdcf3b874e67
Create Date: 2026-06-15 18:43:55.461266
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd6411f695d84'
down_revision: Union[str, None] = 'cdcf3b874e67'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('reportes_emergencia', sa.Column('estado', sa.String(length=20), nullable=False, server_default='pendiente'))
    op.add_column('reportes_emergencia', sa.Column('asignado_a', sa.String(length=255), nullable=True))
    op.alter_column('reportes_emergencia', 'estado', server_default=None)


def downgrade() -> None:
    op.drop_column('reportes_emergencia', 'asignado_a')
    op.drop_column('reportes_emergencia', 'estado')
