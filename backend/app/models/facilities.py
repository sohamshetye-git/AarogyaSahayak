import uuid
from datetime import datetime, timezone, time as dt_time, date
import enum
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, Date, Time, ForeignKey, Text, Enum, JSON
)
from sqlalchemy.orm import relationship
from app.database import Base

def generate_uuid() -> str:
    return str(uuid.uuid4())

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class FacilityTypeEnum(str, enum.Enum):
    SUB_CENTRE = "SUB_CENTRE"
    SUB_CENTER = "SUB_CENTER" # legacy compatibility
    PHC = "PHC"
    PRIMARY_HEALTH_CENTRE = "PRIMARY_HEALTH_CENTRE"
    CHC = "CHC"
    COMMUNITY_HEALTH_CENTRE = "COMMUNITY_HEALTH_CENTRE"
    SUB_DISTRICT_HOSPITAL = "SUB_DISTRICT_HOSPITAL"
    DISTRICT_HOSPITAL = "DISTRICT_HOSPITAL"
    HOSPITAL = "HOSPITAL" # legacy compatibility
    SPECIALIZED_HOSPITAL = "SPECIALIZED_HOSPITAL"
    DIAGNOSTIC_CENTRE = "DIAGNOSTIC_CENTRE"
    TB_NCD_CENTRE = "TB_NCD_CENTRE"
    AYUSHMAN_HELP_DESK = "AYUSHMAN_HELP_DESK"
    PHARMACY = "PHARMACY"


class FacilityOwnershipEnum(str, enum.Enum):
    GOVERNMENT = "GOVERNMENT"
    PRIVATE_EMPANELLED = "PRIVATE_EMPANELLED"
    NGO_CHARITABLE = "NGO_CHARITABLE"

class VerificationStatusEnum(str, enum.Enum):
    VERIFIED = "VERIFIED"
    UNVERIFIED = "UNVERIFIED"
    REPORTED = "REPORTED"
    SUSPENDED = "SUSPENDED"

class ServiceAvailabilityStatusEnum(str, enum.Enum):
    VERIFIED_AVAILABLE = "VERIFIED_AVAILABLE"
    REPORTED_UNCONFIRMED = "REPORTED_UNCONFIRMED"
    UNAVAILABLE = "UNAVAILABLE"
    UNKNOWN = "UNKNOWN"

class AssistanceStatusEnum(str, enum.Enum):
    PENDING = "PENDING"
    CONTACTED = "CONTACTED"
    TRANSPORT_PLANNED = "TRANSPORT_PLANNED"
    DEPARTED = "DEPARTED"
    ARRIVED = "ARRIVED"
    COMPLETED = "COMPLETED"
    ESCALATED_TO_DOCTOR = "ESCALATED_TO_DOCTOR"
    UNREACHABLE = "UNREACHABLE"
    RESCHEDULED = "RESCHEDULED"
    CANCELLED = "CANCELLED"

class AppointmentStatusEnum(str, enum.Enum):
    REQUESTED = "REQUESTED"
    FACILITY_REVIEW = "FACILITY_REVIEW"
    CONFIRMED = "CONFIRMED"
    ARRIVED = "ARRIVED"
    IN_SERVICE = "IN_SERVICE"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    RESCHEDULED = "RESCHEDULED"
    NO_SHOW = "NO_SHOW"
    UNAVAILABLE = "UNAVAILABLE"

class Facility(Base):
    __tablename__ = "facilities"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    public_reference = Column(String(50), unique=True, index=True, nullable=True, default=lambda: f"FAC-{uuid.uuid4().hex[:8].upper()}") # e.g. FAC-2026-001
    code = Column(String(50), unique=True, index=True, nullable=True) # legacy compat e.g. PHC-09
    official_name = Column(String(255), nullable=True)
    name = Column(String(255), nullable=True) # legacy compat
    localized_name = Column(JSON, default=dict) # {"mr-IN": "...", "hi-IN": "...", "en-IN": "..."}
    facility_type = Column(Enum(FacilityTypeEnum), default=FacilityTypeEnum.PHC, nullable=False, index=True)
    ownership = Column(Enum(FacilityOwnershipEnum), default=FacilityOwnershipEnum.GOVERNMENT, nullable=False)
    authority = Column(String(150), default="Public Health Department, Maharashtra")
    
    # Location
    state = Column(String(100), default="Maharashtra")
    district = Column(String(100), default="District 04")
    district_id = Column(String(36), nullable=True)
    district_name = Column(String(150), default="District 04") # legacy compat
    block = Column(String(100), default="Kalyanpur Block")
    block_name = Column(String(150), default="Kalyanpur Block") # legacy compat
    village = Column(String(150), nullable=True)
    pincode = Column(String(10), nullable=True, index=True)
    address = Column(String(255), nullable=True)
    landmark = Column(String(255), nullable=True)
    latitude = Column(Float, nullable=True, default=18.5204)
    longitude = Column(Float, nullable=True, default=73.8567)

    
    # Contact
    phone = Column(String(30), nullable=True)
    email = Column(String(150), nullable=True)
    emergency_helpline = Column(String(30), default="108")
    
    # Status & Freshness
    is_active = Column(Boolean, default=True)
    verification_status = Column(Enum(VerificationStatusEnum), default=VerificationStatusEnum.VERIFIED, index=True)
    source_id = Column(String(100), default="GOVT_REGISTRY_NIN")
    source_name = Column(String(150), default="National Health Portal / State Registry")
    last_verified_at = Column(DateTime, default=utc_now)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    services = relationship("FacilityService", back_populates="facility", cascade="all, delete-orphan")
    hours = relationship("FacilityHours", back_populates="facility", cascade="all, delete-orphan")
    schemes = relationship("FacilitySchemeEmpanelment", back_populates="facility", cascade="all, delete-orphan")
    searches = relationship("FacilitySearch", back_populates="selected_facility")
    assistance_requests = relationship("FacilityAssistanceRequest", back_populates="facility")
    appointment_requests = relationship("FacilityAppointmentRequest", back_populates="facility")


class FacilityService(Base):
    __tablename__ = "facility_services"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    facility_id = Column(String(36), ForeignKey("facilities.id"), nullable=False, index=True)
    service_code = Column(String(100), nullable=False, index=True) # e.g. EMERGENCY_24X7, MATERNITY_DELIVERY, CHILD_VACCINATION, TB_DOTS, NCD_DIABETES_BP, PATHOLOGY_XRAY, AYUSHMAN_HELP_DESK, PHARMACY, GENERAL_OPD
    localized_service_name = Column(JSON, default=dict) # {"mr-IN": "प्रसूती सेवा", "hi-IN": "प्रसव सेवा", "en-IN": "Maternity and Delivery"}
    service_level = Column(String(50), default="PRIMARY") # PRIMARY, SECONDARY, TERTIARY
    availability_status = Column(Enum(ServiceAvailabilityStatusEnum), default=ServiceAvailabilityStatusEnum.VERIFIED_AVAILABLE)
    emergency_capability = Column(Boolean, default=False, index=True)
    appointment_requirement = Column(Boolean, default=False)
    cost_type = Column(String(50), default="FREE") # FREE, SUBSIDIZED, SCHEME_CASHLESS, CHARGEABLE
    source = Column(String(150), default="Facility Inspection 2026")
    last_verified_at = Column(DateTime, default=utc_now)
    created_at = Column(DateTime, default=utc_now)

    facility = relationship("Facility", back_populates="services")


class FacilityHours(Base):
    __tablename__ = "facility_hours"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    facility_id = Column(String(36), ForeignKey("facilities.id"), nullable=False, index=True)
    day_of_week = Column(String(20), nullable=False) # MONDAY, TUESDAY, WEDNESDAY, THURSDAY, FRIDAY, SATURDAY, SUNDAY, ALL_DAYS
    opening_time = Column(String(10), nullable=True) # "08:00"
    closing_time = Column(String(10), nullable=True) # "16:00"
    is_24x7_emergency = Column(Boolean, default=False)
    verification_status = Column(Enum(VerificationStatusEnum), default=VerificationStatusEnum.VERIFIED)
    source = Column(String(150), default="Official Gazette")
    last_verified_at = Column(DateTime, default=utc_now)
    created_at = Column(DateTime, default=utc_now)

    facility = relationship("Facility", back_populates="hours")


class FacilitySchemeEmpanelment(Base):
    __tablename__ = "facility_scheme_empanelments"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    facility_id = Column(String(36), ForeignKey("facilities.id"), nullable=False, index=True)
    scheme_code = Column(String(100), nullable=False, index=True) # PMJAY, MJPJAY, JSY, JSSK, PMMVY, RBSK, NIKSHAY
    scheme_name = Column(String(200), nullable=False)
    empanelment_reference = Column(String(100), nullable=True)
    specialties_covered = Column(JSON, default=list) # e.g. ["General Medicine", "Obstetrics & Gynaecology", "Cardiology"]
    effective_from = Column(Date, nullable=True)
    effective_until = Column(Date, nullable=True)
    verification_status = Column(Enum(VerificationStatusEnum), default=VerificationStatusEnum.VERIFIED)
    official_source = Column(String(255), default="State Health Assurance Society (SHAS)")
    last_verified_at = Column(DateTime, default=utc_now)
    created_at = Column(DateTime, default=utc_now)

    facility = relationship("Facility", back_populates="schemes")


class FacilitySearch(Base):
    __tablename__ = "facility_searches"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    citizen_id = Column(String(36), ForeignKey("citizen_profiles.id"), nullable=True, index=True)
    household_member_id = Column(String(36), ForeignKey("household_members.id"), nullable=True, index=True)
    requested_service = Column(String(100), nullable=True)
    urgency = Column(String(50), default="ROUTINE") # ROUTINE, URGENT, EMERGENCY
    patient_category = Column(String(50), default="GENERAL") # MATERNAL, CHILD, ADULT, ELDERLY, NCD
    location_method = Column(String(50), default="GPS") # GPS, PINCODE_VILLAGE, SAVED, ASHA_HELP
    coordinates_or_locality = Column(JSON, default=dict) # {"latitude": ..., "longitude": ..., "village": "...", "pincode": "..."}
    consent_reference = Column(String(100), nullable=True)
    consent_purpose = Column(String(255), default="Healthcare facility matching")
    consent_timestamp = Column(DateTime, default=utc_now)
    filters_applied = Column(JSON, default=dict)
    result_facility_ids = Column(JSON, default=list)
    selected_facility_id = Column(String(36), ForeignKey("facilities.id"), nullable=True, index=True)
    created_at = Column(DateTime, default=utc_now)

    citizen = relationship("CitizenProfile", foreign_keys=[citizen_id])
    household_member = relationship("HouseholdMember", foreign_keys=[household_member_id])
    selected_facility = relationship("Facility", foreign_keys=[selected_facility_id], back_populates="searches")


class FacilityCallEvent(Base):
    __tablename__ = "facility_call_events"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    facility_id = Column(String(36), ForeignKey("facilities.id"), nullable=False, index=True)
    citizen_id = Column(String(36), ForeignKey("citizen_profiles.id"), nullable=True, index=True)
    dialled_phone = Column(String(30), nullable=False)
    event_type = Column(String(50), default="CALL_INITIATED") # CALL_INITIATED (never claims call connected)
    initiated_at = Column(DateTime, default=utc_now)
    contact_feedback = Column(String(50), nullable=True) # CONNECTED, UNREACHABLE, BUSY, CANCELLED_BY_USER

    facility = relationship("Facility")
    citizen = relationship("CitizenProfile")


class FacilityAssistanceRequest(Base):
    __tablename__ = "facility_assistance_requests"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    request_reference = Column(String(100), unique=True, nullable=False, index=True)
    citizen_id = Column(String(36), ForeignKey("citizen_profiles.id"), nullable=False, index=True)
    household_member_id = Column(String(36), ForeignKey("household_members.id"), nullable=True, index=True)
    case_id = Column(String(36), ForeignKey("cases.id"), nullable=True, index=True)
    need_id = Column(String(36), ForeignKey("citizen_needs.id"), nullable=True, index=True)
    facility_id = Column(String(36), ForeignKey("facilities.id"), nullable=False, index=True)
    assistance_type = Column(String(50), default="TRANSPORT_AND_DIRECTION") # TRANSPORT, DIRECTION_GUIDANCE, ACCOMPANY_VISIT, EMERGENCY_EVACUATION
    safety_priority = Column(String(50), default="ROUTINE") # ROUTINE, HIGH, URGENT, EMERGENCY
    assistance_reason = Column(Text, nullable=False)
    transport_needed = Column(Boolean, default=False)
    assigned_asha_id = Column(String(36), nullable=True, index=True)
    assigned_asha_name = Column(String(150), default="Sita Patel (Kalyanpur)")
    citizen_location = Column(JSON, default=dict)
    preferred_contact = Column(String(50), default="PHONE")
    consent_given = Column(Boolean, default=True)
    status = Column(Enum(AssistanceStatusEnum), default=AssistanceStatusEnum.PENDING, index=True)
    due_at = Column(DateTime, nullable=True)
    transport_plan = Column(JSON, default=dict) # {"mode": "Auto/108", "departure_time": "...", "driver_contact": "..."}
    outcome = Column(Text, nullable=True)
    idempotency_key = Column(String(100), unique=True, nullable=True, index=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    citizen = relationship("CitizenProfile", foreign_keys=[citizen_id])
    household_member = relationship("HouseholdMember", foreign_keys=[household_member_id])
    case = relationship("Case", foreign_keys=[case_id])
    need = relationship("CitizenNeed", foreign_keys=[need_id])
    facility = relationship("Facility", foreign_keys=[facility_id], back_populates="assistance_requests")


class FacilityAppointmentRequest(Base):
    __tablename__ = "facility_appointment_requests"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    appointment_reference = Column(String(100), unique=True, nullable=False, index=True) # e.g. APT-2026-001
    citizen_id = Column(String(36), ForeignKey("citizen_profiles.id"), nullable=False, index=True)
    household_member_id = Column(String(36), ForeignKey("household_members.id"), nullable=True, index=True)
    facility_id = Column(String(36), ForeignKey("facilities.id"), nullable=False, index=True)
    service_code = Column(String(100), nullable=False) # e.g. CHILD_VACCINATION, GENERAL_OPD, ANTENATAL_CARE
    service_name = Column(String(200), nullable=False)
    requested_slot = Column(String(100), nullable=False) # e.g. "2026-08-28 10:00 AM - 12:00 PM"
    status = Column(Enum(AppointmentStatusEnum), default=AppointmentStatusEnum.REQUESTED, index=True)
    facility_confirmation_source = Column(String(150), nullable=True) # e.g. "PHC Kalyanpur OPD Desk"
    confirmed_slot = Column(DateTime, nullable=True)
    doctor_or_desk_notes = Column(Text, nullable=True)
    idempotency_key = Column(String(100), unique=True, nullable=True, index=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    citizen = relationship("CitizenProfile", foreign_keys=[citizen_id])
    household_member = relationship("HouseholdMember", foreign_keys=[household_member_id])
    facility = relationship("Facility", foreign_keys=[facility_id], back_populates="appointment_requests")


class UserLocationPreference(Base):
    __tablename__ = "user_location_preferences"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, unique=True, index=True)
    preferred_source = Column(String(50), default="DEVICE_GPS", nullable=False) # DEVICE_GPS, MANUAL_VILLAGE, MANUAL_PINCODE, REGISTERED_HOME
    manual_village_id = Column(String(36), nullable=True)
    manual_village_name = Column(String(150), nullable=True)
    manual_pincode = Column(String(10), nullable=True)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    user = relationship("User", foreign_keys=[user_id])


class CareRequestLocation(Base):
    __tablename__ = "care_request_locations"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    service_request_id = Column(String(36), ForeignKey("service_requests.id"), nullable=True, index=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    accuracy_meters = Column(Float, nullable=True)
    altitude_meters = Column(Float, nullable=True)
    source = Column(String(50), default="DEVICE_GPS", nullable=False) # DEVICE_GPS, MANUAL_VILLAGE, MANUAL_PINCODE, MAP_SELECTED, REGISTERED_HOME
    formatted_address = Column(Text, nullable=True)
    village = Column(String(150), nullable=True)
    pincode = Column(String(10), nullable=True)
    block = Column(String(150), nullable=True)
    district = Column(String(150), nullable=True)
    state = Column(String(100), default="Maharashtra")
    place_id = Column(String(150), nullable=True)
    captured_at = Column(DateTime, default=utc_now)
    confirmed_at = Column(DateTime, default=utc_now)

    service_request = relationship("ServiceRequest", foreign_keys=[service_request_id])


class VisitLocation(Base):
    __tablename__ = "visit_locations"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    visit_id = Column(String(36), ForeignKey("asha_visits.id"), nullable=False, index=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    accuracy_meters = Column(Float, nullable=True)
    source = Column(String(50), default="DEVICE_GPS", nullable=False)
    captured_at = Column(DateTime, default=utc_now)

    visit = relationship("AshaVisit", foreign_keys=[visit_id])

