"""enhance_idempotency_records

Revision ID: c8d7e6f5a4b3
Revises: 4bc3e9a23653
Create Date: 2026-08-24 11:55:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c8d7e6f5a4b3'
down_revision: Union[str, None] = '4bc3e9a23653'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new audit & payload integrity columns
    op.add_column('idempotency_records', sa.Column('user_id', sa.String(length=36), nullable=True))
    op.add_column('idempotency_records', sa.Column('http_method', sa.String(length=10), server_default='POST', nullable=False))
    op.add_column('idempotency_records', sa.Column('operation', sa.String(length=100), nullable=True))
    op.add_column('idempotency_records', sa.Column('payload_hash', sa.String(length=64), nullable=True))
    op.add_column('idempotency_records', sa.Column('resource_type', sa.String(length=50), nullable=True))
    op.add_column('idempotency_records', sa.Column('resource_id', sa.String(length=100), nullable=True))
    op.add_column('idempotency_records', sa.Column('updated_at', sa.DateTime(), nullable=True))
    
    op.create_index(op.f('ix_idempotency_records_user_id'), 'idempotency_records', ['user_id'], unique=False)
    op.create_index(op.f('ix_idempotency_records_payload_hash'), 'idempotency_records', ['payload_hash'], unique=False)
    op.create_foreign_key('fk_idempotency_records_user_id_users', 'idempotency_records', 'users', ['user_id'], ['id'])


def downgrade() -> None:
    op.drop_constraint('fk_idempotency_records_user_id_users', 'idempotency_records', type_='foreignkey')
    op.drop_index(op.f('ix_idempotency_records_payload_hash'), table_name='idempotency_records')
    op.drop_index(op.f('ix_idempotency_records_user_id'), table_name='idempotency_records')
    op.drop_column('idempotency_records', 'updated_at')
    op.drop_column('idempotency_records', 'resource_id')
    op.drop_column('idempotency_records', 'resource_type')
    op.drop_column('idempotency_records', 'payload_hash')
    op.drop_column('idempotency_records', 'operation')
    op.drop_column('idempotency_records', 'http_method')
    op.drop_column('idempotency_records', 'user_id')
