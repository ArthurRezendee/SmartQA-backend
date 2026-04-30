"""add_element_map_to_stress_tests

Adiciona element_map e worker_batches à tabela stress_tests
para suportar a arquitetura Orquestrador → Workers → Agregador.

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-04-30 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'stress_tests',
        sa.Column('element_map', sa.Text(), nullable=True),
    )
    op.add_column(
        'stress_tests',
        sa.Column('worker_batches', sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('stress_tests', 'worker_batches')
    op.drop_column('stress_tests', 'element_map')
