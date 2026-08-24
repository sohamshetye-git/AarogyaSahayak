from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.models import Case, CitizenProfile, User, UserRoleEnum
from app.schemas import CitizenCreateCaseRequest, CitizenCaseDTO, StandardResponse
from app.services.case_service import CaseService
from app.dependencies import get_optional_user, get_current_user
from app.integrations import neo4j_adapter, bhashini_adapter

router = APIRouter(prefix="/citizen", tags=["Citizen"])

@router.post("/cases", response_model=StandardResponse)
def create_citizen_case(
    req: CitizenCreateCaseRequest,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    # Find or create citizen profile
    if current_user and current_user.citizen_profile:
        profile = current_user.citizen_profile
    else:
        # Default citizen profile if guest/demo
        profile = db.query(CitizenProfile).first()
        if not profile:
            profile = CitizenProfile(
                display_name="Sunita Devi",
                age_estimate=28,
                sex="Female",
                preferred_language=req.preferred_language,
                village_name="Kalyanpur",
                is_pregnant=req.is_pregnant,
                gestational_weeks=req.gestational_weeks
            )
            db.add(profile)
            db.commit()
            db.refresh(profile)

    new_case = CaseService.create_case(
        db=db,
        req=req,
        citizen_profile=profile,
        created_by_name=profile.display_name
    )

    return StandardResponse(
        data={
            "case_id": new_case.id,
            "case_reference": new_case.reference,
            "priority": new_case.priority.value,
            "status": new_case.status.value,
            "safety_rule_triggered": new_case.safety_rule_triggered,
            "safety_rule_reason": new_case.safety_rule_reason,
            "citizen_guidance_text": new_case.citizen_guidance_text,
            "assigned_asha_name": new_case.assigned_asha_name,
            "created_at": new_case.created_at.isoformat()
        }
    )

@router.get("/cases", response_model=StandardResponse)
def get_my_cases(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    if current_user and current_user.citizen_profile:
        cases = db.query(Case).filter(Case.citizen_id == current_user.citizen_profile.id).order_by(Case.created_at.desc()).all()
    else:
        cases = db.query(Case).order_by(Case.created_at.desc()).limit(10).all()

    items = [
        {
            "id": c.id,
            "reference": c.reference,
            "priority": c.priority.value,
            "status": c.status.value,
            "primary_concern": c.primary_concern,
            "citizen_guidance_text": c.citizen_guidance_text,
            "assigned_asha_name": c.assigned_asha_name,
            "assigned_facility_name": c.assigned_facility_name,
            "created_at": c.created_at.isoformat(),
            "updated_at": c.updated_at.isoformat()
        }
        for c in cases
    ]
    return StandardResponse(data=items)

@router.get("/cases/{case_id}", response_model=StandardResponse)
def get_case_status(case_id: str, db: Session = Depends(get_db)):
    case = db.query(Case).filter((Case.id == case_id) | (Case.reference == case_id)).first()
    if not case:
        raise HTTPException(status_code=404, detail={"code": "CASE_NOT_FOUND", "message": "Case not found"})

    # Friendly human-readable status for citizen
    status_explanations = {
        "NEW": "Your request has been received.",
        "ASHA_ASSIGNED": "Your assigned ASHA worker has been notified.",
        "ASHA_ACKNOWLEDGED": "Your ASHA worker has received and opened your case.",
        "CITIZEN_CONTACTED": "ASHA worker has contacted you.",
        "VISIT_SCHEDULED": "A home visit has been scheduled.",
        "REFERRED_TO_PHC": "ASHA worker has referred your case to the Primary Health Center.",
        "DOCTOR_ACKNOWLEDGED": "PHC Doctor has received your referral and is preparing for consultation.",
        "CONSULTATION_IN_PROGRESS": "Consultation completed by doctor.",
        "FOLLOW_UP_REQUIRED": "Doctor has prescribed a care plan. ASHA follow-up scheduled.",
        "COMPLETED": "Care plan completed."
    }

    return StandardResponse(
        data={
            "id": case.id,
            "reference": case.reference,
            "priority": case.priority.value,
            "status": case.status.value,
            "status_explanation": status_explanations.get(case.status.value, "Your case is actively being monitored."),
            "primary_concern": case.primary_concern,
            "citizen_guidance_text": case.citizen_guidance_text,
            "assigned_asha_name": case.assigned_asha_name,
            "assigned_facility_name": case.assigned_facility_name,
            "created_at": case.created_at.isoformat()
        }
    )

@router.get("/scheme-checks", response_model=StandardResponse)
def check_citizen_schemes(condition: str = "Pregnancy care", db: Session = Depends(get_db)):
    schemes = neo4j_adapter.find_eligible_schemes(condition=condition)
    return StandardResponse(data=schemes)
