from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from app.database import get_db
from app.models import User, CitizenProfile, TeleconsultationRequest
from app.schemas import StandardResponse
from app.schemas.teleconsultation import (
    TeleconsultationDraftCreateDTO, TeleconsultationIntakeUpdateDTO,
    TeleconsultationSubmitDTO, TeleconsultationMessageCreateDTO,
    TeleconsultationSymptomsUpdateDTO
)
from app.services.citizen_service import CitizenService
from app.services.teleconsultation_service import TeleconsultationService
from app.dependencies import get_optional_user

router = APIRouter(prefix="/citizen/doctor-requests", tags=["Citizen Doctor Requests"])

@router.post("/draft", response_model=StandardResponse)
def create_draft(
    dto: TeleconsultationDraftCreateDTO,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    profile = CitizenService.get_or_create_default_profile(db, current_user)
    draft = TeleconsultationService.create_draft(db, profile.id, dto)
    return StandardResponse(data={
        "id": draft.id,
        "public_reference": draft.public_reference,
        "status": draft.status,
        "mode": draft.mode,
        "language_code": draft.language_code
    })

@router.patch("/{request_id}/draft", response_model=StandardResponse)
def update_draft(
    request_id: str,
    dto: TeleconsultationIntakeUpdateDTO,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    profile = CitizenService.get_or_create_default_profile(db, current_user)
    updated = TeleconsultationService.update_draft_intake(db, request_id, profile.id, dto)
    return StandardResponse(data={
        "id": updated.id,
        "public_reference": updated.public_reference,
        "status": updated.status,
        "priority": updated.priority,
        "safety_rule_triggered": updated.safety_rule_triggered,
        "safety_reason": updated.safety_reason
    })

@router.post("/{request_id}/submit", response_model=StandardResponse)
def submit_request(
    request_id: str,
    dto: TeleconsultationSubmitDTO,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    profile = CitizenService.get_or_create_default_profile(db, current_user)
    detail = TeleconsultationService.submit_request(db, request_id, profile.id, dto)
    return StandardResponse(data=detail)

@router.get("/{request_id}", response_model=StandardResponse)
def get_request(
    request_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    profile = CitizenService.get_or_create_default_profile(db, current_user)
    detail = TeleconsultationService.get_request_detail(db, request_id, profile.id)
    return StandardResponse(data=detail)

@router.get("/{request_id}/status", response_model=StandardResponse)
def get_request_status(
    request_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    profile = CitizenService.get_or_create_default_profile(db, current_user)
    detail = TeleconsultationService.get_request_detail(db, request_id, profile.id)
    return StandardResponse(data={
        "id": detail["id"],
        "public_reference": detail["public_reference"],
        "status": detail["status"],
        "queue_position": detail["queue_position"],
        "estimated_wait_minutes": detail["estimated_wait_minutes"],
        "doctor": detail["doctor"],
        "messages": detail["messages"]
    })

@router.post("/{request_id}/cancel", response_model=StandardResponse)
def cancel_request(
    request_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    profile = CitizenService.get_or_create_default_profile(db, current_user)
    res = TeleconsultationService.cancel_request(db, request_id, profile.id)
    return StandardResponse(data=res)

@router.get("/{request_id}/conversation", response_model=StandardResponse)
def get_request_conversation(
    request_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    profile = CitizenService.get_or_create_default_profile(db, current_user)
    tele_req, _ = TeleconsultationService.resolve_canonical_request(db, request_id)
    if not tele_req:
        raise HTTPException(status_code=404, detail="Request not found")
    detail = TeleconsultationService.get_request_detail(db, tele_req.id, profile.id)
    return StandardResponse(data=detail)

@router.post("/{request_id}/messages", response_model=StandardResponse)
def send_message(
    request_id: str,
    dto: TeleconsultationMessageCreateDTO,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    profile = CitizenService.get_or_create_default_profile(db, current_user)
    body_text = dto.body or dto.message_text or ""
    if not body_text.strip():
        raise HTTPException(status_code=400, detail="Message text cannot be empty")

    msg = TeleconsultationService.send_message(
        db=db,
        request_id=request_id,
        sender_type="CITIZEN",
        sender_role="CITIZEN",
        sender_name=profile.display_name,
        message_text=body_text,
        sender_id=profile.id,
        client_message_id=dto.client_message_id,
        message_type=dto.message_type or "TEXT"
    )
    return StandardResponse(data={
        "id": msg.id,
        "conversation_id": getattr(msg, "conversation_id", None) or getattr(msg, "request_id", None),
        "service_request_id": getattr(msg, "service_request_id", None),
        "sender_user_id": getattr(msg, "sender_user_id", None) or getattr(msg, "sender_id", None),
        "sender_role": getattr(msg, "sender_role", None) or getattr(msg, "sender_type", None),
        "sender_name": getattr(msg, "sender_name", None),
        "message_type": getattr(msg, "message_type", "TEXT"),
        "body": getattr(msg, "body", None) or getattr(msg, "message_text", None),
        "message_text": getattr(msg, "message_text", None),
        "client_message_id": getattr(msg, "client_message_id", None),
        "status": getattr(msg, "status", "SENT"),
        "created_at": msg.created_at.isoformat() if getattr(msg, "created_at", None) else ""
    })

@router.post("/{request_id}/update-symptoms", response_model=StandardResponse)
def update_symptoms(
    request_id: str,
    dto: TeleconsultationSymptomsUpdateDTO,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    profile = CitizenService.get_or_create_default_profile(db, current_user)
    updated = CitizenService.update_doctor_request_symptoms(
        db=db,
        citizen_id=profile.id,
        request_id=request_id,
        new_symptoms=dto.new_symptoms,
        notes=getattr(dto, "notes", None)
    )
    return StandardResponse(data=updated)

@router.get("/{request_id}/summary", response_model=StandardResponse)
def get_consultation_summary(
    request_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    profile = CitizenService.get_or_create_default_profile(db, current_user)
    detail = TeleconsultationService.get_request_detail(db, request_id, profile.id)
    return StandardResponse(data=detail)

@router.get("/active/current", response_model=StandardResponse)
def get_active_request(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    profile = CitizenService.get_or_create_default_profile(db, current_user)
    active = db.query(TeleconsultationRequest).filter(
        TeleconsultationRequest.citizen_id == profile.id,
        ~TeleconsultationRequest.status.in_(["COMPLETED", "CANCELLED", "EXPIRED"])
    ).order_by(TeleconsultationRequest.created_at.desc()).first()

    if not active:
        return StandardResponse(data=None)
    return StandardResponse(data=TeleconsultationService.get_request_detail(db, active.id, profile.id))
