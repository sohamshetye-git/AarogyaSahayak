"""add doctor investigations module tables

Revision ID: f9a8b7c6d5e4
Revises: e8f90a1b2c3d
Create Date: 2026-08-26 17:25:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision = 'f9a8b7c6d5e4'
down_revision = 'b1c2d3e4f5a6'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    tables = inspector.get_table_names()

    if 'investigation_orders' not in tables:
        op.create_table(
            'investigation_orders',
            sa.Column('id', sa.String(length=36), nullable=False),
            sa.Column('reference', sa.String(length=50), nullable=False),
            sa.Column('citizen_id', sa.String(length=36), nullable=False),
            sa.Column('case_id', sa.String(length=36), nullable=False),
            sa.Column('referral_id', sa.String(length=36), nullable=True),
            sa.Column('consultation_id', sa.String(length=36), nullable=True),
            sa.Column('ordered_by_doctor_id', sa.String(length=36), nullable=True),
            sa.Column('facility_id', sa.String(length=36), nullable=True),
            sa.Column('test_name', sa.String(length=200), nullable=False),
            sa.Column('test_code', sa.String(length=50), nullable=True),
            sa.Column('category', sa.String(length=50), nullable=True, server_default='GENERAL'),
            sa.Column('priority', sa.String(length=50), nullable=True, server_default='ROUTINE'),
            sa.Column('clinical_reason', sa.Text(), nullable=True),
            sa.Column('specimen_type', sa.String(length=100), nullable=True),
            sa.Column('preparation_instructions', sa.Text(), nullable=True),
            sa.Column('collection_location', sa.String(length=200), nullable=True),
            sa.Column('ordered_at', sa.DateTime(), nullable=True),
            sa.Column('due_at', sa.DateTime(), nullable=True),
            sa.Column('expected_result_at', sa.DateTime(), nullable=True),
            sa.Column('status', sa.String(length=50), nullable=True, server_default='ORDERED'),
            sa.Column('idempotency_key', sa.String(length=100), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['case_id'], ['cases.id'], ),
            sa.ForeignKeyConstraint(['citizen_id'], ['citizen_profiles.id'], ),
            sa.ForeignKeyConstraint(['consultation_id'], ['consultations.id'], ),
            sa.ForeignKeyConstraint(['ordered_by_doctor_id'], ['users.id'], ),
            sa.ForeignKeyConstraint(['referral_id'], ['referrals.id'], ),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('idempotency_key'),
            sa.UniqueConstraint('reference')
        )
        op.create_index(op.f('ix_investigation_orders_case_id'), 'investigation_orders', ['case_id'], unique=False)
        op.create_index(op.f('ix_investigation_orders_citizen_id'), 'investigation_orders', ['citizen_id'], unique=False)
        op.create_index(op.f('ix_investigation_orders_consultation_id'), 'investigation_orders', ['consultation_id'], unique=False)
        op.create_index(op.f('ix_investigation_orders_ordered_at'), 'investigation_orders', ['ordered_at'], unique=False)
        op.create_index(op.f('ix_investigation_orders_priority'), 'investigation_orders', ['priority'], unique=False)
        op.create_index(op.f('ix_investigation_orders_referral_id'), 'investigation_orders', ['referral_id'], unique=False)
        op.create_index(op.f('ix_investigation_orders_status'), 'investigation_orders', ['status'], unique=False)

    if 'investigation_samples' not in tables:
        op.create_table(
            'investigation_samples',
            sa.Column('id', sa.String(length=36), nullable=False),
            sa.Column('investigation_order_id', sa.String(length=36), nullable=False),
            sa.Column('sample_reference', sa.String(length=100), nullable=True),
            sa.Column('collected_by_user_id', sa.String(length=36), nullable=True),
            sa.Column('collected_at', sa.DateTime(), nullable=True),
            sa.Column('collection_status', sa.String(length=50), nullable=True, server_default='PENDING'),
            sa.Column('rejection_reason', sa.Text(), nullable=True),
            sa.Column('recollection_required', sa.Boolean(), nullable=True, server_default=sa.text('false')),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['collected_by_user_id'], ['users.id'], ),
            sa.ForeignKeyConstraint(['investigation_order_id'], ['investigation_orders.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_investigation_samples_investigation_order_id'), 'investigation_samples', ['investigation_order_id'], unique=False)

    if 'investigation_results' not in tables:
        op.create_table(
            'investigation_results',
            sa.Column('id', sa.String(length=36), nullable=False),
            sa.Column('investigation_order_id', sa.String(length=36), nullable=False),
            sa.Column('result_source', sa.String(length=100), nullable=True, server_default='PHC_LAB'),
            sa.Column('laboratory_name', sa.String(length=200), nullable=True, server_default='PHC Kalyanpur Central Lab'),
            sa.Column('resulted_at', sa.DateTime(), nullable=True),
            sa.Column('entered_by_user_id', sa.String(length=36), nullable=True),
            sa.Column('verified_by_user_id', sa.String(length=36), nullable=True),
            sa.Column('verification_status', sa.String(length=50), nullable=True, server_default='VERIFIED'),
            sa.Column('report_attachment_id', sa.String(length=100), nullable=True),
            sa.Column('critical_flag', sa.Boolean(), nullable=True, server_default=sa.text('false')),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['entered_by_user_id'], ['users.id'], ),
            sa.ForeignKeyConstraint(['investigation_order_id'], ['investigation_orders.id'], ),
            sa.ForeignKeyConstraint(['verified_by_user_id'], ['users.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_investigation_results_critical_flag'), 'investigation_results', ['critical_flag'], unique=False)
        op.create_index(op.f('ix_investigation_results_investigation_order_id'), 'investigation_results', ['investigation_order_id'], unique=False)

    if 'investigation_result_items' not in tables:
        op.create_table(
            'investigation_result_items',
            sa.Column('id', sa.String(length=36), nullable=False),
            sa.Column('result_id', sa.String(length=36), nullable=False),
            sa.Column('parameter_name', sa.String(length=200), nullable=False),
            sa.Column('parameter_code', sa.String(length=50), nullable=True),
            sa.Column('value', sa.String(length=100), nullable=False),
            sa.Column('unit', sa.String(length=50), nullable=True),
            sa.Column('reference_low', sa.String(length=50), nullable=True),
            sa.Column('reference_high', sa.String(length=50), nullable=True),
            sa.Column('source_flag', sa.String(length=50), nullable=True, server_default='NORMAL'),
            sa.Column('remarks', sa.Text(), nullable=True),
            sa.ForeignKeyConstraint(['result_id'], ['investigation_results.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_investigation_result_items_result_id'), 'investigation_result_items', ['result_id'], unique=False)

    if 'investigation_reviews' not in tables:
        op.create_table(
            'investigation_reviews',
            sa.Column('id', sa.String(length=36), nullable=False),
            sa.Column('result_id', sa.String(length=36), nullable=False),
            sa.Column('doctor_id', sa.String(length=36), nullable=False),
            sa.Column('review_note', sa.Text(), nullable=False),
            sa.Column('outcome', sa.String(length=100), nullable=False),
            sa.Column('reviewed_at', sa.DateTime(), nullable=True),
            sa.Column('critical_acknowledged_at', sa.DateTime(), nullable=True),
            sa.Column('care_plan_updated', sa.Boolean(), nullable=True, server_default=sa.text('false')),
            sa.Column('related_follow_up_id', sa.String(length=36), nullable=True),
            sa.Column('related_higher_referral_id', sa.String(length=36), nullable=True),
            sa.ForeignKeyConstraint(['doctor_id'], ['users.id'], ),
            sa.ForeignKeyConstraint(['related_follow_up_id'], ['follow_ups.id'], ),
            sa.ForeignKeyConstraint(['related_higher_referral_id'], ['referrals.id'], ),
            sa.ForeignKeyConstraint(['result_id'], ['investigation_results.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_investigation_reviews_result_id'), 'investigation_reviews', ['result_id'], unique=False)

    if 'investigation_asha_tasks' not in tables:
        op.create_table(
            'investigation_asha_tasks',
            sa.Column('id', sa.String(length=36), nullable=False),
            sa.Column('investigation_order_id', sa.String(length=36), nullable=False),
            sa.Column('asha_user_id', sa.String(length=36), nullable=False),
            sa.Column('citizen_id', sa.String(length=36), nullable=False),
            sa.Column('task_type', sa.String(length=100), nullable=True, server_default='ATTENDANCE_ASSISTANCE'),
            sa.Column('due_date', sa.DateTime(), nullable=True),
            sa.Column('instructions', sa.Text(), nullable=False),
            sa.Column('status', sa.String(length=50), nullable=True, server_default='PENDING'),
            sa.Column('contacted_citizen', sa.Boolean(), nullable=True, server_default=sa.text('false')),
            sa.Column('attendance_confirmed', sa.Boolean(), nullable=True, server_default=sa.text('false')),
            sa.Column('unable_to_attend_reason', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['asha_user_id'], ['users.id'], ),
            sa.ForeignKeyConstraint(['citizen_id'], ['citizen_profiles.id'], ),
            sa.ForeignKeyConstraint(['investigation_order_id'], ['investigation_orders.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_investigation_asha_tasks_asha_user_id'), 'investigation_asha_tasks', ['asha_user_id'], unique=False)
        op.create_index(op.f('ix_investigation_asha_tasks_citizen_id'), 'investigation_asha_tasks', ['citizen_id'], unique=False)
        op.create_index(op.f('ix_investigation_asha_tasks_investigation_order_id'), 'investigation_asha_tasks', ['investigation_order_id'], unique=False)
        op.create_index(op.f('ix_investigation_asha_tasks_status'), 'investigation_asha_tasks', ['status'], unique=False)


def downgrade():
    op.drop_table('investigation_asha_tasks')
    op.drop_table('investigation_reviews')
    op.drop_table('investigation_result_items')
    op.drop_table('investigation_results')
    op.drop_table('investigation_samples')
    op.drop_table('investigation_orders')
