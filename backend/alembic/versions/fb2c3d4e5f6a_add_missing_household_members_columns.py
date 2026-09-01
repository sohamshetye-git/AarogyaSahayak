"""add missing columns to household_members

Revision ID: fb2c3d4e5f6a
Revises: ea1b2c3d4e5f
Create Date: 2026-09-01 19:47:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fb2c3d4e5f6a'
down_revision: Union[str, Sequence[str], None] = 'ea1b2c3d4e5f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_columns = {col['name'] for col in inspector.get_columns('household_members')}

    # 1. is_active (non-nullable boolean, backfilled to True, server_default dropped)
    if 'is_active' not in existing_columns:
        op.add_column(
            'household_members',
            sa.Column(
                'is_active',
                sa.Boolean(),
                nullable=False,
                server_default=sa.true(),
            )
        )
        # Remove server_default so application-level defaults apply
        op.alter_column('household_members', 'is_active', server_default=None)

    # 2. linked_citizen_profile_id (nullable string(36) with foreign key and index)
    if 'linked_citizen_profile_id' not in existing_columns:
        op.add_column(
            'household_members',
            sa.Column('linked_citizen_profile_id', sa.String(length=36), nullable=True)
        )
        op.create_foreign_key(
            'fk_household_members_linked_citizen_profile_id',
            'household_members',
            'citizen_profiles',
            ['linked_citizen_profile_id'],
            ['id']
        )
        op.create_index(
            op.f('ix_household_members_linked_citizen_profile_id'),
            'household_members',
            ['linked_citizen_profile_id'],
            unique=False
        )

    # 3. phone (nullable string(20))
    if 'phone' not in existing_columns:
        op.add_column(
            'household_members',
            sa.Column('phone', sa.String(length=20), nullable=True)
        )

    # 4. abha_reference (nullable string(50))
    if 'abha_reference' not in existing_columns:
        op.add_column(
            'household_members',
            sa.Column('abha_reference', sa.String(length=50), nullable=True)
        )

    # 5. health_notes (nullable text)
    if 'health_notes' not in existing_columns:
        op.add_column(
            'household_members',
            sa.Column('health_notes', sa.Text(), nullable=True)
        )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_columns = {col['name'] for col in inspector.get_columns('household_members')}
    existing_indexes = {idx['name'] for idx in inspector.get_indexes('household_members')}
    existing_fks = {fk['name'] for fk in inspector.get_foreign_keys('household_members')}

    if 'health_notes' in existing_columns:
        op.drop_column('household_members', 'health_notes')

    if 'abha_reference' in existing_columns:
        op.drop_column('household_members', 'abha_reference')

    if 'phone' in existing_columns:
        op.drop_column('household_members', 'phone')

    if 'ix_household_members_linked_citizen_profile_id' in existing_indexes:
        op.drop_index(op.f('ix_household_members_linked_citizen_profile_id'), table_name='household_members')

    if 'fk_household_members_linked_citizen_profile_id' in existing_fks:
        op.drop_constraint('fk_household_members_linked_citizen_profile_id', 'household_members', type_='foreignkey')

    if 'linked_citizen_profile_id' in existing_columns:
        op.drop_column('household_members', 'linked_citizen_profile_id')

    if 'is_active' in existing_columns:
        op.drop_column('household_members', 'is_active')
