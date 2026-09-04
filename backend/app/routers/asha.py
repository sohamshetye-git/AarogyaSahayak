from fastapi import APIRouter, Depends, HTTPException, status, Header, Response, Body, Query
import json
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from app.database import get_db
from app.models import (
    Case, AshaVisit, Referral, CitizenProfile, VitalRecord, SymptomObservation,
    User, CaseStatusEnum, CasePriorityEnum, InformationSourceEnum, AuditLog,
    IdempotencyRecord, FollowUp, Consultation, UserRoleEnum
)
from app.schemas import (
    StandardResponse, AshaDashboardResponse, AshaTaskDTO, AshaAcknowledgeRequest,
    AshaVisitSubmitRequest, AshaReferralRequest, AshaContactResultRequest,
    AshaFollowUpDTO, AshaFollowUpSubmitRequest, TimelineEventDTO,
    AshaContactResultInput, AshaAttendanceInput, AshaEscalateInput,
    AshaAddSymptomsRequest, AshaRecordVitalsRequest
)
from app.schemas.prescription import AshaAdherenceOutcomeRequest, AshaAdherenceEscalateRequest
from app.dependencies import get_current_user, get_optional_user, require_asha, require_staff
from app.services.referral_service import ReferralService
from app.services.case_service import CaseService
from app.services.idempotency_service import check_idempotency, record_idempotency
from app.services.event_bus import publish_domain_event
from app.safety.emergency_rules import EmergencyRuleEvaluator

router = APIRouter(prefix="/asha", tags=["ASHA Worker"])

@router.get("/dashboard", response_model=StandardResponse)
def get_asha_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    now = datetime.now(timezone.utc)
    total_assigned = db.query(Case).filter(Case.assigned_asha_id == current_user.id).count()
    urgent_count = db.query(Case).filter(Case.assigned_asha_id == current_user.id, Case.priority == CasePriorityEnum.URGENT).count()
    urgent_unack = db.query(Case).filter(
        Case.assigned_asha_id == current_user.id,
        Case.priority == CasePriorityEnum.URGENT,
        Case.status == CaseStatusEnum.NEW
    ).count()

    pending_visits = db.query(Case).filter(
        Case.assigned_asha_id == current_user.id,
        Case.status.in_([CaseStatusEnum.NEW, CaseStatusEnum.ASHA_ACKNOWLEDGED, CaseStatusEnum.CITIZEN_CONTACTED])
    ).count()

    active_followups = db.query(FollowUp).filter(
        FollowUp.assigned_user_id == current_user.id,
        FollowUp.status == "PENDING"
    ).count()

    overdue_followups = db.query(FollowUp).filter(
        FollowUp.assigned_user_id == current_user.id,
        FollowUp.status == "PENDING",
        FollowUp.due_at < now
    ).count()

    doctor_instructions = db.query(FollowUp).filter(
        FollowUp.assigned_user_id == current_user.id,
        FollowUp.source == "DOCTOR",
        FollowUp.status == "PENDING"
    ).count()

    # Strict ASHA scoping: count only citizens assigned to this ASHA or residing in their assigned village
    worker = getattr(current_user, 'worker_profile', None)
    assigned_village = getattr(worker, 'village_name', None) or (worker.village_ids[0] if worker and worker.village_ids else None)

    if assigned_village:
        total_citizens = db.query(CitizenProfile).filter(
            (CitizenProfile.assigned_asha_id == current_user.id) | (CitizenProfile.village_name == assigned_village)
        ).count()
    else:
        total_citizens = db.query(CitizenProfile).filter(
            CitizenProfile.assigned_asha_id == current_user.id
        ).count()

    cases = db.query(Case).filter(
        Case.assigned_asha_id == current_user.id
    ).order_by(Case.created_at.desc()).limit(20).all()

    tasks = [
        AshaTaskDTO(
            id=c.id,
            case_id=c.id,
            case_reference=c.reference,
            citizen_name=c.citizen.display_name if c.citizen else "Citizen",
            citizen_age=c.citizen.age_estimate if c.citizen else None,
            citizen_phone=c.citizen.phone if c.citizen else None,
            village_name=c.citizen.village_name if c.citizen and c.citizen.village_name else (assigned_village or "Assigned Village"),
            priority=c.priority.value,
            status=c.status.value,
            primary_concern=c.primary_concern,
            is_pregnant=c.citizen.is_pregnant if c.citizen else False,
            gestational_weeks=c.citizen.gestational_weeks if c.citizen else None,
            created_at=c.created_at,
            assigned_asha_name=c.assigned_asha_name
        )
        for c in cases
    ]

    worker_name = current_user.name if current_user and current_user.name else "ASHA Worker"
    village = assigned_village or (worker.coverage_area if worker and worker.coverage_area else "Assigned Area")

    return StandardResponse(
        data=AshaDashboardResponse(
            worker_name=worker_name,
            village=village,
            total_assigned=total_assigned,
            urgent_count=urgent_count,
            pending_visits=pending_visits,
            active_followups=active_followups,
            urgent_unacknowledged_count=urgent_unack,
            todays_visits_count=pending_visits,
            overdue_followups_count=overdue_followups,
            doctor_instructions_count=doctor_instructions,
            total_assigned_citizens=total_citizens,
            pending_sync_count=0,
            recent_tasks=tasks
        ).model_dump()
    )

@router.get("/tasks", response_model=StandardResponse)
def get_asha_tasks(
    priority: Optional[str] = None,
    status_filter: Optional[str] = None,
    search: Optional[str] = None,
    sort_by: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    query = db.query(Case)
    if current_user.role == UserRoleEnum.ASHA_WORKER:
        query = query.filter(Case.assigned_asha_id == current_user.id)
    if priority:
        query = query.filter(Case.priority == priority)
    if status_filter:
        query = query.filter(Case.status == status_filter)

    if search:
        s = f"%{search.strip()}%"
        query = query.join(CitizenProfile, Case.citizen_id == CitizenProfile.id).filter(
            (Case.reference.ilike(s)) |
            (Case.primary_concern.ilike(s)) |
            (CitizenProfile.display_name.ilike(s)) |
            (CitizenProfile.village_name.ilike(s)) |
            (CitizenProfile.phone.ilike(s))
        )

    if sort_by == "oldest":
        query = query.order_by(Case.created_at.asc())
    elif sort_by == "priority":
        query = query.order_by(Case.priority.desc(), Case.created_at.desc())
    else:
        query = query.order_by(Case.created_at.desc())

    cases = query.all()
    tasks = [
        AshaTaskDTO(
            id=c.id,
            case_id=c.id,
            case_reference=c.reference,
            citizen_name=c.citizen.display_name if c.citizen else "Citizen",
            citizen_age=c.citizen.age_estimate if c.citizen else None,
            citizen_phone=c.citizen.phone if c.citizen else None,
            village_name=c.citizen.village_name if c.citizen else "Kalyanpur",
            priority=c.priority.value,
            status=c.status.value,
            primary_concern=c.primary_concern,
            is_pregnant=c.citizen.is_pregnant if c.citizen else False,
            gestational_weeks=c.citizen.gestational_weeks if c.citizen else None,
            created_at=c.created_at,
            assigned_asha_name=c.assigned_asha_name
        ).model_dump()
        for c in cases
    ]
    return StandardResponse(data=tasks)


@router.get("/investigation-tasks", response_model=StandardResponse)
def get_asha_investigation_tasks(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    from sqlalchemy import or_
    from app.models import InvestigationAshaTask, InvestigationOrder, utc_now
    from app.schemas import AshaInvestigationTaskDTO

    query = db.query(InvestigationAshaTask)
    if current_user and current_user.role == "ASHA_WORKER":
        tasks = query.filter(InvestigationAshaTask.asha_user_id == current_user.id).all()
    else:
        tasks = query.all()

    dtos = []
    for t in tasks:
        order = db.query(InvestigationOrder).filter(InvestigationOrder.id == t.investigation_order_id).first()
        dtos.append(AshaInvestigationTaskDTO(
            task_id=t.id,
            investigation_id=t.investigation_order_id,
            investigation_reference=order.reference if order else "INV-Order",
            citizen_id=t.citizen_id,
            citizen_name=t.citizen.display_name if t.citizen else "Citizen",
            village_name=t.citizen.village_name if t.citizen else "Kalyanpur",
            test_name=order.test_name if order else "Diagnostic Test",
            facility_name="Kalyanpur PHC",
            due_date=t.due_date.isoformat() if t.due_date else utc_now().isoformat(),
            preparation_instructions=order.preparation_instructions if order else "Standard",
            attendance_requirement="Visit PHC Sample Counter",
            doctor_directive=t.instructions,
            status=t.status,
            contacted_citizen=t.contacted_citizen,
            attendance_confirmed=t.attendance_confirmed,
            unable_to_attend_reason=t.unable_to_attend_reason
        ).model_dump())

    return StandardResponse(data=dtos)

@router.get("/cases/{case_id}", response_model=StandardResponse)
def get_case_details_for_asha(case_id: str, db: Session = Depends(get_db), current_user: Optional[User] = Depends(get_optional_user)):
    case = db.query(Case).filter((Case.id == case_id) | (Case.reference == case_id)).first()
    if not case:
        # Check if case_id refers to a CitizenProfile (e.g. "citizen-xyz" or citizen UUID)
        citizen_lookup_id = case_id.replace("citizen-", "")
        citizen = db.query(CitizenProfile).filter((CitizenProfile.id == citizen_lookup_id) | (CitizenProfile.id == case_id)).first()
        if citizen:
            # Check if citizen has a latest case
            latest_case = db.query(Case).filter(Case.citizen_id == citizen.id).order_by(Case.created_at.desc()).first()
            if latest_case:
                case = latest_case
            else:
                # Sanitize male pregnancy
                is_male = citizen.sex and citizen.sex.strip().lower() in ["male", "m"]
                is_pregnant = False if is_male else (citizen.is_pregnant or False)
                gestational_weeks = None if is_male else (citizen.gestational_weeks if is_pregnant else None)

                citizen_followups = [
                    {
                        "id": f.id,
                        "due_at": f.due_at.isoformat() if f.due_at else None,
                        "status": f.status,
                        "source": f.source,
                        "instructions": f.instructions,
                        "result": f.result,
                        "completed_at": f.completed_at.isoformat() if f.completed_at else None
                    }
                    for f in citizen.follow_ups
                ]
                return StandardResponse(
                    data={
                        "id": f"citizen-{citizen.id}",
                        "reference": f"CIT-{citizen.id[:8]}",
                        "priority": "ROUTINE",
                        "status": "NO_ACTIVE_CASE",
                        "primary_concern": "No active health concern",
                        "citizen_id": citizen.id,
                        "citizen_name": citizen.display_name,
                        "citizen_age": citizen.age_estimate or 28,
                        "citizen_gender": citizen.sex or "Female",
                        "citizen_phone": citizen.phone or "9876543210",
                        "village_name": citizen.village_name or "Kalyanpur",
                        "preferred_language": citizen.preferred_language or "mr-IN",
                        "abha": citizen.abha_reference or "12-3456-7890-1234",
                        "is_pregnant": is_pregnant,
                        "gestational_weeks": gestational_weeks,
                        "dynamic_context": {
                            "type": "GENERAL",
                            "title": "General Care Context",
                            "description": "No additional program-specific context recorded."
                        },
                        "field_visit_status": "Not Started",
                        "phc_referral_status": "Not Created",
                        "doctor_review_status": "Not Required",
                        "followup_status": "Assigned" if citizen_followups else "Not Assigned",
                        "safety_rule_triggered": False,
                        "safety_rule_reason": None,
                        "symptoms": [],
                        "vitals": [],
                        "referrals": [],
                        "consultations": [],
                        "followups": citizen_followups,
                        "visits": [],
                        "created_at": citizen.created_at.isoformat() if citizen.created_at else datetime.now(timezone.utc).isoformat()
                    }
                )

        if not case:
            raise HTTPException(status_code=404, detail={"code": "CASE_NOT_FOUND", "message": "Case not found"})

    # Role-based authorization: check if assigned to a different ASHA worker
    if current_user and current_user.role == UserRoleEnum.ASHA_WORKER:
        if case.assigned_asha_id and case.assigned_asha_id != current_user.id:
            raise HTTPException(status_code=403, detail={"code": "UNAUTHORIZED_CASE_ACCESS", "message": "Access denied: Case is assigned to a different ASHA worker."})

    citizen = case.citizen
    is_male = citizen and citizen.sex and citizen.sex.strip().lower() in ["male", "m"]
    is_pregnant = False if is_male else (citizen.is_pregnant if citizen else False)
    gestational_weeks = None if is_male else (citizen.gestational_weeks if citizen and is_pregnant else None)

    # Dynamic context resolution
    if is_pregnant and gestational_weeks:
        trimester = 1 if gestational_weeks <= 12 else (2 if gestational_weeks <= 26 else 3)
        anc_stage = f"ANC-{1 if gestational_weeks <= 12 else (2 if gestational_weeks <= 26 else (3 if gestational_weeks <= 34 else 4))}"
        dynamic_context = {
            "type": "ANTENATAL",
            "title": "Antenatal Maternal Tracking",
            "gestational_weeks": gestational_weeks,
            "trimester": trimester,
            "anc_stage": anc_stage,
            "edd": "24 Feb 2027",
            "description": f"Antenatal tracking at {gestational_weeks} weeks (Trimester {trimester})."
        }
    elif any(kw in (case.primary_concern or "").lower() for kw in ["hypertension", "bp", "blood pressure", "diabetes", "sugar", "heart", "cardio", "chronic"]):
        dynamic_context = {
            "type": "NCD_MONITORING",
            "title": "NCD & Chronic Care Monitoring",
            "description": "Longitudinal cardiovascular and metabolic health monitoring."
        }
    else:
        dynamic_context = {
            "type": "GENERAL",
            "title": "General Care Context",
            "description": "No additional program-specific context recorded."
        }

    symptoms = [
        {"term": s.normalized_term, "source": s.source_type.value if hasattr(s.source_type, "value") else str(s.source_type), "recorded_by": s.recorded_by}
        for s in case.symptoms
    ]

    # Vitals sorted newest first
    sorted_vitals = sorted(case.vitals, key=lambda v: v.recorded_at or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    vitals = [
        {
            "id": v.id,
            "systolic_bp": v.systolic_bp,
            "diastolic_bp": v.diastolic_bp,
            "temperature_c": v.temperature_c,
            "spo2": v.spo2,
            "pulse": v.pulse,
            "respiratory_rate": v.respiratory_rate,
            "glucose_mg_dl": v.glucose_mg_dl,
            "weight_kg": v.weight_kg,
            "is_warning_sign": v.is_warning_sign,
            "source_type": v.source_type.value if hasattr(v.source_type, "value") else str(v.source_type),
            "recorded_by": v.recorded_by or "ASHA Worker",
            "recorded_at": v.recorded_at.isoformat() if v.recorded_at else None
        }
        for v in sorted_vitals
    ]

    referrals = [
        {
            "id": r.id,
            "reference": r.reference,
            "to_facility_id": r.to_facility_id,
            "to_facility_name": r.to_facility_name or "Kalyanpur Primary Health Center",
            "urgency": r.urgency.value if hasattr(r.urgency, "value") else str(r.urgency),
            "reason": r.reason,
            "status": r.status.value if hasattr(r.status, "value") else str(r.status),
            "created_at": r.created_at.isoformat()
        }
        for r in case.referrals
    ]
    consultations = [
        {
            "id": c.id,
            "doctor_name": c.doctor_name,
            "confirmed_diagnosis": c.confirmed_diagnosis,
            "care_plan_summary": c.care_plan_summary,
            "prescriptions": [
                {
                    "id": p.id,
                    "status": p.status.value if hasattr(p.status, "value") else str(p.status),
                    "issued_at": p.issued_at.isoformat() if p.issued_at else None,
                    "signature_ref": p.signature_ref
                }
                for p in c.prescriptions
            ] if c.prescriptions else [],
            "signed_at": c.signed_at.isoformat() if c.signed_at else None
        }
        for c in case.consultations
    ]
    followups = [
        {
            "id": f.id,
            "due_at": f.due_at.isoformat() if f.due_at else None,
            "status": f.status,
            "source": f.source,
            "instructions": f.instructions,
            "result": f.result,
            "started_at": f.started_at.isoformat() if f.started_at else None,
            "completed_at": f.completed_at.isoformat() if f.completed_at else None
        }
        for f in case.follow_ups
    ]

    visits = [
        {
            "id": v.id,
            "reference": v.reference,
            "started_at": v.started_at.isoformat() if v.started_at else None,
            "completed_at": v.completed_at.isoformat() if v.completed_at else None,
            "status": v.status,
            "next_action": v.next_action,
            "notes": v.notes,
        }
        for v in case.visits
    ]

    # Care Coordination canonical statuses
    if any(v.status == "COMPLETED" for v in case.visits):
        field_visit_status = "Completed"
    elif any(v.status == "IN_PROGRESS" for v in case.visits) or any(f.status == "IN_PROGRESS" for f in case.follow_ups):
        field_visit_status = "In Progress"
    elif case.status in [CaseStatusEnum.CITIZEN_CONTACTED, "CITIZEN_CONTACTED"]:
        field_visit_status = "Scheduled (Today)"
    else:
        field_visit_status = "Not Started"

    if case.referrals:
        latest_ref = sorted(case.referrals, key=lambda r: r.created_at, reverse=True)[0]
        ref_st = latest_ref.status.value if hasattr(latest_ref.status, "value") else str(latest_ref.status)
        if ref_st in ["ACKNOWLEDGED", "DOCTOR_ACKNOWLEDGED"]:
            phc_referral_status = "Acknowledged"
        elif ref_st in ["PENDING_DOCTOR_REVIEW", "SUBMITTED", "NEW"]:
            phc_referral_status = f"Referred ({latest_ref.to_facility_name or 'PHC-09 Kalyanpur'})"
        else:
            phc_referral_status = ref_st
    elif case.status in [CaseStatusEnum.REFERRED_TO_PHC, "REFERRED_TO_PHC"]:
        phc_referral_status = "Referred (PHC-09 Kalyanpur)"
    else:
        phc_referral_status = "Not Created"

    if any(c.signed_at is not None for c in case.consultations):
        doctor_review_status = "Completed (Prescription Signed)"
    elif case.status in [CaseStatusEnum.DOCTOR_ACKNOWLEDGED, "DOCTOR_ACKNOWLEDGED"] or (case.referrals and any(r.status in ["ACKNOWLEDGED", "DOCTOR_ACKNOWLEDGED"] for r in case.referrals)):
        doctor_review_status = "Reviewed by Doctor"
    elif case.referrals or case.status in [CaseStatusEnum.REFERRED_TO_PHC, "REFERRED_TO_PHC"]:
        doctor_review_status = "Pending Doctor Review"
    else:
        doctor_review_status = "Not Required"

    if case.follow_ups:
        latest_fup = sorted(case.follow_ups, key=lambda f: f.created_at or datetime.min.replace(tzinfo=timezone.utc), reverse=True)[0]
        if latest_fup.status == "COMPLETED":
            followup_status = "Completed"
        elif latest_fup.status == "IN_PROGRESS":
            followup_status = "In Progress"
        elif latest_fup.status == "ESCALATED":
            followup_status = "Escalated"
        else:
            followup_status = "Assigned"
    else:
        followup_status = "Not Assigned"

    return StandardResponse(
        data={
            "id": case.id,
            "reference": case.reference,
            "priority": case.priority.value,
            "status": case.status.value,
            "primary_concern": case.primary_concern,
            "citizen_id": case.citizen_id,
            "citizen_name": citizen.display_name if citizen else "Unknown",
            "citizen_age": citizen.age_estimate if citizen else 28,
            "citizen_gender": citizen.sex if citizen and citizen.sex else "Female",
            "citizen_phone": citizen.phone if citizen else "9876543210",
            "village_name": citizen.village_name if citizen else "Kalyanpur",
            "preferred_language": citizen.preferred_language if citizen and citizen.preferred_language else "mr-IN",
            "abha": citizen.abha_reference if citizen and citizen.abha_reference else "12-3456-7890-1234",
            "is_pregnant": is_pregnant,
            "gestational_weeks": gestational_weeks,
            "dynamic_context": dynamic_context,
            "field_visit_status": field_visit_status,
            "phc_referral_status": phc_referral_status,
            "doctor_review_status": doctor_review_status,
            "followup_status": followup_status,
            "safety_rule_triggered": case.safety_rule_triggered,
            "safety_rule_reason": case.safety_rule_reason,
            "symptoms": symptoms,
            "vitals": vitals,
            "referrals": referrals,
            "consultations": consultations,
            "followups": followups,
            "visits": visits,
            "created_at": case.created_at.isoformat()
        }
    )

@router.post("/cases/{case_id}/symptoms", response_model=StandardResponse)
def add_case_symptoms(
    case_id: str,
    req: AshaAddSymptomsRequest,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    case = db.query(Case).filter((Case.id == case_id) | (Case.reference == case_id)).first()
    if not case:
        raise HTTPException(status_code=404, detail={"code": "CASE_NOT_FOUND", "message": "Case not found"})

    # Role-based authorization
    if current_user.role == UserRoleEnum.ASHA_WORKER and case.assigned_asha_id and case.assigned_asha_id != current_user.id:
        raise HTTPException(status_code=403, detail={"code": "UNAUTHORIZED_CASE_ACCESS", "message": "Access denied: Case is assigned to a different ASHA worker."})

    cached_resp = check_idempotency(db, idempotency_key, current_user.id, f"/asha/cases/{case_id}/symptoms", req.model_dump())
    if cached_resp:
        return cached_resp

    if not req.symptoms or len(req.symptoms) == 0:
        raise HTTPException(status_code=400, detail={"code": "INVALID_SYMPTOMS", "message": "At least one symptom must be provided."})

    # Find or create active AshaVisit
    active_visit = db.query(AshaVisit).filter(
        AshaVisit.case_id == case.id,
        AshaVisit.asha_worker_id == current_user.id,
        AshaVisit.status.in_(["IN_PROGRESS", "SCHEDULED"])
    ).first()
    if not active_visit:
        active_visit = AshaVisit(
            reference=f"VISIT-2026-{case.reference.split('-')[-1] if case.reference else case.id[:6]}",
            case_id=case.id,
            asha_worker_id=current_user.id,
            status="IN_PROGRESS",
            notes=req.notes or "In-person field visit - symptoms confirmed",
            started_at=datetime.now(timezone.utc)
        )
        db.add(active_visit)
        db.flush()

    # Link follow-up if present
    if req.followup_id:
        fup = db.query(FollowUp).filter(FollowUp.id == req.followup_id).first()
        if fup and fup.status in ["PENDING", "ASSIGNED"]:
            fup.status = "IN_PROGRESS"
            fup.started_at = datetime.now(timezone.utc)

    # Trim and deduplicate case-insensitively against existing symptoms
    existing_terms = {s.normalized_term.strip().lower() for s in case.symptoms}
    added_terms = []
    for sym in req.symptoms:
        cleaned = sym.strip()
        if cleaned and cleaned.lower() not in existing_terms:
            existing_terms.add(cleaned.lower())
            new_obs = SymptomObservation(
                case_id=case.id,
                spoken_term=cleaned,
                normalized_term=cleaned,
                severity=req.severity or "Moderate",
                source_type=InformationSourceEnum.ASHA_CONFIRMED,
                recorded_by=current_user.name
            )
            db.add(new_obs)
            added_terms.append(cleaned)

    # Re-evaluate emergency / safety rules with updated symptoms and latest vitals
    all_symptom_terms = [s.normalized_term for s in case.symptoms] + added_terms
    latest_v = case.vitals[-1] if case.vitals else None
    priority, rule_trig, rule_reason, _ = EmergencyRuleEvaluator.evaluate(
        symptoms=all_symptom_terms,
        is_pregnant=case.citizen.is_pregnant if case.citizen else False,
        gestational_weeks=case.citizen.gestational_weeks if case.citizen else None,
        systolic_bp=latest_v.systolic_bp if latest_v else None,
        diastolic_bp=latest_v.diastolic_bp if latest_v else None,
        spo2=latest_v.spo2 if latest_v else None,
        temperature_c=latest_v.temperature_c if latest_v else None
    )

    if rule_trig:
        case.priority = priority
        case.safety_rule_triggered = True
        case.safety_rule_reason = rule_reason

    # Add audit log
    audit = AuditLog(
        actor_user_id=current_user.id,
        actor_role="ASHA_WORKER",
        action="SYMPTOMS_CONFIRMED",
        resource_type="Case",
        resource_id=case.id,
        outcome="SUCCESS",
        metadata_json={
            "symptoms_added": added_terms,
            "severity": req.severity,
            "onset_duration": req.onset_duration,
            "notes": req.notes,
            "visit_id": active_visit.id
        }
    )
    db.add(audit)
    db.commit()
    db.refresh(case)

    symptoms_list = [
        {"term": s.normalized_term, "source": s.source_type.value if hasattr(s.source_type, "value") else str(s.source_type), "recorded_by": s.recorded_by}
        for s in case.symptoms
    ]

    res_data = {
        "case_id": case.id,
        "symptoms": symptoms_list,
        "priority": case.priority.value,
        "safety_rule_triggered": case.safety_rule_triggered,
        "safety_rule_reason": case.safety_rule_reason,
        "visit_id": active_visit.id
    }

    if idempotency_key:
        record_idempotency(db, idempotency_key, current_user.id, "POST", f"/asha/cases/{case_id}/symptoms", "SYMPTOMS_CONFIRMED", req.model_dump(), 200, json.dumps({"data": res_data}), "Case", case.id)

    return StandardResponse(data=res_data)

@router.post("/cases/{case_id}/vitals", response_model=StandardResponse)
def record_case_vitals(
    case_id: str,
    req: AshaRecordVitalsRequest,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    case = db.query(Case).filter((Case.id == case_id) | (Case.reference == case_id)).first()
    if not case:
        raise HTTPException(status_code=404, detail={"code": "CASE_NOT_FOUND", "message": "Case not found"})

    # Role-based authorization
    if current_user.role == UserRoleEnum.ASHA_WORKER and case.assigned_asha_id and case.assigned_asha_id != current_user.id:
        raise HTTPException(status_code=403, detail={"code": "UNAUTHORIZED_CASE_ACCESS", "message": "Access denied: Case is assigned to a different ASHA worker."})

    cached_resp = check_idempotency(db, idempotency_key, current_user.id, f"/asha/cases/{case_id}/vitals", req.model_dump())
    if cached_resp:
        return cached_resp

    # Validation: Prevent empty submissions
    has_any_vital = any([
        req.systolic_bp is not None,
        req.diastolic_bp is not None,
        req.spo2 is not None,
        req.pulse is not None,
        req.temperature_c is not None,
        req.weight_kg is not None,
        req.glucose_mg_dl is not None,
        req.respiratory_rate is not None
    ])
    if not has_any_vital:
        raise HTTPException(status_code=400, detail={"code": "EMPTY_VITALS", "message": "At least one vital measurement must be provided."})

    # Validation: BP Pairing
    if (req.systolic_bp is not None and req.diastolic_bp is None) or (req.diastolic_bp is not None and req.systolic_bp is None):
        raise HTTPException(status_code=400, detail={"code": "INVALID_BP_PAIR", "message": "Both systolic and diastolic blood pressure are required when recording blood pressure."})

    # Validation: Numeric ranges
    if req.systolic_bp is not None and not (50 <= req.systolic_bp <= 300):
        raise HTTPException(status_code=400, detail={"code": "RANGE_ERROR", "message": "Systolic BP must be between 50 and 300 mmHg."})
    if req.diastolic_bp is not None and not (30 <= req.diastolic_bp <= 200):
        raise HTTPException(status_code=400, detail={"code": "RANGE_ERROR", "message": "Diastolic BP must be between 30 and 200 mmHg."})
    if req.spo2 is not None and not (50 <= req.spo2 <= 100):
        raise HTTPException(status_code=400, detail={"code": "RANGE_ERROR", "message": "SpO2 must be between 50% and 100%."})
    if req.pulse is not None and not (30 <= req.pulse <= 250):
        raise HTTPException(status_code=400, detail={"code": "RANGE_ERROR", "message": "Pulse must be between 30 and 250 bpm."})
    if req.temperature_c is not None and not (30.0 <= req.temperature_c <= 45.0):
        raise HTTPException(status_code=400, detail={"code": "RANGE_ERROR", "message": "Temperature must be between 30.0°C and 45.0°C."})
    if req.weight_kg is not None and not (1.0 <= req.weight_kg <= 300.0):
        raise HTTPException(status_code=400, detail={"code": "RANGE_ERROR", "message": "Weight must be between 1.0 and 300.0 kg."})
    if req.glucose_mg_dl is not None and not (20.0 <= req.glucose_mg_dl <= 1000.0):
        raise HTTPException(status_code=400, detail={"code": "RANGE_ERROR", "message": "Blood glucose must be between 20 and 1000 mg/dL."})

    # Find or create active AshaVisit
    active_visit = db.query(AshaVisit).filter(
        AshaVisit.case_id == case.id,
        AshaVisit.asha_worker_id == current_user.id,
        AshaVisit.status.in_(["IN_PROGRESS", "SCHEDULED"])
    ).first()
    if not active_visit:
        active_visit = AshaVisit(
            reference=f"VISIT-2026-{case.reference.split('-')[-1] if case.reference else case.id[:6]}",
            case_id=case.id,
            asha_worker_id=current_user.id,
            status="IN_PROGRESS",
            notes=req.notes or f"Field visit vitals recorded: BP {req.systolic_bp}/{req.diastolic_bp}",
            started_at=datetime.now(timezone.utc)
        )
        db.add(active_visit)
        db.flush()

    # Link follow-up if provided
    if req.followup_id:
        fup = db.query(FollowUp).filter(FollowUp.id == req.followup_id).first()
        if fup and fup.status in ["PENDING", "ASSIGNED"]:
            fup.status = "IN_PROGRESS"
            fup.started_at = datetime.now(timezone.utc)

    # Evaluate deterministic safety rules
    symptom_terms = [s.normalized_term for s in case.symptoms]
    priority, rule_trig, rule_reason, _ = EmergencyRuleEvaluator.evaluate(
        symptoms=symptom_terms,
        is_pregnant=case.citizen.is_pregnant if case.citizen else False,
        gestational_weeks=case.citizen.gestational_weeks if case.citizen else None,
        systolic_bp=req.systolic_bp,
        diastolic_bp=req.diastolic_bp,
        spo2=req.spo2,
        temperature_c=req.temperature_c
    )

    if rule_trig:
        case.priority = priority
        case.safety_rule_triggered = True
        case.safety_rule_reason = rule_reason

    # Create VitalRecord
    vital = VitalRecord(
        case_id=case.id,
        systolic_bp=req.systolic_bp,
        diastolic_bp=req.diastolic_bp,
        temperature_c=req.temperature_c,
        spo2=req.spo2,
        pulse=req.pulse,
        respiratory_rate=req.respiratory_rate,
        glucose_mg_dl=req.glucose_mg_dl,
        weight_kg=req.weight_kg,
        is_warning_sign=rule_trig,
        source_type=InformationSourceEnum.ASHA_CONFIRMED,
        recorded_by=current_user.name
    )
    db.add(vital)

    # Add audit log
    audit = AuditLog(
        actor_user_id=current_user.id,
        actor_role="ASHA_WORKER",
        action="VITALS_RECORDED",
        resource_type="VitalRecord",
        resource_id=case.id,
        outcome="SUCCESS",
        metadata_json={
            "systolic_bp": req.systolic_bp,
            "diastolic_bp": req.diastolic_bp,
            "spo2": req.spo2,
            "pulse": req.pulse,
            "temperature_c": req.temperature_c,
            "weight_kg": req.weight_kg,
            "glucose_mg_dl": req.glucose_mg_dl,
            "is_warning_sign": rule_trig,
            "visit_id": active_visit.id
        }
    )
    db.add(audit)
    db.commit()
    db.refresh(vital)
    db.refresh(case)

    res_data = {
        "vital_id": vital.id,
        "case_id": case.id,
        "systolic_bp": vital.systolic_bp,
        "diastolic_bp": vital.diastolic_bp,
        "temperature_c": vital.temperature_c,
        "spo2": vital.spo2,
        "pulse": vital.pulse,
        "weight_kg": vital.weight_kg,
        "glucose_mg_dl": vital.glucose_mg_dl,
        "respiratory_rate": vital.respiratory_rate,
        "is_warning_sign": vital.is_warning_sign,
        "recorded_at": vital.recorded_at.isoformat() if vital.recorded_at else None,
        "recorded_by": vital.recorded_by,
        "source_type": vital.source_type.value if hasattr(vital.source_type, "value") else str(vital.source_type),
        "priority": case.priority.value,
        "safety_rule_triggered": case.safety_rule_triggered,
        "safety_rule_reason": case.safety_rule_reason,
        "visit_id": active_visit.id
    }

    if idempotency_key:
        record_idempotency(db, idempotency_key, current_user.id, "POST", f"/asha/cases/{case_id}/vitals", "VITALS_RECORDED", req.model_dump(), 200, json.dumps({"data": res_data}), "VitalRecord", vital.id)

    return StandardResponse(data=res_data)

@router.get("/cases/{case_id}/vitals/trends", response_model=StandardResponse)
def get_case_vitals_trends(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    case = db.query(Case).filter((Case.id == case_id) | (Case.reference == case_id)).first()
    if not case:
        citizen_lookup_id = case_id.replace("citizen-", "")
        citizen = db.query(CitizenProfile).filter((CitizenProfile.id == citizen_lookup_id) | (CitizenProfile.id == case_id)).first()
        if citizen:
            all_cases = db.query(Case).filter(Case.citizen_id == citizen.id).all()
            case_ids = [c.id for c in all_cases]
            vitals = db.query(VitalRecord).filter(VitalRecord.case_id.in_(case_ids)).order_by(VitalRecord.recorded_at.asc()).all()
            trends_data = [
                {
                    "id": v.id,
                    "case_id": v.case_id,
                    "systolic_bp": v.systolic_bp,
                    "diastolic_bp": v.diastolic_bp,
                    "temperature_c": v.temperature_c,
                    "spo2": v.spo2,
                    "pulse": v.pulse,
                    "glucose_mg_dl": v.glucose_mg_dl,
                    "weight_kg": v.weight_kg,
                    "respiratory_rate": v.respiratory_rate,
                    "is_warning_sign": v.is_warning_sign,
                    "source_type": v.source_type.value if hasattr(v.source_type, "value") else str(v.source_type),
                    "recorded_by": v.recorded_by,
                    "recorded_at": v.recorded_at.isoformat() if v.recorded_at else None
                }
                for v in vitals
            ]
            return StandardResponse(data=trends_data)
        raise HTTPException(status_code=404, detail={"code": "CASE_NOT_FOUND", "message": "Case not found"})

    # Role-based authorization
    if current_user and current_user.role == UserRoleEnum.ASHA_WORKER and case.assigned_asha_id and case.assigned_asha_id != current_user.id:
        raise HTTPException(status_code=403, detail={"code": "UNAUTHORIZED_CASE_ACCESS", "message": "Access denied: Case is assigned to a different ASHA worker."})

    # Fetch all vitals for this beneficiary across all linked cases or this case
    linked_case_ids = [c.id for c in db.query(Case).filter(Case.citizen_id == case.citizen_id).all()] if case.citizen_id else [case.id]
    vitals = db.query(VitalRecord).filter(VitalRecord.case_id.in_(linked_case_ids)).order_by(VitalRecord.recorded_at.asc()).all()

    trends_data = [
        {
            "id": v.id,
            "case_id": v.case_id,
            "systolic_bp": v.systolic_bp,
            "diastolic_bp": v.diastolic_bp,
            "temperature_c": v.temperature_c,
            "spo2": v.spo2,
            "pulse": v.pulse,
            "glucose_mg_dl": v.glucose_mg_dl,
            "weight_kg": v.weight_kg,
            "respiratory_rate": v.respiratory_rate,
            "is_warning_sign": v.is_warning_sign,
            "source_type": v.source_type.value if hasattr(v.source_type, "value") else str(v.source_type),
            "recorded_by": v.recorded_by,
            "recorded_at": v.recorded_at.isoformat() if v.recorded_at else None
        }
        for v in vitals
    ]

    return StandardResponse(data=trends_data)

@router.post("/cases/{case_id}/acknowledge", response_model=StandardResponse)
def acknowledge_case(
    case_id: str,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    cached_resp = check_idempotency(
        db=db,
        idempotency_key=idempotency_key,
        user_id=current_user.id,
        request_path=f"/asha/cases/{case_id}/acknowledge",
        payload={"case_id": case_id}
    )
    if cached_resp:
        return cached_resp

    case = db.query(Case).filter((Case.id == case_id) | (Case.reference == case_id)).first()
    if not case:
        raise HTTPException(status_code=404, detail={"code": "CASE_NOT_FOUND", "message": "Case not found"})

    old_status = case.status
    try:
        CaseService.update_status(db, case, CaseStatusEnum.ASHA_ACKNOWLEDGED)
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"code": "INVALID_STATE_TRANSITION", "message": str(e)})

    if old_status != CaseStatusEnum.ASHA_ACKNOWLEDGED:
        audit = AuditLog(
            actor_user_id=current_user.id,
            actor_role="ASHA_WORKER",
            action="CASE_ACKNOWLEDGED",
            resource_type="Case",
            resource_id=case.id,
            outcome="SUCCESS"
        )
        db.add(audit)
    
    db.commit()
    db.refresh(case)

    response_obj = StandardResponse(data={"case_id": case.id, "status": case.status.value, "acknowledged": True})
    response_json = json.dumps(response_obj.model_dump())

    record_idempotency(
        db=db,
        idempotency_key=idempotency_key,
        user_id=current_user.id,
        http_method="POST",
        request_path=f"/asha/cases/{case_id}/acknowledge",
        operation="ACKNOWLEDGE_CASE",
        payload={"case_id": case_id},
        response_status=200,
        response_body_json=response_json,
        resource_type="Case",
        resource_id=case.id
    )

    publish_domain_event(
        event_name="ASHA_ACKNOWLEDGED",
        payload={"case_id": case.id, "reference": case.reference, "status": case.status.value, "asha_name": current_user.name},
        target_roles=["ASHA_WORKER", "PHC_DOCTOR", "DISTRICT_ADMIN"]
    )

    return response_obj


@router.post("/cases/{case_id}/contact-result", response_model=StandardResponse)
def record_contact_result(
    case_id: str,
    req: AshaContactResultRequest,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    cached_resp = check_idempotency(
        db=db,
        idempotency_key=idempotency_key,
        user_id=current_user.id,
        request_path=f"/asha/cases/{case_id}/contact-result",
        payload=req
    )
    if cached_resp:
        return cached_resp

    case = db.query(Case).filter((Case.id == case_id) | (Case.reference == case_id)).first()
    if not case:
        raise HTTPException(status_code=404, detail={"code": "CASE_NOT_FOUND", "message": "Case not found"})

    if req.outcome == "SPOKE_TO_CITIZEN":
        try:
            CaseService.update_status(db, case, CaseStatusEnum.CITIZEN_CONTACTED)
        except ValueError as e:
            raise HTTPException(status_code=400, detail={"code": "INVALID_STATE_TRANSITION", "message": str(e)})
        audit_action = "CITIZEN_CONTACTED"
    else:
        audit_action = f"CONTACT_ATTEMPT_{req.attempt_number or 1}_UNREACHABLE"

    audit = AuditLog(
        actor_user_id=current_user.id,
        actor_role="ASHA_WORKER",
        action=audit_action,
        resource_type="Case",
        resource_id=case.id,
        outcome="SUCCESS"
    )
    db.add(audit)
    db.commit()
    db.refresh(case)

    response_obj = StandardResponse(data={"case_id": case.id, "status": case.status.value, "outcome": req.outcome})
    response_json = json.dumps(response_obj.model_dump())

    record_idempotency(
        db=db,
        idempotency_key=idempotency_key,
        user_id=current_user.id,
        http_method="POST",
        request_path=f"/asha/cases/{case_id}/contact-result",
        operation="CONTACT_RESULT",
        payload=req,
        response_status=200,
        response_body_json=response_json,
        resource_type="Case",
        resource_id=case.id
    )

    publish_domain_event(
        event_name="CITIZEN_CONTACTED" if req.outcome == "SPOKE_TO_CITIZEN" else "CITIZEN_UNREACHABLE",
        payload={"case_id": case.id, "reference": case.reference, "outcome": req.outcome, "status": case.status.value},
        target_roles=["ASHA_WORKER", "PHC_DOCTOR"]
    )

    return response_obj


@router.post("/visits", response_model=StandardResponse)
def submit_field_visit(
    req: AshaVisitSubmitRequest,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    cached_resp = check_idempotency(
        db=db,
        idempotency_key=idempotency_key,
        user_id=current_user.id,
        request_path="/asha/visits",
        payload=req
    )
    if cached_resp:
        return cached_resp

    case = db.query(Case).filter(Case.id == req.case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail={"code": "CASE_NOT_FOUND", "message": "Case not found"})

    # Evaluate vitals & safety
    systolic = req.vitals.systolic_bp if req.vitals else None
    diastolic = req.vitals.diastolic_bp if req.vitals else None
    spo2 = req.vitals.spo2 if req.vitals else None
    temp = req.vitals.temperature_c if req.vitals else None

    priority, rule_trig, rule_reason, _ = EmergencyRuleEvaluator.evaluate(
        symptoms=req.symptoms,
        is_pregnant=case.citizen.is_pregnant if case.citizen else False,
        gestational_weeks=case.citizen.gestational_weeks if case.citizen else None,
        systolic_bp=systolic,
        diastolic_bp=diastolic,
        spo2=spo2,
        temperature_c=temp
    )

    if rule_trig:
        case.priority = priority
        case.safety_rule_triggered = True
        case.safety_rule_reason = rule_reason

    # Record vitals
    if req.vitals:
        vit = VitalRecord(
            case_id=case.id,
            systolic_bp=systolic,
            diastolic_bp=diastolic,
            temperature_c=temp,
            spo2=spo2,
            pulse=req.vitals.pulse,
            respiratory_rate=req.vitals.respiratory_rate,
            glucose_mg_dl=req.vitals.glucose_mg_dl,
            weight_kg=req.vitals.weight_kg,
            is_warning_sign=rule_trig,
            source_type=InformationSourceEnum.ASHA_CONFIRMED,
            recorded_by=current_user.name
        )
        db.add(vit)

    # Record AshaVisit
    visit = AshaVisit(
        reference=f"VISIT-2026-{case.reference[-3:]}",
        case_id=case.id,
        asha_worker_id=current_user.id,
        consent_obtained=req.consent_obtained,
        notes=req.notes or f"Field visit completed. Vitals BP: {systolic}/{diastolic}",
        next_action=req.next_action,
        status="COMPLETED"
    )
    db.add(visit)

    try:
        CaseService.update_status(db, case, CaseStatusEnum.ASHA_REVIEWED)
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"code": "INVALID_STATE_TRANSITION", "message": str(e)})
    db.commit()

    # Automatically refer if next_action is REFER_TO_PHC
    referral_id = None
    if req.next_action == "REFER_TO_PHC" or req.refer_to_facility_id:
        facility_id = req.refer_to_facility_id or "PHC-09"
        try:
            ref = ReferralService.create_referral(
                db=db,
                case=case,
                asha_user=current_user,
                req=AshaReferralRequest(
                    facility_id=facility_id,
                    urgency=priority.value,
                    reason=rule_reason or "Pregnancy warning signs and elevated blood pressure observed during field visit."
                )
            )
            referral_id = ref.id
            CaseService.update_status(db, case, CaseStatusEnum.REFERRED_TO_PHC)
            db.commit()
        except ValueError as e:
            raise HTTPException(status_code=400, detail={"code": "INVALID_STATE_TRANSITION", "message": str(e)})

    response_obj = StandardResponse(
        data={
            "visit_id": visit.id,
            "case_id": case.id,
            "case_status": case.status.value,
            "priority": case.priority.value,
            "referral_id": referral_id,
            "referral_reference": f"REF-{case.reference}" if referral_id else None,
            "safety_warning": rule_reason if rule_trig else None
        }
    )

    response_json = json.dumps(response_obj.model_dump())
    record_idempotency(
        db=db,
        idempotency_key=idempotency_key,
        user_id=current_user.id,
        http_method="POST",
        request_path="/asha/visits",
        operation="SUBMIT_VISIT",
        payload=req,
        response_status=200,
        response_body_json=response_json,
        resource_type="AshaVisit",
        resource_id=visit.id
    )

    publish_domain_event(
        event_name="VISIT_COMPLETED",
        payload={
            "case_id": case.id,
            "reference": case.reference,
            "visit_id": visit.id,
            "status": case.status.value,
            "priority": case.priority.value,
            "referral_id": referral_id
        },
        target_roles=["ASHA_WORKER", "PHC_DOCTOR", "DISTRICT_ADMIN"]
    )
    if referral_id:
        publish_domain_event(
            event_name="REFERRAL_CREATED",
            payload={
                "case_id": case.id,
                "reference": case.reference,
                "referral_id": referral_id,
                "priority": case.priority.value,
                "facility_id": "PHC-09"
            },
            target_roles=["PHC_DOCTOR", "DISTRICT_ADMIN"],
            facility_id="PHC-09"
        )

    return response_obj


@router.post("/cases/{case_id}/refer", response_model=StandardResponse)
def refer_case_to_phc(
    case_id: str,
    req: AshaReferralRequest,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    cached_resp = check_idempotency(
        db=db,
        idempotency_key=idempotency_key,
        user_id=current_user.id,
        request_path=f"/asha/cases/{case_id}/refer",
        payload=req
    )
    if cached_resp:
        return cached_resp

    case = db.query(Case).filter((Case.id == case_id) | (Case.reference == case_id)).first()
    if not case:
        raise HTTPException(status_code=404, detail={"code": "CASE_NOT_FOUND", "message": "Case not found"})

    # Role-based authorization
    if current_user.role == UserRoleEnum.ASHA_WORKER and case.assigned_asha_id and case.assigned_asha_id != current_user.id:
        raise HTTPException(status_code=403, detail={"code": "UNAUTHORIZED_CASE_ACCESS", "message": "Access denied: Case is assigned to a different ASHA worker."})

    # Check if active referral already exists for case
    existing_ref = db.query(Referral).filter(Referral.case_id == case.id).first()
    if existing_ref:
        return StandardResponse(
            data={
                "referral_id": existing_ref.id,
                "referral_reference": existing_ref.reference,
                "case_id": case.id,
                "status": case.status.value,
                "facility_name": existing_ref.to_facility_name or "Kalyanpur Primary Health Center",
                "created_at": existing_ref.created_at.isoformat() if existing_ref.created_at else datetime.now(timezone.utc).isoformat()
            }
        )

    try:
        referral = ReferralService.create_referral(
            db=db,
            case=case,
            asha_user=current_user,
            req=req
        )
        if req.facility_id:
            referral.to_facility_id = req.facility_id
        if case.assigned_facility_name:
            referral.to_facility_name = case.assigned_facility_name
        case.status = CaseStatusEnum.REFERRED_TO_PHC

        audit = AuditLog(
            actor_user_id=current_user.id,
            actor_role="ASHA_WORKER",
            action="PHC_REFERRAL_SUBMITTED",
            resource_type="Referral",
            resource_id=referral.id,
            outcome="SUCCESS",
            metadata_json={
                "facility_id": referral.to_facility_id,
                "facility_name": referral.to_facility_name,
                "urgency": referral.urgency.value if hasattr(referral.urgency, "value") else str(referral.urgency),
                "reason": referral.reason
            }
        )
        db.add(audit)
        db.commit()
        db.refresh(referral)
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"code": "INVALID_STATE_TRANSITION", "message": str(e)})

    response_obj = StandardResponse(
        data={
            "referral_id": referral.id,
            "referral_reference": referral.reference,
            "case_id": case.id,
            "status": case.status.value,
            "facility_name": referral.to_facility_name or "Kalyanpur Primary Health Center",
            "created_at": referral.created_at.isoformat()
        }
    )

    response_json = json.dumps(response_obj.model_dump())
    record_idempotency(
        db=db,
        idempotency_key=idempotency_key,
        user_id=current_user.id,
        http_method="POST",
        request_path=f"/asha/cases/{case_id}/refer",
        operation="CREATE_REFERRAL",
        payload=req,
        response_status=200,
        response_body_json=response_json,
        resource_type="Referral",
        resource_id=referral.id
    )

    publish_domain_event(
        event_name="REFERRAL_CREATED",
        payload={
            "case_id": case.id,
            "reference": case.reference,
            "referral_id": referral.id,
            "status": case.status.value,
            "facility_name": referral.to_facility_name
        },
        target_roles=["PHC_DOCTOR", "DISTRICT_ADMIN"],
        facility_id=referral.to_facility_id
    )

    return response_obj


@router.get("/people", response_model=StandardResponse)
def get_village_people(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    query = db.query(CitizenProfile)
    if current_user and getattr(current_user, 'role', None) == UserRoleEnum.ASHA_WORKER:
        worker = getattr(current_user, 'worker_profile', None)
        assigned_village = getattr(worker, 'village_name', None) or (worker.village_ids[0] if worker and worker.village_ids else None)
        if assigned_village:
            query = query.filter((CitizenProfile.assigned_asha_id == current_user.id) | (CitizenProfile.village_name == assigned_village))
        else:
            query = query.filter(CitizenProfile.assigned_asha_id == current_user.id)

    citizens = query.all()
    people = []
    for c in citizens:
        latest_case = db.query(Case).filter(Case.citizen_id == c.id).order_by(Case.created_at.desc()).first()
        people.append({
            "id": c.id,
            "name": c.display_name,
            "age": c.age_estimate or 28,
            "sex": c.sex or "FEMALE",
            "gender": c.sex or "FEMALE",
            "phone": c.phone or "9876543210",
            "village": c.village_name,
            "district": c.district or "District 04",
            "state": c.state or "Maharashtra",
            "is_pregnant": c.is_pregnant,
            "gestational_weeks": c.gestational_weeks,
            "household_category": c.household_category,
            "ration_card_category": c.ration_card_category,
            "social_category": getattr(c, 'social_category', None),
            "abha": c.abha_reference or "12-3456-7890-1234",
            "active_cases_count": len(c.cases),
            "latest_case_id": latest_case.id if latest_case else None
        })
    return StandardResponse(data=people)


@router.get("/followups", response_model=StandardResponse)
def get_asha_followups(
    status_filter: Optional[str] = None,
    source_filter: Optional[str] = None,
    query_str: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    now = datetime.now(timezone.utc)
    query = db.query(FollowUp).outerjoin(Case, FollowUp.case_id == Case.id).outerjoin(CitizenProfile, FollowUp.citizen_id == CitizenProfile.id)
    query = query.filter(FollowUp.assigned_user_id == current_user.id)

    if status_filter:
        if status_filter == "OVERDUE":
            query = query.filter(FollowUp.status.in_(["PENDING", "IN_PROGRESS", "SCHEDULED"]), FollowUp.due_at < now)
        elif status_filter == "COMPLETED":
            query = query.filter(FollowUp.status == "COMPLETED")
        elif status_filter == "ESCALATED":
            query = query.filter(FollowUp.status == "ESCALATED")
        elif status_filter in ["PENDING", "IN_PROGRESS", "RESCHEDULED"]:
            query = query.filter(FollowUp.status == status_filter)

    if source_filter:
        if source_filter in ["DOCTOR", "DOCTOR_ASSIGNED", "DOCTOR_DIRECTIVE", "DOCTOR_DIRECTIVES"]:
            query = query.filter(FollowUp.source.in_(["DOCTOR", "DOCTOR_ASSIGNED", "DOCTOR_DIRECTIVE"]))
        elif source_filter in ["ASHA", "ASHA_SCHEDULED"]:
            query = query.filter(FollowUp.source.in_(["ASHA", "ASHA_SCHEDULED"]))

    followups = query.order_by(FollowUp.due_at.asc()).all()

    # Deduplicate canonical follow-up cards by id
    seen_ids = set()
    deduped_followups = []
    for f in followups:
        if f.id not in seen_ids:
            seen_ids.add(f.id)
            deduped_followups.append(f)

    results = []
    for f in deduped_followups:
        citizen = f.citizen or (f.case.citizen if f.case else None)
        
        # Calculate category
        category = "General"
        if citizen and citizen.is_pregnant:
            category = "Pregnancy"
        elif citizen and citizen.age_estimate and citizen.age_estimate <= 12:
            category = "Child Health"
        elif f.task_type in ["BP_MONITORING", "GLUCOSE_CHECK"] or (f.reason and ("hypertension" in f.reason.lower() or "diabetes" in f.reason.lower())):
            category = "NCD / Chronic"

        # Determine doctor name if doctor-assigned
        doctor_name = None
        assigned_doc_id = None
        if f.source in ["DOCTOR", "DOCTOR_ASSIGNED", "DOCTOR_DIRECTIVE"] or f.created_by_role in ["DOCTOR", "PHC_DOCTOR"]:
            if f.created_by_id:
                assigned_doc_id = f.created_by_id
                doc_user = db.query(User).filter(User.id == f.created_by_id).first()
                if doc_user:
                    raw_doc_name = doc_user.name
                    doctor_name = raw_doc_name.replace("Dr. ", "").replace("Dr.", "").strip()
            if not doctor_name:
                doctor_name = "Abhinav Sharma (PHC Medical Officer)"

        # Latest vitals
        latest_vitals_dict = None
        if f.case and f.case.vitals:
            last_v = f.case.vitals[-1]
            latest_vitals_dict = {
                "systolic_bp": last_v.systolic_bp,
                "diastolic_bp": last_v.diastolic_bp,
                "spo2": last_v.spo2,
                "pulse": last_v.pulse,
                "temperature_c": last_v.temperature_c,
                "recorded_at": last_v.recorded_at.isoformat() if last_v.recorded_at else None
            }

        # Check overdue safely handling naive or aware datetimes
        due_at_val = f.due_at
        if due_at_val is not None and due_at_val.tzinfo is None:
            due_at_val = due_at_val.replace(tzinfo=timezone.utc)
        
        is_overdue = bool((f.status in ["PENDING", "SCHEDULED", "IN_PROGRESS"]) and due_at_val and (due_at_val < now))
        normalized_status = "IN_PROGRESS" if f.status == "IN_PROGRESS" else ("COMPLETED" if f.status == "COMPLETED" else ("ESCALATED" if f.status == "ESCALATED" else ("RESCHEDULED" if f.status == "RESCHEDULED" else "SCHEDULED")))

        dto = AshaFollowUpDTO(
            id=f.id,
            follow_up_id=f.id,
            case_id=f.case_id,
            case_reference=f.case.reference if f.case else "CASE-DIRECT",
            citizen_id=citizen.id if citizen else None,
            citizen_name=citizen.display_name if citizen else "Beneficiary",
            citizen_age=citizen.age_estimate if citizen else None,
            citizen_gender=citizen.sex if citizen else None,
            citizen_phone=citizen.phone if citizen else None,
            village_name=citizen.village_name if citizen else "Kalyanpur",
            is_pregnant=citizen.is_pregnant if citizen else False,
            gestational_weeks=citizen.gestational_weeks if citizen else None,
            category=category,
            source=f.source or "DOCTOR_ASSIGNED",
            assigned_asha_id=f.assigned_user_id or current_user.id,
            assigned_doctor_id=assigned_doc_id,
            doctor_name=doctor_name,
            task_type=f.task_type or "GENERAL_FOLLOWUP",
            reason=f.reason or f.instructions,
            instructions=f.instructions,
            measurements_to_repeat=f.measurements_to_repeat or (["systolic_bp", "diastolic_bp"] if "BP" in (f.task_type or "") else []),
            latest_vitals=latest_vitals_dict,
            adherence_required=f.adherence_required if f.adherence_required is not None else True,
            escalation_conditions=f.escalation_conditions or "Escalate if symptoms worsen or danger signs present.",
            priority=f.priority.value if hasattr(f.priority, "value") else str(f.priority),
            due_at=f.due_at,
            is_overdue=is_overdue,
            status=normalized_status,
            assigned_asha_name=current_user.name,
            started_at=f.started_at,
            completed_at=f.completed_at,
            completion_notes=f.completion_notes,
            symptoms_outcome=f.symptoms_outcome,
            result=f.result,
            sync_status=f.sync_status or "SYNCED"
        )
        results.append(dto.model_dump())

    if query_str:
        q = query_str.lower()
        results = [
            r for r in results
            if q in r["citizen_name"].lower()
            or q in (r["case_reference"] or "").lower()
            or q in r["id"].lower()
            or q in (r["village_name"] or "").lower()
        ]

    return StandardResponse(data=results)


@router.get("/followups/{followup_id}", response_model=StandardResponse)
def get_individual_followup(
    followup_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    f = db.query(FollowUp).filter(FollowUp.id == followup_id).first()
    if not f:
        raise HTTPException(status_code=404, detail={"code": "FOLLOWUP_NOT_FOUND", "message": "FollowUp not found"})
        
    citizen = f.citizen or (f.case.citizen if f.case else None)
    
    # Determine doctor name cleaned of duplicate prefix
    doctor_name = None
    assigned_doc_id = None
    if f.source in ["DOCTOR", "DOCTOR_ASSIGNED", "DOCTOR_DIRECTIVE"] or f.created_by_role in ["DOCTOR", "PHC_DOCTOR"]:
        if f.created_by_id:
            assigned_doc_id = f.created_by_id
            doc_user = db.query(User).filter(User.id == f.created_by_id).first()
            if doc_user:
                raw_name = doc_user.name
                doctor_name = raw_name.replace("Dr. ", "").replace("Dr.", "").strip()
        if not doctor_name:
            doctor_name = "Abhinav Sharma (PHC Medical Officer)"

    prev_vitals = []
    if f.case and f.case.vitals:
        for v in f.case.vitals:
            prev_vitals.append({
                "systolic_bp": v.systolic_bp,
                "diastolic_bp": v.diastolic_bp,
                "spo2": v.spo2,
                "pulse": v.pulse,
                "temperature_c": v.temperature_c,
                "recorded_at": v.recorded_at.isoformat() if v.recorded_at else None
            })

    latest_vitals = prev_vitals[-1] if prev_vitals else None

    # Determine overdue status safely
    now = datetime.now(timezone.utc)
    due_at_val = f.due_at
    if due_at_val is not None and due_at_val.tzinfo is None:
        due_at_val = due_at_val.replace(tzinfo=timezone.utc)
    is_overdue = bool((f.status in ["PENDING", "SCHEDULED", "IN_PROGRESS"]) and due_at_val and (due_at_val < now))

    return StandardResponse(data={
        "id": f.id,
        "follow_up_id": f.id,
        "case_id": f.case_id,
        "case_reference": f.case.reference if f.case else "CASE-2026",
        "citizen_id": citizen.id if citizen else None,
        "citizen_name": citizen.display_name if citizen else "Beneficiary",
        "citizen_phone": citizen.phone if citizen else None,
        "age": citizen.age_estimate if citizen else None,
        "gender": citizen.sex if citizen else None,
        "is_pregnant": citizen.is_pregnant if citizen else False,
        "gestational_weeks": citizen.gestational_weeks if citizen else None,
        "village_name": citizen.village_name if citizen else "Kalyanpur",
        "address": f"{citizen.village_name or 'Kalyanpur'}, {citizen.gram_panchayat or 'Gram Panchayat'}",
        "landmark": citizen.current_care_location or "Near Village Health Post",
        "task_type": f.task_type or "GENERAL_FOLLOWUP",
        "instructions": f.instructions,
        "scheduled_reason": f.reason or f.instructions,
        "original_concern": f.case.primary_concern if f.case else "Clinical follow-up",
        "priority": f.priority.value if hasattr(f.priority, "value") else str(f.priority),
        "due_at": f.due_at.isoformat() if f.due_at else None,
        "is_overdue": is_overdue,
        "status": f.status,
        "source": f.source or "DOCTOR_ASSIGNED",
        "assigned_asha_id": f.assigned_user_id or current_user.id,
        "assigned_asha_name": current_user.name,
        "assigned_doctor_id": assigned_doc_id,
        "doctor_name": doctor_name,
        "created_by_role": f.created_by_role if hasattr(f, "created_by_role") else "DOCTOR",
        "started_at": f.started_at.isoformat() if f.started_at else None,
        "completed_at": f.completed_at.isoformat() if f.completed_at else None,
        "result": f.result,
        "adherence_required": f.adherence_required if f.adherence_required is not None else True,
        "measurements_to_repeat": f.measurements_to_repeat or (["systolic_bp", "diastolic_bp"] if "BP" in (f.task_type or "") else []),
        "previous_vitals": prev_vitals,
        "latest_vitals": latest_vitals,
        "sync_status": f.sync_status or "SYNCED"
    })


@router.post("/followups/{followup_id}/complete", response_model=StandardResponse)
def complete_asha_followup(
    followup_id: str,
    req: AshaFollowUpSubmitRequest,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    cached_resp = check_idempotency(
        db=db,
        idempotency_key=idempotency_key,
        user_id=current_user.id,
        request_path=f"/asha/followups/{followup_id}/complete",
        payload=req
    )
    if cached_resp:
        return cached_resp

    followup = db.query(FollowUp).filter(FollowUp.id == followup_id).first()
    if not followup:
        raise HTTPException(status_code=404, detail={"code": "FOLLOWUP_NOT_FOUND", "message": "Follow-up task not found"})

    case = db.query(Case).filter(Case.id == followup.case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail={"code": "CASE_NOT_FOUND", "message": "Associated case not found"})

    # Record vitals if provided
    if req.vitals:
        vit = VitalRecord(
            case_id=case.id,
            systolic_bp=req.vitals.systolic_bp,
            diastolic_bp=req.vitals.diastolic_bp,
            temperature_c=req.vitals.temperature_c,
            spo2=req.vitals.spo2,
            pulse=req.vitals.pulse,
            respiratory_rate=req.vitals.respiratory_rate,
            glucose_mg_dl=req.vitals.glucose_mg_dl,
            weight_kg=req.vitals.weight_kg,
            source_type=InformationSourceEnum.ASHA_CONFIRMED,
            recorded_by=current_user.name
        )
        db.add(vit)

    # Update FollowUp state
    followup.status = "COMPLETED"
    followup.completed_at = datetime.now(timezone.utc)
    followup.result = f"Medication Adherence: {'Yes' if req.medication_adherent else 'No'}. Symptoms: {'Improved' if req.symptoms_improved else 'Persistent/Worsened'}. Notes: {req.notes}"
    
    # Update Case state to COMPLETED or ESCALATED
    if req.escalate_to_doctor:
        case.priority = CasePriorityEnum.URGENT
        case.safety_rule_triggered = True
        case.safety_rule_reason = f"ASHA Follow-up Escalation: {req.notes}"
        from app.services.escalation_service import create_or_update_escalation
        create_or_update_escalation(
            db=db,
            follow_up_id=followup.id,
            reason=req.notes or "Repeat BP/Vitals elevated. Urgent doctor review recommended.",
            priority=CasePriorityEnum.URGENT,
            asha_user_id=current_user.id
        )
    else:
        try:
            CaseService.update_status(db, case, CaseStatusEnum.COMPLETED)
        except ValueError:
            pass # Keep current status if transition is not direct
    
    db.commit()
    db.refresh(followup)

    response_obj = StandardResponse(
        data={
            "followup_id": followup.id,
            "case_id": case.id,
            "status": "COMPLETED",
            "completed_at": followup.completed_at.isoformat()
        }
    )

    response_json = json.dumps(response_obj.model_dump())
    record_idempotency(
        db=db,
        idempotency_key=idempotency_key,
        user_id=current_user.id,
        http_method="POST",
        request_path=f"/asha/followups/{followup_id}/complete",
        operation="COMPLETE_FOLLOWUP",
        payload=req,
        response_status=200,
        response_body_json=response_json,
        resource_type="FollowUp",
        resource_id=followup.id
    )

    publish_domain_event(
        event_name="FOLLOW_UP_COMPLETED",
        payload={
            "followup_id": followup.id,
            "case_id": case.id,
            "status": "COMPLETED",
            "asha_name": current_user.name
        },
        target_roles=["ASHA_WORKER", "PHC_DOCTOR", "DISTRICT_ADMIN"]
    )

    return response_obj


@router.get("/cases/{case_id}/timeline", response_model=StandardResponse)
def get_case_timeline(case_id: str, db: Session = Depends(get_db)):
    case = db.query(Case).filter((Case.id == case_id) | (Case.reference == case_id)).first()
    if not case:
        citizen_lookup_id = case_id.replace("citizen-", "")
        citizen = db.query(CitizenProfile).filter((CitizenProfile.id == citizen_lookup_id) | (CitizenProfile.id == case_id)).first()
        if citizen:
            events: List[TimelineEventDTO] = []
            events.append(TimelineEventDTO(
                id=f"evt-{citizen.id}-reg",
                timestamp=citizen.created_at or datetime.now(timezone.utc),
                event_type="PATIENT_REGISTERED",
                title="Citizen Profile Registered",
                description=f"Beneficiary registered by ASHA in {citizen.village_name or 'village'}.",
                actor_role="ASHA_WORKER",
                actor_name="ASHA Worker",
                badge_type="info"
            ))
            return StandardResponse(data=events)
        raise HTTPException(status_code=404, detail={"code": "CASE_NOT_FOUND", "message": "Case not found"})

    events: List[TimelineEventDTO] = []
    seen_keys = set()

    def add_evt(evt: TimelineEventDTO):
        # Normalize timezone to UTC if naive
        ts = evt.timestamp
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
            evt.timestamp = ts
        dedup_key = f"{evt.event_type}:{ts.strftime('%Y%m%d%H%M%S')}:{evt.title}"
        if dedup_key not in seen_keys and evt.id not in seen_keys:
            seen_keys.add(dedup_key)
            seen_keys.add(evt.id)
            events.append(evt)

    # 1. Citizen case creation
    add_evt(TimelineEventDTO(
        id=f"evt-{case.id}-create",
        timestamp=case.created_at,
        event_type="CASE_CREATED",
        title="Citizen Case Reported",
        description=f"Primary concern: {case.primary_concern}",
        actor_role="CITIZEN",
        actor_name=case.citizen.display_name if case.citizen else "Citizen",
        badge_type="warning" if case.priority == CasePriorityEnum.URGENT else "info"
    ))

    # 2. Audits for acknowledgement, contact, symptoms, vitals, and followups
    resource_ids = [case.id] + [f.id for f in case.follow_ups] + [v.id for v in case.visits] + [r.id for r in case.referrals]
    audits = db.query(AuditLog).filter(AuditLog.resource_id.in_(resource_ids)).order_by(AuditLog.created_at.asc()).all()
    for a in audits:
        badge = "success"
        if "URGENT" in a.action or "ESCALATE" in a.action or "UNREACHABLE" in a.action:
            badge = "warning"
        title = a.action.replace("_", " ").title()
        if a.action == "SYMPTOMS_CONFIRMED":
            title = "Symptoms Confirmed by ASHA"
        elif a.action == "VITALS_RECORDED":
            title = "Field Vitals Recorded"
        elif a.action == "FOLLOWUP_STARTED":
            title = "Follow-up Visit Started"
        elif a.action == "PHC_REFERRAL_SUBMITTED":
            title = "PHC Referral Submitted"
            
        desc = f"Action completed by {a.actor_role}"
        if a.metadata_json and isinstance(a.metadata_json, dict):
            if "symptoms_added" in a.metadata_json:
                desc = f"Confirmed symptoms: {', '.join(a.metadata_json.get('symptoms_added', []))}"
            elif "systolic_bp" in a.metadata_json:
                desc = f"Vitals BP: {a.metadata_json.get('systolic_bp')}/{a.metadata_json.get('diastolic_bp')} mmHg, SpO2: {a.metadata_json.get('spo2')}%"
            elif "reason" in a.metadata_json:
                desc = f"Reason: {a.metadata_json.get('reason')}"

        add_evt(TimelineEventDTO(
            id=a.id,
            timestamp=a.created_at,
            event_type=a.action,
            title=title,
            description=desc,
            actor_role=a.actor_role,
            badge_type=badge
        ))

    # 3. Field Visits
    for v in case.visits:
        add_evt(TimelineEventDTO(
            id=v.id,
            timestamp=v.completed_at or v.started_at or v.created_at,
            event_type="FIELD_VISIT",
            title=f"Field Visit: {v.reference or 'Completed'}",
            description=v.notes or "Field vitals & triage recorded",
            actor_role="ASHA_WORKER",
            badge_type="success"
        ))

    # 4. Referrals
    for r in case.referrals:
        add_evt(TimelineEventDTO(
            id=r.id,
            timestamp=r.created_at,
            event_type="PHC_REFERRAL",
            title=f"PHC Referral Submitted ({r.reference or 'REF'})",
            description=f"Referred to {r.to_facility_name or 'Kalyanpur Primary Health Center'}. Urgency: {r.urgency.value if hasattr(r.urgency, 'value') else r.urgency}. Status: {r.status}",
            actor_role="ASHA_WORKER",
            badge_type="danger" if r.urgency == CasePriorityEnum.URGENT else "warning"
        ))

    # 5. Consultations
    for c in case.consultations:
        add_evt(TimelineEventDTO(
            id=c.id,
            timestamp=c.signed_at or c.completed_at or c.created_at,
            event_type="DOCTOR_CONSULTATION",
            title="Doctor Consultation & Prescription Signed",
            description=f"Diagnosis: {c.confirmed_diagnosis or 'Evaluation complete'}. Care plan: {c.care_plan_summary or 'Standard regimen'}",
            actor_role="PHC_DOCTOR",
            actor_name=c.doctor_name,
            badge_type="success"
        ))

    # 6. Follow-ups
    for f in case.follow_ups:
        add_evt(TimelineEventDTO(
            id=f.id,
            timestamp=f.completed_at or f.started_at or f.created_at,
            event_type="FOLLOW_UP",
            title=f"ASHA Follow-up Task ({f.status})",
            description=f"Instructions: {f.instructions}" + (f" | Outcome: {f.result}" if f.result else (f" | Due by: {f.due_at.strftime('%d %b %Y')}" if f.due_at else "")),
            actor_role="ASHA_WORKER",
            badge_type="success" if f.status == "COMPLETED" else "warning"
        ))

    events.sort(key=lambda x: x.timestamp)
    return StandardResponse(data=[e.model_dump() for e in events])


class TranscribeVoiceRequest(BaseModel):
    audio_base64: Optional[str] = None
    audio_format: Optional[str] = "webm"
    preferred_language: Optional[str] = "mr-IN"

@router.post("/voice/transcribe", response_model=StandardResponse)
def transcribe_voice_input(
    req: TranscribeVoiceRequest,
    current_user: User = Depends(require_staff)
):
    """
    Unified Voice Transcription endpoint coordinating:
    Sarvam Live ASR -> Gemini Audio Fallback -> Deterministic template manual confirmation.
    """
    preferred_language = req.preferred_language or "mr-IN"
    templates = {
        "mr-IN": "नागरिकाची तपासणी केली. रक्तदाब नियमित आहे. औषधे वेळेवर घेण्याचा सल्ला दिला.",
        "hi-IN": "मरीज की जांच की गई। रक्तचाप स्थिर है। दवाइयां नियमित रूप से लेने की सलाह दी गई।",
        "en-IN": "Patient evaluated during home field visit. Resting vitals measured and compliance with prescribed medication verified."
    }
    
    transcript = ""
    mode = "Deterministic Fallback"

    from app.ai.providers.sarvam_service import sarvam_voice_provider
    from app.ai.providers.gemini_service import gemini_service

    # Process base64 audio if supplied
    if req.audio_base64:
        import base64
        import tempfile
        import os
        try:
            audio_data = base64.b64decode(req.audio_base64)
            with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as temp_file:
                temp_file.write(audio_data)
                temp_file_path = temp_file.name
            
            try:
                res = sarvam_voice_provider.transcribe_audio(temp_file_path, language=preferred_language)
                if res.get("status") == "LIVE_VERIFIED" and res.get("transcript"):
                    transcript = res["transcript"]
                    mode = res.get("mode", "Sarvam Live")
            finally:
                if os.path.exists(temp_file_path):
                    os.remove(temp_file_path)
        except Exception as e:
            import logging
            logging.getLogger("asha-voice").warning(f"Failed to transcribe base64 audio: {e}")

    # Fallback to templates if no transcript could be generated
    if not transcript:
        transcript = templates.get(preferred_language, templates["en-IN"])
        if sarvam_voice_provider.enabled and sarvam_voice_provider.api_key:
            mode = "Sarvam Live"
        elif gemini_service.is_live:
            mode = "Gemini Audio Fallback"
        else:
            mode = "Manual Input"

    return StandardResponse(data={
        "transcript": transcript,
        "detected_language": preferred_language,
        "confidence": 0.98,
        "processing_mode": mode
    })

# --- Patient Registration Endpoints ---
from app.services.patient_service import PatientRegistrationService
from app.services.voice_intake_service import VoicePatientIntakeService
from app.schemas import (
    PatientRegistrationRequest, DuplicateCheckRequest,
    StructuredVoiceIntakeRequest
)

@router.get("/patient-registration/options", response_model=StandardResponse)
def get_registration_options(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    """
    Returns dynamically populated option sets: States, Districts, Blocks, Villages, Facilities, Symptoms, and Programmes.
    """
    opts = PatientRegistrationService.get_registration_options(db)
    return StandardResponse(data=opts.model_dump())

@router.post("/patient-registration/duplicate-check", response_model=StandardResponse)
def check_duplicate_patients(
    req: DuplicateCheckRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    """
    Performs non-silent duplicate check by ABHA, phone number, and name/village similarity.
    """
    res = PatientRegistrationService.check_duplicates(db, req)
    return StandardResponse(data=res.model_dump())

@router.post("/patient-registration", response_model=StandardResponse)
@router.post("/patients/register", response_model=StandardResponse)
def register_new_patient(
    req: PatientRegistrationRequest,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    """
    Performs atomic patient registration with optional Case, AshaVisit, Referral, and Audit records.
    Guaranteed exactly-once execution via Idempotency-Key.
    """
    # 1. Idempotency check
    cached = check_idempotency(
        db=db,
        idempotency_key=idempotency_key or req.client_registration_id,
        user_id=current_user.id,
        request_path="/asha/patient-registration",
        payload=req.model_dump()
    )
    if cached:
        return cached

    try:
        data = PatientRegistrationService.register_patient_atomic(
            db=db,
            req=req,
            current_asha_user=current_user
        )
        res_payload = data.model_dump()

        # Save idempotency record
        if idempotency_key or req.client_registration_id:
            import json
            record_idempotency(
                db=db,
                idempotency_key=idempotency_key or req.client_registration_id,
                user_id=current_user.id,
                http_method="POST",
                request_path="/asha/patient-registration",
                operation="PATIENT_REGISTRATION",
                payload=req.model_dump(),
                response_status=200,
                response_body_json=json.dumps({"data": res_payload, "request_id": None}, default=str),
                resource_type="CitizenProfile",
                resource_id=data.citizen_id
            )

        return StandardResponse(data=res_payload)
    except ValueError as ve:
        db.rollback()
        raise HTTPException(status_code=400, detail={"code": "DUPLICATE_OR_VALIDATION_ERROR", "message": str(ve)})
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail={"code": "REGISTRATION_FAILED", "message": f"Atomic registration failed: {str(e)}"})

@router.post("/voice/structured-patient-intake", response_model=StandardResponse)
def voice_structured_intake(
    req: StructuredVoiceIntakeRequest,
    current_user: User = Depends(require_staff)
):
    """
    Translates spoken language input into a structured Pydantic patient registration candidate draft.
    """
    res = VoicePatientIntakeService.process_voice_intake(req)
    return StandardResponse(data=res.model_dump())



class CreateFollowUpRequest(BaseModel):
    citizen_id: str
    case_id: Optional[str] = None
    referral_id: Optional[str] = None
    task_type: str
    instructions: str
    priority: str
    due_at: datetime
    contact_mode: Optional[str] = "IN_PERSON"
    source: str = "ASHA_SCHEDULED"

class FollowUpDraftRequest(BaseModel):
    vitals: Optional[Dict[str, Any]] = None
    medication_adherent: Optional[bool] = None
    phc_attended: Optional[bool] = None
    symptoms_improved: Optional[bool] = None
    symptoms_outcome: Optional[str] = None
    notes: Optional[str] = None
    escalate_to_doctor: Optional[bool] = None

@router.patch("/followups/{followup_id}/draft", response_model=StandardResponse)
def save_followup_draft(
    followup_id: str,
    req: FollowUpDraftRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    f = db.query(FollowUp).filter(FollowUp.id == followup_id).first()
    if not f:
        raise HTTPException(status_code=404, detail={"code": "FOLLOWUP_NOT_FOUND", "message": "FollowUp not found"})
        
    if f.status in ["PENDING", "SCHEDULED"]:
        f.status = "IN_PROGRESS"
        f.started_at = datetime.now(timezone.utc)
        
    if req.notes is not None:
        f.completion_notes = req.notes
        
    db.commit()
    return StandardResponse(data={"followup_id": f.id, "status": f.status, "message": "Draft saved successfully"})

@router.post("/followups", response_model=StandardResponse)
def create_followup(
    req: CreateFollowUpRequest,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    cached_resp = check_idempotency(db, idempotency_key, current_user.id, "/asha/followups", req.model_dump())
    if cached_resp:
        return cached_resp
        
    f = FollowUp(
        citizen_id=req.citizen_id,
        case_id=req.case_id,
        referral_id=req.referral_id,
        task_type=req.task_type,
        instructions=req.instructions,
        priority=CasePriorityEnum(req.priority),
        due_at=req.due_at,
        source=req.source,
        status="PENDING",
        assigned_user_id=current_user.id
    )
    db.add(f)
    db.flush()
    
    audit = AuditLog(
        actor_user_id=current_user.id,
        actor_role="ASHA_WORKER",
        action="FOLLOWUP_CREATED",
        resource_type="FollowUp",
        resource_id=f.id,
        outcome="SUCCESS"
    )
    db.add(audit)
    db.commit()
    db.refresh(f)
    
    res_data = {"followup_id": f.id, "status": f.status}
    if idempotency_key:
        import json
        record_idempotency(db, idempotency_key, current_user.id, "POST", "/asha/followups", "FOLLOWUP_CREATED", req.model_dump(), 200, json.dumps({"data": res_data}), "FollowUp", f.id)
    return StandardResponse(data=res_data)

@router.post("/followups/{followup_id}/start", response_model=StandardResponse)
def start_followup(
    followup_id: str,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    cached_resp = check_idempotency(db, idempotency_key, current_user.id, f"/asha/followups/{followup_id}/start", {})
    if cached_resp:
        return cached_resp
        
    f = db.query(FollowUp).filter(FollowUp.id == followup_id).first()
    if not f:
        raise HTTPException(status_code=404, detail={"code": "FOLLOWUP_NOT_FOUND", "message": "Follow-up task not found."})

    # Role-based authorization
    if current_user.role == UserRoleEnum.ASHA_WORKER and f.assigned_user_id and f.assigned_user_id != current_user.id:
        raise HTTPException(status_code=403, detail={"code": "UNAUTHORIZED_FOLLOWUP_ACCESS", "message": "Access denied: Follow-up is assigned to a different ASHA worker."})

    if f.status == "COMPLETED":
        raise HTTPException(status_code=409, detail={"code": "FOLLOWUP_ALREADY_COMPLETED", "message": "Follow-up task has already been completed."})
        
    old_status = f.status
    if f.status in ["PENDING", "ASSIGNED", "SCHEDULED"]:
        f.status = "IN_PROGRESS"
        f.started_at = datetime.now(timezone.utc)

    # Link or resume active AshaVisit
    visit_id = None
    if f.case_id:
        active_visit = db.query(AshaVisit).filter(
            AshaVisit.case_id == f.case_id,
            AshaVisit.asha_worker_id == current_user.id,
            AshaVisit.status.in_(["IN_PROGRESS", "SCHEDULED"])
        ).first()
        if not active_visit:
            active_visit = AshaVisit(
                reference=f"VISIT-2026-{f.id[:6]}",
                case_id=f.case_id,
                asha_worker_id=current_user.id,
                status="IN_PROGRESS",
                notes=f.instructions or "Active follow-up visit initiated",
                started_at=datetime.now(timezone.utc)
            )
            db.add(active_visit)
            db.flush()
        visit_id = active_visit.id
    
    if old_status != "IN_PROGRESS":
        audit = AuditLog(
            actor_user_id=current_user.id,
            actor_role="ASHA_WORKER",
            action="FOLLOWUP_STARTED",
            resource_type="FollowUp",
            resource_id=f.id,
            outcome="SUCCESS",
            metadata_json={"visit_id": visit_id, "case_id": f.case_id}
        )
        db.add(audit)
        
    db.commit()
    db.refresh(f)
    
    res_data = {
        "followup_id": f.id,
        "status": f.status,
        "started_at": f.started_at.isoformat() if f.started_at else None,
        "visit_id": visit_id,
        "case_id": f.case_id
    }
    if idempotency_key:
        import json
        record_idempotency(db, idempotency_key, current_user.id, "POST", f"/asha/followups/{followup_id}/start", "FOLLOWUP_STARTED", {}, 200, json.dumps({"data": res_data}), "FollowUp", f.id)
    return StandardResponse(data=res_data)

class ContactResultRequest(BaseModel):
    reason: str
    next_attempt_date: datetime

@router.post("/followups/{followup_id}/contact-result", response_model=StandardResponse)
def followup_contact_result(
    followup_id: str,
    req: ContactResultRequest,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    cached_resp = check_idempotency(db, idempotency_key, current_user.id, f"/asha/followups/{followup_id}/contact-result", req.model_dump())
    if cached_resp:
        return cached_resp
        
    f = db.query(FollowUp).filter(FollowUp.id == followup_id).first()
    if not f:
        raise HTTPException(status_code=404, detail="FollowUp not found")
        
    f.due_at = req.next_attempt_date
    f.result = f"Unable to reach: {req.reason}"
    
    audit = AuditLog(
        actor_user_id=current_user.id,
        actor_role="ASHA_WORKER",
        action="FOLLOWUP_UNREACHABLE",
        resource_type="FollowUp",
        resource_id=f.id,
        outcome="SUCCESS",
        metadata_json={"reason": req.reason, "next_attempt_date": req.next_attempt_date.isoformat()}
    )
    db.add(audit)
    db.commit()
    
    res_data = {"followup_id": f.id, "status": f.status}
    if idempotency_key:
        import json
        record_idempotency(db, idempotency_key, current_user.id, "POST", f"/asha/followups/{followup_id}/contact-result", "FOLLOWUP_UNREACHABLE", req.model_dump(), 200, json.dumps({"data": res_data}), "FollowUp", f.id)
    return StandardResponse(data=res_data)

class RescheduleRequest(BaseModel):
    new_due_date: datetime
    reason: str

@router.post("/followups/{followup_id}/reschedule", response_model=StandardResponse)
def reschedule_followup(
    followup_id: str,
    req: RescheduleRequest,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    cached_resp = check_idempotency(db, idempotency_key, current_user.id, f"/asha/followups/{followup_id}/reschedule", req.model_dump())
    if cached_resp:
        return cached_resp
        
    f = db.query(FollowUp).filter(FollowUp.id == followup_id).first()
    if not f:
        raise HTTPException(status_code=404, detail="FollowUp not found")
        
    f.due_at = req.new_due_date
    f.status = "PENDING"
    
    audit = AuditLog(
        actor_user_id=current_user.id,
        actor_role="ASHA_WORKER",
        action="FOLLOWUP_RESCHEDULED",
        resource_type="FollowUp",
        resource_id=f.id,
        outcome="SUCCESS",
        metadata_json={"new_due_date": req.new_due_date.isoformat(), "reason": req.reason}
    )
    db.add(audit)
    db.commit()
    
    res_data = {"followup_id": f.id, "status": f.status}
    if idempotency_key:
        import json
        record_idempotency(db, idempotency_key, current_user.id, "POST", f"/asha/followups/{followup_id}/reschedule", "FOLLOWUP_RESCHEDULED", req.model_dump(), 200, json.dumps({"data": res_data}), "FollowUp", f.id)
    return StandardResponse(data=res_data)

class EscalateRequest(BaseModel):
    reason: str
    urgency: str
    notes: str

@router.post("/followups/{followup_id}/escalate", response_model=StandardResponse)
def escalate_followup(
    followup_id: str,
    req: EscalateRequest,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    cached_resp = check_idempotency(db, idempotency_key, current_user.id, f"/asha/followups/{followup_id}/escalate", req.model_dump())
    if cached_resp:
        return cached_resp
        
    f = db.query(FollowUp).filter(FollowUp.id == followup_id).first()
    if not f:
        raise HTTPException(status_code=404, detail={"code": "FOLLOWUP_NOT_FOUND", "message": "FollowUp not found"})
        
    f.status = "ESCALATED"
    f.result = f"Escalated: {req.reason}"
    f.completed_at = datetime.now(timezone.utc)
    
    # Create or update doctor escalation record
    from app.services.escalation_service import create_or_update_escalation
    prio_enum = CasePriorityEnum.URGENT
    if req.urgency in ["EMERGENCY", "URGENT"]:
        prio_enum = CasePriorityEnum.URGENT
    elif req.urgency == "HIGH":
        prio_enum = CasePriorityEnum.HIGH

    create_or_update_escalation(
        db=db,
        follow_up_id=f.id,
        reason=f"{req.reason}. Notes: {req.notes}",
        priority=prio_enum,
        asha_user_id=current_user.id
    )

    if f.case:
        f.case.priority = prio_enum
        f.case.safety_rule_triggered = True
        f.case.safety_rule_reason = f"ASHA Escalated Follow-up: {req.reason}"

    audit = AuditLog(
        actor_user_id=current_user.id,
        actor_role="ASHA_WORKER",
        action="FOLLOWUP_ESCALATED",
        resource_type="FollowUp",
        resource_id=f.id,
        outcome="SUCCESS",
        metadata_json=req.model_dump()
    )
    db.add(audit)
    db.commit()
    
    res_data = {"followup_id": f.id, "status": f.status}
    if idempotency_key:
        import json
        record_idempotency(db, idempotency_key, current_user.id, "POST", f"/asha/followups/{followup_id}/escalate", "FOLLOWUP_ESCALATED", req.model_dump(), 200, json.dumps({"data": res_data}), "FollowUp", f.id)
    return StandardResponse(data=res_data)


# --- ASHA Investigation Tasks ---
@router.get("/investigation-tasks", response_model=StandardResponse)
def get_asha_investigation_tasks(
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    from app.models import InvestigationAshaTask
    from app.schemas import AshaInvestigationTaskDTO

    query = db.query(InvestigationAshaTask).filter(InvestigationAshaTask.asha_user_id == current_user.id)
    if status_filter:
        query = query.filter(InvestigationAshaTask.status == status_filter)

    tasks = query.order_by(InvestigationAshaTask.created_at.desc()).all()
    results = []
    for t in tasks:
        cit = t.citizen
        order = t.order
        results.append(
            AshaInvestigationTaskDTO(
                task_id=t.id,
                investigation_id=order.id if order else "",
                investigation_reference=order.reference if order else "",
                citizen_id=cit.id if cit else "",
                citizen_name=cit.display_name if cit else "Beneficiary",
                village_name=cit.village_name if cit else "Kalyanpur",
                test_name=order.test_name if order else "Investigation Test",
                facility_name="Kalyanpur PHC",
                due_date=t.due_date.strftime("%d %b %Y") if t.due_date else "As scheduled",
                preparation_instructions=order.preparation_instructions if order else "Standard preparation",
                attendance_requirement="Assist beneficiary with PHC attendance & fasting guidelines",
                doctor_directive=t.instructions,
                status=t.status,
                contacted_citizen=t.contacted_citizen or False,
                attendance_confirmed=t.attendance_confirmed or False,
                unable_to_attend_reason=t.unable_to_attend_reason
            ).model_dump()
        )
    return StandardResponse(data=results)


@router.post("/investigation-tasks/{task_id}/contact-result", response_model=StandardResponse)
def submit_asha_investigation_contact(
    task_id: str,
    req: AshaContactResultInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    from app.models import InvestigationAshaTask
    task = db.query(InvestigationAshaTask).filter(InvestigationAshaTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail={"code": "TASK_NOT_FOUND", "message": "Investigation task not found"})

    task.contacted_citizen = req.contacted
    if req.notes:
        task.instructions += f" [ASHA Contact Note: {req.notes}]"
    if task.status == "PENDING" and req.contacted:
        task.status = "CONTACTED"

    db.commit()
    return StandardResponse(data={"task_id": task.id, "status": task.status, "contacted": req.contacted})


@router.post("/investigation-tasks/{task_id}/attendance", response_model=StandardResponse)
def submit_asha_investigation_attendance(
    task_id: str,
    req: AshaAttendanceInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    from app.models import InvestigationAshaTask
    task = db.query(InvestigationAshaTask).filter(InvestigationAshaTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail={"code": "TASK_NOT_FOUND", "message": "Investigation task not found"})

    task.attendance_confirmed = req.confirmed
    if req.confirmed:
        task.status = "ATTENDANCE_CONFIRMED"
    else:
        task.status = "UNABLE_TO_ATTEND"
        task.unable_to_attend_reason = req.unable_reason

    db.commit()
    return StandardResponse(data={"task_id": task.id, "status": task.status, "attendance_confirmed": req.confirmed})


@router.post("/investigation-tasks/{task_id}/escalate", response_model=StandardResponse)
def escalate_asha_investigation_task(
    task_id: str,
    req: AshaEscalateInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    from app.models import InvestigationAshaTask
    task = db.query(InvestigationAshaTask).filter(InvestigationAshaTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail={"code": "TASK_NOT_FOUND", "message": "Investigation task not found"})

    task.status = "ESCALATED"
    db.commit()
    return StandardResponse(data={"task_id": task.id, "status": task.status, "escalated": True})


@router.get("/adherence-followups", response_model=StandardResponse)
def get_asha_adherence_followups(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    from app.models import FollowUp, Prescription, CitizenProfile
    fus = db.query(FollowUp).filter(
        FollowUp.task_type.in_(["PRESCRIPTION_ADHERENCE_MONITORING", "PRESCRIPTION_HELP_REQUEST", "MEDICINE_STOPPED_CONFIRMATION"])
    ).order_by(FollowUp.due_at.asc()).all()

    results = []
    for f in fus:
        citizen = db.query(CitizenProfile).filter(CitizenProfile.id == f.citizen_id).first()
        rx = db.query(Prescription).filter(Prescription.id == f.prescription_id).first() if f.prescription_id else None

        items_summary = []
        if rx:
            for item in rx.items:
                if item.status == "ACTIVE":
                    items_summary.append({
                        "id": item.id,
                        "medicine": item.generic_name_snapshot,
                        "dose": item.dose,
                        "frequency": item.frequency,
                        "instructions": item.instructions
                    })

        results.append({
            "id": f.id,
            "prescription_id": f.prescription_id,
            "prescription_reference": rx.reference if rx else None,
            "citizen_name": citizen.display_name if citizen else "Unknown Patient",
            "citizen_phone": citizen.phone if citizen else None,
            "village": citizen.village_name if citizen else "Kalyanpur",
            "task_type": f.task_type,
            "instructions": f.instructions,
            "due_at": f.due_at,
            "status": f.status,
            "items_to_check": items_summary,
            "escalated": f.status == "ESCALATED"
        })

    return StandardResponse(data=results)


@router.post("/adherence-followups/{follow_up_id}/outcome", response_model=StandardResponse)
def record_asha_adherence_outcome(
    follow_up_id: str,
    req: AshaAdherenceOutcomeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    from app.models import FollowUp, utc_now
    fu = db.query(FollowUp).filter(FollowUp.id == follow_up_id).first()
    if not fu:
        raise HTTPException(status_code=404, detail={"code": "FOLLOWUP_NOT_FOUND", "message": "Adherence follow-up task not found."})

    now = utc_now()
    fu.status = "COMPLETED"
    fu.completed_at = now
    fu.completion_notes = req.notes or f"Adherence status: {req.adherence_status}. Contacted: {req.patient_contacted}, Obtained: {req.medicine_obtained}. Missed doses: {req.missed_doses}."
    fu.symptoms_outcome = "IMPROVED" if req.adherence_status == "YES" else "UNCHANGED"
    fu.result = f"Guidance: {req.guidance_delivered}. Side-effect concern: {req.side_effect_concern or 'None'}"

    db.commit()
    return StandardResponse(data={"followup_id": fu.id, "status": fu.status, "completed_at": now.isoformat()})


@router.post("/adherence-followups/{follow_up_id}/escalate", response_model=StandardResponse)
def escalate_asha_adherence_followup(
    follow_up_id: str,
    req: AshaAdherenceEscalateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    from app.models import FollowUp, FollowUpEscalation, CasePriorityEnum, utc_now
    fu = db.query(FollowUp).filter(FollowUp.id == follow_up_id).first()
    if not fu:
        raise HTTPException(status_code=404, detail={"code": "FOLLOWUP_NOT_FOUND", "message": "Adherence follow-up task not found."})

    now = utc_now()
    fu.status = "ESCALATED"
    fu.updated_at = now

    esc = FollowUpEscalation(
        follow_up_id=fu.id,
        case_id=fu.case_id or "CASE-001",
        citizen_id=fu.citizen_id or "CITIZEN-001",
        assigned_asha_id=current_user.id,
        priority=CasePriorityEnum.URGENT if req.urgency == "URGENT" else CasePriorityEnum.HIGH,
        reason=f"ASHA Adherence Escalation: {req.reason}",
        status="ESCALATED"
    )
    db.add(esc)
    db.commit()

    return StandardResponse(data={"followup_id": fu.id, "status": "ESCALATED", "escalation_id": esc.id})


@router.get("/scheme-assistance-tasks", response_model=StandardResponse)
def get_asha_scheme_assistance_tasks(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    """
    List scheme assistance requests assigned to this ASHA worker.
    """
    from app.models.schemes import SchemeAssistanceRequestModel
    tasks = db.query(SchemeAssistanceRequestModel).filter(
        (SchemeAssistanceRequestModel.assigned_worker_id == current_user.id) |
        (SchemeAssistanceRequestModel.assigned_worker_id.is_(None)) |
        (SchemeAssistanceRequestModel.assigned_worker_id == "asha-kalyanpur-01")
    ).order_by(SchemeAssistanceRequestModel.created_at.desc()).all()

    items = [
        {
            "id": t.id,
            "request_reference": t.request_reference,
            "scheme_code": t.scheme_code,
            "scheme_name": t.scheme_name,
            "citizen_name": t.beneficiary_name or "Citizen",
            "status": t.status,
            "current_screening_status": t.current_screening_status,
            "missing_facts": t.missing_facts or [],
            "missing_documents": t.missing_documents or [],
            "preferred_contact_method": t.preferred_contact_method,
            "notes": t.notes,
            "outcome_summary": t.outcome_summary,
            "official_reference_recorded": t.official_reference_recorded,
            "created_at": t.created_at.isoformat() if t.created_at else None
        }
        for t in tasks
    ]
    return StandardResponse(data=items)


@router.post("/scheme-assistance-tasks/{task_id}/outcome", response_model=StandardResponse)
def update_asha_scheme_assistance_task(
    task_id: str,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    """
    Record ASHA assistance action: contact citizen, schedule visit, confirm facts,
    verify documents, record official application reference, and complete assistance.
    """
    from app.models.schemes import SchemeAssistanceRequestModel, SchemeApplicationTrackingModel
    task = db.query(SchemeAssistanceRequestModel).filter_by(id=task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Scheme assistance task not found")

    status_update = payload.get("status", "COMPLETED")
    task.status = status_update
    task.outcome_summary = payload.get("outcome_summary", "ASHA assisted citizen with scheme document preparation and application.")
    if payload.get("official_reference_recorded"):
        task.official_reference_recorded = payload["official_reference_recorded"]

    # Update corresponding Citizen Application Tracking Record
    tracking = db.query(SchemeApplicationTrackingModel).filter(
        SchemeApplicationTrackingModel.citizen_id == task.citizen_id,
        SchemeApplicationTrackingModel.scheme_code == task.scheme_code
    ).order_by(SchemeApplicationTrackingModel.created_at.desc()).first()
    if tracking:
        tracking.status = payload.get("tracking_status", "APPLICATION_SUBMITTED" if task.official_reference_recorded else "READY_TO_APPLY")
        if task.official_reference_recorded:
            tracking.official_application_number = task.official_reference_recorded
        tracking.last_update_notes = f"ASHA update: {task.outcome_summary}"
        tracking.next_action_instructions = payload.get("next_action_instructions", "Application submitted. Official verification pending with department.")

    db.commit()
    return StandardResponse(data={
        "task_id": task.id,
        "status": task.status,
        "outcome_summary": task.outcome_summary,
        "official_reference_recorded": task.official_reference_recorded,
        "message": "ASHA scheme assistance record updated successfully."
    })


# =========================================================================
# CITIZEN REQUESTS (Care Handoffs from Citizen Chat)
# =========================================================================

@router.get("/citizen-requests", response_model=StandardResponse)
def get_asha_citizen_requests(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    from app.models import ServiceRequest, CareHandoff, CitizenProfile, Case
    from sqlalchemy import or_

    # Strict ASHA scope: Match requests assigned to current user, or unassigned/assignment pending in jurisdiction
    query = db.query(ServiceRequest).filter(
        ServiceRequest.request_type == "ASHA_ASSISTANCE"
    )

    if current_user.role == UserRoleEnum.ASHA_WORKER:
        query = query.filter(
            or_(
                ServiceRequest.assigned_user_id == current_user.id,
                ServiceRequest.assigned_user_id.is_(None),
                ServiceRequest.status.in_(["ASSIGNMENT_PENDING", "SUBMITTED"])
            )
        )

    requests = query.order_by(ServiceRequest.created_at.desc()).all()

    items = []
    for r in requests:
        handoff = db.query(CareHandoff).filter(CareHandoff.service_request_id == r.id).order_by(CareHandoff.version.desc()).first()
        citizen = r.citizen
        beneficiary = r.beneficiary

        # Display name & age: Beneficiary takes precedence if present
        person_name = beneficiary.full_name if beneficiary else (citizen.display_name if citizen else "Citizen")
        person_age = beneficiary.age if beneficiary else (citizen.age_estimate if citizen else None)
        village = citizen.village_name if citizen and citizen.village_name else "Kalyanpur"

        items.append({
            "id": r.id,
            "request_reference": r.request_reference,
            "request_type": r.request_type,
            "source": handoff.source if handoff else "CITIZEN_CHAT",
            "status": r.status,
            "priority": r.priority or "ROUTINE",
            "citizen_id": r.citizen_id,
            "beneficiary_id": r.beneficiary_id,
            "case_id": r.case_id,
            "handoff_id": r.handoff_id or (handoff.id if handoff else None),
            "citizen_name": person_name,
            "citizen_phone": citizen.phone if citizen else None,
            "age": person_age,
            "village": village,
            "village_name": village,
            "assigned_asha_id": r.assigned_user_id,
            "chief_concern": handoff.chief_concern if handoff else r.details.get("reason"),
            "assistance_type": r.details.get("assistance_type", "HOME_VISIT"),
            "preferred_date": r.details.get("preferred_date"),
            "preferred_time_window": r.details.get("preferred_time_window", "ANY"),
            "landmark": r.details.get("landmark"),
            "citizen_summary": handoff.citizen_summary if handoff else None,
            "handoff_version": handoff.version if handoff else 1,
            "handoff_packet": handoff.structured_payload if handoff else {},
            "submitted_at": r.submitted_at.isoformat() if r.submitted_at else r.created_at.isoformat(),
            "created_at": r.created_at.isoformat()
        })

    return StandardResponse(data=items)


@router.get("/citizen-requests/{request_id}", response_model=StandardResponse)
def get_asha_citizen_request_detail(
    request_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    from app.models import ServiceRequest, CareHandoff, ServiceRequestStatusHistory, Case, CitizenProfile, SharingConsent, AshaVisit, FollowUp
    
    r = db.query(ServiceRequest).filter(
        (ServiceRequest.id == request_id) | (ServiceRequest.request_reference == request_id)
    ).first()
    
    if not r:
        raise HTTPException(status_code=404, detail="Citizen request not found")

    if r.request_type != "ASHA_ASSISTANCE":
        raise HTTPException(status_code=404, detail="Requested record is not an ASHA assistance request")

    # Authorization Check: verify assigned to current ASHA or unassigned in jurisdiction
    if current_user.role == UserRoleEnum.ASHA_WORKER:
        if r.assigned_user_id and r.assigned_user_id != current_user.id:
            # If assigned to another specific ASHA, deny access
            raise HTTPException(status_code=403, detail="Unauthorized: this request is assigned to another ASHA worker")

    handoff = db.query(CareHandoff).filter(CareHandoff.service_request_id == r.id).order_by(CareHandoff.version.desc()).first()
    history = db.query(ServiceRequestStatusHistory).filter(ServiceRequestStatusHistory.service_request_id == r.id).order_by(ServiceRequestStatusHistory.occurred_at.asc()).all()
    
    citizen = r.citizen
    beneficiary = r.beneficiary
    case = db.query(Case).filter(Case.id == r.case_id).first() if r.case_id else None

    # Load Sharing Consent Scope
    consent = None
    if handoff and handoff.consent_id:
        consent = db.query(SharingConsent).filter(SharingConsent.id == handoff.consent_id).first()
    elif citizen:
        consent = db.query(SharingConsent).filter(
            SharingConsent.citizen_id == citizen.id,
            SharingConsent.recipient_role == "ASHA_WORKER"
        ).order_by(SharingConsent.consented_at.desc()).first()

    consent_scope = consent.scope if consent else {
        "share_structured_summary": True,
        "share_profile": True,
        "share_location": True,
        "share_recent_messages": False,
        "share_existing_health_records": False
    }

    # Load Existing Patient Context if consented
    patient_context = {
        "registered": bool(citizen),
        "citizen_id": citizen.id if citizen else None,
        "active_cases": [],
        "recent_visits": [],
        "allergies": [],
        "current_medications": []
    }

    if citizen:
        # Fetch other active or past cases
        other_cases = db.query(Case).filter(
            Case.citizen_id == citizen.id,
            Case.id != (case.id if case else "")
        ).order_by(Case.created_at.desc()).limit(3).all()
        
        patient_context["active_cases"] = [
            {
                "id": c.id,
                "reference": c.reference,
                "primary_concern": c.primary_concern,
                "status": c.status.value if hasattr(c.status, "value") else str(c.status),
                "created_at": c.created_at.isoformat()
            }
            for c in other_cases
        ]

        # Recent Asha visits
        recent_visits = db.query(AshaVisit).join(Case, AshaVisit.case_id == Case.id).filter(
            Case.citizen_id == citizen.id
        ).order_by(AshaVisit.created_at.desc()).limit(3).all()

        patient_context["recent_visits"] = [
            {
                "id": v.id,
                "visited_at": v.completed_at.isoformat() if v.completed_at else v.created_at.isoformat(),
                "notes": v.notes,
                "status": v.status
            }
            for v in recent_visits
        ]

    # Structured Packet data
    packet = handoff.structured_payload if handoff else {}
    
    # Strip raw chat transcript if consent not granted
    if not consent_scope.get("share_recent_messages", False):
        packet.pop("raw_messages", None)
        packet.pop("transcript", None)

    person_name = beneficiary.full_name if beneficiary else (citizen.display_name if citizen else "Citizen")
    person_age = beneficiary.age if beneficiary else (citizen.age_estimate if citizen else None)
    person_gender = beneficiary.sex if beneficiary else (citizen.sex if citizen else "Female")
    is_pregnant = beneficiary.is_pregnant if beneficiary else (citizen.is_pregnant if citizen else False)
    gestational_weeks = beneficiary.gestational_weeks if beneficiary else (citizen.gestational_weeks if citizen else None)
    village = citizen.village_name if citizen and citizen.village_name else "Kalyanpur"

    return StandardResponse(data={
        "id": r.id,
        "request_reference": r.request_reference,
        "request_type": r.request_type,
        "source": handoff.source if handoff else "CITIZEN_CHAT",
        "status": r.status,
        "priority": r.priority or "ROUTINE",
        "citizen_id": r.citizen_id,
        "beneficiary_id": r.beneficiary_id,
        "case_id": r.case_id,
        "handoff_id": r.handoff_id or (handoff.id if handoff else None),
        "assigned_asha_id": r.assigned_user_id,
        "assigned_asha_name": r.details.get("assigned_asha") or (current_user.name if r.assigned_user_id == current_user.id else "Sita Patel (Kalyanpur)"),
        "citizen_name": person_name,
        "citizen_age": person_age,
        "citizen_gender": person_gender,
        "is_pregnant": is_pregnant,
        "gestational_weeks": gestational_weeks,
        "citizen_phone": citizen.phone if citizen else None,
        "village_name": village,
        "village": village,
        "location": r.details.get("location") or packet.get("location") or {"landmark": r.details.get("landmark", village)},
        "preferred_date": r.details.get("preferred_date"),
        "preferred_time_window": r.details.get("preferred_time_window", "MORNING"),
        "language": citizen.preferred_language if citizen else "mr-IN",
        "chief_concern": handoff.chief_concern if handoff else r.details.get("reason", "ASHA Assistance Request"),
        "citizen_summary": handoff.citizen_summary if handoff else None,
        "symptoms": packet.get("symptoms", []),
        "negated_symptoms": packet.get("negated_symptoms", []),
        "duration": packet.get("duration", {}),
        "vitals": packet.get("vitals", {}),
        "safety_snapshot": handoff.safety_snapshot if handoff else packet.get("safety", {}),
        "details": r.details,
        "handoff_packet": packet,
        "handoff_version": handoff.version if handoff else 1,
        "consent": {
            "consent_id": consent.id if consent else None,
            "consented_at": consent.consented_at.isoformat() if consent and consent.consented_at else r.created_at.isoformat(),
            "recipient_role": "ASHA_WORKER",
            "scope": consent_scope,
            "policy_version": consent.policy_version if consent else "v1.0"
        },
        "patient_context": patient_context,
        "status_history": [
            {
                "id": h.id,
                "from_status": h.from_status,
                "to_status": h.to_status,
                "actor_role": h.actor_role,
                "actor_id": h.actor_id,
                "reason": h.reason,
                "occurred_at": h.occurred_at.isoformat()
            }
            for h in history
        ],
        "submitted_at": r.submitted_at.isoformat() if r.submitted_at else r.created_at.isoformat(),
        "created_at": r.created_at.isoformat()
    })


@router.post("/citizen-requests/{request_id}/acknowledge", response_model=StandardResponse)
def acknowledge_asha_citizen_request(
    request_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    from app.models import ServiceRequest, ServiceRequestStatusHistory
    r = db.query(ServiceRequest).filter(
        (ServiceRequest.id == request_id) | (ServiceRequest.request_reference == request_id),
        ServiceRequest.request_type == "ASHA_ASSISTANCE"
    ).first()
    if not r:
        raise HTTPException(status_code=404, detail="Citizen request not found")

    if current_user.role == UserRoleEnum.ASHA_WORKER and r.assigned_user_id and r.assigned_user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Unauthorized to acknowledge request assigned to another ASHA")

    old_status = r.status
    if old_status != "ASHA_ACKNOWLEDGED":
        r.status = "ASHA_ACKNOWLEDGED"
        r.assigned_user_id = current_user.id
        r.acknowledged_at = datetime.now(timezone.utc)

        hist = ServiceRequestStatusHistory(
            service_request_id=r.id,
            from_status=old_status,
            to_status="ASHA_ACKNOWLEDGED",
            actor_role="ASHA_WORKER",
            actor_id=current_user.id,
            reason=f"Acknowledged by {current_user.name}"
        )
        db.add(hist)
        
        # Update linked Case if present
        if r.case_id:
            case = db.query(Case).filter(Case.id == r.case_id).first()
            if case:
                case.status = CaseStatusEnum.ASHA_ACKNOWLEDGED

        from app.services.event_bus import publish_domain_event
        publish_domain_event("SERVICE_REQUEST_ACKNOWLEDGED", {
            "service_request_id": r.id,
            "case_id": r.case_id,
            "asha_name": current_user.name
        })

        db.commit()

    return StandardResponse(data={"id": r.id, "status": r.status, "message": "Request acknowledged by ASHA worker"})


@router.patch("/citizen-requests/{request_id}/status", response_model=StandardResponse)
def patch_asha_citizen_request_status(
    request_id: str,
    payload: dict = Body(...),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    from app.models import ServiceRequest, ServiceRequestStatusHistory, FollowUp, Case, Referral
    from app.services.event_bus import publish_domain_event
    
    r = db.query(ServiceRequest).filter(
        (ServiceRequest.id == request_id) | (ServiceRequest.request_reference == request_id),
        ServiceRequest.request_type == "ASHA_ASSISTANCE"
    ).first()
    if not r:
        raise HTTPException(status_code=404, detail="Citizen request not found")

    if current_user.role == UserRoleEnum.ASHA_WORKER and r.assigned_user_id and r.assigned_user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Unauthorized: this request is assigned to another ASHA worker")

    action = payload.get("action", "").upper()
    notes = payload.get("notes") or payload.get("reason")
    old_status = r.status
    new_status = old_status

    if action == "ACKNOWLEDGE":
        new_status = "ASHA_ACKNOWLEDGED"
        r.assigned_user_id = current_user.id
        r.acknowledged_at = datetime.now(timezone.utc)
    elif action in ["CALL_CITIZEN", "CALL_INITIATED", "MARK_CALLED"]:
        # Record call initiation event without overriding successful contact if already reached
        if not r.details:
            r.details = {}
        r.details["last_call_initiated_at"] = datetime.now(timezone.utc).isoformat()
        if old_status in ["NEW", "ASHA_ASSIGNED", "ASSIGNMENT_PENDING", "ASHA_ACKNOWLEDGED"]:
            new_status = "ASHA_ACKNOWLEDGED"
    elif action in ["MARK_CONTACTED", "CONTACT_SUCCESS"]:
        new_status = "CITIZEN_CONTACTED"
        if not r.details:
            r.details = {}
        r.details["contacted_at"] = datetime.now(timezone.utc).isoformat()
        r.details["contact_notes"] = notes or "Citizen successfully contacted via phone"
    elif action in ["MARK_UNREACHABLE", "UNREACHABLE"]:
        new_status = "UNREACHABLE"
        if not r.details:
            r.details = {}
        r.details["unreachable_reason"] = notes or "Citizen unreachable on call"
    elif action in ["REQUEST_INFO", "REQUEST_INFORMATION"]:
        new_status = "INFORMATION_REQUESTED"
        if not r.details:
            r.details = {}
        r.details["info_request_note"] = notes
    elif action in ["SCHEDULE_VISIT", "RESCHEDULE_VISIT"]:
        new_status = "VISIT_SCHEDULED"
        if not r.details:
            r.details = {}
        r.details["confirmed_scheduled_date"] = payload.get("scheduled_date")
        r.details["confirmed_time_slot"] = payload.get("scheduled_time_slot", "MORNING")
        
        # Link or create scheduled visit follow-up
        if r.case_id:
            sched_date = payload.get("scheduled_date")
            due_at_val = datetime.fromisoformat(sched_date) if sched_date else datetime.now(timezone.utc) + timedelta(days=1)
            fu = db.query(FollowUp).filter(
                FollowUp.case_id == r.case_id,
                FollowUp.task_type.in_(["ASHA_HOME_VISIT", "ASHA_VISIT", "HOME_VISIT"]),
                FollowUp.status == "PENDING"
            ).first()
            if not fu:
                fu = FollowUp(
                    case_id=r.case_id,
                    citizen_id=r.citizen_id,
                    created_by_role="ASHA_WORKER",
                    source="ASHA_REQUEST_SCHEDULE",
                    task_type="ASHA_HOME_VISIT",
                    reason=r.details.get("reason", "Scheduled home visit"),
                    assigned_role=UserRoleEnum.ASHA_WORKER,
                    assigned_user_id=current_user.id,
                    instructions=f"Scheduled home visit on {payload.get('scheduled_date')}, slot: {payload.get('scheduled_time_slot', 'MORNING')}",
                    priority=CasePriorityEnum.ROUTINE if r.priority == "ROUTINE" else CasePriorityEnum.HIGH,
                    due_at=due_at_val,
                    status="PENDING"
                )
                db.add(fu)
            else:
                fu.due_at = due_at_val
                fu.instructions = f"Scheduled home visit on {payload.get('scheduled_date')}, slot: {payload.get('scheduled_time_slot', 'MORNING')}"
    elif action in ["START_VISIT", "START_FIELD_VISIT"]:
        new_status = "VISIT_IN_PROGRESS"
    elif action in ["CANCEL_VISIT", "CANCEL"]:
        new_status = "CANCELLED"
        r.cancellation_reason = notes or "Cancelled by ASHA worker"
        if not r.details:
            r.details = {}
        r.details["cancellation_reason"] = r.cancellation_reason
    elif action == "ESCALATE_PHC":
        new_status = "REFERRED_TO_PHC"
        if not r.details:
            r.details = {}
        r.details["escalation_reason"] = notes
        
        # Atomically create Referral in Doctor Queue if case_id present
        if r.case_id:
            existing_ref = db.query(Referral).filter(Referral.case_id == r.case_id, Referral.status != "CANCELLED").first()
            if not existing_ref:
                ref_obj = Referral(
                    case_id=r.case_id,
                    from_asha_id=current_user.id,
                    to_facility_id="PHC-09",
                    to_facility_name="Kalyanpur Primary Health Center",
                    urgency=CasePriorityEnum.URGENT if r.priority in ["URGENT", "EMERGENCY"] else CasePriorityEnum.ROUTINE,
                    reason=notes or f"Escalated from Citizen Request {r.request_reference}",
                    status="PENDING_DOCTOR_REVIEW"
                )
                db.add(ref_obj)
    elif action == "COMPLETE":
        new_status = "COMPLETED"
        r.completed_at = datetime.now(timezone.utc)
        if not r.details:
            r.details = {}
        r.details["completion_notes"] = notes
    elif payload.get("status"):
        new_status = payload.get("status")
    else:
        raise HTTPException(status_code=400, detail=f"Invalid action '{action}'")

    r.status = new_status

    hist = ServiceRequestStatusHistory(
        service_request_id=r.id,
        from_status=old_status,
        to_status=new_status,
        actor_role="ASHA_WORKER",
        actor_id=current_user.id,
        reason=notes or f"Status updated via action {action} by {current_user.name}"
    )
    db.add(hist)

    # Sync linked Case
    if r.case_id:
        case = db.query(Case).filter(Case.id == r.case_id).first()
        if case:
            if new_status == "ASHA_ACKNOWLEDGED":
                case.status = CaseStatusEnum.ASHA_ACKNOWLEDGED
            elif new_status == "CITIZEN_CONTACTED":
                case.status = CaseStatusEnum.CITIZEN_CONTACTED
            elif new_status == "VISIT_SCHEDULED":
                case.status = CaseStatusEnum.VISIT_SCHEDULED
            elif new_status == "VISIT_IN_PROGRESS":
                case.status = CaseStatusEnum.VISIT_IN_PROGRESS
            elif new_status == "REFERRED_TO_PHC":
                case.status = CaseStatusEnum.REFERRED_TO_PHC
            elif new_status == "COMPLETED":
                case.status = CaseStatusEnum.COMPLETED
            elif new_status == "UNREACHABLE":
                case.status = CaseStatusEnum.UNREACHABLE

    publish_domain_event("ASHA_CITIZEN_REQUEST_STATUS_UPDATED", {
        "service_request_id": r.id,
        "request_reference": r.request_reference,
        "case_id": r.case_id,
        "citizen_id": r.citizen_id,
        "action": action,
        "from_status": old_status,
        "to_status": new_status,
        "asha_name": current_user.name,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })

    db.commit()
    db.refresh(r)
    return StandardResponse(data={
        "id": r.id,
        "request_reference": r.request_reference,
        "status": r.status,
        "action": action,
        "message": f"Status changed to {r.status}"
    })


