"""mudadncas_access_credentials

Revision ID: c97a63f56521
Revises: 2603b9df6ff0
Create Date: 2026-04-03 05:32:35.250733

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c97a63f56521'
down_revision: Union[str, Sequence[str], None] = '2603b9df6ff0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # No-op: changes already applied by f1a2b3c4d5e6_refactor_screen_target_separation
    pass


def downgrade() -> None:
    """Downgrade schema."""
    # No-op: see upgrade
    pass
