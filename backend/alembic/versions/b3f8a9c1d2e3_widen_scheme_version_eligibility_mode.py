"""widen_scheme_version_eligibility_mode

Revision ID: b3f8a9c1d2e3
Revises: 5360c828eb23
Create Date: 2026-09-02 07:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b3f8a9c1d2e3'
down_revision: Union[str, Sequence[str], None] = '5360c828eb23'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Widen scheme_versions.eligibility_mode to VARCHAR(128) to support canonical composite eligibility modes
    # e.g., 'STATE_RESIDENCE_RELEVANCE_PLUS_OFFICIAL_VERIFICATION' (len 52)
    # and 'DETERMINISTIC_PRESCREEN_PLUS_RCH_FACILITY_VERIFICATION' (len 54)
    with op.batch_alter_table('scheme_versions') as batch_op:
        batch_op.alter_column(
            'eligibility_mode',
            existing_type=sa.String(length=50),
            type_=sa.String(length=128),
            existing_nullable=False,
            existing_server_default='DETERMINISTIC_RULES'
        )


def downgrade() -> None:
    with op.batch_alter_table('scheme_versions') as batch_op:
        batch_op.alter_column(
            'eligibility_mode',
            existing_type=sa.String(length=128),
            type_=sa.String(length=50),
            existing_nullable=False,
            existing_server_default='DETERMINISTIC_RULES'
        )

