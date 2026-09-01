"""add real location contracts

Revision ID: a1b2c3d4e5f6
Revises: f9a8b7c6d5e4
Create Date: 2026-08-28 12:35:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = 'e9a8b7c6d5e4'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # 1. user_location_preferences
    op.create_table(
        'user_location_preferences',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('user_id', sa.String(length=36), sa.ForeignKey('users.id'), nullable=False, unique=True),
        sa.Column('preferred_source', sa.String(length=50), nullable=False, server_default='DEVICE_GPS'),
        sa.Column('manual_village_id', sa.String(length=36), nullable=True),
        sa.Column('manual_village_name', sa.String(length=150), nullable=True),
        sa.Column('manual_pincode', sa.String(length=10), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True)
    )
    op.create_index('ix_user_location_preferences_user_id', 'user_location_preferences', ['user_id'])

    # 2. care_request_locations
    op.create_table(
        'care_request_locations',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('service_request_id', sa.String(length=36), sa.ForeignKey('service_requests.id'), nullable=True),
        sa.Column('latitude', sa.Float(), nullable=False),
        sa.Column('longitude', sa.Float(), nullable=False),
        sa.Column('accuracy_meters', sa.Float(), nullable=True),
        sa.Column('altitude_meters', sa.Float(), nullable=True),
        sa.Column('source', sa.String(length=50), nullable=False, server_default='DEVICE_GPS'),
        sa.Column('formatted_address', sa.Text(), nullable=True),
        sa.Column('village', sa.String(length=150), nullable=True),
        sa.Column('pincode', sa.String(length=10), nullable=True),
        sa.Column('block', sa.String(length=150), nullable=True),
        sa.Column('district', sa.String(length=150), nullable=True),
        sa.Column('state', sa.String(length=100), server_default='Maharashtra', nullable=True),
        sa.Column('place_id', sa.String(length=150), nullable=True),
        sa.Column('captured_at', sa.DateTime(), nullable=True),
        sa.Column('confirmed_at', sa.DateTime(), nullable=True)
    )
    op.create_index('ix_care_request_locations_service_request_id', 'care_request_locations', ['service_request_id'])

    # 3. visit_locations
    op.create_table(
        'visit_locations',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('visit_id', sa.String(length=36), sa.ForeignKey('asha_visits.id'), nullable=False),
        sa.Column('latitude', sa.Float(), nullable=False),
        sa.Column('longitude', sa.Float(), nullable=False),
        sa.Column('accuracy_meters', sa.Float(), nullable=True),
        sa.Column('source', sa.String(length=50), nullable=False, server_default='DEVICE_GPS'),
        sa.Column('captured_at', sa.DateTime(), nullable=True)
    )
    op.create_index('ix_visit_locations_visit_id', 'visit_locations', ['visit_id'])

    # 4. Enhance facilities table with canonical attributes
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_fac_cols = {col["name"] for col in inspector.get_columns('facilities')} if inspector.has_table('facilities') else set()

    if 'public_reference' not in existing_fac_cols:
        op.add_column('facilities', sa.Column('public_reference', sa.String(length=50), nullable=True))
        op.create_index('ix_facilities_public_reference', 'facilities', ['public_reference'], unique=True)

    if 'official_name' not in existing_fac_cols:
        op.add_column('facilities', sa.Column('official_name', sa.String(length=255), nullable=True))

    if 'localized_name' not in existing_fac_cols:
        op.add_column('facilities', sa.Column('localized_name', sa.JSON(), nullable=True))

    if 'ownership' not in existing_fac_cols:
        op.add_column('facilities', sa.Column('ownership', sa.String(length=50), server_default='GOVERNMENT', nullable=True))

    if 'authority' not in existing_fac_cols:
        op.add_column('facilities', sa.Column('authority', sa.String(length=150), server_default='Public Health Department, Maharashtra', nullable=True))

    if 'state' not in existing_fac_cols:
        op.add_column('facilities', sa.Column('state', sa.String(length=100), server_default='Maharashtra', nullable=True))

    if 'district' not in existing_fac_cols:
        op.add_column('facilities', sa.Column('district', sa.String(length=100), server_default='District 04', nullable=True))

    if 'block' not in existing_fac_cols:
        op.add_column('facilities', sa.Column('block', sa.String(length=100), server_default='Kalyanpur Block', nullable=True))

    if 'village' not in existing_fac_cols:
        op.add_column('facilities', sa.Column('village', sa.String(length=150), nullable=True))

    if 'pincode' not in existing_fac_cols:
        op.add_column('facilities', sa.Column('pincode', sa.String(length=10), nullable=True))
        op.create_index('ix_facilities_pincode', 'facilities', ['pincode'], unique=False)

    if 'landmark' not in existing_fac_cols:
        op.add_column('facilities', sa.Column('landmark', sa.String(length=255), nullable=True))

    if 'latitude' not in existing_fac_cols:
        op.add_column('facilities', sa.Column('latitude', sa.Float(), server_default='18.5204', nullable=True))

    if 'longitude' not in existing_fac_cols:
        op.add_column('facilities', sa.Column('longitude', sa.Float(), server_default='73.8567', nullable=True))

    if 'phone' not in existing_fac_cols:
        op.add_column('facilities', sa.Column('phone', sa.String(length=30), nullable=True))

    if 'email' not in existing_fac_cols:
        op.add_column('facilities', sa.Column('email', sa.String(length=150), nullable=True))

    if 'emergency_helpline' not in existing_fac_cols:
        op.add_column('facilities', sa.Column('emergency_helpline', sa.String(length=30), server_default='108', nullable=True))

    if 'verification_status' not in existing_fac_cols:
        op.add_column('facilities', sa.Column('verification_status', sa.String(length=50), server_default='VERIFIED', nullable=True))

    if 'source_id' not in existing_fac_cols:
        op.add_column('facilities', sa.Column('source_id', sa.String(length=100), server_default='GOVT_REGISTRY_NIN', nullable=True))

    if 'source_name' not in existing_fac_cols:
        op.add_column('facilities', sa.Column('source_name', sa.String(length=150), server_default='National Health Portal / State Registry', nullable=True))

    if 'last_verified_at' not in existing_fac_cols:
        op.add_column('facilities', sa.Column('last_verified_at', sa.DateTime(), nullable=True))

    if 'updated_at' not in existing_fac_cols:
        op.add_column('facilities', sa.Column('updated_at', sa.DateTime(), nullable=True))

    # 5. Facility Child Tables
    existing_tables = set(inspector.get_table_names())
    if 'facility_services' not in existing_tables:
        op.create_table(
            'facility_services',
            sa.Column('id', sa.String(length=36), primary_key=True),
            sa.Column('facility_id', sa.String(length=36), sa.ForeignKey('facilities.id'), nullable=False),
            sa.Column('service_code', sa.String(length=100), nullable=False),
            sa.Column('localized_service_name', sa.JSON(), nullable=True),
            sa.Column('service_level', sa.String(length=50), server_default='PRIMARY', nullable=True),
            sa.Column('availability_status', sa.String(length=50), server_default='VERIFIED_AVAILABLE', nullable=True),
            sa.Column('emergency_capability', sa.Boolean(), server_default='false', nullable=True),
            sa.Column('appointment_requirement', sa.Boolean(), server_default='false', nullable=True),
            sa.Column('cost_type', sa.String(length=50), server_default='FREE', nullable=True),
            sa.Column('source', sa.String(length=150), server_default='Facility Inspection 2026', nullable=True),
            sa.Column('last_verified_at', sa.DateTime(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True)
        )
        op.create_index('ix_facility_services_facility_id', 'facility_services', ['facility_id'])
        op.create_index('ix_facility_services_service_code', 'facility_services', ['service_code'])

    if 'facility_hours' not in existing_tables:
        op.create_table(
            'facility_hours',
            sa.Column('id', sa.String(length=36), primary_key=True),
            sa.Column('facility_id', sa.String(length=36), sa.ForeignKey('facilities.id'), nullable=False),
            sa.Column('day_of_week', sa.String(length=20), nullable=False),
            sa.Column('opening_time', sa.String(length=10), nullable=True),
            sa.Column('closing_time', sa.String(length=10), nullable=True),
            sa.Column('is_24x7_emergency', sa.Boolean(), server_default='false', nullable=True),
            sa.Column('verification_status', sa.String(length=50), server_default='VERIFIED', nullable=True),
            sa.Column('source', sa.String(length=150), server_default='Official Gazette', nullable=True),
            sa.Column('last_verified_at', sa.DateTime(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True)
        )
        op.create_index('ix_facility_hours_facility_id', 'facility_hours', ['facility_id'])

    if 'facility_scheme_empanelments' not in existing_tables:
        op.create_table(
            'facility_scheme_empanelments',
            sa.Column('id', sa.String(length=36), primary_key=True),
            sa.Column('facility_id', sa.String(length=36), sa.ForeignKey('facilities.id'), nullable=False),
            sa.Column('scheme_code', sa.String(length=100), nullable=False),
            sa.Column('scheme_name', sa.String(length=200), nullable=False),
            sa.Column('empanelment_reference', sa.String(length=100), nullable=True),
            sa.Column('specialties_covered', sa.JSON(), nullable=True),
            sa.Column('effective_from', sa.Date(), nullable=True),
            sa.Column('effective_until', sa.Date(), nullable=True),
            sa.Column('verification_status', sa.String(length=50), server_default='VERIFIED', nullable=True),
            sa.Column('official_source', sa.String(length=255), server_default='State Health Assurance Society (SHAS)', nullable=True),
            sa.Column('last_verified_at', sa.DateTime(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True)
        )
        op.create_index('ix_facility_scheme_empanelments_facility_id', 'facility_scheme_empanelments', ['facility_id'])
        op.create_index('ix_facility_scheme_empanelments_scheme_code', 'facility_scheme_empanelments', ['scheme_code'])

    if 'facility_searches' not in existing_tables:
        op.create_table(
            'facility_searches',
            sa.Column('id', sa.String(length=36), primary_key=True),
            sa.Column('citizen_id', sa.String(length=36), sa.ForeignKey('citizen_profiles.id'), nullable=True),
            sa.Column('household_member_id', sa.String(length=36), sa.ForeignKey('household_members.id'), nullable=True),
            sa.Column('requested_service', sa.String(length=100), nullable=True),
            sa.Column('urgency', sa.String(length=50), server_default='ROUTINE', nullable=True),
            sa.Column('patient_category', sa.String(length=50), server_default='GENERAL', nullable=True),
            sa.Column('location_method', sa.String(length=50), server_default='GPS', nullable=True),
            sa.Column('coordinates_or_locality', sa.JSON(), nullable=True),
            sa.Column('consent_reference', sa.String(length=100), nullable=True),
            sa.Column('consent_purpose', sa.String(length=255), server_default='Healthcare facility matching', nullable=True),
            sa.Column('consent_timestamp', sa.DateTime(), nullable=True),
            sa.Column('filters_applied', sa.JSON(), nullable=True),
            sa.Column('result_facility_ids', sa.JSON(), nullable=True),
            sa.Column('selected_facility_id', sa.String(length=36), sa.ForeignKey('facilities.id'), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True)
        )
        op.create_index('ix_facility_searches_citizen_id', 'facility_searches', ['citizen_id'])
        op.create_index('ix_facility_searches_selected_facility_id', 'facility_searches', ['selected_facility_id'])

    if 'facility_assistance_requests' not in existing_tables:
        op.create_table(
            'facility_assistance_requests',
            sa.Column('id', sa.String(length=36), primary_key=True),
            sa.Column('request_reference', sa.String(length=100), nullable=False),
            sa.Column('citizen_id', sa.String(length=36), sa.ForeignKey('citizen_profiles.id'), nullable=False),
            sa.Column('household_member_id', sa.String(length=36), sa.ForeignKey('household_members.id'), nullable=True),
            sa.Column('case_id', sa.String(length=36), sa.ForeignKey('cases.id'), nullable=True),
            sa.Column('need_id', sa.String(length=36), sa.ForeignKey('citizen_needs.id'), nullable=True),
            sa.Column('facility_id', sa.String(length=36), sa.ForeignKey('facilities.id'), nullable=False),
            sa.Column('assistance_type', sa.String(length=50), server_default='TRANSPORT_AND_DIRECTION', nullable=True),
            sa.Column('safety_priority', sa.String(length=50), server_default='ROUTINE', nullable=True),
            sa.Column('assistance_reason', sa.Text(), nullable=False),
            sa.Column('transport_needed', sa.Boolean(), server_default='false', nullable=True),
            sa.Column('assigned_asha_id', sa.String(length=36), nullable=True),
            sa.Column('assigned_asha_name', sa.String(length=150), server_default='Sita Patel (Kalyanpur)', nullable=True),
            sa.Column('citizen_location', sa.JSON(), nullable=True),
            sa.Column('preferred_contact', sa.String(length=50), server_default='PHONE', nullable=True),
            sa.Column('consent_given', sa.Boolean(), server_default='true', nullable=True),
            sa.Column('status', sa.String(length=50), server_default='PENDING', nullable=True),
            sa.Column('due_at', sa.DateTime(), nullable=True),
            sa.Column('transport_plan', sa.JSON(), nullable=True),
            sa.Column('outcome', sa.Text(), nullable=True),
            sa.Column('idempotency_key', sa.String(length=100), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True)
        )
        op.create_index('ix_facility_assistance_requests_request_reference', 'facility_assistance_requests', ['request_reference'], unique=True)
        op.create_index('ix_facility_assistance_requests_citizen_id', 'facility_assistance_requests', ['citizen_id'])
        op.create_index('ix_facility_assistance_requests_facility_id', 'facility_assistance_requests', ['facility_id'])

    if 'facility_appointment_requests' not in existing_tables:
        op.create_table(
            'facility_appointment_requests',
            sa.Column('id', sa.String(length=36), primary_key=True),
            sa.Column('appointment_reference', sa.String(length=100), nullable=False),
            sa.Column('citizen_id', sa.String(length=36), sa.ForeignKey('citizen_profiles.id'), nullable=False),
            sa.Column('household_member_id', sa.String(length=36), sa.ForeignKey('household_members.id'), nullable=True),
            sa.Column('facility_id', sa.String(length=36), sa.ForeignKey('facilities.id'), nullable=False),
            sa.Column('service_code', sa.String(length=100), nullable=False),
            sa.Column('service_name', sa.String(length=200), nullable=False),
            sa.Column('requested_slot', sa.String(length=100), nullable=False),
            sa.Column('status', sa.String(length=50), server_default='REQUESTED', nullable=True),
            sa.Column('facility_confirmation_source', sa.String(length=150), nullable=True),
            sa.Column('doctor_or_desk_notes', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True)
        )
        op.create_index('ix_facility_appointment_requests_appointment_reference', 'facility_appointment_requests', ['appointment_reference'], unique=True)
        op.create_index('ix_facility_appointment_requests_citizen_id', 'facility_appointment_requests', ['citizen_id'])
        op.create_index('ix_facility_appointment_requests_facility_id', 'facility_appointment_requests', ['facility_id'])

def downgrade() -> None:
    op.drop_table('visit_locations')
    op.drop_table('care_request_locations')
    op.drop_table('user_location_preferences')
