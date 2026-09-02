"""populate_government_schemes_catalog

Revision ID: 5360c828eb23
Revises: 97fadbd11b95
Create Date: 2026-09-01 22:02:10.371737

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5360c828eb23'
down_revision: Union[str, Sequence[str], None] = '97fadbd11b95'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Safe catalog preparation revision.
    
    Data import is decoupled from DDL migrations and executed explicitly via
    `python -m app.schemes.import_kb --apply` during the service startup sequence.
    This revision was previously failing due to VARCHAR(50) truncation in PostgreSQL
    and was rolled back (leaving production at 97fadbd11b95). Keeping this revision
    as a no-op preserves linear migration history and maintains compatibility across all environments.
    """
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass

