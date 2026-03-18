"""add_analysis_jobs_table

Revision ID: d3e4f5a6b7c8
Revises: 0f163115d8f0
Create Date: 2026-03-18 04:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd3e4f5a6b7c8'
down_revision: Union[str, Sequence[str], None] = '0f163115d8f0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'analysis_jobs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('qa_analysis_id', sa.Integer(), nullable=False),
        sa.Column('job_type', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['qa_analysis_id'], ['qa_analyses.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_analysis_jobs_qa_analysis_id', 'analysis_jobs', ['qa_analysis_id'])
    op.create_index('ix_analysis_jobs_status', 'analysis_jobs', ['status'])


def downgrade() -> None:
    op.drop_index('ix_analysis_jobs_status', table_name='analysis_jobs')
    op.drop_index('ix_analysis_jobs_qa_analysis_id', table_name='analysis_jobs')
    op.drop_table('analysis_jobs')
