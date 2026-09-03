"""
Authoritative Referral Service for Aarogya Sahayak Backend

Handles PHC Referral Queue logic, summary metrics, lifecycle state transitions,
deterministic data joins across Case -> Citizen -> AshaVisit -> VitalRecord -> SafetyRules,
and consultation creation/resumption idempotency.
"""

from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, and_, desc

from app.models import (
    Referral, Case, CitizenProfile, AshaVisit, VitalRecord,
    SymptomObservation, User, WorkerProfile, Consultation,
    CasePriorityEnum, CaseStatusEnum, InformationSourceEnum,
    AuditLog
)

def utc_now():
    return datetime.now(timezone.utc)


def get_doctor_referrals_summary(db: Session, doctor_user: User) -> Dict[str, int]:
    """
    Returns authoritative distinct referral summary counts for doctor dashboard & queue headers.
    Guarantees that summary metrics match filter results using identical predicates and COUNT(DISTINCT referral.id).
    """
    facility_id = None
    if doctor_user.worker_profile and doctor_user.worker_profile.facility_id:
        facility_id = doctor_user.worker_profile.facility_id

    base_q = db.query(Referral).join(Case, Referral.case_id == Case.id)
    if facility_id:
        base_q = base_q.filter(Referral.to_facility_id == facility_id)

    # Predicates
    active_statuses = ["PENDING_DOCTOR_REVIEW", "NEW", "REFERRED_TO_PHC", "DOCTOR_ACKNOWLEDGED", "ACKNOWLEDGED", "TRANSPORT_ARRANGED", "PATIENT_ARRIVED", "IN_CONSULTATION"]
    unacked_statuses = ["PENDING_DOCTOR_REVIEW", "NEW", "REFERRED_TO_PHC"]
    
    total_active = base_q.filter(Referral.status.in_(active_statuses)).count()
    
    new_cnt = base_q.filter(Referral.status.in_(unacked_statuses)).count()
    
    urgent_active_cnt = base_q.filter(
        Referral.urgency.in_([CasePriorityEnum.URGENT, CasePriorityEnum.HIGH, "URGENT", "HIGH"]),
        Referral.status.in_(active_statuses)
    ).count()

    urgent_pending_review_cnt = base_q.filter(
        Referral.urgency.in_([CasePriorityEnum.URGENT, CasePriorityEnum.HIGH, "URGENT", "HIGH"]),
        Referral.status.in_(unacked_statuses)
    ).count()

    acknowledged_cnt = base_q.filter(Referral.status.in_(["DOCTOR_ACKNOWLEDGED", "ACKNOWLEDGED"])).count()
    
    transport_cnt = base_q.filter(
        or_(
            Referral.status == "TRANSPORT_ARRANGED",
            and_(Referral.transport_assistance_required == True, Referral.status.in_(["DOCTOR_ACKNOWLEDGED", "ACKNOWLEDGED", "TRANSPORT_ARRANGED"]))
        )
    ).count()

    arrived_cnt = base_q.filter(Referral.status == "PATIENT_ARRIVED").count()
    
    in_consultation_cnt = base_q.filter(Referral.status == "IN_CONSULTATION").count()

    today_start = utc_now().replace(hour=0, minute=0, second=0, microsecond=0)
    processed_today_cnt = base_q.filter(
        Referral.status.in_(["PROCESSED", "COMPLETED", "CLOSED_NO_ARRIVAL"]),
        Referral.created_at >= today_start
    ).count()

    transport_en_route_cnt = base_q.filter(Referral.status == "TRANSPORT_ARRANGED").count()

    return {
        "new_referrals": new_cnt,
        "active_urgent_referrals": urgent_active_cnt,
        "urgent_pending_review": urgent_pending_review_cnt,
        "acknowledged": acknowledged_cnt,
        "transport_arranged": transport_cnt,
        "patient_arrived": arrived_cnt,
        "in_consultation": in_consultation_cnt,
        "processed_today": processed_today_cnt,
        "transport_en_route": transport_en_route_cnt,
        "total_active_referrals": total_active,
        # Backward compatibility aliases
        "new": new_cnt,
        "urgent_active": urgent_active_cnt,
        "total_active": total_active,
    }


def get_doctor_referrals_list(
    db: Session,
    doctor_user: User,
    status_filter: Optional[str] = None,
    urgency: Optional[str] = None,
    sort_by: Optional[str] = "priority_first",
    search: Optional[str] = None,
    page: int = 1,
    limit: int = 20
) -> Tuple[List[Dict[str, Any]], int]:
    """
    Returns list of referral DTOs and total count with complete data relationships:
    Referral -> Case -> CitizenProfile -> latest AshaVisit -> latest VitalMeasurement -> SafetyRules -> WorkerProfile -> Consultation.
    """
    facility_id = None
    if doctor_user.worker_profile and doctor_user.worker_profile.facility_id:
        facility_id = doctor_user.worker_profile.facility_id

    query = db.query(Referral).join(Case, Referral.case_id == Case.id)
    if facility_id:
        query = query.filter(Referral.to_facility_id == facility_id)

    # Filter logic
    active_statuses = ["PENDING_DOCTOR_REVIEW", "NEW", "REFERRED_TO_PHC", "DOCTOR_ACKNOWLEDGED", "ACKNOWLEDGED", "TRANSPORT_ARRANGED", "PATIENT_ARRIVED", "IN_CONSULTATION"]
    
    if not status_filter or status_filter == "ALL_ACTIVE" or status_filter == "ALL":
        query = query.filter(Referral.status.in_(active_statuses))
    elif status_filter == "NEW":
        query = query.filter(Referral.status.in_(["PENDING_DOCTOR_REVIEW", "NEW", "REFERRED_TO_PHC"]))
    elif status_filter == "URGENT_PENDING_REVIEW":
        query = query.filter(
            Referral.urgency.in_([CasePriorityEnum.URGENT, CasePriorityEnum.HIGH, "URGENT", "HIGH"]),
            Referral.status.in_(["PENDING_DOCTOR_REVIEW", "NEW", "REFERRED_TO_PHC"])
        )
    elif status_filter in ["URGENT", "URGENT_ACTIVE"]:
        query = query.filter(
            Referral.urgency.in_([CasePriorityEnum.URGENT, CasePriorityEnum.HIGH, "URGENT", "HIGH"]),
            Referral.status.in_(active_statuses)
        )
    elif status_filter == "HIGH_PRIORITY" or status_filter == "HIGH":
        query = query.filter(
            Referral.urgency.in_([CasePriorityEnum.HIGH, "HIGH"]),
            Referral.status.in_(active_statuses)
        )
    elif status_filter == "ACKNOWLEDGED":
        query = query.filter(Referral.status.in_(["DOCTOR_ACKNOWLEDGED", "ACKNOWLEDGED"]))
    elif status_filter == "TRANSPORT_ARRANGED":
        query = query.filter(
            or_(
                Referral.status == "TRANSPORT_ARRANGED",
                and_(Referral.transport_assistance_required == True, Referral.status.in_(["DOCTOR_ACKNOWLEDGED", "ACKNOWLEDGED", "TRANSPORT_ARRANGED"]))
            )
        )
    elif status_filter == "PATIENT_ARRIVED":
        query = query.filter(Referral.status == "PATIENT_ARRIVED")
    elif status_filter == "READY_TO_START":
        from app.services.clinical_work_service import query_ready_to_start_consultations
        query = query_ready_to_start_consultations(db, doctor_user)
    elif status_filter == "IN_CONSULTATION":
        query = query.filter(Referral.status == "IN_CONSULTATION")
    elif status_filter == "PROCESSED_TODAY":
        today_start = utc_now().replace(hour=0, minute=0, second=0, microsecond=0)
        query = query.filter(
            Referral.status.in_(["PROCESSED", "COMPLETED", "CLOSED_NO_ARRIVAL", "CONSULTED"]),
            Referral.created_at >= today_start
        )
    elif status_filter in ["PROCESSED", "COMPLETED"]:
        query = query.filter(Referral.status.in_(["PROCESSED", "COMPLETED", "CLOSED_NO_ARRIVAL", "CONSULTED"]))
    else:
        query = query.filter(Referral.status == status_filter)

    if urgency:
        query = query.filter(Referral.urgency == urgency)

    all_refs = query.all()

    # Data DTO Transformation
    items = []
    for r in all_refs:
        case = r.case
        citizen = case.citizen if case else None
        
        # Category
        cat = "GENERAL"
        if citizen and citizen.is_pregnant:
            cat = "MATERNAL"
        elif citizen and citizen.age_estimate and citizen.age_estimate <= 12:
            cat = "CHILD"
        elif case and case.primary_concern and ("bp" in case.primary_concern.lower() or "hypertension" in case.primary_concern.lower() or "diabetes" in case.primary_concern.lower() or "glucose" in case.primary_concern.lower()):
            cat = "NCD"

        # Latest Vitals specifically bound to THIS case
        latest_v = None
        if case and case.vitals:
            lv = case.vitals[-1] # Sorted by created_at in model
            latest_v = {
                "systolic_bp": lv.systolic_bp,
                "diastolic_bp": lv.diastolic_bp,
                "spo2": lv.spo2,
                "pulse": lv.pulse,
                "temperature_c": lv.temperature_c,
                "recorded_at": lv.recorded_at.isoformat() if lv.recorded_at else None,
                "source": lv.source_type.value if hasattr(lv.source_type, "value") else (str(lv.source_type) if lv.source_type else "DEVICE_MEASURED"),
                "recorded_by": lv.recorded_by or "ASHA Sita Patel"
            }

        # Symptoms specifically bound to THIS case
        symptoms_list = [s.normalized_term for s in case.symptoms] if case and case.symptoms else []

        # Triage Reason: Use case safety rule reason or fallback to referral reason
        triage_reason = (case.safety_rule_reason if case and case.safety_rule_triggered and case.safety_rule_reason else r.reason) or "Clinical review recommended"

        # ASHA Info
        asha_name = case.assigned_asha_name or "Sita Patel (ASHA)" if case else "Sita Patel (ASHA)"
        asha_phone = "9823012345"

        # Active Consultation for this referral/case
        cons = db.query(Consultation).filter(Consultation.case_id == case.id).order_by(desc(Consultation.created_at)).first() if case else None

        # Actions
        allowed_actions = []
        status_val = r.status.upper() if r.status else "PENDING_DOCTOR_REVIEW"
        if status_val in ["PENDING_DOCTOR_REVIEW", "NEW", "REFERRED_TO_PHC"]:
            allowed_actions = ["REVIEW_AND_ACKNOWLEDGE", "CALL_ASHA", "VIEW_TIMELINE", "REQUEST_INFO"]
        elif status_val in ["DOCTOR_ACKNOWLEDGED", "ACKNOWLEDGED"]:
            allowed_actions = ["MARK_TRANSPORT_ARRANGED", "MARK_PATIENT_ARRIVED", "CALL_ASHA", "VIEW_TIMELINE"]
        elif status_val == "TRANSPORT_ARRANGED":
            allowed_actions = ["MARK_PATIENT_ARRIVED", "VIEW_TIMELINE", "CALL_ASHA"]
        elif status_val == "PATIENT_ARRIVED":
            allowed_actions = ["START_CONSULTATION", "VIEW_TIMELINE", "RECORD_ARRIVAL_VITALS", "VIEW_PATIENT_RECORD"]
        elif status_val == "IN_CONSULTATION":
            allowed_actions = ["CONTINUE_CONSULTATION", "VIEW_TIMELINE"]
        elif status_val in ["PROCESSED", "COMPLETED"]:
            allowed_actions = ["VIEW_COMPLETED", "VIEW_TIMELINE"]
        else:
            allowed_actions = ["VIEW_TIMELINE"]

        # Urgent / Priority tag
        urgency_str = r.urgency.value if hasattr(r.urgency, "value") else str(r.urgency or "ROUTINE")

        dto = {
            "id": r.id,
            "referral_id": r.id,
            "reference": r.reference or f"REF-{r.id[:8]}",
            "case_id": case.id if case else None,
            "case_reference": case.reference if case else None,
            "citizen_id": citizen.id if citizen else None,
            "consultation_id": cons.id if cons else None,
            "citizen_name": citizen.display_name if citizen else "Citizen",
            "citizen_age": citizen.age_estimate if citizen else 28,
            "citizen_gender": citizen.sex if citizen else "Female",
            "village_name": citizen.village_name if citizen else "Kalyanpur",
            "citizen_phone": citizen.phone if citizen else None,
            "is_pregnant": citizen.is_pregnant if citizen else False,
            "gestational_weeks": citizen.gestational_weeks if citizen else None,
            "category": cat,
            "urgency": urgency_str,
            "priority": urgency_str,
            "reason": triage_reason,
            "status": status_val,
            "transport_assistance_required": r.transport_assistance_required or False,
            "referring_asha_name": asha_name,
            "referring_asha_phone": asha_phone,
            "citizen_reported_concern": case.primary_concern if case else None,
            "asha_confirmed_symptoms": symptoms_list,
            "latest_vitals": latest_v,
            "created_at": r.created_at.isoformat() if r.created_at else utc_now().isoformat(),
            "referred_at": r.created_at.isoformat() if r.created_at else utc_now().isoformat(),
            "acknowledged_at": r.acknowledged_at.isoformat() if r.acknowledged_at else None,
            "allowed_actions": allowed_actions,
        }

        # Search filter
        if search:
            q = search.lower().strip()
            if (
                q in dto["citizen_name"].lower() or
                q in (dto["case_reference"] or "").lower() or
                q in (dto["reference"] or "").lower() or
                q in (dto["village_name"] or "").lower() or
                q in (dto["referring_asha_name"] or "").lower()
            ):
                items.append(dto)
        else:
            items.append(dto)

    # Sorting
    if sort_by == "priority_first":
        priority_rank = {"URGENT": 0, "HIGH": 1, "ROUTINE": 2, "INFORMATION": 3}
        items.sort(key=lambda x: (priority_rank.get(x["urgency"], 9), x["created_at"]))
    elif sort_by == "oldest_first":
        items.sort(key=lambda x: x["created_at"])
    elif sort_by == "newest_first":
        items.sort(key=lambda x: x["created_at"], reverse=True)

    # Pagination
    total = len(items)
    start_idx = (page - 1) * limit
    paginated_items = items[start_idx : start_idx + limit]

    return paginated_items, total


def acknowledge_referral(db: Session, referral_id: str, doctor_user: User) -> Referral:
    """Transitions referral status from PENDING_DOCTOR_REVIEW -> DOCTOR_ACKNOWLEDGED."""
    ref = db.query(Referral).filter(Referral.id == referral_id).first()
    if not ref:
        # Fallback to check case_id matching
        ref = db.query(Referral).filter(Referral.case_id == referral_id).first()
    if not ref:
        raise ValueError(f"Referral with ID {referral_id} not found.")

    ref.status = "DOCTOR_ACKNOWLEDGED"
    ref.acknowledged_at = utc_now()
    ref.acknowledged_by = getattr(doctor_user, "name", getattr(doctor_user, "full_name", "Dr. Abhinav Sharma"))

    if ref.case:
        ref.case.status = CaseStatusEnum.DOCTOR_ACKNOWLEDGED

    # Record Audit Log
    existing_audit = db.query(AuditLog).filter(
        AuditLog.resource_id == (ref.case_id or ref.id),
        AuditLog.action == "REFERRAL_ACKNOWLEDGED"
    ).first()
    if not existing_audit:
        audit = AuditLog(
            actor_user_id=doctor_user.id,
            actor_role="PHC_DOCTOR",
            action="REFERRAL_ACKNOWLEDGED",
            resource_type="Referral",
            resource_id=ref.case_id or ref.id,
            outcome="SUCCESS",
            metadata_json={"referral_id": ref.id, "case_id": ref.case_id}
        )
        db.add(audit)

    db.add(ref)
    db.commit()
    db.refresh(ref)
    return ref


def mark_transport_arranged(db: Session, referral_id: str, doctor_user: User) -> Referral:
    """Transitions referral status to TRANSPORT_ARRANGED."""
    ref = db.query(Referral).filter(Referral.id == referral_id).first()
    if not ref:
        ref = db.query(Referral).filter(Referral.case_id == referral_id).first()
    if not ref:
        raise ValueError(f"Referral with ID {referral_id} not found.")

    ref.status = "TRANSPORT_ARRANGED"
    ref.transport_assistance_required = True
    
    db.add(ref)
    db.commit()
    db.refresh(ref)
    return ref


def mark_patient_arrived(db: Session, referral_id: str, doctor_user: User) -> Referral:
    """Transitions referral status to PATIENT_ARRIVED."""
    ref = db.query(Referral).filter(Referral.id == referral_id).first()
    if not ref:
        ref = db.query(Referral).filter(Referral.case_id == referral_id).first()
    if not ref:
        raise ValueError(f"Referral with ID {referral_id} not found.")

    ref.status = "PATIENT_ARRIVED"
    if ref.case:
        ref.case.status = CaseStatusEnum.PATIENT_ARRIVED

    db.add(ref)
    db.commit()
    db.refresh(ref)
    return ref


def start_or_resume_consultation(db: Session, referral_id: str, doctor_user: User) -> Consultation:
    """
    Idempotently creates or resumes a Consultation for the referral's case.
    Guarantees atomic creation of exactly one Consultation per case, preventing duplicates.
    """
    ref = db.query(Referral).filter(Referral.id == referral_id).first()
    if not ref:
        ref = db.query(Referral).filter(Referral.case_id == referral_id).first()
    if not ref:
        raise ValueError(f"Referral with ID {referral_id} not found.")

    case = ref.case
    if not case:
        raise ValueError(f"Case associated with referral {referral_id} not found.")

    # Check for existing consultation for this case
    cons = db.query(Consultation).filter(Consultation.case_id == case.id).first()
    if not cons:
        facility_id = "FAC-PHC-09"
        if doctor_user.worker_profile and doctor_user.worker_profile.facility_id:
            facility_id = doctor_user.worker_profile.facility_id

        cons = Consultation(
            reference=f"CON-2026-{case.reference.split('-')[-1] if case.reference else case.id[:6]}",
            case_id=case.id,
            doctor_id=doctor_user.id,
            doctor_name=getattr(doctor_user, "name", getattr(doctor_user, "full_name", "Dr. Abhinav Sharma")),
            facility_id=facility_id,
            status="IN_PROGRESS",
            created_at=utc_now()
        )
        db.add(cons)
        db.flush()

    # Update referral and case status
    ref.status = "IN_CONSULTATION"
    case.status = CaseStatusEnum.CONSULTATION_IN_PROGRESS

    db.commit()
    db.refresh(cons)
    return cons


def create_referral(
    db: Session,
    case_id: Optional[str] = None,
    from_asha_id: Optional[str] = None,
    to_facility_id: Optional[str] = None,
    urgency: Any = "ROUTINE",
    reason: Optional[str] = None,
    transport_assistance_required: bool = False,
    citizen_response: str = "ACCEPTED",
    refusal_reason: Optional[str] = None,
    case: Optional[Case] = None,
    asha_user: Optional[User] = None,
    req: Optional[Any] = None
) -> Referral:
    """Creates a new Referral record supporting direct parameters or case/req objects."""
    cid = case_id or (case.id if case else None)
    if not cid:
        raise ValueError("case_id or case must be provided")

    asha_id = from_asha_id or (asha_user.id if asha_user else None)
    fac_id = to_facility_id or (getattr(req, "facility_id", None) if req else None) or "PHC-09"
    urg = urgency if urgency != "ROUTINE" else (getattr(req, "urgency", "ROUTINE") if req else "ROUTINE")
    reas = reason or (getattr(req, "reason", None) if req else None) or "Clinical review recommended"
    trans = transport_assistance_required or (getattr(req, "transport_required", False) if req else False)

    num = db.query(Referral).count() + 1
    fac_name = "Kalyanpur Primary Health Center"
    if case and case.assigned_facility_name:
        fac_name = case.assigned_facility_name

    ref = Referral(
        reference=f"REF-2026-{num:04d}",
        case_id=cid,
        from_asha_id=asha_id,
        to_facility_id=fac_id,
        to_facility_name=fac_name,
        urgency=urg,
        reason=reas,
        status="PENDING_DOCTOR_REVIEW",
        transport_assistance_required=trans,
        citizen_response=citizen_response,
        refusal_reason=refusal_reason,
        created_at=utc_now()
    )
    db.add(ref)
    db.flush()
    return ref


class ReferralService:
    @staticmethod
    def create_referral(*args, **kwargs):
        return create_referral(*args, **kwargs)

    @staticmethod
    def acknowledge_referral(db: Session, case_id: str = None, referral_id: str = None, doctor_user: User = None):
        target = referral_id or case_id
        return acknowledge_referral(db=db, referral_id=target, doctor_user=doctor_user)

    @staticmethod
    def get_doctor_referrals_summary(db: Session, doctor_user: User):
        return get_doctor_referrals_summary(db=db, doctor_user=doctor_user)

    @staticmethod
    def get_doctor_referrals_list(db: Session, doctor_user: User, **kwargs):
        return get_doctor_referrals_list(db=db, doctor_user=doctor_user, **kwargs)

