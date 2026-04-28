"""add_stress_test_tables

Adiciona suporte a Stress Test:
- Tabela stress_tests
- Tabela stress_test_findings
- Campo stress_tests_per_month em plans
- Campo stress_tests_used_current_cycle em billing_accounts

Revision ID: c3d4e5f6a7b8
Revises: b1c2d3e4f5a6
Create Date: 2026-04-28 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, None] = 'b1c2d3e4f5a6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Adiciona stress_tests_per_month em plans
    op.add_column(
        'plans',
        sa.Column('stress_tests_per_month', sa.Integer(), nullable=False, server_default='0'),
    )

    # 2. Adiciona stress_tests_used_current_cycle em billing_accounts
    op.add_column(
        'billing_accounts',
        sa.Column('stress_tests_used_current_cycle', sa.Integer(), nullable=False, server_default='0'),
    )

    # 3. Cria enums
    stress_severity_enum = sa.Enum(
        'critical', 'high', 'medium', 'low',
        name='stress_severity_enum',
    )
    stress_category_enum = sa.Enum(
        'crash', 'validation', 'ui_error', 'http_error', 'security', 'functional', 'ux',
        name='stress_category_enum',
    )
    stress_severity_enum.create(op.get_bind(), checkfirst=True)
    stress_category_enum.create(op.get_bind(), checkfirst=True)

    # 4. Cria tabela stress_tests
    op.create_table(
        'stress_tests',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('target_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('owner_type', sa.String(length=20), nullable=False, server_default='user'),
        sa.Column('owner_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('total_findings', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['target_id'], ['targets.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_stress_tests_id', 'stress_tests', ['id'])
    op.create_index('ix_stress_tests_target_id', 'stress_tests', ['target_id'])

    # 5. Cria tabela stress_test_findings
    op.create_table(
        'stress_test_findings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('stress_test_id', sa.Integer(), nullable=False),
        sa.Column('order_index', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('severity', stress_severity_enum, nullable=False, server_default='medium'),
        sa.Column('category', stress_category_enum, nullable=False, server_default='functional'),
        sa.Column('element', sa.Text(), nullable=True),
        sa.Column('input_used', sa.Text(), nullable=True),
        sa.Column('steps_to_reproduce', sa.Text(), nullable=True),
        sa.Column('error_details', sa.Text(), nullable=True),
        sa.Column('screenshot_path', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['stress_test_id'], ['stress_tests.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_stress_test_findings_id', 'stress_test_findings', ['id'])
    op.create_index('ix_stress_test_findings_stress_test_id', 'stress_test_findings', ['stress_test_id'])


def downgrade() -> None:
    op.drop_index('ix_stress_test_findings_stress_test_id', table_name='stress_test_findings')
    op.drop_index('ix_stress_test_findings_id', table_name='stress_test_findings')
    op.drop_table('stress_test_findings')

    op.drop_index('ix_stress_tests_target_id', table_name='stress_tests')
    op.drop_index('ix_stress_tests_id', table_name='stress_tests')
    op.drop_table('stress_tests')

    op.execute("DROP TYPE IF EXISTS stress_severity_enum")
    op.execute("DROP TYPE IF EXISTS stress_category_enum")

    op.drop_column('billing_accounts', 'stress_tests_used_current_cycle')
    op.drop_column('plans', 'stress_tests_per_month')
