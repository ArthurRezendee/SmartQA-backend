"""add deleted_at to screens and targets

Revision ID: a9b0c1d2e3f4
Revises: e7f8a9b0c1d2
Create Date: 2026-04-06

"""
from alembic import op
import sqlalchemy as sa

revision = 'a9b0c1d2e3f4'
down_revision = 'e7f8a9b0c1d2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('screens', sa.Column('deleted_at', sa.DateTime(), nullable=True))
    op.add_column('targets', sa.Column('deleted_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column('targets', 'deleted_at')
    op.drop_column('screens', 'deleted_at')
