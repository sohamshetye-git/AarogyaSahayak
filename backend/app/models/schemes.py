import uuid
from datetime import datetime, timezone
import enum
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, Date, ForeignKey, Text, Enum, JSON, Numeric
)
from sqlalchemy.orm import relationship
from app.database import Base

def generate_uuid() -> str:
    return str(uuid.uuid4())

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class GovernmentLevelEnum(str, enum.Enum):
    CENTRAL = 'CENTRAL'
    STATE = 'STATE'
    DISTRICT = 'DISTRICT'
    CENTRAL_STATE = 'CENTRAL_STATE'
    OTHER = 'OTHER'

class ReviewStateEnum(str, enum.Enum):
    DRAFT = 'DRAFT'
    IN_REVIEW = 'IN_REVIEW'
    APPROVED = 'APPROVED'
    BLOCKED = 'BLOCKED'
    SUPERSEDED = 'SUPERSEDED'
    RETIRED = 'RETIRED'

class SourceTierEnum(str, enum.Enum):
    TIER_1_AUTHORITY = 'TIER_1_AUTHORITY'
    TIER_2_VERIFICATION = 'TIER_2_VERIFICATION'
    TIER_3_AGGREGATOR = 'TIER_3_AGGREGATOR'
    TIER_4_STATE_DISTRICT = 'TIER_4_STATE_DISTRICT'
    TIER_5_DISCOVERY = 'TIER_5_DISCOVERY'

class EligibilityOutputEnum(str, enum.Enum):
    SERVICE_AVAILABLE = 'SERVICE_AVAILABLE'
    LIKELY_ELIGIBLE = 'LIKELY_ELIGIBLE'
    POTENTIALLY_ELIGIBLE = 'POTENTIALLY_ELIGIBLE'
    MORE_INFORMATION_REQUIRED = 'MORE_INFORMATION_REQUIRED'
    OFFICIAL_VERIFICATION_REQUIRED = 'OFFICIAL_VERIFICATION_REQUIRED'
    VERIFIED_ELIGIBLE = 'VERIFIED_ELIGIBLE'
    NOT_ELIGIBLE = 'NOT_ELIGIBLE'
    NOT_APPLICABLE = 'NOT_APPLICABLE'
    SOURCE_REVIEW_REQUIRED = 'SOURCE_REVIEW_REQUIRED'

class AuthorityModel(Base):
    __tablename__ = 'authorities'

    authority_id = Column(String(36), primary_key=True, default=generate_uuid)
    authority_code = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    authority_type = Column(String(100), nullable=False)
    government_level = Column(Enum(GovernmentLevelEnum), nullable=False)
    official_url = Column(String(500), nullable=False)
    contact_json = Column(JSON, default=dict)
    created_at = Column(DateTime, default=utc_now)

class SchemeModel(Base):
    __tablename__ = 'schemes'

    scheme_id = Column(String(36), primary_key=True, default=generate_uuid)
    scheme_code = Column(String(100), unique=True, nullable=False, index=True)
    canonical_name = Column(String(255), nullable=False)
    short_name = Column(String(100), nullable=True)
    entity_type = Column(String(100), nullable=False)
    authority_id = Column(String(36), ForeignKey('authorities.authority_id'), nullable=True)
    category_codes = Column(JSON, default=list)
    created_at = Column(DateTime, default=utc_now)

    versions = relationship('SchemeVersionModel', back_populates='scheme', cascade='all, delete-orphan')

class SchemeVersionModel(Base):
    __tablename__ = 'scheme_versions'

    scheme_version_id = Column(String(36), primary_key=True, default=generate_uuid)
    scheme_id = Column(String(36), ForeignKey('schemes.scheme_id'), nullable=False, index=True)
    version_label = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    eligibility_mode = Column(String(128), nullable=False, default='DETERMINISTIC_RULES')
    result_ceiling = Column(Enum(EligibilityOutputEnum), nullable=False, default=EligibilityOutputEnum.LIKELY_ELIGIBLE)
    active_status = Column(Text, nullable=False, default='ACTIVE')
    effective_from = Column(Date, nullable=True)
    effective_until = Column(Date, nullable=True)
    source_last_updated_at = Column(DateTime, nullable=True)
    last_verified_at = Column(DateTime, default=utc_now)
    review_due_at = Column(DateTime, nullable=True)
    review_state = Column(Enum(ReviewStateEnum), default=ReviewStateEnum.APPROVED)
    data_confidence = Column(String(50), default='HIGH')
    official_information_url = Column(String(500), nullable=True)
    official_application_url = Column(String(500), nullable=True)
    version_payload = Column(JSON, default=dict)
    created_by = Column(String(100), default='SYSTEM_IMPORT')
    created_at = Column(DateTime, default=utc_now)

    scheme = relationship('SchemeModel', back_populates='versions')
    rule_sets = relationship('EligibilityRuleSetModel', back_populates='scheme_version', cascade='all, delete-orphan')
    benefits = relationship('SchemeBenefitModel', back_populates='scheme_version', cascade='all, delete-orphan')
    assistance_capabilities = relationship('SchemeAssistanceCapabilityModel', back_populates='scheme_version', cascade='all, delete-orphan')


class SourceDocumentModel(Base):
    __tablename__ = 'source_documents'

    source_document_id = Column(String(36), primary_key=True, default=generate_uuid)
    source_code = Column(String(100), unique=True, nullable=False, index=True)
    title = Column(String(255), nullable=False)
    authority_name = Column(String(255), nullable=True)
    source_tier = Column(Enum(SourceTierEnum), nullable=False, default=SourceTierEnum.TIER_1_AUTHORITY)
    document_type = Column(String(100), nullable=False, default='OFFICIAL_WEB_PAGE')
    official_url = Column(String(500), nullable=False)
    language_code = Column(String(10), default='en')
    content_sha256 = Column(String(64), nullable=True)
    last_verified = Column(Text, nullable=True)
    review_state = Column(Enum(ReviewStateEnum), default=ReviewStateEnum.APPROVED)
    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime, default=utc_now)

class EligibilityRuleSetModel(Base):
    __tablename__ = 'eligibility_rule_sets'

    rule_set_id = Column(String(36), primary_key=True, default=generate_uuid)
    scheme_version_id = Column(String(36), ForeignKey('scheme_versions.scheme_version_id'), nullable=False, index=True)
    rule_set_code = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    result_ceiling = Column(Enum(EligibilityOutputEnum), nullable=False, default=EligibilityOutputEnum.LIKELY_ELIGIBLE)
    official_verification_required = Column(Boolean, default=True)
    expression_json = Column(JSON, nullable=False)
    effective_from = Column(Date, nullable=True)
    effective_until = Column(Date, nullable=True)
    created_at = Column(DateTime, default=utc_now)

    scheme_version = relationship('SchemeVersionModel', back_populates='rule_sets')

class SchemeBenefitModel(Base):
    __tablename__ = 'scheme_benefits'

    benefit_id = Column(String(36), primary_key=True, default=generate_uuid)
    scheme_version_id = Column(String(36), ForeignKey('scheme_versions.scheme_version_id'), nullable=False, index=True)
    benefit_type = Column(String(100), default='GENERAL')
    description = Column(Text, nullable=False)
    amount = Column(Numeric(14, 2), nullable=True)
    currency = Column(String(10), default='INR')
    period = Column(String(50), nullable=True)
    details_json = Column(JSON, default=dict)
    created_at = Column(DateTime, default=utc_now)

    scheme_version = relationship('SchemeVersionModel', back_populates='benefits')

class SchemeEvaluationModel(Base):
    __tablename__ = 'scheme_evaluations'

    evaluation_id = Column(String(36), primary_key=True, default=generate_uuid)
    citizen_id = Column(String(36), ForeignKey('citizen_profiles.id'), nullable=True, index=True)
    household_member_id = Column(String(36), ForeignKey('household_members.id'), nullable=True, index=True)
    beneficiary_type = Column(String(50), default='MYSELF') # MYSELF, SPOUSE, CHILD, PARENT, MEMBER
    beneficiary_name = Column(String(255), nullable=True)
    case_id = Column(String(36), nullable=True, index=True)
    evaluator_user_id = Column(String(36), nullable=True)
    evaluator_role = Column(String(50), default='CITIZEN')
    normalized_fact_hash = Column(String(64), nullable=False, index=True)
    input_facts_json = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=utc_now)

    results = relationship('SchemeEvaluationResultModel', back_populates='evaluation', cascade='all, delete-orphan')

class SchemeEvaluationResultModel(Base):
    __tablename__ = 'scheme_evaluation_results'

    result_id = Column(String(36), primary_key=True, default=generate_uuid)
    evaluation_id = Column(String(36), ForeignKey('scheme_evaluations.evaluation_id'), nullable=False, index=True)
    scheme_id = Column(String(36), nullable=False, index=True)
    scheme_code = Column(String(100), nullable=False)
    scheme_version_id = Column(String(36), nullable=False)
    status = Column(Enum(EligibilityOutputEnum), nullable=False)
    explanation = Column(Text, nullable=True)
    matched_rules_json = Column(JSON, default=list)
    failed_rules_json = Column(JSON, default=list)
    unknown_rules_json = Column(JSON, default=list)
    missing_fields_json = Column(JSON, default=list)
    benefits_json = Column(JSON, default=list)
    documents_json = Column(JSON, default=list)
    access_steps_json = Column(JSON, default=list)
    official_urls_json = Column(JSON, default=dict)
    last_verified = Column(Text, nullable=True)
    disclaimer = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now)

    evaluation = relationship('SchemeEvaluationModel', back_populates='results')

class SchemeScreeningSessionModel(Base):
    __tablename__ = 'scheme_screening_sessions'

    id = Column(String(36), primary_key=True, default=generate_uuid)
    session_reference = Column(String(100), unique=True, nullable=False, index=True)
    citizen_id = Column(String(36), ForeignKey('citizen_profiles.id'), nullable=False, index=True)
    household_member_id = Column(String(36), ForeignKey('household_members.id'), nullable=True, index=True)
    beneficiary_type = Column(String(50), default='MYSELF') # MYSELF, SPOUSE, CHILD, PARENT, MEMBER
    beneficiary_name = Column(String(255), nullable=True)
    target_scheme_code = Column(String(100), nullable=True)
    status = Column(String(50), default='IN_PROGRESS') # IN_PROGRESS, COMPLETED, ABANDONED
    facts_json = Column(JSON, default=dict)
    answered_questions_json = Column(JSON, default=list)
    last_evaluated_results_json = Column(JSON, default=list)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

class SavedSchemeModel(Base):
    __tablename__ = 'saved_schemes'

    id = Column(String(36), primary_key=True, default=generate_uuid)
    citizen_id = Column(String(36), ForeignKey('citizen_profiles.id'), nullable=False, index=True)
    household_member_id = Column(String(36), ForeignKey('household_members.id'), nullable=True)
    scheme_code = Column(String(100), nullable=False, index=True)
    scheme_name = Column(String(255), nullable=False)
    notes = Column(Text, nullable=True)
    saved_status = Column(String(50), default='LIKELY_ELIGIBLE')
    created_at = Column(DateTime, default=utc_now)

class SchemeAssistanceRequestModel(Base):
    __tablename__ = 'scheme_assistance_requests'

    id = Column(String(36), primary_key=True, default=generate_uuid)
    request_reference = Column(String(100), unique=True, nullable=False, index=True)
    citizen_id = Column(String(36), ForeignKey('citizen_profiles.id'), nullable=False, index=True)
    household_member_id = Column(String(36), ForeignKey('household_members.id'), nullable=True)
    beneficiary_name = Column(String(255), nullable=True)
    scheme_code = Column(String(100), nullable=False, index=True)
    scheme_name = Column(String(255), nullable=False)
    screening_id = Column(String(36), nullable=True)
    current_screening_status = Column(String(50), default='MORE_INFORMATION_REQUIRED')
    missing_facts = Column(JSON, default=list)
    missing_documents = Column(JSON, default=list)
    preferred_contact_method = Column(String(50), default='HOME_VISIT') # HOME_VISIT, PHONE_CALL, PHC_MEETING
    consent_given = Column(Boolean, default=True)
    assigned_worker_id = Column(String(36), nullable=True)
    assigned_worker_name = Column(String(255), default='Sita Patel (Kalyanpur)')
    due_date = Column(DateTime, nullable=True)
    status = Column(String(50), default='PENDING') # PENDING, SCHEDULED, IN_PROGRESS, COMPLETED, CANCELLED
    notes = Column(Text, nullable=True)
    outcome_summary = Column(Text, nullable=True)
    official_reference_recorded = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

class SchemeApplicationTrackingModel(Base):
    __tablename__ = 'scheme_application_trackings'

    id = Column(String(36), primary_key=True, default=generate_uuid)
    application_reference = Column(String(100), unique=True, nullable=False, index=True)
    citizen_id = Column(String(36), ForeignKey('citizen_profiles.id'), nullable=False, index=True)
    household_member_id = Column(String(36), ForeignKey('household_members.id'), nullable=True)
    beneficiary_name = Column(String(255), nullable=True)
    scheme_code = Column(String(100), nullable=False, index=True)
    scheme_name = Column(String(255), nullable=False)
    status = Column(String(50), default='READY_TO_APPLY')
    # Status progression: SCREENING_STARTED, SCREENING_COMPLETED, INFORMATION_REQUIRED, DOCUMENTS_PENDING,
    # ASHA_ASSISTANCE_REQUESTED, READY_TO_APPLY, REFERRED_TO_OFFICIAL_CHANNEL, APPLICATION_SUBMITTED,
    # OFFICIAL_VERIFICATION_PENDING, APPROVED, REJECTED, BENEFIT_RECEIVED, CLOSED
    official_application_number = Column(String(100), nullable=True)
    official_portal_url = Column(String(500), nullable=True)
    assigned_asha_name = Column(String(255), default='Sita Patel')
    missing_documents = Column(JSON, default=list)
    next_action_instructions = Column(Text, nullable=True)
    last_update_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

class SchemeVerificationModel(Base):
    __tablename__ = 'scheme_verifications'

    verification_id = Column(String(36), primary_key=True, default=generate_uuid)
    citizen_id = Column(String(36), ForeignKey('citizen_profiles.id'), nullable=False, index=True)
    scheme_code = Column(String(100), nullable=False, index=True)
    verification_status = Column(Enum(EligibilityOutputEnum), default=EligibilityOutputEnum.VERIFIED_ELIGIBLE)
    verification_method = Column(String(150), nullable=False)
    verification_reference = Column(String(100), nullable=False)
    verified_by_user_id = Column(String(36), nullable=False)
    verified_at = Column(DateTime, default=utc_now)
    notes = Column(Text, nullable=True)

class AssistanceCapabilityModel(Base):
    __tablename__ = 'assistance_capabilities'

    capability_id = Column(String(36), primary_key=True, default=generate_uuid)
    capability_code = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    facility_service_code = Column(String(100), nullable=True, index=True)
    created_at = Column(DateTime, default=utc_now)

    scheme_mappings = relationship('SchemeAssistanceCapabilityModel', back_populates='capability', cascade='all, delete-orphan')

class SchemeAssistanceCapabilityModel(Base):
    __tablename__ = 'scheme_assistance_capabilities'

    id = Column(String(36), primary_key=True, default=generate_uuid)
    scheme_version_id = Column(String(36), ForeignKey('scheme_versions.scheme_version_id'), nullable=False, index=True)
    capability_id = Column(String(36), ForeignKey('assistance_capabilities.capability_id'), nullable=False, index=True)
    required_level = Column(String(50), default='REQUIRED') # REQUIRED, OPTIONAL, PREFERRED
    assistance_type = Column(String(100), default='IN_PERSON') # IN_PERSON, APPLICATION_ASSISTANCE, VERIFICATION, ESCALATION
    source_reference = Column(String(255), default='Official Government Scheme Guideline 2026')
    created_at = Column(DateTime, default=utc_now)

    scheme_version = relationship('SchemeVersionModel', back_populates='assistance_capabilities')
    capability = relationship('AssistanceCapabilityModel', back_populates='scheme_mappings')

