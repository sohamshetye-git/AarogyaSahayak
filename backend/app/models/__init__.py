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
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    citizen_profile = relationship("CitizenProfile", back_populates="user", uselist=False)
    worker_profile = relationship("WorkerProfile", back_populates="user", uselist=False)

class CitizenProfile(Base):
    __tablename__ = "citizen_profiles"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    display_name = Column(String(150), nullable=False)
    age_estimate = Column(Integer, nullable=True)
    sex = Column(String(20), nullable=True)
    phone = Column(String(20), nullable=True)
    village_id = Column(String(36), nullable=True)
    village_name = Column(String(150), default="Kalyanpur")
    preferred_language = Column(String(10), default="mr-IN")
    abha_reference = Column(String(50), nullable=True)
    is_pregnant = Column(Boolean, default=False)
    gestational_weeks = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=utc_now)

    user = relationship("User", back_populates="citizen_profile")
    cases = relationship("Case", back_populates="citizen")

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
    professional_registration = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=utc_now)

    user = relationship("User", back_populates="worker_profile")

class Facility(Base):
    __tablename__ = "facilities"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    code = Column(String(50), unique=True, index=True, nullable=False) # e.g. PHC-09
    name = Column(String(200), nullable=False)
    facility_type = Column(String(50), default="PHC") # PHC, CHC, SUB_CENTER, DISTRICT_HOSPITAL
    district_id = Column(String(36), nullable=True)
    district_name = Column(String(150), default="District 04")
    block_name = Column(String(150), default="Kalyanpur Block")
    address = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utc_now)

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
    created_at = Column(DateTime, default=utc_now)

    case = relationship("Case", back_populates="referrals")

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

class Prescription(Base):
    __tablename__ = "prescriptions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    consultation_id = Column(String(36), ForeignKey("consultations.id"), nullable=False, index=True)
    doctor_id = Column(String(36), nullable=False)
    status = Column(String(50), default="SIGNED")
    issued_at = Column(DateTime, default=utc_now)
    signature_ref = Column(String(255), nullable=True)

    consultation = relationship("Consultation", back_populates="prescriptions")
    items = relationship("PrescriptionItem", back_populates="prescription", cascade="all, delete-orphan")

class PrescriptionItem(Base):
    __tablename__ = "prescription_items"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    prescription_id = Column(String(36), ForeignKey("prescriptions.id"), nullable=False, index=True)
    medicine = Column(String(200), nullable=False)
    strength = Column(String(100), nullable=True)
    form = Column(String(50), default="Tablet") # Tablet, Syrup, Injection
    dose = Column(String(50), default="1 tablet")
    frequency = Column(String(50), default="Twice daily")
    duration = Column(String(50), default="5 days")
    timing = Column(String(50), default="After food")
    instructions = Column(String(255), nullable=True)

    prescription = relationship("Prescription", back_populates="items")

class TestOrder(Base):
    __tablename__ = "test_orders"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    consultation_id = Column(String(36), ForeignKey("consultations.id"), nullable=False, index=True)
    test_name = Column(String(200), nullable=False)
    priority = Column(String(50), default="URGENT")
    reason = Column(String(255), nullable=True)
    facility_id = Column(String(36), nullable=True)
    status = Column(String(50), default="PENDING")
    ordered_at = Column(DateTime, default=utc_now)

    consultation = relationship("Consultation", back_populates="test_orders")

class FollowUp(Base):
    __tablename__ = "follow_ups"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    case_id = Column(String(36), ForeignKey("cases.id"), nullable=False, index=True)
    task_type = Column(String(100), default="BP_MONITORING")
    assigned_role = Column(Enum(UserRoleEnum), default=UserRoleEnum.ASHA_WORKER)
    assigned_user_id = Column(String(36), nullable=True, index=True)
    instructions = Column(Text, nullable=False)
    priority = Column(Enum(CasePriorityEnum), default=CasePriorityEnum.HIGH)
    due_at = Column(DateTime, nullable=False, index=True)
    status = Column(String(50), default="PENDING", index=True) # PENDING, COMPLETED, OVERDUE
    result = Column(Text, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now)

    case = relationship("Case", back_populates="follow_ups")

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
