"""add language_confirmed_at to citizen_profiles

Revision ID: d8f7e6d5c4b3
Revises: c7e6d5c4b3a2
Create Date: 2026-08-26 23:39:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd8f7e6d5c4b3'
down_revision: Union[str, None] = 'c7e6d5c4b3a2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'citizen_profiles',
        sa.Column('language_confirmed_at', sa.DateTime(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('citizen_profiles', 'language_confirmed_at')
