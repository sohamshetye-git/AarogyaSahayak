import uuid
from datetime import datetime, timezone
import enum
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Text, Enum, JSON
)
from sqlalchemy.orm import relationship
from app.database import Base

def generate_uuid() -> str:
    return str(uuid.uuid4())

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class UserRoleEnum(str, enum.Enum):
    CITIZEN = "CITIZEN"
    ASHA_WORKER = "ASHA_WORKER"
    PHC_DOCTOR = "PHC_DOCTOR"
    DISTRICT_ADMIN = "DISTRICT_ADMIN"
    SYSTEM_ADMIN = "SYSTEM_ADMIN"

class CasePriorityEnum(str, enum.Enum):
    URGENT = "URGENT"
    HIGH = "HIGH"
    FOLLOW_UP = "FOLLOW_UP"
    ROUTINE = "ROUTINE"
    INFORMATION = "INFORMATION"

class CaseStatusEnum(str, enum.Enum):
    NEW = "NEW"
    ASHA_ASSIGNED = "ASHA_ASSIGNED"
    ASHA_ACKNOWLEDGED = "ASHA_ACKNOWLEDGED"
    CITIZEN_CONTACTED = "CITIZEN_CONTACTED"
    VISIT_SCHEDULED = "VISIT_SCHEDULED"
    VISIT_IN_PROGRESS = "VISIT_IN_PROGRESS"
    ASHA_REVIEWED = "ASHA_REVIEWED"
    REFERRED_TO_PHC = "REFERRED_TO_PHC"
    DOCTOR_ACKNOWLEDGED = "DOCTOR_ACKNOWLEDGED"
    PATIENT_ARRIVED = "PATIENT_ARRIVED"
    CONSULTATION_IN_PROGRESS = "CONSULTATION_IN_PROGRESS"
    FOLLOW_UP_REQUIRED = "FOLLOW_UP_REQUIRED"
    REFERRED_TO_HIGHER_FACILITY = "REFERRED_TO_HIGHER_FACILITY"
    COMPLETED = "COMPLETED"
    UNREACHABLE = "UNREACHABLE"
    DECLINED = "DECLINED"
    PENDING_SYNC = "PENDING_SYNC"

class InformationSourceEnum(str, enum.Enum):
    CITIZEN_REPORTED = "CITIZEN_REPORTED"
    ASHA_CONFIRMED = "ASHA_CONFIRMED"
    DEVICE_MEASURED = "DEVICE_MEASURED"
    AI_EXTRACTED = "AI_EXTRACTED"
    RULE_GENERATED = "RULE_GENERATED"
    DOCTOR_CONFIRMED = "DOCTOR_CONFIRMED"

class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    identifier = Column(String(100), unique=True, index=True, nullable=False) # username or phone
    name = Column(String(150), nullable=False)
    phone = Column(String(20), nullable=True, index=True)
    email = Column(String(150), nullable=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum(UserRoleEnum), nullable=False, default=UserRoleEnum.CITIZEN)
    preferred_language = Column(String(10), default="mr-IN")
    is_active = Column(Boolean, default=True)
    account_status = Column(String(50), default="ACTIVE") # ACTIVE, SUSPENDED
    staff_id = Column(String(50), unique=True, index=True, nullable=True)
    must_change_password = Column(Boolean, default=False)
    created_by_admin_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    last_login_at = Column(DateTime, nullable=True)
    password_changed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    citizen_profile = relationship("CitizenProfile", back_populates="user", uselist=False)
    worker_profile = relationship("WorkerProfile", back_populates="user", uselist=False, foreign_keys="[WorkerProfile.user_id]")

class CitizenProfile(Base):
    __tablename__ = "citizen_profiles"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True, unique=True, index=True)
    display_name = Column(String(150), nullable=False)
    legal_name = Column(String(150), nullable=True)
    preferred_name = Column(String(150), nullable=True)
    date_of_birth = Column(String(20), nullable=True) # YYYY-MM-DD
    age_estimate = Column(Integer, nullable=True)
    sex = Column(String(20), nullable=True)
    phone = Column(String(20), nullable=True, index=True)
    alternate_phone = Column(String(20), nullable=True)
    preferred_contact_method = Column(String(30), default="PHONE")
    abha_reference = Column(String(50), unique=True, nullable=True, index=True)
    
    # Location
    address = Column(Text, nullable=True)
    current_care_location = Column(String(255), nullable=True)
    village_id = Column(String(36), nullable=True)
    village_name = Column(String(150), default="Kalyanpur")
    pincode = Column(String(10), nullable=True)
    state = Column(String(100), default="Maharashtra")
    district = Column(String(100), default="District 04")
    block_taluka = Column(String(100), default="Kalyanpur Block")
    gram_panchayat = Column(String(100), default="Kalyanpur GP")
    sub_center_id = Column(String(36), nullable=True)
    assigned_facility_id = Column(String(36), nullable=True)
    assigned_asha_id = Column(String(36), nullable=True, index=True)
    
    # Emergency Contact
    emergency_contact_name = Column(String(150), nullable=True)
    emergency_contact_phone = Column(String(20), nullable=True)
    emergency_contact_relation = Column(String(50), nullable=True)
    
    # Household & Demographics
    head_of_household_name = Column(String(150), nullable=True)
    head_of_household_relation = Column(String(50), nullable=True)
    family_id = Column(String(50), nullable=True)
    household_category = Column(String(50), default="OTHER") # PRIORITY, BPL, ANTYODAYA, OTHER
    ration_card_category = Column(String(50), nullable=True) # YELLOW, ORANGE, WHITE
    preferred_language = Column(String(10), default="mr-IN")
    literacy_assistance_needed = Column(Boolean, default=False)
    accessibility_needs = Column(Text, nullable=True)
    
    # Consent
    registration_consent_obtained = Column(Boolean, default=False)
    voice_consent_obtained = Column(Boolean, default=False)
    consent_method = Column(String(30), default="VERBAL") # VERBAL, WRITTEN, GUARDIAN_ASSISTED
    guardian_name = Column(String(150), nullable=True)
    guardian_relation = Column(String(50), nullable=True)
    consent_timestamp = Column(DateTime, nullable=True)
    
    # Health Profile
    blood_group = Column(String(10), nullable=True) # A+, A-, B+, B-, AB+, AB-, O+, O-, UNKNOWN
    allergies = Column(JSON, default=list) # list of allergy strings
    chronic_conditions = Column(JSON, default=list) # list of chronic conditions
    current_medications = Column(JSON, default=list) # list of dicts: name, dose, frequency
    disability_notes = Column(Text, nullable=True)
    previous_illnesses = Column(Text, nullable=True)
    previous_surgeries = Column(Text, nullable=True)
    tobacco_use = Column(String(50), default="NONE")
    alcohol_use = Column(String(50), default="NONE")
    programme_enrollments = Column(JSON, default=list) # list of programme codes
    health_notes = Column(Text, nullable=True)
    
    # Special condition status
    is_pregnant = Column(Boolean, default=False)
    gestational_weeks = Column(Integer, nullable=True)
    anc_registration_number = Column(String(50), nullable=True)
    language_confirmed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    user = relationship("User", back_populates="citizen_profile")
    cases = relationship("Case", back_populates="citizen")
    attachments = relationship("CitizenAttachment", back_populates="citizen", cascade="all, delete-orphan")
    follow_ups = relationship("FollowUp", back_populates="citizen", cascade="all, delete-orphan")
    prescriptions = relationship("Prescription", back_populates="citizen", cascade="all, delete-orphan")
    household_members = relationship("HouseholdMember", foreign_keys="[HouseholdMember.citizen_id]", back_populates="citizen", cascade="all, delete-orphan")
    chat_sessions = relationship("CitizenChatSession", back_populates="citizen", cascade="all, delete-orphan")
    needs = relationship("CitizenNeed", back_populates="citizen", cascade="all, delete-orphan")
    service_requests = relationship("ServiceRequest", back_populates="citizen", cascade="all, delete-orphan")

class CitizenAttachment(Base):
    __tablename__ = "citizen_attachments"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    citizen_id = Column(String(36), ForeignKey("citizen_profiles.id"), nullable=False, index=True)
    case_id = Column(String(36), nullable=True, index=True)
    document_type = Column(String(50), nullable=False) # MCP_CARD, VACCINATION_CARD, PRESCRIPTION, LAB_REPORT, REFERRAL_DOC, OTHER
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(255), nullable=False)
    file_size = Column(Integer, default=0)
    mime_type = Column(String(100), default="application/pdf")
    uploaded_by = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=utc_now)

    citizen = relationship("CitizenProfile", back_populates="attachments")

class WorkerProfile(Base):
    __tablename__ = "worker_profiles"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    worker_type = Column(String(50), nullable=False) # ASHA, DOCTOR, ADMIN
    facility_id = Column(String(36), nullable=True)
    facility_name = Column(String(150), nullable=True)
    district_id = Column(String(36), nullable=True)
    district_name = Column(String(150), default="District 04")
    village_ids = Column(JSON, nullable=True) # List of assigned village IDs
    village_name = Column(String(150), nullable=True)
    coverage_area = Column(String(200), nullable=True)
    professional_registration = Column(String(100), nullable=True) # e.g. medical registration number
    employee_id = Column(String(50), unique=True, index=True, nullable=True)
    specialization = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=utc_now)

    user = relationship("User", back_populates="worker_profile", foreign_keys=[user_id])

# Import Facility models
from app.models.facilities import (
    FacilityTypeEnum, FacilityOwnershipEnum, VerificationStatusEnum,
    ServiceAvailabilityStatusEnum, AssistanceStatusEnum, AppointmentStatusEnum,
    Facility, FacilityService, FacilityHours, FacilitySchemeEmpanelment,
    FacilitySearch, FacilityCallEvent, FacilityAssistanceRequest, FacilityAppointmentRequest,
    UserLocationPreference, CareRequestLocation, VisitLocation
)



class Case(Base):
    __tablename__ = "cases"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    reference = Column(String(50), unique=True, index=True, nullable=False) # e.g. CASE-2026-001
    citizen_id = Column(String(36), ForeignKey("citizen_profiles.id"), nullable=False, index=True)
    priority = Column(Enum(CasePriorityEnum), nullable=False, default=CasePriorityEnum.ROUTINE, index=True)
    status = Column(Enum(CaseStatusEnum), nullable=False, default=CaseStatusEnum.NEW, index=True)
    primary_concern = Column(Text, nullable=False)
    preferred_language = Column(String(10), default="mr-IN")
    
    # Assignment
    assigned_asha_id = Column(String(36), nullable=True, index=True)
    assigned_asha_name = Column(String(150), nullable=True)
    assigned_facility_id = Column(String(36), nullable=True, index=True)
    assigned_facility_name = Column(String(150), nullable=True)
    assigned_doctor_id = Column(String(36), nullable=True, index=True)
    assigned_doctor_name = Column(String(150), nullable=True)
    
    # Safety and guidance
    safety_rule_triggered = Column(Boolean, default=False)
    safety_rule_reason = Column(Text, nullable=True)
    citizen_guidance_text = Column(Text, nullable=True)
    
    version = Column(Integer, default=1)
    created_at = Column(DateTime, default=utc_now, index=True)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)
    completed_at = Column(DateTime, nullable=True)

    citizen = relationship("CitizenProfile", back_populates="cases")
    symptoms = relationship("SymptomObservation", back_populates="case", cascade="all, delete-orphan")
    vitals = relationship("VitalRecord", back_populates="case", cascade="all, delete-orphan")
    visits = relationship("AshaVisit", back_populates="case")
    referrals = relationship("Referral", back_populates="case")
    consultations = relationship("Consultation", back_populates="case")
    follow_ups = relationship("FollowUp", back_populates="case")
    prescriptions = relationship("Prescription", back_populates="case", cascade="all, delete-orphan")

class SymptomObservation(Base):
    __tablename__ = "symptom_observations"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    case_id = Column(String(36), ForeignKey("cases.id"), nullable=False, index=True)
    spoken_term = Column(String(200), nullable=True)
    normalized_term = Column(String(200), nullable=False)
    severity = Column(String(50), nullable=True)
    duration_text = Column(String(100), nullable=True)
    source_type = Column(Enum(InformationSourceEnum), default=InformationSourceEnum.CITIZEN_REPORTED)
    recorded_by = Column(String(100), nullable=True)
    recorded_at = Column(DateTime, default=utc_now)

    case = relationship("Case", back_populates="symptoms")

class VitalRecord(Base):
    __tablename__ = "vital_records"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    case_id = Column(String(36), ForeignKey("cases.id"), nullable=False, index=True)
    visit_id = Column(String(36), nullable=True)
    systolic_bp = Column(Integer, nullable=True)
    diastolic_bp = Column(Integer, nullable=True)
    temperature_c = Column(Float, nullable=True)
    spo2 = Column(Integer, nullable=True)
    pulse = Column(Integer, nullable=True)
    respiratory_rate = Column(Integer, nullable=True)
    glucose_mg_dl = Column(Float, nullable=True)
    weight_kg = Column(Float, nullable=True)
    is_warning_sign = Column(Boolean, default=False)
    source_type = Column(Enum(InformationSourceEnum), default=InformationSourceEnum.DEVICE_MEASURED)
    recorded_by = Column(String(100), nullable=True)
    recorded_at = Column(DateTime, default=utc_now)

    case = relationship("Case", back_populates="vitals")

class AshaVisit(Base):
    __tablename__ = "asha_visits"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    reference = Column(String(50), unique=True, index=True) # e.g. VISIT-2026-001
    case_id = Column(String(36), ForeignKey("cases.id"), nullable=False, index=True)
    asha_worker_id = Column(String(36), nullable=False, index=True)
    visit_type = Column(String(50), default="URGENT_TRIAGE")
    status = Column(String(50), default="COMPLETED")
    scheduled_at = Column(DateTime, nullable=True)
    started_at = Column(DateTime, default=utc_now)
    completed_at = Column(DateTime, default=utc_now)
    consent_obtained = Column(Boolean, default=True)
    notes = Column(Text, nullable=True)
    next_action = Column(String(100), default="REFER_TO_PHC")
    offline_client_id = Column(String(100), nullable=True)
    version = Column(Integer, default=1)
    created_at = Column(DateTime, default=utc_now)

    case = relationship("Case", back_populates="visits")

class Referral(Base):
    __tablename__ = "referrals"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    reference = Column(String(50), unique=True, index=True) # e.g. REF-2026-001
    case_id = Column(String(36), ForeignKey("cases.id"), nullable=False, index=True)
    from_asha_id = Column(String(36), nullable=True)
    from_doctor_id = Column(String(36), nullable=True)
    to_facility_id = Column(String(36), nullable=False, index=True)
    to_facility_name = Column(String(200), default="Kalyanpur PHC")
    urgency = Column(Enum(CasePriorityEnum), default=CasePriorityEnum.URGENT)
    reason = Column(Text, nullable=False)
    status = Column(String(50), default="PENDING_DOCTOR_REVIEW", index=True) # PENDING_DOCTOR_REVIEW, ACKNOWLEDGED, CONSULTED
    acknowledged_by = Column(String(100), nullable=True)
    acknowledged_at = Column(DateTime, nullable=True)
    arrived_at = Column(DateTime, nullable=True)
    transport_assistance_required = Column(Boolean, default=False)
    citizen_response = Column(String(50), default="ACCEPTED")
    refusal_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now)

    case = relationship("Case", back_populates="referrals")
    follow_ups = relationship("FollowUp", back_populates="referral", cascade="all, delete-orphan")
    prescriptions = relationship("Prescription", back_populates="referral")

class Consultation(Base):
    __tablename__ = "consultations"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    reference = Column(String(50), unique=True, index=True) # e.g. CONS-2026-001
    case_id = Column(String(36), ForeignKey("cases.id"), nullable=False, index=True)
    doctor_id = Column(String(36), nullable=False, index=True)
    doctor_name = Column(String(150), default="Dr. Abhinav Sharma")
    facility_id = Column(String(36), nullable=False)
    consultation_type = Column(String(50), default="IN_PERSON_PHC")
    status = Column(String(50), default="COMPLETED") # IN_PROGRESS, COMPLETED
    examination_notes = Column(Text, nullable=True)
    clinical_summary = Column(Text, nullable=True)
    provisional_diagnosis = Column(String(255), nullable=True)
    confirmed_diagnosis = Column(String(255), nullable=True)
    icd10_code = Column(String(50), nullable=True)
    care_plan_summary = Column(Text, nullable=True)
    asha_followup_instructions = Column(Text, nullable=True)
    followup_due_days = Column(Integer, default=3)
    started_at = Column(DateTime, default=utc_now)
    completed_at = Column(DateTime, default=utc_now)
    signed_at = Column(DateTime, default=utc_now)
    version = Column(Integer, default=1)
    created_at = Column(DateTime, default=utc_now)

    case = relationship("Case", back_populates="consultations")
    prescriptions = relationship("Prescription", back_populates="consultation", cascade="all, delete-orphan")
    test_orders = relationship("TestOrder", back_populates="consultation", cascade="all, delete-orphan")

class MedicineCatalog(Base):
    __tablename__ = "medicine_catalog"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    generic_name = Column(String(200), nullable=False, index=True)
    brand_name = Column(String(200), nullable=True)
    formulation = Column(String(100), nullable=False, default="Tablet") # Tablet, Syrup, Injection, Ointment, Capsule, Drops, Inhaler
    strength_options = Column(JSON, nullable=True) # list of str
    route_options = Column(JSON, nullable=True) # list of str
    medicine_category = Column(String(100), default="Essential") # Essential, Maternal, Child, NCD, Acute, Antibiotic
    phc_availability_status = Column(String(50), default="AVAILABLE") # AVAILABLE, LOW_STOCK, OUT_OF_STOCK
    active = Column(Boolean, default=True)
    source_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

class Prescription(Base):
    __tablename__ = "prescriptions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    reference = Column(String(100), unique=True, index=True, nullable=False) # e.g. RX-20260826-ABCD
    citizen_id = Column(String(36), ForeignKey("citizen_profiles.id"), nullable=False, index=True)
    case_id = Column(String(36), ForeignKey("cases.id"), nullable=False, index=True)
    referral_id = Column(String(36), ForeignKey("referrals.id"), nullable=True, index=True)
    consultation_id = Column(String(36), ForeignKey("consultations.id"), nullable=False, index=True)
    prescriber_doctor_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    doctor_id = Column(String(36), nullable=True) # legacy column compatibility
    facility_id = Column(String(36), nullable=True)
    status = Column(String(50), default="DRAFT", index=True) # DRAFT, READY_FOR_REVIEW, SIGNED, ACTIVE, COMPLETED, AMENDED, PARTIALLY_STOPPED, STOPPED, CANCELLED, VOIDED
    version_number = Column(Integer, default=1)
    supersedes_prescription_id = Column(String(36), ForeignKey("prescriptions.id"), nullable=True, index=True)
    clinical_context = Column(Text, nullable=True)
    patient_language = Column(String(20), default="en-IN")
    signed_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)
    cancellation_reason = Column(Text, nullable=True)
    idempotency_key = Column(String(255), nullable=True, index=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    citizen = relationship("CitizenProfile", back_populates="prescriptions")
    case = relationship("Case", back_populates="prescriptions")
    referral = relationship("Referral", back_populates="prescriptions")
    consultation = relationship("Consultation", back_populates="prescriptions")
    prescriber = relationship("User", foreign_keys=[prescriber_doctor_id])
    supersedes_prescription = relationship("Prescription", remote_side=[id])
    items = relationship("PrescriptionItem", back_populates="prescription", cascade="all, delete-orphan")
    safety_checks = relationship("PrescriptionSafetyCheck", back_populates="prescription", cascade="all, delete-orphan")
    amendments_as_original = relationship("PrescriptionAmendment", foreign_keys="[PrescriptionAmendment.original_prescription_id]", back_populates="original_prescription")
    acknowledgements = relationship("PrescriptionAcknowledgement", back_populates="prescription", cascade="all, delete-orphan")

class PrescriptionItem(Base):
    __tablename__ = "prescription_items"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    prescription_id = Column(String(36), ForeignKey("prescriptions.id"), nullable=False, index=True)
    medicine_catalog_id = Column(String(36), ForeignKey("medicine_catalog.id"), nullable=True, index=True)
    generic_name_snapshot = Column(String(200), nullable=False)
    medicine = Column(String(200), nullable=True) # legacy column compatibility
    brand_name_snapshot = Column(String(200), nullable=True)
    formulation = Column(String(100), default="Tablet")
    strength = Column(String(100), nullable=True)
    dose = Column(String(100), default="1")
    dose_unit = Column(String(50), default="tablet")
    route = Column(String(50), default="Oral")
    frequency = Column(String(100), default="Twice daily")
    timing = Column(String(100), default="After food")
    duration_value = Column(Integer, default=5)
    duration_unit = Column(String(20), default="days")
    quantity = Column(Integer, default=10)
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)
    instructions = Column(Text, nullable=True)
    indication = Column(String(255), nullable=True)
    as_needed = Column(Boolean, default=False)
    max_frequency = Column(String(100), nullable=True)
    adherence_monitoring_required = Column(Boolean, default=False)
    status = Column(String(50), default="ACTIVE", index=True) # ACTIVE, STOPPED, COMPLETED
    stopped_at = Column(DateTime, nullable=True)
    stopped_by_doctor_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    stop_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    prescription = relationship("Prescription", back_populates="items")
    medicine_catalog = relationship("MedicineCatalog")
    stopped_by_doctor = relationship("User", foreign_keys=[stopped_by_doctor_id])

class PrescriptionSafetyCheck(Base):
    __tablename__ = "prescription_safety_checks"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    prescription_id = Column(String(36), ForeignKey("prescriptions.id"), nullable=False, index=True)
    check_type = Column(String(100), nullable=False)
    severity = Column(String(50), nullable=False) # BLOCKING_ERROR, DOCTOR_CONFIRMATION_REQUIRED, INFORMATION_WARNING, PASSED
    message = Column(Text, nullable=False)
    source_rule = Column(String(100), nullable=True)
    requires_confirmation = Column(Boolean, default=False)
    confirmed_by_doctor = Column(Boolean, default=False)
    confirmed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now)

    prescription = relationship("Prescription", back_populates="safety_checks")

class PrescriptionAmendment(Base):
    __tablename__ = "prescription_amendments"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    original_prescription_id = Column(String(36), ForeignKey("prescriptions.id"), nullable=False, index=True)
    new_prescription_id = Column(String(36), ForeignKey("prescriptions.id"), nullable=False, index=True)
    reason_code = Column(String(100), nullable=False)
    reason_note = Column(Text, nullable=True)
    created_by_doctor_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=utc_now)

    original_prescription = relationship("Prescription", foreign_keys=[original_prescription_id], back_populates="amendments_as_original")
    new_prescription = relationship("Prescription", foreign_keys=[new_prescription_id])
    created_by_doctor = relationship("User", foreign_keys=[created_by_doctor_id])

class PrescriptionAcknowledgement(Base):
    __tablename__ = "prescription_acknowledgements"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    prescription_id = Column(String(36), ForeignKey("prescriptions.id"), nullable=False, index=True)
    citizen_id = Column(String(36), ForeignKey("citizen_profiles.id"), nullable=False, index=True)
    instructions_understood = Column(Boolean, default=True)
    language = Column(String(20), default="en-IN")
    acknowledged_at = Column(DateTime, default=utc_now)
    help_requested = Column(Boolean, default=False)
    help_note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now)

    prescription = relationship("Prescription", back_populates="acknowledgements")
    citizen = relationship("CitizenProfile")

class TestOrder(Base):
    __tablename__ = "test_orders"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    consultation_id = Column(String(36), ForeignKey("consultations.id"), nullable=False, index=True)
    test_name = Column(String(200), nullable=False)
    priority = Column(String(50), default="URGENT")
    reason = Column(String(255), nullable=True)
    facility_id = Column(String(36), nullable=True)
    status = Column(String(50), default="PENDING")
    result = Column(Text, nullable=True)
    ordered_at = Column(DateTime, default=utc_now)
    reviewed_at = Column(DateTime, nullable=True)
    reviewed_by_doctor_id = Column(String(36), nullable=True)

    consultation = relationship("Consultation", back_populates="test_orders")

class FollowUp(Base):
    __tablename__ = "follow_ups"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    case_id = Column(String(36), ForeignKey("cases.id"), nullable=True, index=True)
    citizen_id = Column(String(36), ForeignKey("citizen_profiles.id"), nullable=True, index=True)
    referral_id = Column(String(36), ForeignKey("referrals.id"), nullable=True, index=True)
    consultation_id = Column(String(36), ForeignKey("consultations.id"), nullable=True, index=True)
    prescription_id = Column(String(36), ForeignKey("prescriptions.id"), nullable=True, index=True)
    created_by_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    created_by_role = Column(String(50), default="DOCTOR")
    source = Column(String(50), default="DOCTOR_ASSIGNED")  # ASHA_SCHEDULED or DOCTOR_ASSIGNED
    task_type = Column(String(100), default="BP_MONITORING")
    reason = Column(Text, nullable=True)
    assigned_role = Column(Enum(UserRoleEnum), default=UserRoleEnum.ASHA_WORKER)
    assigned_user_id = Column(String(36), nullable=True, index=True)
    instructions = Column(Text, nullable=False)
    measurements_to_repeat = Column(JSON, nullable=True)  # e.g. ["systolic_bp", "diastolic_bp", "spo2"]
    adherence_required = Column(Boolean, default=True)
    escalation_conditions = Column(Text, nullable=True)
    priority = Column(Enum(CasePriorityEnum), default=CasePriorityEnum.HIGH)
    due_at = Column(DateTime, nullable=False, index=True)
    status = Column(String(50), default="PENDING", index=True)  # PENDING, IN_PROGRESS, RESCHEDULED, ESCALATED, COMPLETED, REVIEWED, CANCELLED
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    completion_notes = Column(Text, nullable=True)
    symptoms_outcome = Column(String(50), nullable=True)  # IMPROVED, UNCHANGED, WORSENED
    result = Column(Text, nullable=True)
    sync_status = Column(String(50), default="SYNCED")  # SYNCED, PENDING_SYNC
    reviewed_by_doctor_at = Column(DateTime, nullable=True)
    reviewed_by_doctor_id = Column(String(36), nullable=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    case = relationship("Case", back_populates="follow_ups")
    citizen = relationship("CitizenProfile", back_populates="follow_ups")
    referral = relationship("Referral", back_populates="follow_ups")
    consultation = relationship("Consultation")
    prescription = relationship("Prescription")

class FollowUpEscalation(Base):
    __tablename__ = "follow_up_escalations"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    follow_up_id = Column(String(36), ForeignKey("follow_ups.id"), nullable=False, unique=True, index=True)
    case_id = Column(String(36), ForeignKey("cases.id"), nullable=False, index=True)
    citizen_id = Column(String(36), ForeignKey("citizen_profiles.id"), nullable=False, index=True)
    consultation_id = Column(String(36), ForeignKey("consultations.id"), nullable=True)
    referral_id = Column(String(36), ForeignKey("referrals.id"), nullable=True)
    assigned_doctor_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    assigned_asha_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    priority = Column(Enum(CasePriorityEnum), default=CasePriorityEnum.URGENT, nullable=False)
    reason = Column(Text, nullable=False)
    status = Column(String(50), default="ESCALATED", nullable=False, index=True) # ESCALATED, DOCTOR_ACKNOWLEDGED, ACTION_ASSIGNED, RESOLVED, CANCELLED
    escalated_at = Column(DateTime, default=utc_now, nullable=False)
    acknowledged_at = Column(DateTime, nullable=True)
    acknowledged_by = Column(String(36), nullable=True)
    action_type = Column(String(100), nullable=True) # REQUEST_PATIENT_TO_PHC, REPEAT_FOLLOWUP, CONSULTATION_STARTED
    action_notes = Column(Text, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    resolved_by = Column(String(36), nullable=True)
    resolution = Column(Text, nullable=True)
    resolution_outcome = Column(String(50), nullable=True)
    version = Column(Integer, default=1)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    follow_up = relationship("FollowUp", backref="escalation", uselist=False)
    case = relationship("Case")
    citizen = relationship("CitizenProfile")

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    recipient_user_id = Column(String(36), nullable=False, index=True)
    case_id = Column(String(36), nullable=True, index=True)
    notification_type = Column(String(50), default="URGENT_CASE_ALERT")
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    priority = Column(Enum(CasePriorityEnum), default=CasePriorityEnum.HIGH)
    read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utc_now)

class DoctorAlert(Base):
    __tablename__ = "doctor_alerts"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    alert_reference = Column(String(50), unique=True, index=True, nullable=False)
    facility_id = Column(String(36), nullable=False, index=True)
    doctor_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    citizen_id = Column(String(36), ForeignKey("citizen_profiles.id"), nullable=True, index=True)
    case_id = Column(String(36), ForeignKey("cases.id"), nullable=True, index=True)
    
    category = Column(String(50), nullable=False, index=True) # CLINICAL, REFERRAL, INVESTIGATION, FOLLOW_UP, PRESCRIPTION, CITIZEN_REQUEST, OPERATIONAL, SYSTEM
    alert_type = Column(String(100), nullable=False, index=True)
    severity = Column(String(50), nullable=False, index=True) # CRITICAL, URGENT, HIGH, INFORMATION
    title = Column(String(255), nullable=False)
    safe_summary = Column(Text, nullable=False)
    
    source_entity_type = Column(String(50), nullable=False, index=True) # REFERRAL, CONSULTATION, INVESTIGATION, FOLLOWUP, CITIZEN, SYSTEM
    source_entity_id = Column(String(36), nullable=False, index=True)
    source_event_id = Column(String(100), nullable=True)
    lifecycle_version = Column(Integer, default=1, nullable=False)
    
    status = Column(String(50), default="NEW", nullable=False, index=True) # NEW, SEEN, ACKNOWLEDGED, IN_ACTION, RESOLVED, SNOOZED, DISMISSED, ESCALATED
    response_due_at = Column(DateTime, nullable=True, index=True)
    
    created_at = Column(DateTime, default=utc_now, index=True)
    seen_at = Column(DateTime, nullable=True)
    acknowledged_at = Column(DateTime, nullable=True)
    snoozed_until = Column(DateTime, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    dismissed_at = Column(DateTime, nullable=True)
    
    acknowledged_by_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    resolved_by_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    dismissed_by_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    
    resolution_note = Column(Text, nullable=True)
    dismissal_reason = Column(Text, nullable=True)
    snooze_reason = Column(Text, nullable=True)

    citizen = relationship("CitizenProfile", backref="doctor_alerts")
    case = relationship("Case", backref="doctor_alerts")
    doctor = relationship("User", foreign_keys=[doctor_id])
    actions = relationship("AlertAction", back_populates="alert", cascade="all, delete-orphan")

class AlertAction(Base):
    __tablename__ = "alert_actions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    alert_id = Column(String(36), ForeignKey("doctor_alerts.id"), nullable=False, index=True)
    action = Column(String(100), nullable=False) # CREATED, SEEN, ACKNOWLEDGED, SNOOZED, RESOLVED, DISMISSED, ESCALATED, PHONE_REVEALED
    previous_status = Column(String(50), nullable=True)
    new_status = Column(String(50), nullable=False)
    actor_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    actor_role = Column(String(50), nullable=False)
    note = Column(Text, nullable=True)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=utc_now)

    alert = relationship("DoctorAlert", back_populates="actions")
    actor = relationship("User", foreign_keys=[actor_id])

class ClusterAlert(Base):
    __tablename__ = "cluster_alerts"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    alert_title = Column(String(200), nullable=False)
    district_id = Column(String(36), nullable=True)
    district_name = Column(String(150), default="District 04")
    block_name = Column(String(150), default="Kalyanpur Block")
    village_name = Column(String(150), default="Kalyanpur")
    symptom_group = Column(String(100), nullable=False) # e.g. FEVER_JOINT_PAIN, MATERNAL_HYPERTENSION
    case_count = Column(Integer, default=5)
    time_window_hours = Column(Integer, default=48)
    risk_level = Column(Enum(CasePriorityEnum), default=CasePriorityEnum.HIGH)
    status = Column(String(50), default="UNDER_INVESTIGATION") # UNDER_INVESTIGATION, RESOLVED
    created_at = Column(DateTime, default=utc_now)

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    actor_user_id = Column(String(36), nullable=True)
    actor_role = Column(String(50), nullable=False)
    action = Column(String(100), nullable=False) # e.g. CASE_CREATED, VITALS_RECORDED, REFERRAL_SUBMITTED, PRESCRIPTION_SIGNED
    resource_type = Column(String(50), nullable=False)
    resource_id = Column(String(100), nullable=False)
    outcome = Column(String(50), default="SUCCESS")
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=utc_now)

class SchemeCheck(Base):
    __tablename__ = "scheme_checks"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    citizen_id = Column(String(36), nullable=False, index=True)
    case_id = Column(String(36), nullable=True)
    scheme_code = Column(String(50), nullable=False) # e.g. JSY, PMJAY, MJPJAY
    scheme_name = Column(String(200), nullable=False)
    result = Column(String(50), default="POTENTIALLY_ELIGIBLE") # POTENTIALLY_ELIGIBLE, VERIFIED_ELIGIBLE, NOT_ELIGIBLE
    reason_summary = Column(Text, nullable=True)
    source_urls = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=utc_now)

class DocumentRecord(Base):
    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    case_id = Column(String(36), nullable=False, index=True)
    document_type = Column(String(50), nullable=False) # REFERRAL_SUMMARY, CONSULTATION_NOTE, PRESCRIPTION_SLIP
    title = Column(String(200), nullable=False)
    file_path = Column(String(255), nullable=True)
    mime_type = Column(String(100), default="application/pdf")
    created_by = Column(String(100), nullable=True)
    signed_by = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=utc_now)

class IdempotencyRecord(Base):
    """
    Stores API responses to ensure safe retries of network requests 
    when ASHA workers reconnect from offline mode.
    """
    __tablename__ = "idempotency_records"

    idempotency_key = Column(String(128), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    http_method = Column(String(10), default="POST", nullable=False)
    request_path = Column(String(255), nullable=False)
    operation = Column(String(100), nullable=True)
    payload_hash = Column(String(64), nullable=True, index=True)
    resource_type = Column(String(50), nullable=True)
    resource_id = Column(String(100), nullable=True)
    response_status = Column(Integer, nullable=False)
    response_body = Column(Text, nullable=False) # Store JSON string
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

class AIUsageEvent(Base):
    __tablename__ = "ai_usage_events"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    provider = Column(String(50), nullable=False)
    mode = Column(String(50), nullable=False) # LIVE, MOCK, FALLBACK
    operation = Column(String(100), nullable=False) # e.g. ASR, TRANSLATE, RETRIEVE, SUMMARY
    requesting_role = Column(String(50), nullable=True)
    request_fingerprint = Column(String(64), nullable=True)
    cache_hit = Column(Boolean, default=False)
    status = Column(String(50), default="SUCCESS") # SUCCESS, ERROR, BUDGET_EXCEEDED
    latency_ms = Column(Float, default=0.0)
    input_tokens = Column(Integer, nullable=True)
    output_tokens = Column(Integer, nullable=True)
    audio_duration = Column(Float, nullable=True)
    result_count = Column(Integer, default=0)
    retry_count = Column(Integer, default=0)
    estimated_cost = Column(Float, default=0.0)
    created_at = Column(DateTime, default=utc_now)


from app.models.schemes import (
    GovernmentLevelEnum, ReviewStateEnum, SourceTierEnum, EligibilityOutputEnum,
    AuthorityModel, SchemeModel, SchemeVersionModel, SourceDocumentModel,
    EligibilityRuleSetModel, SchemeBenefitModel, SchemeEvaluationModel,
    SchemeEvaluationResultModel, SchemeVerificationModel, SavedSchemeModel,
    SchemeAssistanceRequestModel, SchemeApplicationTrackingModel, SchemeScreeningSessionModel
)
from app.models.eligibility_profile import SchemeEligibilityProfileModel

class InvestigationOrder(Base):
    __tablename__ = "investigation_orders"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    reference = Column(String(50), unique=True, index=True, nullable=False)
    citizen_id = Column(String(36), ForeignKey("citizen_profiles.id"), nullable=False, index=True)
    case_id = Column(String(36), ForeignKey("cases.id"), nullable=False, index=True)
    referral_id = Column(String(36), ForeignKey("referrals.id"), nullable=True, index=True)
    consultation_id = Column(String(36), ForeignKey("consultations.id"), nullable=True, index=True)
    ordered_by_doctor_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    facility_id = Column(String(36), nullable=True)
    test_name = Column(String(200), nullable=False)
    test_code = Column(String(50), nullable=True)
    category = Column(String(50), default="GENERAL")
    priority = Column(String(50), default="ROUTINE", index=True)
    clinical_reason = Column(Text, nullable=True)
    specimen_type = Column(String(100), nullable=True)
    preparation_instructions = Column(Text, nullable=True)
    collection_location = Column(String(200), nullable=True)
    ordered_at = Column(DateTime, default=utc_now, index=True)
    due_at = Column(DateTime, nullable=True)
    expected_result_at = Column(DateTime, nullable=True)
    status = Column(String(50), default="ORDERED", index=True)
    idempotency_key = Column(String(100), unique=True, nullable=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    citizen = relationship("CitizenProfile", backref="investigation_orders")
    case = relationship("Case", backref="investigation_orders")
    referral = relationship("Referral", backref="investigation_orders")
    consultation = relationship("Consultation", backref="investigation_orders_canonical")
    ordered_by_doctor = relationship("User", foreign_keys=[ordered_by_doctor_id])

    sample = relationship("InvestigationSample", back_populates="order", uselist=False, cascade="all, delete-orphan")
    result = relationship("InvestigationResult", back_populates="order", uselist=False, cascade="all, delete-orphan")
    asha_tasks = relationship("InvestigationAshaTask", back_populates="order", cascade="all, delete-orphan")


class InvestigationSample(Base):
    __tablename__ = "investigation_samples"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    investigation_order_id = Column(String(36), ForeignKey("investigation_orders.id"), nullable=False, index=True)
    sample_reference = Column(String(100), nullable=True)
    collected_by_user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    collected_at = Column(DateTime, nullable=True)
    collection_status = Column(String(50), default="PENDING")
    rejection_reason = Column(Text, nullable=True)
    recollection_required = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utc_now)

    order = relationship("InvestigationOrder", back_populates="sample")
    collected_by = relationship("User", foreign_keys=[collected_by_user_id])


class InvestigationResult(Base):
    __tablename__ = "investigation_results"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    investigation_order_id = Column(String(36), ForeignKey("investigation_orders.id"), nullable=False, index=True)
    result_source = Column(String(100), default="PHC_LAB")
    laboratory_name = Column(String(200), default="PHC Kalyanpur Central Lab")
    resulted_at = Column(DateTime, default=utc_now)
    entered_by_user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    verified_by_user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    verification_status = Column(String(50), default="VERIFIED")
    report_attachment_id = Column(String(100), nullable=True)
    critical_flag = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    order = relationship("InvestigationOrder", back_populates="result")
    entered_by = relationship("User", foreign_keys=[entered_by_user_id])
    verified_by = relationship("User", foreign_keys=[verified_by_user_id])
    items = relationship("InvestigationResultItem", back_populates="result", cascade="all, delete-orphan")
    review = relationship("InvestigationReview", back_populates="result", uselist=False, cascade="all, delete-orphan")


class InvestigationResultItem(Base):
    __tablename__ = "investigation_result_items"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    result_id = Column(String(36), ForeignKey("investigation_results.id"), nullable=False, index=True)
    parameter_name = Column(String(200), nullable=False)
    parameter_code = Column(String(50), nullable=True)
    value = Column(String(100), nullable=False)
    unit = Column(String(50), nullable=True)
    reference_low = Column(String(50), nullable=True)
    reference_high = Column(String(50), nullable=True)
    source_flag = Column(String(50), default="NORMAL")
    remarks = Column(Text, nullable=True)

    result = relationship("InvestigationResult", back_populates="items")


class InvestigationReview(Base):
    __tablename__ = "investigation_reviews"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    result_id = Column(String(36), ForeignKey("investigation_results.id"), nullable=False, index=True)
    doctor_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    review_note = Column(Text, nullable=False)
    outcome = Column(String(100), nullable=False)
    reviewed_at = Column(DateTime, default=utc_now)
    critical_acknowledged_at = Column(DateTime, nullable=True)
    care_plan_updated = Column(Boolean, default=False)
    related_follow_up_id = Column(String(36), ForeignKey("follow_ups.id"), nullable=True)
    related_higher_referral_id = Column(String(36), ForeignKey("referrals.id"), nullable=True)

    result = relationship("InvestigationResult", back_populates="review")
    doctor = relationship("User", foreign_keys=[doctor_id])
    related_follow_up = relationship("FollowUp", foreign_keys=[related_follow_up_id])
    related_higher_referral = relationship("Referral", foreign_keys=[related_higher_referral_id])


class InvestigationAshaTask(Base):
    __tablename__ = "investigation_asha_tasks"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    investigation_order_id = Column(String(36), ForeignKey("investigation_orders.id"), nullable=False, index=True)
    asha_user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    citizen_id = Column(String(36), ForeignKey("citizen_profiles.id"), nullable=False, index=True)
    task_type = Column(String(100), default="ATTENDANCE_ASSISTANCE")
    due_date = Column(DateTime, nullable=True)
    instructions = Column(Text, nullable=False)
    status = Column(String(50), default="PENDING", index=True)
    contacted_citizen = Column(Boolean, default=False)
    attendance_confirmed = Column(Boolean, default=False)
    unable_to_attend_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    order = relationship("InvestigationOrder", back_populates="asha_tasks")
    asha_user = relationship("User", foreign_keys=[asha_user_id])
    citizen = relationship("CitizenProfile", foreign_keys=[citizen_id])


class HouseholdMember(Base):
    __tablename__ = "household_members"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    citizen_id = Column(String(36), ForeignKey("citizen_profiles.id"), nullable=False, index=True)
    linked_citizen_profile_id = Column(String(36), ForeignKey("citizen_profiles.id"), nullable=True, index=True)
    full_name = Column(String(150), nullable=False)
    relationship_type = Column(String(50), nullable=False) # SELF, MOTHER, FATHER, SPOUSE, CHILD, ELDER, OTHER
    age = Column(Integer, nullable=True)
    sex = Column(String(20), nullable=True)
    phone = Column(String(20), nullable=True)
    abha_reference = Column(String(50), nullable=True)
    is_pregnant = Column(Boolean, default=False)
    gestational_weeks = Column(Integer, nullable=True)
    blood_group = Column(String(10), nullable=True)
    chronic_conditions = Column(JSON, default=list)
    health_notes = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    citizen = relationship("CitizenProfile", foreign_keys=[citizen_id], back_populates="household_members")

    @property
    def relationship(self):
        return self.relationship_type

    @relationship.setter
    def relationship(self, value):
        self.relationship_type = value



class CitizenChatSession(Base):
    __tablename__ = "citizen_chat_sessions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    session_reference = Column(String(50), unique=True, index=True, nullable=False)
    citizen_id = Column(String(36), ForeignKey("citizen_profiles.id"), nullable=False, index=True)
    person_affected_id = Column(String(36), ForeignKey("household_members.id"), nullable=True)
    preferred_language = Column(String(10), default="mr-IN")
    detected_language = Column(String(10), default="mr-IN")
    channel = Column(String(20), default="VOICE") # VOICE, TEXT, MIXED
    current_state = Column(String(50), default="STARTED", index=True)
    primary_intent = Column(String(100), nullable=True)
    status = Column(String(30), default="ACTIVE", index=True)
    started_at = Column(DateTime, default=utc_now)
    last_activity_at = Column(DateTime, default=utc_now)
    expires_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    linked_need_id = Column(String(36), nullable=True)
    linked_case_id = Column(String(36), nullable=True)
    consent_status = Column(Boolean, default=True)
    device_id = Column(String(100), nullable=True)
    offline_created = Column(Boolean, default=False)
    sync_status = Column(String(30), default="SYNCED")
    # Conversation Intelligence Tracking
    current_question_id = Column(String(100), nullable=True)
    awaiting_answer = Column(Boolean, default=False)
    conversation_stage = Column(String(50), default="INITIAL") # INITIAL, UNDERSTANDING, QUESTIONING, GUIDING, ACTION
    current_topic = Column(String(100), nullable=True)
    previous_topic = Column(String(100), nullable=True)
    last_assistant_question = Column(Text, nullable=True)
    last_intent = Column(String(100), nullable=True)
    context_transition = Column(String(100), nullable=True)
    context_state = Column(JSON, default=dict) # versioned symptoms, facts, questions, safety history

    citizen = relationship("CitizenProfile", back_populates="chat_sessions")
    person_affected = relationship("HouseholdMember", foreign_keys=[person_affected_id])
    messages = relationship("CitizenChatMessage", back_populates="session", cascade="all, delete-orphan")
    conversation_state_rel = relationship("CitizenConversationState", back_populates="session", uselist=False, cascade="all, delete-orphan")


class CitizenConversationState(Base):
    __tablename__ = "citizen_conversation_states"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    session_id = Column(String(36), ForeignKey("citizen_chat_sessions.id"), unique=True, nullable=False, index=True)
    current_topic = Column(String(100), nullable=True)
    previous_topic = Column(String(100), nullable=True)
    active_need_id = Column(String(36), nullable=True)
    last_assistant_question = Column(Text, nullable=True)
    asked_question_keys = Column(JSON, default=list)
    confirmed_facts = Column(JSON, default=dict)
    negated_facts = Column(JSON, default=list)
    uncertain_facts = Column(JSON, default=list)
    compact_summary = Column(Text, nullable=True)
    last_intent = Column(String(100), nullable=True)
    context_transition = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    session = relationship("CitizenChatSession", back_populates="conversation_state_rel")


class CitizenChatMessage(Base):
    __tablename__ = "citizen_chat_messages"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    session_id = Column(String(36), ForeignKey("citizen_chat_sessions.id"), nullable=False, index=True)
    sequence_number = Column(Integer, default=1)
    sender = Column(String(20), nullable=False) # CITIZEN, ASSISTANT, SYSTEM
    input_type = Column(String(20), default="TEXT") # VOICE, TEXT, SYSTEM
    original_text = Column(Text, nullable=True)
    confirmed_text = Column(Text, nullable=True)
    translated_text = Column(Text, nullable=True)
    language = Column(String(10), default="mr-IN")
    message_type = Column(String(50), default="TEXT") # TRANSCRIPT, UNDERSTANDING, QUESTION, RESPONSE, SAFETY_ALERT, SAFE_GUIDANCE, ACTION_CHOICES
    structured_payload = Column(JSON, nullable=True) # typed UI blocks & payload
    confirmation_status = Column(String(30), default="CONFIRMED") # PENDING, CONFIRMED, EDITED, REJECTED
    intent_classification = Column(String(50), nullable=True) # validated message purpose
    in_reply_to_question_id = Column(String(100), nullable=True)
    idempotency_key = Column(String(100), nullable=True, index=True)
    model_provider = Column(String(50), nullable=True)
    model_name = Column(String(50), nullable=True)
    prompt_version = Column(String(20), nullable=True)
    temporary_audio_reference = Column(String(255), nullable=True)
    audio_consent_at = Column(DateTime, nullable=True)
    transcription_provider = Column(String(50), nullable=True)
    transcription_confidence = Column(Float, nullable=True)
    audio_deleted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now)

    session = relationship("CitizenChatSession", back_populates="messages")


class CitizenNeed(Base):
    __tablename__ = "citizen_needs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    need_reference = Column(String(50), unique=True, index=True, nullable=False)
    session_id = Column(String(36), ForeignKey("citizen_chat_sessions.id"), nullable=True, index=True)
    citizen_id = Column(String(36), ForeignKey("citizen_profiles.id"), nullable=False, index=True)
    person_affected_id = Column(String(36), ForeignKey("household_members.id"), nullable=True)
    primary_intent = Column(String(100), nullable=False)
    secondary_intents = Column(JSON, default=list)
    requested_service = Column(String(100), nullable=True)
    detected_language = Column(String(10), default="mr-IN")
    confirmed_summary = Column(Text, nullable=False)
    structured_facts = Column(JSON, default=dict) # versioned facts {symptoms, duration, vitals, temperature_f, etc.}
    facts_version = Column(Integer, default=1)
    location = Column(JSON, nullable=True)
    special_context = Column(String(50), default="GENERAL")
    urgency = Column(String(30), default="ROUTINE")
    safety_result_id = Column(String(36), nullable=True)
    status = Column(String(30), default="CONFIRMED")
    citizen_confirmed_at = Column(DateTime, default=utc_now)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    citizen = relationship("CitizenProfile", back_populates="needs")
    session = relationship("CitizenChatSession", foreign_keys=[session_id])
    person_affected = relationship("HouseholdMember", foreign_keys=[person_affected_id])


class ServiceRequest(Base):
    __tablename__ = "service_requests"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    request_reference = Column(String(50), unique=True, index=True, nullable=False)
    citizen_id = Column(String(36), ForeignKey("citizen_profiles.id"), nullable=False, index=True)
    beneficiary_id = Column(String(36), nullable=True, index=True)
    citizen_need_id = Column(String(36), ForeignKey("citizen_needs.id"), nullable=True, index=True)
    need_id = Column(String(36), ForeignKey("citizen_needs.id"), nullable=True, index=True)
    chat_session_id = Column(String(36), ForeignKey("citizen_chat_sessions.id"), nullable=True, index=True)
    case_id = Column(String(36), ForeignKey("cases.id"), nullable=True, index=True)
    handoff_id = Column(String(36), nullable=True, index=True)
    request_type = Column(String(50), nullable=False) # DOCTOR_CONSULTATION, ASHA_ASSISTANCE, EMERGENCY_TRANSPORT, FACILITY_SEARCH, SCHEME_SCREENING
    requested_channel = Column(String(50), default="CALLBACK") # AUDIO, VIDEO, CHAT, CALLBACK, HOME_VISIT
    status = Column(String(50), default="SUBMITTED", index=True) # DRAFT, SUBMITTED, SAFETY_TRIAGED, WAITING_FOR_DOCTOR, DOCTOR_ASSIGNED, DOCTOR_ACCEPTED, READY_TO_CONNECT, IN_CONSULTATION, COMPLETED, CANCELLED, EXPIRED, UNREACHABLE, REFERRED_IN_PERSON, EMERGENCY_ESCALATED, ASSIGNMENT_PENDING, ASHA_ASSIGNED, ASHA_ACKNOWLEDGED, CITIZEN_CONTACTED, VISIT_SCHEDULED, VISIT_IN_PROGRESS
    priority = Column(String(30), default="ROUTINE")
    assigned_role = Column(String(50), nullable=True) # PHC_DOCTOR, ASHA_WORKER
    assigned_user_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    assigned_worker_id = Column(String(36), ForeignKey("worker_profiles.id"), nullable=True)
    assigned_facility_id = Column(String(36), ForeignKey("facilities.id"), nullable=True)
    submitted_at = Column(DateTime, default=utc_now)
    acknowledged_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    cancellation_reason = Column(Text, nullable=True)
    details = Column(JSON, default=dict)
    idempotency_key = Column(String(100), unique=True, nullable=True, index=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    citizen = relationship("CitizenProfile", back_populates="service_requests")
    beneficiary = relationship("HouseholdMember", primaryjoin="ServiceRequest.beneficiary_id == HouseholdMember.id", foreign_keys=[beneficiary_id])
    need = relationship("CitizenNeed", foreign_keys=[need_id])
    case = relationship("Case", foreign_keys=[case_id])
    session = relationship("CitizenChatSession", foreign_keys=[chat_session_id])
    assigned_user = relationship("User", foreign_keys=[assigned_user_id])
    assigned_worker = relationship("WorkerProfile", foreign_keys=[assigned_worker_id])
    assigned_facility = relationship("Facility", foreign_keys=[assigned_facility_id])
    handoffs = relationship("CareHandoff", back_populates="service_request", cascade="all, delete-orphan")
    status_history = relationship("ServiceRequestStatusHistory", back_populates="service_request", cascade="all, delete-orphan")


class CareHandoff(Base):
    __tablename__ = "care_handoffs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    version = Column(Integer, default=1, nullable=False)
    service_request_id = Column(String(36), ForeignKey("service_requests.id"), nullable=True, index=True)
    citizen_id = Column(String(36), ForeignKey("citizen_profiles.id"), nullable=False, index=True)
    beneficiary_id = Column(String(36), nullable=True, index=True)
    chat_session_id = Column(String(36), ForeignKey("citizen_chat_sessions.id"), nullable=True, index=True)
    citizen_need_id = Column(String(36), ForeignKey("citizen_needs.id"), nullable=True, index=True)
    case_id = Column(String(36), ForeignKey("cases.id"), nullable=True, index=True)
    consent_id = Column(String(36), ForeignKey("sharing_consents.id"), nullable=True, index=True)
    request_type = Column(String(50), nullable=False) # DOCTOR_CONSULTATION, ASHA_ASSISTANCE
    requested_channel = Column(String(50), default="CALLBACK") # AUDIO, VIDEO, CHAT, CALLBACK, HOME_VISIT
    recipient_role = Column(String(50), nullable=False) # PHC_DOCTOR, ASHA_WORKER
    source = Column(String(50), default="CITIZEN_CHAT")
    citizen_summary = Column(Text, nullable=False)
    chief_concern = Column(String(255), nullable=True)
    structured_payload = Column(JSON, default=dict) # Full canonical CareHandoffPacket
    safety_snapshot = Column(JSON, default=dict) # Deterministic evaluated safety
    supersedes_handoff_id = Column(String(36), ForeignKey("care_handoffs.id"), nullable=True)
    created_at = Column(DateTime, default=utc_now)

    service_request = relationship("ServiceRequest", back_populates="handoffs")
    citizen = relationship("CitizenProfile")
    beneficiary = relationship("HouseholdMember", primaryjoin="CareHandoff.beneficiary_id == HouseholdMember.id", foreign_keys=[beneficiary_id])
    consent = relationship("SharingConsent")
    case = relationship("Case")


class SharingConsent(Base):
    __tablename__ = "sharing_consents"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    citizen_id = Column(String(36), ForeignKey("citizen_profiles.id"), nullable=False, index=True)
    beneficiary_id = Column(String(36), nullable=True, index=True)
    recipient_role = Column(String(50), nullable=False) # PHC_DOCTOR, ASHA_WORKER
    purpose = Column(String(100), default="CARE_HANDOFF")
    scope = Column(JSON, default=dict) # {share_structured_summary, share_profile, share_location, share_recent_messages, share_existing_health_records}
    policy_version = Column(String(20), default="v1.0")
    consent_text = Column(Text, nullable=True)
    consented_at = Column(DateTime, default=utc_now)
    revoked_at = Column(DateTime, nullable=True)

    citizen = relationship("CitizenProfile")
    beneficiary = relationship("HouseholdMember", primaryjoin="SharingConsent.beneficiary_id == HouseholdMember.id", foreign_keys=[beneficiary_id])


class ServiceRequestStatusHistory(Base):
    __tablename__ = "service_request_status_history"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    service_request_id = Column(String(36), ForeignKey("service_requests.id"), nullable=False, index=True)
    from_status = Column(String(50), nullable=True)
    to_status = Column(String(50), nullable=False)
    actor_role = Column(String(50), nullable=False) # CITIZEN, PHC_DOCTOR, ASHA_WORKER, SYSTEM
    actor_id = Column(String(36), nullable=True)
    reason = Column(Text, nullable=True)
    occurred_at = Column(DateTime, default=utc_now)

    service_request = relationship("ServiceRequest", back_populates="status_history")


class TeleconsultationRequest(Base):
    __tablename__ = "teleconsultation_requests"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    public_reference = Column(String(50), unique=True, index=True, nullable=False)
    citizen_id = Column(String(36), ForeignKey("citizen_profiles.id"), nullable=False, index=True)
    household_member_id = Column(String(36), ForeignKey("household_members.id"), nullable=True, index=True)
    citizen_need_id = Column(String(36), ForeignKey("citizen_needs.id"), nullable=True, index=True)
    service_request_id = Column(String(36), ForeignKey("service_requests.id"), nullable=True, index=True)
    case_id = Column(String(36), ForeignKey("cases.id"), nullable=True, index=True)
    facility_id = Column(String(36), ForeignKey("facilities.id"), nullable=True, default="PHC-09")
    assigned_doctor_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    consultation_id = Column(String(36), ForeignKey("consultations.id"), nullable=True, index=True)
    
    language_code = Column(String(10), default="mr-IN")
    mode = Column(String(50), default="AUDIO") # AUDIO, VIDEO, CHAT, CALLBACK, SCHEDULED, IN_PERSON_PHC
    status = Column(String(50), default="DRAFT", index=True) 
    # Lifecycle: DRAFT, SUBMITTED, TRIAGED, WAITING_FOR_DOCTOR, DOCTOR_ASSIGNED, DOCTOR_ACCEPTED, READY_TO_CONNECT, IN_CONSULTATION, COMPLETED, CANCELLED, EXPIRED, UNREACHABLE, REFERRED_TO_EMERGENCY, REFERRED_TO_IN_PERSON_PHC
    priority = Column(String(30), default="ROUTINE") # EMERGENCY, URGENT, PRIORITY, ROUTINE, INSUFFICIENT_INFORMATION
    
    chief_complaint = Column(Text, nullable=True)
    symptoms = Column(JSON, default=list)
    duration_text = Column(String(100), nullable=True)
    severity_level = Column(String(50), nullable=True)
    structured_intake = Column(JSON, default=dict)
    safety_rule_triggered = Column(Boolean, default=False)
    safety_rule_ids = Column(JSON, default=list)
    safety_reason = Column(Text, nullable=True)
    
    queue_position = Column(Integer, nullable=True)
    estimated_wait_minutes = Column(Integer, default=5)
    scheduled_at = Column(DateTime, nullable=True)
    submitted_at = Column(DateTime, nullable=True)
    accepted_at = Column(DateTime, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    cancellation_reason = Column(Text, nullable=True)
    
    clinical_notes = Column(Text, nullable=True)
    disposition = Column(String(100), nullable=True)
    patient_guidance = Column(Text, nullable=True)
    
    idempotency_key = Column(String(100), unique=True, nullable=True, index=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)
    version = Column(Integer, default=1)

    citizen = relationship("CitizenProfile", foreign_keys=[citizen_id])
    household_member = relationship("HouseholdMember", foreign_keys=[household_member_id])
    citizen_need = relationship("CitizenNeed", foreign_keys=[citizen_need_id])
    service_request = relationship("ServiceRequest", foreign_keys=[service_request_id])
    case = relationship("Case", foreign_keys=[case_id])
    assigned_doctor = relationship("User", foreign_keys=[assigned_doctor_id])
    consultation = relationship("Consultation", foreign_keys=[consultation_id])
    facility = relationship("Facility", foreign_keys=[facility_id])

    consents = relationship("TeleconsultationConsent", back_populates="request", cascade="all, delete-orphan")
    status_history = relationship("TeleconsultationStatusHistory", back_populates="request", cascade="all, delete-orphan")
    messages = relationship("TeleconsultationMessage", back_populates="request", cascade="all, delete-orphan")
    attachments = relationship("TeleconsultationAttachment", back_populates="request", cascade="all, delete-orphan")


class TeleconsultationConsent(Base):
    __tablename__ = "teleconsultation_consents"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    request_id = Column(String(36), ForeignKey("teleconsultation_requests.id"), nullable=False, index=True)
    share_concern = Column(Boolean, default=True)
    share_medical_history = Column(Boolean, default=True)
    audio_video_consent = Column(Boolean, default=True)
    store_transcript_consent = Column(Boolean, default=True)
    share_location_consent = Column(Boolean, default=False)
    consented_at = Column(DateTime, default=utc_now)

    request = relationship("TeleconsultationRequest", back_populates="consents")


class TeleconsultationStatusHistory(Base):
    __tablename__ = "teleconsultation_status_history"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    request_id = Column(String(36), ForeignKey("teleconsultation_requests.id"), nullable=False, index=True)
    from_status = Column(String(50), nullable=True)
    to_status = Column(String(50), nullable=False)
    changed_by_user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    changed_by_role = Column(String(50), default="CITIZEN")
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now)

    request = relationship("TeleconsultationRequest", back_populates="status_history")
    changed_by_user = relationship("User", foreign_keys=[changed_by_user_id])


class TeleconsultationMessage(Base):
    __tablename__ = "teleconsultation_messages"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    request_id = Column(String(36), ForeignKey("teleconsultation_requests.id"), nullable=False, index=True)
    sender_type = Column(String(30), nullable=False) # CITIZEN, DOCTOR, SYSTEM
    sender_id = Column(String(36), nullable=True)
    sender_name = Column(String(150), nullable=True)
    message_text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=utc_now)

    request = relationship("TeleconsultationRequest", back_populates="messages")


class TeleconsultationAttachment(Base):
    __tablename__ = "teleconsultation_attachments"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    request_id = Column(String(36), ForeignKey("teleconsultation_requests.id"), nullable=False, index=True)
    file_name = Column(String(255), nullable=False)
    file_url = Column(String(500), nullable=False)
    file_type = Column(String(50), default="REPORT") # REPORT, IMAGE, PRESCRIPTION, AUDIO
    file_size_bytes = Column(Integer, default=0)
    uploaded_by = Column(String(50), default="CITIZEN")
    created_at = Column(DateTime, default=utc_now)

    request = relationship("TeleconsultationRequest", back_populates="attachments")


# Scheme models
from app.models.schemes import (
    GovernmentLevelEnum, ReviewStateEnum, SourceTierEnum, EligibilityOutputEnum,
    AuthorityModel, SchemeModel, SchemeVersionModel, SourceDocumentModel,
    EligibilityRuleSetModel, SchemeBenefitModel, SchemeEvaluationModel,
    SchemeEvaluationResultModel, SchemeScreeningSessionModel, SavedSchemeModel,
    SchemeAssistanceRequestModel, SchemeApplicationTrackingModel, SchemeVerificationModel,
    AssistanceCapabilityModel, SchemeAssistanceCapabilityModel
)

# -------------------------------------------------------------
# Citizen Authentication & Guest Session Models
# -------------------------------------------------------------

class CitizenAuthIdentity(Base):
    __tablename__ = "citizen_auth_identities"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, unique=True, index=True)
    phone_normalized = Column(String(20), nullable=False, unique=True, index=True) # E.164 e.g. +919876543210
    phone_hash = Column(String(64), nullable=False, unique=True, index=True) # SHA-256
    phone_verified_at = Column(DateTime, default=utc_now)
    provider = Column(String(50), default="MOCK_SMS") # MOCK_SMS, BHASHINI, SARVAM, TWILIO, MSG91
    created_at = Column(DateTime, default=utc_now)

    user = relationship("User")

class OtpChallenge(Base):
    __tablename__ = "otp_challenges"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    phone_hash = Column(String(64), nullable=False, index=True)
    otp_hash = Column(String(128), nullable=False)
    attempts = Column(Integer, default=0)
    max_attempts = Column(Integer, default=5)
    expires_at = Column(DateTime, nullable=False, index=True)
    consumed_at = Column(DateTime, nullable=True)
    ip_address = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=utc_now)

class AuthSession(Base):
    __tablename__ = "auth_sessions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    refresh_token_hash = Column(String(128), nullable=False, index=True)
    device_id = Column(String(100), nullable=True)
    expires_at = Column(DateTime, nullable=False)
    revoked_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now)

    user = relationship("User")

class GuestSession(Base):
    __tablename__ = "guest_sessions"

    id = Column(String(36), primary_key=True, default=generate_uuid) # Non-guessable random token/uuid
    locale = Column(String(10), default="mr-IN")
    device_session_hash = Column(String(64), nullable=True, index=True)
    intended_action = Column(JSON, nullable=True) # e.g. {"type": "SPEAK_TO_DOCTOR", "channel": "CALLBACK"}
    context_data = Column(JSON, default=dict) # chat draft, need draft, safety snapshot, beneficiary draft
    expires_at = Column(DateTime, nullable=False, index=True)
    migrated_to_user_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    migrated_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now)

    migrated_user = relationship("User", foreign_keys=[migrated_to_user_id])

class GuestSessionMigration(Base):
    __tablename__ = "guest_session_migrations"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    guest_session_id = Column(String(36), ForeignKey("guest_sessions.id"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    migration_status = Column(String(30), default="COMPLETED") # IN_PROGRESS, COMPLETED, FAILED
    idempotency_key = Column(String(100), unique=True, nullable=False, index=True)
    migrated_entities = Column(JSON, default=dict) # {"chat_sessions": [...], "needs": [...], "service_requests": [...]}
    created_at = Column(DateTime, default=utc_now)

    guest_session = relationship("GuestSession")
    user = relationship("User")


# -------------------------------------------------------------
# Canonical Doctor Chat Models
# -------------------------------------------------------------
class DoctorChatThread(Base):
    __tablename__ = "doctor_chat_threads"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    service_request_id = Column(String(36), ForeignKey("service_requests.id"), unique=True, index=True, nullable=False)
    citizen_id = Column(String(36), ForeignKey("citizen_profiles.id"), nullable=False, index=True)
    doctor_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    facility_id = Column(String(36), ForeignKey("facilities.id"), nullable=False, default="PHC-09")
    channel = Column(String(30), nullable=False, default="DOCTOR_CHAT")
    status = Column(String(30), nullable=False, default="WAITING_FOR_DOCTOR", index=True) 
    # Status: WAITING_FOR_DOCTOR, DOCTOR_ACCEPTED, IN_CONSULTATION, COMPLETED, CANCELLED
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    service_request = relationship("ServiceRequest", foreign_keys=[service_request_id])
    citizen = relationship("CitizenProfile", foreign_keys=[citizen_id])
    doctor = relationship("User", foreign_keys=[doctor_id])
    facility = relationship("Facility", foreign_keys=[facility_id])
    messages = relationship("DoctorChatMessage", back_populates="thread", cascade="all, delete-orphan", order_by="DoctorChatMessage.created_at")


class DoctorChatMessage(Base):
    __tablename__ = "doctor_chat_messages"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    conversation_id = Column(String(36), ForeignKey("doctor_chat_threads.id"), nullable=False, index=True)
    service_request_id = Column(String(36), ForeignKey("service_requests.id"), nullable=True, index=True)
    sender_role = Column(String(30), nullable=False, default="CITIZEN") # CITIZEN, PHC_DOCTOR, SYSTEM
    sender_user_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    sender_id = Column(String(36), nullable=True, index=True)
    sender_name = Column(String(150), nullable=True)
    body = Column(Text, nullable=False)
    client_message_id = Column(String(100), unique=True, index=True, nullable=False)
    status = Column(String(30), nullable=False, default="SENT") # SENDING, SENT, DELIVERED, READ, FAILED
    delivery_status = Column(String(30), nullable=True, default="DELIVERED")
    created_at = Column(DateTime, default=utc_now, index=True)
    delivered_at = Column(DateTime, nullable=True)
    read_at = Column(DateTime, nullable=True)

    thread = relationship("DoctorChatThread", back_populates="messages")
    service_request = relationship("ServiceRequest", foreign_keys=[service_request_id])
    sender_user = relationship("User", foreign_keys=[sender_user_id])






