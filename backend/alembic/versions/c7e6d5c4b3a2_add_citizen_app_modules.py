"""add citizen app modules

Revision ID: c7e6d5c4b3a2
Revises: 68c9fdcc90e2
Create Date: 2026-08-26 23:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'c7e6d5c4b3a2'
down_revision: Union[str, Sequence[str], None] = '68c9fdcc90e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. household_members
    op.create_table(
        'household_members',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('citizen_id', sa.String(length=36), nullable=False),
        sa.Column('full_name', sa.String(length=150), nullable=False),
        sa.Column('relationship_type', sa.String(length=50), nullable=False),
        sa.Column('age', sa.Integer(), nullable=True),
        sa.Column('sex', sa.String(length=20), nullable=True),
        sa.Column('is_pregnant', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('gestational_weeks', sa.Integer(), nullable=True),
        sa.Column('blood_group', sa.String(length=10), nullable=True),
        sa.Column('chronic_conditions', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['citizen_id'], ['citizen_profiles.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_household_members_citizen_id'), 'household_members', ['citizen_id'], unique=False)

    # 2. citizen_chat_sessions
    op.create_table(
        'citizen_chat_sessions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('session_reference', sa.String(length=50), nullable=False),
        sa.Column('citizen_id', sa.String(length=36), nullable=False),
        sa.Column('person_affected_id', sa.String(length=36), nullable=True),
        sa.Column('preferred_language', sa.String(length=10), nullable=True, server_default='mr-IN'),
        sa.Column('detected_language', sa.String(length=10), nullable=True, server_default='mr-IN'),
        sa.Column('channel', sa.String(length=20), nullable=True, server_default='VOICE'),
        sa.Column('current_state', sa.String(length=50), nullable=True, server_default='STARTED'),
        sa.Column('primary_intent', sa.String(length=100), nullable=True),
        sa.Column('status', sa.String(length=30), nullable=True, server_default='ACTIVE'),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('last_activity_at', sa.DateTime(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('linked_need_id', sa.String(length=36), nullable=True),
        sa.Column('linked_case_id', sa.String(length=36), nullable=True),
        sa.Column('consent_status', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('device_id', sa.String(length=100), nullable=True),
        sa.Column('offline_created', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('sync_status', sa.String(length=30), nullable=True, server_default='SYNCED'),
        sa.ForeignKeyConstraint(['citizen_id'], ['citizen_profiles.id'], ),
        sa.ForeignKeyConstraint(['person_affected_id'], ['household_members.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_citizen_chat_sessions_session_reference'), 'citizen_chat_sessions', ['session_reference'], unique=True)
    op.create_index(op.f('ix_citizen_chat_sessions_citizen_id'), 'citizen_chat_sessions', ['citizen_id'], unique=False)
    op.create_index(op.f('ix_citizen_chat_sessions_current_state'), 'citizen_chat_sessions', ['current_state'], unique=False)
    op.create_index(op.f('ix_citizen_chat_sessions_status'), 'citizen_chat_sessions', ['status'], unique=False)

    # 3. citizen_chat_messages
    op.create_table(
        'citizen_chat_messages',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('session_id', sa.String(length=36), nullable=False),
        sa.Column('sequence_number', sa.Integer(), nullable=True, server_default='1'),
        sa.Column('sender', sa.String(length=20), nullable=False),
        sa.Column('input_type', sa.String(length=20), nullable=True, server_default='TEXT'),
        sa.Column('original_text', sa.Text(), nullable=True),
        sa.Column('confirmed_text', sa.Text(), nullable=True),
        sa.Column('translated_text', sa.Text(), nullable=True),
        sa.Column('language', sa.String(length=10), nullable=True, server_default='mr-IN'),
        sa.Column('message_type', sa.String(length=50), nullable=True, server_default='TEXT'),
        sa.Column('structured_payload', sa.JSON(), nullable=True),
        sa.Column('confirmation_status', sa.String(length=30), nullable=True, server_default='CONFIRMED'),
        sa.Column('model_provider', sa.String(length=50), nullable=True),
        sa.Column('model_name', sa.String(length=50), nullable=True),
        sa.Column('prompt_version', sa.String(length=20), nullable=True),
        sa.Column('temporary_audio_reference', sa.String(length=255), nullable=True),
        sa.Column('audio_consent_at', sa.DateTime(), nullable=True),
        sa.Column('transcription_provider', sa.String(length=50), nullable=True),
        sa.Column('transcription_confidence', sa.Float(), nullable=True),
        sa.Column('audio_deleted_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['citizen_chat_sessions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_citizen_chat_messages_session_id'), 'citizen_chat_messages', ['session_id'], unique=False)

    # 4. citizen_needs
    op.create_table(
        'citizen_needs',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('need_reference', sa.String(length=50), nullable=False),
        sa.Column('session_id', sa.String(length=36), nullable=True),
        sa.Column('citizen_id', sa.String(length=36), nullable=False),
        sa.Column('person_affected_id', sa.String(length=36), nullable=True),
        sa.Column('primary_intent', sa.String(length=100), nullable=False),
        sa.Column('secondary_intents', sa.JSON(), nullable=True),
        sa.Column('requested_service', sa.String(length=100), nullable=True),
        sa.Column('detected_language', sa.String(length=10), nullable=True, server_default='mr-IN'),
        sa.Column('confirmed_summary', sa.Text(), nullable=False),
        sa.Column('location', sa.JSON(), nullable=True),
        sa.Column('special_context', sa.String(length=50), nullable=True, server_default='GENERAL'),
        sa.Column('urgency', sa.String(length=30), nullable=True, server_default='ROUTINE'),
        sa.Column('safety_result_id', sa.String(length=36), nullable=True),
        sa.Column('status', sa.String(length=30), nullable=True, server_default='CONFIRMED'),
        sa.Column('citizen_confirmed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['citizen_chat_sessions.id'], ),
        sa.ForeignKeyConstraint(['citizen_id'], ['citizen_profiles.id'], ),
        sa.ForeignKeyConstraint(['person_affected_id'], ['household_members.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_citizen_needs_need_reference'), 'citizen_needs', ['need_reference'], unique=True)
    op.create_index(op.f('ix_citizen_needs_citizen_id'), 'citizen_needs', ['citizen_id'], unique=False)
    op.create_index(op.f('ix_citizen_needs_session_id'), 'citizen_needs', ['session_id'], unique=False)

    # 5. service_requests
    op.create_table(
        'service_requests',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('request_reference', sa.String(length=50), nullable=False),
        sa.Column('citizen_id', sa.String(length=36), nullable=False),
        sa.Column('need_id', sa.String(length=36), nullable=True),
        sa.Column('case_id', sa.String(length=36), nullable=True),
        sa.Column('request_type', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=30), nullable=True, server_default='PENDING'),
        sa.Column('priority', sa.String(length=30), nullable=True, server_default='ROUTINE'),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('assigned_worker_id', sa.String(length=36), nullable=True),
        sa.Column('assigned_facility_id', sa.String(length=36), nullable=True),
        sa.Column('idempotency_key', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['citizen_id'], ['citizen_profiles.id'], ),
        sa.ForeignKeyConstraint(['need_id'], ['citizen_needs.id'], ),
        sa.ForeignKeyConstraint(['case_id'], ['cases.id'], ),
        sa.ForeignKeyConstraint(['assigned_worker_id'], ['worker_profiles.id'], ),
        sa.ForeignKeyConstraint(['assigned_facility_id'], ['facilities.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_service_requests_request_reference'), 'service_requests', ['request_reference'], unique=True)
    op.create_index(op.f('ix_service_requests_citizen_id'), 'service_requests', ['citizen_id'], unique=False)
    op.create_index(op.f('ix_service_requests_need_id'), 'service_requests', ['need_id'], unique=False)
    op.create_index(op.f('ix_service_requests_case_id'), 'service_requests', ['case_id'], unique=False)
    op.create_index(op.f('ix_service_requests_status'), 'service_requests', ['status'], unique=False)
    op.create_index(op.f('ix_service_requests_idempotency_key'), 'service_requests', ['idempotency_key'], unique=True)


def downgrade() -> None:
    op.drop_table('service_requests')
    op.drop_table('citizen_needs')
    op.drop_table('citizen_chat_messages')
    op.drop_table('citizen_chat_sessions')
    op.drop_table('household_members')
