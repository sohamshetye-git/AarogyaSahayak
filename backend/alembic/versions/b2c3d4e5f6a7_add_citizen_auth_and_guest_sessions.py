"""add citizen auth and guest sessions

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-08-29 19:35:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'b2c3d4e5f6a7'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # 1. citizen_auth_identities
    op.create_table(
        'citizen_auth_identities',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('user_id', sa.String(length=36), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('phone_normalized', sa.String(length=20), nullable=False),
        sa.Column('phone_hash', sa.String(length=64), nullable=False),
        sa.Column('phone_verified_at', sa.DateTime(), nullable=True),
        sa.Column('provider', sa.String(length=50), server_default='MOCK_SMS', nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True)
    )
    op.create_index('ix_citizen_auth_identities_user_id', 'citizen_auth_identities', ['user_id'], unique=True)
    op.create_index('ix_citizen_auth_identities_phone_normalized', 'citizen_auth_identities', ['phone_normalized'], unique=True)
    op.create_index('ix_citizen_auth_identities_phone_hash', 'citizen_auth_identities', ['phone_hash'], unique=True)

    # 2. otp_challenges
    op.create_table(
        'otp_challenges',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('phone_hash', sa.String(length=64), nullable=False),
        sa.Column('otp_hash', sa.String(length=128), nullable=False),
        sa.Column('attempts', sa.Integer(), server_default='0', nullable=False),
        sa.Column('max_attempts', sa.Integer(), server_default='5', nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('consumed_at', sa.DateTime(), nullable=True),
        sa.Column('ip_address', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True)
    )
    op.create_index('ix_otp_challenges_phone_hash', 'otp_challenges', ['phone_hash'])
    op.create_index('ix_otp_challenges_expires_at', 'otp_challenges', ['expires_at'])

    # 3. auth_sessions
    op.create_table(
        'auth_sessions',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('user_id', sa.String(length=36), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('refresh_token_hash', sa.String(length=128), nullable=False),
        sa.Column('device_id', sa.String(length=100), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('revoked_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True)
    )
    op.create_index('ix_auth_sessions_user_id', 'auth_sessions', ['user_id'])
    op.create_index('ix_auth_sessions_refresh_token_hash', 'auth_sessions', ['refresh_token_hash'])

    # 4. guest_sessions
    op.create_table(
        'guest_sessions',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('locale', sa.String(length=10), server_default='mr-IN', nullable=True),
        sa.Column('device_session_hash', sa.String(length=64), nullable=True),
        sa.Column('intended_action', sa.JSON(), nullable=True),
        sa.Column('context_data', sa.JSON(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('migrated_to_user_id', sa.String(length=36), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('migrated_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True)
    )
    op.create_index('ix_guest_sessions_device_session_hash', 'guest_sessions', ['device_session_hash'])
    op.create_index('ix_guest_sessions_expires_at', 'guest_sessions', ['expires_at'])
    op.create_index('ix_guest_sessions_migrated_to_user_id', 'guest_sessions', ['migrated_to_user_id'])

    # 5. guest_session_migrations
    op.create_table(
        'guest_session_migrations',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('guest_session_id', sa.String(length=36), sa.ForeignKey('guest_sessions.id'), nullable=False),
        sa.Column('user_id', sa.String(length=36), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('migration_status', sa.String(length=30), server_default='COMPLETED', nullable=False),
        sa.Column('idempotency_key', sa.String(length=100), nullable=False),
        sa.Column('migrated_entities', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True)
    )
    op.create_index('ix_guest_session_migrations_guest_session_id', 'guest_session_migrations', ['guest_session_id'])
    op.create_index('ix_guest_session_migrations_user_id', 'guest_session_migrations', ['user_id'])
    op.create_index('ix_guest_session_migrations_idempotency_key', 'guest_session_migrations', ['idempotency_key'], unique=True)


def downgrade() -> None:
    op.drop_table('guest_session_migrations')
    op.drop_table('guest_sessions')
    op.drop_table('auth_sessions')
    op.drop_table('otp_challenges')
    op.drop_table('citizen_auth_identities')
