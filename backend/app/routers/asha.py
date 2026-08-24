from fastapi import APIRouter, Depends, HTTPException, status, Header, Response
import json
from sqlalchemy.orm import Session
from typing import List, Optional
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
    AshaFollowUpDTO, AshaFollowUpSubmitRequest, TimelineEventDTO
)
from app.dependencies import get_current_user, require_asha, require_staff
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
    total_assigned = db.query(Case).count()
    urgent_count = db.query(Case).filter(Case.priority == CasePriorityEnum.URGENT).count()
    pending_visits = db.query(Case).filter(
        Case.status.in_([CaseStatusEnum.NEW, CaseStatusEnum.ASHA_ACKNOWLEDGED, CaseStatusEnum.CITIZEN_CONTACTED])
    ).count()
    active_followups = db.query(Case).filter(Case.status == CaseStatusEnum.FOLLOW_UP_REQUIRED).count()

    cases = db.query(Case).order_by(Case.created_at.desc()).limit(15).all()

    tasks = [
        AshaTaskDTO(
            id=c.id,
            case_id=c.id,
            case_reference=c.reference,
            citizen_name=c.citizen.display_name if c.citizen else "Citizen",
            village_name=c.citizen.village_name if c.citizen else "Kalyanpur",
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

    worker_name = current_user.name if current_user else "Sita Patel"
    village = "Kalyanpur Village"

    return StandardResponse(
        data=AshaDashboardResponse(
            worker_name=worker_name,
            village=village,
            total_assigned=total_assigned,
            urgent_count=urgent_count,
            pending_visits=pending_visits,
            active_followups=active_followups,
            recent_tasks=tasks
        ).model_dump()
    )

@router.get("/tasks", response_model=StandardResponse)
def get_asha_tasks(
    priority: Optional[str] = None,
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    query = db.query(Case)
    if priority:
        query = query.filter(Case.priority == priority)
    if status_filter:
        query = query.filter(Case.status == status_filter)

    cases = query.order_by(Case.created_at.desc()).all()
    tasks = [
        AshaTaskDTO(
            id=c.id,
            case_id=c.id,
            case_reference=c.reference,
            citizen_name=c.citizen.display_name if c.citizen else "Citizen",
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

@router.get("/cases/{case_id}", response_model=StandardResponse)
def get_case_details_for_asha(case_id: str, db: Session = Depends(get_db)):
    case = db.query(Case).filter((Case.id == case_id) | (Case.reference == case_id)).first()
    if not case:
        raise HTTPException(status_code=404, detail={"code": "CASE_NOT_FOUND", "message": "Case not found"})

    symptoms = [
        {"term": s.normalized_term, "source": s.source_type.value, "recorded_by": s.recorded_by}
        for s in case.symptoms
    ]
    vitals = [
        {
            "systolic_bp": v.systolic_bp,
            "diastolic_bp": v.diastolic_bp,
            "temperature_c": v.temperature_c,
            "spo2": v.spo2,
            "pulse": v.pulse,
            "recorded_at": v.recorded_at.isoformat()
        }
        for v in case.vitals
    ]

    return StandardResponse(
        data={
            "id": case.id,
            "reference": case.reference,
            "priority": case.priority.value,
            "status": case.status.value,
            "primary_concern": case.primary_concern,
            "citizen_name": case.citizen.display_name if case.citizen else "Unknown",
            "citizen_age": case.citizen.age_estimate if case.citizen else 28,
            "citizen_phone": case.citizen.phone if case.citizen else "9876543210",
            "village_name": case.citizen.village_name if case.citizen else "Kalyanpur",
            "is_pregnant": case.citizen.is_pregnant if case.citizen else False,
            "gestational_weeks": case.citizen.gestational_weeks if case.citizen else None,
            "safety_rule_triggered": case.safety_rule_triggered,
            "safety_rule_reason": case.safety_rule_reason,
            "symptoms": symptoms,
            "vitals": vitals,
            "created_at": case.created_at.isoformat()
        }
    )

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

    try:
        CaseService.update_status(db, case, CaseStatusEnum.ASHA_ACKNOWLEDGED)
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"code": "INVALID_STATE_TRANSITION", "message": str(e)})

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

    try:
        CaseService.update_status(db, case, CaseStatusEnum.CITIZEN_CONTACTED)
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"code": "INVALID_STATE_TRANSITION", "message": str(e)})
    db.commit()
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
        event_name="CITIZEN_CONTACTED",
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

    try:
        referral = ReferralService.create_referral(
            db=db,
            case=case,
            asha_user=current_user,
            req=req
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"code": "INVALID_STATE_TRANSITION", "message": str(e)})

    response_obj = StandardResponse(
        data={
            "referral_id": referral.id,
            "referral_reference": referral.reference,
            "case_id": case.id,
            "status": case.status.value,
            "facility_name": referral.to_facility_name,
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
def get_village_people(db: Session = Depends(get_db)):
    citizens = db.query(CitizenProfile).all()
    people = [
        {
            "id": c.id,
            "name": c.display_name,
            "age": c.age_estimate or 28,
            "phone": c.phone or "9876543210",
            "village": c.village_name,
            "is_pregnant": c.is_pregnant,
            "gestational_weeks": c.gestational_weeks,
            "abha": c.abha_reference or "12-3456-7890-1234",
            "active_cases_count": len(c.cases)
        }
        for c in citizens
    ]
    return StandardResponse(data=people)


@router.get("/followups", response_model=StandardResponse)
def get_asha_followups(
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    query = db.query(FollowUp).join(Case, FollowUp.case_id == Case.id)
    if status_filter:
        query = query.filter(FollowUp.status == status_filter)

    followups = query.order_by(FollowUp.due_at.asc()).all()
    results = [
        AshaFollowUpDTO(
            id=f.id,
            case_id=f.case_id,
            case_reference=f.case.reference if f.case else "CASE-2026",
            citizen_name=f.case.citizen.display_name if f.case and f.case.citizen else "Citizen",
            citizen_phone=f.case.citizen.phone if f.case and f.case.citizen else None,
            village_name=f.case.citizen.village_name if f.case and f.case.citizen else "Kalyanpur",
            is_pregnant=f.case.citizen.is_pregnant if f.case and f.case.citizen else False,
            task_type=f.task_type,
            instructions=f.instructions,
            priority=f.priority.value if hasattr(f.priority, "value") else str(f.priority),
            due_at=f.due_at,
            status=f.status,
            completed_at=f.completed_at,
            result=f.result
        ).model_dump()
        for f in followups
    ]
    return StandardResponse(data=results)


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
        raise HTTPException(status_code=404, detail={"code": "CASE_NOT_FOUND", "message": "Case not found"})

    events: List[TimelineEventDTO] = []

    # 1. Citizen case creation
    events.append(TimelineEventDTO(
        id=f"evt-{case.id}-create",
        timestamp=case.created_at,
        event_type="CASE_CREATED",
        title="Citizen Case Reported",
        description=f"Primary concern: {case.primary_concern}",
        actor_role="CITIZEN",
        actor_name=case.citizen.display_name if case.citizen else "Citizen",
        badge_type="warning" if case.priority == CasePriorityEnum.URGENT else "info"
    ))

    # 2. Audits for acknowledgement and contact
    audits = db.query(AuditLog).filter(AuditLog.resource_id == case.id).order_by(AuditLog.created_at.asc()).all()
    for a in audits:
        events.append(TimelineEventDTO(
            id=a.id,
            timestamp=a.created_at,
            event_type=a.action,
            title=a.action.replace("_", " ").title(),
            description=f"Action completed by {a.actor_role}",
            actor_role=a.actor_role,
            badge_type="success"
        ))

    # 3. Field Visits
    for v in case.visits:
        events.append(TimelineEventDTO(
            id=v.id,
            timestamp=v.completed_at or v.started_at,
            event_type="FIELD_VISIT",
            title=f"Field Visit: {v.reference or 'Completed'}",
            description=v.notes or "Field vitals & triage recorded",
            actor_role="ASHA_WORKER",
            badge_type="success"
        ))

    # 4. Referrals
    for r in case.referrals:
        events.append(TimelineEventDTO(
            id=r.id,
            timestamp=r.created_at,
            event_type="PHC_REFERRAL",
            title=f"PHC Referral Submitted ({r.reference or 'REF'})",
            description=f"Referred to {r.to_facility_name}. Urgency: {r.urgency.value if hasattr(r.urgency, 'value') else r.urgency}. Status: {r.status}",
            actor_role="ASHA_WORKER",
            badge_type="danger" if r.urgency == CasePriorityEnum.URGENT else "warning"
        ))

    # 5. Consultations
    for c in case.consultations:
        events.append(TimelineEventDTO(
            id=c.id,
            timestamp=c.signed_at or c.completed_at,
            event_type="DOCTOR_CONSULTATION",
            title="Doctor Consultation & Prescription Signed",
            description=f"Diagnosis: {c.confirmed_diagnosis}. Care plan: {c.care_plan_summary or 'Standard regimen'}",
            actor_role="PHC_DOCTOR",
            actor_name=c.doctor_name,
            badge_type="success"
        ))

    # 6. Follow-ups
    for f in case.follow_ups:
        events.append(TimelineEventDTO(
            id=f.id,
            timestamp=f.completed_at or f.created_at,
            event_type="FOLLOW_UP",
            title=f"ASHA Follow-up Task ({f.status})",
            description=f"Instructions: {f.instructions}" + (f" | Outcome: {f.result}" if f.result else f" | Due by: {f.due_at.strftime('%d %b %Y')}"),
            actor_role="ASHA_WORKER",
            badge_type="success" if f.status == "COMPLETED" else "warning"
        ))

    events.sort(key=lambda x: x.timestamp)
    return StandardResponse(data=[e.model_dump() for e in events])


@router.post("/voice/transcribe", response_model=StandardResponse)
def transcribe_voice_input(
    audio_format: Optional[str] = "webm",
    preferred_language: Optional[str] = "mr-IN",
    current_user: User = Depends(require_staff)
):
    """
    Simulated lightweight voice transcription supporting mock/bhashini fallback.
    Returns deterministic clinical note templates based on language.
    """
    templates = {
        "mr-IN": "नागरिकाची तपासणी केली. रक्तदाब नियमित आहे. औषधे वेळेवर घेण्याचा सल्ला दिला.",
        "hi-IN": "मरीज की जांच की गई। रक्तचाप स्थिर है। दवाइयां नियमित रूप से लेने की सलाह दी गई।",
        "en-IN": "Patient evaluated during home field visit. Resting vitals measured and compliance with prescribed medication verified."
    }
    transcript = templates.get(preferred_language, templates["en-IN"])
    return StandardResponse(data={
        "transcript": transcript,
        "detected_language": preferred_language,
        "confidence": 0.96,
        "processing_mode": "mock_bhashini_fallback"
    })
