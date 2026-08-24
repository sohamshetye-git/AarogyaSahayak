from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.models import (
    Case, Referral, Consultation, Prescription, FollowUp, User, CitizenProfile,
    CaseStatusEnum, CasePriorityEnum, AuditLog
)
from app.schemas import (
    StandardResponse, DoctorDashboardResponse, DoctorReferralDTO,
    DoctorConsultationSubmitRequest
)
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
    referrals_query = db.query(Referral).join(Case, Referral.case_id == Case.id)
    referrals = referrals_query.order_by(Referral.created_at.desc()).all()

    urgent_count = sum(1 for r in referrals if r.urgency == CasePriorityEnum.URGENT and r.status != "CONSULTED")
    today_consultations = db.query(Consultation).count()
    pending_followups = db.query(FollowUp).filter(FollowUp.status == "PENDING").count()

    items = [
        DoctorReferralDTO(
            id=r.id,
            reference=r.reference,
            case_id=r.case.id,
            case_reference=r.case.reference,
            citizen_name=r.case.citizen.display_name if r.case.citizen else "Citizen",
            citizen_age=r.case.citizen.age_estimate if r.case.citizen else 28,
            is_pregnant=r.case.citizen.is_pregnant if r.case.citizen else False,
            gestational_weeks=r.case.citizen.gestational_weeks if r.case.citizen else None,
            urgency=r.urgency.value,
            reason=r.reason,
            status=r.status,
            referring_asha_name=r.case.assigned_asha_name,
            created_at=r.created_at,
            acknowledged_at=r.acknowledged_at
        )
        for r in referrals
    ]

    doctor_name = current_user.name if current_user else "Dr. Abhinav Sharma"
    facility_name = "Kalyanpur PHC"

    return StandardResponse(
        data=DoctorDashboardResponse(
            doctor_name=doctor_name,
            facility_name=facility_name,
            urgent_referrals_count=urgent_count,
            today_consultations_count=today_consultations,
            pending_followups_count=pending_followups,
            referrals=items
        ).model_dump()
    )

@router.get("/referrals", response_model=StandardResponse)
def get_doctor_referrals(
    urgency: Optional[str] = None,
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    query = db.query(Referral).join(Case, Referral.case_id == Case.id)
    if urgency:
        query = query.filter(Referral.urgency == urgency)
    if status_filter:
        query = query.filter(Referral.status == status_filter)

    referrals = query.order_by(Referral.created_at.desc()).all()
    items = [
        DoctorReferralDTO(
            id=r.id,
            reference=r.reference,
            case_id=r.case.id,
            case_reference=r.case.reference,
            citizen_name=r.case.citizen.display_name if r.case.citizen else "Citizen",
            citizen_age=r.case.citizen.age_estimate if r.case.citizen else 28,
            is_pregnant=r.case.citizen.is_pregnant if r.case.citizen else False,
            gestational_weeks=r.case.citizen.gestational_weeks if r.case.citizen else None,
            urgency=r.urgency.value,
            reason=r.reason,
            status=r.status,
            referring_asha_name=r.case.assigned_asha_name,
            created_at=r.created_at,
            acknowledged_at=r.acknowledged_at
        ).model_dump()
        for r in referrals
    ]
    return StandardResponse(data=items)

@router.get("/referrals/{case_id}", response_model=StandardResponse)
def get_case_for_doctor(case_id: str, db: Session = Depends(get_db)):
    case = db.query(Case).filter((Case.id == case_id) | (Case.reference == case_id)).first()
    if not case:
        raise HTTPException(status_code=404, detail={"code": "CASE_NOT_FOUND", "message": "Case not found"})

    referral = db.query(Referral).filter(Referral.case_id == case.id).first()

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
            "recorded_at": v.recorded_at.isoformat(),
            "source": v.source_type.value
        }
        for v in case.vitals
    ]

    # Include recent visit notes if any
    visits = [
        {
            "reference": v.reference,
            "notes": v.notes,
            "completed_at": v.completed_at.isoformat() if v.completed_at else None
        }
        for v in case.visits
    ]

    return StandardResponse(
        data={
            "case_id": case.id,
            "case_reference": case.reference,
            "referral_id": referral.id if referral else None,
            "referral_reference": referral.reference if referral else None,
            "referral_status": referral.status if referral else "N/A",
            "citizen_name": case.citizen.display_name if case.citizen else "Sunita Devi",
            "citizen_age": case.citizen.age_estimate if case.citizen else 28,
            "is_pregnant": case.citizen.is_pregnant if case.citizen else False,
            "gestational_weeks": case.citizen.gestational_weeks if case.citizen else None,
            "village_name": case.citizen.village_name if case.citizen else "Kalyanpur",
            "priority": case.priority.value,
            "status": case.status.value,
            "primary_concern": case.primary_concern,
            "safety_rule_triggered": case.safety_rule_triggered,
            "safety_rule_reason": case.safety_rule_reason,
            "assigned_asha_name": case.assigned_asha_name,
            "symptoms": symptoms,
            "vitals": vitals,
            "visits": visits,
            "ai_assisted_summary": "AI-assisted summary – human review required: Patient presents with symptoms and blood pressure consistent with maternal pre-eclampsia evaluation.",
            "created_at": case.created_at.isoformat()
        }
    )

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

@router.get("/patients", response_model=StandardResponse)
def get_doctor_patients(db: Session = Depends(get_db)):
    citizens = db.query(CitizenProfile).all()
    patients = [
        {
            "id": c.id,
            "name": c.display_name,
            "age": c.age_estimate or 28,
            "gender": c.sex or "Female",
            "village": c.village_name,
            "is_pregnant": c.is_pregnant,
            "gestational_weeks": c.gestational_weeks,
            "cases_count": len(c.cases)
        }
        for c in citizens
    ]
    return StandardResponse(data=patients)
