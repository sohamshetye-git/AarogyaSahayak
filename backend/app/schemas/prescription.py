from datetime import datetime
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field


class PrescriptionItemCreate(BaseModel):
    id: Optional[str] = None
    medicine_catalog_id: Optional[str] = None
    generic_name_snapshot: str
    brand_name_snapshot: Optional[str] = None
    formulation: str = "Tablet"
    strength: Optional[str] = "500 mg"
    dose: str = "1"
    dose_unit: str = "tablet"
    route: str = "Oral"
    frequency: str = "Twice daily"
    timing: str = "After food"
    duration_value: int = 5
    duration_unit: str = "days"
    quantity: int = 10
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    instructions: Optional[str] = None
    indication: Optional[str] = None
    as_needed: bool = False
    max_frequency: Optional[str] = None
    adherence_monitoring_required: bool = False


class PrescriptionItemResponse(BaseModel):
    id: str
    prescription_id: str
    medicine_catalog_id: Optional[str] = None
    generic_name_snapshot: str = "Unspecified Medicine"
    brand_name_snapshot: Optional[str] = None
    formulation: str
    strength: Optional[str] = None
    dose: str
    dose_unit: str
    route: str
    frequency: str
    timing: str
    duration_value: int
    duration_unit: str
    quantity: int
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    instructions: Optional[str] = None
    indication: Optional[str] = None
    as_needed: bool
    max_frequency: Optional[str] = None
    adherence_monitoring_required: bool
    status: str
    stopped_at: Optional[datetime] = None
    stopped_by_doctor_id: Optional[str] = None
    stop_reason: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PrescriptionCreateDraft(BaseModel):
    citizen_id: str
    case_id: str
    consultation_id: str
    referral_id: Optional[str] = None
    facility_id: Optional[str] = None
    clinical_context: Optional[str] = None
    patient_language: str = "en-IN"
    items: List[PrescriptionItemCreate] = []


class PrescriptionUpdateDraft(BaseModel):
    clinical_context: Optional[str] = None
    patient_language: Optional[str] = None
    items: List[PrescriptionItemCreate] = []


class PrescriptionSafetyCheckResponse(BaseModel):
    id: str
    prescription_id: str
    check_type: str
    severity: str
    message: str
    source_rule: Optional[str] = None
    requires_confirmation: bool
    confirmed_by_doctor: bool
    confirmed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PrescriptionSignRequest(BaseModel):
    confirmed_warnings: List[str] = []
    instructions_reviewed: bool = True


class PrescriptionAmendRequest(BaseModel):
    reason_code: str  # DOSE_ADJUSTED, MEDICINE_REPLACED, DURATION_CHANGED, REPORTED_DIFFICULTY, INVESTIGATION_REVIEW, CLINICAL_REASSESSMENT, AVAILABILITY_ISSUE, OTHER
    reason_note: Optional[str] = None
    items: List[PrescriptionItemCreate] = []


class StopMedicineRequest(BaseModel):
    stop_date: Optional[datetime] = None
    stop_reason: str
    doctor_note: Optional[str] = None
    patient_guidance: Optional[str] = None
    asha_notification_required: bool = True


class PrescriptionCancelRequest(BaseModel):
    cancellation_reason: str


class PrescriptionFollowUpAssignRequest(BaseModel):
    asha_id: Optional[str] = None
    due_in_days: int = 3
    instructions: str
    measurements_to_repeat: Optional[List[str]] = None


class MedicineCatalogResponse(BaseModel):
    id: str
    generic_name: str
    brand_name: Optional[str] = None
    formulation: str
    strength_options: Optional[List[str]] = None
    route_options: Optional[List[str]] = None
    medicine_category: str
    phc_availability_status: str
    active: bool

    class Config:
        from_attributes = True


class PrescriptionDetailResponse(BaseModel):
    id: str
    reference: str
    citizen_id: str
    case_id: str
    referral_id: Optional[str] = None
    consultation_id: str
    prescriber_doctor_id: str
    facility_id: Optional[str] = None
    status: str
    version_number: int
    supersedes_prescription_id: Optional[str] = None
    clinical_context: Optional[str] = None
    patient_language: str
    signed_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    cancellation_reason: Optional[str] = None
    idempotency_key: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    # Linked details
    patient_name: Optional[str] = None
    patient_age: Optional[int] = None
    patient_gender: Optional[str] = None
    patient_village: Optional[str] = None
    patient_category: Optional[str] = None
    case_reference: Optional[str] = None
    consultation_reference: Optional[str] = None
    prescriber_doctor_name: Optional[str] = None
    
    items: List[PrescriptionItemResponse] = []
    safety_checks: List[PrescriptionSafetyCheckResponse] = []

    class Config:
        from_attributes = True


class PrescriptionSummaryResponse(BaseModel):
    drafts_count: int = 0
    awaiting_signature_count: int = 0
    signed_today_count: int = 0
    active_count: int = 0
    ending_soon_count: int = 0
    adherence_followup_required_count: int = 0
    amended_count: int = 0
    stopped_cancelled_count: int = 0
    phc_name: str = "Kalyanpur Primary Health Centre"
    last_synchronized_at: datetime = Field(default_factory=datetime.utcnow)


class CitizenPrescriptionResponse(BaseModel):
    id: str
    reference: str
    status: str
    prescriber_doctor_name: str
    facility_name: str
    signed_at: Optional[datetime] = None
    patient_instructions_en: str
    patient_instructions_mr: str
    patient_instructions_hi: str
    items: List[PrescriptionItemResponse] = []
    next_review_date: Optional[datetime] = None
    acknowledged: bool = False


class CitizenAcknowledgeRequest(BaseModel):
    instructions_understood: bool = True
    language: str = "mr-IN"


class CitizenRequestHelpRequest(BaseModel):
    help_note: str


class AshaAdherenceOutcomeRequest(BaseModel):
    patient_contacted: bool = True
    medicine_obtained: bool = True
    adherence_status: str  # YES, PARTIAL, NO
    missed_doses: int = 0
    difficulty_reported: Optional[str] = None
    side_effect_concern: Optional[str] = None
    vitals_recorded: Optional[Dict[str, Any]] = None
    guidance_delivered: str
    notes: Optional[str] = None


class AshaAdherenceEscalateRequest(BaseModel):
    reason: str
    urgency: str = "HIGH"


class AdminPrescriptionAnalyticsResponse(BaseModel):
    prescriptions_signed_total: int
    active_prescriptions_count: int
    amendment_rate_percentage: float
    stopped_item_count: int
    adherence_followup_completion_rate: float
    escalation_rate_percentage: float
    category_breakdown: Dict[str, int]
    phc_prescribing_workload: List[Dict[str, Any]]
