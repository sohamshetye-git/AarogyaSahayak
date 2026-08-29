"""enhance_referrals_and_followups

Revision ID: a9b8c7d6e5f4
Revises: e8f90a1b2c3d
Create Date: 2026-08-25 06:40:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'a9b8c7d6e5f4'
down_revision: Union[str, Sequence[str], None] = 'e8f90a1b2c3d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Update referrals table
    with op.batch_alter_table('referrals') as batch_op:
        batch_op.add_column(sa.Column('transport_assistance_required', sa.Boolean(), server_default='false', nullable=True))
        batch_op.add_column(sa.Column('citizen_response', sa.String(length=50), server_default='ACCEPTED', nullable=True))
        batch_op.add_column(sa.Column('refusal_reason', sa.Text(), nullable=True))

    # 2. Update follow_ups table
    with op.batch_alter_table('follow_ups') as batch_op:
        batch_op.alter_column('case_id', existing_type=sa.String(length=36), nullable=True)
        batch_op.add_column(sa.Column('citizen_id', sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column('referral_id', sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column('created_by_id', sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column('source', sa.String(length=50), server_default='DOCTOR_ASSIGNED', nullable=True))
        batch_op.add_column(sa.Column('updated_at', sa.DateTime(), nullable=True))

        # Constraints
        batch_op.create_foreign_key('fk_follow_ups_citizen_id_citizen_profiles', 'citizen_profiles', ['citizen_id'], ['id'])
        batch_op.create_foreign_key('fk_follow_ups_referral_id_referrals', 'referrals', ['referral_id'], ['id'])
        batch_op.create_foreign_key('fk_follow_ups_created_by_id_users', 'users', ['created_by_id'], ['id'])

        # Indexes
        batch_op.create_index('ix_follow_ups_citizen_id', ['citizen_id'], unique=False)
        batch_op.create_index('ix_follow_ups_referral_id', ['referral_id'], unique=False)
        batch_op.create_index('ix_follow_ups_created_by_id', ['created_by_id'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('follow_ups') as batch_op:
        batch_op.drop_index('ix_follow_ups_created_by_id')
        batch_op.drop_index('ix_follow_ups_referral_id')
        batch_op.drop_index('ix_follow_ups_citizen_id')
        batch_op.drop_constraint('fk_follow_ups_created_by_id_users', type_='foreignkey')
        batch_op.drop_constraint('fk_follow_ups_referral_id_referrals', type_='foreignkey')
        batch_op.drop_constraint('fk_follow_ups_citizen_id_citizen_profiles', type_='foreignkey')
        batch_op.drop_column('updated_at')
        batch_op.drop_column('source')
        batch_op.drop_column('created_by_id')
        batch_op.drop_column('referral_id')
        batch_op.drop_column('citizen_id')
        batch_op.alter_column('case_id', existing_type=sa.String(length=36), nullable=False)

    with op.batch_alter_table('referrals') as batch_op:
        batch_op.drop_column('refusal_reason')
        batch_op.drop_column('citizen_response')
        batch_op.drop_column('transport_assistance_required')
