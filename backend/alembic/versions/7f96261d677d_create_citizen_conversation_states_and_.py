"""create_citizen_conversation_states_and_sync_columns

Revision ID: 7f96261d677d
Revises: fb2c3d4e5f6a
Create Date: 2026-09-01 20:37:49.486106

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7f96261d677d'
down_revision: Union[str, Sequence[str], None] = 'fb2c3d4e5f6a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    # 1. citizen_chat_sessions missing columns
    if inspector.has_table('citizen_chat_sessions'):
        sess_cols = {col['name'] for col in inspector.get_columns('citizen_chat_sessions')}
        if 'current_question_id' not in sess_cols:
            op.add_column('citizen_chat_sessions', sa.Column('current_question_id', sa.String(length=100), nullable=True))
        if 'awaiting_answer' not in sess_cols:
            op.add_column('citizen_chat_sessions', sa.Column('awaiting_answer', sa.Boolean(), nullable=True, server_default='false'))
        if 'conversation_stage' not in sess_cols:
            op.add_column('citizen_chat_sessions', sa.Column('conversation_stage', sa.String(length=50), nullable=True, server_default='INITIAL'))
        if 'current_topic' not in sess_cols:
            op.add_column('citizen_chat_sessions', sa.Column('current_topic', sa.String(length=100), nullable=True))
        if 'previous_topic' not in sess_cols:
            op.add_column('citizen_chat_sessions', sa.Column('previous_topic', sa.String(length=100), nullable=True))
        if 'last_assistant_question' not in sess_cols:
            op.add_column('citizen_chat_sessions', sa.Column('last_assistant_question', sa.Text(), nullable=True))
        if 'last_intent' not in sess_cols:
            op.add_column('citizen_chat_sessions', sa.Column('last_intent', sa.String(length=100), nullable=True))
        if 'context_transition' not in sess_cols:
            op.add_column('citizen_chat_sessions', sa.Column('context_transition', sa.String(length=100), nullable=True))
        if 'context_state' not in sess_cols:
            op.add_column('citizen_chat_sessions', sa.Column('context_state', sa.JSON(), nullable=True))

    # 2. citizen_chat_messages missing columns
    if inspector.has_table('citizen_chat_messages'):
        msg_cols = {col['name'] for col in inspector.get_columns('citizen_chat_messages')}
        if 'intent_classification' not in msg_cols:
            op.add_column('citizen_chat_messages', sa.Column('intent_classification', sa.String(length=50), nullable=True))
        if 'in_reply_to_question_id' not in msg_cols:
            op.add_column('citizen_chat_messages', sa.Column('in_reply_to_question_id', sa.String(length=100), nullable=True))
        if 'idempotency_key' not in msg_cols:
            op.add_column('citizen_chat_messages', sa.Column('idempotency_key', sa.String(length=100), nullable=True))
            op.create_index(op.f('ix_citizen_chat_messages_idempotency_key'), 'citizen_chat_messages', ['idempotency_key'], unique=False)

    # 3. citizen_needs missing columns
    if inspector.has_table('citizen_needs'):
        need_cols = {col['name'] for col in inspector.get_columns('citizen_needs')}
        if 'structured_facts' not in need_cols:
            op.add_column('citizen_needs', sa.Column('structured_facts', sa.JSON(), nullable=True))
        if 'facts_version' not in need_cols:
            op.add_column('citizen_needs', sa.Column('facts_version', sa.Integer(), nullable=True, server_default='1'))

    # 4. citizen_conversation_states table
    if not inspector.has_table('citizen_conversation_states'):
        op.create_table(
            'citizen_conversation_states',
            sa.Column('id', sa.String(length=36), nullable=False),
            sa.Column('session_id', sa.String(length=36), nullable=False),
            sa.Column('current_topic', sa.String(length=100), nullable=True),
            sa.Column('previous_topic', sa.String(length=100), nullable=True),
            sa.Column('active_need_id', sa.String(length=36), nullable=True),
            sa.Column('last_assistant_question', sa.Text(), nullable=True),
            sa.Column('asked_question_keys', sa.JSON(), nullable=True),
            sa.Column('confirmed_facts', sa.JSON(), nullable=True),
            sa.Column('negated_facts', sa.JSON(), nullable=True),
            sa.Column('uncertain_facts', sa.JSON(), nullable=True),
            sa.Column('compact_summary', sa.Text(), nullable=True),
            sa.Column('last_intent', sa.String(length=100), nullable=True),
            sa.Column('context_transition', sa.String(length=100), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['session_id'], ['citizen_chat_sessions.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_citizen_conversation_states_session_id'), 'citizen_conversation_states', ['session_id'], unique=True)


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if inspector.has_table('citizen_conversation_states'):
        op.drop_table('citizen_conversation_states')

