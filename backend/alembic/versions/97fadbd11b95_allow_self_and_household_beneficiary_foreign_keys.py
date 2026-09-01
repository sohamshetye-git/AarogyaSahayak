"""allow_self_and_household_beneficiary_foreign_keys

Revision ID: 97fadbd11b95
Revises: 7f96261d677d
Create Date: 2026-09-01 21:18:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '97fadbd11b95'
down_revision: Union[str, Sequence[str], None] = '7f96261d677d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    # 1. sharing_consents: drop foreign key constraint on beneficiary_id if present
    if inspector.has_table('sharing_consents'):
        fks = inspector.get_foreign_keys('sharing_consents')
        for fk in fks:
            if fk.get('referred_table') == 'household_members' and 'beneficiary_id' in fk.get('constrained_columns', []):
                fk_name = fk.get('name')
                if fk_name:
                    op.drop_constraint(fk_name, 'sharing_consents', type_='foreignkey')

    # 2. service_requests: drop foreign key constraint on beneficiary_id if present
    if inspector.has_table('service_requests'):
        fks = inspector.get_foreign_keys('service_requests')
        for fk in fks:
            if fk.get('referred_table') == 'household_members' and 'beneficiary_id' in fk.get('constrained_columns', []):
                fk_name = fk.get('name')
                if fk_name:
                    op.drop_constraint(fk_name, 'service_requests', type_='foreignkey')

    # 3. care_handoffs: drop foreign key constraint on beneficiary_id if present
    if inspector.has_table('care_handoffs'):
        fks = inspector.get_foreign_keys('care_handoffs')
        for fk in fks:
            if fk.get('referred_table') == 'household_members' and 'beneficiary_id' in fk.get('constrained_columns', []):
                fk_name = fk.get('name')
                if fk_name:
                    op.drop_constraint(fk_name, 'care_handoffs', type_='foreignkey')


def downgrade() -> None:
    # We do not re-add restrictive foreign keys on downgrade to prevent breaking Self requests
    pass
