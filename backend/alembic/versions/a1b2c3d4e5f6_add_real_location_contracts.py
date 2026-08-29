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

def downgrade() -> None:
    op.drop_table('visit_locations')
    op.drop_table('care_request_locations')
    op.drop_table('user_location_preferences')
