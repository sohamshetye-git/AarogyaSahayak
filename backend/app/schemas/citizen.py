from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class LanguageUpdateRequestDTO(BaseModel):
    preferred_language: str = Field(..., description="Language code e.g. mr-IN, hi-IN, en-IN")

class BeneficiaryItemDTO(BaseModel):
    beneficiary_id: str
    citizen_id: Optional[str] = None
    household_member_id: Optional[str] = None
    profile_id: Optional[str] = None
    display_name: str
    relationship: str  # "SELF" | "CHILD" | "SPOUSE" | "PARENT" | "OTHER"
    age: Optional[int] = None
    gender: Optional[str] = None
    is_registered_patient: bool = True
    existing_case_id: Optional[str] = None

class BeneficiaryListResponseDTO(BaseModel):
    items: List[BeneficiaryItemDTO] = Field(default_factory=list)

class HouseholdMemberDTO(BaseModel):
    id: str
    citizen_id: str
    full_name: str
    relationship_type: str
    age: Optional[int] = None
    sex: Optional[str] = None
    phone: Optional[str] = None
    abha_reference: Optional[str] = None
    is_pregnant: bool = False
    gestational_weeks: Optional[int] = None
    blood_group: Optional[str] = None
    chronic_conditions: List[str] = []
    is_active: bool = True
    created_at: datetime

class HouseholdMemberCreateRequest(BaseModel):
    full_name: str
    relationship_type: str # SELF, MOTHER, FATHER, SPOUSE, CHILD, ELDER, OTHER
    age: Optional[int] = None
    sex: Optional[str] = None
    phone: Optional[str] = None
    abha_reference: Optional[str] = None
    is_pregnant: bool = False
    gestational_weeks: Optional[int] = None
    blood_group: Optional[str] = None
    chronic_conditions: List[str] = []
    health_notes: Optional[str] = None
    consent_obtained: bool = True

class HouseholdMemberUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    relationship_type: Optional[str] = None
    age: Optional[int] = None
    sex: Optional[str] = None
    phone: Optional[str] = None
    abha_reference: Optional[str] = None
    is_pregnant: Optional[bool] = None
    gestational_weeks: Optional[int] = None
    blood_group: Optional[str] = None
    chronic_conditions: Optional[List[str]] = None
    health_notes: Optional[str] = None
    is_active: Optional[bool] = None

class CitizenProfileDTO(BaseModel):
    id: str
    user_id: Optional[str] = None
    display_name: str
    legal_name: Optional[str] = None
    preferred_name: Optional[str] = None
    date_of_birth: Optional[str] = None
    age: Optional[int] = None
    sex: Optional[str] = None
    phone: Optional[str] = None
    alternate_phone: Optional[str] = None
    is_phone_verified: bool = True
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    emergency_contact_relation: Optional[str] = None
    address: Optional[str] = None
    current_care_location: Optional[str] = None
    village_name: str = "Kalyanpur"
    gram_panchayat: Optional[str] = "Kalyanpur GP"
    block_taluka: str = "Kalyanpur Block"
    district: str = "District 04"
    state: str = "Maharashtra"
    pincode: Optional[str] = "411001"
    preferred_language: str = "mr-IN"
    abha_reference: Optional[str] = None
    abha_masked: Optional[str] = None
    abha_status: str = "NOT_LINKED"
    abha_status_label: str = "Not Linked"
    blood_group: Optional[str] = None
    allergies: List[str] = []
    chronic_conditions: List[str] = []
    is_pregnant: bool = False
    gestational_weeks: Optional[int] = None
    updated_at: Optional[datetime] = None
    household_count: int = 1

class CitizenProfileUpdateRequest(BaseModel):
    display_name: Optional[str] = None
    legal_name: Optional[str] = None
    preferred_name: Optional[str] = None
    date_of_birth: Optional[str] = None
    age: Optional[int] = None
    sex: Optional[str] = None
    phone: Optional[str] = None
    alternate_phone: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    emergency_contact_relation: Optional[str] = None
    address: Optional[str] = None
    current_care_location: Optional[str] = None
    village_name: Optional[str] = None
    gram_panchayat: Optional[str] = None
    block_taluka: Optional[str] = None
    district: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    preferred_language: Optional[str] = None
    blood_group: Optional[str] = None
    allergies: Optional[List[str]] = None
    chronic_conditions: Optional[List[str]] = None
    is_pregnant: Optional[bool] = None
    gestational_weeks: Optional[int] = None

class CareTeamMemberDTO(BaseModel):
    id: str
    role: str # ASHA_WORKER, PHC_DOCTOR, PHC_FACILITY
    name: str
    designation: str
    facility_name: Optional[str] = None
    facility_id: Optional[str] = None
    phone: Optional[str] = None
    action_type: str # CALL, MESSAGE, VISIT
    is_verified: bool = True
    operating_hours: Optional[str] = None
    address: Optional[str] = None

class CareTeamResponseDTO(BaseModel):
    assigned_asha: Optional[CareTeamMemberDTO] = None
    assigned_phc: Optional[CareTeamMemberDTO] = None
    assigned_doctor: Optional[CareTeamMemberDTO] = None
    emergency_contact_108: Dict[str, Any]

class ConsentRecordDTO(BaseModel):
    id: str
    recipient_role: str
    recipient_name: Optional[str] = None
    purpose: str
    purpose_label: str
    scope: Dict[str, Any]
    policy_version: str = "v1.0"
    consent_text: Optional[str] = None
    consented_at: datetime
    expires_at: Optional[datetime] = None
    is_revoked: bool = False
    revoked_at: Optional[datetime] = None
    can_revoke: bool = True

class ConsentRevokeRequest(BaseModel):
    consent_id: str
    reason: Optional[str] = None

class AbhaLinkStatusDTO(BaseModel):
    status: str # NOT_LINKED, LINK_PENDING, LINKED_UNVERIFIED, VERIFIED_SANDBOX, VERIFIED_LIVE
    status_label: str
    status_badge_color: str
    abha_number_masked: Optional[str] = None
    abha_address: Optional[str] = None
    is_live_abdm: bool = False
    verification_mode: str
    disclaimer: str


class StartChatSessionRequest(BaseModel):
    person_affected_id: Optional[str] = None
    preferred_language: str = "mr-IN"
    channel: str = "VOICE" # VOICE, TEXT, MIXED
    device_id: Optional[str] = None
    offline_created: bool = False

class ChatMessageCreateRequest(BaseModel):
    input_type: str = "TEXT" # VOICE, TEXT
    original_text: str
    language: str = "mr-IN"
    temporary_audio_reference: Optional[str] = None
    in_reply_to_question_id: Optional[str] = None
    idempotency_key: Optional[str] = None

class ChatVoiceTranscribeRequest(BaseModel):
    audio_base64: Optional[str] = None
    audio_format: Optional[str] = "webm"
    preferred_language: Optional[str] = "mr-IN"
    duration_seconds: Optional[float] = None

class TranscriptConfirmationRequest(BaseModel):
    confirmed_text: str
    action: str = "CONFIRM" # CONFIRM, EDIT, RETRY
    in_reply_to_question_id: Optional[str] = None
    idempotency_key: Optional[str] = None

class UnderstandingConfirmationRequest(BaseModel):
    confirmed_understanding: Dict[str, Any]
    action: str = "CONFIRM" # CONFIRM, EDIT

class CitizenNeedCreateRequest(BaseModel):
    session_id: Optional[str] = None
    person_affected_id: Optional[str] = None
    primary_intent: str
    secondary_intents: List[str] = []
    requested_service: Optional[str] = None
    detected_language: str = "mr-IN"
    confirmed_summary: str
    location: Optional[Dict[str, Any]] = None
    special_context: str = "GENERAL"
    urgency: str = "ROUTINE"

class HandoffPreviewRequest(BaseModel):
    session_id: Optional[str] = None
    need_id: Optional[str] = None
    beneficiary_id: Optional[str] = None
    request_type: str = "DOCTOR_CONSULTATION" # DOCTOR_CONSULTATION | ASHA_ASSISTANCE
    requested_channel: Optional[str] = "CALLBACK"
    chief_concern: Optional[str] = None
    symptoms: Optional[List[str]] = None

class DoctorRequestCreateDTO(BaseModel):
    beneficiary_id: Optional[str] = None
    chat_session_id: Optional[str] = None
    citizen_need_id: Optional[str] = None
    need_id: Optional[str] = None
    case_id: Optional[str] = None
    channel: str = "CALLBACK" # AUDIO, VIDEO, CHAT, CALLBACK, HOME_VISIT
    handoff_packet: Dict[str, Any] = Field(default_factory=dict)
    consent_id: Optional[str] = None
    sharing_scope: Dict[str, bool] = Field(default_factory=dict)
    chief_complaint: Optional[str] = None
    symptoms: List[str] = Field(default_factory=list)
    preferred_language: str = "mr-IN"
    request_type: str = "TELECONSULTATION" # TELECONSULTATION, CALLBACK
    idempotency_key: Optional[str] = None

class AshaRequestCreateDTO(BaseModel):
    beneficiary_id: Optional[str] = None
    chat_session_id: Optional[str] = None
    citizen_need_id: Optional[str] = None
    need_id: Optional[str] = None
    case_id: Optional[str] = None
    assistance_type: str = "HOME_VISIT" # HOME_VISIT | PHONE_SUPPORT | FACILITY_HELP | SCHEME_HELP
    preferred_date: Optional[str] = None
    preferred_time_window: str = "ANY" # MORNING | AFTERNOON | EVENING | ANY
    location: Dict[str, Any] = Field(default_factory=dict)
    landmark: Optional[str] = None
    mobility_or_accessibility_note: Optional[str] = None
    handoff_packet: Dict[str, Any] = Field(default_factory=dict)
    consent_id: Optional[str] = None
    sharing_scope: Dict[str, bool] = Field(default_factory=dict)
    reason: Optional[str] = None
    urgency: str = "ROUTINE"
    idempotency_key: Optional[str] = None

class ServiceRequestUpdateDTO(BaseModel):
    new_information: str
    updated_symptoms: List[str] = Field(default_factory=list)
    updated_vitals: Dict[str, Any] = Field(default_factory=dict)
    share_with_active_request: bool = True

class ServiceRequestCancelDTO(BaseModel):
    reason: str = "Resolved or citizen cancelled"

class SchemeScreeningRequest(BaseModel):
    person_affected_id: Optional[str] = None
    is_pregnant: Optional[bool] = None
    gestational_weeks: Optional[int] = None
    household_category: Optional[str] = None
    ration_card_category: Optional[str] = None
    age: Optional[int] = None
    sex: Optional[str] = None
    income_annual: Optional[float] = None
    disability_status: Optional[bool] = None

class FacilitySearchRequest(BaseModel):
    facility_type: Optional[str] = None
    service_type: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    max_distance_km: float = 20.0

class CitizenHomeSummaryDTO(BaseModel):
    citizen_name: str
    preferred_language: str
    unread_notifications_count: int
    active_case: Optional[Dict[str, Any]] = None
    responsible_person: Optional[Dict[str, Any]] = None
    quick_actions: List[Dict[str, Any]]
    recent_prescriptions: List[Dict[str, Any]]
    upcoming_appointments: List[Dict[str, Any]]

class CitizenTimelineEventDTO(BaseModel):
    id: str
    event_type: str
    title: str
    description: str
    status_label: str
    actor_role: str
    timestamp: datetime
    is_citizen_safe: bool = True

class PatientResolutionRequestDTO(BaseModel):
    beneficiary_id: Optional[str] = None
    candidate_name: Optional[str] = None
    phone: Optional[str] = None
    abha_reference: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    village_name: Optional[str] = None
    confirm_register_new_duplicate: bool = False

class PatientResolutionResponseDTO(BaseModel):
    resolution_type: str # SELF, HOUSEHOLD_MEMBER, POTENTIAL_DUPLICATE, NEW_PERSON
    resolved_citizen_id: Optional[str] = None
    resolved_household_member_id: Optional[str] = None
    display_name: Optional[str] = None
    relationship_type: Optional[str] = None
    is_registered: bool = False
    requires_duplicate_confirmation: bool = False
    message: Optional[str] = None
    potential_matches: List[Dict[str, Any]] = Field(default_factory=list)
    actions: List[str] = Field(default_factory=list)

class ServiceRequestStatusPatchDTO(BaseModel):
    action: str # ACKNOWLEDGE, CALL_CITIZEN, MARK_UNREACHABLE, REQUEST_INFO, SCHEDULE_VISIT, START_VISIT, ESCALATE_PHC, COMPLETE, ACCEPT, REVIEW, DECLINE, START_CONSULTATION, RECOMMEND_IN_PERSON, ESCALATE_EMERGENCY
    status: Optional[str] = None
    reason: Optional[str] = None
    notes: Optional[str] = None
    scheduled_date: Optional[str] = None
    scheduled_time_slot: Optional[str] = None
    provisional_diagnosis: Optional[str] = None
    patient_guidance: Optional[str] = None
    prescriptions: Optional[List[Dict[str, Any]]] = None
    investigation_orders: Optional[List[Dict[str, Any]]] = None
    follow_up_plan: Optional[Dict[str, Any]] = None


# -------------------------------------------------------------
# Citizen Authentication & Guest Access Schemas
# -------------------------------------------------------------

class CitizenOtpRequestDTO(BaseModel):
    phone: str = Field(..., description="10-digit Indian mobile number")

class CitizenOtpVerifyDTO(BaseModel):
    phone: str = Field(..., description="10-digit Indian mobile number")
    otp: str = Field(..., description="6-digit numeric OTP code")
    otp_request_id: Optional[str] = Field(None, description="Optional exact OTP request ID returned during request")
    purpose: Optional[str] = Field("LOGIN", description="Purpose of OTP challenge")
    device_id: Optional[str] = None
    idempotency_key: Optional[str] = None

class CitizenRefreshTokenDTO(BaseModel):
    refresh_token: Optional[str] = None

class CitizenOnboardingRequestDTO(BaseModel):
    phone: str
    full_name: str
    date_of_birth: Optional[str] = None
    age: Optional[int] = None
    gender: str = "OTHER"
    village: Optional[str] = "Kalyanpur"
    district: Optional[str] = "District 04"
    pincode: Optional[str] = None
    preferred_language: str = "mr-IN"
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    emergency_contact_relation: Optional[str] = None
    abha_reference: Optional[str] = None
    consent_obtained: bool = True
    confirm_potential_duplicate: bool = False
    idempotency_key: Optional[str] = None

class GuestSessionCreateDTO(BaseModel):
    locale: Optional[str] = "mr-IN"
    device_hash: Optional[str] = None

class GuestSessionUpdateDTO(BaseModel):
    context_data: Optional[Dict[str, Any]] = None
    intended_action: Optional[Dict[str, Any]] = None

class GuestSessionMigrateDTO(BaseModel):
    idempotency_key: Optional[str] = None


