"""add_patient_registration_extensions

Revision ID: e8f90a1b2c3d
Revises: d7e63dffcabc
Create Date: 2026-08-25 00:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'e8f90a1b2c3d'
down_revision: Union[str, Sequence[str], None] = 'd7e63dffcabc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new columns to citizen_profiles
    with op.batch_alter_table('citizen_profiles') as batch_op:
        batch_op.add_column(sa.Column('legal_name', sa.String(length=150), nullable=True))
        batch_op.add_column(sa.Column('preferred_name', sa.String(length=150), nullable=True))
        batch_op.add_column(sa.Column('current_care_location', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('date_of_birth', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('alternate_phone', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('preferred_contact_method', sa.String(length=30), server_default='PHONE', nullable=True))
        batch_op.add_column(sa.Column('address', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('pincode', sa.String(length=10), nullable=True))
        batch_op.add_column(sa.Column('state', sa.String(length=100), server_default='Maharashtra', nullable=True))
        batch_op.add_column(sa.Column('district', sa.String(length=100), server_default='District 04', nullable=True))
        batch_op.add_column(sa.Column('block_taluka', sa.String(length=100), server_default='Kalyanpur Block', nullable=True))
        batch_op.add_column(sa.Column('gram_panchayat', sa.String(length=100), server_default='Kalyanpur GP', nullable=True))
        batch_op.add_column(sa.Column('sub_center_id', sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column('assigned_facility_id', sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column('assigned_asha_id', sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column('emergency_contact_name', sa.String(length=150), nullable=True))
        batch_op.add_column(sa.Column('emergency_contact_phone', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('emergency_contact_relation', sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column('head_of_household_name', sa.String(length=150), nullable=True))
        batch_op.add_column(sa.Column('head_of_household_relation', sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column('family_id', sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column('household_category', sa.String(length=50), server_default='OTHER', nullable=True))
        batch_op.add_column(sa.Column('ration_card_category', sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column('literacy_assistance_needed', sa.Boolean(), server_default='false', nullable=True))
        batch_op.add_column(sa.Column('accessibility_needs', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('registration_consent_obtained', sa.Boolean(), server_default='false', nullable=True))
        batch_op.add_column(sa.Column('voice_consent_obtained', sa.Boolean(), server_default='false', nullable=True))
        batch_op.add_column(sa.Column('consent_method', sa.String(length=30), server_default='VERBAL', nullable=True))
        batch_op.add_column(sa.Column('guardian_name', sa.String(length=150), nullable=True))
        batch_op.add_column(sa.Column('guardian_relation', sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column('consent_timestamp', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('blood_group', sa.String(length=10), nullable=True))
        batch_op.add_column(sa.Column('allergies', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('chronic_conditions', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('current_medications', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('disability_notes', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('previous_illnesses', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('previous_surgeries', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('tobacco_use', sa.String(length=50), server_default='NONE', nullable=True))
        batch_op.add_column(sa.Column('alcohol_use', sa.String(length=50), server_default='NONE', nullable=True))
        batch_op.add_column(sa.Column('programme_enrollments', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('health_notes', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('anc_registration_number', sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column('updated_at', sa.DateTime(), nullable=True))

    # Create citizen_attachments table
    op.create_table(
        'citizen_attachments',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('citizen_id', sa.String(length=36), nullable=False),
        sa.Column('case_id', sa.String(length=36), nullable=True),
        sa.Column('document_type', sa.String(length=50), nullable=False),
        sa.Column('file_name', sa.String(length=255), nullable=False),
        sa.Column('file_path', sa.String(length=255), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('mime_type', sa.String(length=100), nullable=True),
        sa.Column('uploaded_by', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['citizen_id'], ['citizen_profiles.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_citizen_attachments_citizen_id'), 'citizen_attachments', ['citizen_id'], unique=False)
    op.create_index(op.f('ix_citizen_attachments_case_id'), 'citizen_attachments', ['case_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_citizen_attachments_case_id'), table_name='citizen_attachments')
    op.drop_index(op.f('ix_citizen_attachments_citizen_id'), table_name='citizen_attachments')
    op.drop_table('citizen_attachments')
    with op.batch_alter_table('citizen_profiles') as batch_op:
        batch_op.drop_column('updated_at')
        batch_op.drop_column('anc_registration_number')
        batch_op.drop_column('health_notes')
        batch_op.drop_column('programme_enrollments')
        batch_op.drop_column('alcohol_use')
        batch_op.drop_column('tobacco_use')
        batch_op.drop_column('previous_surgeries')
        batch_op.drop_column('previous_illnesses')
        batch_op.drop_column('disability_notes')
        batch_op.drop_column('current_medications')
        batch_op.drop_column('chronic_conditions')
        batch_op.drop_column('allergies')
        batch_op.drop_column('blood_group')
        batch_op.drop_column('consent_timestamp')
        batch_op.drop_column('guardian_relation')
        batch_op.drop_column('guardian_name')
        batch_op.drop_column('consent_method')
        batch_op.drop_column('voice_consent_obtained')
        batch_op.drop_column('registration_consent_obtained')
        batch_op.drop_column('accessibility_needs')
        batch_op.drop_column('literacy_assistance_needed')
        batch_op.drop_column('ration_card_category')
        batch_op.drop_column('household_category')
        batch_op.drop_column('family_id')
        batch_op.drop_column('head_of_household_relation')
        batch_op.drop_column('head_of_household_name')
        batch_op.drop_column('emergency_contact_relation')
        batch_op.drop_column('emergency_contact_phone')
        batch_op.drop_column('emergency_contact_name')
        batch_op.drop_column('assigned_asha_id')
        batch_op.drop_column('assigned_facility_id')
        batch_op.drop_column('sub_center_id')
        batch_op.drop_column('gram_panchayat')
        batch_op.drop_column('block_taluka')
        batch_op.drop_column('district')
        batch_op.drop_column('state')
        batch_op.drop_column('pincode')
        batch_op.drop_column('address')
        batch_op.drop_column('preferred_contact_method')
        batch_op.drop_column('alternate_phone')
        batch_op.drop_column('date_of_birth')
