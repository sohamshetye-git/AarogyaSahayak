"""add_staff_management_and_password_policy

Revision ID: c1a2b3d4e5f6
Revises: b3f8a9c1d2e3
Create Date: 2026-09-04 05:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c1a2b3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'b3f8a9c1d2e3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Update users table
    with op.batch_alter_table('users') as batch_op:
        batch_op.add_column(sa.Column('account_status', sa.String(length=50), nullable=True, server_default='ACTIVE'))
        batch_op.add_column(sa.Column('staff_id', sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column('must_change_password', sa.Boolean(), nullable=True, server_default=sa.text('false')))
        batch_op.add_column(sa.Column('created_by_admin_id', sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column('last_login_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('password_changed_at', sa.DateTime(), nullable=True))
        batch_op.create_index(batch_op.f('ix_users_staff_id'), ['staff_id'], unique=True)
        batch_op.create_foreign_key('fk_users_created_by_admin_id', 'users', ['created_by_admin_id'], ['id'])

    # 2. Update worker_profiles table
    with op.batch_alter_table('worker_profiles') as batch_op:
        batch_op.add_column(sa.Column('village_name', sa.String(length=150), nullable=True))
        batch_op.add_column(sa.Column('coverage_area', sa.String(length=200), nullable=True))
        batch_op.add_column(sa.Column('employee_id', sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column('specialization', sa.String(length=100), nullable=True))
        batch_op.create_index(batch_op.f('ix_worker_profiles_employee_id'), ['employee_id'], unique=True)


def downgrade() -> None:
    with op.batch_alter_table('worker_profiles') as batch_op:
        batch_op.drop_index(batch_op.f('ix_worker_profiles_employee_id'))
        batch_op.drop_column('specialization')
        batch_op.drop_column('employee_id')
        batch_op.drop_column('coverage_area')
        batch_op.drop_column('village_name')

    with op.batch_alter_table('users') as batch_op:
        batch_op.drop_constraint('fk_users_created_by_admin_id', type_='foreignkey')
        batch_op.drop_index(batch_op.f('ix_users_staff_id'))
        batch_op.drop_column('password_changed_at')
        batch_op.drop_column('last_login_at')
        batch_op.drop_column('created_by_admin_id')
        batch_op.drop_column('must_change_password')
        batch_op.drop_column('staff_id')
        batch_op.drop_column('account_status')
