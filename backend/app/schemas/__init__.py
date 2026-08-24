from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

# --- Common / Envelope ---
class StandardResponse(BaseModel):
    data: Any
    request_id: Optional[str] = None

class ErrorDetail(BaseModel):
    code: str
    message: str
    fields: Optional[Dict[str, str]] = None

class ErrorResponse(BaseModel):
    error: ErrorDetail
    request_id: Optional[str] = None

# --- Auth Schemas ---
class LoginRequest(BaseModel):
    identifier: str = Field(..., description="Username, phone, or staff ID")
    password: str

class UserSessionDTO(BaseModel):
    id: str
    identifier: str
    name: str
    role: str
    preferred_language: str = "mr-IN"
    facility_id: Optional[str] = None
    facility_name: Optional[str] = None
    village_ids: Optional[List[str]] = None
    district_id: Optional[str] = None

class AuthResponseData(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserSessionDTO

# --- Vitals & Symptoms ---
class VitalRecordInput(BaseModel):
    systolic_bp: Optional[int] = None
    diastolic_bp: Optional[int] = None
    temperature_c: Optional[float] = None
    spo2: Optional[int] = None
    pulse: Optional[int] = None
    respiratory_rate: Optional[int] = None
    glucose_mg_dl: Optional[float] = None
    weight_kg: Optional[float] = None

class VitalRecordDTO(VitalRecordInput):
    id: str
    case_id: str
    is_warning_sign: bool = False
    source_type: str
    recorded_by: Optional[str] = None
    recorded_at: datetime

class SymptomDTO(BaseModel):
    id: Optional[str] = None
    term: str
    normalized_term: str
    severity: Optional[str] = None
    duration_text: Optional[str] = None
    source_type: str = "CITIZEN_REPORTED"

# --- Citizen Schemas ---
class CitizenCreateCaseRequest(BaseModel):
    client_case_id: Optional[str] = None
    preferred_language: str = "mr-IN"
    spoken_transcript: Optional[str] = None
    symptoms: List[str] = []
    is_pregnant: bool = False
    gestational_weeks: Optional[int] = None
    vitals: Optional[VitalRecordInput] = None
    consent_to_process: bool = True

class CitizenCaseDTO(BaseModel):
    id: str
    reference: str
    priority: str
    status: str
    primary_concern: str
    preferred_language: str
    assigned_asha_name: Optional[str] = None
    assigned_facility_name: Optional[str] = None
    safety_rule_triggered: bool = False
    safety_rule_reason: Optional[str] = None
    citizen_guidance_text: Optional[str] = None
    created_at: datetime
    updated_at: datetime

# --- ASHA Schemas ---
class AshaTaskDTO(BaseModel):
    id: str
    case_id: str
    case_reference: str
    citizen_name: str
    village_name: str
    priority: str
    status: str
    primary_concern: str
    is_pregnant: bool = False
    gestational_weeks: Optional[int] = None
    created_at: datetime
    assigned_asha_name: Optional[str] = None

class AshaDashboardResponse(BaseModel):
    worker_name: str
    village: str
    total_assigned: int
    urgent_count: int
    pending_visits: int
    active_followups: int
    recent_tasks: List[AshaTaskDTO]

class AshaAcknowledgeRequest(BaseModel):
    acknowledged_at: Optional[datetime] = None

class AshaContactResultRequest(BaseModel):
    outcome: str # SPOKE_TO_CITIZEN, CITIZEN_UNREACHABLE, FAMILY_RESPONDED
    notes: Optional[str] = None
    next_action: str # PLAN_VISIT, ESCALATE, RESCHEDULE

class AshaVisitSubmitRequest(BaseModel):
    case_id: str
    consent_obtained: bool = True
    symptoms: List[str] = []
    vitals: Optional[VitalRecordInput] = None
    notes: Optional[str] = None
    next_action: str = "REFER_TO_PHC"
    refer_to_facility_id: Optional[str] = None

class AshaReferralRequest(BaseModel):
    facility_id: str
    urgency: str = "URGENT"
    reason: str
    transport_required: bool = False

class AshaFollowUpDTO(BaseModel):
    id: str
    case_id: str
    case_reference: str
    citizen_name: str
    citizen_phone: Optional[str] = None
    village_name: str
    is_pregnant: bool = False
    task_type: str
    instructions: str
    priority: str
    due_at: datetime
    status: str
    completed_at: Optional[datetime] = None
    result: Optional[str] = None

class AshaFollowUpSubmitRequest(BaseModel):
    vitals: Optional[VitalRecordInput] = None
    medication_adherent: bool = True
    symptoms_improved: bool = True
    notes: str
    escalate_to_doctor: bool = False

class TimelineEventDTO(BaseModel):
    id: str
    timestamp: datetime
    event_type: str
    title: str
    description: str
    actor_role: str
    actor_name: Optional[str] = None
    badge_type: Optional[str] = "info"

# --- Doctor Schemas ---
class DoctorReferralDTO(BaseModel):
    id: str
    reference: str
    case_id: str
    case_reference: str
    citizen_name: str
    citizen_age: Optional[int] = None
    is_pregnant: bool = False
    gestational_weeks: Optional[int] = None
    urgency: str
    reason: str
    status: str
    referring_asha_name: Optional[str] = None
    created_at: datetime
    acknowledged_at: Optional[datetime] = None

class DoctorDashboardResponse(BaseModel):
    doctor_name: str
    facility_name: str
    urgent_referrals_count: int
    today_consultations_count: int
    pending_followups_count: int
    referrals: List[DoctorReferralDTO]

class PrescriptionItemInput(BaseModel):
    medicine: str
    strength: Optional[str] = None
    form: str = "Tablet"
    dose: str = "1 tablet"
    frequency: str = "Twice daily"
    duration: str = "5 days"
    timing: Optional[str] = "After food"
    instructions: Optional[str] = None

class DoctorConsultationSubmitRequest(BaseModel):
    case_id: str
    examination_notes: Optional[str] = None
    clinical_summary: Optional[str] = None
    provisional_diagnosis: Optional[str] = None
    confirmed_diagnosis: str
    icd10_code: Optional[str] = None
    prescription_items: List[PrescriptionItemInput] = []
    investigation_orders: List[str] = []
    care_plan_summary: Optional[str] = None
    asha_followup_instructions: Optional[str] = None
    followup_due_days: int = 3

# --- Admin Schemas ---
class ClusterAlertDTO(BaseModel):
    id: str
    alert_title: str
    district_name: str
    block_name: str
    village_name: str
    symptom_group: str
    case_count: int
    time_window_hours: int
    risk_level: str
    status: str
    created_at: datetime

class AdminDashboardResponse(BaseModel):
    district_name: str
    total_cases: int
    urgent_cases: int
    active_referrals: int
    completed_consultations: int
    active_cluster_alerts: int
    maternal_high_risk_cases: int
    alerts: List[ClusterAlertDTO]

class SystemHealthResponse(BaseModel):
    status: str = "HEALTHY"
    database_connected: bool = True
    integration_mode: str = "mock"
    services: Dict[str, str]
