"""add_stress_test_steps

Adiciona tabela stress_test_steps para rastreabilidade completa de cada
ataque executado durante o stress test. Steps com result='bug' referenciam
o finding correspondente via finding_id.

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-04-30 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'e5f6a7b8c9d0'
down_revision: Union[str, None] = 'd4e5f6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'stress_test_steps',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('stress_test_id', sa.Integer(), nullable=False),
        sa.Column('worker_id', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('element_label', sa.String(length=255), nullable=False),
        sa.Column('element_kind', sa.String(length=50), nullable=True),
        sa.Column('field_type', sa.String(length=50), nullable=True),
        sa.Column('attack_key', sa.String(length=50), nullable=True),
        sa.Column('attack_description', sa.Text(), nullable=True),
        # ok | bug | skipped
        sa.Column('result', sa.String(length=20), nullable=False, server_default='ok'),
        sa.Column('finding_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['stress_test_id'], ['stress_tests.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['finding_id'], ['stress_test_findings.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_stress_test_steps_id', 'stress_test_steps', ['id'])
    op.create_index('ix_stress_test_steps_stress_test_id', 'stress_test_steps', ['stress_test_id'])
    op.create_index('ix_stress_test_steps_finding_id', 'stress_test_steps', ['finding_id'])


def downgrade() -> None:
    op.drop_index('ix_stress_test_steps_finding_id', table_name='stress_test_steps')
    op.drop_index('ix_stress_test_steps_stress_test_id', table_name='stress_test_steps')
    op.drop_index('ix_stress_test_steps_id', table_name='stress_test_steps')
    op.drop_table('stress_test_steps')
