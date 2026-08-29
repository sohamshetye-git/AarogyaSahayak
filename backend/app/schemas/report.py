from datetime import date, datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict


class DatePeriodFilter(BaseModel):
    date_from: str
    date_to: str
    timezone: str = "Asia/Kolkata"


class FacilityContext(BaseModel):
    facility_id: str
    facility_name: str
    doctor_name: Optional[str] = None


class OverviewMetrics(BaseModel):
    unique_patients_seen: int = 0
    new_referrals: int = 0
    active_urgent_referrals: int = 0
    consultations_completed: int = 0
    patients_waiting: int = 0
    results_awaiting_review: int = 0
    active_followups: int = 0
    escalations_pending: int = 0
    prescriptions_signed: int = 0
    higher_center_referrals: int = 0


class DoctorReportOverviewResponse(BaseModel):
    period: DatePeriodFilter
    facility: FacilityContext
    metrics: OverviewMetrics
    pending_work_count: int = 0
    recent_activity_count: int = 0
    data_generated_at: str

    model_config = ConfigDict(from_attributes=True)


class ReferralReportResponse(BaseModel):
    period: DatePeriodFilter
    facility: FacilityContext
    referrals_received: int = 0
    new_unacknowledged: int = 0
    active_urgent: int = 0
    acknowledged: int = 0
    transport_arranged: int = 0
    patients_arrived: int = 0
    consultations_started: int = 0
    consultations_completed: int = 0
    higher_center_referrals: int = 0
    cancelled_no_show: int = 0
    avg_acknowledgement_minutes: float = 0.0
    median_acknowledgement_minutes: float = 0.0
    longest_unacknowledged_hours: float = 0.0
    avg_referral_to_arrival_hours: float = 0.0
    avg_arrival_to_consultation_minutes: float = 0.0
    urgent_acknowledgement_rate_pct: float = 0.0
    no_arrival_rate_pct: float = 0.0
    by_day: List[Dict[str, Any]] = []

    model_config = ConfigDict(from_attributes=True)


class ConsultationReportResponse(BaseModel):
    period: DatePeriodFilter
    facility: FacilityContext
    ready_to_start: int = 0
    started: int = 0
    in_progress: int = 0
    saved_drafts: int = 0
    awaiting_investigations: int = 0
    followup_required: int = 0
    completed: int = 0
    higher_center_referral: int = 0
    cancelled_incomplete: int = 0
    consultations_per_day_avg: float = 0.0
    completion_rate_pct: float = 0.0
    avg_arrival_to_start_minutes: float = 0.0
    avg_consultation_duration_minutes: float = 0.0
    completed_with_followup: int = 0
    result_review_encounters: int = 0
    workload_by_category: Dict[str, int] = {}
    by_day: List[Dict[str, Any]] = []

    model_config = ConfigDict(from_attributes=True)


class PatientWorkloadReportResponse(BaseModel):
    period: DatePeriodFilter
    facility: FacilityContext
    unique_patients_seen: int = 0
    new_patients: int = 0
    returning_patients: int = 0
    active_cases: int = 0
    high_risk_active_care: int = 0
    maternal_patients: int = 0
    children: int = 0
    ncd_patients: int = 0
    elderly_patients: int = 0
    workload_by_village: Dict[str, int] = {}
    workload_by_category: Dict[str, int] = {}
    comparison_vs_previous_period_pct: float = 0.0

    model_config = ConfigDict(from_attributes=True)


class InvestigationReportResponse(BaseModel):
    period: DatePeriodFilter
    facility: FacilityContext
    ordered: int = 0
    sample_pending: int = 0
    sample_collected: int = 0
    in_process: int = 0
    results_available: int = 0
    results_awaiting_doctor_review: int = 0
    critical_results: int = 0
    critical_results_acknowledged: int = 0
    reviewed: int = 0
    recollection_required: int = 0
    cancelled: int = 0
    avg_order_to_collection_hours: float = 0.0
    avg_collection_to_result_hours: float = 0.0
    avg_result_to_review_hours: float = 0.0
    recollection_rate_pct: float = 0.0
    backlog_count: int = 0
    by_type: Dict[str, int] = {}

    model_config = ConfigDict(from_attributes=True)


class PrescriptionReportResponse(BaseModel):
    period: DatePeriodFilter
    facility: FacilityContext
    drafts: int = 0
    awaiting_signature: int = 0
    signed: int = 0
    active: int = 0
    ending_soon: int = 0
    completed: int = 0
    amended: int = 0
    partially_stopped: int = 0
    stopped: int = 0
    adherence_followups_assigned: int = 0
    signed_with_allergy_review: int = 0
    warnings_acknowledged: int = 0
    amendments_count: int = 0
    stopped_medicines_count: int = 0
    citizen_acknowledgements_count: int = 0
    adherence_completion_rate_pct: float = 0.0

    model_config = ConfigDict(from_attributes=True)


class AshaFollowupReportResponse(BaseModel):
    period: DatePeriodFilter
    facility: FacilityContext
    assigned: int = 0
    pending: int = 0
    in_progress: int = 0
    due_today: int = 0
    overdue: int = 0
    completed_by_asha: int = 0
    result_ready_for_doctor: int = 0
    reviewed: int = 0
    escalated: int = 0
    resolved: int = 0
    completion_rate_pct: float = 0.0
    overdue_rate_pct: float = 0.0
    median_completion_hours: float = 0.0
    escalation_rate_pct: float = 0.0
    avg_doctor_review_hours: float = 0.0
    workload_by_asha: Dict[str, int] = {}

    model_config = ConfigDict(from_attributes=True)


class MaternalReportResponse(BaseModel):
    period: DatePeriodFilter
    facility: FacilityContext
    active_pregnancies: int = 0
    anc_registered: int = 0
    high_priority_maternal_cases: int = 0
    pregnancy_warning_sign_cases: int = 0
    elevated_bp_warning_events: int = 0
    urgent_phc_referrals: int = 0
    maternal_consultations: int = 0
    maternal_followups: int = 0
    overdue_maternal_followups: int = 0
    postnatal_followups: int = 0
    higher_center_referrals: int = 0

    model_config = ConfigDict(from_attributes=True)


class ChildHealthReportResponse(BaseModel):
    period: DatePeriodFilter
    facility: FacilityContext
    registered_children: int = 0
    under_five_active_cases: int = 0
    fever_dehydration_warnings: int = 0
    high_priority_referrals: int = 0
    nutrition_followups: int = 0
    immunization_info_missing: int = 0
    completed_consultations: int = 0
    pending_child_followups: int = 0

    model_config = ConfigDict(from_attributes=True)


class NcdReportResponse(BaseModel):
    period: DatePeriodFilter
    facility: FacilityContext
    hypertension_monitoring_cases: int = 0
    diabetes_monitoring_cases: int = 0
    repeat_bp_tasks: int = 0
    repeat_glucose_tasks: int = 0
    medication_adherence_followups: int = 0
    overdue_ncd_tasks: int = 0
    escalated_ncd_cases: int = 0
    completed_ncd_reviews: int = 0

    model_config = ConfigDict(from_attributes=True)


class SafetyReportResponse(BaseModel):
    period: DatePeriodFilter
    facility: FacilityContext
    deterministic_safety_warnings: int = 0
    urgent_cases_acknowledged: int = 0
    urgent_cases_unacknowledged: int = 0
    asha_escalations: int = 0
    critical_investigation_alerts: int = 0
    critical_alerts_acknowledged: int = 0
    higher_center_referrals: int = 0
    unresolved_escalations: int = 0
    avg_doctor_acknowledgement_minutes: float = 0.0
    by_category: Dict[str, int] = {}

    model_config = ConfigDict(from_attributes=True)


class FunnelStageItem(BaseModel):
    stage_key: str
    stage_label: str
    count: int
    conversion_from_prior_pct: float
    conversion_from_start_pct: float
    median_time_from_prior_minutes: Optional[float] = None
    target_route: str


class CareWorkflowFunnelResponse(BaseModel):
    period: DatePeriodFilter
    facility: FacilityContext
    stages: List[FunnelStageItem]

    model_config = ConfigDict(from_attributes=True)


class PendingWorkItem(BaseModel):
    id: str
    task_type: str
    patient_name: str
    citizen_id: str
    priority: str
    waiting_time_display: str
    source_entity_type: str
    source_entity_id: str
    action_label: str
    target_route: str


class RecentActivityItem(BaseModel):
    id: str
    event_title: str
    description: str
    actor_name: str
    actor_role: str
    timestamp: str
    target_route: str
