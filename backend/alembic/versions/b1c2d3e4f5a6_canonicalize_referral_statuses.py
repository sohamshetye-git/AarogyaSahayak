"""canonicalize_referral_statuses

Revision ID: b1c2d3e4f5a6
Revises: 96cf257187ef
Create Date: 2026-08-26 13:36:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'b1c2d3e4f5a6'
down_revision: Union[str, Sequence[str], None] = '96cf257187ef'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.execute("UPDATE referrals SET status = 'PROCESSED' WHERE status IN ('CONSULTED', 'COMPLETED')")
    op.execute("UPDATE referrals SET status = 'DOCTOR_ACKNOWLEDGED' WHERE status IN ('ACKNOWLEDGED', 'AWAITING_INVESTIGATION')")
    op.execute("UPDATE referrals SET status = 'PENDING_DOCTOR_REVIEW' WHERE status IN ('REFERRED_TO_PHC', 'NEW')")

def downgrade() -> None:
    pass
