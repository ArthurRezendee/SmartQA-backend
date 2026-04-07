"""add refresh token to users

Revision ID: e7f8a9b0c1d2
Revises: c97a63f56521
Create Date: 2026-04-05

"""
from alembic import op
import sqlalchemy as sa

revision = 'e7f8a9b0c1d2'
down_revision = 'c97a63f56521'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('refresh_token', sa.String(64), nullable=True))
    op.add_column('users', sa.Column('refresh_token_expires_at', sa.DateTime(timezone=True), nullable=True))
    op.create_index('ix_users_refresh_token', 'users', ['refresh_token'], unique=True)


def downgrade() -> None:
    op.drop_index('ix_users_refresh_token', table_name='users')
    op.drop_column('users', 'refresh_token_expires_at')
    op.drop_column('users', 'refresh_token')
