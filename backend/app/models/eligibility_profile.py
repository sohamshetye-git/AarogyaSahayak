import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Text, JSON, Numeric
)
from sqlalchemy.orm import relationship
from app.database import Base

def generate_uuid() -> str:
    return str(uuid.uuid4())

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class SchemeEligibilityProfileModel(Base):
    __tablename__ = "scheme_eligibility_profiles"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    citizen_id = Column(String(36), ForeignKey("citizen_profiles.id"), unique=True, nullable=False, index=True)
    
    # Demographics & Geography
    age_years = Column(Integer, nullable=True)
    age_months = Column(Integer, nullable=True)
    date_of_birth = Column(String(20), nullable=True)
    gender = Column(String(20), nullable=True) # FEMALE, MALE, OTHER
    
    state = Column(String(100), default="Maharashtra")
    district = Column(String(100), default="District 04")
    block_taluka = Column(String(100), default="Kalyanpur Block")
    gram_panchayat = Column(String(100), default="Kalyanpur GP")
    village_name = Column(String(150), default="Kalyanpur")
    area_type = Column(String(20), default="RURAL") # RURAL, URBAN
    
    # Maternal / Child Status
    is_pregnant = Column(Boolean, default=False)
    gestational_weeks = Column(Integer, nullable=True)
    is_lactating = Column(Boolean, default=False)
    postpartum_days = Column(Integer, nullable=True)
    child_order = Column(Integer, nullable=True)
    second_child_gender = Column(String(20), nullable=True)
    living_children_count = Column(Integer, default=0)
    planned_delivery_facility_type = Column(String(50), default="GOVERNMENT") # GOVERNMENT, JSY_ACCREDITED_PRIVATE, PRIVATE, HOME
    is_tribal_woman = Column(Boolean, default=False)
    
    # Social Category & Economic Status
    social_category = Column(String(50), nullable=True) # SC, ST, OBC, GENERAL
    household_category = Column(String(50), default="OTHER") # BPL, ANTYODAYA, AAY, PRIORITY, OTHER
    ration_card_category = Column(String(50), nullable=True) # YELLOW, ORANGE, WHITE, BPL, AAY
    has_bpl_ration_card = Column(Boolean, nullable=True)
    has_nfsa_ration_card = Column(Boolean, nullable=True)
    annual_family_income = Column(Numeric(14, 2), nullable=True)
    net_family_income_annual = Column(Numeric(14, 2), nullable=True)
    
    # Disability
    has_disability = Column(Boolean, default=False)
    disability_percent = Column(Float, nullable=True)
    
    # Scheme Registrations & Welfare Identifiers
    has_aadhaar = Column(Boolean, default=True)
    is_pmjay_beneficiary = Column(Boolean, default=False)
    has_e_shram_card = Column(Boolean, default=False)
    has_mgnrega_job_card = Column(Boolean, default=False)
    is_pm_kisan_woman_beneficiary = Column(Boolean, default=False)
    is_pregnant_lactating_aww_awh_asha = Column(Boolean, default=False)
    received_same_equipment_free_from_government_within_3_years = Column(Boolean, default=False)
    
    # Health Conditions (for relevant disease programs)
    suspected_tb = Column(Boolean, default=False)
    diagnosed_tb = Column(Boolean, default=False)
    diagnosed_and_notified_tb = Column(Boolean, default=False)
    suspected_or_diagnosed_leprosy = Column(Boolean, default=False)
    is_sick_infant = Column(Boolean, default=False)
    
    # Metadata, Audit & Field Provenance
    field_provenance_json = Column(JSON, default=dict) # { field_name: { "source": "CITIZEN_REPORTED"|"ASHA_CAPTURED", "captured_by": user_id, "updated_at": iso_str } }
    extra_facts_json = Column(JSON, default=dict) # Any arbitrary extended questionnaire facts
    consent_obtained = Column(Boolean, default=True)
    captured_by_user_id = Column(String(36), nullable=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    citizen = relationship("CitizenProfile", backref="scheme_eligibility_profile")
