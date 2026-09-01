"""add_government_scheme_tables

Revision ID: 4895d1d54c65
Revises: a9b8c7d6e5f4
Create Date: 2026-08-25 15:09:49.147350

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4895d1d54c65'
down_revision: Union[str, Sequence[str], None] = 'a9b8c7d6e5f4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Ensure citizen_profiles indexes exist
    op.create_index(op.f('ix_citizen_profiles_phone'), 'citizen_profiles', ['phone'], unique=False)

    # 2. Create authorities table
    op.create_table(
        'authorities',
        sa.Column('authority_id', sa.String(length=36), nullable=False),
        sa.Column('authority_code', sa.String(length=100), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('authority_type', sa.String(length=100), nullable=False),
        sa.Column('government_level', sa.String(length=50), nullable=False),
        sa.Column('official_url', sa.String(length=500), nullable=False),
        sa.Column('contact_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('authority_id')
    )
    op.create_index(op.f('ix_authorities_authority_code'), 'authorities', ['authority_code'], unique=True)

    # 3. Create schemes table
    op.create_table(
        'schemes',
        sa.Column('scheme_id', sa.String(length=36), nullable=False),
        sa.Column('scheme_code', sa.String(length=100), nullable=False),
        sa.Column('canonical_name', sa.String(length=255), nullable=False),
        sa.Column('short_name', sa.String(length=100), nullable=True),
        sa.Column('entity_type', sa.String(length=100), nullable=False),
        sa.Column('authority_id', sa.String(length=36), nullable=True),
        sa.Column('category_codes', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['authority_id'], ['authorities.authority_id']),
        sa.PrimaryKeyConstraint('scheme_id')
    )
    op.create_index(op.f('ix_schemes_scheme_code'), 'schemes', ['scheme_code'], unique=True)

    # 4. Create scheme_versions table
    op.create_table(
        'scheme_versions',
        sa.Column('scheme_version_id', sa.String(length=36), nullable=False),
        sa.Column('scheme_id', sa.String(length=36), nullable=False),
        sa.Column('version_label', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('eligibility_mode', sa.String(length=50), nullable=False, server_default='DETERMINISTIC_RULES'),
        sa.Column('result_ceiling', sa.String(length=50), nullable=False, server_default='LIKELY_ELIGIBLE'),
        sa.Column('active_status', sa.Text(), nullable=False, server_default='ACTIVE'),
        sa.Column('effective_from', sa.Date(), nullable=True),
        sa.Column('effective_until', sa.Date(), nullable=True),
        sa.Column('source_last_updated_at', sa.DateTime(), nullable=True),
        sa.Column('last_verified_at', sa.DateTime(), nullable=True),
        sa.Column('review_due_at', sa.DateTime(), nullable=True),
        sa.Column('review_state', sa.String(length=50), server_default='APPROVED'),
        sa.Column('data_confidence', sa.String(length=50), server_default='HIGH'),
        sa.Column('official_information_url', sa.String(length=500), nullable=True),
        sa.Column('official_application_url', sa.String(length=500), nullable=True),
        sa.Column('version_payload', sa.JSON(), nullable=True),
        sa.Column('created_by', sa.String(length=100), server_default='SYSTEM_IMPORT'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['scheme_id'], ['schemes.scheme_id']),
        sa.PrimaryKeyConstraint('scheme_version_id')
    )
    op.create_index(op.f('ix_scheme_versions_scheme_id'), 'scheme_versions', ['scheme_id'], unique=False)

    # 5. Create source_documents table
    op.create_table(
        'source_documents',
        sa.Column('source_document_id', sa.String(length=36), nullable=False),
        sa.Column('source_code', sa.String(length=100), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('authority_name', sa.String(length=255), nullable=True),
        sa.Column('source_tier', sa.String(length=50), nullable=False, server_default='TIER_1_AUTHORITY'),
        sa.Column('document_type', sa.String(length=100), nullable=False, server_default='OFFICIAL_WEB_PAGE'),
        sa.Column('official_url', sa.String(length=500), nullable=False),
        sa.Column('language_code', sa.String(length=10), server_default='en'),
        sa.Column('content_sha256', sa.String(length=64), nullable=True),
        sa.Column('last_verified', sa.Text(), nullable=True),
        sa.Column('review_state', sa.String(length=50), server_default='APPROVED'),
        sa.Column('metadata_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('source_document_id')
    )
    op.create_index(op.f('ix_source_documents_source_code'), 'source_documents', ['source_code'], unique=True)

    # 6. Create eligibility_rule_sets table
    op.create_table(
        'eligibility_rule_sets',
        sa.Column('rule_set_id', sa.String(length=36), nullable=False),
        sa.Column('scheme_version_id', sa.String(length=36), nullable=False),
        sa.Column('rule_set_code', sa.String(length=100), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('result_ceiling', sa.String(length=50), nullable=False, server_default='LIKELY_ELIGIBLE'),
        sa.Column('official_verification_required', sa.Boolean(), server_default='true'),
        sa.Column('expression_json', sa.JSON(), nullable=False),
        sa.Column('effective_from', sa.Date(), nullable=True),
        sa.Column('effective_until', sa.Date(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['scheme_version_id'], ['scheme_versions.scheme_version_id']),
        sa.PrimaryKeyConstraint('rule_set_id')
    )
    op.create_index(op.f('ix_eligibility_rule_sets_rule_set_code'), 'eligibility_rule_sets', ['rule_set_code'], unique=True)
    op.create_index(op.f('ix_eligibility_rule_sets_scheme_version_id'), 'eligibility_rule_sets', ['scheme_version_id'], unique=False)

    # 7. Create scheme_benefits table
    op.create_table(
        'scheme_benefits',
        sa.Column('benefit_id', sa.String(length=36), nullable=False),
        sa.Column('scheme_version_id', sa.String(length=36), nullable=False),
        sa.Column('benefit_type', sa.String(length=100), server_default='GENERAL'),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('amount', sa.Numeric(14, 2), nullable=True),
        sa.Column('currency', sa.String(length=10), server_default='INR'),
        sa.Column('period', sa.String(length=50), nullable=True),
        sa.Column('details_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['scheme_version_id'], ['scheme_versions.scheme_version_id']),
        sa.PrimaryKeyConstraint('benefit_id')
    )
    op.create_index(op.f('ix_scheme_benefits_scheme_version_id'), 'scheme_benefits', ['scheme_version_id'], unique=False)

    # 8. Create assistance_capabilities table
    op.create_table(
        'assistance_capabilities',
        sa.Column('capability_id', sa.String(length=36), nullable=False),
        sa.Column('capability_code', sa.String(length=100), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('facility_service_code', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('capability_id')
    )
    op.create_index(op.f('ix_assistance_capabilities_capability_code'), 'assistance_capabilities', ['capability_code'], unique=True)
    op.create_index(op.f('ix_assistance_capabilities_facility_service_code'), 'assistance_capabilities', ['facility_service_code'], unique=False)

    # 9. Create scheme_assistance_capabilities table
    op.create_table(
        'scheme_assistance_capabilities',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('scheme_version_id', sa.String(length=36), nullable=False),
        sa.Column('capability_id', sa.String(length=36), nullable=False),
        sa.Column('required_level', sa.String(length=50), server_default='REQUIRED'),
        sa.Column('assistance_type', sa.String(length=100), server_default='IN_PERSON'),
        sa.Column('source_reference', sa.String(length=255), server_default='Official Government Scheme Guideline 2026'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['scheme_version_id'], ['scheme_versions.scheme_version_id']),
        sa.ForeignKeyConstraint(['capability_id'], ['assistance_capabilities.capability_id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_scheme_assistance_capabilities_scheme_version_id'), 'scheme_assistance_capabilities', ['scheme_version_id'], unique=False)
    op.create_index(op.f('ix_scheme_assistance_capabilities_capability_id'), 'scheme_assistance_capabilities', ['capability_id'], unique=False)

    # 10. Create scheme_evaluations table
    op.create_table(
        'scheme_evaluations',
        sa.Column('evaluation_id', sa.String(length=36), nullable=False),
        sa.Column('citizen_id', sa.String(length=36), nullable=True),
        sa.Column('household_member_id', sa.String(length=36), nullable=True),
        sa.Column('beneficiary_type', sa.String(length=50), server_default='MYSELF'),
        sa.Column('beneficiary_name', sa.String(length=255), nullable=True),
        sa.Column('case_id', sa.String(length=36), nullable=True),
        sa.Column('evaluator_user_id', sa.String(length=36), nullable=True),
        sa.Column('evaluator_role', sa.String(length=50), server_default='CITIZEN'),
        sa.Column('normalized_fact_hash', sa.String(length=64), nullable=False),
        sa.Column('input_facts_json', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['citizen_id'], ['citizen_profiles.id']),
        sa.PrimaryKeyConstraint('evaluation_id')
    )
    op.create_index(op.f('ix_scheme_evaluations_citizen_id'), 'scheme_evaluations', ['citizen_id'], unique=False)
    op.create_index(op.f('ix_scheme_evaluations_case_id'), 'scheme_evaluations', ['case_id'], unique=False)
    op.create_index(op.f('ix_scheme_evaluations_normalized_fact_hash'), 'scheme_evaluations', ['normalized_fact_hash'], unique=False)

    # 11. Create scheme_evaluation_results table
    op.create_table(
        'scheme_evaluation_results',
        sa.Column('result_id', sa.String(length=36), nullable=False),
        sa.Column('evaluation_id', sa.String(length=36), nullable=False),
        sa.Column('scheme_id', sa.String(length=36), nullable=False),
        sa.Column('scheme_code', sa.String(length=100), nullable=False),
        sa.Column('scheme_version_id', sa.String(length=36), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('explanation', sa.Text(), nullable=True),
        sa.Column('matched_rules_json', sa.JSON(), nullable=True),
        sa.Column('failed_rules_json', sa.JSON(), nullable=True),
        sa.Column('unknown_rules_json', sa.JSON(), nullable=True),
        sa.Column('missing_fields_json', sa.JSON(), nullable=True),
        sa.Column('benefits_json', sa.JSON(), nullable=True),
        sa.Column('documents_json', sa.JSON(), nullable=True),
        sa.Column('access_steps_json', sa.JSON(), nullable=True),
        sa.Column('official_urls_json', sa.JSON(), nullable=True),
        sa.Column('last_verified', sa.Text(), nullable=True),
        sa.Column('disclaimer', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['evaluation_id'], ['scheme_evaluations.evaluation_id']),
        sa.PrimaryKeyConstraint('result_id')
    )
    op.create_index(op.f('ix_scheme_evaluation_results_evaluation_id'), 'scheme_evaluation_results', ['evaluation_id'], unique=False)
    op.create_index(op.f('ix_scheme_evaluation_results_scheme_id'), 'scheme_evaluation_results', ['scheme_id'], unique=False)


def downgrade() -> None:
    op.drop_table('scheme_evaluation_results')
    op.drop_table('scheme_evaluations')
    op.drop_table('scheme_assistance_capabilities')
    op.drop_table('assistance_capabilities')
    op.drop_table('scheme_benefits')
    op.drop_table('eligibility_rule_sets')
    op.drop_table('source_documents')
    op.drop_table('scheme_versions')
    op.drop_table('schemes')
    op.drop_table('authorities')
    op.drop_index(op.f('ix_citizen_profiles_phone'), table_name='citizen_profiles')
