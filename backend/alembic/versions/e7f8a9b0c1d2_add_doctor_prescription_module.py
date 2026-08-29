"""add doctor prescription module tables and columns

Revision ID: e7f8a9b0c1d2
Revises: f9a8b7c6d5e4
Create Date: 2026-08-26 18:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision = 'e7f8a9b0c1d2'
down_revision = 'f9a8b7c6d5e4'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    tables = inspector.get_table_names()

    # 1. Medicine Catalog
    if 'medicine_catalog' not in tables:
        op.create_table(
            'medicine_catalog',
            sa.Column('id', sa.String(length=36), nullable=False),
            sa.Column('generic_name', sa.String(length=200), nullable=False),
            sa.Column('brand_name', sa.String(length=200), nullable=True),
            sa.Column('formulation', sa.String(length=100), nullable=False, server_default='Tablet'),
            sa.Column('strength_options', sa.JSON(), nullable=True),
            sa.Column('route_options', sa.JSON(), nullable=True),
            sa.Column('medicine_category', sa.String(length=100), nullable=True, server_default='Essential'),
            sa.Column('phc_availability_status', sa.String(length=50), nullable=True, server_default='AVAILABLE'),
            sa.Column('active', sa.Boolean(), nullable=True, server_default='true'),
            sa.Column('source_metadata', sa.JSON(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_medicine_catalog_generic_name'), 'medicine_catalog', ['generic_name'], unique=False)

    # 2. Upgrade / Create Prescriptions Table Columns
    if 'prescriptions' in tables:
        cols = [c['name'] for c in inspector.get_columns('prescriptions')]
        if 'doctor_id' in cols:
            op.alter_column('prescriptions', 'doctor_id', nullable=True)
        if 'reference' not in cols:
            op.add_column('prescriptions', sa.Column('reference', sa.String(length=100), nullable=True))
        if 'citizen_id' not in cols:
            op.add_column('prescriptions', sa.Column('citizen_id', sa.String(length=36), nullable=True))
        if 'case_id' not in cols:
            op.add_column('prescriptions', sa.Column('case_id', sa.String(length=36), nullable=True))
        if 'referral_id' not in cols:
            op.add_column('prescriptions', sa.Column('referral_id', sa.String(length=36), nullable=True))
        if 'prescriber_doctor_id' not in cols:
            op.add_column('prescriptions', sa.Column('prescriber_doctor_id', sa.String(length=36), nullable=True))
        if 'facility_id' not in cols:
            op.add_column('prescriptions', sa.Column('facility_id', sa.String(length=36), nullable=True))
        if 'version_number' not in cols:
            op.add_column('prescriptions', sa.Column('version_number', sa.Integer(), server_default='1'))
        if 'supersedes_prescription_id' not in cols:
            op.add_column('prescriptions', sa.Column('supersedes_prescription_id', sa.String(length=36), nullable=True))
        if 'clinical_context' not in cols:
            op.add_column('prescriptions', sa.Column('clinical_context', sa.Text(), nullable=True))
        if 'patient_language' not in cols:
            op.add_column('prescriptions', sa.Column('patient_language', sa.String(length=20), server_default='en-IN'))
        if 'signed_at' not in cols:
            op.add_column('prescriptions', sa.Column('signed_at', sa.DateTime(), nullable=True))
        if 'completed_at' not in cols:
            op.add_column('prescriptions', sa.Column('completed_at', sa.DateTime(), nullable=True))
        if 'cancelled_at' not in cols:
            op.add_column('prescriptions', sa.Column('cancelled_at', sa.DateTime(), nullable=True))
        if 'cancellation_reason' not in cols:
            op.add_column('prescriptions', sa.Column('cancellation_reason', sa.Text(), nullable=True))
        if 'idempotency_key' not in cols:
            op.add_column('prescriptions', sa.Column('idempotency_key', sa.String(length=255), nullable=True))
        if 'created_at' not in cols:
            op.add_column('prescriptions', sa.Column('created_at', sa.DateTime(), nullable=True))
        if 'updated_at' not in cols:
            op.add_column('prescriptions', sa.Column('updated_at', sa.DateTime(), nullable=True))

    # 3. Upgrade / Create Prescription Items Table Columns
    if 'prescription_items' in tables:
        cols = [c['name'] for c in inspector.get_columns('prescription_items')]
        if 'medicine' in cols:
            op.alter_column('prescription_items', 'medicine', nullable=True)
        if 'medicine_catalog_id' not in cols:
            op.add_column('prescription_items', sa.Column('medicine_catalog_id', sa.String(length=36), nullable=True))
        if 'generic_name_snapshot' not in cols:
            op.add_column('prescription_items', sa.Column('generic_name_snapshot', sa.String(length=200), nullable=True))
        if 'brand_name_snapshot' not in cols:
            op.add_column('prescription_items', sa.Column('brand_name_snapshot', sa.String(length=200), nullable=True))
        if 'formulation' not in cols:
            op.add_column('prescription_items', sa.Column('formulation', sa.String(length=100), server_default='Tablet'))
        if 'dose_unit' not in cols:
            op.add_column('prescription_items', sa.Column('dose_unit', sa.String(length=50), server_default='tablet'))
        if 'route' not in cols:
            op.add_column('prescription_items', sa.Column('route', sa.String(length=50), server_default='Oral'))
        if 'duration_value' not in cols:
            op.add_column('prescription_items', sa.Column('duration_value', sa.Integer(), server_default='5'))
        if 'duration_unit' not in cols:
            op.add_column('prescription_items', sa.Column('duration_unit', sa.String(length=20), server_default='days'))
        if 'quantity' not in cols:
            op.add_column('prescription_items', sa.Column('quantity', sa.Integer(), server_default='10'))
        if 'start_date' not in cols:
            op.add_column('prescription_items', sa.Column('start_date', sa.DateTime(), nullable=True))
        if 'end_date' not in cols:
            op.add_column('prescription_items', sa.Column('end_date', sa.DateTime(), nullable=True))
        if 'indication' not in cols:
            op.add_column('prescription_items', sa.Column('indication', sa.String(length=255), nullable=True))
        if 'as_needed' not in cols:
            op.add_column('prescription_items', sa.Column('as_needed', sa.Boolean(), server_default='false'))
        if 'max_frequency' not in cols:
            op.add_column('prescription_items', sa.Column('max_frequency', sa.String(length=100), nullable=True))
        if 'adherence_monitoring_required' not in cols:
            op.add_column('prescription_items', sa.Column('adherence_monitoring_required', sa.Boolean(), server_default='false'))
        if 'status' not in cols:
            op.add_column('prescription_items', sa.Column('status', sa.String(length=50), server_default='ACTIVE'))
        if 'stopped_at' not in cols:
            op.add_column('prescription_items', sa.Column('stopped_at', sa.DateTime(), nullable=True))
        if 'stopped_by_doctor_id' not in cols:
            op.add_column('prescription_items', sa.Column('stopped_by_doctor_id', sa.String(length=36), nullable=True))
        if 'stop_reason' not in cols:
            op.add_column('prescription_items', sa.Column('stop_reason', sa.Text(), nullable=True))
        if 'created_at' not in cols:
            op.add_column('prescription_items', sa.Column('created_at', sa.DateTime(), nullable=True))
        if 'updated_at' not in cols:
            op.add_column('prescription_items', sa.Column('updated_at', sa.DateTime(), nullable=True))

    # 4. Prescription Safety Checks
    if 'prescription_safety_checks' not in tables:
        op.create_table(
            'prescription_safety_checks',
            sa.Column('id', sa.String(length=36), nullable=False),
            sa.Column('prescription_id', sa.String(length=36), nullable=False),
            sa.Column('check_type', sa.String(length=100), nullable=False),
            sa.Column('severity', sa.String(length=50), nullable=False),
            sa.Column('message', sa.Text(), nullable=False),
            sa.Column('source_rule', sa.String(length=100), nullable=True),
            sa.Column('requires_confirmation', sa.Boolean(), server_default='false'),
            sa.Column('confirmed_by_doctor', sa.Boolean(), server_default='false'),
            sa.Column('confirmed_at', sa.DateTime(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['prescription_id'], ['prescriptions.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_prescription_safety_checks_prescription_id'), 'prescription_safety_checks', ['prescription_id'], unique=False)

    # 5. Prescription Amendments
    if 'prescription_amendments' not in tables:
        op.create_table(
            'prescription_amendments',
            sa.Column('id', sa.String(length=36), nullable=False),
            sa.Column('original_prescription_id', sa.String(length=36), nullable=False),
            sa.Column('new_prescription_id', sa.String(length=36), nullable=False),
            sa.Column('reason_code', sa.String(length=100), nullable=False),
            sa.Column('reason_note', sa.Text(), nullable=True),
            sa.Column('created_by_doctor_id', sa.String(length=36), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['new_prescription_id'], ['prescriptions.id'], ),
            sa.ForeignKeyConstraint(['original_prescription_id'], ['prescriptions.id'], ),
            sa.ForeignKeyConstraint(['created_by_doctor_id'], ['users.id'], ),
            sa.PrimaryKeyConstraint('id')
        )

    # 6. Prescription Acknowledgements
    if 'prescription_acknowledgements' not in tables:
        op.create_table(
            'prescription_acknowledgements',
            sa.Column('id', sa.String(length=36), nullable=False),
            sa.Column('prescription_id', sa.String(length=36), nullable=False),
            sa.Column('citizen_id', sa.String(length=36), nullable=False),
            sa.Column('instructions_understood', sa.Boolean(), server_default='true'),
            sa.Column('language', sa.String(length=20), server_default='en-IN'),
            sa.Column('acknowledged_at', sa.DateTime(), nullable=True),
            sa.Column('help_requested', sa.Boolean(), server_default='false'),
            sa.Column('help_note', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['citizen_id'], ['citizen_profiles.id'], ),
            sa.ForeignKeyConstraint(['prescription_id'], ['prescriptions.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )

    # 7. Add prescription_id to follow_ups
    if 'follow_ups' in tables:
        cols = [c['name'] for c in inspector.get_columns('follow_ups')]
        if 'prescription_id' not in cols:
            op.add_column('follow_ups', sa.Column('prescription_id', sa.String(length=36), nullable=True))
            op.create_index(op.f('ix_follow_ups_prescription_id'), 'follow_ups', ['prescription_id'], unique=False)


def downgrade():
    pass
