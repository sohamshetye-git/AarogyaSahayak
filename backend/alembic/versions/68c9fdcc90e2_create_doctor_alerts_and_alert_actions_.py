"""create doctor_alerts and alert_actions tables

Revision ID: 68c9fdcc90e2
Revises: e7f8a9b0c1d2
Create Date: 2026-08-26 19:33:03.467116

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '68c9fdcc90e2'
down_revision: Union[str, Sequence[str], None] = 'e7f8a9b0c1d2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('doctor_alerts',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('alert_reference', sa.String(length=50), nullable=False),
    sa.Column('facility_id', sa.String(length=36), nullable=False),
    sa.Column('doctor_id', sa.String(length=36), nullable=True),
    sa.Column('citizen_id', sa.String(length=36), nullable=True),
    sa.Column('case_id', sa.String(length=36), nullable=True),
    sa.Column('category', sa.String(length=50), nullable=False),
    sa.Column('alert_type', sa.String(length=100), nullable=False),
    sa.Column('severity', sa.String(length=50), nullable=False),
    sa.Column('title', sa.String(length=255), nullable=False),
    sa.Column('safe_summary', sa.Text(), nullable=False),
    sa.Column('source_entity_type', sa.String(length=50), nullable=False),
    sa.Column('source_entity_id', sa.String(length=36), nullable=False),
    sa.Column('source_event_id', sa.String(length=100), nullable=True),
    sa.Column('lifecycle_version', sa.Integer(), nullable=False),
    sa.Column('status', sa.String(length=50), nullable=False),
    sa.Column('response_due_at', sa.DateTime(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('seen_at', sa.DateTime(), nullable=True),
    sa.Column('acknowledged_at', sa.DateTime(), nullable=True),
    sa.Column('snoozed_until', sa.DateTime(), nullable=True),
    sa.Column('resolved_at', sa.DateTime(), nullable=True),
    sa.Column('dismissed_at', sa.DateTime(), nullable=True),
    sa.Column('acknowledged_by_id', sa.String(length=36), nullable=True),
    sa.Column('resolved_by_id', sa.String(length=36), nullable=True),
    sa.Column('dismissed_by_id', sa.String(length=36), nullable=True),
    sa.Column('resolution_note', sa.Text(), nullable=True),
    sa.Column('dismissal_reason', sa.Text(), nullable=True),
    sa.Column('snooze_reason', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['acknowledged_by_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['case_id'], ['cases.id'], ),
    sa.ForeignKeyConstraint(['citizen_id'], ['citizen_profiles.id'], ),
    sa.ForeignKeyConstraint(['dismissed_by_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['doctor_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['resolved_by_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_doctor_alerts_alert_reference'), 'doctor_alerts', ['alert_reference'], unique=True)
    op.create_index(op.f('ix_doctor_alerts_alert_type'), 'doctor_alerts', ['alert_type'], unique=False)
    op.create_index(op.f('ix_doctor_alerts_case_id'), 'doctor_alerts', ['case_id'], unique=False)
    op.create_index(op.f('ix_doctor_alerts_category'), 'doctor_alerts', ['category'], unique=False)
    op.create_index(op.f('ix_doctor_alerts_citizen_id'), 'doctor_alerts', ['citizen_id'], unique=False)
    op.create_index(op.f('ix_doctor_alerts_created_at'), 'doctor_alerts', ['created_at'], unique=False)
    op.create_index(op.f('ix_doctor_alerts_doctor_id'), 'doctor_alerts', ['doctor_id'], unique=False)
    op.create_index(op.f('ix_doctor_alerts_facility_id'), 'doctor_alerts', ['facility_id'], unique=False)
    op.create_index(op.f('ix_doctor_alerts_response_due_at'), 'doctor_alerts', ['response_due_at'], unique=False)
    op.create_index(op.f('ix_doctor_alerts_severity'), 'doctor_alerts', ['severity'], unique=False)
    op.create_index(op.f('ix_doctor_alerts_source_entity_id'), 'doctor_alerts', ['source_entity_id'], unique=False)
    op.create_index(op.f('ix_doctor_alerts_source_entity_type'), 'doctor_alerts', ['source_entity_type'], unique=False)
    op.create_index(op.f('ix_doctor_alerts_status'), 'doctor_alerts', ['status'], unique=False)

    op.create_table('alert_actions',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('alert_id', sa.String(length=36), nullable=False),
    sa.Column('action', sa.String(length=100), nullable=False),
    sa.Column('previous_status', sa.String(length=50), nullable=True),
    sa.Column('new_status', sa.String(length=50), nullable=False),
    sa.Column('actor_id', sa.String(length=36), nullable=True),
    sa.Column('actor_role', sa.String(length=50), nullable=False),
    sa.Column('note', sa.Text(), nullable=True),
    sa.Column('metadata_json', sa.JSON(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['actor_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['alert_id'], ['doctor_alerts.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_alert_actions_alert_id'), 'alert_actions', ['alert_id'], unique=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('prescriptions', sa.Column('signature_ref', sa.VARCHAR(length=255), autoincrement=False, nullable=True))
    op.add_column('prescriptions', sa.Column('issued_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True))
    op.drop_constraint(None, 'prescriptions', type_='foreignkey')
    op.drop_constraint(None, 'prescriptions', type_='foreignkey')
    op.drop_constraint(None, 'prescriptions', type_='foreignkey')
    op.drop_constraint(None, 'prescriptions', type_='foreignkey')
    op.drop_constraint(None, 'prescriptions', type_='foreignkey')
    op.drop_index(op.f('ix_prescriptions_supersedes_prescription_id'), table_name='prescriptions')
    op.drop_index(op.f('ix_prescriptions_status'), table_name='prescriptions')
    op.drop_index(op.f('ix_prescriptions_referral_id'), table_name='prescriptions')
    op.drop_index(op.f('ix_prescriptions_reference'), table_name='prescriptions')
    op.drop_index(op.f('ix_prescriptions_prescriber_doctor_id'), table_name='prescriptions')
    op.drop_index(op.f('ix_prescriptions_idempotency_key'), table_name='prescriptions')
    op.drop_index(op.f('ix_prescriptions_citizen_id'), table_name='prescriptions')
    op.drop_index(op.f('ix_prescriptions_case_id'), table_name='prescriptions')
    op.alter_column('prescriptions', 'doctor_id',
               existing_type=sa.VARCHAR(length=36),
               nullable=False)
    op.alter_column('prescriptions', 'prescriber_doctor_id',
               existing_type=sa.VARCHAR(length=36),
               nullable=True)
    op.alter_column('prescriptions', 'case_id',
               existing_type=sa.VARCHAR(length=36),
               nullable=True)
    op.alter_column('prescriptions', 'citizen_id',
               existing_type=sa.VARCHAR(length=36),
               nullable=True)
    op.alter_column('prescriptions', 'reference',
               existing_type=sa.VARCHAR(length=100),
               nullable=True)
    op.drop_constraint(None, 'prescription_safety_checks', type_='foreignkey')
    op.create_foreign_key(op.f('prescription_safety_checks_prescription_id_fkey'), 'prescription_safety_checks', 'prescriptions', ['prescription_id'], ['id'], ondelete='CASCADE')
    op.add_column('prescription_items', sa.Column('form', sa.VARCHAR(length=50), autoincrement=False, nullable=True))
    op.add_column('prescription_items', sa.Column('duration', sa.VARCHAR(length=50), autoincrement=False, nullable=True))
    op.drop_constraint(None, 'prescription_items', type_='foreignkey')
    op.drop_constraint(None, 'prescription_items', type_='foreignkey')
    op.drop_index(op.f('ix_prescription_items_status'), table_name='prescription_items')
    op.drop_index(op.f('ix_prescription_items_medicine_catalog_id'), table_name='prescription_items')
    op.alter_column('prescription_items', 'instructions',
               existing_type=sa.Text(),
               type_=sa.VARCHAR(length=255),
               existing_nullable=True)
    op.alter_column('prescription_items', 'timing',
               existing_type=sa.String(length=100),
               type_=sa.VARCHAR(length=50),
               existing_nullable=True)
    op.alter_column('prescription_items', 'frequency',
               existing_type=sa.String(length=100),
               type_=sa.VARCHAR(length=50),
               existing_nullable=True)
    op.alter_column('prescription_items', 'dose',
               existing_type=sa.String(length=100),
               type_=sa.VARCHAR(length=50),
               existing_nullable=True)
    op.alter_column('prescription_items', 'medicine',
               existing_type=sa.VARCHAR(length=200),
               nullable=False)
    op.alter_column('prescription_items', 'generic_name_snapshot',
               existing_type=sa.VARCHAR(length=200),
               nullable=True)
    op.drop_index(op.f('ix_prescription_amendments_original_prescription_id'), table_name='prescription_amendments')
    op.drop_index(op.f('ix_prescription_amendments_new_prescription_id'), table_name='prescription_amendments')
    op.drop_constraint(None, 'prescription_acknowledgements', type_='foreignkey')
    op.create_foreign_key(op.f('prescription_acknowledgements_prescription_id_fkey'), 'prescription_acknowledgements', 'prescriptions', ['prescription_id'], ['id'], ondelete='CASCADE')
    op.drop_index(op.f('ix_prescription_acknowledgements_prescription_id'), table_name='prescription_acknowledgements')
    op.drop_index(op.f('ix_prescription_acknowledgements_citizen_id'), table_name='prescription_acknowledgements')
    op.drop_index(op.f('ix_investigation_orders_reference'), table_name='investigation_orders')
    op.drop_index(op.f('ix_investigation_orders_ordered_by_doctor_id'), table_name='investigation_orders')
    op.create_unique_constraint(op.f('investigation_orders_reference_key'), 'investigation_orders', ['reference'], postgresql_nulls_not_distinct=False)
    op.drop_constraint(None, 'follow_ups', type_='foreignkey')
    op.drop_index(op.f('ix_alert_actions_alert_id'), table_name='alert_actions')
    op.drop_table('alert_actions')
    op.drop_index(op.f('ix_doctor_alerts_status'), table_name='doctor_alerts')
    op.drop_index(op.f('ix_doctor_alerts_source_entity_type'), table_name='doctor_alerts')
    op.drop_index(op.f('ix_doctor_alerts_source_entity_id'), table_name='doctor_alerts')
    op.drop_index(op.f('ix_doctor_alerts_severity'), table_name='doctor_alerts')
    op.drop_index(op.f('ix_doctor_alerts_response_due_at'), table_name='doctor_alerts')
    op.drop_index(op.f('ix_doctor_alerts_facility_id'), table_name='doctor_alerts')
    op.drop_index(op.f('ix_doctor_alerts_doctor_id'), table_name='doctor_alerts')
    op.drop_index(op.f('ix_doctor_alerts_created_at'), table_name='doctor_alerts')
    op.drop_index(op.f('ix_doctor_alerts_citizen_id'), table_name='doctor_alerts')
    op.drop_index(op.f('ix_doctor_alerts_category'), table_name='doctor_alerts')
    op.drop_index(op.f('ix_doctor_alerts_case_id'), table_name='doctor_alerts')
    op.drop_index(op.f('ix_doctor_alerts_alert_type'), table_name='doctor_alerts')
    op.drop_index(op.f('ix_doctor_alerts_alert_reference'), table_name='doctor_alerts')
    op.drop_table('doctor_alerts')
    # ### end Alembic commands ###
