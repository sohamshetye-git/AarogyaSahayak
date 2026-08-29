"""add teleconsultation module tables

Revision ID: e9a8b7c6d5e4
Revises: d8f7e6d5c4b3
Create Date: 2026-08-26 23:51:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'e9a8b7c6d5e4'
down_revision: Union[str, None] = 'd8f7e6d5c4b3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. teleconsultation_requests
    op.create_table(
        'teleconsultation_requests',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('public_reference', sa.String(length=50), nullable=False),
        sa.Column('citizen_id', sa.String(length=36), nullable=False),
        sa.Column('household_member_id', sa.String(length=36), nullable=True),
        sa.Column('citizen_need_id', sa.String(length=36), nullable=True),
        sa.Column('service_request_id', sa.String(length=36), nullable=True),
        sa.Column('case_id', sa.String(length=36), nullable=True),
        sa.Column('facility_id', sa.String(length=36), nullable=True),
        sa.Column('assigned_doctor_id', sa.String(length=36), nullable=True),
        sa.Column('consultation_id', sa.String(length=36), nullable=True),
        sa.Column('language_code', sa.String(length=10), nullable=True),
        sa.Column('mode', sa.String(length=50), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=True),
        sa.Column('priority', sa.String(length=30), nullable=True),
        sa.Column('chief_complaint', sa.Text(), nullable=True),
        sa.Column('symptoms', sa.JSON(), nullable=True),
        sa.Column('duration_text', sa.String(length=100), nullable=True),
        sa.Column('severity_level', sa.String(length=50), nullable=True),
        sa.Column('structured_intake', sa.JSON(), nullable=True),
        sa.Column('safety_rule_triggered', sa.Boolean(), nullable=True),
        sa.Column('safety_rule_ids', sa.JSON(), nullable=True),
        sa.Column('safety_reason', sa.Text(), nullable=True),
        sa.Column('queue_position', sa.Integer(), nullable=True),
        sa.Column('estimated_wait_minutes', sa.Integer(), nullable=True),
        sa.Column('scheduled_at', sa.DateTime(), nullable=True),
        sa.Column('submitted_at', sa.DateTime(), nullable=True),
        sa.Column('accepted_at', sa.DateTime(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('cancellation_reason', sa.Text(), nullable=True),
        sa.Column('clinical_notes', sa.Text(), nullable=True),
        sa.Column('disposition', sa.String(length=100), nullable=True),
        sa.Column('patient_guidance', sa.Text(), nullable=True),
        sa.Column('idempotency_key', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('version', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['assigned_doctor_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['case_id'], ['cases.id'], ),
        sa.ForeignKeyConstraint(['citizen_id'], ['citizen_profiles.id'], ),
        sa.ForeignKeyConstraint(['citizen_need_id'], ['citizen_needs.id'], ),
        sa.ForeignKeyConstraint(['consultation_id'], ['consultations.id'], ),
        sa.ForeignKeyConstraint(['facility_id'], ['facilities.id'], ),
        sa.ForeignKeyConstraint(['household_member_id'], ['household_members.id'], ),
        sa.ForeignKeyConstraint(['service_request_id'], ['service_requests.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_teleconsultation_requests_assigned_doctor_id'), 'teleconsultation_requests', ['assigned_doctor_id'], unique=False)
    op.create_index(op.f('ix_teleconsultation_requests_case_id'), 'teleconsultation_requests', ['case_id'], unique=False)
    op.create_index(op.f('ix_teleconsultation_requests_citizen_id'), 'teleconsultation_requests', ['citizen_id'], unique=False)
    op.create_index(op.f('ix_teleconsultation_requests_citizen_need_id'), 'teleconsultation_requests', ['citizen_need_id'], unique=False)
    op.create_index(op.f('ix_teleconsultation_requests_consultation_id'), 'teleconsultation_requests', ['consultation_id'], unique=False)
    op.create_index(op.f('ix_teleconsultation_requests_household_member_id'), 'teleconsultation_requests', ['household_member_id'], unique=False)
    op.create_index(op.f('ix_teleconsultation_requests_idempotency_key'), 'teleconsultation_requests', ['idempotency_key'], unique=True)
    op.create_index(op.f('ix_teleconsultation_requests_public_reference'), 'teleconsultation_requests', ['public_reference'], unique=True)
    op.create_index(op.f('ix_teleconsultation_requests_service_request_id'), 'teleconsultation_requests', ['service_request_id'], unique=False)
    op.create_index(op.f('ix_teleconsultation_requests_status'), 'teleconsultation_requests', ['status'], unique=False)

    # 2. teleconsultation_consents
    op.create_table(
        'teleconsultation_consents',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('request_id', sa.String(length=36), nullable=False),
        sa.Column('share_concern', sa.Boolean(), nullable=True),
        sa.Column('share_medical_history', sa.Boolean(), nullable=True),
        sa.Column('audio_video_consent', sa.Boolean(), nullable=True),
        sa.Column('store_transcript_consent', sa.Boolean(), nullable=True),
        sa.Column('share_location_consent', sa.Boolean(), nullable=True),
        sa.Column('consented_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['request_id'], ['teleconsultation_requests.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_teleconsultation_consents_request_id'), 'teleconsultation_consents', ['request_id'], unique=False)

    # 3. teleconsultation_status_history
    op.create_table(
        'teleconsultation_status_history',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('request_id', sa.String(length=36), nullable=False),
        sa.Column('from_status', sa.String(length=50), nullable=True),
        sa.Column('to_status', sa.String(length=50), nullable=False),
        sa.Column('changed_by_user_id', sa.String(length=36), nullable=True),
        sa.Column('changed_by_role', sa.String(length=50), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['changed_by_user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['request_id'], ['teleconsultation_requests.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_teleconsultation_status_history_request_id'), 'teleconsultation_status_history', ['request_id'], unique=False)

    # 4. teleconsultation_messages
    op.create_table(
        'teleconsultation_messages',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('request_id', sa.String(length=36), nullable=False),
        sa.Column('sender_type', sa.String(length=30), nullable=False),
        sa.Column('sender_id', sa.String(length=36), nullable=True),
        sa.Column('sender_name', sa.String(length=150), nullable=True),
        sa.Column('message_text', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['request_id'], ['teleconsultation_requests.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_teleconsultation_messages_request_id'), 'teleconsultation_messages', ['request_id'], unique=False)

    # 5. teleconsultation_attachments
    op.create_table(
        'teleconsultation_attachments',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('request_id', sa.String(length=36), nullable=False),
        sa.Column('file_name', sa.String(length=255), nullable=False),
        sa.Column('file_url', sa.String(length=500), nullable=False),
        sa.Column('file_type', sa.String(length=50), nullable=True),
        sa.Column('file_size_bytes', sa.Integer(), nullable=True),
        sa.Column('uploaded_by', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['request_id'], ['teleconsultation_requests.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_teleconsultation_attachments_request_id'), 'teleconsultation_attachments', ['request_id'], unique=False)


def downgrade() -> None:
    op.drop_table('teleconsultation_attachments')
    op.drop_table('teleconsultation_messages')
    op.drop_table('teleconsultation_status_history')
    op.drop_table('teleconsultation_consents')
    op.drop_table('teleconsultation_requests')
