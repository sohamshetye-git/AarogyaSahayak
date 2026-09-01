"""enhance teleconsultation messages schema for live chat

Revision ID: d9e8f7a6b5c4
Revises: 68c9fdcc90e2
Create Date: 2026-08-31 18:45:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'd9e8f7a6b5c4'
down_revision: Union[str, None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new columns to teleconsultation_messages if not existing
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_cols = {col["name"] for col in inspector.get_columns('teleconsultation_messages')} if inspector.has_table('teleconsultation_messages') else set()

    if 'conversation_id' not in existing_cols:
        op.add_column('teleconsultation_messages', sa.Column('conversation_id', sa.String(length=36), nullable=True))
        op.create_index('ix_teleconsultation_messages_conversation_id', 'teleconsultation_messages', ['conversation_id'], unique=False)

    if 'service_request_id' not in existing_cols:
        op.add_column('teleconsultation_messages', sa.Column('service_request_id', sa.String(length=36), nullable=True))
        op.create_index('ix_teleconsultation_messages_service_request_id', 'teleconsultation_messages', ['service_request_id'], unique=False)

    if 'sender_user_id' not in existing_cols:
        op.add_column('teleconsultation_messages', sa.Column('sender_user_id', sa.String(length=36), nullable=True))
        op.create_index('ix_teleconsultation_messages_sender_user_id', 'teleconsultation_messages', ['sender_user_id'], unique=False)

    if 'sender_role' not in existing_cols:
        op.add_column('teleconsultation_messages', sa.Column('sender_role', sa.String(length=30), nullable=True, server_default='CITIZEN'))

    if 'message_type' not in existing_cols:
        op.add_column('teleconsultation_messages', sa.Column('message_type', sa.String(length=30), nullable=True, server_default='TEXT'))

    if 'body' not in existing_cols:
        op.add_column('teleconsultation_messages', sa.Column('body', sa.Text(), nullable=True))

    if 'client_message_id' not in existing_cols:
        op.add_column('teleconsultation_messages', sa.Column('client_message_id', sa.String(length=100), nullable=True))
        op.create_index('ix_teleconsultation_messages_client_message_id', 'teleconsultation_messages', ['client_message_id'], unique=True)

    if 'status' not in existing_cols:
        op.add_column('teleconsultation_messages', sa.Column('status', sa.String(length=30), nullable=True, server_default='SENT'))

    if 'delivered_at' not in existing_cols:
        op.add_column('teleconsultation_messages', sa.Column('delivered_at', sa.DateTime(), nullable=True))

    if 'read_at' not in existing_cols:
        op.add_column('teleconsultation_messages', sa.Column('read_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_index('ix_teleconsultation_messages_client_message_id', table_name='teleconsultation_messages')
    op.drop_index('ix_teleconsultation_messages_sender_user_id', table_name='teleconsultation_messages')
    op.drop_index('ix_teleconsultation_messages_service_request_id', table_name='teleconsultation_messages')
    op.drop_index('ix_teleconsultation_messages_conversation_id', table_name='teleconsultation_messages')
    op.drop_column('teleconsultation_messages', 'read_at')
    op.drop_column('teleconsultation_messages', 'delivered_at')
    op.drop_column('teleconsultation_messages', 'status')
    op.drop_column('teleconsultation_messages', 'client_message_id')
    op.drop_column('teleconsultation_messages', 'body')
    op.drop_column('teleconsultation_messages', 'message_type')
    op.drop_column('teleconsultation_messages', 'sender_role')
    op.drop_column('teleconsultation_messages', 'sender_user_id')
    op.drop_column('teleconsultation_messages', 'service_request_id')
    op.drop_column('teleconsultation_messages', 'conversation_id')
