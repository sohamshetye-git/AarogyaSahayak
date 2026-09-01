"""create doctor chat tables

Revision ID: ea1b2c3d4e5f
Revises: b2c3d4e5f6a7, d9e8f7a6b5c4
Create Date: 2026-08-31 19:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'ea1b2c3d4e5f'
down_revision: Union[str, Sequence[str], None] = 'd9e8f7a6b5c4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = set(inspector.get_table_names())

    if 'doctor_chat_threads' not in tables:
        op.create_table(
            'doctor_chat_threads',
            sa.Column('id', sa.String(length=36), primary_key=True),
            sa.Column('service_request_id', sa.String(length=36), sa.ForeignKey('service_requests.id'), nullable=False),
            sa.Column('citizen_id', sa.String(length=36), sa.ForeignKey('citizen_profiles.id'), nullable=False),
            sa.Column('doctor_id', sa.String(length=36), sa.ForeignKey('users.id'), nullable=True),
            sa.Column('facility_id', sa.String(length=36), sa.ForeignKey('facilities.id'), nullable=False, server_default='PHC-09'),
            sa.Column('channel', sa.String(length=30), nullable=False, server_default='DOCTOR_CHAT'),
            sa.Column('status', sa.String(length=30), nullable=False, server_default='WAITING_FOR_DOCTOR'),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
        )
        op.create_index('ix_doctor_chat_threads_service_request_id', 'doctor_chat_threads', ['service_request_id'], unique=True)
        op.create_index('ix_doctor_chat_threads_citizen_id', 'doctor_chat_threads', ['citizen_id'], unique=False)
        op.create_index('ix_doctor_chat_threads_doctor_id', 'doctor_chat_threads', ['doctor_id'], unique=False)
        op.create_index('ix_doctor_chat_threads_status', 'doctor_chat_threads', ['status'], unique=False)

    if 'doctor_chat_messages' not in tables:
        op.create_table(
            'doctor_chat_messages',
            sa.Column('id', sa.String(length=36), primary_key=True),
            sa.Column('conversation_id', sa.String(length=36), sa.ForeignKey('doctor_chat_threads.id'), nullable=False),
            sa.Column('service_request_id', sa.String(length=36), sa.ForeignKey('service_requests.id'), nullable=True),
            sa.Column('sender_role', sa.String(length=30), nullable=False, server_default='CITIZEN'),
            sa.Column('sender_id', sa.String(length=36), nullable=True),
            sa.Column('sender_name', sa.String(length=150), nullable=True),
            sa.Column('body', sa.Text(), nullable=False),
            sa.Column('client_message_id', sa.String(length=100), nullable=False),
            sa.Column('status', sa.String(length=30), nullable=False, server_default='SENT'),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('delivered_at', sa.DateTime(), nullable=True),
            sa.Column('read_at', sa.DateTime(), nullable=True),
        )
        op.create_index('ix_doctor_chat_messages_conversation_id', 'doctor_chat_messages', ['conversation_id'], unique=False)
        op.create_index('ix_doctor_chat_messages_service_request_id', 'doctor_chat_messages', ['service_request_id'], unique=False)
        op.create_index('ix_doctor_chat_messages_sender_id', 'doctor_chat_messages', ['sender_id'], unique=False)
        op.create_index('ix_doctor_chat_messages_client_message_id', 'doctor_chat_messages', ['client_message_id'], unique=True)
        op.create_index('ix_doctor_chat_messages_created_at', 'doctor_chat_messages', ['created_at'], unique=False)


def downgrade() -> None:
    op.drop_table('doctor_chat_messages')
    op.drop_table('doctor_chat_threads')
