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

class UserDistrictDTO(BaseModel):
    id: Optional[str] = None
    name: Optional[str] = None

class UserFacilityDTO(BaseModel):
    id: Optional[str] = None
    name: Optional[str] = None

class UserCoverageDTO(BaseModel):
    village_id: Optional[str] = None
    village_ids: Optional[List[str]] = None
    village_name: Optional[str] = None
    coverage_area: Optional[str] = None

class UserSessionDTO(BaseModel):
    id: str
    identifier: str
    name: str
    full_name: Optional[str] = None
    role: str
    preferred_language: str = "mr-IN"
    facility_id: Optional[str] = None
    facility_name: Optional[str] = None
    village_ids: Optional[List[str]] = None
    village_name: Optional[str] = None
    district_id: Optional[str] = None
    district_name: Optional[str] = None
    coverage_area: Optional[str] = None
    district: Optional[UserDistrictDTO] = None
    facility: Optional[UserFacilityDTO] = None
    coverage: Optional[UserCoverageDTO] = None
    must_change_password: bool = False
    staff_id: Optional[str] = None
    account_status: str = "ACTIVE"

class ChangePasswordRequest(BaseModel):
    old_password: str = Field(..., description="Current password or temporary password")
    new_password: str = Field(..., min_length=6, description="New secure password")


class UserPreferencesUpdateRequest(BaseModel):
    preferred_language: str = Field(..., pattern="^(en-IN|hi-IN|mr-IN)$", description="User preferred language code")

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
    citizen_age: Optional[int] = None
    citizen_phone: Optional[str] = None
    village_name: str
    priority: str
    status: str
    primary_concern: str
    is_pregnant: bool = False
    gestational_weeks: Optional[int] = None
    created_at: datetime
    scheduled_visit_time: Optional[datetime] = None
    assigned_asha_name: Optional[str] = None

class AshaDashboardResponse(BaseModel):
    worker_name: str
    village: str
    total_assigned: int
    urgent_count: int
    pending_visits: int
    active_followups: int
    urgent_unacknowledged_count: int = 0
    todays_visits_count: int = 0
    overdue_followups_count: int = 0
    doctor_instructions_count: int = 0
    total_assigned_citizens: int = 0
    pending_sync_count: int = 0
    recent_tasks: List[AshaTaskDTO]

class AshaAcknowledgeRequest(BaseModel):
    acknowledged_at: Optional[datetime] = None

class AshaContactResultRequest(BaseModel):
    outcome: str # SPOKE_TO_CITIZEN, CITIZEN_UNREACHABLE, FAMILY_RESPONDED
    notes: Optional[str] = None
    next_action: Optional[str] = "PLAN_VISIT" # PLAN_VISIT, ESCALATE, RESCHEDULE
    respondent_type: Optional[str] = "CITIZEN" # CITIZEN, FAMILY_MEMBER
    current_condition_update: Optional[str] = None
    preferred_visit_time: Optional[str] = None
    attempt_number: Optional[int] = 1
    reason_unreachable: Optional[str] = None
    next_attempt_date: Optional[str] = None
    escalate_to_phc: Optional[bool] = False

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
    follow_up_id: Optional[str] = None
    case_id: Optional[str] = None
    case_reference: Optional[str] = None
    citizen_id: Optional[str] = None
    citizen_name: str
    citizen_age: Optional[int] = None
    citizen_gender: Optional[str] = None
    citizen_phone: Optional[str] = None
    village_name: str
    is_pregnant: bool = False
    gestational_weeks: Optional[int] = None
    category: str = "General"  # Pregnancy, Child, NCD, General
    source: str = "ASHA_SCHEDULED"  # ASHA_SCHEDULED or DOCTOR_ASSIGNED
    assigned_asha_id: Optional[str] = None
    assigned_doctor_id: Optional[str] = None
    doctor_name: Optional[str] = None
    task_type: str = "GENERAL_FOLLOWUP"
    reason: Optional[str] = None
    instructions: str
    measurements_to_repeat: Optional[List[str]] = None
    latest_vitals: Optional[Dict[str, Any]] = None
    adherence_required: bool = True
    escalation_conditions: Optional[str] = None
    priority: str
    due_at: datetime
    is_overdue: bool = False
    status: str
    assigned_asha_name: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    completion_notes: Optional[str] = None
    symptoms_outcome: Optional[str] = None
    result: Optional[str] = None
    sync_status: str = "SYNCED"

class AshaFollowUpSubmitRequest(BaseModel):
    vitals: Optional[VitalRecordInput] = None
    medication_adherent: bool = True
    phc_attended: bool = False
    symptoms_improved: bool = True
    symptoms_outcome: Optional[str] = "IMPROVED"  # IMPROVED, UNCHANGED, WORSENED
    notes: str
    escalate_to_doctor: bool = False
    next_followup_required: bool = False
class AshaAddSymptomsRequest(BaseModel):
    symptoms: List[str]
    onset_duration: Optional[str] = None
    severity: Optional[str] = None  # Mild, Moderate, Severe
    notes: Optional[str] = None
    followup_id: Optional[str] = None

class AshaRecordVitalsRequest(BaseModel):
    systolic_bp: Optional[int] = None
    diastolic_bp: Optional[int] = None
    spo2: Optional[int] = None
    pulse: Optional[int] = None
    temperature_c: Optional[float] = None
    weight_kg: Optional[float] = None
    glucose_mg_dl: Optional[float] = None
    respiratory_rate: Optional[int] = None
    notes: Optional[str] = None
    followup_id: Optional[str] = None

class TimelineEventDTO(BaseModel):
    id: str
    timestamp: datetime
    event_type: str
    title: str
    description: str
    actor_role: str
    actor_name: Optional[str] = None
    badge_type: Optional[str] = "info"

class DoctorReferralDTO(BaseModel):
    id: str
    referral_id: Optional[str] = None
    referral_reference: Optional[str] = None
    reference: str
    case_id: str
    case_reference: str
    citizen_id: Optional[str] = None
    citizen_name: str
    citizen_age: Optional[int] = None
    citizen_gender: Optional[str] = None
    village_name: Optional[str] = None
    citizen_phone: Optional[str] = None
    is_pregnant: bool = False
    gestational_weeks: Optional[int] = None
    category: str = "GENERAL"  # MATERNAL, CHILD, NCD, GENERAL
    urgency: str
    reason: str
    status: str
    arrival_status: str = "WAITING_ARRIVAL"  # WAITING_ARRIVAL, ARRIVED, TRANSPORT_EN_ROUTE
    referring_asha_name: Optional[str] = None
    referring_asha_phone: Optional[str] = None
    citizen_reported_concern: Optional[str] = None
    asha_confirmed_symptoms: List[str] = []
    latest_vitals: Optional[Dict[str, Any]] = None
    created_at: datetime
    referred_at: Optional[datetime] = None
    acknowledged_at: Optional[datetime] = None
    arrived_at: Optional[datetime] = None
    allowed_actions: List[str] = []

class DoctorDashboardMetricsDTO(BaseModel):
    new_referrals_count: int
    urgent_cases_count: int
    awaiting_consultation_count: int
    asha_followups_count: int
    escalations_count: int
    completed_today_count: int

class TodayClinicalWorkDTO(BaseModel):
    patients_arrived: int = 0
    consultations_in_progress: int = 0
    pending_investigations: int = 0
    followups_to_review: int = 0

class WaitingPatientItemDTO(BaseModel):
    citizen_id: str
    citizen_name: str
    age: Optional[int] = 22
    gender: Optional[str] = "Female"
    village_name: Optional[str] = "Ganeshpur"
    case_id: str
    case_reference: str
    referral_id: str
    referral_reference: str
    consultation_id: Optional[str] = None
    consultation_status: Optional[str] = None
    priority: str = "URGENT"
    category: str = "MATERNAL"
    clinical_context: Optional[str] = None
    chief_concern: str
    arrived_at: Optional[str] = None
    waiting_minutes: int = 0
    referring_asha_name: Optional[str] = None
    referring_asha_phone: Optional[str] = None
    latest_vitals: Optional[Dict[str, Any]] = None

class WaitingPatientsResponseDTO(BaseModel):
    items: List[WaitingPatientItemDTO] = []
    total: int = 0

class StartOrResumeConsultationRequest(BaseModel):
    referral_id: str
    idempotency_key: Optional[str] = None

class AshaFollowUpMonitorDTO(BaseModel):
    id: str
    citizen_id: Optional[str] = None
    citizen_name: str
    citizen_age: Optional[int] = None
    village_name: Optional[str] = None
    is_pregnant: bool = False
    case_id: str
    case_reference: str
    task_type: str
    reason: Optional[str] = None
    assigned_asha_name: str
    assigned_asha_phone: Optional[str] = None
    due_at: datetime
    status: str
    repeat_vitals: Optional[Dict[str, Any]] = None
    adherence_reported: Optional[bool] = None
    completion_result: Optional[str] = None
    is_escalated: bool = False

class AshaEscalationItemDTO(BaseModel):
    id: str
    followup_id: str
    case_id: str
    case_reference: str
    citizen_id: Optional[str] = None
    citizen_name: str
    village_name: Optional[str] = None
    is_pregnant: bool = False
    escalation_reason: str
    asha_notes: Optional[str] = None
    latest_vitals: Optional[Dict[str, Any]] = None
    referring_asha_name: str
    referring_asha_phone: Optional[str] = None
    urgency: str = "HIGH"
    escalated_at: datetime
    is_acknowledged: bool = False

class DoctorTimelineEventDTO(BaseModel):
    event_id: str
    event_type: str
    title: str
    safe_description: str
    actor_name: str
    actor_role: str
    occurred_at: datetime
    source_entity_type: str
    source_entity_id: str
    category: str = "GENERAL"  # CITIZEN, ASHA, DOCTOR, REFERRAL, CONSULTATION, INVESTIGATION, FOLLOWUP

class DoctorCaseTimelineResponse(BaseModel):
    case_id: str
    case_reference: str
    citizen_id: str
    citizen_name: str
    citizen_age: Optional[int] = None
    citizen_gender: Optional[str] = None
    village_name: Optional[str] = None
    is_pregnant: bool = False
    gestational_weeks: Optional[int] = None
    priority: str
    status: str
    primary_concern: str
    assigned_asha_name: Optional[str] = None
    assigned_asha_phone: Optional[str] = None
    assigned_facility_name: Optional[str] = None
    latest_vitals: Optional[Dict[str, Any]] = None
    referral_status: Optional[str] = None
    consultation_status: Optional[str] = None
    events: List[DoctorTimelineEventDTO]

class RecentActivityItemDTO(BaseModel):
    id: str
    event_type: str
    title: str
    description: str
    actor_name: str
    actor_role: str
    timestamp: datetime
    case_id: Optional[str] = None
    case_reference: Optional[str] = None

class ClinicalWorkSummaryResponseData(BaseModel):
    generated_at: datetime
    doctor_id: str
    phc_id: str
    ready_to_start: int
    consultations_in_progress: int
    results_ready_for_review: int
    asha_followups_to_review: int

class DoctorInvestigationItemDTO(BaseModel):
    id: str
    investigation_order_id: Optional[str] = None
    test_name: str
    priority: str
    reason: Optional[str] = None
    status: str
    ordered_at: datetime
    reviewed_at: Optional[datetime] = None
    case_id: str
    case_reference: str
    consultation_id: str
    consultation_reference: str
    citizen_id: str
    patient_id: Optional[str] = None
    citizen_name: str
    citizen_age: Optional[int] = None
    citizen_gender: Optional[str] = None
    village_name: Optional[str] = None
    is_abnormal: bool = False
    result: Optional[str] = None

class DoctorFollowUpReviewItemDTO(BaseModel):
    id: str
    case_id: str
    case_reference: str
    citizen_id: str
    citizen_name: str
    citizen_age: Optional[int] = None
    village_name: Optional[str] = None
    assigned_asha_name: str
    task_type: str
    reason: Optional[str] = None
    instructions: str
    priority: str
    due_at: datetime
    completed_at: Optional[datetime] = None
    status: str
    symptoms_outcome: Optional[str] = None
    completion_notes: Optional[str] = None
    escalation_reason: Optional[str] = None
    repeat_vitals: Optional[Dict[str, Any]] = None
    reviewed_by_doctor_at: Optional[datetime] = None

class FollowUpEscalationDTO(BaseModel):
    escalation_id: str
    follow_up_id: str
    case_id: str
    citizen_id: str
    consultation_id: Optional[str] = None
    referral_id: Optional[str] = None
    asha_worker_id: str
    asha_worker_name: str
    patient_name: str
    citizen_age: Optional[int] = None
    citizen_gender: Optional[str] = None
    village_name: Optional[str] = None
    is_pregnant: bool = False
    gestational_weeks: Optional[int] = None
    case_reference: str
    priority: str
    status: str
    reason: str
    escalated_at: datetime
    acknowledged_at: Optional[datetime] = None
    acknowledged_by_doctor_name: Optional[str] = None
    action_type: Optional[str] = None
    action_notes: Optional[str] = None
    resolved_at: Optional[datetime] = None
    resolution: Optional[str] = None
    resolution_outcome: Optional[str] = None
    latest_vitals: Optional[Dict[str, Any]] = None

class EscalationActionRequest(BaseModel):
    action_type: str
    action_notes: str

class EscalationResolveRequest(BaseModel):
    resolution_notes: str
    resolution_outcome: str

class EscalationCallAshaRequest(BaseModel):
    notes: Optional[str] = None

class FollowUpReviewRequest(BaseModel):
    review_notes: str
    next_action: Optional[str] = "NO_FURTHER_ACTION"

class FollowUpRescheduleRequest(BaseModel):
    new_due_at: datetime
    reason: str

class FollowUpCancelRequest(BaseModel):
    reason: str

class RecentCareActivityItemDTO(BaseModel):
    event_id: str
    event_type: str
    title: str
    description: str
    patient_id: str
    patient_name: str
    case_id: str
    case_reference: str
    source_entity_type: str
    source_entity_id: str
    actor_id: Optional[str] = None
    actor_name: str
    actor_role: str
    occurred_at: str
    target_route: str

class RecentCareActivityResponse(BaseModel):
    items: List[RecentCareActivityItemDTO]
    total: int
    page: int = 1
    limit: int = 8

class DoctorDashboardResponse(BaseModel):
    doctor_name: str
    doctor_role: str = "PHC Medical Officer"
    facility_name: str
    facility_code: Optional[str] = "PHC-09"
    metrics: DoctorDashboardMetricsDTO
    urgent_summary: Optional[Dict[str, Any]] = None
    incoming_referrals: List[DoctorReferralDTO]
    today_clinical_work: TodayClinicalWorkDTO
    asha_followups: List[AshaFollowUpMonitorDTO]
    escalations: List[AshaEscalationItemDTO]
    recent_activity: List[RecentCareActivityItemDTO]
    notifications_count: int = 0
    # Backward compatibility fields
    urgent_referrals_count: int = 0
    today_consultations_count: int = 0
    pending_followups_count: int = 0
    referrals: List[DoctorReferralDTO] = []

class PrescriptionItemInput(BaseModel):
    medicine: str
    strength: Optional[str] = None
    form: str = "Tablet"
    dose: str = "1 tablet"
    frequency: str = "Twice daily"
    duration: str = "5 days"
    timing: Optional[str] = "After food"
    instructions: Optional[str] = None

class InvestigationOrderItemInput(BaseModel):
    test_name: str
    priority: str = "ROUTINE"  # URGENT, ROUTINE
    clinical_reason: Optional[str] = None
    preparation_instructions: Optional[str] = None
    target_facility: Optional[str] = "Kalyanpur PHC Lab"
    due_days: int = 1
    status: str = "ORDERED"

class AshaFollowUpDirectiveInput(BaseModel):
    purpose: Optional[str] = None
    priority: str = "HIGH"
    due_days: int = 3
    instructions: str
    measurements_to_repeat: List[str] = []
    adherence_required: bool = True
    phc_attendance_check: bool = False
    escalation_conditions: Optional[str] = None
    citizen_guidance: Optional[str] = None

class HigherFacilityReferralInput(BaseModel):
    target_facility: str = "Kalyanpur CHC"
    clinical_reason: str
    urgency: str = "URGENT"
    transport_type: str = "EMTS_108"
    stabilization_notes: Optional[str] = None
    expected_transfer_time: Optional[str] = None

class PatientGuidanceInput(BaseModel):
    language: str = "mr-IN"  # mr-IN, hi-IN, en-IN
    guidance_text: str
    confirmed_by_doctor: bool = True

class DoctorConsultationSubmitRequest(BaseModel):
    case_id: str
    referral_id: Optional[str] = None
    status: str = "COMPLETED"  # IN_PROGRESS, COMPLETED, AWAITING_INVESTIGATION, FOLLOW_UP_REQUIRED, REFERRED_HIGHER_CENTER
    disposition: str = "DISCHARGE_FOLLOWUP"  # OBSERVATION, AWAIT_INVESTIGATION, SCHEDULED_REVIEW, HIGHER_REFERRAL, EMERGENCY_TRANSFER, DISCHARGE_FOLLOWUP, COMPLETE_NO_FOLLOWUP
    examination_notes: Optional[str] = None
    systemic_examination: Optional[Dict[str, Any]] = None
    clinical_summary: Optional[str] = None
    provisional_diagnosis: Optional[str] = None
    confirmed_diagnosis: str = "Clinical Examination Complete"
    icd10_code: Optional[str] = None
    differential_considerations: Optional[str] = None
    clinical_reasoning: Optional[str] = None
    prescription_items: List[PrescriptionItemInput] = []
    investigation_orders: List[str] = []
    investigation_orders_detailed: List[InvestigationOrderItemInput] = []
    care_plan_summary: Optional[str] = None
    asha_followup_instructions: Optional[str] = None
    followup_due_days: int = 3
    asha_followup_directive: Optional[AshaFollowUpDirectiveInput] = None
    higher_facility_referral: Optional[HigherFacilityReferralInput] = None
    patient_guidance: Optional[PatientGuidanceInput] = None

# --- Doctor FollowUp DTOs ---
class DoctorFollowUpItemDTO(BaseModel):
    follow_up_id: str
    follow_up_reference: str
    case_id: str
    case_reference: str
    citizen_id: str
    citizen_name: str
    patient_name: str
    age: int
    patient_age: int
    gender: str
    patient_gender: str
    village_name: str
    is_pregnant: bool = False
    gestational_weeks: Optional[int] = None
    priority: str
    status: str
    source: str = "DOCTOR_ASSIGNED"
    directive: str
    instructions: str
    assigned_doctor_id: Optional[str] = None
    assigned_doctor_name: Optional[str] = None
    created_by_doctor_name: Optional[str] = None
    assigned_asha_id: Optional[str] = None
    assigned_asha_name: Optional[str] = None
    due_at: Optional[str] = None
    completed_at: Optional[str] = None
    reviewed_at: Optional[str] = None
    latest_vitals: Optional[Dict[str, Any]] = None
    symptoms_outcome: Optional[str] = None
    escalation_reason: Optional[str] = None

class DoctorFollowUpSummaryDTO(BaseModel):
    result_ready: int = 0
    escalated: int = 0
    overdue: int = 0
    due_today: int = 0
    pending_asha: int = 0
    reviewed_today: int = 0
    resolved_today: int = 0
    actionable: int = 0
    total: int = 0

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

# --- Staff Management Schemas ---
class StaffCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=150, description="Full legal name")
    role: str = Field(..., description="Role: ASHA_WORKER or PHC_DOCTOR")
    phone: str = Field(..., min_length=10, max_length=15, description="Phone number")
    email: Optional[str] = None
    employee_id: Optional[str] = None
    preferred_language: str = "mr-IN"
    district: Optional[str] = None
    district_id: Optional[str] = None
    assigned_facility_id: Optional[str] = None
    facility_id: Optional[str] = None
    facility_name: Optional[str] = None
    # ASHA specific
    village_name: Optional[str] = None
    village_ids: Optional[List[str]] = None
    coverage_area: Optional[str] = None
    # Doctor specific
    medical_registration_number: Optional[str] = None
    specialization: Optional[str] = None

class StaffUpdateRequest(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    preferred_language: Optional[str] = None
    village_name: Optional[str] = None
    coverage_area: Optional[str] = None
    specialization: Optional[str] = None
    medical_registration_number: Optional[str] = None

class StaffTransferRequest(BaseModel):
    facility_id: Optional[str] = None
    facility_name: Optional[str] = None
    village_name: Optional[str] = None
    village_ids: Optional[List[str]] = None
    coverage_area: Optional[str] = None
    reason: Optional[str] = None

class StaffSuspendRequest(BaseModel):
    reason: Optional[str] = None

class StaffMemberDTO(BaseModel):
    id: str
    staff_id: str
    identifier: str
    name: str
    role: str
    phone: Optional[str] = None
    phone_masked: Optional[str] = None
    email: Optional[str] = None
    employee_id: Optional[str] = None
    assigned_facility_id: Optional[str] = None
    assigned_facility_name: Optional[str] = None
    district_id: Optional[str] = None
    district_name: Optional[str] = None
    village_ids: Optional[List[str]] = None
    village_name: Optional[str] = None
    coverage_area: Optional[str] = None
    medical_registration_number: Optional[str] = None
    specialization: Optional[str] = None
    preferred_language: str = "mr-IN"
    account_status: str = "ACTIVE"
    must_change_password: bool = False
    last_login_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class StaffSummaryCountsDTO(BaseModel):
    total: int = 0
    active: int = 0
    suspended: int = 0
    asha_workers: int = 0
    phc_doctors: int = 0

class StaffListResponseData(BaseModel):
    summary: StaffSummaryCountsDTO
    staff: List[StaffMemberDTO]
    total: int
    page: int
    limit: int

class StaffCredentialsResponse(BaseModel):
    staff_id: str
    identifier: str
    name: str
    role: str
    temporary_password: str
    must_change_password: bool = True
    notice: str = "Save these credentials now. The temporary password will not be shown again."


# --- Patient Registration Schemas ---
class MedicationItemInput(BaseModel):
    name: str
    dose: Optional[str] = None
    frequency: Optional[str] = None

class PatientRegistrationOptionsResponse(BaseModel):
    states: List[str]
    districts: List[str]
    blocks: List[str]
    villages: List[Dict[str, str]]
    facilities: List[Dict[str, Any]]
    sub_centers: List[Dict[str, str]]
    symptoms: List[Dict[str, str]]
    blood_groups: List[str]
    household_categories: List[str]
    ration_card_categories: List[str]
    special_conditions: List[Dict[str, str]]
    programmes: List[Dict[str, str]]
    languages: List[Dict[str, str]]

class DuplicateCheckRequest(BaseModel):
    abha_number: Optional[str] = None
    phone: Optional[str] = None
    full_name: Optional[str] = None
    date_of_birth: Optional[str] = None
    approximate_age: Optional[int] = None
    village_name: Optional[str] = None
    family_id: Optional[str] = None

class DuplicateCitizenSummary(BaseModel):
    id: str
    display_name: str
    masked_phone: Optional[str] = None
    masked_abha: Optional[str] = None
    village_name: str
    age_estimate: Optional[int] = None
    active_case_count: int = 0
    similarity_reason: str

class DuplicateCheckResponse(BaseModel):
    has_potential_duplicate: bool
    potential_matches: List[DuplicateCitizenSummary] = []

class VitalsInput(BaseModel):
    measured: bool = True
    unmeasured_reason: Optional[str] = None
    systolic_bp: Optional[int] = None
    diastolic_bp: Optional[int] = None
    temperature_c: Optional[float] = None
    spo2: Optional[int] = None
    pulse: Optional[int] = None
    respiratory_rate: Optional[int] = None
    weight_kg: Optional[float] = None
    height_cm: Optional[float] = None
    muac_cm: Optional[float] = None
    glucose_mg_dl: Optional[float] = None
    repeat_bp_systolic: Optional[int] = None
    repeat_bp_diastolic: Optional[int] = None
    measurement_location: Optional[str] = "HOME"

class MaternalConditionInput(BaseModel):
    lmp_date: Optional[str] = None
    edd_date: Optional[str] = None
    gestational_weeks: Optional[int] = None
    gravida: Optional[int] = None
    para: Optional[int] = None
    anc_registered: bool = False
    mcp_card_available: bool = False
    previous_high_risk: bool = False
    last_anc_date: Optional[str] = None
    ifa_adherence: Optional[str] = "REGULAR" # REGULAR, IRREGULAR, NONE
    td_vaccine_taken: bool = False
    bleeding: bool = False
    severe_headache: bool = False
    blurred_vision: bool = False
    severe_swelling: bool = False
    abdominal_pain: bool = False
    reduced_fetal_movement: bool = False
    labour_warning_signs: bool = False

class PostnatalConditionInput(BaseModel):
    delivery_date: Optional[str] = None
    delivery_type: Optional[str] = "NORMAL"
    place_of_delivery: Optional[str] = "INSTITUTIONAL"
    postnatal_day: Optional[int] = None
    maternal_fever: bool = False
    maternal_bleeding: bool = False
    breastfeeding_status: Optional[str] = "EXCLUSIVE"
    newborn_feeding_well: bool = True
    newborn_danger_signs: bool = False

class ChildConditionInput(BaseModel):
    age_in_months: Optional[int] = None
    guardian_name: Optional[str] = None
    immunization_status: Optional[str] = "UP_TO_DATE"
    fever: bool = False
    diarrhoea: bool = False
    vomiting: bool = False
    reduced_intake: bool = False
    dehydration_signs: bool = False

class TBConditionInput(BaseModel):
    cough_duration_weeks: Optional[int] = None
    fever: bool = False
    night_sweats: bool = False
    weight_loss: bool = False
    tb_contact_history: bool = False
    existing_tb_treatment: bool = False
    breathlessness: bool = False

class NCDConditionInput(BaseModel):
    known_hypertension: bool = False
    known_diabetes: bool = False
    previous_monitoring: bool = False
    medicine_adherence: Optional[str] = "REGULAR"
    tobacco_exposure: bool = False

class SpecialConditionsInput(BaseModel):
    condition_type: str = "NONE" # NONE, PREGNANCY, POSTNATAL, CHILD, NCD, TB, NUTRITION, OTHER
    maternal: Optional[MaternalConditionInput] = None
    postnatal: Optional[PostnatalConditionInput] = None
    child: Optional[ChildConditionInput] = None
    tb: Optional[TBConditionInput] = None
    ncd: Optional[NCDConditionInput] = None
    notes: Optional[str] = None

class ReferralInput(BaseModel):
    required: bool = False
    facility_id: Optional[str] = None
    urgency: str = "ROUTINE"
    reason: Optional[str] = None
    transport_assistance_required: bool = False
    citizen_response: str = "ACCEPTED" # ACCEPTED, REFUSED
    refusal_reason: Optional[str] = None

class FollowUpInput(BaseModel):
    required: bool = False
    due_date: Optional[str] = None
    purpose: Optional[str] = None
    notes: Optional[str] = None

class PatientRegistrationRequest(BaseModel):
    client_registration_id: Optional[str] = None
    
    # 1. Identity & Location
    full_name: str = Field(..., min_length=2)
    date_of_birth: Optional[str] = None
    exact_dob_unknown: bool = False
    approximate_age: Optional[int] = None
    sex: str = "FEMALE" # FEMALE, MALE, OTHER
    phone: Optional[str] = None
    alternate_phone: Optional[str] = None
    preferred_contact_method: str = "PHONE"
    abha_number: Optional[str] = None
    address: Optional[str] = None
    village_name: str = "Kalyanpur"
    village_id: Optional[str] = None
    pincode: Optional[str] = None
    state: str = "Maharashtra"
    district: str = "District 04"
    block_taluka: str = "Kalyanpur Block"
    gram_panchayat: str = "Kalyanpur GP"
    sub_center_id: Optional[str] = None
    assigned_facility_id: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    emergency_contact_relation: Optional[str] = None
    
    # Duplicate Override
    duplicate_override_reason: Optional[str] = None
    
    # 2. Household & Consent
    head_of_household_name: Optional[str] = None
    head_of_household_relation: Optional[str] = None
    family_id: Optional[str] = None
    household_category: str = "OTHER"
    ration_card_category: Optional[str] = None
    preferred_language: str = "mr-IN"
    literacy_assistance_needed: bool = False
    accessibility_needs: Optional[str] = None
    registration_consent_obtained: bool = True
    voice_consent_obtained: bool = False
    consent_method: str = "VERBAL"
    guardian_name: Optional[str] = None
    guardian_relation: Optional[str] = None
    
    # 3. Health Profile
    blood_group: Optional[str] = "UNKNOWN"
    allergies: List[str] = []
    chronic_conditions: List[str] = []
    current_medications: List[MedicationItemInput] = []
    disability_notes: Optional[str] = None
    previous_illnesses: Optional[str] = None
    previous_surgeries: Optional[str] = None
    tobacco_use: str = "NONE"
    alcohol_use: str = "NONE"
    programme_enrollments: List[str] = []
    health_notes: Optional[str] = None
    
    # 4. Current Health Concern
    create_current_case: bool = False
    reason_for_visit: Optional[str] = None
    chief_complaint: Optional[str] = None
    symptoms: List[str] = []
    duration: Optional[str] = None
    onset: Optional[str] = None
    severity: Optional[str] = "MODERATE"
    danger_signs: List[str] = []
    spoken_transcript: Optional[str] = None
    confirmed_summary: Optional[str] = None
    
    # 5. Vitals & Special Conditions
    vitals: Optional[VitalsInput] = None
    special_conditions: Optional[SpecialConditionsInput] = None
    
    # 6. Risk, Follow-up & Referral (Nested)
    referral: Optional[ReferralInput] = None
    follow_up: Optional[FollowUpInput] = None

    # Legacy flat referral fields (for backward compatibility)
    referral_required: Optional[bool] = None
    referral_facility_id: Optional[str] = None
    referral_urgency: Optional[str] = None
    referral_reason: Optional[str] = None

    # Legacy flat followup fields (for backward compatibility)
    followup_required: Optional[bool] = None
    followup_date: Optional[str] = None
    followup_purpose: Optional[str] = None
    followup_notes: Optional[str] = None
    
    # 7. Attachments metadata
    attachment_ids: List[str] = []
    accuracy_confirmed_by_asha: bool = True

class PatientRegistrationResponseData(BaseModel):
    citizen_id: str
    citizen_reference: str
    citizen_name: str
    case_id: Optional[str] = None
    case_reference: Optional[str] = None
    visit_id: Optional[str] = None
    referral_id: Optional[str] = None
    referral_reference: Optional[str] = None
    follow_up_id: Optional[str] = None
    follow_up_due_date: Optional[str] = None
    safety_result: Optional[Dict[str, Any]] = None
    schemes_evaluated: Optional[List[Dict[str, Any]]] = None
    next_route: str = "/asha/people"

# --- Voice Structured Intake Schemas ---
class StructuredVoiceIntakeRequest(BaseModel):
    audio_base64: Optional[str] = None
    audio_format: Optional[str] = "webm"
    raw_transcript: Optional[str] = None
    language: str = "mr-IN"
    consent_obtained: bool = True
    field_context: Optional[str] = "ALL"

class StructuredVoiceIntakeResponse(BaseModel):
    transcript: str
    language: str
    processing_provider: str
    confidence: float
    requires_human_confirmation: bool = True
    extracted_fields: Dict[str, Any]
    field_confidence: Dict[str, float] = {}
    unrecognized_text: Optional[str] = None
    warnings: List[str] = []


# --- Doctor Investigation Schemas ---
class InvestigationOrderCreateInput(BaseModel):
    citizen_id: str
    case_id: str
    consultation_id: Optional[str] = None
    referral_id: Optional[str] = None
    test_name: str
    test_code: Optional[str] = None
    category: str = "GENERAL"
    priority: str = "ROUTINE"
    clinical_reason: Optional[str] = None
    specimen_type: Optional[str] = None
    preparation_instructions: Optional[str] = None
    collection_location: Optional[str] = None
    due_at: Optional[datetime] = None
    expected_result_at: Optional[datetime] = None
    assign_asha_assistance: bool = False
    asha_instructions: Optional[str] = None
    idempotency_key: Optional[str] = None

class SampleCollectInput(BaseModel):
    sample_reference: Optional[str] = None
    specimen_type: Optional[str] = None
    collected_at: Optional[datetime] = None
    collection_notes: Optional[str] = None
    rejection_reason: Optional[str] = None
    recollection_required: bool = False

class ResultItemInput(BaseModel):
    parameter_name: str
    parameter_code: Optional[str] = None
    value: str
    unit: Optional[str] = None
    reference_low: Optional[str] = None
    reference_high: Optional[str] = None
    source_flag: str = "NORMAL"  # NORMAL, LOW, HIGH, CRITICAL
    remarks: Optional[str] = None

class ResultEntryInput(BaseModel):
    result_source: str = "PHC Manual/Demonstration Entry"
    laboratory_name: str = "PHC Kalyanpur Central Lab"
    resulted_at: Optional[datetime] = None
    report_attachment_id: Optional[str] = None
    critical_flag: bool = False
    items: List[ResultItemInput] = []

class CriticalAcknowledgeInput(BaseModel):
    notes: Optional[str] = None
    action: Optional[str] = "ACKNOWLEDGED"

class DoctorReviewInput(BaseModel):
    review_note: str
    outcome: str  # NO_CHANGE, REPEAT_TEST, UPDATE_CARE_PLAN, PHC_REVIEW, ASHA_FOLLOW_UP, REFER_HIGHER, EMERGENCY_ACTION
    update_care_plan: bool = False
    care_plan_notes: Optional[str] = None
    create_followup: bool = False
    followup_instructions: Optional[str] = None
    followup_due_days: int = 3
    create_referral: bool = False
    referral_reason: Optional[str] = None
    referral_facility: Optional[str] = None

class RecollectionRequestInput(BaseModel):
    reason: str

class InvestigationSummaryDTO(BaseModel):
    total_ordered_today: int = 0
    sample_pending: int = 0
    sample_collected: int = 0
    results_ready: int = 0
    urgent_critical_results: int = 0
    awaiting_doctor_review: int = 0
    reviewed_today: int = 0
    recollection_required: int = 0

class ResultItemDTO(BaseModel):
    id: str
    parameter_name: str
    parameter_code: Optional[str] = None
    value: str
    unit: Optional[str] = None
    reference_low: Optional[str] = None
    reference_high: Optional[str] = None
    source_flag: str = "NORMAL"
    remarks: Optional[str] = None

class InvestigationResultDTO(BaseModel):
    id: str
    result_source: str
    laboratory_name: str
    resulted_at: str
    entered_by_name: Optional[str] = None
    verification_status: str
    critical_flag: bool
    report_attachment_id: Optional[str] = None
    items: List[ResultItemDTO] = []

class InvestigationReviewDTO(BaseModel):
    id: str
    doctor_id: str
    doctor_name: Optional[str] = None
    review_note: str
    outcome: str
    reviewed_at: str
    critical_acknowledged_at: Optional[str] = None
    care_plan_updated: bool = False
    related_follow_up_id: Optional[str] = None
    related_higher_referral_id: Optional[str] = None

class InvestigationSampleDTO(BaseModel):
    id: str
    sample_reference: Optional[str] = None
    collected_by_name: Optional[str] = None
    collected_at: Optional[str] = None
    collection_status: str
    rejection_reason: Optional[str] = None
    recollection_required: bool = False

class RecollectionRequestInput(BaseModel):
    sample_id: Optional[str] = None
    reason_code: str = "INSUFFICIENT_SAMPLE"
    reason_note: str = "Recollection requested"
    reason: Optional[str] = None
    priority: Optional[str] = "HIGH"
    due_at: Optional[str] = None
    collection_location: Optional[str] = "Kalyanpur PHC"
    assign_asha_assistance: bool = False

class DoctorInvestigationItemDTO(BaseModel):
    id: str
    reference: str
    investigation_id: str
    investigation_order_id: Optional[str] = None
    investigation_reference: str
    citizen_id: str
    patient_id: Optional[str] = None
    citizen_name: str
    citizen_age: Optional[int] = 30
    citizen_gender: Optional[str] = "Female"
    village_name: Optional[str] = "Kalyanpur"
    clinical_context: Optional[str] = "General"
    case_id: str
    case_reference: str
    consultation_id: Optional[str] = None
    consultation_reference: Optional[str] = None
    referral_id: Optional[str] = None
    ordering_doctor_name: Optional[str] = None
    test_name: str
    test_code: Optional[str] = None
    category: str = "GENERAL"
    priority: str = "ROUTINE"
    status: str
    clinical_reason: Optional[str] = None
    specimen_type: Optional[str] = None
    preparation_instructions: Optional[str] = None
    collection_location: Optional[str] = None
    ordered_at: str
    due_at: Optional[str] = None
    expected_result_at: Optional[str] = None
    assigned_asha_name: Optional[str] = None
    sample_id: Optional[str] = None
    result_id: Optional[str] = None
    sample: Optional[InvestigationSampleDTO] = None
    result: Optional[InvestigationResultDTO] = None
    review: Optional[InvestigationReviewDTO] = None
    is_abnormal: bool = False
    result_preview: Optional[str] = None

class TestDetailDTO(BaseModel):
    name: str
    code: Optional[str] = None
    category: str = "GENERAL"

class PatientDetailDTO(BaseModel):
    citizen_id: str
    name: str
    age: Optional[int] = 30
    gender: Optional[str] = "Female"
    village: Optional[str] = "Kalyanpur"

class CaseDetailDTO(BaseModel):
    case_id: str
    reference: str

class ConsultationDetailDTO(BaseModel):
    consultation_id: Optional[str] = None
    reference: Optional[str] = None

class OrderDetailMetaDTO(BaseModel):
    clinical_reason: Optional[str] = "Not recorded"
    specimen_type: Optional[str] = "Not recorded"
    preparation_instructions: Optional[str] = "Not recorded"
    collection_location: Optional[str] = "Kalyanpur PHC"
    ordered_by: str = "Dr. Abhinav Sharma"
    ordered_at: str
    due_at: Optional[str] = None
    expected_result_at: Optional[str] = None

class InvestigationDetailDTO(BaseModel):
    investigation_id: str
    investigation_reference: str
    id: str
    reference: str
    status: str
    priority: str = "ROUTINE"
    test: TestDetailDTO
    patient: PatientDetailDTO
    case: CaseDetailDTO
    consultation: Optional[ConsultationDetailDTO] = None
    order: OrderDetailMetaDTO
    sample: Optional[InvestigationSampleDTO] = None
    result: Optional[InvestigationResultDTO] = None
    review: Optional[InvestigationReviewDTO] = None
    citizen_id: str
    case_id: str
    consultation_id: Optional[str] = None

class CitizenInvestigationInstructionDTO(BaseModel):
    investigation_id: str
    reference: str
    test_name: str
    purpose: str
    date_and_location: str
    preparation_instructions: str
    help_contact: str
    status: str
    result_summary: Optional[str] = None
    guidance: Optional[str] = None
    acknowledged_by_citizen: bool = False

class CitizenAcknowledgeInput(BaseModel):
    request_asha_help: bool = False
    notes: Optional[str] = None

class AshaInvestigationTaskDTO(BaseModel):
    task_id: str
    investigation_id: str
    investigation_reference: str
    citizen_id: str
    citizen_name: str
    village_name: str
    test_name: str
    facility_name: str
    due_date: str
    preparation_instructions: str
    attendance_requirement: str
    doctor_directive: str
    status: str
    contacted_citizen: bool = False
    attendance_confirmed: bool = False
    unable_to_attend_reason: Optional[str] = None

class AshaContactResultInput(BaseModel):
    contacted: bool = True
    instructions_explained: bool = True
    notes: Optional[str] = None

class AshaAttendanceInput(BaseModel):
    confirmed: bool
    unable_reason: Optional[str] = None

class AshaEscalateInput(BaseModel):
    reason: str
    recorded_vitals: Optional[Dict[str, Any]] = None


