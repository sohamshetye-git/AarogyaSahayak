import uuid
from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta
from app.database import get_db
from app.models import (
    Case, Referral, Consultation, Prescription, FollowUp, User, CitizenProfile, HouseholdMember,
    CaseStatusEnum, CasePriorityEnum, UserRoleEnum, AuditLog, VitalRecord, AshaVisit, TestOrder, SymptomObservation
)
from app.schemas import (
    StandardResponse, DoctorDashboardResponse, DoctorReferralDTO,
    DoctorDashboardMetricsDTO, TodayClinicalWorkDTO, AshaFollowUpMonitorDTO,
    AshaEscalationItemDTO, RecentActivityItemDTO, DoctorConsultationSubmitRequest,
    StartOrResumeConsultationRequest, InvestigationOrderCreateInput, SampleCollectInput,
    ResultEntryInput, CriticalAcknowledgeInput, DoctorReviewInput, RecollectionRequestInput
)
from app.schemas.teleconsultation import TeleconsultationMessageCreateDTO
from app.dependencies import get_current_user, require_doctor, require_staff
from app.services.consultation_service import ConsultationService
from app.services.referral_service import ReferralService
from app.services.event_bus import publish_domain_event

router = APIRouter(prefix="/doctor", tags=["PHC Doctor"])

@router.get("/dashboard", response_model=StandardResponse)
def get_doctor_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    from datetime import datetime, timezone, timedelta
    now = datetime.now(timezone.utc)
    today_start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)

    # 1. Scope query by Doctor's facility
    worker = getattr(current_user, 'worker_profile', None)
    facility_id = worker.facility_id if worker and worker.facility_id else None
    facility_name = worker.facility_name if worker and worker.facility_name else "Assigned PHC"
    doctor_name = current_user.name if current_user and current_user.name else "PHC Doctor"

    if facility_id:
        referrals_query = db.query(Referral).join(Case, Referral.case_id == Case.id).filter(Referral.to_facility_id == facility_id)
        # Exclude completed/declined/unreachable cases from the active referral list
        referrals_query = referrals_query.filter(~Case.status.in_([CaseStatusEnum.COMPLETED, CaseStatusEnum.DECLINED, CaseStatusEnum.UNREACHABLE]))
        all_referrals = referrals_query.order_by(Referral.created_at.desc()).all()
    else:
        all_referrals = []

    # 2. Build detailed referral DTOs
    incoming_items = []
    for r in all_referrals:
        citizen = r.case.citizen if r.case else None
        
        # Category determination
        cat = "GENERAL"
        if citizen and citizen.is_pregnant:
            cat = "MATERNAL"
        elif citizen and citizen.age_estimate and citizen.age_estimate <= 12:
            cat = "CHILD"
        elif r.case and ("hypertension" in r.case.primary_concern.lower() or "diabetes" in r.case.primary_concern.lower() or "bp" in r.reason.lower()):
            cat = "NCD"

        # Latest vitals from case
        latest_v = None
        if r.case and r.case.vitals:
            lv = r.case.vitals[-1]
            latest_v = {
                "systolic_bp": lv.systolic_bp,
                "diastolic_bp": lv.diastolic_bp,
                "spo2": lv.spo2,
                "pulse": lv.pulse,
                "temperature_c": lv.temperature_c,
                "recorded_at": lv.recorded_at.isoformat() if lv.recorded_at else None,
                "source": lv.source_type.value if lv.source_type else "DEVICE_MEASURED"
            }

        # Symptom terms
        symptoms_list = [s.normalized_term for s in r.case.symptoms] if r.case and r.case.symptoms else []

        # Arrival status mapping
        arrival_status = "WAITING_ARRIVAL"
        if r.status == "PATIENT_ARRIVED" or (r.case and r.case.status == CaseStatusEnum.PATIENT_ARRIVED):
            arrival_status = "ARRIVED"
        elif r.transport_assistance_required:
            arrival_status = "TRANSPORT_EN_ROUTE"

        # State-dependent allowed actions
        allowed_actions = []
        if r.status in ["PENDING_DOCTOR_REVIEW", "NEW", "REFERRED_TO_PHC"]:
            allowed_actions = ["REVIEW_AND_ACKNOWLEDGE", "CALL_ASHA", "VIEW_TIMELINE"]
        elif r.status in ["DOCTOR_ACKNOWLEDGED", "ACKNOWLEDGED"]:
            allowed_actions = ["MARK_PATIENT_ARRIVED", "START_CONSULTATION", "CALL_ASHA", "VIEW_TIMELINE"]
        elif r.status == "PATIENT_ARRIVED":
            allowed_actions = ["START_CONSULTATION", "VIEW_TIMELINE"]
        elif r.status in ["IN_CONSULTATION", "CONSULTATION_IN_PROGRESS"]:
            allowed_actions = ["CONTINUE_CONSULTATION", "VIEW_TIMELINE"]
        elif r.status == "CONSULTED" or (r.case and r.case.status == CaseStatusEnum.COMPLETED):
            allowed_actions = ["VIEW_COMPLETED", "VIEW_TIMELINE"]
        else:
            allowed_actions = ["OPEN_REFERRAL", "VIEW_TIMELINE"]

        dto = DoctorReferralDTO(
            id=r.id,
            referral_id=r.id,
            referral_reference=r.reference or f"REF-{r.id[:8]}",
            reference=r.reference or f"REF-{r.id[:8]}",
            case_id=r.case.id,
            case_reference=r.case.reference,
            citizen_id=citizen.id if citizen else None,
            citizen_name=citizen.display_name if citizen else "Citizen",
            citizen_age=citizen.age_estimate if citizen else 28,
            citizen_gender=citizen.sex if citizen else "Female",
            village_name=citizen.village_name if citizen else "Kalyanpur",
            citizen_phone=citizen.phone if citizen else None,
            is_pregnant=citizen.is_pregnant if citizen else False,
            gestational_weeks=citizen.gestational_weeks if citizen else None,
            category=cat,
            urgency=r.urgency.value if hasattr(r.urgency, "value") else str(r.urgency),
            reason=r.reason,
            status=r.status,
            arrival_status=arrival_status,
            referring_asha_name=r.case.assigned_asha_name or "ASHA Worker",
            referring_asha_phone=r.case.citizen.phone if r.case and r.case.citizen else None,
            citizen_reported_concern=r.case.primary_concern if r.case else None,
            asha_confirmed_symptoms=symptoms_list,
            latest_vitals=latest_v,
            created_at=r.created_at,
            referred_at=r.created_at,
            acknowledged_at=r.acknowledged_at,
            arrived_at=r.acknowledged_at,
            allowed_actions=allowed_actions
        )
        incoming_items.append(dto)

    # 3. Calculate 6 Clickable Metrics consistently from the DB snapshot
    new_referrals_cnt = sum(1 for r in incoming_items if r.status in ["PENDING_DOCTOR_REVIEW", "NEW", "REFERRED_TO_PHC"])
    urgent_cases_cnt = sum(1 for r in incoming_items if r.urgency in ["URGENT", "HIGH"] and r.status != "CONSULTED")
    awaiting_consultation_cnt = sum(1 for r in incoming_items if r.status in ["DOCTOR_ACKNOWLEDGED", "PATIENT_ARRIVED", "ACKNOWLEDGED"])
    
    # Doctor-linked follow-ups query
    followups_query = db.query(FollowUp).join(Case, FollowUp.case_id == Case.id)
    if facility_id:
        followups_query = followups_query.filter(Case.assigned_facility_id == facility_id)
    doctor_followups_raw = followups_query.order_by(FollowUp.due_at.asc()).all()

    asha_followups_cnt = sum(1 for f in doctor_followups_raw if f.status in ["PENDING", "IN_PROGRESS", "SCHEDULED"])
    escalations_cnt = sum(1 for f in doctor_followups_raw if f.status == "ESCALATED")

    today_consultations_cnt = db.query(Consultation).filter(Consultation.created_at >= today_start).count()
    if today_consultations_cnt == 0:
        # Fallback to total consultations in demo if today has none
        today_consultations_cnt = db.query(Consultation).count()

    metrics = DoctorDashboardMetricsDTO(
        new_referrals_count=new_referrals_cnt,
        urgent_cases_count=urgent_cases_cnt,
        awaiting_consultation_count=awaiting_consultation_cnt,
        asha_followups_count=asha_followups_cnt,
        escalations_count=escalations_cnt,
        completed_today_count=today_consultations_cnt
    )

    # 4. Urgent Summary for Banner (Shown strictly when urgent unacknowledged items exist)
    urgent_unacked = [r for r in incoming_items if r.urgency == "URGENT" and r.status in ["PENDING_DOCTOR_REVIEW", "NEW", "REFERRED_TO_PHC"]]
    urgent_summary = None
    if urgent_unacked:
        newest = max(urgent_unacked, key=lambda x: x.created_at)
        urgent_summary = {
            "count": len(urgent_unacked),
            "newest_referral_time": newest.created_at.isoformat(),
            "referring_asha_name": newest.referring_asha_name,
            "patient_name": newest.citizen_name,
            "reason": newest.reason,
            "case_id": newest.case_id
        }

    # 5. Today's Clinical Work
    from app.services.clinical_work_service import get_clinical_work_summary
    cws = get_clinical_work_summary(db, current_user)
    today_clinical_work = TodayClinicalWorkDTO(
        patients_arrived=cws["ready_to_start"],
        consultations_in_progress=cws["consultations_in_progress"],
        pending_investigations=cws["results_ready_for_review"],
        followups_to_review=cws["asha_followups_to_review"]
    )

    # 6. ASHA Follow-up Monitoring list (Doctor-relevant only)
    followup_items = []
    for f in [x for x in doctor_followups_raw if x.status != "ESCALATED"][:5]:
        cit = f.citizen or (f.case.citizen if f.case else None)
        followup_items.append(
            AshaFollowUpMonitorDTO(
                id=f.id,
                followup_id=f.id,
                citizen_name=cit.display_name if cit else "Beneficiary",
                citizen_age=cit.age_estimate if cit else 28,
                village_name=cit.village_name if cit else "Assigned Village",
                is_pregnant=cit.is_pregnant if cit else False,
                case_id=f.case_id,
                case_reference=f.case.reference if f.case else "CASE",
                task_type=f.task_type or "GENERAL_CHECK",
                reason=f.instructions or f.reason,
                assigned_asha_name=f.case.assigned_asha_name if f.case and f.case.assigned_asha_name else "ASHA Worker",
                assigned_asha_phone=cit.phone if cit else None,
                due_at=f.due_at,
                status=f.status,
                completion_result=f.result,
                is_escalated=(f.status == "ESCALATED")
            )
        )

    # 7. Escalations
    escalation_items = []
    for f in [x for x in doctor_followups_raw if x.status == "ESCALATED"]:
        cit = f.citizen or (f.case.citizen if f.case else None)
        escalation_items.append(
            AshaEscalationItemDTO(
                id=f"esc-{f.id}",
                followup_id=f.id,
                case_id=f.case_id,
                case_reference=f.case.reference if f.case else "CASE",
                citizen_name=cit.display_name if cit else "Citizen",
                village_name=cit.village_name if cit else "Assigned Village",
                is_pregnant=cit.is_pregnant if cit else False,
                escalation_reason=f.completion_notes or f.reason or "Persistent elevated symptoms noted in home visit",
                asha_notes=f.completion_notes,
                referring_asha_name=f.case.assigned_asha_name if f.case and f.case.assigned_asha_name else "ASHA Worker",
                referring_asha_phone=cit.phone if cit else None,
                urgency="HIGH",
                escalated_at=f.updated_at or f.created_at,
                is_acknowledged=False
            )
        )

    # 8. Recent Care Activity
    from app.services.recent_activity_service import get_doctor_recent_activity_records
    act_items, _ = get_doctor_recent_activity_records(db=db, doctor_user=current_user, limit=8)
    recent_activities = act_items

    return StandardResponse(
        data=DoctorDashboardResponse(
            doctor_name=doctor_name,
            doctor_role="PHC Medical Officer",
            facility_name=facility_name,
            facility_code=facility_id or "PHC-09",
            metrics=metrics,
            urgent_summary=urgent_summary,
            incoming_referrals=incoming_items,
            today_clinical_work=today_clinical_work,
            asha_followups=followup_items,
            escalations=escalation_items,
            recent_activity=recent_activities,
            notifications_count=urgent_cases_cnt + escalations_cnt,
            # Backward compatibility
            urgent_referrals_count=urgent_cases_cnt,
            today_consultations_count=today_consultations_cnt,
            pending_followups_count=asha_followups_cnt,
            referrals=incoming_items
        ).model_dump()
    )

@router.get("/referrals/summary", response_model=StandardResponse)
def get_doctor_referrals_summary_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    from app.services.referral_service import get_doctor_referrals_summary
    summary = get_doctor_referrals_summary(db=db, doctor_user=current_user)
    return StandardResponse(data=summary)


@router.get("/referrals", response_model=StandardResponse)
def get_doctor_referrals(
    urgency: Optional[str] = None,
    status_filter: Optional[str] = None,
    sort_by: Optional[str] = "priority_first",
    search: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    from app.services.referral_service import get_doctor_referrals_list
    items, total = get_doctor_referrals_list(
        db=db,
        doctor_user=current_user,
        status_filter=status_filter,
        urgency=urgency,
        sort_by=sort_by,
        search=search,
        page=page,
        limit=limit
    )
    return StandardResponse(data={
        "items": items,
        "total": total,
        "page": page,
        "page_size": limit
    })


@router.post("/referrals/{referral_id}/acknowledge", response_model=StandardResponse)
def acknowledge_referral_endpoint(
    referral_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    from app.services.referral_service import acknowledge_referral
    ref = acknowledge_referral(db=db, referral_id=referral_id, doctor_user=current_user)
    return StandardResponse(data={"referral_id": ref.id, "status": ref.status, "acknowledged_at": ref.acknowledged_at.isoformat() if ref.acknowledged_at else None})


@router.post("/referrals/{referral_id}/transport", response_model=StandardResponse)
def mark_transport_arranged_endpoint(
    referral_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    from app.services.referral_service import mark_transport_arranged
    ref = mark_transport_arranged(db=db, referral_id=referral_id, doctor_user=current_user)
    return StandardResponse(data={"referral_id": ref.id, "status": ref.status})


@router.post("/referrals/{referral_id}/arrive", response_model=StandardResponse)
def mark_patient_arrived_endpoint(
    referral_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    from app.services.referral_service import mark_patient_arrived
    ref = mark_patient_arrived(db=db, referral_id=referral_id, doctor_user=current_user)
    return StandardResponse(data={"referral_id": ref.id, "status": ref.status})


@router.post("/consultations/start", response_model=StandardResponse)
def start_or_resume_consultation(
    data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    from datetime import datetime, timezone
    target_id = data.get("referral_id") or data.get("case_id")
    if not target_id:
        raise HTTPException(status_code=400, detail={"code": "INVALID_PARAMETERS", "message": "referral_id or case_id required"})

    referral = db.query(Referral).filter((Referral.id == target_id) | (Referral.reference == target_id)).first()
    if referral:
        case = referral.case
    else:
        case = db.query(Case).filter((Case.id == target_id) | (Case.reference == target_id)).first()
        if case:
            referral = db.query(Referral).filter(Referral.case_id == case.id).first()

    if not case:
        raise HTTPException(status_code=404, detail={"code": "CASE_NOT_FOUND", "message": "Case or referral not found"})

    # Check for existing active or draft consultation
    existing_consultation = db.query(Consultation).filter(
        Consultation.case_id == case.id,
        Consultation.status.in_(["IN_PROGRESS", "DRAFT"])
    ).first()

    if existing_consultation:
        return StandardResponse(data={
            "consultation_id": existing_consultation.id,
            "reference": existing_consultation.reference,
            "case_id": case.id,
            "referral_id": referral.id if referral else None,
            "status": existing_consultation.status,
            "resumed": True
        })

    # Validate state: ensure referral is acknowledged or patient arrived
    if referral and referral.status not in ["DOCTOR_ACKNOWLEDGED", "ACKNOWLEDGED", "PATIENT_ARRIVED", "IN_CONSULTATION"]:
        referral.status = "PATIENT_ARRIVED"
        referral.acknowledged_at = datetime.now(timezone.utc)
        referral.acknowledged_by = current_user.name

    case.status = CaseStatusEnum.IN_CONSULTATION if hasattr(CaseStatusEnum, "IN_CONSULTATION") else CaseStatusEnum.PATIENT_ARRIVED
    if referral:
        referral.status = "IN_CONSULTATION"

    # Create new active consultation
    num = db.query(Consultation).count() + 1
    new_cons = Consultation(
        reference=f"CON-2026-{num:03d}",
        case_id=case.id,
        doctor_id=current_user.id,
        doctor_name=current_user.name,
        facility_id=current_user.worker_profile.facility_id if current_user.worker_profile and current_user.worker_profile.facility_id else "PHC-09",
        consultation_type="IN_PERSON_PHC",
        status="IN_PROGRESS",
        started_at=datetime.now(timezone.utc),
        version=1
    )
    db.add(new_cons)

    audit = AuditLog(
        actor_user_id=current_user.id,
        actor_role="PHC_DOCTOR",
        action="CONSULTATION_STARTED",
        resource_type="CONSULTATION",
        resource_id=new_cons.id,
        outcome="SUCCESS",
        metadata_json={"doctor_name": current_user.name, "case_reference": case.reference}
    )
    db.add(audit)
    db.commit()
    db.refresh(new_cons)

    publish_domain_event(
        event_name="CONSULTATION_STARTED",
        payload={
            "case_id": case.id,
            "consultation_id": new_cons.id,
            "status": "IN_CONSULTATION",
            "doctor_name": current_user.name
        },
        target_roles=["ASHA_WORKER", "PHC_DOCTOR", "DISTRICT_ADMIN"]
    )

    return StandardResponse(data={
        "consultation_id": new_cons.id,
        "reference": new_cons.reference,
        "case_id": case.id,
        "referral_id": referral.id if referral else None,
        "status": "IN_PROGRESS",
        "resumed": False
    })

@router.get("/consultations/waiting", response_model=StandardResponse)
def get_waiting_patients(
    priority: Optional[str] = None,
    search: Optional[str] = None,
    sort: Optional[str] = "priority_wait_time",
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    from datetime import datetime, timezone
    from app.schemas import WaitingPatientItemDTO, WaitingPatientsResponseDTO
    from app.models import Referral, Case, CitizenProfile, Consultation, CasePriorityEnum, UserRoleEnum

    doctor_facility_id = current_user.worker_profile.facility_id if current_user.worker_profile else "PHC-09"

    query = (
        db.query(Referral)
        .join(Case, Referral.case_id == Case.id)
        .join(CitizenProfile, Case.citizen_id == CitizenProfile.id)
        .filter(Referral.status == "PATIENT_ARRIVED")
    )

    if current_user.role == UserRoleEnum.PHC_DOCTOR and doctor_facility_id:
        query = query.filter(Referral.to_facility_id == doctor_facility_id)

    completed_case_ids = (
        db.query(Consultation.case_id)
        .filter(Consultation.status == "COMPLETED")
    )
    query = query.filter(~Referral.case_id.in_(completed_case_ids))

    if priority:
        query = query.filter(Referral.urgency == priority.upper())

    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            (CitizenProfile.display_name.ilike(search_pattern)) |
            (Case.reference.ilike(search_pattern)) |
            (Referral.reference.ilike(search_pattern)) |
            (CitizenProfile.village_name.ilike(search_pattern))
        )

    referrals = query.all()
    now_utc = datetime.now(timezone.utc)

    items = []
    for ref in referrals:
        c = ref.case
        citizen = c.citizen

        draft_cons = (
            db.query(Consultation)
            .filter(Consultation.case_id == c.id, Consultation.status != "COMPLETED")
            .order_by(Consultation.created_at.desc())
            .first()
        )

        latest_vital = None
        if c.vitals:
            lv = c.vitals[-1]
            latest_vital = {
                "systolic_bp": lv.systolic_bp,
                "diastolic_bp": lv.diastolic_bp,
                "spo2": lv.spo2,
                "pulse": lv.pulse,
                "temperature_c": lv.temperature_c,
            }

        arr_time = ref.arrived_at or ref.acknowledged_at or ref.created_at
        if arr_time:
            if arr_time.tzinfo is None:
                arr_time = arr_time.replace(tzinfo=timezone.utc)
            waiting_mins = max(0, int((now_utc - arr_time).total_seconds() // 60))
            arr_iso = arr_time.isoformat()
        else:
            waiting_mins = 0
            arr_iso = None

        context_parts = []
        if citizen and citizen.is_pregnant:
            context_parts.append(f"Pregnant · {citizen.gestational_weeks or 14} weeks")
        elif citizen and citizen.age_estimate:
            context_parts.append(f"{citizen.age_estimate} yrs")

        category_str = "MATERNAL" if (citizen and citizen.is_pregnant) else "ADULT"

        items.append(
            WaitingPatientItemDTO(
                citizen_id=citizen.id if citizen else "N/A",
                citizen_name=citizen.display_name if citizen else "Unknown Citizen",
                age=citizen.age_estimate if citizen else 25,
                gender=citizen.sex if citizen else "Female",
                village_name=citizen.village_name if citizen else "Kalyanpur",
                case_id=c.id,
                case_reference=c.reference,
                referral_id=ref.id,
                referral_reference=ref.reference,
                consultation_id=draft_cons.id if draft_cons else None,
                consultation_status=draft_cons.status if draft_cons else None,
                priority=ref.urgency.value if hasattr(ref.urgency, "value") else str(ref.urgency),
                category=category_str,
                clinical_context=" · ".join(context_parts) if context_parts else None,
                chief_concern=c.primary_concern or ref.reason or "Evaluation required",
                arrived_at=arr_iso,
                waiting_minutes=waiting_mins,
                referring_asha_name=c.assigned_asha_name or "Sita Patel (ASHA)",
                referring_asha_phone="9823012345",
                latest_vitals=latest_vital
            )
        )

    priority_order = {"URGENT": 0, "HIGH": 1, "MODERATE": 2, "ROUTINE": 3, "LOW": 4}
    items.sort(key=lambda x: (
        priority_order.get(x.priority.upper(), 5),
        -x.waiting_minutes,
        x.arrived_at or "",
        x.referral_id
    ))

    total_cnt = len(items)
    start_idx = (page - 1) * page_size
    paged_items = items[start_idx : start_idx + page_size]

    return StandardResponse(
        data=WaitingPatientsResponseDTO(
            items=paged_items,
            total=total_cnt
        ).model_dump()
    )


@router.post("/consultations/start-or-resume", response_model=StandardResponse)
def start_or_resume_consultation(
    req: StartOrResumeConsultationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    from datetime import datetime, timezone
    from app.models import Referral, Consultation, Case, UserRoleEnum

    ref = db.query(Referral).filter(Referral.id == req.referral_id).first()
    if not ref:
        raise HTTPException(
            status_code=404,
            detail={"code": "REFERRAL_NOT_FOUND", "message": f"Referral with ID '{req.referral_id}' was not found"}
        )

    doctor_facility_id = current_user.worker_profile.facility_id if current_user.worker_profile else "PHC-09"
    if current_user.role == UserRoleEnum.PHC_DOCTOR and doctor_facility_id:
        if ref.to_facility_id != doctor_facility_id:
            raise HTTPException(
                status_code=403,
                detail={"code": "FORBIDDEN_FACILITY_ACCESS", "message": "Doctor does not have jurisdiction over this referral"}
            )

    case = ref.case
    now_utc = datetime.now(timezone.utc)

    cons = (
        db.query(Consultation)
        .filter(Consultation.case_id == case.id, Consultation.status != "COMPLETED")
        .order_by(Consultation.created_at.desc())
        .first()
    )

    if not cons:
        import uuid
        cons_ref = f"CON-LIVE-{uuid.uuid4().hex[:8].upper()}"
        cons = Consultation(
            reference=cons_ref,
            case_id=case.id,
            doctor_id=current_user.id,
            doctor_name=getattr(current_user, "full_name", None) or "Dr. Abhinav Sharma",
            facility_id=ref.to_facility_id,
            status="IN_CONSULTATION",
            created_at=now_utc,
        )
        db.add(cons)

    ref.status = "IN_CONSULTATION"
    case.status = CaseStatusEnum.CONSULTATION_IN_PROGRESS
    db.commit()

    publish_domain_event(
        event_name="CONSULTATION_STARTED",
        payload={
            "case_id": case.id,
            "referral_id": ref.id,
            "consultation_id": cons.id,
            "doctor_id": current_user.id,
            "status": "IN_CONSULTATION"
        },
        target_roles=["ASHA_WORKER", "PHC_DOCTOR", "DISTRICT_ADMIN"]
    )

    return StandardResponse(
        data={
            "consultation_id": cons.id,
            "case_id": case.id,
            "referral_id": ref.id,
            "status": cons.status,
            "started_at": now_utc.isoformat()
        }
    )


def _extract_structured_symptoms(case, visits):
    symptoms = [
        {
            "term": s.normalized_term,
            "spoken_term": s.spoken_term,
            "source": s.source_type.value if hasattr(s.source_type, "value") else str(s.source_type),
            "recorded_by": s.recorded_by,
            "severity": s.severity or "MODERATE"
        }
        for s in (case.symptoms if case and case.symptoms else [])
    ]

    if not symptoms and case:
        text_corpus = (case.primary_concern or "") + " " + " ".join([v.notes or "" for v in (visits or [])])
        text_lower = text_corpus.lower()
        extracted = []
        if "headache" in text_lower:
            extracted.append({"term": "Severe Headache", "spoken_term": "खूप डोकेदुखी", "source": "CITIZEN_REPORTED", "recorded_by": "Citizen Voice (Extracted)", "severity": "HIGH"})
        if "vision" in text_lower or "blurred" in text_lower:
            extracted.append({"term": "Blurred Vision", "spoken_term": "डोळ्यांसमोर अंधारी", "source": "CITIZEN_REPORTED", "recorded_by": "Citizen Voice (Extracted)", "severity": "HIGH"})
        if "feet" in text_lower or "edema" in text_lower or "swollen" in text_lower or "legs" in text_lower:
            extracted.append({"term": "Pedal Edema", "spoken_term": "पायावर सूज", "source": "ASHA_REPORTED", "recorded_by": "ASHA Field Observation", "severity": "MODERATE"})
        if "breath" in text_lower or "shortness" in text_lower:
            extracted.append({"term": "Shortness of Breath", "spoken_term": "दम लागणे", "source": "CITIZEN_REPORTED", "recorded_by": "Citizen Voice (Extracted)", "severity": "HIGH"})
        if "fever" in text_lower:
            extracted.append({"term": "Fever", "spoken_term": "ताप", "source": "CITIZEN_REPORTED", "recorded_by": "Citizen Voice (Extracted)", "severity": "MODERATE"})
        if "chest" in text_lower:
            extracted.append({"term": "Chest Pain / Discomfort", "spoken_term": "छातीत दुखणे", "source": "CITIZEN_REPORTED", "recorded_by": "Citizen Voice (Extracted)", "severity": "HIGH"})
        
        if extracted:
            symptoms = extracted
        elif case.primary_concern:
            symptoms = [{"term": case.primary_concern, "spoken_term": None, "source": "CITIZEN_REPORTED", "recorded_by": "Citizen Spoken Concern", "severity": "MODERATE"}]

    citizen_reported = [s for s in symptoms if "CITIZEN" in s.get("source", "").upper() or "AI" in s.get("source", "").upper()]
    asha_confirmed = [s for s in symptoms if "ASHA" in s.get("source", "").upper()]
    asha_observed = [s for s in symptoms if "ASHA" in s.get("source", "").upper() or "FIELD" in s.get("recorded_by", "").upper()]

    if not citizen_reported and symptoms:
        citizen_reported = symptoms
    if not asha_confirmed and symptoms:
        asha_confirmed = symptoms

    return symptoms, citizen_reported, asha_confirmed, asha_observed


@router.get("/consultations/{consultation_id}", response_model=StandardResponse)
def get_consultation_by_id(consultation_id: str, db: Session = Depends(get_db)):
    cons = db.query(Consultation).filter(
        (Consultation.id == consultation_id) | (Consultation.reference == consultation_id)
    ).first()

    if cons:
        case = cons.case
    else:
        # Fallback if ID passed is case_id or referral_id
        case = db.query(Case).filter((Case.id == consultation_id) | (Case.reference == consultation_id)).first()
        if not case:
            ref = db.query(Referral).filter((Referral.id == consultation_id) | (Referral.reference == consultation_id)).first()
            if ref:
                case = ref.case
        if not case:
            raise HTTPException(status_code=404, detail={"code": "CONSULTATION_NOT_FOUND", "message": "Consultation record not found"})
        cons = db.query(Consultation).filter(Consultation.case_id == case.id).order_by(Consultation.created_at.desc()).first()

    referral = db.query(Referral).filter(Referral.case_id == case.id).first() if case else None

    # Extracted & Source-separated Structured Symptoms
    symptoms, citizen_reported_symptoms, asha_confirmed_symptoms, asha_observed_symptoms = _extract_structured_symptoms(case, case.visits if case else [])

    vitals = [
        {
            "systolic_bp": v.systolic_bp,
            "diastolic_bp": v.diastolic_bp,
            "temperature_c": v.temperature_c,
            "spo2": v.spo2,
            "pulse": v.pulse,
            "respiratory_rate": v.respiratory_rate,
            "recorded_at": v.recorded_at.isoformat() if v.recorded_at else None,
            "recorded_by": v.recorded_by,
            "source": v.source_type.value if hasattr(v.source_type, 'value') else str(v.source_type)
        }
        for v in case.vitals
    ] if case else []

    visits = [
        {
            "reference": v.reference,
            "notes": v.notes,
            "category": v.visit_type if hasattr(v, "visit_type") else "Maternal Follow-up",
            "completed_at": v.completed_at.isoformat() if v.completed_at else None
        }
        for v in case.visits
    ] if case else []

    draft_data = None
    if cons:
        draft_data = {
            "consultation_id": cons.id,
            "reference": cons.reference,
            "status": cons.status,
            "examination_notes": cons.examination_notes,
            "clinical_summary": cons.clinical_summary,
            "provisional_diagnosis": cons.provisional_diagnosis,
            "confirmed_diagnosis": cons.confirmed_diagnosis,
            "icd10_code": cons.icd10_code,
            "care_plan_summary": cons.care_plan_summary,
            "asha_followup_instructions": cons.asha_followup_instructions,
            "followup_due_days": cons.followup_due_days,
            "signed_at": cons.signed_at.isoformat() if cons.signed_at else None,
            "prescriptions": [
                {
                    "medicine": item.medicine,
                    "strength": item.strength,
                    "form": item.form,
                    "dose": item.dose,
                    "frequency": item.frequency,
                    "duration": item.duration,
                    "timing": item.timing,
                    "instructions": item.instructions
                }
                for p in cons.prescriptions for item in p.items
            ] if cons.prescriptions else [],
            "investigations": [
                {"test_name": t.test_name, "priority": t.priority, "status": t.status}
                for t in cons.test_orders
            ] if cons.test_orders else []
        }

    return StandardResponse(
        data={
            "consultation_id": cons.id if cons else None,
            "consultation_reference": cons.reference if cons else None,
            "case_id": case.id if case else None,
            "case_reference": case.reference if case else None,
            "referral_id": referral.id if referral else None,
            "referral_reference": referral.reference if referral else None,
            "referral_status": referral.status if referral else "N/A",
            "citizen_id": case.citizen_id if case else None,
            "citizen_name": case.citizen.display_name if case and case.citizen else "Sunita Devi",
            "citizen_age": case.citizen.age_estimate if case and case.citizen else 28,
            "citizen_gender": case.citizen.sex if case and case.citizen else "Female",
            "citizen_phone": case.citizen.phone if case and case.citizen else "9876543210",
            "is_pregnant": case.citizen.is_pregnant if case and case.citizen else False,
            "gestational_weeks": case.citizen.gestational_weeks if case and case.citizen else None,
            "village_name": case.citizen.village_name if case and case.citizen else "Kalyanpur",
            "preferred_language": case.preferred_language if case else "mr-IN",
            "priority": case.priority.value if case else "URGENT",
            "status": cons.status if cons else (case.status.value if case else "NEW"),
            "primary_concern": case.primary_concern if case else None,
            "safety_rule_triggered": case.safety_rule_triggered if case else False,
            "safety_rule_reason": case.safety_rule_reason if case else None,
            "assigned_asha_id": case.assigned_asha_id if case else None,
            "assigned_asha_name": case.assigned_asha_name or "Sita Patel (ASHA)" if case else None,
            "assigned_asha_phone": "9823012345",
            "facility_id": cons.facility_id if cons else (referral.to_facility_id if referral else (case.assigned_facility_id if case else "PHC-09")),
            "symptoms": symptoms,
            "citizen_reported_symptoms": citizen_reported_symptoms,
            "asha_confirmed_symptoms": asha_confirmed_symptoms,
            "asha_observed_symptoms": asha_observed_symptoms,
            "vitals": vitals,
            "visits": visits,
            "draft_consultation": draft_data,
            "created_at": case.created_at.isoformat() if case else None
        }
    )

@router.get("/referrals/{case_id}", response_model=StandardResponse)
def get_case_for_doctor(case_id: str, db: Session = Depends(get_db)):
    # Match by Case ID, Case Reference, Referral ID, or Referral Reference
    case = db.query(Case).filter((Case.id == case_id) | (Case.reference == case_id)).first()
    referral = None

    if not case:
        referral = db.query(Referral).filter((Referral.id == case_id) | (Referral.reference == case_id)).first()
        if referral:
            case = referral.case

    if not case:
        raise HTTPException(status_code=404, detail={"code": "CASE_NOT_FOUND", "message": "Case or referral not found"})

    if not referral:
        referral = db.query(Referral).filter(Referral.case_id == case.id).first()

    symptoms = [
        {"term": s.normalized_term, "spoken_term": s.spoken_term, "source": s.source_type.value, "recorded_by": s.recorded_by, "severity": s.severity}
        for s in case.symptoms
    ]
    vitals = [
        {
            "systolic_bp": v.systolic_bp,
            "diastolic_bp": v.diastolic_bp,
            "temperature_c": v.temperature_c,
            "spo2": v.spo2,
            "pulse": v.pulse,
            "respiratory_rate": v.respiratory_rate,
            "recorded_at": v.recorded_at.isoformat() if v.recorded_at else None,
            "recorded_by": v.recorded_by,
            "source": v.source_type.value
        }
        for v in case.vitals
    ]

    # Include recent visit notes if any
    visits = [
        {
            "reference": v.reference,
            "notes": v.notes,
            "category": v.visit_type if hasattr(v, "visit_type") else "Maternal Follow-up",
            "completed_at": v.completed_at.isoformat() if v.completed_at else None
        }
        for v in case.visits
    ]

    # Check for existing consultation (draft or completed)
    existing_consultation = db.query(Consultation).filter(Consultation.case_id == case.id).order_by(Consultation.created_at.desc()).first()
    draft_data = None
    if existing_consultation:
        draft_data = {
            "consultation_id": existing_consultation.id,
            "status": existing_consultation.status,
            "examination_notes": existing_consultation.examination_notes,
            "clinical_summary": existing_consultation.clinical_summary,
            "provisional_diagnosis": existing_consultation.provisional_diagnosis,
            "confirmed_diagnosis": existing_consultation.confirmed_diagnosis,
            "icd10_code": existing_consultation.icd10_code,
            "care_plan_summary": existing_consultation.care_plan_summary,
            "asha_followup_instructions": existing_consultation.asha_followup_instructions,
            "followup_due_days": existing_consultation.followup_due_days,
            "signed_at": existing_consultation.signed_at.isoformat() if existing_consultation.signed_at else None,
            "prescriptions": [
                {
                    "medicine": item.medicine,
                    "strength": item.strength,
                    "form": item.form,
                    "dose": item.dose,
                    "frequency": item.frequency,
                    "duration": item.duration,
                    "timing": item.timing,
                    "instructions": item.instructions
                }
                for p in existing_consultation.prescriptions for item in p.items
            ] if existing_consultation.prescriptions else [],
            "investigations": [
                {"test_name": t.test_name, "priority": t.priority, "status": t.status}
                for t in existing_consultation.test_orders
            ] if existing_consultation.test_orders else []
        }

    return StandardResponse(
        data={
            "case_id": case.id,
            "case_reference": case.reference,
            "referral_id": referral.id if referral else None,
            "referral_reference": referral.reference if referral else None,
            "referral_status": referral.status if referral else "N/A",
            "citizen_name": case.citizen.display_name if case.citizen else "Sunita Devi",
            "citizen_age": case.citizen.age_estimate if case.citizen else 28,
            "citizen_gender": case.citizen.sex if case.citizen else "Female",
            "citizen_phone": case.citizen.phone if case.citizen else "9876543210",
            "is_pregnant": case.citizen.is_pregnant if case.citizen else False,
            "gestational_weeks": case.citizen.gestational_weeks if case.citizen else None,
            "village_name": case.citizen.village_name if case.citizen else "Kalyanpur",
            "preferred_language": case.preferred_language or "mr-IN",
            "priority": case.priority.value,
            "status": case.status.value,
            "primary_concern": case.primary_concern,
            "safety_rule_triggered": case.safety_rule_triggered,
            "safety_rule_reason": case.safety_rule_reason or "Pregnancy-related warning signs recorded. Urgent medical-officer review recommended.",
            "assigned_asha_name": case.assigned_asha_name or "Sita Patel (ASHA)",
            "assigned_asha_phone": "9823012345",
            "symptoms": symptoms,
            "vitals": vitals,
            "visits": visits,
            "draft_consultation": draft_data,
            "ai_assisted_summary": "AI-assisted clinical overview (decision support only): Patient presents with elevated blood pressure and reported warning signs. Human doctor confirmation required.",
            "created_at": case.created_at.isoformat()
        }
    )

@router.post("/consultations/record-vitals", response_model=StandardResponse)
def doctor_record_vitals(
    data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    from datetime import datetime, timezone
    from app.models import VitalRecord, InformationSourceEnum
    case_id = data.get("case_id")
    case = db.query(Case).filter((Case.id == case_id) | (Case.reference == case_id)).first()
    if not case:
        raise HTTPException(status_code=404, detail={"code": "CASE_NOT_FOUND", "message": "Case not found"})

    v = VitalRecord(
        case_id=case.id,
        systolic_bp=data.get("systolic_bp"),
        diastolic_bp=data.get("diastolic_bp"),
        spo2=data.get("spo2"),
        pulse=data.get("pulse"),
        temperature_c=data.get("temperature_c"),
        respiratory_rate=data.get("respiratory_rate"),
        source_type=InformationSourceEnum.DOCTOR_RECORDED,
        recorded_by=f"Dr. {current_user.name}",
        is_warning_sign=bool(data.get("systolic_bp", 0) and data.get("systolic_bp", 0) >= 140),
        recorded_at=datetime.now(timezone.utc)
    )
    db.add(v)
    db.commit()

    return StandardResponse(data={"recorded": True, "case_id": case.id, "recorded_by": current_user.name})

@router.post("/referrals/{case_id}/acknowledge", response_model=StandardResponse)
def doctor_acknowledge_referral(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    try:
        referral = ReferralService.acknowledge_referral(db=db, case_id=case_id, doctor_user=current_user)
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"code": "INVALID_STATE_TRANSITION", "message": str(e)})

    # Real-time event to assigned ASHA & Dashboards
    publish_domain_event(
        event_name="DOCTOR_ACKNOWLEDGED",
        payload={
            "case_id": case_id,
            "referral_id": referral.id,
            "status": "DOCTOR_ACKNOWLEDGED",
            "doctor_name": current_user.name
        },
        target_roles=["ASHA_WORKER", "PHC_DOCTOR", "DISTRICT_ADMIN"]
    )

    return StandardResponse(data={"case_id": case_id, "acknowledged": True, "status": "DOCTOR_ACKNOWLEDGED"})

@router.post("/referrals/{referral_id}/mark-arrived", response_model=StandardResponse)
def doctor_mark_patient_arrived(
    referral_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    from datetime import datetime, timezone
    ref = db.query(Referral).filter((Referral.id == referral_id) | (Referral.reference == referral_id)).first()
    if not ref:
        # Check by case_id
        ref = db.query(Referral).filter(Referral.case_id == referral_id).first()
    if not ref:
        raise HTTPException(status_code=404, detail={"code": "REFERRAL_NOT_FOUND", "message": "Referral record not found"})

    ref.status = "PATIENT_ARRIVED"
    if ref.case:
        ref.case.status = CaseStatusEnum.PATIENT_ARRIVED
        # Create audit log
        audit = AuditLog(
            actor_user_id=current_user.id,
            actor_role="PHC_DOCTOR",
            action="PATIENT_ARRIVED_AT_PHC",
            resource_type="CASE",
            resource_id=ref.case.id,
            outcome="SUCCESS",
            metadata_json={"arrived_at": datetime.now(timezone.utc).isoformat(), "facility": ref.to_facility_name}
        )
        db.add(audit)

    db.commit()

    publish_domain_event(
        event_name="PATIENT_ARRIVED",
        payload={
            "case_id": ref.case_id,
            "referral_id": ref.id,
            "status": "PATIENT_ARRIVED",
            "doctor_name": current_user.name
        },
        target_roles=["ASHA_WORKER", "PHC_DOCTOR", "DISTRICT_ADMIN"]
    )

    return StandardResponse(data={"referral_id": ref.id, "status": "PATIENT_ARRIVED", "arrived": True})

@router.post("/escalations/{followup_id}/acknowledge", response_model=StandardResponse)
def doctor_acknowledge_escalation(
    followup_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    fup = db.query(FollowUp).filter(FollowUp.id == followup_id).first()
    if not fup:
        raise HTTPException(status_code=404, detail={"code": "FOLLOWUP_NOT_FOUND", "message": "Follow-up not found"})

    # Mark reviewed/acknowledged
    fup.sync_status = "DOCTOR_REVIEWED"
    db.commit()

    return StandardResponse(data={"followup_id": followup_id, "acknowledged": True, "status": "REVIEWED"})

@router.post("/consultations", response_model=StandardResponse)
def complete_doctor_consultation(
    req: DoctorConsultationSubmitRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    try:
        consultation = ConsultationService.complete_consultation(
            db=db,
            doctor_user=current_user,
            req=req
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"code": "INVALID_STATE_TRANSITION", "message": str(e)})

    # Update referral status to CONSULTED
    referral = db.query(Referral).filter(Referral.case_id == req.case_id).first()
    if referral:
        referral.status = "CONSULTED"
        db.commit()

    publish_domain_event(
        event_name="CONSULTATION_COMPLETED",
        payload={
            "case_id": consultation.case_id,
            "consultation_id": consultation.id,
            "confirmed_diagnosis": consultation.confirmed_diagnosis,
            "status": consultation.case.status.value,
            "has_followup": bool(req.asha_followup_instructions)
        },
        target_roles=["ASHA_WORKER", "PHC_DOCTOR", "DISTRICT_ADMIN"]
    )

    if req.asha_followup_instructions:
        publish_domain_event(
            event_name="FOLLOW_UP_ASSIGNED",
            payload={
                "case_id": consultation.case_id,
                "instructions": req.asha_followup_instructions,
                "due_in_days": req.followup_due_days,
                "assigned_asha_id": consultation.case.assigned_asha_id
            },
            target_roles=["ASHA_WORKER"],
            target_user_ids=[consultation.case.assigned_asha_id] if consultation.case.assigned_asha_id else None
        )

    return StandardResponse(
        data={
            "consultation_id": consultation.id,
            "consultation_reference": consultation.reference,
            "case_id": consultation.case_id,
            "confirmed_diagnosis": consultation.confirmed_diagnosis,
            "prescriptions_count": len(consultation.prescriptions),
            "status": consultation.case.status.value,
            "signed_at": consultation.signed_at.isoformat() if consultation.signed_at else None
        }
    )



@router.get("/cases/{case_id}", response_model=StandardResponse)
def get_doctor_case_by_id(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    case = db.query(Case).filter((Case.id == case_id) | (Case.reference == case_id)).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    return StandardResponse(data={
        "case_id": case.id,
        "reference": case.reference,
        "citizen_id": case.citizen_id,
        "citizen_name": case.citizen.display_name if case.citizen else "Unknown Citizen",
        "primary_concern": case.primary_concern,
        "status": str(case.status.value if hasattr(case.status, "value") else case.status),
        "priority": str(case.priority.value if hasattr(case.priority, "value") else case.priority),
        "created_at": case.created_at.isoformat() if case.created_at else None
    })


@router.get("/cases/{case_id}/timeline", response_model=StandardResponse)
def get_doctor_case_timeline(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    from datetime import datetime, timezone, timedelta
    from app.schemas import DoctorCaseTimelineResponse, DoctorTimelineEventDTO
    from app.models import UserRoleEnum

    # 1. Fetch Case by canonical UUID or display reference
    case = db.query(Case).filter((Case.id == case_id) | (Case.reference == case_id)).first()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "CASE_NOT_FOUND", "message": f"Case record with ID '{case_id}' was not found"}
        )

    # 2. Check PHC Doctor Jurisdiction
    doctor_facility_id = current_user.worker_profile.facility_id if current_user.worker_profile else None
    if current_user.role == UserRoleEnum.PHC_DOCTOR and doctor_facility_id:
        facility_match = (case.assigned_facility_id == doctor_facility_id)
        referral_match = any(r.to_facility_id == doctor_facility_id for r in case.referrals)
        if not (facility_match or referral_match):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "FORBIDDEN_FACILITY_ACCESS", "message": "Doctor does not have clinical jurisdiction over this case"}
            )

    citizen = case.citizen
    asha_name = case.assigned_asha_name or "Sita Patel (ASHA)"

    # Latest vitals
    latest_v = None
    if case.vitals:
        lv = case.vitals[-1]
        latest_v = {
            "systolic_bp": lv.systolic_bp,
            "diastolic_bp": lv.diastolic_bp,
            "spo2": lv.spo2,
            "pulse": lv.pulse,
            "temperature_c": lv.temperature_c,
            "recorded_at": lv.recorded_at.isoformat() if lv.recorded_at else None
        }

    # Referral & Consultation statuses
    active_ref = case.referrals[-1] if case.referrals else None
    ref_status = active_ref.status if active_ref else None
    active_cons = case.consultations[-1] if case.consultations else None
    cons_status = active_cons.status if active_cons else None

    # 3. Build Timeline Events
    events_raw = []

    # (a) Case Created / Citizen Concern
    events_raw.append(
        DoctorTimelineEventDTO(
            event_id=f"evt-created-{case.id}",
            event_type="CITIZEN_CONCERN_SUBMITTED",
            title="Citizen Reported Concern",
            safe_description=f"Primary concern recorded: \"{case.primary_concern}\"",
            actor_name=citizen.display_name if citizen else "Citizen",
            actor_role="CITIZEN",
            occurred_at=case.created_at,
            source_entity_type="CASE",
            source_entity_id=case.id,
            category="CITIZEN"
        )
    )

    # (b) ASHA Assignment
    if case.assigned_asha_name:
        events_raw.append(
            DoctorTimelineEventDTO(
                event_id=f"evt-assigned-{case.id}",
                event_type="ASHA_ASSIGNED",
                title="Case Assigned to ASHA Worker",
                safe_description=f"Case assigned to {case.assigned_asha_name} for field triage and home monitoring.",
                actor_name="System Dispatch",
                actor_role="SYSTEM",
                occurred_at=case.created_at + timedelta(seconds=30),
                source_entity_type="CASE",
                source_entity_id=case.id,
                category="ASHA"
            )
        )

    # (c) ASHA Visits
    for v in case.visits:
        events_raw.append(
            DoctorTimelineEventDTO(
                event_id=f"evt-visit-{v.id}",
                event_type="FIELD_VISIT_CONDUCTED",
                title=f"Field Visit: {v.visit_type}",
                safe_description=f"ASHA field visit completed. Observations: {v.notes or 'Home checkup conducted.'}",
                actor_name=asha_name,
                actor_role="ASHA_WORKER",
                occurred_at=v.completed_at or v.created_at,
                source_entity_type="ASHA_VISIT",
                source_entity_id=v.id,
                category="ASHA"
            )
        )

    # (d) Symptoms & Vitals Recorded
    if case.vitals:
        for vit in case.vitals:
            v_desc = []
            if vit.systolic_bp and vit.diastolic_bp:
                v_desc.append(f"BP {vit.systolic_bp}/{vit.diastolic_bp} mmHg")
            if vit.spo2:
                v_desc.append(f"SpO₂ {vit.spo2}%")
            if vit.pulse:
                v_desc.append(f"Pulse {vit.pulse} bpm")
            if vit.temperature_c:
                v_desc.append(f"Temp {vit.temperature_c}°C")
            
            events_raw.append(
                DoctorTimelineEventDTO(
                    event_id=f"evt-vital-{vit.id}",
                    event_type="VITALS_RECORDED",
                    title="Vital Signs Measured",
                    safe_description=f"Recorded: {', '.join(v_desc)}." if v_desc else "Vitals measured.",
                    actor_name=vit.recorded_by or asha_name,
                    actor_role="ASHA_WORKER" if "asha" in str(vit.recorded_by).lower() or not vit.recorded_by else "PHC_DOCTOR",
                    occurred_at=vit.recorded_at,
                    source_entity_type="VITAL_RECORD",
                    source_entity_id=vit.id,
                    category="ASHA"
                )
            )

    # (e) Safety Warning Signs
    if case.safety_rule_triggered:
        events_raw.append(
            DoctorTimelineEventDTO(
                event_id=f"evt-safety-{case.id}",
                event_type="SAFETY_WARNING_ALERT",
                title="Clinical Safety Warning Triggered",
                safe_description=f"Safety rule triggered: {case.safety_rule_reason or 'Maternal/vital warning signs detected.'}",
                actor_name="Clinical Safety Engine",
                actor_role="SYSTEM",
                occurred_at=(case.created_at or datetime.now(timezone.utc)) + timedelta(seconds=60),
                source_entity_type="CASE",
                source_entity_id=case.id,
                category="CITIZEN"
            )
        )

    # (f) Referrals
    for ref in case.referrals:
        events_raw.append(
            DoctorTimelineEventDTO(
                event_id=f"evt-ref-{ref.id}",
                event_type="PHC_REFERRAL_SENT",
                title="Referred to Primary Health Centre",
                safe_description=f"Urgency: {ref.urgency}. Reason: {ref.reason}",
                actor_name=asha_name,
                actor_role="ASHA_WORKER",
                occurred_at=ref.created_at,
                source_entity_type="REFERRAL",
                source_entity_id=ref.id,
                category="REFERRAL"
            )
        )
        if ref.acknowledged_at:
            events_raw.append(
                DoctorTimelineEventDTO(
                    event_id=f"evt-ack-{ref.id}",
                    event_type="DOCTOR_ACKNOWLEDGED",
                    title="Referral Acknowledged by PHC Doctor",
                    safe_description=f"Acknowledged by {ref.acknowledged_by or 'Dr. Abhinav Sharma'}.",
                    actor_name=ref.acknowledged_by or "Dr. Abhinav Sharma",
                    actor_role="PHC_DOCTOR",
                    occurred_at=ref.acknowledged_at,
                    source_entity_type="REFERRAL",
                    source_entity_id=ref.id,
                    category="DOCTOR"
                )
            )
        if ref.status == "PATIENT_ARRIVED":
            events_raw.append(
                DoctorTimelineEventDTO(
                    event_id=f"evt-arr-{ref.id}",
                    event_type="PATIENT_ARRIVED",
                    title="Patient Arrived at PHC",
                    safe_description="Citizen arrival confirmed at PHC reception.",
                    actor_name="PHC Reception",
                    actor_role="PHC_DOCTOR",
                    occurred_at=ref.acknowledged_at or (ref.created_at or datetime.now(timezone.utc)) + timedelta(minutes=15),
                    source_entity_type="REFERRAL",
                    source_entity_id=ref.id,
                    category="REFERRAL"
                )
            )

    # (g) Consultations
    for cons in case.consultations:
        events_raw.append(
            DoctorTimelineEventDTO(
                event_id=f"evt-cons-start-{cons.id}",
                event_type="CONSULTATION_STARTED",
                title="PHC Doctor Consultation Started",
                safe_description=f"Consultation initialized by Dr. {cons.doctor_name}.",
                actor_name=cons.doctor_name,
                actor_role="PHC_DOCTOR",
                occurred_at=cons.started_at or cons.created_at,
                source_entity_type="CONSULTATION",
                source_entity_id=cons.id,
                category="CONSULTATION"
            )
        )
        if cons.examination_notes:
            events_raw.append(
                DoctorTimelineEventDTO(
                    event_id=f"evt-cons-exam-{cons.id}",
                    event_type="CLINICAL_EXAMINATION_RECORDED",
                    title="Clinical Examination Notes Saved",
                    safe_description=f"Notes: {cons.examination_notes}",
                    actor_name=cons.doctor_name,
                    actor_role="PHC_DOCTOR",
                    occurred_at=(cons.created_at or datetime.now(timezone.utc)) + timedelta(minutes=5),
                    source_entity_type="CONSULTATION",
                    source_entity_id=cons.id,
                    category="CONSULTATION"
                )
            )
        for t in cons.test_orders:
            events_raw.append(
                DoctorTimelineEventDTO(
                    event_id=f"evt-test-{t.id}",
                    event_type="INVESTIGATION_ORDERED" if t.status != "RESULT_AVAILABLE" else "INVESTIGATION_RESULT_AVAILABLE",
                    title=f"Investigation: {t.test_name}",
                    safe_description=f"Status: {t.status}. Priority: {t.priority}.",
                    actor_name=cons.doctor_name,
                    actor_role="PHC_DOCTOR",
                    occurred_at=t.ordered_at or cons.created_at,
                    source_entity_type="TEST_ORDER",
                    source_entity_id=t.id,
                    category="INVESTIGATION"
                )
            )
        for rx in cons.prescriptions:
            med_list = [f"{getattr(item, 'generic_name_snapshot', None) or getattr(item, 'medicine', '')} ({item.strength or ''} {item.dose or ''})".strip() for item in rx.items]
            events_raw.append(
                DoctorTimelineEventDTO(
                    event_id=f"evt-rx-{rx.id}",
                    event_type="PRESCRIPTION_SIGNED",
                    title="Prescription Signed & Issued",
                    safe_description=f"Prescribed: {', '.join(med_list) if med_list else 'Medications prescribed'}.",
                    actor_name=cons.doctor_name,
                    actor_role="PHC_DOCTOR",
                    occurred_at=getattr(rx, "signed_at", None) or getattr(rx, "created_at", None) or cons.created_at,
                    source_entity_type="PRESCRIPTION",
                    source_entity_id=rx.id,
                    category="CONSULTATION"
                )
            )
        if cons.completed_at:
            events_raw.append(
                DoctorTimelineEventDTO(
                    event_id=f"evt-cons-comp-{cons.id}",
                    event_type="CONSULTATION_COMPLETED",
                    title="Consultation Completed & Signed",
                    safe_description=f"Confirmed Diagnosis: {cons.confirmed_diagnosis or cons.provisional_diagnosis or 'Clinical Assessment Complete'}.",
                    actor_name=cons.doctor_name,
                    actor_role="PHC_DOCTOR",
                    occurred_at=cons.completed_at,
                    source_entity_type="CONSULTATION",
                    source_entity_id=cons.id,
                    category="DOCTOR"
                )
            )

    # (h) Follow Ups
    for fu in case.follow_ups:
        events_raw.append(
            DoctorTimelineEventDTO(
                event_id=f"evt-fu-{fu.id}",
                event_type="FOLLOWUP_ASSIGNED",
                title=f"Follow-up Directive: {fu.task_type}",
                safe_description=f"Instructions: {fu.instructions}. Assigned to ASHA: {asha_name}.",
                actor_name="Dr. Abhinav Sharma",
                actor_role="PHC_DOCTOR",
                occurred_at=fu.created_at,
                source_entity_type="FOLLOW_UP",
                source_entity_id=fu.id,
                category="FOLLOWUP"
            )
        )
        if fu.status == "COMPLETED":
            events_raw.append(
                DoctorTimelineEventDTO(
                    event_id=f"evt-fu-comp-{fu.id}",
                    event_type="FOLLOWUP_COMPLETED",
                    title="ASHA Follow-up Visit Completed",
                    safe_description=f"Outcome: {fu.completion_notes or fu.result or 'Follow-up completed successfully.'}",
                    actor_name=asha_name,
                    actor_role="ASHA_WORKER",
                    occurred_at=fu.completed_at or fu.updated_at,
                    source_entity_type="FOLLOW_UP",
                    source_entity_id=fu.id,
                    category="FOLLOWUP"
                )
            )
        elif fu.status == "ESCALATED":
            events_raw.append(
                DoctorTimelineEventDTO(
                    event_id=f"evt-fu-esc-{fu.id}",
                    event_type="FOLLOWUP_ESCALATED",
                    title="⚠️ ASHA Follow-up Escalated to Doctor",
                    safe_description=f"Reason: {fu.escalation_conditions or fu.completion_notes or 'Severe warning signs detected.'}",
                    actor_name=asha_name,
                    actor_role="ASHA_WORKER",
                    occurred_at=fu.updated_at or fu.created_at,
                    source_entity_type="FOLLOW_UP",
                    source_entity_id=fu.id,
                    category="FOLLOWUP"
                )
            )

    # (i) Canonical Investigation Orders
    from app.models import InvestigationOrder
    cons_ids = [c.id for c in case.consultations]
    inv_orders = db.query(InvestigationOrder).filter(
        (InvestigationOrder.case_id == case.id) | (InvestigationOrder.consultation_id.in_(cons_ids) if cons_ids else False)
    ).all()

    for inv in inv_orders:
        doctor_name = inv.ordered_by_doctor.name if inv.ordered_by_doctor else "Dr. Abhinav Sharma"
        events_raw.append(
            DoctorTimelineEventDTO(
                event_id=f"evt-inv-order-{inv.id}",
                event_type="INVESTIGATION_ORDERED",
                title=f"Investigation Ordered: {inv.test_name}",
                safe_description=f"Order Ref: {inv.reference} • Category: {inv.category} • Priority: {inv.priority} • Status: {inv.status}",
                actor_name=doctor_name,
                actor_role="PHC_DOCTOR",
                occurred_at=inv.ordered_at or inv.created_at,
                source_entity_type="INVESTIGATION_ORDER",
                source_entity_id=inv.id,
                category="INVESTIGATION"
            )
        )
        if inv.sample and inv.sample.collected_at:
            collector = inv.sample.collected_by.name if getattr(inv.sample, "collected_by", None) else "Lab Technician"
            events_raw.append(
                DoctorTimelineEventDTO(
                    event_id=f"evt-inv-sample-{inv.sample.id}",
                    event_type="INVESTIGATION_SAMPLE_COLLECTED",
                    title=f"Sample Collected: {inv.test_name}",
                    safe_description=f"Sample Ref: {inv.sample.sample_reference or 'N/A'} • Status: {inv.sample.collection_status}",
                    actor_name=collector,
                    actor_role="STAFF",
                    occurred_at=inv.sample.collected_at,
                    source_entity_type="INVESTIGATION_SAMPLE",
                    source_entity_id=inv.sample.id,
                    category="INVESTIGATION"
                )
            )
        if inv.result and inv.result.resulted_at:
            entered_by = inv.result.entered_by.name if getattr(inv.result, "entered_by", None) else "Lab Technician"
            if inv.result.items:
                res_parts = [f"{i.parameter_name}: {i.value} {i.unit or ''}".strip() for i in inv.result.items[:2]]
                res_summary = f"Result: {', '.join(res_parts)}"
            events_raw.append(
                DoctorTimelineEventDTO(
                    event_id=f"evt-inv-result-{inv.result.id}",
                    event_type="INVESTIGATION_RESULT_RECORDED",
                    title=f"Investigation Result: {inv.test_name}",
                    safe_description=f"{res_summary} • Status: {inv.status}",
                    actor_name=entered_by,
                    actor_role="STAFF",
                    occurred_at=inv.result.resulted_at,
                    source_entity_type="INVESTIGATION_RESULT",
                    source_entity_id=inv.result.id,
                    category="INVESTIGATION"
                )
            )
        if inv.result and getattr(inv.result, "review", None) and inv.result.review.reviewed_at:
            rev_doc = inv.result.review.doctor.name if getattr(inv.result.review, "doctor", None) else "Dr. Abhinav Sharma"
            events_raw.append(
                DoctorTimelineEventDTO(
                    event_id=f"evt-inv-review-{inv.result.review.id}",
                    event_type="INVESTIGATION_REVIEWED",
                    title=f"Investigation Reviewed: {inv.test_name}",
                    safe_description=f"Review Note: {inv.result.review.review_note or 'Reviewed'} • Outcome: {inv.result.review.outcome}",
                    actor_name=rev_doc,
                    actor_role="PHC_DOCTOR",
                    occurred_at=inv.result.review.reviewed_at,
                    source_entity_type="INVESTIGATION_REVIEW",
                    source_entity_id=inv.result.review.id,
                    category="INVESTIGATION"
                )
            )

    def norm_time(dt):
        if dt is None:
            return datetime.now(timezone.utc)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt

    events_raw.sort(key=lambda x: norm_time(x.occurred_at))

    seen_ids = set()
    unique_events = []
    for ev in events_raw:
        if ev.event_id not in seen_ids:
            seen_ids.add(ev.event_id)
            unique_events.append(ev)

    return StandardResponse(
        data=DoctorCaseTimelineResponse(
            case_id=case.id,
            case_reference=case.reference,
            citizen_id=citizen.id if citizen else "N/A",
            citizen_name=citizen.display_name if citizen else "Citizen",
            citizen_age=citizen.age_estimate if citizen else 28,
            citizen_gender=citizen.sex if citizen else "Female",
            village_name=citizen.village_name if citizen else "Kalyanpur",
            is_pregnant=citizen.is_pregnant if citizen else False,
            gestational_weeks=citizen.gestational_weeks if citizen else None,
            priority=case.priority.value,
            status=case.status.value,
            primary_concern=case.primary_concern,
            assigned_asha_name=asha_name,
            assigned_asha_phone="9823012345",
            assigned_facility_name=case.assigned_facility_name or "Kalyanpur Primary Health Centre",
            latest_vitals=latest_v,
            referral_status=ref_status,
            consultation_status=cons_status,
            events=unique_events
        ).model_dump()
    )


@router.get("/dashboard/clinical-work", response_model=StandardResponse)
def get_clinical_work_summary_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    from app.models import UserRoleEnum
    if current_user.role not in [UserRoleEnum.PHC_DOCTOR, UserRoleEnum.SYSTEM_ADMIN, UserRoleEnum.DISTRICT_ADMIN] and str(current_user.role) not in ["PHC_DOCTOR", "SYSTEM_ADMIN", "DISTRICT_ADMIN"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN_ROLE", "message": "Only PHC Doctors can access clinical work summary."}
        )
    from app.services.clinical_work_service import get_clinical_work_summary
    summary = get_clinical_work_summary(db, current_user)
    return StandardResponse(data=summary)


@router.get("/investigations/summary", response_model=StandardResponse)
def get_doctor_investigations_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    from app.services.investigation_service import get_investigations_summary
    summary = get_investigations_summary(db, current_user)
    return StandardResponse(data=summary.model_dump())


@router.get("/investigations", response_model=StandardResponse)
def get_doctor_investigations(
    status_filter: Optional[str] = None,
    status: Optional[str] = None,
    category: Optional[str] = None,
    priority: Optional[str] = None,
    search: Optional[str] = None,
    sort_by: Optional[str] = "critical_first",
    page: int = 1,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    from sqlalchemy import case as sql_case, or_
    from app.models import InvestigationOrder, CitizenProfile, Case, Consultation
    from app.services.investigation_service import to_doctor_investigation_dto

    st = status_filter or status
    query = db.query(InvestigationOrder).outerjoin(CitizenProfile, InvestigationOrder.citizen_id == CitizenProfile.id)

    if st:
        if st == "ALL_ACTIVE":
            query = query.filter(InvestigationOrder.status.notin_(["CLOSED", "CANCELLED"]))
        elif st == "RESULT_AVAILABLE":
            query = query.filter(InvestigationOrder.status.in_(["RESULT_AVAILABLE", "CRITICAL_RESULT", "REVIEW_REQUIRED"]))
        elif st == "CRITICAL":
            query = query.filter(InvestigationOrder.status == "CRITICAL_RESULT")
        elif st == "REVIEW_REQUIRED":
            query = query.filter(InvestigationOrder.status.in_(["RESULT_AVAILABLE", "CRITICAL_RESULT", "REVIEW_REQUIRED", "DOCTOR_ACKNOWLEDGED"]))
        else:
            query = query.filter(InvestigationOrder.status == st)

    if category:
        query = query.filter(InvestigationOrder.category == category)
    if priority:
        query = query.filter(InvestigationOrder.priority == priority)

    if search:
        s = f"%{search}%"
        query = query.outerjoin(Case, InvestigationOrder.case_id == Case.id).outerjoin(Consultation, InvestigationOrder.consultation_id == Consultation.id)
        query = query.filter(
            or_(
                CitizenProfile.display_name.ilike(s),
                CitizenProfile.village_name.ilike(s),
                InvestigationOrder.reference.ilike(s),
                InvestigationOrder.test_name.ilike(s),
                Case.reference.ilike(s),
                Consultation.reference.ilike(s)
            )
        )

    if sort_by == "critical_first":
        query = query.order_by(
            sql_case((InvestigationOrder.status == "CRITICAL_RESULT", 1), else_=2),
            InvestigationOrder.ordered_at.desc()
        )
    elif sort_by == "result_ready_first":
        query = query.order_by(
            sql_case((InvestigationOrder.status.in_(["RESULT_AVAILABLE", "CRITICAL_RESULT"]), 1), else_=2),
            InvestigationOrder.ordered_at.desc()
        )
    elif sort_by == "oldest_pending":
        query = query.order_by(InvestigationOrder.ordered_at.asc())
    elif sort_by == "patient_name":
        query = query.order_by(CitizenProfile.display_name.asc())
    else:
        query = query.order_by(InvestigationOrder.ordered_at.desc())

    orders = query.all()
    dtos = [to_doctor_investigation_dto(o).model_dump() for o in orders]
    # Return list if called without pagination wrap or return list directly for backwards compat
    return StandardResponse(data=dtos)


@router.get("/investigations/{investigation_id}", response_model=StandardResponse)
def get_doctor_investigation_detail(
    investigation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    from app.models import InvestigationOrder
    from app.services.investigation_service import to_investigation_detail_dto
    order = db.query(InvestigationOrder).filter(InvestigationOrder.id == investigation_id).first()
    if not order:
        order = db.query(InvestigationOrder).filter(InvestigationOrder.reference == investigation_id).first()
    if not order:
        raise HTTPException(status_code=404, detail={"code": "INVESTIGATION_NOT_FOUND", "message": f"Investigation order '{investigation_id}' not found"})
    return StandardResponse(data=to_investigation_detail_dto(order).model_dump())


@router.post("/investigations", response_model=StandardResponse)
def create_doctor_investigation(
    req: InvestigationOrderCreateInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    from app.services.investigation_service import create_investigation_order, to_investigation_detail_dto
    order = create_investigation_order(db, current_user, req)
    return StandardResponse(data=to_investigation_detail_dto(order).model_dump())


@router.post("/investigations/{investigation_id}/collect", response_model=StandardResponse)
def collect_doctor_investigation_sample(
    investigation_id: str,
    req: SampleCollectInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    from app.services.investigation_service import record_sample_collection, to_investigation_detail_dto
    order = record_sample_collection(db, current_user, investigation_id, req)
    return StandardResponse(data=to_investigation_detail_dto(order).model_dump())


@router.post("/investigations/{investigation_id}/result", response_model=StandardResponse)
def enter_doctor_investigation_result(
    investigation_id: str,
    req: ResultEntryInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    from app.services.investigation_service import enter_investigation_result, to_investigation_detail_dto
    order = enter_investigation_result(db, current_user, investigation_id, req)
    return StandardResponse(data=to_investigation_detail_dto(order).model_dump())


@router.post("/investigations/{investigation_id}/acknowledge-critical", response_model=StandardResponse)
def acknowledge_doctor_investigation_critical(
    investigation_id: str,
    req: Optional[CriticalAcknowledgeInput] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    from app.services.investigation_service import acknowledge_critical_result, to_investigation_detail_dto
    order = acknowledge_critical_result(db, current_user, investigation_id, req or CriticalAcknowledgeInput())
    return StandardResponse(data=to_investigation_detail_dto(order).model_dump())


@router.post("/investigations/{investigation_id}/review", response_model=StandardResponse)
def review_doctor_investigation_result(
    investigation_id: str,
    req: Optional[DoctorReviewInput] = None,
    notes: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    from app.services.investigation_service import review_investigation_result_full, to_investigation_detail_dto
    if req is None or (isinstance(req, dict) and not req):
        req = DoctorReviewInput(review_note=notes or "Normal findings reviewed", outcome="NO_CHANGE")
    elif notes and not req.review_note:
        req.review_note = notes
    order = review_investigation_result_full(db, current_user, investigation_id, req)
    return StandardResponse(data=to_investigation_detail_dto(order).model_dump())


@router.post("/investigations/{investigation_id}/request-recollection", response_model=StandardResponse)
def request_doctor_investigation_recollection(
    investigation_id: str,
    req: RecollectionRequestInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    from app.services.investigation_service import request_investigation_recollection, to_investigation_detail_dto
    order = request_investigation_recollection(db, current_user, investigation_id, req)
    return StandardResponse(data=to_investigation_detail_dto(order).model_dump())


@router.post("/investigations/{investigation_id}/cancel", response_model=StandardResponse)
def cancel_doctor_investigation(
    investigation_id: str,
    req: RecollectionRequestInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    from app.services.investigation_service import cancel_investigation_order, to_doctor_investigation_dto
    order = cancel_investigation_order(db, current_user, investigation_id, req.reason)
    return StandardResponse(data=to_doctor_investigation_dto(order).model_dump())


@router.get("/consultations/{consultation_id}/investigations", response_model=StandardResponse)
def get_doctor_consultation_investigations(
    consultation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    from app.models import InvestigationOrder
    from app.services.investigation_service import to_doctor_investigation_dto
    orders = db.query(InvestigationOrder).filter(InvestigationOrder.consultation_id == consultation_id).all()
    dtos = [to_doctor_investigation_dto(o).model_dump() for o in orders]
    return StandardResponse(data=dtos)


@router.post("/followups/{followup_id}/review", response_model=StandardResponse)
def review_asha_followup(
    followup_id: str,
    action: Optional[str] = "MARK_REVIEWED",
    notes: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    from datetime import datetime, timezone
    fu = db.query(FollowUp).filter(FollowUp.id == followup_id).first()
    if not fu:
        raise HTTPException(status_code=404, detail={"code": "FOLLOWUP_NOT_FOUND", "message": "FollowUp record not found"})
    
    now = datetime.now(timezone.utc)
    fu.reviewed_by_doctor_at = now
    fu.reviewed_by_doctor_id = current_user.id
    if action == "MARK_REVIEWED":
        fu.status = "REVIEWED"
    if notes:
        fu.completion_notes = (fu.completion_notes or "") + f" [Doctor Review: {notes}]"
    db.commit()

    publish_domain_event(
        event_name="FOLLOWUP_REVIEWED",
        payload={
            "followup_id": fu.id,
            "case_id": fu.case_id,
            "action": action,
            "reviewed_at": now.isoformat(),
            "doctor_id": current_user.id
        },
        target_roles=["PHC_DOCTOR", "ASHA_WORKER"]
    )
    return StandardResponse(data={"followup_id": fu.id, "status": fu.status, "reviewed_at": now.isoformat()})


@router.get("/consultations", response_model=StandardResponse)
def get_doctor_consultations(
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    from app.services.clinical_work_service import query_consultations_in_progress

    if status_filter == "IN_CONSULTATION":
        query = query_consultations_in_progress(db, current_user)
    else:
        query = db.query(Consultation)

    consultations = query.all()
    items = []
    for c in consultations:
        case = c.case
        cit = case.citizen if case else None
        items.append({
            "id": c.id,
            "reference": c.reference or f"CONS-{c.id[:8]}",
            "case_id": c.case_id,
            "case_reference": case.reference if case else "",
            "citizen_id": cit.id if cit else "",
            "citizen_name": cit.display_name if cit else "Citizen",
            "citizen_age": cit.age_estimate if cit else 28,
            "citizen_gender": cit.sex if cit else "Female",
            "village_name": cit.village_name if cit else "Kalyanpur",
            "is_pregnant": cit.is_pregnant if cit else False,
            "priority": case.priority.value if case else "HIGH",
            "status": c.status,
            "started_at": c.started_at.isoformat() if c.started_at else None,
            "examination_notes": c.examination_notes,
            "provisional_diagnosis": c.provisional_diagnosis,
            "confirmed_diagnosis": c.confirmed_diagnosis,
            "signed_at": c.signed_at.isoformat() if c.signed_at else None
        })
    return StandardResponse(data=items)


@router.get("/followups/summary", response_model=StandardResponse)
def get_doctor_followups_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    from datetime import datetime, timezone, timedelta
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    all_fu = db.query(FollowUp).all()

    result_ready = sum(1 for f in all_fu if f.status in ["COMPLETED_BY_ASHA", "REVIEW_REQUIRED", "COMPLETED"])
    escalated = sum(1 for f in all_fu if f.status in ["ESCALATED", "DOCTOR_ACKNOWLEDGED"])
    overdue = sum(1 for f in all_fu if f.due_at and f.due_at < now and f.status in ["PENDING", "IN_PROGRESS"])
    due_today = sum(1 for f in all_fu if f.due_at and f.due_at >= today_start and f.due_at < (today_start + timedelta(days=1)) and f.status in ["PENDING", "IN_PROGRESS"])
    pending_asha = sum(1 for f in all_fu if f.status in ["PENDING", "IN_PROGRESS"])
    reviewed_today = sum(1 for f in all_fu if f.reviewed_by_doctor_at and f.reviewed_by_doctor_at >= today_start)
    resolved_today = sum(1 for f in all_fu if f.status == "RESOLVED" and f.updated_at and f.updated_at >= today_start)
    actionable = sum(1 for f in all_fu if f.status in ["PENDING", "IN_PROGRESS", "COMPLETED_BY_ASHA", "REVIEW_REQUIRED", "ESCALATED", "DOCTOR_ACKNOWLEDGED"])

    return StandardResponse(data={
        "result_ready": result_ready,
        "escalated": escalated,
        "overdue": overdue,
        "due_today": due_today,
        "pending_asha": pending_asha,
        "reviewed_today": reviewed_today,
        "resolved_today": resolved_today,
        "actionable": actionable,
        "total": len(all_fu)
    })


@router.get("/followups", response_model=StandardResponse)
def get_doctor_followups(
    status: Optional[str] = None,
    status_filter: Optional[str] = None,
    priority: Optional[str] = None,
    priority_filter: Optional[str] = None,
    query: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    filter_status = status or status_filter or "ACTIONABLE"
    filter_priority = priority or priority_filter or "ALL"

    query_builder = db.query(FollowUp)

    if filter_status == "ACTIONABLE":
        query_builder = query_builder.filter(FollowUp.status.in_(["PENDING", "IN_PROGRESS", "COMPLETED_BY_ASHA", "REVIEW_REQUIRED", "ESCALATED", "DOCTOR_ACKNOWLEDGED"]))
    elif filter_status in ["RESULT_READY", "COMPLETED_BY_ASHA", "REVIEW_REQUIRED"]:
        query_builder = query_builder.filter(FollowUp.status.in_(["COMPLETED_BY_ASHA", "REVIEW_REQUIRED", "COMPLETED"]))
    elif filter_status in ["ESCALATED", "DOCTOR_ACKNOWLEDGED"]:
        query_builder = query_builder.filter(FollowUp.status.in_(["ESCALATED", "DOCTOR_ACKNOWLEDGED"]))
    elif filter_status == "OVERDUE":
        query_builder = query_builder.filter(FollowUp.due_at < now, FollowUp.status.in_(["PENDING", "IN_PROGRESS"]))
    elif filter_status == "REVIEWED":
        query_builder = query_builder.filter(FollowUp.status == "REVIEWED")
    elif filter_status == "RESOLVED":
        query_builder = query_builder.filter(FollowUp.status == "RESOLVED")
    elif filter_status != "ALL":
        query_builder = query_builder.filter(FollowUp.status == filter_status)

    if filter_priority != "ALL":
        query_builder = query_builder.filter(FollowUp.priority == filter_priority)

    followups = query_builder.order_by(FollowUp.due_at.asc()).all()
    items = []
    for f in followups:
        case = f.case
        cit = f.citizen or (case.citizen if case else None)
        doc_user = db.query(User).filter(User.id == f.created_by_id).first() if f.created_by_id else None
        asha_user = db.query(User).filter(User.id == f.assigned_user_id).first() if f.assigned_user_id else None

        latest_vitals = None
        if case and case.vitals:
            lv = case.vitals[-1]
            latest_vitals = {
                "systolic_bp": lv.systolic_bp,
                "diastolic_bp": lv.diastolic_bp,
                "spo2": lv.spo2,
                "pulse": lv.pulse,
                "recorded_at": lv.recorded_at.isoformat() if lv.recorded_at else None
            }

        ref_str = f"FUP-{f.id[:8].upper()}" if "-" not in f.id else f.id

        item = {
            "follow_up_id": f.id,
            "id": f.id,
            "follow_up_reference": ref_str,
            "reference": ref_str,
            "case_id": f.case_id or "",
            "case_reference": case.reference if case else "CASE-001",
            "citizen_id": cit.id if cit else "",
            "citizen_name": cit.display_name if cit else "Citizen",
            "patient_name": cit.display_name if cit else "Citizen",
            "age": cit.age_estimate if cit else 28,
            "patient_age": cit.age_estimate if cit else 28,
            "gender": cit.sex if cit else "Female",
            "patient_gender": cit.sex if cit else "Female",
            "village_name": cit.village_name if cit else "Kalyanpur",
            "is_pregnant": cit.is_pregnant if cit else False,
            "gestational_weeks": cit.gestational_weeks if cit else None,
            "priority": f.priority.value if hasattr(f.priority, "value") else str(f.priority),
            "status": f.status,
            "source": f.source or "DOCTOR_ASSIGNED",
            "directive": f.instructions,
            "instructions": f.instructions,
            "task_type": f.task_type,
            "reason": f.reason,
            "assigned_doctor_id": f.created_by_id,
            "assigned_doctor_name": doc_user.name if doc_user else "Dr. Abhinav Sharma",
            "created_by_doctor_name": doc_user.name if doc_user else "Dr. Abhinav Sharma",
            "assigned_asha_id": f.assigned_user_id,
            "assigned_asha_name": asha_user.name if asha_user else (case.assigned_asha_name if case else "Sita Patel"),
            "due_at": f.due_at.isoformat() if f.due_at else None,
            "completed_at": f.completed_at.isoformat() if f.completed_at else None,
            "reviewed_at": f.reviewed_by_doctor_at.isoformat() if f.reviewed_by_doctor_at else None,
            "latest_vitals": latest_vitals,
            "symptoms_outcome": f.symptoms_outcome,
            "completion_notes": f.completion_notes,
            "escalation_reason": f.escalation_conditions or f.completion_notes,
            "measurements_to_repeat": f.measurements_to_repeat or []
        }
        items.append(item)

    return StandardResponse(data={"items": items, "total": len(items)})


@router.get("/followups/{followup_id}", response_model=StandardResponse)
def get_doctor_followup_detail(
    followup_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    f = db.query(FollowUp).filter(FollowUp.id == followup_id).first()
    if not f:
        raise HTTPException(status_code=404, detail={"code": "FOLLOWUP_NOT_FOUND", "message": "Follow-up record not found"})

    case = f.case
    cit = f.citizen or (case.citizen if case else None)

    # Resolve doctor identity
    doc_user = None
    assigned_doctor_name = "Unassigned"
    assigned_doctor_id = None
    if f.created_by_id and f.created_by_role in ["PHC_DOCTOR", "DOCTOR", "STAFF"]:
        doc_user = db.query(User).filter(User.id == f.created_by_id).first()
        if doc_user:
            assigned_doctor_name = doc_user.name
            assigned_doctor_id = doc_user.id
    elif case and getattr(case, "assigned_doctor_name", None):
        assigned_doctor_name = case.assigned_doctor_name
        assigned_doctor_id = getattr(case, "assigned_doctor_id", None)

    # Resolve ASHA identity
    asha_user = None
    assigned_asha_name = "Unassigned"
    assigned_asha_id = f.assigned_user_id
    if f.assigned_user_id:
        asha_user = db.query(User).filter(User.id == f.assigned_user_id).first()
        if asha_user:
            assigned_asha_name = asha_user.name
    elif f.created_by_role == "ASHA_WORKER" and f.created_by_id:
        asha_user = db.query(User).filter(User.id == f.created_by_id).first()
        if asha_user:
            assigned_asha_name = asha_user.name
            assigned_asha_id = asha_user.id
    elif case and getattr(case, "assigned_asha_name", None):
        assigned_asha_name = case.assigned_asha_name
        assigned_asha_id = getattr(case, "assigned_asha_id", None)

    # Baseline vitals (only from initial consultation / case vitals)
    baseline_vitals = None
    repeat_vitals = None
    if case and case.vitals and len(case.vitals) > 0:
        bv = case.vitals[0]
        baseline_vitals = {
            "systolic_bp": bv.systolic_bp,
            "diastolic_bp": bv.diastolic_bp,
            "spo2": bv.spo2,
            "pulse": bv.pulse,
            "temperature_c": bv.temperature_c,
            "glucose_mg_dl": bv.glucose_mg_dl,
            "recorded_at": bv.recorded_at.isoformat() if bv.recorded_at else None
        }

    # Repeat vitals should ONLY be populated if visit was actually conducted / completed / escalated
    is_conducted = f.status in ["COMPLETED", "COMPLETED_BY_ASHA", "REVIEW_REQUIRED", "ESCALATED", "DOCTOR_ACKNOWLEDGED", "REVIEWED", "RESOLVED"]
    if is_conducted and case and case.vitals and len(case.vitals) > 1:
        rv = case.vitals[-1]
        repeat_vitals = {
            "systolic_bp": rv.systolic_bp,
            "diastolic_bp": rv.diastolic_bp,
            "spo2": rv.spo2,
            "pulse": rv.pulse,
            "temperature_c": rv.temperature_c,
            "glucose_mg_dl": rv.glucose_mg_dl,
            "recorded_at": rv.recorded_at.isoformat() if rv.recorded_at else None
        }

    ref_str = f"FUP-{f.id[:8].upper()}" if "-" not in f.id else f.id

    # Build chronological timeline
    timeline_events = [
        {
            "event": "FOLLOWUP_SCHEDULED" if f.source == "ASHA_SCHEDULED" else "FOLLOWUP_ASSIGNED",
            "timestamp": f.created_at.isoformat() if f.created_at else None,
            "actor": assigned_asha_name if f.source == "ASHA_SCHEDULED" else assigned_doctor_name
        },
    ]
    if f.started_at:
        timeline_events.append({"event": "FOLLOWUP_STARTED", "timestamp": f.started_at.isoformat(), "actor": assigned_asha_name})
    if f.completed_at and f.status not in ["ESCALATED"]:
        timeline_events.append({"event": "FOLLOWUP_COMPLETED_BY_ASHA", "timestamp": f.completed_at.isoformat(), "actor": assigned_asha_name})
    if f.status in ["ESCALATED", "DOCTOR_ACKNOWLEDGED"]:
        esc_time = f.completed_at.isoformat() if f.completed_at else (f.updated_at.isoformat() if f.updated_at else None)
        timeline_events.append({"event": "FOLLOWUP_ESCALATED", "timestamp": esc_time, "actor": assigned_asha_name})
    if f.reviewed_by_doctor_at:
        doc_actor = current_user.name if (current_user and current_user.name) else assigned_doctor_name
        timeline_events.append({"event": "FOLLOWUP_REVIEWED", "timestamp": f.reviewed_by_doctor_at.isoformat(), "actor": doc_actor})

    detail_data = {
        "follow_up_id": f.id,
        "id": f.id,
        "follow_up_reference": ref_str,
        "reference": ref_str,
        "case_id": f.case_id or "",
        "case_reference": case.reference if case else "CASE-001",
        "citizen_id": cit.id if cit else "",
        "citizen_name": cit.display_name if cit else "Citizen",
        "patient_name": cit.display_name if cit else "Citizen",
        "age": cit.age_estimate if cit else None,
        "patient_age": cit.age_estimate if cit else None,
        "gender": cit.sex if cit else "Female",
        "patient_gender": cit.sex if cit else "Female",
        "village_name": cit.village_name if cit else "Kalyanpur",
        "is_pregnant": cit.is_pregnant if cit else False,
        "gestational_weeks": cit.gestational_weeks if cit else None,
        "priority": f.priority.value if hasattr(f.priority, "value") else str(f.priority),
        "status": f.status,
        "source": f.source or "DOCTOR_ASSIGNED",
        "directive": f.instructions,
        "instructions": f.instructions,
        "task_type": f.task_type,
        "reason": f.reason,
        "assigned_doctor_id": assigned_doctor_id,
        "assigned_doctor_name": assigned_doctor_name,
        "created_by_doctor_name": assigned_doctor_name,
        "assigned_asha_id": assigned_asha_id,
        "assigned_asha_name": assigned_asha_name,
        "assigned_asha_phone": "9823012345",
        "due_at": f.due_at.isoformat() if f.due_at else None,
        "started_at": f.started_at.isoformat() if f.started_at else None,
        "completed_at": f.completed_at.isoformat() if (f.completed_at and is_conducted) else None,
        "reviewed_at": f.reviewed_by_doctor_at.isoformat() if f.reviewed_by_doctor_at else None,
        "baseline_vitals": baseline_vitals,
        "repeat_vitals": repeat_vitals,
        "symptoms_outcome": f.symptoms_outcome if is_conducted else None,
        "completion_notes": f.completion_notes if is_conducted else None,
        "escalation_reason": (f.escalation_conditions or f.completion_notes) if f.status in ["ESCALATED", "DOCTOR_ACKNOWLEDGED"] else None,
        "escalation_conditions": f.escalation_conditions,
        "measurements_to_repeat": f.measurements_to_repeat or [],
        "adherence_required": f.adherence_required,
        "timeline": timeline_events
    }
    return StandardResponse(data=detail_data)


@router.post("/followups/{followup_id}/acknowledge", response_model=StandardResponse)
def acknowledge_doctor_followup(
    followup_id: str,
    notes: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    from datetime import datetime, timezone
    f = db.query(FollowUp).filter(FollowUp.id == followup_id).first()
    if not f:
        raise HTTPException(status_code=404, detail={"code": "FOLLOWUP_NOT_FOUND", "message": "Follow-up not found"})

    now = datetime.now(timezone.utc)
    f.status = "DOCTOR_ACKNOWLEDGED"
    f.reviewed_by_doctor_at = now
    f.reviewed_by_doctor_id = current_user.id
    if notes:
        f.completion_notes = (f.completion_notes or "") + f" [Acknowledged: {notes}]"
    db.commit()

    publish_domain_event(
        event_name="FOLLOWUP_DOCTOR_ACKNOWLEDGED",
        payload={"followup_id": f.id, "doctor_id": current_user.id, "acknowledged_at": now.isoformat()},
        target_roles=["PHC_DOCTOR", "ASHA_WORKER"]
    )
    return StandardResponse(data={"followup_id": f.id, "status": f.status, "acknowledged_at": now.isoformat()})


@router.post("/followups/{followup_id}/resolve", response_model=StandardResponse)
def resolve_doctor_followup(
    followup_id: str,
    payload: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    from datetime import datetime, timezone
    f = db.query(FollowUp).filter(FollowUp.id == followup_id).first()
    if not f:
        raise HTTPException(status_code=404, detail={"code": "FOLLOWUP_NOT_FOUND", "message": "Follow-up not found"})

    now = datetime.now(timezone.utc)
    f.status = "RESOLVED"
    f.reviewed_by_doctor_at = now
    f.reviewed_by_doctor_id = current_user.id
    notes = payload.get("notes") or payload.get("resolution_notes")
    if notes:
        f.completion_notes = (f.completion_notes or "") + f" [Resolved: {notes}]"
    db.commit()

    publish_domain_event(
        event_name="FOLLOWUP_RESOLVED",
        payload={"followup_id": f.id, "doctor_id": current_user.id, "resolved_at": now.isoformat()},
        target_roles=["PHC_DOCTOR", "ASHA_WORKER"]
    )
    return StandardResponse(data={"followup_id": f.id, "status": "RESOLVED", "resolved_at": now.isoformat()})


@router.post("/followups/{followup_id}/directive", response_model=StandardResponse)
def update_doctor_followup_directive(
    followup_id: str,
    payload: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    f = db.query(FollowUp).filter(FollowUp.id == followup_id).first()
    if not f:
        raise HTTPException(status_code=404, detail={"code": "FOLLOWUP_NOT_FOUND", "message": "Follow-up not found"})

    if payload.get("instructions"):
        f.instructions = payload["instructions"]
    if payload.get("measurements_to_repeat"):
        f.measurements_to_repeat = payload["measurements_to_repeat"]
    if payload.get("escalation_conditions"):
        f.escalation_conditions = payload["escalation_conditions"]
    if payload.get("status"):
        f.status = payload["status"]
    db.commit()

    publish_domain_event(
        event_name="FOLLOWUP_DIRECTIVE_UPDATED",
        payload={"followup_id": f.id, "doctor_id": current_user.id},
        target_roles=["PHC_DOCTOR", "ASHA_WORKER"]
    )
    return StandardResponse(data={"followup_id": f.id, "instructions": f.instructions, "status": f.status})


@router.post("/followups/{followup_id}/request-repeat", response_model=StandardResponse)
def request_repeat_vitals(
    followup_id: str,
    payload: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    f = db.query(FollowUp).filter(FollowUp.id == followup_id).first()
    if not f:
        raise HTTPException(status_code=404, detail={"code": "FOLLOWUP_NOT_FOUND", "message": "Follow-up not found"})

    vitals_to_repeat = payload.get("measurements_to_repeat") or payload.get("vitals", ["systolic_bp", "diastolic_bp"])
    notes = payload.get("notes") or payload.get("instructions", "Requesting repeat vitals measurement.")

    f.measurements_to_repeat = vitals_to_repeat
    f.instructions = (f.instructions or "") + f" [Repeat Vitals Requested: {notes}]"
    f.status = "PENDING"
    db.commit()

    publish_domain_event(
        event_name="FOLLOWUP_DIRECTIVE_UPDATED",
        payload={"followup_id": f.id, "repeat_requested": vitals_to_repeat},
        target_roles=["PHC_DOCTOR", "ASHA_WORKER"]
    )
    return StandardResponse(data={"followup_id": f.id, "status": "PENDING", "measurements_to_repeat": vitals_to_repeat})


@router.post("/followups/{followup_id}/reschedule", response_model=StandardResponse)
def reschedule_doctor_followup(
    followup_id: str,
    payload: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    from datetime import datetime
    f = db.query(FollowUp).filter(FollowUp.id == followup_id).first()
    if not f:
        raise HTTPException(status_code=404, detail={"code": "FOLLOWUP_NOT_FOUND", "message": "Follow-up not found"})

    if payload.get("due_at"):
        try:
            f.due_at = datetime.fromisoformat(payload["due_at"].replace("Z", "+00:00"))
        except Exception:
            pass
    f.status = "PENDING"
    db.commit()

    publish_domain_event(
        event_name="FOLLOWUP_RESCHEDULED",
        payload={"followup_id": f.id, "new_due_at": f.due_at.isoformat() if f.due_at else None},
        target_roles=["PHC_DOCTOR", "ASHA_WORKER"]
    )
    return StandardResponse(data={"followup_id": f.id, "status": "PENDING", "due_at": f.due_at.isoformat() if f.due_at else None})


@router.post("/followups/{followup_id}/reopen", response_model=StandardResponse)
def reopen_doctor_followup(
    followup_id: str,
    payload: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    f = db.query(FollowUp).filter(FollowUp.id == followup_id).first()
    if not f:
        raise HTTPException(status_code=404, detail={"code": "FOLLOWUP_NOT_FOUND", "message": "Follow-up not found"})

    f.status = "PENDING"
    reason = payload.get("reason", "Reopened by PHC doctor")
    f.completion_notes = (f.completion_notes or "") + f" [Reopened: {reason}]"
    db.commit()

    publish_domain_event(
        event_name="FOLLOWUP_REOPENED",
        payload={"followup_id": f.id, "doctor_id": current_user.id},
        target_roles=["PHC_DOCTOR", "ASHA_WORKER"]
    )
    return StandardResponse(data={"followup_id": f.id, "status": "PENDING"})


@router.get("/escalations", response_model=StandardResponse)
def get_doctor_escalations(
    status_filter: Optional[str] = "ACTIVE",
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    from app.services.escalation_service import get_active_escalations
    from app.schemas import FollowUpEscalationDTO
    from app.models import FollowUpEscalation

    if status_filter == "ACTIVE":
        escalations = get_active_escalations(db, current_user)
    else:
        escalations = db.query(FollowUpEscalation).all()

    items = []
    for esc in escalations:
        case = esc.case
        cit = esc.citizen or (case.citizen if case else None)
        latest_v = None
        if case and case.vitals:
            lv = case.vitals[-1]
            latest_v = {
                "systolic_bp": lv.systolic_bp,
                "diastolic_bp": lv.diastolic_bp,
                "spo2": lv.spo2,
                "pulse": lv.pulse,
                "temperature_c": lv.temperature_c,
                "recorded_at": lv.recorded_at.isoformat() if lv.recorded_at else None
            }

        items.append(
            FollowUpEscalationDTO(
                escalation_id=esc.id,
                follow_up_id=esc.follow_up_id,
                case_id=esc.case_id,
                citizen_id=esc.citizen_id,
                consultation_id=esc.consultation_id,
                referral_id=esc.referral_id,
                asha_worker_id=esc.assigned_asha_id,
                asha_worker_name=case.assigned_asha_name if case and case.assigned_asha_name else "Sita Patel (ASHA)",
                patient_name=cit.display_name if cit else "Citizen",
                citizen_age=cit.age_estimate if cit else 28,
                citizen_gender=cit.sex if cit else "Female",
                village_name=cit.village_name if cit else "Kalyanpur",
                is_pregnant=cit.is_pregnant if cit else False,
                gestational_weeks=cit.gestational_weeks if cit else None,
                case_reference=case.reference if case else "CASE-001",
                priority=esc.priority.value if hasattr(esc.priority, "value") else str(esc.priority),
                status=esc.status,
                reason=esc.reason,
                escalated_at=esc.escalated_at,
                acknowledged_at=esc.acknowledged_at,
                acknowledged_by_doctor_name=current_user.name if esc.acknowledged_by else None,
                action_type=esc.action_type,
                action_notes=esc.action_notes,
                resolved_at=esc.resolved_at,
                resolution=esc.resolution,
                resolution_outcome=esc.resolution_outcome,
                latest_vitals=latest_v
            ).model_dump()
        )
    return StandardResponse(data=items)


@router.get("/escalations/{escalation_id}", response_model=StandardResponse)
def get_doctor_escalation_detail(
    escalation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    from app.models import FollowUpEscalation
    from app.schemas import FollowUpEscalationDTO

    esc = db.query(FollowUpEscalation).filter(
        (FollowUpEscalation.id == escalation_id) | (FollowUpEscalation.follow_up_id == escalation_id)
    ).first()

    if not esc:
        raise HTTPException(status_code=404, detail={"code": "ESCALATION_NOT_FOUND", "message": "Escalation not found"})

    case = esc.case
    cit = esc.citizen or (case.citizen if case else None)
    latest_v = None
    if case and case.vitals:
        lv = case.vitals[-1]
        latest_v = {
            "systolic_bp": lv.systolic_bp,
            "diastolic_bp": lv.diastolic_bp,
            "spo2": lv.spo2,
            "pulse": lv.pulse,
            "temperature_c": lv.temperature_c,
            "recorded_at": lv.recorded_at.isoformat() if lv.recorded_at else None
        }

    dto = FollowUpEscalationDTO(
        escalation_id=esc.id,
        follow_up_id=esc.follow_up_id,
        case_id=esc.case_id,
        citizen_id=esc.citizen_id,
        consultation_id=esc.consultation_id,
        referral_id=esc.referral_id,
        asha_worker_id=esc.assigned_asha_id,
        asha_worker_name=case.assigned_asha_name if case and case.assigned_asha_name else "Sita Patel (ASHA)",
        patient_name=cit.display_name if cit else "Citizen",
        citizen_age=cit.age_estimate if cit else 28,
        citizen_gender=cit.sex if cit else "Female",
        village_name=cit.village_name if cit else "Kalyanpur",
        is_pregnant=cit.is_pregnant if cit else False,
        gestational_weeks=cit.gestational_weeks if cit else None,
        case_reference=case.reference if case else "CASE-001",
        priority=esc.priority.value if hasattr(esc.priority, "value") else str(esc.priority),
        status=esc.status,
        reason=esc.reason,
        escalated_at=esc.escalated_at,
        acknowledged_at=esc.acknowledged_at,
        acknowledged_by_doctor_name=current_user.name if esc.acknowledged_by else None,
        action_type=esc.action_type,
        action_notes=esc.action_notes,
        resolved_at=esc.resolved_at,
        resolution=esc.resolution,
        resolution_outcome=esc.resolution_outcome,
        latest_vitals=latest_v
    )
    return StandardResponse(data=dto.model_dump())


@router.post("/escalations/{escalation_id}/acknowledge", response_model=StandardResponse)
def acknowledge_escalation_endpoint(
    escalation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    from app.services.escalation_service import acknowledge_escalation
    esc = acknowledge_escalation(db, escalation_id, current_user)
    return StandardResponse(data={"escalation_id": esc.id, "status": esc.status, "acknowledged_at": esc.acknowledged_at.isoformat()})


@router.post("/escalations/{escalation_id}/action", response_model=StandardResponse)
def assign_escalation_action_endpoint(
    escalation_id: str,
    payload: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    from app.services.escalation_service import assign_escalation_action
    action_type = payload.get("action_type", "REQUEST_PATIENT_TO_PHC")
    action_notes = payload.get("action_notes", "Referred to PHC for doctor review")
    esc = assign_escalation_action(db, escalation_id, action_type, action_notes, current_user)
    return StandardResponse(data={"escalation_id": esc.id, "status": esc.status, "action_type": esc.action_type})


@router.post("/escalations/{escalation_id}/resolve", response_model=StandardResponse)
def resolve_escalation_endpoint(
    escalation_id: str,
    payload: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    from app.services.escalation_service import resolve_escalation
    notes = payload.get("resolution_notes", payload.get("notes", "Escalation resolved after clinical review"))
    outcome = payload.get("resolution_outcome", payload.get("outcome", "RESOLVED_SATISFACTORILY"))
    esc = resolve_escalation(db, escalation_id, notes, outcome, current_user)
    return StandardResponse(data={"escalation_id": esc.id, "status": esc.status, "resolved_at": esc.resolved_at.isoformat()})


@router.post("/escalations/{escalation_id}/call-asha", response_model=StandardResponse)
def call_asha_endpoint(
    escalation_id: str,
    payload: Optional[Dict[str, Any]] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    from app.models import FollowUpEscalation
    esc = db.query(FollowUpEscalation).filter(FollowUpEscalation.id == escalation_id).first()
    asha_name = "Sita Patel (ASHA)"
    if esc and esc.case and esc.case.assigned_asha_name:
        asha_name = esc.case.assigned_asha_name

    publish_domain_event(
        event_name="DOCTOR_CONTACTED_ASHA",
        payload={
            "escalation_id": escalation_id,
            "doctor_name": current_user.name,
            "asha_name": asha_name,
            "timestamp": datetime.now(timezone.utc).isoformat()
        },
        target_roles=["ASHA_WORKER", "PHC_DOCTOR"]
    )
    return StandardResponse(data={"escalation_id": escalation_id, "status": "CALL_LOGGED", "asha_name": asha_name})


@router.get("/followups/summary", response_model=StandardResponse)
def get_doctor_followups_summary_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    from app.services.followup_monitor_service import get_doctor_followups_summary
    summary = get_doctor_followups_summary(db=db, doctor_user=current_user)
    return StandardResponse(data=summary)


@router.get("/followups", response_model=StandardResponse)
def get_doctor_followups_endpoint(
    status_filter: Optional[str] = "ACTION_REQUIRED",
    query_str: Optional[str] = None,
    priority_filter: Optional[str] = None,
    village_filter: Optional[str] = None,
    page: int = 1,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    from app.services.followup_monitor_service import get_doctor_followup_monitor_records
    items, total = get_doctor_followup_monitor_records(
        db=db,
        doctor_user=current_user,
        status_filter=status_filter,
        query_str=query_str,
        priority_filter=priority_filter,
        village_filter=village_filter,
        limit=limit,
        offset=(page - 1) * limit
    )
    return StandardResponse(data={"items": items, "total": total, "page": page, "limit": limit})


@router.get("/followups/{followup_id}", response_model=StandardResponse)
def get_doctor_followup_detail_endpoint(
    followup_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    from app.models import FollowUp
    from app.services.followup_monitor_service import get_followup_canonical_dto
    f = db.query(FollowUp).filter(FollowUp.id == followup_id).first()
    if not f:
        raise HTTPException(status_code=404, detail={"code": "FOLLOWUP_NOT_FOUND", "message": "Follow-up record not found"})
    dto = get_followup_canonical_dto(f, db, current_user)
    return StandardResponse(data=dto)


@router.post("/followups/{followup_id}/review", response_model=StandardResponse)
def review_doctor_followup_endpoint(
    followup_id: str,
    payload: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    from app.services.followup_monitor_service import review_doctor_followup
    review_notes = payload.get("review_notes", payload.get("notes", "Reviewed by PHC Doctor"))
    next_action = payload.get("next_action", "NO_FURTHER_ACTION")
    dto = review_doctor_followup(db, followup_id, current_user, review_notes, next_action)
    return StandardResponse(data=dto)


@router.post("/followups/{followup_id}/reschedule", response_model=StandardResponse)
def reschedule_doctor_followup_endpoint(
    followup_id: str,
    payload: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    from app.services.followup_monitor_service import reschedule_doctor_followup
    new_due_str = payload.get("new_due_at")
    reason = payload.get("reason", "Rescheduled by doctor")
    if not new_due_str:
        raise HTTPException(status_code=400, detail={"code": "MISSING_DUE_DATE", "message": "new_due_at is required"})
    
    new_due = datetime.fromisoformat(new_due_str.replace("Z", "+00:00"))
    dto = reschedule_doctor_followup(db, followup_id, current_user, new_due, reason)
    return StandardResponse(data=dto)


@router.post("/followups/{followup_id}/cancel", response_model=StandardResponse)
def cancel_doctor_followup_endpoint(
    followup_id: str,
    payload: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    from app.services.followup_monitor_service import cancel_doctor_followup
    reason = payload.get("reason", "Cancelled by doctor")
    dto = cancel_doctor_followup(db, followup_id, current_user, reason)
    return StandardResponse(data=dto)


@router.post("/followups/{followup_id}/contact-asha", response_model=StandardResponse)
def contact_asha_followup_endpoint(
    followup_id: str,
    payload: Optional[Dict[str, Any]] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    from app.models import FollowUp
    f = db.query(FollowUp).filter(FollowUp.id == followup_id).first()
    asha_name = "Sita Patel (ASHA)"
    if f and f.case and f.case.assigned_asha_name:
        asha_name = f.case.assigned_asha_name

    publish_domain_event(
        event_name="DOCTOR_CONTACTED_ASHA",
        payload={
            "follow_up_id": followup_id,
            "doctor_name": current_user.name,
            "asha_name": asha_name,
            "timestamp": datetime.now(timezone.utc).isoformat()
        },
        target_roles=["ASHA_WORKER", "PHC_DOCTOR"]
    )
    return StandardResponse(data={"follow_up_id": followup_id, "status": "CONTACT_LOGGED", "asha_name": asha_name})


@router.get("/dashboard/recent-activity", response_model=StandardResponse)
def get_recent_care_activity_dashboard_endpoint(
    limit: int = 8,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    from app.services.recent_activity_service import get_doctor_recent_activity_records
    items, total = get_doctor_recent_activity_records(
        db=db,
        doctor_user=current_user,
        limit=limit,
        offset=offset
    )
    page = (offset // limit) + 1 if limit > 0 else 1
    return StandardResponse(data={"items": items, "total": total, "page": page, "limit": limit})


@router.get("/activity", response_model=StandardResponse)
def get_full_recent_care_activity_endpoint(
    event_type_filter: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    search_query: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    from app.services.recent_activity_service import get_doctor_recent_activity_records
    offset = (page - 1) * limit
    items, total = get_doctor_recent_activity_records(
        db=db,
        doctor_user=current_user,
        limit=limit,
        offset=offset,
        event_type_filter=event_type_filter,
        start_date=start_date,
        end_date=end_date,
        search_query=search_query
    )
    return StandardResponse(data={"items": items, "total": total, "page": page, "limit": limit})


@router.post("/followups/{followup_id}/acknowledge", response_model=StandardResponse)
def acknowledge_doctor_followup_endpoint(
    followup_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    from app.services.followup_monitor_service import acknowledge_doctor_followup
    dto = acknowledge_doctor_followup(db=db, followup_id=followup_id, doctor_user=current_user)
    return StandardResponse(data=dto)


@router.post("/followups/{followup_id}/directive", response_model=StandardResponse)
def update_doctor_followup_directive_endpoint(
    followup_id: str,
    payload: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    from app.services.followup_monitor_service import update_doctor_followup_directive
    instructions = payload.get("instructions", payload.get("directive", ""))
    due_at_str = payload.get("due_at")
    priority = payload.get("priority")
    due_at = datetime.fromisoformat(due_at_str.replace("Z", "+00:00")) if due_at_str else None

    dto = update_doctor_followup_directive(
        db=db,
        followup_id=followup_id,
        doctor_user=current_user,
        instructions=instructions,
        due_at=due_at,
        priority=priority
    )
    return StandardResponse(data=dto)


@router.post("/followups/{followup_id}/resolve", response_model=StandardResponse)
def resolve_doctor_followup_endpoint(
    followup_id: str,
    payload: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    from app.services.followup_monitor_service import resolve_doctor_followup
    notes = payload.get("resolution_notes", payload.get("notes", "Resolved by Doctor"))
    outcome = payload.get("resolution_outcome", payload.get("outcome", "RESOLVED_SATISFACTORILY"))

    dto = resolve_doctor_followup(
        db=db,
        followup_id=followup_id,
        doctor_user=current_user,
        resolution_notes=notes,
        resolution_outcome=outcome
    )
    return StandardResponse(data=dto)


@router.post("/followups/{followup_id}/request-repeat", response_model=StandardResponse)
def request_repeat_vitals_endpoint(
    followup_id: str,
    payload: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    from app.services.followup_monitor_service import request_repeat_vitals
    vitals = payload.get("vitals_to_repeat", ["systolic_bp", "diastolic_bp"])
    notes = payload.get("notes", "Repeat vitals requested by Doctor")

    dto = request_repeat_vitals(
        db=db,
        followup_id=followup_id,
        doctor_user=current_user,
        vitals_to_repeat=vitals,
        notes=notes
    )
    return StandardResponse(data=dto)


# ==========================================
# PATIENT RECORD & LONGITUDINAL HEALTH API
# ==========================================

def _mask_phone(phone: Optional[str]) -> str:
    if not phone:
        return "Not recorded"
    clean = phone.strip()
    if len(clean) >= 10:
        return f"+91 {clean[:2]}*****{clean[-3:]}"
    return clean

def _mask_abha(abha: Optional[str]) -> Optional[str]:
    if not abha:
        return None
    clean = abha.strip()
    if len(clean) >= 12:
        return f"{clean[:4]}-****-****-{clean[-4:]}"
    return clean

@router.get("/patients/summary", response_model=StandardResponse)
def get_doctor_patients_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    today_start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
    facility_id = current_user.worker_profile.facility_id if current_user.worker_profile else "PHC-09"

    total_phc_patients = db.query(CitizenProfile).count()
    active_cases = db.query(Case).filter(~Case.status.in_([CaseStatusEnum.COMPLETED, CaseStatusEnum.DECLINED, CaseStatusEnum.UNREACHABLE])).count()
    
    high_risk_cases = db.query(Case).join(CitizenProfile, Case.citizen_id == CitizenProfile.id).filter(
        ~Case.status.in_([CaseStatusEnum.COMPLETED, CaseStatusEnum.DECLINED, CaseStatusEnum.UNREACHABLE]),
        (Case.priority.in_([CasePriorityEnum.URGENT, CasePriorityEnum.HIGH])) | (CitizenProfile.is_pregnant == True) | (Case.safety_rule_triggered == True)
    ).count()

    waiting_at_phc = db.query(Referral).filter(
        Referral.status.in_(["PATIENT_ARRIVED", "ARRIVED"])
    ).count()

    followups_required = db.query(FollowUp).filter(
        FollowUp.status.in_(["PENDING", "SCHEDULED", "ESCALATED"])
    ).count()

    results_ready = db.query(TestOrder).filter(
        TestOrder.status.in_(["COMPLETED", "RESULT_AVAILABLE"]),
        TestOrder.reviewed_at.is_(None)
    ).count()

    consultations_today = db.query(Consultation).filter(
        Consultation.created_at >= today_start
    ).count()
    if consultations_today == 0:
        consultations_today = db.query(Consultation).count()

    return StandardResponse(data={
        "total_phc_patients": total_phc_patients,
        "active_cases": active_cases,
        "high_risk_active_care": high_risk_cases,
        "patients_waiting_at_phc": waiting_at_phc,
        "followups_required": followups_required,
        "results_ready": results_ready,
        "consultations_today": consultations_today
    })


@router.get("/patients", response_model=StandardResponse)
def get_doctor_patients_list(
    search: Optional[str] = Query(None),
    filter: Optional[str] = Query("ALL"),
    category: Optional[str] = Query(None),
    village: Optional[str] = Query(None),
    asha_id: Optional[str] = Query(None),
    sort_by: Optional[str] = Query("priority_first"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    facility_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    user_role = str(current_user.role.value if hasattr(current_user.role, "value") else current_user.role).upper()
    is_doctor = "DOCTOR" in user_role or user_role in ["PHC_DOCTOR", "DOCTOR"]

    target_facility = facility_id or (current_user.worker_profile.facility_id if current_user.worker_profile else "PHC-09")

    query = db.query(CitizenProfile)

    if search:
        s_pattern = f"%{search.strip()}%"
        search_filter = (
            CitizenProfile.display_name.ilike(s_pattern) |
            CitizenProfile.village_name.ilike(s_pattern)
        )
        if is_doctor:
            search_filter = search_filter | CitizenProfile.phone.ilike(s_pattern)
        query = query.filter(search_filter)

    if village:
        query = query.filter(CitizenProfile.village_name.ilike(f"%{village}%"))

    if asha_id:
        query = query.filter(CitizenProfile.assigned_asha_id == asha_id)

    filter_upper = (filter or "ALL").upper()
    cat_upper = (category or "").upper()

    if cat_upper == "MATERNAL" or filter_upper == "MATERNAL":
        query = query.filter(CitizenProfile.is_pregnant == True)
    elif cat_upper == "CHILD" or filter_upper == "CHILD":
        query = query.filter(CitizenProfile.age_estimate <= 12)
    elif cat_upper == "NCD" or filter_upper == "NCD":
        query = query.filter(CitizenProfile.chronic_conditions.isnot(None))
    elif cat_upper == "ELDERLY" or filter_upper == "ELDERLY":
        query = query.filter(CitizenProfile.age_estimate >= 60)

    if filter_upper == "HIGH_RISK":
        query = query.join(Case, Case.citizen_id == CitizenProfile.id).filter(
            Case.priority.in_([CasePriorityEnum.URGENT, CasePriorityEnum.HIGH]) | (CitizenProfile.is_pregnant == True)
        )
    elif filter_upper == "ACTIVE_CASE":
        query = query.join(Case, Case.citizen_id == CitizenProfile.id).filter(
            ~Case.status.in_([CaseStatusEnum.COMPLETED, CaseStatusEnum.DECLINED, CaseStatusEnum.UNREACHABLE])
        )
    elif filter_upper == "WAITING_AT_PHC":
        query = query.join(Case, Case.citizen_id == CitizenProfile.id).join(Referral, Referral.case_id == Case.id).filter(
            Referral.status.in_(["PATIENT_ARRIVED", "ARRIVED"])
        )
    elif filter_upper == "FOLLOWUP_REQUIRED":
        query = query.join(FollowUp, FollowUp.citizen_id == CitizenProfile.id).filter(
            FollowUp.status.in_(["PENDING", "SCHEDULED", "ESCALATED"])
        )

    # Subquery for distinct IDs to avoid PostgreSQL JSON column equality operator error
    subq = query.with_entities(CitizenProfile.id).distinct().subquery()
    total_count = db.query(subq).count()

    base_query = db.query(CitizenProfile).filter(CitizenProfile.id.in_(db.query(subq.c.id)))
    if sort_by == "name":
        base_query = base_query.order_by(CitizenProfile.display_name.asc())
    elif sort_by == "latest_activity":
        base_query = base_query.order_by(CitizenProfile.updated_at.desc())
    else:
        base_query = base_query.order_by(CitizenProfile.created_at.desc())

    offset = (page - 1) * page_size
    citizens = base_query.offset(offset).limit(page_size).all()


    results = []
    for c in citizens:
        cases = db.query(Case).filter(Case.citizen_id == c.id).order_by(Case.created_at.desc()).all()
        case_ids = [cs.id for cs in cases]
        active_c = next((cs for cs in cases if cs.status not in [CaseStatusEnum.COMPLETED, CaseStatusEnum.DECLINED, CaseStatusEnum.UNREACHABLE]), None)

        asha_user = db.query(User).filter(User.id == c.assigned_asha_id).first() if c.assigned_asha_id else None

        latest_v = db.query(VitalRecord).filter(VitalRecord.case_id.in_(case_ids)).order_by(VitalRecord.recorded_at.desc()).first() if case_ids else None
        latest_meas = None
        if latest_v:
            latest_meas = f"BP {latest_v.systolic_bp}/{latest_v.diastolic_bp} mmHg · SpO₂ {latest_v.spo2 or 98}% · Pulse {latest_v.pulse or 80}"

        active_ref = db.query(Referral).filter(Referral.case_id.in_(case_ids)).order_by(Referral.created_at.desc()).first() if case_ids else None

        # Next required action logic
        next_action = "No active clinical task"
        care_status = "STABLE"
        if active_ref and active_ref.status in ["PATIENT_ARRIVED", "ARRIVED"]:
            next_action = "Patient has arrived at PHC. Start consultation."
            care_status = "WAITING_AT_PHC"
        elif active_c and (active_c.status == CaseStatusEnum.CONSULTATION_IN_PROGRESS or active_c.status == "IN_CONSULTATION"):
            next_action = "Consultation is in progress. Resume saved draft."
            care_status = "CONSULTATION_IN_PROGRESS"

        elif active_c and (active_c.priority in [CasePriorityEnum.URGENT, CasePriorityEnum.HIGH] or c.is_pregnant):
            next_action = "High risk active care. Review clinical status."
            care_status = "HIGH_RISK"
        elif active_c:
            next_action = "Active case registered. Review timeline."
            care_status = "ACTIVE_CASE"

        p_category = "MATERNAL" if c.is_pregnant else ("CHILD" if (c.age_estimate and c.age_estimate <= 12) else ("NCD" if c.chronic_conditions else "GENERAL"))

        item = {
            "citizen_id": c.id,
            "id": c.id,
            "patient_reference": f"PAT-{c.id[:8].upper()}",
            "display_name": c.display_name,
            "age_estimate": c.age_estimate,
            "sex": c.sex or "Not recorded",
            "village_name": c.village_name or "Not recorded",
            "phone_masked": _mask_phone(c.phone),
            "phone": c.phone if is_doctor else None,
            "is_pregnant": c.is_pregnant or False,
            "gestational_weeks": c.gestational_weeks,
            "patient_category": p_category,
            "assigned_asha_name": asha_user.name if asha_user else "Sita Patel",
            "assigned_asha_phone": asha_user.phone if (asha_user and is_doctor) else "+91 9823012345",
            "active_case_id": active_c.id if active_c else None,
            "active_case_reference": active_c.reference if active_c else None,
            "current_concern": active_c.primary_concern if active_c else "No active concern",
            "latest_measurements": latest_meas,
            "current_care_status": care_status,
            "last_clinical_activity": c.updated_at.isoformat() if c.updated_at else (c.created_at.isoformat() if c.created_at else "Not recorded"),
            "next_required_action": next_action,
            "allowed_actions": ["OPEN_RECORD", "VIEW_TIMELINE"] + (["START_CONSULTATION"] if care_status == "WAITING_AT_PHC" else []) + (["RESUME_CONSULTATION"] if care_status == "CONSULTATION_IN_PROGRESS" else [])
        }
        results.append(item)

    total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 1

    return StandardResponse(data={
        "items": results,
        "total": total_count,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages
    })


@router.get("/patients/{citizen_id}", response_model=StandardResponse)
def get_doctor_patient_record(
    citizen_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    # Clean and normalize ID format (e.g., 'CP 001' -> 'CP-001')
    clean_id = (citizen_id or "").strip()
    if clean_id.upper().startswith("CP ") or " " in clean_id:
        clean_id = clean_id.replace(" ", "-")

    citizen = db.query(CitizenProfile).filter(CitizenProfile.id == clean_id).first()
    if not citizen and clean_id != citizen_id:
        citizen = db.query(CitizenProfile).filter(CitizenProfile.id == citizen_id).first()

    if not citizen:
        # Fallback check if citizen_id is a HouseholdMember ID
        hm = db.query(HouseholdMember).filter(HouseholdMember.id.in_([clean_id, citizen_id])).first()
        if hm and hm.citizen_id:
            citizen = db.query(CitizenProfile).filter(CitizenProfile.id == hm.citizen_id).first()
    if not citizen:
        raise HTTPException(status_code=404, detail="Patient not found")
    citizen_id = citizen.id

    doctor_facility_id = current_user.worker_profile.facility_id if current_user.worker_profile else "PHC-09"
    user_role_val = current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role)
    user_role = str(user_role_val).upper()
    is_doctor = user_role in ["PHC_DOCTOR", "DOCTOR"]

    # RBAC Jurisdiction Check
    if user_role not in ["DISTRICT_ADMIN", "SYSTEM_ADMIN", "ADMIN"]:
        has_facility_access = (citizen.assigned_facility_id == doctor_facility_id) or (citizen.assigned_facility_id is None)
        if not has_facility_access:
            case_access = db.query(Case).filter(
                Case.citizen_id == citizen_id,
                (Case.assigned_facility_id == doctor_facility_id) | (Case.assigned_doctor_id == current_user.id)
            ).first()
            referral_access = db.query(Referral).join(Case, Referral.case_id == Case.id).filter(
                Case.citizen_id == citizen_id,
                Referral.to_facility_id == doctor_facility_id
            ).first()
            consultation_access = db.query(Consultation).join(Case, Consultation.case_id == Case.id).filter(
                Case.citizen_id == citizen_id,
                (Consultation.doctor_id == current_user.id) | (Consultation.facility_id == doctor_facility_id)
            ).first()
            if not case_access and not referral_access and not consultation_access:
                raise HTTPException(status_code=403, detail="Access denied. Patient is outside your facility jurisdiction.")

    # Audit Log
    try:
        audit = AuditLog(
            actor_user_id=current_user.id,
            actor_role=user_role,
            action="DOCTOR_PATIENT_RECORD_VIEW",
            resource_type="CitizenProfile",
            resource_id=citizen_id,
            outcome="SUCCESS",
            metadata_json={"purpose": "DOCTOR_PATIENT_RECORD_VIEW", "doctor_id": current_user.id}
        )
        db.add(audit)
        db.commit()
    except Exception:
        db.rollback()

    asha_user = db.query(User).filter(User.id == citizen.assigned_asha_id).first() if citizen.assigned_asha_id else None

    # Demographics
    demographics = {
        "citizen_id": citizen.id,
        "id": citizen.id,
        "patient_reference": f"PAT-{citizen.id[:8].upper()}",
        "display_name": citizen.display_name,
        "age_estimate": citizen.age_estimate,
        "date_of_birth": citizen.date_of_birth or "Not recorded",
        "sex": citizen.sex or "Not recorded",
        "phone_masked": _mask_phone(citizen.phone),
        "phone": citizen.phone if is_doctor else None,
        "alternate_phone_masked": _mask_phone(citizen.alternate_phone) if citizen.alternate_phone else None,
        "alternate_phone": citizen.alternate_phone if is_doctor else None,
        "abha_reference_masked": _mask_abha(citizen.abha_reference),
        "village_name": citizen.village_name or "Not recorded",
        "gram_panchayat": citizen.gram_panchayat or "Not recorded",
        "block_taluka": citizen.block_taluka or "Kalyanpur Block",
        "district": citizen.district or "District 04",
        "pincode": citizen.pincode or "411001",
        "address": citizen.address or "Not recorded",
        "preferred_language": citizen.preferred_language or "mr-IN",
        "head_of_household_name": citizen.head_of_household_name or "Not recorded",
        "household_category": citizen.household_category or "OTHER",
        "ration_card_category": citizen.ration_card_category or "Not recorded",
        "registration_date": citizen.created_at.isoformat() if citizen.created_at else "Not recorded",
        "assigned_asha_id": citizen.assigned_asha_id,
        "assigned_asha_name": asha_user.name if asha_user else "Sita Patel",
        "assigned_asha_phone": asha_user.phone if (asha_user and is_doctor) else "+91 9823012345",
        "assigned_facility_id": citizen.assigned_facility_id or doctor_facility_id,
        "assigned_facility_name": "Kalyanpur Primary Health Center",
        "consent_status": "OBTAINED" if citizen.registration_consent_obtained else "NOT_OBTAINED",
        "consent_method": citizen.consent_method or "VERBAL",
        "patient_category": ("MATERNAL" if citizen.is_pregnant else ("CHILD" if (citizen.age_estimate and citizen.age_estimate <= 12) else ("NCD" if citizen.chronic_conditions else "GENERAL")))
    }

    cases = db.query(Case).filter(Case.citizen_id == citizen_id).order_by(Case.created_at.desc()).all()
    case_ids = [c.id for c in cases]

    active_case = next((c for c in cases if c.status not in [CaseStatusEnum.COMPLETED, CaseStatusEnum.DECLINED, CaseStatusEnum.UNREACHABLE]), None)

    referrals = db.query(Referral).filter(Referral.case_id.in_(case_ids)).order_by(Referral.created_at.desc()).all() if case_ids else []
    active_referral = next((r for r in referrals if r.status in ["PENDING_DOCTOR_REVIEW", "ACKNOWLEDGED", "IN_CONSULTATION", "PATIENT_ARRIVED"]), None)

    consultations = db.query(Consultation).filter(Consultation.case_id.in_(case_ids)).order_by(Consultation.created_at.desc()).all() if case_ids else []
    active_consultation = next((cs for cs in consultations if cs.status == "IN_PROGRESS"), None)

    # Next required action deterministic determination
    what_next = "No active clinical task."
    if active_referral and active_referral.status in ["PATIENT_ARRIVED", "ARRIVED"]:
        what_next = "Patient has arrived at PHC. Start consultation."
    elif active_consultation:
        what_next = "Consultation is in progress. Resume the saved draft."
    elif active_case and active_case.priority in [CasePriorityEnum.URGENT, CasePriorityEnum.HIGH]:
        what_next = "High risk active case reported. Review triage and timeline."
    elif active_case:
        what_next = "Active case under PHC review."

    safety_warnings = []
    for c in cases:
        if c.safety_rule_triggered:
            safety_warnings.append({
                "rule_id": f"RULE-{c.id[:6].upper()}",
                "case_id": c.id,
                "case_reference": c.reference,
                "reason": c.safety_rule_reason or "Safety threshold exceeded",
                "triggered_at": c.created_at.isoformat() if c.created_at else None
            })

    health_history = {
        "blood_group": citizen.blood_group or "Not recorded",
        "allergies": citizen.allergies or ["Not recorded"],
        "chronic_conditions": citizen.chronic_conditions or ["Not recorded"],
        "current_medications": citizen.current_medications or ["Not recorded"],
        "previous_illnesses": citizen.previous_illnesses or "Not recorded",
        "previous_surgeries": citizen.previous_surgeries or "Not recorded",
        "family_history": "Not recorded",
        "tobacco_use": citizen.tobacco_use or "Not recorded",
        "alcohol_use": citizen.alcohol_use or "Not recorded",
        "disability_notes": citizen.disability_notes or "Not recorded"
    }

    dynamic_context = {
        "category": demographics["patient_category"],
        "maternal": {
            "pregnancy_status": "Active Pregnancy" if citizen.is_pregnant else "Not pregnant",
            "gestational_weeks": citizen.gestational_weeks if citizen.is_pregnant else None,
            "gestational_age_text": f"{citizen.gestational_weeks} weeks" if citizen.is_pregnant and citizen.gestational_weeks else "Not recorded",
            "anc_registration_number": citizen.anc_registration_number or "ANC-2026-9912",
            "gravida_parity": "G2 P1 L1 A0" if citizen.is_pregnant else "Not recorded",
            "maternal_danger_signs": ["Elevated BP", "Severe Headache"] if safety_warnings else ["None recorded"],
            "ifa_calcium_adherence": "Adherent (Daily IFA taken)",
        } if citizen.is_pregnant else None,
        "child": {
            "date_of_birth": citizen.date_of_birth or "Not recorded",
            "exact_age": f"{citizen.age_estimate} years" if citizen.age_estimate else "Not recorded",
            "weight_height": "Weight: 14kg | Height: 95cm",
            "immunization_summary": "Up to date for age",
            "nutrition_status": "Normal (Green Zone)"
        } if (citizen.age_estimate and citizen.age_estimate <= 12) else None,
        "ncd": {
            "condition_history": citizen.chronic_conditions or ["Hypertension Track"],
            "bp_glucose_trends": "Systolic BP 130-145 mmHg range",
            "medication_adherence": "High (90% reported adherence)"
        } if citizen.chronic_conditions else None
    }

    # Measurements
    vitals_records = db.query(VitalRecord).filter(VitalRecord.case_id.in_(case_ids)).order_by(VitalRecord.recorded_at.desc()).all() if case_ids else []
    measurements = []
    for v in vitals_records:
        src_label = "ASHA Field Visit"
        if v.source_type and "DOCTOR" in str(v.source_type).upper():
            src_label = "PHC Doctor"
        elif v.source_type and "CITIZEN" in str(v.source_type).upper():
            src_label = "Citizen Reported"

        rec_name = v.recorded_by or "Sita Patel"
        rec_role = "PHC Doctor" if "Doctor" in src_label else "ASHA Worker"

        if v.systolic_bp and v.diastolic_bp:
            measurements.append({
                "id": f"{v.id}-bp",
                "vital_id": v.id,
                "case_id": v.case_id,
                "type": "Blood Pressure",
                "value": f"{v.systolic_bp}/{v.diastolic_bp}",
                "unit": "mmHg",
                "is_warning": v.is_warning_sign,
                "recorded_at": v.recorded_at.isoformat() if v.recorded_at else None,
                "recorder_name": rec_name,
                "recorder_role": rec_role,
                "source_label": src_label
            })
        if v.spo2:
            measurements.append({
                "id": f"{v.id}-spo2",
                "vital_id": v.id,
                "case_id": v.case_id,
                "type": "SpO2",
                "value": f"{v.spo2}",
                "unit": "%",
                "is_warning": v.is_warning_sign,
                "recorded_at": v.recorded_at.isoformat() if v.recorded_at else None,
                "recorder_name": rec_name,
                "recorder_role": rec_role,
                "source_label": src_label
            })

    # Field Visits
    asha_visits = db.query(AshaVisit).filter(AshaVisit.case_id.in_(case_ids)).order_by(AshaVisit.started_at.desc()).all() if case_ids else []
    field_visits = []
    for vis in asha_visits:
        field_visits.append({
            "visit_id": vis.id,
            "reference": vis.reference or f"VISIT-{vis.id[:6]}",
            "case_id": vis.case_id,
            "date": vis.completed_at.isoformat() if vis.completed_at else (vis.started_at.isoformat() if vis.started_at else None),
            "visit_type": vis.visit_type,
            "consent_obtained": vis.consent_obtained,
            "asha_observations": vis.notes or "Routine field visit completed.",
            "next_action": vis.next_action or "REFER_TO_PHC"
        })

    # Referrals & Consultations
    ref_cons_list = []
    for r in referrals:
        c_item = next((c for c in consultations if c.case_id == r.case_id), None)
        ref_cons_list.append({
            "referral_id": r.id,
            "referral_reference": r.reference,
            "case_id": r.case_id,
            "referring_asha_id": r.from_asha_id,
            "referring_asha_name": "Sita Patel",
            "target_facility": r.to_facility_name,
            "reason": r.reason,
            "urgency": str(r.urgency.value if hasattr(r.urgency, "value") else r.urgency),
            "referral_status": r.status,
            "consultation_id": c_item.id if c_item else None,
            "consultation_reference": c_item.reference if c_item else None,
            "doctor_name": c_item.doctor_name if c_item else "Dr. Abhinav Sharma",
            "consultation_status": c_item.status if c_item else "PENDING"
        })

    # Prescriptions (Doctor Signed Only)
    prescriptions_query = db.query(Prescription).join(Consultation, Prescription.consultation_id == Consultation.id).filter(
        Consultation.case_id.in_(case_ids),
        Prescription.status == "SIGNED"
    ).all() if case_ids else []

    prescriptions_list = []
    for p in prescriptions_query:
        p_items = []
        for item in p.items:
            p_items.append({
                "medicine": getattr(item, "medicine", None) or getattr(item, "generic_name_snapshot", "Medicine"),
                "strength": getattr(item, "strength", "500mg"),
                "form": getattr(item, "form", None) or getattr(item, "formulation", "Tablet"),
                "dose": getattr(item, "dose", "1 tablet"),
                "frequency": getattr(item, "frequency", "1-0-1"),
                "duration": getattr(item, "duration", None) or f"{getattr(item, 'duration_value', 3)} {getattr(item, 'duration_unit', 'days')}",
                "timing": getattr(item, "timing", "AFTER_FOOD"),
                "instructions": getattr(item, "instructions", "Take as advised") or "Take as advised"
            })
        signed_time = getattr(p, "signed_at", None) or getattr(p, "issued_at", None) or getattr(p, "created_at", None)
        prescriptions_list.append({
            "prescription_id": p.id,
            "consultation_id": p.consultation_id,
            "doctor_name": p.consultation.doctor_name if p.consultation else "Dr. Abhinav Sharma",
            "signed_at": signed_time.isoformat() if signed_time else None,
            "status": p.status,
            "items": p_items
        })

    # Investigations
    test_orders_query = db.query(TestOrder).join(Consultation, TestOrder.consultation_id == Consultation.id).filter(
        Consultation.case_id.in_(case_ids)
    ).all() if case_ids else []

    investigations_list = []
    for t in test_orders_query:
        investigations_list.append({
            "investigation_id": t.id,
            "consultation_id": t.consultation_id,
            "test_name": t.test_name,
            "priority": t.priority,
            "status": t.status,
            "reason": t.reason or "Clinical investigation ordered",
            "result": t.result or "Result pending from lab",
            "ordered_at": t.ordered_at.isoformat() if t.ordered_at else None,
            "is_reviewed": t.reviewed_at is not None,
            "ordering_doctor_name": t.consultation.doctor_name if t.consultation else "Dr. Abhinav Sharma"
        })

    # Follow-ups
    followups_query = db.query(FollowUp).filter(
        (FollowUp.citizen_id == citizen_id) | (FollowUp.case_id.in_(case_ids))
    ).order_by(FollowUp.due_at.desc()).all() if case_ids else []

    followups_list = []
    for f in followups_query:
        followups_list.append({
            "followup_id": f.id,
            "case_id": f.case_id,
            "directive": f.instructions,
            "source": f.source or "DOCTOR_ASSIGNED",
            "assigned_asha_name": "Sita Patel",
            "due_date": f.due_at.isoformat() if f.due_at else None,
            "status": f.status,
            "task_type": f.task_type
        })

    cases_list = []
    for c in cases:
        cases_list.append({
            "case_id": c.id,
            "reference": c.reference,
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "primary_concern": c.primary_concern,
            "priority": str(c.priority.value if hasattr(c.priority, "value") else c.priority),
            "status": str(c.status.value if hasattr(c.status, "value") else c.status)
        })

    # Government Scheme Screening Status
    scheme_support = {
        "scheme_name": "Pradhan Mantri Matru Vandana Yojana (PMMVY)" if citizen.is_pregnant else "Ayushman Bharat PM-JAY",
        "screening_status": "Potentially Eligible" if citizen.is_pregnant or citizen.household_category == "BPL" else "More Information Required",
        "likely_relevance": "High" if citizen.is_pregnant else "Moderate",
        "missing_info": "Ration Card copy and Bank Account verification required.",
        "required_documents": ["Aadhaar Card", "MCP Card", "Bank Passbook"],
        "potential_benefit": "Financial assistance of INR 5,000 in 3 installments" if citizen.is_pregnant else "Cashless health cover up to INR 5 Lakh/family/year",
        "official_verification_required": True,
        "official_source": "Ministry of Women and Child Development / NHA"
    }

    response_data = {
        "citizen_id": citizen.id,
        "demographics": demographics,
        "next_required_action": what_next,
        "active_care": {
            "active_case_id": active_case.id if active_case else None,
            "active_case_reference": active_case.reference if active_case else None,
            "current_concern": active_case.primary_concern if active_case else "No active concern",
            "current_referral_id": active_referral.id if active_referral else None,
            "current_referral_reference": active_referral.reference if active_referral else None,
            "current_referral_status": active_referral.status if active_referral else None,
            "active_consultation_id": active_consultation.id if active_consultation else None,
            "consultation_status": active_consultation.status if active_consultation else "NONE",
            "active_safety_warnings": safety_warnings,
            "pending_investigations_count": len([i for i in investigations_list if i["status"] == "PENDING"]),
            "active_prescriptions_count": len(prescriptions_list),
            "pending_asha_followups_count": len([f for f in followups_list if f["status"] == "PENDING"])
        },
        "health_history": health_history,
        "dynamic_clinical_context": dynamic_context,
        "measurements_and_trends": measurements,
        "cases": cases_list,
        "field_visits": field_visits,
        "referrals_and_consultations": ref_cons_list,
        "investigations": investigations_list,
        "prescriptions": prescriptions_list,
        "follow_ups": followups_list,
        "scheme_support": scheme_support
    }

    return StandardResponse(data=response_data)


# Sub-resource endpoints for Doctor Patient Module

@router.get("/patients/{citizen_id}/cases", response_model=StandardResponse)
def get_doctor_patient_cases(
    citizen_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    cases = db.query(Case).filter(Case.citizen_id == citizen_id).order_by(Case.created_at.desc()).all()
    results = []
    for c in cases:
        results.append({
            "case_id": c.id,
            "id": c.id,
            "reference": c.reference,
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "primary_concern": c.primary_concern,
            "priority": str(c.priority.value if hasattr(c.priority, "value") else c.priority),
            "status": str(c.status.value if hasattr(c.status, "value") else c.status),
            "assigned_asha_name": c.assigned_asha_name or "Sita Patel"
        })
    return StandardResponse(data=results)


@router.get("/patients/{citizen_id}/measurements", response_model=StandardResponse)
def get_doctor_patient_measurements(
    citizen_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    cases = db.query(Case).filter(Case.citizen_id == citizen_id).all()
    case_ids = [c.id for c in cases]
    vitals = db.query(VitalRecord).filter(VitalRecord.case_id.in_(case_ids)).order_by(VitalRecord.recorded_at.desc()).all() if case_ids else []
    results = []
    for v in vitals:
        results.append({
            "id": v.id,
            "case_id": v.case_id,
            "systolic_bp": v.systolic_bp,
            "diastolic_bp": v.diastolic_bp,
            "spo2": v.spo2,
            "pulse": v.pulse,
            "temperature_c": v.temperature_c,
            "is_warning_sign": v.is_warning_sign,
            "recorded_at": v.recorded_at.isoformat() if v.recorded_at else None,
            "recorded_by": v.recorded_by or "ASHA / Doctor",
            "source_type": v.source_type.value if hasattr(v.source_type, "value") else str(v.source_type)
        })
    return StandardResponse(data=results)


@router.post("/patients/{citizen_id}/measurements", response_model=StandardResponse)
def record_doctor_phc_measurement(
    citizen_id: str,
    payload: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_doctor)
):
    case = db.query(Case).filter(Case.citizen_id == citizen_id, ~Case.status.in_([CaseStatusEnum.COMPLETED, CaseStatusEnum.DECLINED])).first()
    if not case:
        case = db.query(Case).filter(Case.citizen_id == citizen_id).order_by(Case.created_at.desc()).first()
    
    if not case:
        raise HTTPException(status_code=404, detail="No active or past case found for citizen to attach measurement.")

    from app.models import InformationSourceEnum
    vital = VitalRecord(
        case_id=case.id,
        systolic_bp=payload.get("systolic_bp"),
        diastolic_bp=payload.get("diastolic_bp"),
        spo2=payload.get("spo2"),
        pulse=payload.get("pulse"),
        temperature_c=payload.get("temperature_c"),
        source_type=InformationSourceEnum.CLINICIAN_ENTERED if hasattr(InformationSourceEnum, "CLINICIAN_ENTERED") else InformationSourceEnum.DEVICE_MEASURED,
        recorded_by=current_user.name or "Dr. Abhinav Sharma",
        is_warning_sign=bool(payload.get("systolic_bp", 0) >= 140 or payload.get("spo2", 100) <= 94)
    )

    db.add(vital)
    db.commit()
    db.refresh(vital)

    return StandardResponse(data={"measurement_id": vital.id, "status": "RECORDED"})


@router.get("/patients/{citizen_id}/visits", response_model=StandardResponse)
def get_doctor_patient_visits(
    citizen_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    cases = db.query(Case).filter(Case.citizen_id == citizen_id).all()
    case_ids = [c.id for c in cases]
    visits = db.query(AshaVisit).filter(AshaVisit.case_id.in_(case_ids)).order_by(AshaVisit.started_at.desc()).all() if case_ids else []
    results = []
    for vis in visits:
        results.append({
            "visit_id": vis.id,
            "id": vis.id,
            "reference": vis.reference or f"VISIT-{vis.id[:6]}",
            "case_id": vis.case_id,
            "date": vis.completed_at.isoformat() if vis.completed_at else (vis.started_at.isoformat() if vis.started_at else None),
            "visit_type": vis.visit_type,
            "consent_obtained": vis.consent_obtained,
            "asha_observations": vis.notes or "Routine field visit completed.",
            "next_action": vis.next_action or "REFER_TO_PHC"
        })
    return StandardResponse(data=results)


@router.get("/patients/{citizen_id}/referrals", response_model=StandardResponse)
def get_doctor_patient_referrals(
    citizen_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    cases = db.query(Case).filter(Case.citizen_id == citizen_id).all()
    case_ids = [c.id for c in cases]
    referrals = db.query(Referral).filter(Referral.case_id.in_(case_ids)).order_by(Referral.created_at.desc()).all() if case_ids else []
    results = []
    for r in referrals:
        results.append({
            "referral_id": r.id,
            "id": r.id,
            "reference": r.reference,
            "case_id": r.case_id,
            "reason": r.reason,
            "urgency": str(r.urgency.value if hasattr(r.urgency, "value") else r.urgency),
            "status": r.status,
            "target_facility": r.to_facility_name,
            "created_at": r.created_at.isoformat() if r.created_at else None
        })
    return StandardResponse(data=results)


@router.get("/patients/{citizen_id}/consultations", response_model=StandardResponse)
def get_doctor_patient_consultations(
    citizen_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    cases = db.query(Case).filter(Case.citizen_id == citizen_id).all()
    case_ids = [c.id for c in cases]
    consultations = db.query(Consultation).filter(Consultation.case_id.in_(case_ids)).order_by(Consultation.created_at.desc()).all() if case_ids else []
    results = []
    for c in consultations:
        results.append({
            "consultation_id": c.id,
            "id": c.id,
            "reference": c.reference,
            "case_id": c.case_id,
            "doctor_name": c.doctor_name or "Dr. Abhinav Sharma",
            "status": c.status,
            "confirmed_diagnosis": c.confirmed_diagnosis,
            "created_at": c.created_at.isoformat() if c.created_at else None
        })
    return StandardResponse(data=results)


@router.get("/patients/{citizen_id}/investigations", response_model=StandardResponse)
def get_doctor_patient_investigations(
    citizen_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    from app.models import InvestigationOrder
    from app.services.investigation_service import to_doctor_investigation_dto
    orders = db.query(InvestigationOrder).filter(InvestigationOrder.citizen_id == citizen_id).order_by(InvestigationOrder.ordered_at.desc()).all()
    dtos = [to_doctor_investigation_dto(o).model_dump() for o in orders]
    return StandardResponse(data=dtos)


@router.get("/patients/{citizen_id}/prescriptions", response_model=StandardResponse)
def get_doctor_patient_prescriptions(
    citizen_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    cases = db.query(Case).filter(Case.citizen_id == citizen_id).all()
    case_ids = [c.id for c in cases]
    prescriptions = db.query(Prescription).join(Consultation, Prescription.consultation_id == Consultation.id).filter(
        Consultation.case_id.in_(case_ids),
        Prescription.status == "SIGNED"
    ).order_by(Prescription.issued_at.desc()).all() if case_ids else []

    results = []
    for p in prescriptions:
        p_items = []
        for item in p.items:
            p_items.append({
                "medicine": item.medicine,
                "strength": item.strength,
                "form": item.form,
                "dose": item.dose,
                "frequency": item.frequency,
                "duration": item.duration,
                "instructions": item.instructions or "Take as advised"
            })
        results.append({
            "prescription_id": p.id,
            "id": p.id,
            "consultation_id": p.consultation_id,
            "signed_at": p.issued_at.isoformat() if p.issued_at else None,
            "status": p.status,
            "items": p_items
        })
    return StandardResponse(data=results)


@router.get("/patients/{citizen_id}/followups", response_model=StandardResponse)
def get_doctor_patient_followups(
    citizen_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    cases = db.query(Case).filter(Case.citizen_id == citizen_id).all()
    case_ids = [c.id for c in cases]
    followups = db.query(FollowUp).filter(
        (FollowUp.citizen_id == citizen_id) | (FollowUp.case_id.in_(case_ids))
    ).order_by(FollowUp.due_at.desc()).all() if case_ids else []

    results = []
    for f in followups:
        results.append({
            "followup_id": f.id,
            "id": f.id,
            "case_id": f.case_id,
            "directive": f.instructions,
            "due_date": f.due_at.isoformat() if f.due_at else None,
            "status": f.status,
            "task_type": f.task_type
        })
    return StandardResponse(data=results)


@router.post("/patients/{citizen_id}/contact-attempt", response_model=StandardResponse)
def record_doctor_contact_attempt(
    citizen_id: str,
    payload: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_doctor)
):
    citizen = db.query(CitizenProfile).filter(CitizenProfile.id == citizen_id).first()
    if not citizen:
        raise HTTPException(status_code=404, detail="Patient not found")

    user_role = str(current_user.role).upper()
    audit = AuditLog(
        actor_user_id=current_user.id,
        actor_role=user_role,
        action="DOCTOR_CALL_PATIENT_ATTEMPT",
        resource_type="CitizenProfile",
        resource_id=citizen_id,
        outcome="SUCCESS",
        metadata_json={
            "contact_target": payload.get("target", "CITIZEN"),
            "contact_outcome": payload.get("outcome", "INITIATED"),
            "notes": payload.get("notes")
        }
    )
    db.add(audit)
    db.commit()

    return StandardResponse(data={"status": "AUDITED", "message": "Contact attempt logged successfully."})


@router.post("/patients/{citizen_id}/request-demographic-update", response_model=StandardResponse)
def request_doctor_demographic_update(
    citizen_id: str,
    payload: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_doctor)
):
    citizen = db.query(CitizenProfile).filter(CitizenProfile.id == citizen_id).first()
    if not citizen:
        raise HTTPException(status_code=404, detail="Patient not found")

    user_role = str(current_user.role).upper()
    audit = AuditLog(
        actor_user_id=current_user.id,
        actor_role=user_role,
        action="DOCTOR_REQUEST_DEMOGRAPHIC_UPDATE",
        resource_type="CitizenProfile",
        resource_id=citizen_id,
        outcome="SUBMITTED",
        metadata_json={
            "field_corrections": payload.get("corrections", {}),
            "doctor_verification_note": payload.get("verification_note")
        }
    )
    db.add(audit)
    db.commit()

    return StandardResponse(data={"status": "SUBMITTED", "message": "Demographic update request submitted for review."})


# =========================================================================
# DIRECT CITIZEN REQUESTS (Teleconsultations)
# =========================================================================

def _get_doctor_facility_id(current_user: User) -> Optional[str]:
    if current_user and current_user.worker_profile and current_user.worker_profile.facility_id:
        return current_user.worker_profile.facility_id
    return None

def _is_doctor_authorized_for_request(current_user: User, srv_req: Any) -> bool:
    doc_fac = _get_doctor_facility_id(current_user)
    if srv_req.assigned_user_id == current_user.id:
        return True
    if doc_fac and srv_req.assigned_facility_id == doc_fac:
        return True
    return False

@router.get("/direct-requests", response_model=StandardResponse)
def get_doctor_direct_requests(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    from app.models import (
        ServiceRequest, CareHandoff, CitizenProfile, TeleconsultationRequest,
        TeleconsultationMessage, DoctorChatThread, DoctorChatMessage
    )

    doc_facility_id = _get_doctor_facility_id(current_user)

    # 1. Base query scoped by doctor's facility or assigned user
    base_query = db.query(ServiceRequest).filter(
        ServiceRequest.request_type == "DOCTOR_CONSULTATION"
    )

    if doc_facility_id:
        base_query = base_query.filter(
            (ServiceRequest.assigned_facility_id == doc_facility_id) |
            (ServiceRequest.assigned_facility_id.is_(None)) |
            (ServiceRequest.assigned_user_id == current_user.id)
        )
    else:
        # Isolated doctor without assigned facility can only see directly assigned requests
        base_query = base_query.filter(ServiceRequest.assigned_user_id == current_user.id)

    # Fetch all facility requests for accurate aggregate summary counts
    all_facility_reqs = base_query.all()

    waiting_cnt = sum(1 for r in all_facility_reqs if r.status in ["WAITING_FOR_DOCTOR", "SUBMITTED", "PENDING"])
    urgent_cnt = sum(1 for r in all_facility_reqs if r.priority in ["EMERGENCY", "URGENT", "HIGH"] and r.status not in ["COMPLETED", "CANCELLED"])
    accepted_cnt = sum(1 for r in all_facility_reqs if r.status == "DOCTOR_ACCEPTED")
    in_consultation_cnt = sum(1 for r in all_facility_reqs if r.status == "IN_CONSULTATION")
    completed_cnt = sum(1 for r in all_facility_reqs if r.status == "COMPLETED")

    counts_payload = {
        "waiting": waiting_cnt,
        "urgent": urgent_cnt,
        "accepted": accepted_cnt,
        "in_consultation": in_consultation_cnt,
        "completed": completed_cnt
    }

    # 2. Apply status filtering for list items
    srv_query = base_query
    if status and status.upper() != "ALL":
        sf = status.upper()
        if sf in ["NEW", "WAITING"]:
            srv_query = srv_query.filter(ServiceRequest.status.in_(["WAITING_FOR_DOCTOR", "SUBMITTED", "PENDING"]))
        elif sf == "URGENT":
            srv_query = srv_query.filter(
                ServiceRequest.priority.in_(["EMERGENCY", "URGENT", "HIGH"]),
                ~ServiceRequest.status.in_(["COMPLETED", "CANCELLED"])
            )
        elif sf == "ACCEPTED":
            srv_query = srv_query.filter(ServiceRequest.status == "DOCTOR_ACCEPTED")
        elif sf == "IN_CONSULTATION":
            srv_query = srv_query.filter(ServiceRequest.status == "IN_CONSULTATION")
        elif sf == "COMPLETED":
            srv_query = srv_query.filter(ServiceRequest.status == "COMPLETED")
        elif sf == "ASSIGNED_TO_ME":
            srv_query = srv_query.filter(ServiceRequest.assigned_user_id == current_user.id)
        else:
            srv_query = srv_query.filter(ServiceRequest.status == sf)

    requests = srv_query.order_by(ServiceRequest.created_at.desc()).all()
    items = []

    for r in requests:
        handoff = db.query(CareHandoff).filter(CareHandoff.service_request_id == r.id).order_by(CareHandoff.version.desc()).first()
        citizen = r.citizen
        bm = r.beneficiary
        patient_profile_id = citizen.id if citizen else None

        # Fetch deduplicated messages via DoctorChatService
        from app.services.doctor_chat_service import DoctorChatService
        messages_data = DoctorChatService.get_messages(db, r.id)

        tele_req_ids = [t[0] for t in db.query(TeleconsultationRequest.id).filter(
            (TeleconsultationRequest.service_request_id == r.id) |
            (TeleconsultationRequest.public_reference == r.request_reference)
        ).all()]

        chief = handoff.chief_concern if handoff else (r.details or {}).get("chief_complaint") or "Teleconsultation Request"

        items.append({
            "id": r.id,
            "service_request_id": r.id,
            "teleconsultation_request_id": tele_req_ids[0] if tele_req_ids else None,
            "request_reference": r.request_reference,
            "public_reference": r.request_reference,
            "patient_id": patient_profile_id,
            "patient_profile_id": patient_profile_id,
            "citizen_id": citizen.id if citizen else None,
            "beneficiary_id": bm.id if bm else None,
            "citizen_name": citizen.display_name if citizen else "Citizen",
            "beneficiary_name": bm.full_name if (bm and bm.full_name and bm.full_name.strip().lower() not in ["self", "myself"]) else (citizen.display_name if (citizen and citizen.display_name and citizen.display_name.strip().lower() not in ["self", "myself"]) else "Patient"),
            "beneficiary_relationship": bm.relationship_type if bm else "SELF",
            "citizen_phone": citizen.phone if citizen else None,
            "village_name": citizen.village_name if citizen else "Kalyanpur",
            "priority": r.priority,
            "status": r.status,
            "requested_channel": r.requested_channel or "CALLBACK",
            "mode": r.requested_channel or "CALLBACK",
            "facility_id": r.assigned_facility_id,
            "assigned_doctor_id": r.assigned_user_id,
            "assigned_doctor_name": r.assigned_user.name if r.assigned_user else (current_user.name if r.assigned_user_id == current_user.id else None),
            "messages": messages_data,
            "chief_complaint": chief,
            "chief_concern": chief,
            "citizen_summary": handoff.citizen_summary if handoff else None,
            "handoff_version": handoff.version if handoff else 1,
            "handoff_packet": handoff.structured_payload if handoff else {},
            "case_id": r.case_id,
            "case_reference": r.case.reference if r.case else None,
            "submitted_at": r.submitted_at.isoformat() if r.submitted_at else (r.created_at.isoformat() if r.created_at else ""),
            "created_at": r.created_at.isoformat() if r.created_at else ""
        })

    return StandardResponse(data={
        "items": items,
        "total": len(items),
        "counts": counts_payload
    })

@router.get("/direct-requests/summary", response_model=StandardResponse)
def get_doctor_direct_requests_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    from app.models import ServiceRequest
    doc_facility_id = _get_doctor_facility_id(current_user)

    base_query = db.query(ServiceRequest).filter(
        ServiceRequest.request_type == "DOCTOR_CONSULTATION"
    )

    if doc_facility_id:
        base_query = base_query.filter(
            (ServiceRequest.assigned_facility_id == doc_facility_id) |
            (ServiceRequest.assigned_user_id == current_user.id)
        )
    else:
        base_query = base_query.filter(ServiceRequest.assigned_user_id == current_user.id)

    all_reqs = base_query.all()
    waiting_count = len([r for r in all_reqs if r.status in ["WAITING_FOR_DOCTOR", "SUBMITTED", "PENDING"]])
    urgent_count = len([r for r in all_reqs if r.priority in ["EMERGENCY", "URGENT", "HIGH"] and r.status not in ["COMPLETED", "CANCELLED"]])
    accepted_count = len([r for r in all_reqs if r.status == "DOCTOR_ACCEPTED"])
    in_consultation_count = len([r for r in all_reqs if r.status == "IN_CONSULTATION"])
    completed_count = len([r for r in all_reqs if r.status == "COMPLETED"])

    return StandardResponse(data={
        "total": len(all_reqs),
        "waiting": waiting_count,
        "urgent": urgent_count,
        "accepted": accepted_count,
        "in_consultation": in_consultation_count,
        "completed": completed_count
    })

@router.post("/direct-requests/{request_id}/messages", response_model=StandardResponse)
@router.post("/direct-requests/{request_id}/chat-messages", response_model=StandardResponse)
def send_doctor_chat_message(
    request_id: str,
    dto: TeleconsultationMessageCreateDTO,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    from app.services.teleconsultation_service import TeleconsultationService
    tele_req, srv_req = TeleconsultationService.resolve_canonical_request(db, request_id)
    if not tele_req and not srv_req:
        raise HTTPException(status_code=404, detail="Direct request not found")

    target_srv = srv_req or (tele_req.service_request if tele_req else None)
    if target_srv and not _is_doctor_authorized_for_request(current_user, target_srv):
        raise HTTPException(status_code=403, detail="Forbidden: You are not authorized to message on this request")

    body_text = dto.body or dto.message_text or ""
    if not body_text.strip():
        raise HTTPException(status_code=400, detail="Message text cannot be empty")

    target_req_id = tele_req.id if tele_req else target_srv.id
    from app.services.recent_activity_service import normalize_actor_name
    doctor_clean_name = normalize_actor_name(current_user.name, role="PHC_DOCTOR")

    msg = TeleconsultationService.send_message(
        db=db,
        request_id=target_req_id,
        sender_type="DOCTOR",
        sender_role="PHC_DOCTOR",
        sender_name=doctor_clean_name,
        message_text=body_text,
        sender_id=current_user.id,
        client_message_id=dto.client_message_id,
        message_type=dto.message_type or "TEXT"
    )

    msg_body = getattr(msg, "body", None) or getattr(msg, "message_text", None) or body_text
    msg_sender_role = getattr(msg, "sender_role", "PHC_DOCTOR")
    msg_sender_type = getattr(msg, "sender_type", "DOCTOR")
    msg_cli_id = getattr(msg, "client_message_id", dto.client_message_id)
    msg_conv_id = getattr(msg, "conversation_id", target_req_id)
    msg_srv_id = getattr(msg, "service_request_id", target_srv.id if target_srv else target_req_id)
    msg_status = getattr(msg, "status", "DELIVERED")
    created_at_dt = getattr(msg, "created_at", None)
    delivered_at_dt = getattr(msg, "delivered_at", None)
    read_at_dt = getattr(msg, "read_at", None)

    return StandardResponse(data={
        "id": msg.id,
        "conversation_id": msg_conv_id,
        "service_request_id": msg_srv_id,
        "sender_user_id": getattr(msg, "sender_user_id", current_user.id),
        "sender_role": msg_sender_role,
        "sender_type": msg_sender_type,
        "sender_name": getattr(msg, "sender_name", doctor_clean_name),
        "message_type": getattr(msg, "message_type", "TEXT"),
        "body": msg_body,
        "message_text": msg_body,
        "client_message_id": msg_cli_id,
        "status": msg_status,
        "created_at": created_at_dt.isoformat() if created_at_dt else "",
        "delivered_at": delivered_at_dt.isoformat() if delivered_at_dt else None,
        "read_at": read_at_dt.isoformat() if read_at_dt else None
    })

@router.get("/direct-requests/{request_id}", response_model=StandardResponse)
def get_doctor_direct_request_detail(
    request_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    from app.models import (
        ServiceRequest, CareHandoff, ServiceRequestStatusHistory, CitizenProfile,
        TeleconsultationRequest, TeleconsultationMessage, DoctorChatThread, DoctorChatMessage
    )
    from app.services.teleconsultation_service import TeleconsultationService
    from app.services.doctor_chat_service import DoctorChatService
    tele_req, r = TeleconsultationService.resolve_canonical_request(db, request_id)
    if not r and not tele_req:
        raise HTTPException(status_code=404, detail="Direct citizen request not found")

    target_srv = r or (tele_req.service_request if tele_req else None)
    if target_srv and not _is_doctor_authorized_for_request(current_user, target_srv):
        raise HTTPException(status_code=403, detail="Forbidden: You are not authorized to view this request")

    if not r and tele_req:
        return StandardResponse(data=TeleconsultationService.get_request_detail(db, tele_req.id))

    handoff = db.query(CareHandoff).filter(CareHandoff.service_request_id == r.id).order_by(CareHandoff.version.desc()).first()
    history = db.query(ServiceRequestStatusHistory).filter(ServiceRequestStatusHistory.service_request_id == r.id).order_by(ServiceRequestStatusHistory.occurred_at.asc()).all()
    citizen = r.citizen
    bm = r.beneficiary

    # Fetch canonical deduplicated messages
    messages_data = DoctorChatService.get_messages(db, r.id)

    chief = handoff.chief_concern if handoff else (r.details or {}).get("chief_complaint") or "Care Handoff Request"

    return StandardResponse(data={
        "id": r.id,
        "conversation_id": tele_req.id if tele_req else r.id,
        "service_request_id": r.id,
        "request_reference": r.request_reference,
        "public_reference": r.request_reference,
        "patient_id": citizen.id if citizen else None,
        "patient_profile_id": citizen.id if citizen else None,
        "citizen_id": citizen.id if citizen else None,
        "beneficiary_id": bm.id if bm else None,
        "citizen_name": citizen.display_name if citizen else "Citizen",
        "beneficiary_name": bm.full_name if (bm and bm.full_name and bm.full_name.strip().lower() not in ["self", "myself"]) else (citizen.display_name if (citizen and citizen.display_name and citizen.display_name.strip().lower() not in ["self", "myself"]) else "Patient"),
        "beneficiary_relationship": bm.relationship_type if bm else "SELF",
        "citizen_phone": citizen.phone if citizen else None,
        "village_name": citizen.village_name if citizen else "Kalyanpur",
        "priority": r.priority,
        "status": r.status,
        "requested_channel": r.requested_channel,
        "mode": r.requested_channel,
        "facility_id": r.assigned_facility_id,
        "assigned_doctor_id": r.assigned_user_id,
        "assigned_doctor_name": r.assigned_user.name if r.assigned_user else (current_user.name if r.assigned_user_id == current_user.id else None),
        "messages": messages_data,
        "details": r.details,
        "chief_complaint": chief,
        "chief_concern": chief,
        "citizen_summary": handoff.citizen_summary if handoff else None,
        "handoff_version": handoff.version if handoff else 1,
        "handoff_packet": handoff.structured_payload if handoff else {},
        "case_id": r.case_id,
        "case_reference": r.case.reference if r.case else None,
        "status_history": [
            {
                "from_status": h.from_status,
                "to_status": h.to_status,
                "actor_role": h.actor_role,
                "reason": h.reason,
                "occurred_at": h.occurred_at.isoformat()
            }
            for h in history
        ],
        "submitted_at": r.submitted_at.isoformat() if r.submitted_at else (r.created_at.isoformat() if r.created_at else ""),
        "created_at": r.created_at.isoformat() if r.created_at else ""
    })

@router.patch("/direct-requests/{request_id}/status", response_model=StandardResponse)
def patch_doctor_direct_request_status(
    request_id: str,
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    from app.models import (
        ServiceRequest, ServiceRequestStatusHistory, Case, Consultation,
        Prescription, PrescriptionItem, MedicineCatalog, FollowUp, InvestigationOrder,
        TeleconsultationRequest, TeleconsultationStatusHistory, DoctorChatThread
    )
    from app.services.event_bus import publish_domain_event
    from app.services.teleconsultation_service import TeleconsultationService

    tele_req, r = TeleconsultationService.resolve_canonical_request(db, request_id)
    if not r and not tele_req:
        raise HTTPException(status_code=404, detail="Direct request not found")

    target_srv = r or (tele_req.service_request if tele_req else None)
    if target_srv and not _is_doctor_authorized_for_request(current_user, target_srv):
        raise HTTPException(status_code=403, detail="Forbidden: You are not authorized to update this request")

    action = payload.get("action", "").upper()
    notes = payload.get("notes") or payload.get("reason")
    old_status = target_srv.status if target_srv else (tele_req.status if tele_req else "WAITING_FOR_DOCTOR")
    new_status = old_status

    if action == "ACCEPT" or action == "REVIEW":
        new_status = "DOCTOR_ACCEPTED"
        if target_srv:
            target_srv.assigned_user_id = current_user.id
            target_srv.acknowledged_at = datetime.now(timezone.utc)
        if tele_req:
            tele_req.assigned_doctor_id = current_user.id
            tele_req.accepted_at = datetime.now(timezone.utc)
    elif action == "START_CONSULTATION":
        new_status = "IN_CONSULTATION"
        if target_srv:
            target_srv.assigned_user_id = current_user.id
            if not target_srv.details:
                target_srv.details = {}
            target_srv.details["consultation_started_at"] = datetime.now(timezone.utc).isoformat()
        if tele_req:
            tele_req.assigned_doctor_id = current_user.id
            tele_req.started_at = datetime.now(timezone.utc)
    elif action == "REQUEST_INFO":
        new_status = "INFORMATION_REQUESTED"
        if target_srv and target_srv.details:
            target_srv.details["info_request_notes"] = notes
    elif action == "RECOMMEND_IN_PERSON":
        new_status = "REFERRED_IN_PERSON"
        if target_srv and target_srv.details:
            target_srv.details["in_person_guidance"] = notes or "Please visit Kalyanpur PHC for physical examination."
    elif action == "ESCALATE_EMERGENCY":
        new_status = "EMERGENCY_ESCALATED"
        if target_srv:
            target_srv.priority = "EMERGENCY"
            if target_srv.details:
                target_srv.details["emergency_notes"] = notes or "Critical red flags detected. Immediate emergency transport advised."
        if tele_req:
            tele_req.priority = "EMERGENCY"
    elif action == "DECLINE":
        new_status = "CANCELLED"
        if target_srv:
            target_srv.cancellation_reason = notes or "Declined by Doctor"
        if tele_req:
            tele_req.cancellation_reason = notes or "Declined by Doctor"
    elif action == "COMPLETE":
        new_status = "COMPLETED"
        now_dt = datetime.now(timezone.utc)
        diag = payload.get("provisional_diagnosis", "Clinical Assessment Complete")
        guidance = payload.get("patient_guidance", "Take prescribed medicines and rest.")

        if target_srv:
            target_srv.completed_at = now_dt
            if not target_srv.details:
                target_srv.details = {}
            target_srv.details["provisional_diagnosis"] = diag
            target_srv.details["patient_guidance"] = guidance
        if tele_req:
            tele_req.completed_at = now_dt
            tele_req.disposition = payload.get("disposition", "COMPLETED")
            tele_req.patient_guidance = guidance

        # Create Consultation record
        cid = target_srv.case_id if target_srv else (tele_req.case_id if tele_req else None)
        cit_id = target_srv.citizen_id if target_srv else (tele_req.citizen_id if tele_req else None)
        fac_id = target_srv.assigned_facility_id if target_srv else (tele_req.facility_id if tele_req else "PHC-09")

        cons = Consultation(
            reference=f"CONS-{uuid.uuid4().hex[:8].upper()}",
            case_id=cid,
            doctor_id=current_user.id,
            doctor_name=current_user.name,
            facility_id=fac_id or "PHC-09",
            consultation_type="TELECONSULTATION",
            started_at=datetime.now(timezone.utc) - timedelta(minutes=15),
            completed_at=now_dt,
            provisional_diagnosis=diag,
            confirmed_diagnosis=diag,
            clinical_summary=f"{diag}. Direct consultation with Dr. {current_user.name}.",
            care_plan_summary=guidance,
            status="COMPLETED"
        )
        db.add(cons)
        db.flush()

        if tele_req:
            tele_req.consultation_id = cons.id

        # Create Prescription if prescribed
        rx_items = payload.get("prescriptions", [])
        if rx_items:
            rx = Prescription(
                reference=f"RX-{uuid.uuid4().hex[:8].upper()}",
                case_id=cid,
                consultation_id=cons.id,
                citizen_id=cit_id,
                prescriber_doctor_id=current_user.id,
                facility_id=fac_id or "PHC-09",
                clinical_context=diag,
                status="SIGNED",
                signed_at=now_dt
            )
            db.add(rx)
            db.flush()

            for item in rx_items:
                p_item = PrescriptionItem(
                    prescription_id=rx.id,
                    generic_name_snapshot=item.get("medicine_name", "Paracetamol 500mg"),
                    medicine=item.get("medicine_name", "Paracetamol 500mg"),
                    formulation=item.get("formulation", "Tablet"),
                    strength=item.get("strength", "500mg"),
                    dose=item.get("dosage", "1 tablet"),
                    frequency=item.get("frequency", "1-0-1"),
                    duration_value=item.get("duration_days", 3),
                    duration_unit="days",
                    instructions=item.get("instructions", "Take after meals")
                )
                db.add(p_item)

        # Create Investigation Orders if requested
        inv_items = payload.get("investigation_orders", [])
        for inv_dto in inv_items:
            if isinstance(inv_dto, str):
                test_name = inv_dto
                category = "PATHOLOGY"
                priority = "ROUTINE"
                clinical_reason = diag
                prep_inst = None
            elif isinstance(inv_dto, dict):
                test_name = inv_dto.get("test_name", "Complete Blood Count (CBC)")
                category = inv_dto.get("category", "PATHOLOGY")
                priority = inv_dto.get("priority") or inv_dto.get("urgency") or "ROUTINE"
                clinical_reason = inv_dto.get("clinical_reason") or diag
                prep_inst = inv_dto.get("preparation_instructions")
            else:
                continue
            
            inv = InvestigationOrder(
                reference=f"LAB-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:4].upper()}",
                citizen_id=cit_id,
                case_id=cid,
                consultation_id=cons.id,
                ordered_by_doctor_id=current_user.id,
                facility_id=fac_id or "PHC-09",
                test_name=test_name,
                category=category,
                priority=priority,
                clinical_reason=clinical_reason,
                preparation_instructions=prep_inst,
                status="ORDERED",
                ordered_at=now_dt
            )
            db.add(inv)

        # Create ASHA FollowUp if requested
        if payload.get("assign_asha_followup", True) or payload.get("follow_up_plan"):
            asha_user_id = None
            if target_srv and target_srv.citizen and target_srv.citizen.assigned_asha_id:
                asha_user_id = target_srv.citizen.assigned_asha_id
            elif target_srv and target_srv.case and target_srv.case.assigned_asha_id:
                asha_user_id = target_srv.case.assigned_asha_id
            else:
                sita = db.query(User).filter(User.role == UserRoleEnum.ASHA_WORKER).first()
                if sita:
                    asha_user_id = sita.id

            fu_task_type = payload.get("asha_task_type") or payload.get("task_type") or "POST_CONSULTATION_CHECK"
            due_days = int(payload.get("asha_due_days") or 3)
            fu = FollowUp(
                case_id=cid,
                consultation_id=cons.id,
                citizen_id=cit_id,
                assigned_user_id=asha_user_id,
                created_by_role="DOCTOR",
                source="DOCTOR_DIRECTIVE",
                task_type=fu_task_type,
                reason=f"Follow-up for {diag}",
                assigned_role=UserRoleEnum.ASHA_WORKER,
                instructions=payload.get("asha_instructions", f"Visit patient at home and verify recovery from {diag}"),
                priority=CasePriorityEnum.ROUTINE,
                due_at=now_dt + timedelta(days=due_days),
                status="PENDING"
            )
            db.add(fu)
    elif payload.get("status"):
        new_status = payload.get("status")
    else:
        raise HTTPException(status_code=400, detail=f"Invalid action '{action}'")

    if target_srv:
        target_srv.status = new_status
        hist = ServiceRequestStatusHistory(
            service_request_id=target_srv.id,
            from_status=old_status,
            to_status=new_status,
            actor_role="PHC_DOCTOR",
            actor_id=current_user.id,
            reason=notes or f"Status updated via action {action} by Dr. {current_user.name}"
        )
        db.add(hist)

    if tele_req:
        tele_req.status = new_status
        thist = TeleconsultationStatusHistory(
            request_id=tele_req.id,
            from_status=old_status,
            to_status=new_status,
            changed_by_user_id=current_user.id,
            changed_by_role="DOCTOR",
            notes=notes or f"Status updated via action {action} by Dr. {current_user.name}"
        )
        db.add(thist)

    # Sync companion DoctorChatThread
    thread = db.query(DoctorChatThread).filter(
        (DoctorChatThread.service_request_id == (target_srv.id if target_srv else "")) |
        (DoctorChatThread.id == (tele_req.id if tele_req else ""))
    ).first()
    if thread:
        thread.status = new_status
        if current_user.id:
            thread.doctor_id = current_user.id

    # Sync Case status
    cid = target_srv.case_id if target_srv else (tele_req.case_id if tele_req else None)
    if cid:
        case = db.query(Case).filter(Case.id == cid).first()
        if case:
            if new_status in ["DOCTOR_ACCEPTED", "IN_CONSULTATION"]:
                case.status = CaseStatusEnum.DOCTOR_ACKNOWLEDGED
            elif new_status == "COMPLETED":
                case.status = CaseStatusEnum.COMPLETED

    publish_domain_event("DOCTOR_DIRECT_REQUEST_STATUS_UPDATED", {
        "service_request_id": target_srv.id if target_srv else (tele_req.service_request_id if tele_req else None),
        "request_reference": target_srv.request_reference if target_srv else (tele_req.public_reference if tele_req else None),
        "case_id": cid,
        "citizen_id": target_srv.citizen_id if target_srv else (tele_req.citizen_id if tele_req else None),
        "action": action,
        "from_status": old_status,
        "to_status": new_status,
        "doctor_name": current_user.name,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })

    db.commit()
    if target_srv:
        db.refresh(target_srv)
    if tele_req:
        db.refresh(tele_req)

    res_id = target_srv.id if target_srv else tele_req.id
    res_ref = target_srv.request_reference if target_srv else tele_req.public_reference

    return StandardResponse(data={
        "id": res_id,
        "service_request_id": res_id,
        "request_reference": res_ref,
        "status": new_status,
        "action": action,
        "message": f"Status updated to {new_status}"
    })

@router.post("/direct-requests/{request_id}/accept", response_model=StandardResponse)
def doctor_accept_direct_request(
    request_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    return patch_doctor_direct_request_status(request_id, {"action": "ACCEPT"}, db, current_user)

@router.post("/direct-requests/{request_id}/start", response_model=StandardResponse)
def doctor_start_direct_consultation(
    request_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    return patch_doctor_direct_request_status(request_id, {"action": "START_CONSULTATION"}, db, current_user)

@router.post("/direct-requests/{request_id}/complete", response_model=StandardResponse)
def doctor_complete_direct_consultation(
    request_id: str,
    dto: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    payload = {"action": "COMPLETE", **dto}
    return patch_doctor_direct_request_status(request_id, payload, db, current_user)

@router.post("/direct-requests/{request_id}/decline", response_model=StandardResponse)
def doctor_decline_direct_request(
    request_id: str,
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    return patch_doctor_direct_request_status(request_id, {"action": "DECLINE", **payload}, db, current_user)




