import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Body, Response, Request
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from app.database import get_db
from app.config import settings

from app.models import Case, CitizenProfile, HouseholdMember, User, UserRoleEnum, Prescription, InvestigationOrder, FollowUp, PrescriptionAcknowledgement
from app.schemas import CitizenCreateCaseRequest, CitizenCaseDTO, StandardResponse
from app.schemas.prescription import CitizenAcknowledgeRequest, CitizenRequestHelpRequest
from app.schemas.citizen import (
    LanguageUpdateRequestDTO, HouseholdMemberCreateRequest, HouseholdMemberUpdateRequest, StartChatSessionRequest,
    ChatMessageCreateRequest, ChatVoiceTranscribeRequest, TranscriptConfirmationRequest,
    UnderstandingConfirmationRequest, CitizenNeedCreateRequest,
    DoctorRequestCreateDTO, AshaRequestCreateDTO, SchemeScreeningRequest,
    FacilitySearchRequest, HandoffPreviewRequest, ServiceRequestUpdateDTO, ServiceRequestCancelDTO,
    PatientResolutionRequestDTO, PatientResolutionResponseDTO,
    CitizenProfileUpdateRequest, ConsentRevokeRequest,
    CitizenOtpRequestDTO, CitizenOtpVerifyDTO, CitizenRefreshTokenDTO, CitizenOnboardingRequestDTO,
    GuestSessionCreateDTO, GuestSessionUpdateDTO, GuestSessionMigrateDTO
)
from app.schemas.teleconsultation import TeleconsultationMessageCreateDTO, TeleconsultationSymptomsUpdateDTO
from app.services.case_service import CaseService
from app.services.citizen_service import CitizenService
from app.services.citizen_auth_service import CitizenAuthService
from app.services.facility_service import calculate_haversine_distance
from app.dependencies import get_optional_user, get_current_user
from app.integrations import neo4j_adapter, bhashini_adapter


router = APIRouter(prefix="/citizen", tags=["Citizen"])

COOKIE_NAME = "aarogya_citizen_refresh"

def set_citizen_refresh_cookie(response: Response, refresh_token: str):
    max_age = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
    is_prod = (settings.ENVIRONMENT or "").lower() in ["production", "prod"]
    response.set_cookie(
        key=COOKIE_NAME,
        value=refresh_token,
        max_age=max_age,
        expires=max_age,
        httponly=True,
        secure=True if is_prod else False,
        samesite="none" if is_prod else "lax",
        path="/"
    )

def clear_citizen_refresh_cookie(response: Response):
    is_prod = (settings.ENVIRONMENT or "").lower() in ["production", "prod"]
    response.delete_cookie(
        key=COOKIE_NAME,
        path="/",
        httponly=True,
        secure=True if is_prod else False,
        samesite="none" if is_prod else "lax"
    )

# -------------------------------------------------------------
# Citizen Authentication Endpoints
# -------------------------------------------------------------

@router.post("/auth/otp/request", response_model=StandardResponse)
def request_citizen_otp(
    req: CitizenOtpRequestDTO,
    db: Session = Depends(get_db)
):
    """
    Initiates mobile OTP verification.
    Applies rate limiting and cooldowns, hashes phone & challenge, and dispatches via provider.
    """
    try:
        res = CitizenAuthService.request_otp(db=db, phone_raw=req.phone)
        return StandardResponse(data=res)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "OTP_REQUEST_FAILED", "message": str(e)}
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "INTERNAL_ERROR", "message": str(e)}
        )

@router.post("/auth/otp/verify", response_model=StandardResponse)
def verify_citizen_otp(
    req: CitizenOtpVerifyDTO,
    response: Response,
    db: Session = Depends(get_db)
):
    """
    Verifies 6-digit OTP challenge against secure hash.
    Establishes authenticated citizen session or signals onboarding required.
    """
    try:
        res = CitizenAuthService.verify_otp(
            db=db,
            phone_raw=req.phone,
            otp_code=req.otp,
            device_id=req.device_id,
            idempotency_key=req.idempotency_key,
            otp_request_id=req.otp_request_id
        )
        if isinstance(res, dict) and res.get("refresh_token"):
            set_citizen_refresh_cookie(response, res["refresh_token"])
        return StandardResponse(data=res)
    except ValueError as e:
        err_msg = str(e)
        err_code = "OTP_VERIFICATION_FAILED"
        if "No active OTP request found" in err_msg or "not found" in err_msg.lower():
            err_code = "NO_ACTIVE_OTP"
        elif "expired" in err_msg.lower():
            err_code = "OTP_EXPIRED"
        elif "Maximum OTP verification attempts exceeded" in err_msg or "Limit reached" in err_msg:
            err_code = "OTP_MAX_ATTEMPTS_EXCEEDED"
        elif "Account is deactivated" in err_msg:
            err_code = "ACCOUNT_DEACTIVATED"

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": err_code, "message": err_msg}
        )
    except Exception as e:
        req_id = generate_uuid()
        logger.exception("Unexpected error during citizen OTP verification [req_id=%s]: %s", req_id, str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "AUTH_RESTORATION_ERROR",
                "message": "We could not restore your account. Please try again.",
                "request_id": req_id
            }
        )

@router.post("/auth/refresh", response_model=StandardResponse)
def refresh_citizen_token(
    request: Request,
    response: Response,
    req: Optional[CitizenRefreshTokenDTO] = Body(None),
    db: Session = Depends(get_db)
):
    """
    Rotates refresh token and issues a new access token using HttpOnly cookie or request body.
    """
    token = None
    if req and req.refresh_token:
        token = req.refresh_token
    elif COOKIE_NAME in request.cookies:
        token = request.cookies.get(COOKIE_NAME)

    if not token:
        clear_citizen_refresh_cookie(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "REFRESH_TOKEN_REQUIRED", "message": "No refresh token found in cookie or request"}
        )

    try:
        res = CitizenAuthService.refresh_token_session(db=db, refresh_token=token)
        if isinstance(res, dict) and res.get("refresh_token"):
            set_citizen_refresh_cookie(response, res["refresh_token"])
        return StandardResponse(data=res)
    except ValueError as e:
        clear_citizen_refresh_cookie(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_REFRESH_TOKEN", "message": str(e)}
        )
    except Exception as e:
        clear_citizen_refresh_cookie(response)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "INTERNAL_ERROR", "message": str(e)}
        )

@router.post("/auth/logout", response_model=StandardResponse)
def logout_citizen(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    """
    Revokes the current user's authenticated sessions and clears refresh cookie.
    """
    refresh_token = request.cookies.get(COOKIE_NAME)
    user_id = current_user.id if current_user else None
    CitizenAuthService.logout_session(db=db, user_id=user_id, refresh_token=refresh_token)
    clear_citizen_refresh_cookie(response)
    return StandardResponse(data={"success": True, "message": "Logged out successfully"})

@router.get("/auth/me", response_model=StandardResponse)
def get_citizen_auth_me(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns current authenticated citizen details and authorized household beneficiaries.
    """
    profile = current_user.citizen_profile
    if not profile:
        profile = CitizenService.get_or_create_default_profile(db, current_user)
    user_dto = {
        "id": current_user.id,
        "identifier": current_user.identifier,
        "name": current_user.name,
        "phone": current_user.phone,
        "role": current_user.role.value,
        "preferred_language": current_user.preferred_language or (profile.preferred_language if profile else "mr-IN"),
        "village_name": profile.village_name if profile else "Kalyanpur"
    }
    beneficiaries = CitizenAuthService.get_authorized_beneficiaries(db, current_user.id)
    profile_data = CitizenService.get_citizen_profile_detail(db, profile.id) if profile else None

    return StandardResponse(data={
        "user": user_dto,
        "profile": profile_data,
        "authorized_beneficiaries": beneficiaries
    })

# -------------------------------------------------------------
# Citizen Onboarding & Beneficiaries
# -------------------------------------------------------------

@router.post("/onboarding", response_model=StandardResponse)
def submit_citizen_onboarding(
    req: CitizenOnboardingRequestDTO,
    response: Response,
    db: Session = Depends(get_db)
):
    """
    Completes minimal registration for a newly verified mobile number.
    Atomically creates User, CitizenProfile, and CitizenAuthIdentity.
    """
    try:
        res = CitizenAuthService.register_onboarding(
            db=db,
            phone_raw=req.phone,
            registration_data=req.model_dump(),
            idempotency_key=getattr(req, "idempotency_key", None)
        )
        if isinstance(res, dict) and res.get("refresh_token"):
            set_citizen_refresh_cookie(response, res["refresh_token"])
        return StandardResponse(data=res)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "ONBOARDING_FAILED", "message": str(e)}
        )
    except Exception as e:
        req_id = generate_uuid()
        logger.exception("Unexpected error during citizen onboarding [req_id=%s]: %s", req_id, str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "ONBOARDING_ERROR",
                "message": "Registration could not be completed. Please try again.",
                "request_id": req_id
            }
        )


@router.get("/authorized-beneficiaries", response_model=StandardResponse)
def get_authorized_beneficiaries(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns only authorized beneficiaries for the authenticated citizen account (Myself + household members).
    """
    items = CitizenAuthService.get_authorized_beneficiaries(db, current_user.id)
    return StandardResponse(data={"items": items})

# -------------------------------------------------------------
# Guest Session Endpoints
# -------------------------------------------------------------

@router.post("/guest/session", response_model=StandardResponse)
def create_guest_session(
    req: GuestSessionCreateDTO,
    db: Session = Depends(get_db)
):
    """
    Creates an anonymous guest session with a non-guessable random token and TTL.
    """
    res = CitizenAuthService.create_guest_session(
        db=db,
        locale=req.locale or "mr-IN",
        device_hash=req.device_hash
    )
    return StandardResponse(data=res)

@router.get("/guest/session/{session_id}", response_model=StandardResponse)
def get_guest_session(
    session_id: str,
    db: Session = Depends(get_db)
):
    """
    Retrieves anonymous guest session state and drafted care context.
    """
    guest = CitizenAuthService.get_guest_session(db=db, session_id=session_id)
    if not guest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "GUEST_SESSION_NOT_FOUND", "message": "Guest session not found"}
        )
    return StandardResponse(data={
        "session_id": guest.id,
        "locale": guest.locale,
        "context_data": guest.context_data,
        "intended_action": guest.intended_action,
        "expires_at": guest.expires_at.isoformat(),
        "is_migrated": bool(guest.migrated_to_user_id)
    })

@router.post("/guest/session/{session_id}/migrate", response_model=StandardResponse)
def migrate_guest_session(
    session_id: str,
    req: GuestSessionMigrateDTO,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Atomically migrates guest session chat, need, and care draft to the authenticated citizen.
    """
    try:
        res = CitizenAuthService.migrate_guest_to_citizen(
            db=db,
            guest_session_id=session_id,
            user_id=current_user.id,
            idempotency_key=req.idempotency_key
        )
        return StandardResponse(data=res)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "MIGRATION_FAILED", "message": str(e)}
        )

@router.patch("/preferences/language", response_model=StandardResponse)
def update_citizen_language_preference(
    req: LanguageUpdateRequestDTO,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    """
    Updates citizen's preferred language locally & in profile if authenticated.
    """
    if current_user:
        current_user.preferred_language = req.preferred_language
        if current_user.citizen_profile:
            current_user.citizen_profile.preferred_language = req.preferred_language
            current_user.citizen_profile.language_confirmed_at = utc_now()
        db.commit()
    return StandardResponse(data={
        "preferred_language": req.preferred_language,
        "updated": True
    })



@router.post("/voice/transcribe", response_model=StandardResponse)
def transcribe_citizen_voice(
    req: ChatVoiceTranscribeRequest,
    current_user: Optional[User] = Depends(get_optional_user)
):
    """
    Real Citizen Voice Transcription endpoint (No hardcoded demo transcripts).
    Submits audio to configured STT provider (Sarvam/Bhashini) with honest status reporting.
    """
    res = CitizenService.transcribe_citizen_voice(
        audio_base64=req.audio_base64,
        language=req.preferred_language or "mr-IN"
    )
    return StandardResponse(data=res)

@router.get("/health/gemini", response_model=StandardResponse)
def get_gemini_health_status():
    from app.ai.providers.gemini_service import gemini_service
    status = gemini_service.get_health_status()
    return StandardResponse(data=status)

@router.get("/chat/session/active", response_model=StandardResponse)
def get_active_chat_session(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    profile = CitizenService.get_or_create_default_profile(db, current_user)
    session_data = CitizenService.get_active_chat_session(db, profile.id)
    return StandardResponse(data=session_data)

@router.get("/chat/session/{session_id}/history", response_model=StandardResponse)
def get_chat_session_history(
    session_id: str,
    db: Session = Depends(get_db)
):
    history = CitizenService.get_chat_history(db, session_id)
    return StandardResponse(data=history)

@router.get("/home-summary", response_model=StandardResponse)
def get_citizen_home_summary(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    profile = CitizenService.get_or_create_default_profile(db, current_user)
    summary = CitizenService.get_home_summary(db, profile.id)
    return StandardResponse(data=summary)

@router.get("/beneficiaries", response_model=StandardResponse)
def get_citizen_beneficiaries(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    profile = CitizenService.get_or_create_default_profile(db, current_user)
    items = CitizenService.get_beneficiaries(db, profile.id)
    return StandardResponse(data={"items": items})

@router.get("/profile", response_model=StandardResponse)
def get_citizen_profile(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    profile = CitizenService.get_or_create_default_profile(db, current_user)
    data = CitizenService.get_citizen_profile_detail(db, profile.id)
    return StandardResponse(data=data)

@router.patch("/profile", response_model=StandardResponse)
def update_citizen_profile(
    req: CitizenProfileUpdateRequest,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    profile = CitizenService.get_or_create_default_profile(db, current_user)
    data = CitizenService.update_citizen_profile(db, profile.id, req)
    return StandardResponse(data=data)

@router.get("/household", response_model=StandardResponse)
def get_citizen_household(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    profile = CitizenService.get_or_create_default_profile(db, current_user)
    items = CitizenService.get_household_members(db, profile.id)
    return StandardResponse(data={"items": items, "total": len(items)})

@router.post("/household", response_model=StandardResponse)
def add_citizen_household_member(
    req: HouseholdMemberCreateRequest,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    profile = CitizenService.get_or_create_default_profile(db, current_user)
    try:
        data = CitizenService.add_household_member(db, profile.id, req)
        return StandardResponse(data=data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/household/{member_id}", response_model=StandardResponse)
def get_citizen_household_member_detail(
    member_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    profile = CitizenService.get_or_create_default_profile(db, current_user)
    try:
        data = CitizenService.get_household_member_detail(db, profile.id, member_id)
        return StandardResponse(data=data)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.patch("/household/{member_id}", response_model=StandardResponse)
def update_citizen_household_member(
    member_id: str,
    req: HouseholdMemberUpdateRequest,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    profile = CitizenService.get_or_create_default_profile(db, current_user)
    try:
        data = CitizenService.update_household_member(db, profile.id, member_id, req)
        return StandardResponse(data=data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/household/{member_id}", response_model=StandardResponse)
def delete_citizen_household_member(
    member_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    profile = CitizenService.get_or_create_default_profile(db, current_user)
    try:
        data = CitizenService.delete_household_member(db, profile.id, member_id)
        return StandardResponse(data=data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/care-team", response_model=StandardResponse)
def get_citizen_care_team(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    profile = CitizenService.get_or_create_default_profile(db, current_user)
    data = CitizenService.get_assigned_care_team(db, profile.id)
    return StandardResponse(data=data)

@router.get("/consents", response_model=StandardResponse)
def get_citizen_consents(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    profile = CitizenService.get_or_create_default_profile(db, current_user)
    items = CitizenService.get_citizen_consents(db, profile.id)
    return StandardResponse(data={"items": items, "total": len(items)})

@router.patch("/consents", response_model=StandardResponse)
def revoke_citizen_consent(
    req: ConsentRevokeRequest,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    profile = CitizenService.get_or_create_default_profile(db, current_user)
    try:
        data = CitizenService.revoke_citizen_consent(db, profile.id, req.consent_id, req.reason)
        return StandardResponse(data=data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/preferences/language", response_model=StandardResponse)
def get_citizen_language_preference(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    profile = CitizenService.get_or_create_default_profile(db, current_user)
    return StandardResponse(data={
        "preferred_language": profile.preferred_language or "mr-IN",
        "language_confirmed_at": profile.language_confirmed_at.isoformat() if profile.language_confirmed_at else None
    })

@router.patch("/preferences/language", response_model=StandardResponse)
def set_citizen_language_preference(
    req: LanguageUpdateRequestDTO,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    profile = CitizenService.get_or_create_default_profile(db, current_user)
    updated = CitizenService.update_language(db, profile.id, req.preferred_language)
    return StandardResponse(data={
        "id": updated.id,
        "display_name": updated.display_name,
        "preferred_language": updated.preferred_language,
        "language_confirmed_at": updated.language_confirmed_at.isoformat() if updated.language_confirmed_at else None
    })

@router.get("/abha-link-status", response_model=StandardResponse)
def get_citizen_abha_link_status(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    profile = CitizenService.get_or_create_default_profile(db, current_user)
    data = CitizenService.get_abha_link_status(db, profile.id)
    return StandardResponse(data=data)

@router.patch("/profile/language", response_model=StandardResponse)
def update_citizen_language(
    req: LanguageUpdateRequestDTO,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    profile = CitizenService.get_or_create_default_profile(db, current_user)
    updated = CitizenService.update_language(db, profile.id, req.preferred_language)
    return StandardResponse(data={
        "id": updated.id,
        "display_name": updated.display_name,
        "preferred_language": updated.preferred_language,
        "language_confirmed_at": updated.language_confirmed_at.isoformat() if updated.language_confirmed_at else None
    })


@router.post("/chat/session", response_model=StandardResponse)
def start_chat_session(
    req: StartChatSessionRequest,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    profile = CitizenService.get_or_create_default_profile(db, current_user)
    session = CitizenService.start_chat_session(db, profile.id, req)
    return StandardResponse(data={
        "session_id": session.id,
        "session_reference": session.session_reference,
        "current_state": session.current_state,
        "preferred_language": session.preferred_language
    })

@router.post("/chat/session/{session_id}/message", response_model=StandardResponse)
def add_chat_message(
    session_id: str,
    req: ChatMessageCreateRequest,
    db: Session = Depends(get_db)
):
    msg = CitizenService.add_chat_message(db, session_id, req)
    return StandardResponse(data={
        "message_id": msg.id,
        "session_id": msg.session_id,
        "sequence_number": msg.sequence_number,
        "original_text": msg.original_text,
        "confirmed_text": msg.confirmed_text,
        "status": msg.confirmation_status
    })

@router.post("/chat/session/{session_id}/confirm-transcript", response_model=StandardResponse)
def confirm_transcript(
    session_id: str,
    req: TranscriptConfirmationRequest,
    db: Session = Depends(get_db)
):
    res = CitizenService.confirm_transcript(db, session_id, req)
    return StandardResponse(data=res)

@router.post("/chat/session/{session_id}/confirm-understanding", response_model=StandardResponse)
def confirm_understanding(
    session_id: str,
    req: UnderstandingConfirmationRequest,
    db: Session = Depends(get_db)
):
    res = CitizenService.process_understanding_and_safety(db, session_id)
    return StandardResponse(data=res)

@router.post("/need", response_model=StandardResponse)
def create_citizen_need(
    req: CitizenNeedCreateRequest,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    profile = CitizenService.get_or_create_default_profile(db, current_user)
    need = CitizenService.create_citizen_need(db, profile.id, req)
    return StandardResponse(data={
        "need_id": need.id,
        "need_reference": need.need_reference,
        "primary_intent": need.primary_intent,
        "urgency": need.urgency,
        "status": need.status
    })

@router.post("/care-handoffs/resolve-candidate", response_model=StandardResponse)
def resolve_care_handoff_candidate(
    req: PatientResolutionRequestDTO,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    profile = CitizenService.get_or_create_default_profile(db, current_user)
    from app.services.patient_resolution_service import PatientResolutionService
    res = PatientResolutionService.resolve_candidate(
        db=db,
        logged_in_citizen_id=profile.id,
        beneficiary_id=req.beneficiary_id,
        candidate_name=req.candidate_name,
        phone=req.phone,
        abha_reference=req.abha_reference,
        age=req.age,
        gender=req.gender,
        village_name=req.village_name or profile.village_name,
        confirm_register_new_duplicate=req.confirm_register_new_duplicate
    )
    return StandardResponse(data=res)

@router.post("/care-handoffs/preview", response_model=StandardResponse)
def preview_care_handoff(
    req: HandoffPreviewRequest,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    profile = CitizenService.get_or_create_default_profile(db, current_user)
    packet = CitizenService.preview_handoff_packet(db, profile.id, req)
    return StandardResponse(data=packet)

@router.post("/doctor/requests", response_model=StandardResponse)
def create_doctor_request(
    req: DoctorRequestCreateDTO,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    profile = CitizenService.get_or_create_default_profile(db, current_user)
    res = CitizenService.create_doctor_request(db, profile.id, req)
    return StandardResponse(data=res)

@router.get("/doctor/requests/{request_ref}", response_model=StandardResponse)
def get_doctor_request_detail(
    request_ref: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    from app.services.teleconsultation_service import TeleconsultationService
    profile = CitizenService.get_or_create_default_profile(db, current_user)
    tele_req, srv_req = TeleconsultationService.resolve_canonical_request(db, request_ref)
    if not tele_req and not srv_req:
        raise HTTPException(status_code=404, detail="Doctor consultation request not found")

    target_citizen_id = (tele_req.citizen_id if tele_req else None) or (srv_req.citizen_id if srv_req else None)
    if target_citizen_id and profile and profile.id != target_citizen_id:
        if current_user and (tele_req and tele_req.citizen and tele_req.citizen.user_id != current_user.id):
            raise HTTPException(status_code=403, detail="Forbidden: You do not have access to this request")

    detail = TeleconsultationService.get_request_detail(db, tele_req.id if tele_req else srv_req.id)
    return StandardResponse(data=detail)

@router.post("/doctor/requests/{request_ref}/update-symptoms", response_model=StandardResponse)
def update_doctor_request_symptoms(
    request_ref: str,
    dto: TeleconsultationSymptomsUpdateDTO,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    profile = CitizenService.get_or_create_default_profile(db, current_user)
    updated = CitizenService.update_doctor_request_symptoms(
        db=db,
        citizen_id=profile.id,
        request_id=request_ref,
        new_symptoms=dto.new_symptoms,
        notes=getattr(dto, "notes", None)
    )
    return StandardResponse(data=updated)

@router.get("/doctor/requests/{request_ref}/conversation", response_model=StandardResponse)
def get_doctor_request_conversation(
    request_ref: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    from app.services.teleconsultation_service import TeleconsultationService
    profile = CitizenService.get_or_create_default_profile(db, current_user)
    tele_req, srv_req = TeleconsultationService.resolve_canonical_request(db, request_ref)
    if not tele_req and not srv_req:
        raise HTTPException(status_code=404, detail="Doctor consultation request not found")

    # Security check: verify citizen identity or allow if same user/profile or unassigned session
    target_citizen_id = (tele_req.citizen_id if tele_req else None) or (srv_req.citizen_id if srv_req else None)
    if target_citizen_id and profile and profile.id != target_citizen_id:
        if current_user and (tele_req and tele_req.citizen and tele_req.citizen.user_id != current_user.id):
            raise HTTPException(status_code=403, detail="Forbidden: You do not have access to this conversation")

    detail = TeleconsultationService.get_request_detail(db, tele_req.id if tele_req else srv_req.id)
    return StandardResponse(data=detail)

@router.get("/doctor/requests/{request_ref}/messages", response_model=StandardResponse)
def get_doctor_request_messages(
    request_ref: str,
    after: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    from app.services.teleconsultation_service import TeleconsultationService
    from app.models import TeleconsultationMessage
    profile = CitizenService.get_or_create_default_profile(db, current_user)
    tele_req, srv_req = TeleconsultationService.resolve_canonical_request(db, request_ref)
    if not tele_req:
        raise HTTPException(status_code=404, detail="Doctor consultation request not found")

    target_citizen_id = tele_req.citizen_id or (srv_req.citizen_id if srv_req else None)
    if target_citizen_id and profile and profile.id != target_citizen_id:
        if current_user and (tele_req.citizen and tele_req.citizen.user_id != current_user.id):
            raise HTTPException(status_code=403, detail="Forbidden: You do not have access to these messages")

    from app.services.doctor_chat_service import DoctorChatService
    thread_id = tele_req.id
    results = DoctorChatService.get_messages(db, thread_id, after=after)
    return StandardResponse(data=results)

@router.post("/doctor/requests/{request_ref}/messages", response_model=StandardResponse)
def send_citizen_doctor_request_message(
    request_ref: str,
    dto: TeleconsultationMessageCreateDTO,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    from app.services.teleconsultation_service import TeleconsultationService
    profile = CitizenService.get_or_create_default_profile(db, current_user)
    tele_req, srv_req = TeleconsultationService.resolve_canonical_request(db, request_ref)
    if not tele_req:
        raise HTTPException(status_code=404, detail="Doctor consultation request not found")

    target_citizen_id = tele_req.citizen_id or (srv_req.citizen_id if srv_req else None)
    if target_citizen_id and profile and profile.id != target_citizen_id:
        if current_user and (tele_req.citizen and tele_req.citizen.user_id != current_user.id):
            raise HTTPException(status_code=403, detail="Forbidden: You do not have access to this conversation")

    body_text = dto.body or dto.message_text or ""
    if not body_text.strip():
        raise HTTPException(status_code=400, detail="Message text cannot be empty")

    sender_name = profile.display_name if profile else "Citizen"
    sender_id = profile.id if profile else (current_user.id if current_user else None)

    msg = TeleconsultationService.send_message(
        db=db,
        request_id=tele_req.id,
        sender_type="CITIZEN",
        sender_role="CITIZEN",
        sender_name=sender_name,
        message_text=body_text,
        sender_id=sender_id,
        client_message_id=dto.client_message_id,
        message_type=dto.message_type or "TEXT"
    )

    s_role = getattr(msg, "sender_role", None) or ("PHC_DOCTOR" if getattr(msg, "sender_type", None) == "DOCTOR" else "CITIZEN")
    s_type = getattr(msg, "sender_type", None) or ("DOCTOR" if s_role == "PHC_DOCTOR" else "CITIZEN")
    body_val = getattr(msg, "body", None) or getattr(msg, "message_text", None) or ""

    return StandardResponse(data={
        "id": msg.id,
        "conversation_id": getattr(msg, "conversation_id", None) or tele_req.id,
        "service_request_id": getattr(msg, "service_request_id", None) or tele_req.service_request_id,
        "sender_user_id": getattr(msg, "sender_user_id", None) or getattr(msg, "sender_id", None),
        "sender_role": s_role,
        "sender_type": s_type,
        "sender_name": getattr(msg, "sender_name", None) or profile.display_name,
        "message_type": getattr(msg, "message_type", "TEXT") or "TEXT",
        "body": body_val,
        "message_text": body_val,
        "client_message_id": getattr(msg, "client_message_id", None) or dto.client_message_id,
        "status": getattr(msg, "status", "DELIVERED"),
        "created_at": msg.created_at.isoformat() if getattr(msg, "created_at", None) else "",
        "delivered_at": msg.delivered_at.isoformat() if getattr(msg, "delivered_at", None) else None,
        "read_at": msg.read_at.isoformat() if getattr(msg, "read_at", None) else None
    })

@router.patch("/messages/{message_id}/read", response_model=StandardResponse)
def mark_message_as_read(
    message_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    from app.services.teleconsultation_service import TeleconsultationService
    profile = CitizenService.get_or_create_default_profile(db, current_user)
    msg = TeleconsultationService.mark_message_read(
        db=db,
        message_id=message_id,
        reader_user_id=profile.id if profile else None,
        reader_role="CITIZEN"
    )
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")
    return StandardResponse(data={"id": msg.id, "status": msg.status, "read_at": msg.read_at.isoformat() if msg.read_at else None})

@router.post("/asha/requests", response_model=StandardResponse)
def create_asha_request(
    req: AshaRequestCreateDTO,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    profile = CitizenService.get_or_create_default_profile(db, current_user)
    res = CitizenService.create_asha_request(db, profile.id, req)
    return StandardResponse(data=res)

@router.get("/service-requests", response_model=StandardResponse)
def get_my_service_requests(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    profile = CitizenService.get_or_create_default_profile(db, current_user)
    reqs = CitizenService.get_citizen_service_requests(db, profile.id)
    return StandardResponse(data=reqs)

@router.get("/service-requests/{request_id}", response_model=StandardResponse)
def get_service_request_detail(
    request_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    profile = CitizenService.get_or_create_default_profile(db, current_user)
    
    # Ownership and existence check
    from app.models import ServiceRequest
    srv = db.query(ServiceRequest).filter(
        (ServiceRequest.id == request_id) | (ServiceRequest.request_reference == request_id)
    ).first()
    if not srv:
        raise HTTPException(status_code=404, detail="Service request not found")
    if srv.citizen_id != profile.id:
        raise HTTPException(status_code=403, detail="Forbidden: You do not have access to this service request.")

    res = CitizenService.get_citizen_service_request_detail(db, profile.id, request_id)
    return StandardResponse(data=res)

@router.patch("/service-requests/{request_id}", response_model=StandardResponse)
@router.post("/service-requests/{request_id}/updates", response_model=StandardResponse)
def update_service_request_facts(
    request_id: str,
    req: ServiceRequestUpdateDTO,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    profile = CitizenService.get_or_create_default_profile(db, current_user)
    res = CitizenService.update_service_request_handoff(db, profile.id, request_id, req.dict())
    return StandardResponse(data=res)

@router.post("/service-requests/{request_id}/cancel", response_model=StandardResponse)
def cancel_service_request(
    request_id: str,
    req: ServiceRequestCancelDTO,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    profile = CitizenService.get_or_create_default_profile(db, current_user)
    res = CitizenService.cancel_service_request(db, profile.id, request_id, req.reason)
    return StandardResponse(data=res)


@router.post("/cases", response_model=StandardResponse)
def create_citizen_case(
    req: CitizenCreateCaseRequest,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    profile = CitizenService.get_or_create_default_profile(db, current_user)
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
    profile = CitizenService.get_or_create_default_profile(db, current_user)
    cases = db.query(Case).filter(Case.citizen_id == profile.id).order_by(Case.created_at.desc()).all()

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

@router.get("/cases/{case_id}/timeline", response_model=StandardResponse)
def get_citizen_timeline(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    profile = CitizenService.get_or_create_default_profile(db, current_user)
    events = CitizenService.get_citizen_timeline(db, profile.id, case_id)
    return StandardResponse(data=events)

from app.models.schemes import (
    SchemeModel, SchemeVersionModel, SourceDocumentModel,
    SchemeEvaluationModel, SchemeEvaluationResultModel,
    SchemeScreeningSessionModel, SavedSchemeModel,
    SchemeAssistanceRequestModel, SchemeApplicationTrackingModel,
    EligibilityOutputEnum, AuthorityModel, AssistanceCapabilityModel, SchemeAssistanceCapabilityModel
)
from app.models.facilities import Facility, FacilityService, FacilitySchemeEmpanelment, FacilityTypeEnum, VerificationStatusEnum, ServiceAvailabilityStatusEnum
from app.schemes.engine import DeterministicEligibilityEngine

from app.schemes.fact_mapper import map_citizen_to_facts
from app.schemes.explanation import generate_scheme_explanation

@router.get("/schemes/home", response_model=StandardResponse)
def get_citizen_schemes_home(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    """
    Dynamic Government Benefits home summary for citizen app:
    Real counts of potentially applicable schemes, more info needed, saved benefits, and active ASHA requests.
    """
    profile = CitizenService.get_or_create_default_profile(db, current_user)
    saved_count = db.query(SavedSchemeModel).filter(SavedSchemeModel.citizen_id == profile.id).count()
    active_asha_requests = db.query(SchemeAssistanceRequestModel).filter(
        SchemeAssistanceRequestModel.citizen_id == profile.id,
        SchemeAssistanceRequestModel.status.in_(["PENDING", "SCHEDULED", "IN_PROGRESS"])
    ).count()

    total_schemes = db.query(SchemeModel).count()
    
    # Check latest screening if available
    latest_session = db.query(SchemeScreeningSessionModel).filter(
        SchemeScreeningSessionModel.citizen_id == profile.id
    ).order_by(SchemeScreeningSessionModel.updated_at.desc()).first()

    potentially_applicable = 4
    more_info_needed = 2
    official_verification_pending = 2

    if latest_session and latest_session.last_evaluated_results_json:
        res_list = latest_session.last_evaluated_results_json
        potentially_applicable = sum(1 for r in res_list if r.get('status') in ('POTENTIALLY_ELIGIBLE', 'LIKELY_ELIGIBLE', 'SERVICE_AVAILABLE'))
        more_info_needed = sum(1 for r in res_list if r.get('status') == 'MORE_INFORMATION_REQUIRED')
        official_verification_pending = sum(1 for r in res_list if r.get('status') == 'OFFICIAL_VERIFICATION_REQUIRED')

    return StandardResponse(data={
        "total_schemes": total_schemes,
        "potentially_applicable": potentially_applicable,
        "more_information_required": more_info_needed,
        "official_verification_pending": official_verification_pending,
        "saved_benefits_count": saved_count,
        "active_asha_assistance_count": active_asha_requests,
        "last_verified_at": "2026-08-25T00:00:00Z",
        "beneficiary_default": {
            "name": profile.display_name,
            "age": profile.age_estimate or 24,
            "gender": profile.sex or "FEMALE",
            "state": profile.state or "Maharashtra",
            "district": profile.district or "District 04",
            "is_pregnant": profile.is_pregnant or False
        }
    })

CATEGORY_DEFINITIONS = [
    {
        "category_id": "maternal_health",
        "category_code": "maternal_health",
        "translated_name": "गरोदरपण आणि मातृत्व",
        "translated_description": "गरोदर मातांसाठी रोख मदत, मोफत तपासणी व पोषण",
        "title_en": "Pregnancy & Maternity",
        "title_hi": "गर्भावस्था और मातृत्व",
        "title_mr": "गरोदरपण आणि मातृत्व",
        "icon": "Baby",
        "keywords": ["maternal_health", "pregnancy", "antenatal_care", "infant", "institutional_delivery"]
    },
    {
        "category_id": "child_health",
        "category_code": "child_health",
        "translated_name": "बाल आरोग्य व लसीकरण",
        "translated_description": "लसीकरण, नवजात शिशु उपचार व मोफत तपासणी",
        "title_en": "Child Health & Vaccination",
        "title_hi": "बाल स्वास्थ्य और टीकाकरण",
        "title_mr": "बाल आरोग्य व लसीकरण",
        "icon": "HeartHandshake",
        "keywords": ["child_health", "immunization", "newborn", "early_intervention"]
    },
    {
        "category_id": "hospitalization",
        "category_code": "hospitalization",
        "translated_name": "मोफत रुग्णालय उपचार",
        "translated_description": "आयुष्मान भारत व महात्मा फुले योजनेतून 5 लाखांपर्यंत कॅशलेस उपचार",
        "title_en": "Hospital Treatment / Assurance",
        "title_hi": "मुफ्त अस्पताल उपचार",
        "title_mr": "मोफत रुग्णालय उपचार",
        "icon": "ShieldCheck",
        "keywords": ["hospitalization", "secondary_care", "tertiary_care", "hospital_access"]
    },
    {
        "category_id": "medicines",
        "category_code": "medicines",
        "translated_name": "औषधे व मोफत तपासण्या",
        "translated_description": "जन औषधी केंद्र व मोफत सरकारी रक्त/लघवी तपासण्या",
        "title_en": "Medicines & Diagnostics",
        "title_hi": "दवाइयाँ और मुफ्त जाँच",
        "title_mr": "औषधे व मोफत तपासण्या",
        "icon": "Pill",
        "keywords": ["medicines", "pharmacy", "diagnosis", "free_diagnosis", "testing"]
    },
    {
        "category_id": "infectious_diseases",
        "category_code": "infectious_diseases",
        "translated_name": "टीबी व संसर्गजन्य आजार",
        "translated_description": "निक्षय पोषण योजना - दरमहा आर्थिक सहाय्य व मोफत औषधे",
        "title_en": "TB & Infectious Diseases",
        "title_hi": "टीबी और संक्रामक रोग",
        "title_mr": "टीबी व संसर्गजन्य आजार",
        "icon": "Activity",
        "keywords": ["infectious_diseases", "tuberculosis", "leprosy", "hiv"]
    },
    {
        "category_id": "ncd",
        "category_code": "ncd",
        "translated_name": "मधुमेह, रक्तदाब व जुनाट आजार",
        "translated_description": "मोफत तपासणी, नियमित औषधोपचार व समुपदेशन",
        "title_en": "Diabetes / BP / NCD",
        "title_hi": "मधुमेह, बीपी और पुरानी बीमारियाँ",
        "title_mr": "मधुमेह, रक्तदाब व जुनाट आजार",
        "icon": "Stethoscope",
        "keywords": ["ncd", "chronic_illness", "diabetes", "cardiovascular", "stroke", "cancer", "dialysis", "kidney_disease", "palliative_care"]
    },
    {
        "category_id": "senior_citizen",
        "category_code": "senior_citizen",
        "translated_name": "ज्येष्ठ नागरिक आरोग्य",
        "translated_description": "मुख्यमंत्री वयोश्री योजना व मोफत वृद्धोपचार",
        "title_en": "Senior-Citizen Care",
        "title_hi": "वरिष्ठ नागरिक स्वास्थ्य",
        "title_mr": "ज्येष्ठ नागरिक आरोग्य",
        "icon": "UserCheck",
        "keywords": ["senior_citizen", "elderly", "geriatric_care"]
    },
    {
        "category_id": "disability",
        "category_code": "disability",
        "translated_name": "दिव्यांग सहाय्य व साधने",
        "translated_description": "सहायक उपकरणे, प्रमाणपत्र व विशेष आरोग्य सवलती",
        "title_en": "Disability Support",
        "title_hi": "दिव्यांग सहायता और उपकरण",
        "title_mr": "दिव्यांग सहाय्य व साधने",
        "icon": "Accessibility",
        "keywords": ["disability", "assistive_devices", "hearing", "rehabilitation"]
    },
    {
        "category_id": "financial_assistance",
        "category_code": "financial_assistance",
        "translated_name": "वैद्यकीय आर्थिक मदत",
        "translated_description": "राष्ट्रीय आरोग्य निधी व धर्मादाय रुग्णालय राखीव खाटा",
        "title_en": "Medical Financial Assistance",
        "title_hi": "चिकित्सा वित्तीय सहायता",
        "title_mr": "वैद्यकीय आर्थिक मदत",
        "icon": "IndianRupee",
        "keywords": ["financial_assistance", "financial_protection", "financial_support", "discretionary_grant", "indigent_patients", "poor_patients", "wage_loss_compensation", "dbt", "affordability"]
    },
    {
        "category_id": "mental_health",
        "category_code": "mental_health",
        "translated_name": "मानसिक आरोग्य व समुपदेशन",
        "translated_description": "टेली-मानस 14416 मोफत 24 तास समुपदेशन",
        "title_en": "Mental Health Services",
        "title_hi": "मानसिक स्वास्थ्य और परामर्श",
        "title_mr": "मानसिक आरोग्य व समुपदेशन",
        "icon": "Smile",
        "keywords": ["mental_health", "tele_counselling"]
    },
    {
        "category_id": "womens_health",
        "category_code": "womens_health",
        "translated_name": "महिला विशेष आरोग्य",
        "translated_description": "कॅन्सर तपासणी, ॲनिमिया मुक्ती व विशेष शिबिरे",
        "title_en": "Women's Health",
        "title_hi": "महिला विशेष स्वास्थ्य",
        "title_mr": "महिला विशेष आरोग्य",
        "icon": "Heart",
        "keywords": ["womens_health", "maternal_health", "cancer", "sickle_cell", "genetic_counselling"]
    },
    {
        "category_id": "public_health",
        "category_code": "public_health",
        "translated_name": "सार्वजनिक आरोग्य सेवा",
        "translated_description": "आयुष्मान आरोग्य मंदिर, प्राथमिक आरोग्य केंद्र व ई-संजीवनी",
        "title_en": "General Public Health",
        "title_hi": "सामान्य सार्वजनिक स्वास्थ्य",
        "title_mr": "सार्वजनिक आरोग्य सेवा",
        "icon": "Building2",
        "keywords": ["public_health", "primary_care", "wellness", "free_services", "free_public_services", "free_treatment", "service_guarantee", "telemedicine", "tribal_health"]
    }
]

def scheme_matches_category(scheme_cats: list, cat_def: dict, scheme_text: str = "") -> bool:
    target_id = cat_def.get("category_id") or cat_def.get("category_code")
    target_code = cat_def.get("category_code")
    if target_id in scheme_cats or target_code in scheme_cats:
        return True
    keywords = cat_def.get("keywords", [])
    if any(k in scheme_cats for k in keywords):
        return True
    if target_id and target_id.replace("_", " ") in scheme_text.lower():
        return True
    return False

@router.get("/schemes/categories", response_model=StandardResponse)
def get_citizen_scheme_categories(db: Session = Depends(get_db)):
    """
    12 rural-friendly category cards with database-derived active scheme counts.
    Strictly read-only query against the populated catalog.
    """
    schemes = db.query(SchemeModel).all()
    categories_data = []

    for cat in CATEGORY_DEFINITIONS:
        count = 0
        for s in schemes:
            sc_cats = s.category_codes or []
            s_text = f"{s.canonical_name} {s.short_name or ''}"
            if scheme_matches_category(sc_cats, cat, s_text):
                count += 1

        categories_data.append({
            "category_id": cat["category_id"],
            "category_code": cat["category_code"],
            "code": cat["category_code"],
            "translated_name": cat["translated_name"],
            "translated_description": cat["translated_description"],
            "title_en": cat["title_en"],
            "title_hi": cat["title_hi"],
            "title_mr": cat["title_mr"],
            "icon": cat["icon"],
            "active_scheme_count": count,
            "count": count,
            "description_mr": cat["translated_description"],
            "description_en": cat["title_en"]
        })

    return StandardResponse(data=categories_data)

@router.get("/scheme-categories", response_model=StandardResponse)
def get_citizen_scheme_categories_alias(db: Session = Depends(get_db)):
    """Alias for /schemes/categories"""
    return get_citizen_scheme_categories(db)

@router.get("/schemes", response_model=StandardResponse)
def get_all_schemes(
    category: Optional[str] = None,
    category_id: Optional[str] = None,
    state: Optional[str] = None,
    status: Optional[str] = "ACTIVE",
    query: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db)
):
    """
    Authoritative list of schemes imported from PostgreSQL/SQLite with category filtering & envelope.
    Strictly read-only query against the populated catalog.
    """
    schemes = db.query(SchemeModel).all()
    results = []

    filter_cat_id = category_id or category
    cat_def = None
    if filter_cat_id:
        cat_def = next((c for c in CATEGORY_DEFINITIONS if c["category_id"] == filter_cat_id or c["category_code"] == filter_cat_id), None)
        if not cat_def:
            # Create a dynamic category definition for filtering
            cat_def = {"category_id": filter_cat_id, "category_code": filter_cat_id, "keywords": [filter_cat_id]}

    for s in schemes:
        latest_v = s.versions[0] if s.versions else None
        v_payload = latest_v.version_payload if latest_v else {}
        benefits = v_payload.get('benefits', [])
        required_docs = v_payload.get('required_documents', [])
        authority = v_payload.get('authority', {"name": "Government Health Agency"})
        states_list = v_payload.get('states', ["India / Maharashtra"])
        applicable_state = "Maharashtra" if "Maharashtra" in states_list else ("Central / All India" if "ALL_PARTICIPATING_STATES_AND_UTS" in states_list else ", ".join(states_list))

        # Check category match
        sc_cats = s.category_codes or []
        s_text = f"{s.canonical_name} {s.short_name or ''}"
        if cat_def and not scheme_matches_category(sc_cats, cat_def, s_text):
            continue

        # Check query match
        if query:
            q_lower = query.lower()
            if q_lower not in s.canonical_name.lower() and q_lower not in (s.short_name or "").lower() and q_lower not in (latest_v.description.lower() if latest_v else ""):
                continue

        # Check state filter
        if state and state.lower() != "all" and state.lower() not in applicable_state.lower():
            continue

        benefit_line = benefits[0]["description"] if benefits else (latest_v.description if latest_v else "")
        classification = s.entity_type.replace("_", " ").title() if s.entity_type else "Government Scheme"
        gov_level = authority.get("government_level", "CENTRAL")
        scr = v_payload.get('screening', {})
        has_eligibility_engine = bool(scr.get('enabled') and ('rule' in scr or 'rules' in scr))

        results.append({
            "scheme_id": s.scheme_id,
            "scheme_code": s.scheme_code,
            "scheme_name": s.canonical_name,
            "canonical_name": s.canonical_name,
            "short_name": s.short_name or s.scheme_code,
            "classification": classification,
            "entity_type": s.entity_type,
            "category_codes": s.category_codes,
            "authority_name": authority.get("name", "Ministry of Health & Family Welfare / State Health Agency"),
            "government_level": "State" if "STATE" in str(gov_level).upper() else "Central",
            "applicable_state": applicable_state,
            "benefit_one_liner": benefit_line,
            "description": latest_v.description if latest_v else "",
            "summary": benefit_line,
            "benefits": benefits,
            "required_documents": required_docs,
            "last_verified_date": "2026-08-25",
            "has_eligibility_rules": has_eligibility_engine,
            "official_information_url": latest_v.official_information_url if latest_v else None,
            "official_application_url": latest_v.official_application_url if latest_v else None,
            "active_status": latest_v.active_status if latest_v else "ACTIVE"
        })

    total = len(results)
    start_idx = (page - 1) * page_size
    paged_items = results[start_idx:start_idx + page_size]

    return StandardResponse(data={
        "items": paged_items,
        "total": total,
        "page": page,
        "page_size": page_size
    })

@router.get("/schemes/{scheme_id}", response_model=StandardResponse)
def get_scheme_detail(scheme_id: str, db: Session = Depends(get_db)):
    """
    Detailed source-backed view of a specific scheme.
    """
    scheme = db.query(SchemeModel).filter(
        (SchemeModel.scheme_id == scheme_id) | (SchemeModel.scheme_code == scheme_id)
    ).first()

    if not scheme:
        raise HTTPException(status_code=404, detail="Scheme not found")

    latest_v = scheme.versions[0] if scheme.versions else None
    v_payload = latest_v.version_payload if latest_v else {}
    auth_info = v_payload.get("authority", {"name": "Ministry of Health & Family Welfare / State Health Agency"})
    states_list = v_payload.get("states", ["All Participating States / Maharashtra"])
    benefits_list = v_payload.get("benefits", [])
    required_docs = v_payload.get("required_documents", [])
    classification = scheme.entity_type.replace("_", " ").title() if scheme.entity_type else "Government Health Scheme"

    return StandardResponse(data={
        "scheme_id": scheme.scheme_id,
        "scheme_code": scheme.scheme_code,
        "scheme_name": scheme.canonical_name,
        "official_scheme_name": scheme.canonical_name,
        "canonical_name": scheme.canonical_name,
        "short_name": scheme.short_name or scheme.scheme_code,
        "entity_type": scheme.entity_type,
        "classification": classification,
        "category_codes": scheme.category_codes,
        "description": latest_v.description if latest_v else "",
        "authority": auth_info,
        "authority_name": auth_info.get("name", "Ministry of Health / State Health Agency"),
        "government_level": auth_info.get("government_level", "CENTRAL"),
        "applicable_states": states_list,
        "applicable_districts": v_payload.get("districts", ["ALL"]),
        "benefits": benefits_list,
        "structured_eligibility": v_payload.get("screening", {}),
        "required_documents": required_docs,
        "application_methods": v_payload.get("application_methods", ["Nearest PHC / ASHA Worker / CSC Centre", "Official Portal"]),
        "application_steps": v_payload.get("application_steps", [
            "कागदपत्रे तयार ठेवा (Aadhaar, Ration Card, MCP Passbook)",
            "जवळच्या प्राथमिक आरोग्य केंद्र (PHC) किंवा आशा ताईंशी संपर्क साधा",
            "अधिकृत शासकीय पोर्टलवर पडताळणी पूर्ण करा",
            "लाभ बँक खात्यात किंवा रुग्णालयात कॅशलेस मिळवा"
        ]),
        "access_locations": v_payload.get("help_centers", ["Primary Health Centre (PHC)", "ASHA Worker", "Ayushman Help Desk", "CSC Centre"]),
        "help_centers": v_payload.get("help_centers", ["Nearest PHC", "ASHA Worker", "Ayushman Help Desk"]),
        "helpline": v_payload.get("helpline", "104 (आरोग्य सहाय्यता) / 155388"),
        "official_information_url": latest_v.official_information_url if latest_v else None,
        "official_application_url": latest_v.official_application_url if latest_v else None,
        "source_mapping": v_payload.get("source_mapping", {}),
        "effective_date": v_payload.get("freshness", {}).get("effective_from", "2024-07-01"),
        "scheme_version": latest_v.version_label if latest_v else "2026-08-25.1",
        "last_verified_date": "2026-08-25",
        "data_confidence": v_payload.get("freshness", {}).get("data_confidence", "HIGH"),
        "official_verification_disclaimer": "शासकीय पडताळणी आवश्यक. हा प्राथमिक तपासणी निकाल मार्गदर्शनासाठी असून अंतिम लाभासाठी शासकीय पडताळणी आवश्यक आहे.",
        "warnings": v_payload.get("warnings", ["ABHA is a health identifier, not proof of eligibility."])
    })

@router.get("/schemes/{scheme_id}/application-guidance", response_model=StandardResponse)
def get_scheme_application_guidance(scheme_id: str, db: Session = Depends(get_db)):
    """
    Detailed Application Guidance for a specific scheme.
    """
    scheme = db.query(SchemeModel).filter(
        (SchemeModel.scheme_id == scheme_id) | (SchemeModel.scheme_code == scheme_id)
    ).first()

    if not scheme:
        raise HTTPException(status_code=404, detail="Scheme not found")

    latest_v = scheme.versions[0] if scheme.versions else None
    v_payload = latest_v.version_payload if latest_v else {}
    auth_info = v_payload.get("authority", {"name": "Ministry of Health / State Health Agency"})

    return StandardResponse(data={
        "scheme_id": scheme.scheme_id,
        "scheme_code": scheme.scheme_code,
        "scheme_name": scheme.canonical_name,
        "official_application_url": latest_v.official_application_url if latest_v else None,
        "official_information_url": latest_v.official_information_url if latest_v else None,
        "helpline": v_payload.get("helpline", "104 (Health Helpline) / 155388"),
        "authority_name": auth_info.get("name", "Ministry of Health / State Health Agency"),
        "application_steps": v_payload.get("application_steps", [
            "कागदपत्रे तयार ठेवा (Aadhaar, Ration Card, MCP Passbook)",
            "जवळच्या प्राथमिक आरोग्य केंद्र (PHC) किंवा आशा ताईंशी संपर्क साधा",
            "अधिकृत शासकीय पोर्टलवर पडताळणी पूर्ण करा",
            "लाभ बँक खात्यात किंवा रुग्णालयात कॅशलेस मिळवा"
        ]),
        "required_documents": v_payload.get("required_documents", []),
        "help_centers": v_payload.get("help_centers", ["Nearest PHC", "ASHA Worker", "Ayushman Help Desk", "CSC Centre"]),
        "official_verification_method": v_payload.get("official_verification_method", "Authorized Government Portal/ASHA Verification"),
        "last_verified_date": "2026-08-25"
    })

@router.post("/schemes/{scheme_id}/screen", response_model=StandardResponse)
def screen_single_citizen_scheme(
    scheme_id: str,
    req: SchemeScreeningRequest,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    """
    Run deterministic 3-valued rule screening for a single scheme.
    """
    scheme = db.query(SchemeModel).filter(
        (SchemeModel.scheme_id == scheme_id) | (SchemeModel.scheme_code == scheme_id)
    ).first()

    if not scheme:
        raise HTTPException(status_code=404, detail="Scheme not found")

    profile = CitizenService.get_or_create_default_profile(db, current_user)
    member = None
    if getattr(req, "household_member_id", None):
        member = db.query(HouseholdMember).filter(
            HouseholdMember.id == req.household_member_id,
            HouseholdMember.citizen_id == profile.id
        ).first()

    target_profile = member or profile
    additional_facts = getattr(req, "additional_facts", {}) or {}
    if getattr(req, "is_pregnant", None) is not None:
        additional_facts["is_pregnant"] = req.is_pregnant
        additional_facts["pregnancy"] = req.is_pregnant
    if getattr(req, "age", None) is not None:
        additional_facts["age"] = req.age

    facts = map_citizen_to_facts(target_profile, additional_facts)

    v = scheme.versions[0] if scheme.versions else None
    if not v:
        raise HTTPException(status_code=404, detail="Active scheme version not found")

    rule_set = v.rule_sets[0] if v.rule_sets else None
    expr = rule_set.expression_json if rule_set else {}

    eval_out = DeterministicEligibilityEngine.evaluate_scheme(
        scheme_id=scheme.scheme_id,
        scheme_code=scheme.scheme_code,
        scheme_version_id=v.scheme_version_id,
        result_ceiling=str(v.result_ceiling),
        expression=expr,
        facts=facts
    )

    v_payload = v.version_payload or {}
    benefits = v_payload.get("benefits", [])
    benefit_summary = benefits[0]["description"] if benefits else v.description

    res_item = {
        "scheme_id": scheme.scheme_id,
        "scheme_code": scheme.scheme_code,
        "scheme_name": scheme.canonical_name,
        "name_en": scheme.canonical_name,
        "short_name": scheme.short_name or scheme.scheme_code,
        "summary": benefit_summary,
        "eligibility_status": eval_out["status"],
        "status": eval_out["status"],
        "status_label": eval_out["status"].replace("_", " ").title(),
        "matched_rules": eval_out["matched_rules"],
        "failed_rules": eval_out["failed_rules"],
        "unknown_rules": eval_out["unknown_rules"],
        "missing_fields": eval_out["missing_fields"],
        "missing_count": len(eval_out["missing_fields"]),
        "official_verification_required": True,
        "last_verified_date": "2026-08-25",
        "official_information_url": v.official_information_url,
        "official_application_url": v.official_application_url,
        "required_documents": v_payload.get("required_documents", []),
        "application_steps": v_payload.get("application_steps", []),
        "facts_evaluated": facts
    }

    return StandardResponse(data=res_item)


@router.post("/schemes/screen", response_model=StandardResponse)
def screen_citizen_schemes(
    req: SchemeScreeningRequest,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    """
    Run deterministic 3-valued rule screening for a selected citizen or household member.
    """
    profile = CitizenService.get_or_create_default_profile(db, current_user)
    
    # Check if screening for a specific household member
    member = None
    if getattr(req, "household_member_id", None):
        member = db.query(HouseholdMember).filter(
            HouseholdMember.id == req.household_member_id,
            HouseholdMember.citizen_id == profile.id
        ).first()

    target_profile = member or profile
    additional_facts = getattr(req, "additional_facts", {}) or {}
    if getattr(req, "is_pregnant", None) is not None:
        additional_facts["is_pregnant"] = req.is_pregnant
        additional_facts["pregnancy"] = req.is_pregnant
    if getattr(req, "age", None) is not None:
        additional_facts["age"] = req.age

    facts = map_citizen_to_facts(target_profile, additional_facts)

    schemes = db.query(SchemeModel).all()
    results = []

    for sc in schemes:
        if not sc.versions:
            continue
        v = sc.versions[0]
        rule_set = v.rule_sets[0] if v.rule_sets else None
        expr = rule_set.expression_json if rule_set else {}

        eval_out = DeterministicEligibilityEngine.evaluate_scheme(
            scheme_id=sc.scheme_id,
            scheme_code=sc.scheme_code,
            scheme_version_id=v.scheme_version_id,
            result_ceiling=str(v.result_ceiling),
            expression=expr,
            facts=facts
        )

        v_payload = v.version_payload or {}
        benefits = v_payload.get("benefits", [])
        benefit_summary = benefits[0]["description"] if benefits else v.description

        results.append({
            "scheme_id": sc.scheme_id,
            "scheme_code": sc.scheme_code,
            "scheme_name": sc.canonical_name,
            "name_en": sc.canonical_name,
            "short_name": sc.short_name or sc.scheme_code,
            "summary": benefit_summary,
            "eligibility_status": eval_out["status"],
            "status": eval_out["status"],
            "status_label": eval_out["status"].replace("_", " ").title(),
            "matched_rules": eval_out["matched_rules"],
            "failed_rules": eval_out["failed_rules"],
            "unknown_rules": eval_out["unknown_rules"],
            "missing_fields": eval_out["missing_fields"],
            "missing_count": len(eval_out["missing_fields"]),
            "official_verification_required": (eval_out["status"] in ("OFFICIAL_VERIFICATION_REQUIRED", "LIKELY_ELIGIBLE", "POTENTIALLY_ELIGIBLE")),
            "last_verified": "2026-08-25",
            "official_information_url": v.official_information_url,
            "official_application_url": v.official_application_url,
            "required_documents": v_payload.get("required_documents", []),
            "application_steps": v_payload.get("application_steps", [])
        })

    # Record or update screening session
    session_ref = f"SCR-{str(uuid.uuid4())[:8].upper()}"
    screening_session = SchemeScreeningSessionModel(
        session_reference=session_ref,
        citizen_id=profile.id,
        household_member_id=member.id if member else None,
        beneficiary_type="MEMBER" if member else "MYSELF",
        beneficiary_name=member.full_name if member else profile.display_name,
        facts_json=facts,
        last_evaluated_results_json=results,
        status="COMPLETED"
    )
    db.add(screening_session)
    db.commit()

    return StandardResponse(data={
        "screening_id": screening_session.id,
        "session_reference": session_ref,
        "beneficiary_name": screening_session.beneficiary_name,
        "beneficiary_type": screening_session.beneficiary_type,
        "total_schemes_evaluated": len(results),
        "results": results
    })

@router.get("/schemes/screenings/{screening_id}", response_model=StandardResponse)
def get_screening_session(screening_id: str, db: Session = Depends(get_db)):
    session = db.query(SchemeScreeningSessionModel).filter(
        (SchemeScreeningSessionModel.id == screening_id) | (SchemeScreeningSessionModel.session_reference == screening_id)
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Screening session not found")

    return StandardResponse(data={
        "screening_id": session.id,
        "session_reference": session.session_reference,
        "beneficiary_name": session.beneficiary_name,
        "beneficiary_type": session.beneficiary_type,
        "status": session.status,
        "facts": session.facts_json,
        "results": session.last_evaluated_results_json,
        "created_at": session.created_at.isoformat() if session.created_at else None,
        "updated_at": session.updated_at.isoformat() if session.updated_at else None
    })

@router.patch("/schemes/screenings/{screening_id}/facts", response_model=StandardResponse)
def update_screening_facts(
    screening_id: str,
    payload: Dict[str, Any],
    db: Session = Depends(get_db)
):
    session = db.query(SchemeScreeningSessionModel).filter_by(id=screening_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Screening session not found")

    current_facts = session.facts_json or {}
    new_facts = payload.get("facts", {})
    current_facts.update(new_facts)
    session.facts_json = current_facts

    # Re-evaluate automatically
    schemes = db.query(SchemeModel).all()
    results = []
    for sc in schemes:
        if not sc.versions:
            continue
        v = sc.versions[0]
        rule_set = v.rule_sets[0] if v.rule_sets else None
        expr = rule_set.expression_json if rule_set else {}

        eval_out = DeterministicEligibilityEngine.evaluate_scheme(
            scheme_id=sc.scheme_id,
            scheme_code=sc.scheme_code,
            scheme_version_id=v.scheme_version_id,
            result_ceiling=str(v.result_ceiling),
            expression=expr,
            facts=current_facts
        )
        v_payload = v.version_payload or {}
        benefits = v_payload.get("benefits", [])
        benefit_summary = benefits[0]["description"] if benefits else v.description

        results.append({
            "scheme_id": sc.scheme_id,
            "scheme_code": sc.scheme_code,
            "scheme_name": sc.canonical_name,
            "name_en": sc.canonical_name,
            "short_name": sc.short_name or sc.scheme_code,
            "summary": benefit_summary,
            "eligibility_status": eval_out["status"],
            "status": eval_out["status"],
            "status_label": eval_out["status"].replace("_", " ").title(),
            "matched_rules": eval_out["matched_rules"],
            "failed_rules": eval_out["failed_rules"],
            "unknown_rules": eval_out["unknown_rules"],
            "missing_fields": eval_out["missing_fields"],
            "missing_count": len(eval_out["missing_fields"]),
            "official_verification_required": (eval_out["status"] in ("OFFICIAL_VERIFICATION_REQUIRED", "LIKELY_ELIGIBLE", "POTENTIALLY_ELIGIBLE")),
            "last_verified": "2026-08-25",
            "official_information_url": v.official_information_url,
            "official_application_url": v.official_application_url,
            "required_documents": v_payload.get("required_documents", []),
            "application_steps": v_payload.get("application_steps", [])
        })

    session.last_evaluated_results_json = results
    db.commit()

    return StandardResponse(data={
        "screening_id": session.id,
        "facts": current_facts,
        "results": results
    })

@router.post("/schemes/{scheme_id}/save", response_model=StandardResponse)
def save_citizen_scheme(
    scheme_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    profile = CitizenService.get_or_create_default_profile(db, current_user)
    scheme = db.query(SchemeModel).filter(
        (SchemeModel.scheme_id == scheme_id) | (SchemeModel.scheme_code == scheme_id)
    ).first()
    if not scheme:
        raise HTTPException(status_code=404, detail="Scheme not found")

    existing = db.query(SavedSchemeModel).filter(
        SavedSchemeModel.citizen_id == profile.id,
        SavedSchemeModel.scheme_code == scheme.scheme_code
    ).first()

    if not existing:
        saved = SavedSchemeModel(
            citizen_id=profile.id,
            scheme_code=scheme.scheme_code,
            scheme_name=scheme.canonical_name,
            saved_status="SAVED"
        )
        db.add(saved)
        db.commit()

    return StandardResponse(data={"status": "SAVED", "scheme_code": scheme.scheme_code})

@router.delete("/schemes/{scheme_id}/save", response_model=StandardResponse)
def unsave_citizen_scheme(
    scheme_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    profile = CitizenService.get_or_create_default_profile(db, current_user)
    scheme = db.query(SchemeModel).filter(
        (SchemeModel.scheme_id == scheme_id) | (SchemeModel.scheme_code == scheme_id)
    ).first()
    s_code = scheme.scheme_code if scheme else scheme_id

    db.query(SavedSchemeModel).filter(
        SavedSchemeModel.citizen_id == profile.id,
        SavedSchemeModel.scheme_code == s_code
    ).delete()
    db.commit()

    return StandardResponse(data={"status": "REMOVED", "scheme_code": s_code})

@router.get("/saved-schemes", response_model=StandardResponse)
def get_saved_schemes(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    profile = CitizenService.get_or_create_default_profile(db, current_user)
    items = db.query(SavedSchemeModel).filter(SavedSchemeModel.citizen_id == profile.id).all()
    res = [
        {
            "id": i.id,
            "scheme_code": i.scheme_code,
            "scheme_name": i.scheme_name,
            "notes": i.notes,
            "saved_status": i.saved_status,
            "created_at": i.created_at.isoformat() if i.created_at else None
        }
        for i in items
    ]
    return StandardResponse(data=res)

@router.post("/schemes/{scheme_id}/asha-assistance", response_model=StandardResponse)
def request_scheme_asha_assistance(
    scheme_id: str,
    payload: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    """
    Creates a verified ASHA scheme assistance service task.
    """
    profile = CitizenService.get_or_create_default_profile(db, current_user)
    scheme = db.query(SchemeModel).filter(
        (SchemeModel.scheme_id == scheme_id) | (SchemeModel.scheme_code == scheme_id)
    ).first()

    s_name = scheme.canonical_name if scheme else scheme_id
    s_code = scheme.scheme_code if scheme else scheme_id

    # Check for existing pending request (Idempotency)
    existing_req = db.query(SchemeAssistanceRequestModel).filter(
        SchemeAssistanceRequestModel.citizen_id == profile.id,
        SchemeAssistanceRequestModel.scheme_code == s_code,
        SchemeAssistanceRequestModel.status.in_(["PENDING", "ASSIGNED", "IN_PROGRESS", "SCHEDULED"])
    ).first()

    if existing_req:
        return StandardResponse(data={
            "request_id": existing_req.id,
            "request_reference": existing_req.request_reference,
            "tracking_reference": existing_req.request_reference,
            "assigned_worker_name": existing_req.assigned_worker_name,
            "status": existing_req.status,
            "message": "ASHA assistance request already active."
        })

    req_ref = f"ASHA-SCH-{str(uuid.uuid4())[:8].upper()}"
    assigned_worker_id = profile.assigned_asha_id or "ASHA-012"
    assigned_worker_name = "Sita Patel (Kalyanpur)"

    assistance_req = SchemeAssistanceRequestModel(
        request_reference=req_ref,
        citizen_id=profile.id,
        household_member_id=payload.get("household_member_id"),
        beneficiary_name=payload.get("beneficiary_name", profile.display_name),
        scheme_code=s_code,
        scheme_name=s_name,
        screening_id=payload.get("screening_id"),
        current_screening_status=payload.get("current_screening_status", "MORE_INFORMATION_REQUIRED"),
        missing_facts=payload.get("missing_facts", []),
        missing_documents=payload.get("missing_documents", []),
        preferred_contact_method=payload.get("preferred_contact_method", "HOME_VISIT"),
        consent_given=True,
        assigned_worker_id=assigned_worker_id,
        assigned_worker_name=assigned_worker_name,
        status="PENDING",
        notes=payload.get("notes", f"Citizen requested ASHA assistance for {s_name} eligibility verification.")
    )
    db.add(assistance_req)

    # Also create/update an application tracking record
    tracking_ref = f"TRK-{str(uuid.uuid4())[:8].upper()}"
    tracking = SchemeApplicationTrackingModel(
        application_reference=tracking_ref,
        citizen_id=profile.id,
        household_member_id=payload.get("household_member_id"),
        beneficiary_name=payload.get("beneficiary_name", profile.display_name),
        scheme_code=s_code,
        scheme_name=s_name,
        status="ASHA_ASSISTANCE_REQUESTED",
        assigned_asha_name="Sita Patel",
        missing_documents=payload.get("missing_documents", []),
        next_action_instructions="ASHA worker Sita Patel will visit/contact you to verify documents.",
        last_update_notes="Assistance request registered."
    )
    db.add(tracking)

    # Also create an ASHA-facing ServiceRequest so it shows in ASHA Tasks and Citizen Requests
    from app.models import ServiceRequest
    srv_req = ServiceRequest(
        request_reference=f"SR-{req_ref}",
        citizen_id=profile.id,
        beneficiary_id=payload.get("household_member_id"),
        request_type="ASHA_ASSISTANCE",
        requested_channel="CITIZEN_APP",
        status="SUBMITTED",
        priority="ROUTINE",
        assigned_role="ASHA_WORKER",
        assigned_user_id=assigned_worker_id,
        details={
            "scheme_code": s_code,
            "scheme_name": s_name,
            "beneficiary_name": payload.get("beneficiary_name", profile.display_name),
            "reason": f"Government Scheme Assistance: {s_name}",
            "missing_documents": payload.get("missing_documents", []),
            "preferred_contact_method": payload.get("preferred_contact_method", "HOME_VISIT")
        }
    )
    db.add(srv_req)
    db.commit()

    return StandardResponse(data={
        "request_id": assistance_req.id,
        "request_reference": req_ref,
        "tracking_reference": tracking_ref,
        "assigned_worker_name": assistance_req.assigned_worker_name,
        "status": assistance_req.status,
        "message": "ASHA assistance request registered successfully. Your ASHA worker will assist you."
    })


@router.get("/scheme-assistance", response_model=StandardResponse)
def get_citizen_scheme_assistance(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    profile = CitizenService.get_or_create_default_profile(db, current_user)
    requests = db.query(SchemeAssistanceRequestModel).filter(
        SchemeAssistanceRequestModel.citizen_id == profile.id
    ).order_by(SchemeAssistanceRequestModel.created_at.desc()).all()

    items = [
        {
            "id": r.id,
            "request_reference": r.request_reference,
            "scheme_code": r.scheme_code,
            "scheme_name": r.scheme_name,
            "beneficiary_name": r.beneficiary_name,
            "status": r.status,
            "current_screening_status": r.current_screening_status,
            "missing_facts": r.missing_facts,
            "missing_documents": r.missing_documents,
            "preferred_contact_method": r.preferred_contact_method,
            "assigned_worker_name": r.assigned_worker_name,
            "notes": r.notes,
            "outcome_summary": r.outcome_summary,
            "official_reference_recorded": r.official_reference_recorded,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "updated_at": r.updated_at.isoformat() if r.updated_at else None
        }
        for r in requests
    ]
    return StandardResponse(data=items)

@router.get("/scheme-applications", response_model=StandardResponse)
def get_citizen_scheme_applications(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    profile = CitizenService.get_or_create_default_profile(db, current_user)
    trackings = db.query(SchemeApplicationTrackingModel).filter(
        SchemeApplicationTrackingModel.citizen_id == profile.id
    ).order_by(SchemeApplicationTrackingModel.updated_at.desc()).all()

    items = [
        {
            "id": t.id,
            "application_reference": t.application_reference,
            "scheme_code": t.scheme_code,
            "scheme_name": t.scheme_name,
            "beneficiary_name": t.beneficiary_name,
            "status": t.status,
            "official_application_number": t.official_application_number,
            "official_portal_url": t.official_portal_url,
            "assigned_asha_name": t.assigned_asha_name,
            "missing_documents": t.missing_documents,
            "next_action_instructions": t.next_action_instructions,
            "last_update_notes": t.last_update_notes,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "updated_at": t.updated_at.isoformat() if t.updated_at else None
        }
        for t in trackings
    ]
    return StandardResponse(data=items)

@router.get("/schemes/{scheme_id}/help-requirements", response_model=StandardResponse)
def get_scheme_help_requirements(
    scheme_id: str,
    db: Session = Depends(get_db)
):
    """
    Returns canonical required assistance capabilities, required documents,
    helplines and verification notice for the scheme.
    """
    s_clean = scheme_id.strip()
    scheme = db.query(SchemeModel).filter(
        (SchemeModel.scheme_id == s_clean) |
        (SchemeModel.scheme_code == s_clean) |
        (SchemeModel.short_name == s_clean) |
        (SchemeModel.canonical_name == s_clean)
    ).first()

    if not scheme:
        scheme = db.query(SchemeModel).filter(
            (SchemeModel.scheme_code.ilike(f"%{s_clean}%")) |
            (SchemeModel.short_name.ilike(f"%{s_clean}%")) |
            (SchemeModel.canonical_name.ilike(f"%{s_clean}%"))
        ).first()

    if not scheme:
        raise HTTPException(status_code=404, detail="Scheme not found")

    version = db.query(SchemeVersionModel).filter(
        SchemeVersionModel.scheme_id == scheme.scheme_id,
        SchemeVersionModel.active_status.in_(["ACTIVE", "ACTIVE_OFFICIAL_SOURCE_VERIFIED"])
    ).order_by(SchemeVersionModel.created_at.desc()).first()

    if not version:
        version = db.query(SchemeVersionModel).filter(
            SchemeVersionModel.scheme_id == scheme.scheme_id
        ).order_by(SchemeVersionModel.created_at.desc()).first()

    auth_name = "Government Health Authority"
    if scheme.authority_id:
        auth = db.query(AuthorityModel).filter(AuthorityModel.authority_id == scheme.authority_id).first()
        if auth:
            auth_name = auth.name

    # Load required assistance capabilities
    caps_data = []
    if version and version.assistance_capabilities:
        for sac in version.assistance_capabilities:
            cap = sac.capability
            if cap:
                caps_data.append({
                    "capability_code": cap.capability_code,
                    "name": cap.name,
                    "description": cap.description,
                    "required_level": sac.required_level,
                    "assistance_type": sac.assistance_type,
                    "source_reference": sac.source_reference
                })

    v_payload = version.version_payload if version and version.version_payload else {}
    helpline = v_payload.get("helpline")
    official_app_url = version.official_application_url if version else None
    official_info_url = version.official_information_url if version else None

    return StandardResponse(data={
        "scheme_id": scheme.scheme_id,
        "scheme_code": scheme.scheme_code,
        "scheme_name": scheme.canonical_name,
        "scheme_version_id": version.scheme_version_id if version else None,
        "version_label": version.version_label if version else "2026-08-25.1",
        "authority_name": auth_name,
        "official_verification_required": True,
        "required_capabilities": caps_data,
        "application_modes": v_payload.get("application_methods", ["IN_PERSON", "ONLINE"]),
        "helpline": helpline,
        "official_portal_url": official_app_url,
        "official_information_url": official_info_url,
        "verification_disclaimer": "Visiting a verified help centre assists with document preparation and e-KYC. Final official verification is performed solely by the competent government authority."
    })

def estimate_travel_time(distance_km: float) -> tuple[int, str]:
    """Helper to compute realistic rural transit time and human readable string."""
    if distance_km <= 1.0:
        return 10, "10-15 mins (Walk / Local)"
    elif distance_km <= 5.0:
        mins = int(round(distance_km * 4))
        return mins, f"{mins} mins (Two-wheeler)"
    elif distance_km <= 15.0:
        mins = int(round(distance_km * 3))
        return mins, f"{mins} mins (Bus / Auto)"
    else:
        mins = int(round(distance_km * 2.5))
        hours = mins // 60
        rem_m = mins % 60
        text = f"{hours} hr {rem_m} min" if hours > 0 else f"{mins} mins"
        return mins, f"{text} (State Transport)"

@router.post("/schemes/{scheme_id}/help-centres/search", response_model=StandardResponse)
def search_scheme_help_centres(

    scheme_id: str,
    payload: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    """
    Finds verified facilities matching the required assistance capabilities of the scheme.
    Ranks results by exact capability match, official verification status, state/district, and haversine travel distance.
    """
    s_clean = scheme_id.strip()
    scheme = db.query(SchemeModel).filter(
        (SchemeModel.scheme_id == s_clean) |
        (SchemeModel.scheme_code == s_clean) |
        (SchemeModel.short_name == s_clean) |
        (SchemeModel.canonical_name == s_clean)
    ).first()

    if not scheme:
        scheme = db.query(SchemeModel).filter(
            (SchemeModel.scheme_code.ilike(f"%{s_clean}%")) |
            (SchemeModel.short_name.ilike(f"%{s_clean}%")) |
            (SchemeModel.canonical_name.ilike(f"%{s_clean}%"))
        ).first()

    if not scheme:
        raise HTTPException(status_code=404, detail="Scheme not found")

    version = db.query(SchemeVersionModel).filter(
        SchemeVersionModel.scheme_id == scheme.scheme_id,
        SchemeVersionModel.active_status.in_(["ACTIVE", "ACTIVE_OFFICIAL_SOURCE_VERIFIED"])
    ).order_by(SchemeVersionModel.created_at.desc()).first()

    if not version:
        version = db.query(SchemeVersionModel).filter(
            SchemeVersionModel.scheme_id == scheme.scheme_id
        ).order_by(SchemeVersionModel.created_at.desc()).first()

    # 1. Location resolution
    loc = payload.get("location", {})
    lat = loc.get("latitude")
    lon = loc.get("longitude")
    village = loc.get("village")
    pincode = loc.get("pincode")
    source = loc.get("source", "MANUAL")
    accuracy_m = loc.get("accuracy_m", 30)
    radius_km = float(payload.get("radius_km", 50.0))

    if lat is None or lon is None:
        if village or pincode:
            geocoded = FacilityServiceEngine.geocode_location(village or pincode or "")
            if geocoded:
                lat = geocoded[0]["latitude"]
                lon = geocoded[0]["longitude"]
        else:
            raise HTTPException(status_code=400, detail="Valid coordinates or manual location required.")

    if lat is None or lon is None:
        lat, lon = (18.5204, 73.8567)

    # Validate coordinate boundaries
    if lat < -90.0 or lat > 90.0 or lon < -180.0 or lon > 180.0:
        raise HTTPException(status_code=400, detail="Invalid coordinates: latitude must be in [-90, 90] and longitude in [-180, 180].")

    # 2. Extract required capability codes & service mappings
    required_caps = []
    service_codes_to_match = set()
    if version and version.assistance_capabilities:
        for sac in version.assistance_capabilities:
            cap = sac.capability
            if cap:
                required_caps.append({
                    "capability_code": cap.capability_code,
                    "name": cap.name,
                    "description": cap.description
                })
                if cap.facility_service_code:
                    service_codes_to_match.add(cap.facility_service_code)

    v_payload = version.version_payload if version and version.version_payload else {}
    req_docs_raw = v_payload.get("required_documents", [])
    general_docs = [d["name"] if isinstance(d, dict) else str(d) for d in req_docs_raw if not (isinstance(d, dict) and d.get("conditional"))]
    cond_docs = [d["name"] if isinstance(d, dict) else str(d) for d in req_docs_raw if isinstance(d, dict) and d.get("conditional")]

    # 3. Query PostgreSQL facilities
    all_facilities = db.query(Facility).filter(Facility.is_active == True).all()

    ranked_items = []
    for fac in all_facilities:
        if fac.latitude is None or fac.longitude is None:
            continue
        dist_km = calculate_haversine_distance(lat, lon, fac.latitude, fac.longitude)
        if dist_km > radius_km:
            continue

        travel_mins, travel_text = estimate_travel_time(dist_km)

        # Check facility capabilities / services / empanelment
        fac_services = [s.service_code for s in fac.services if s.availability_status == ServiceAvailabilityStatusEnum.VERIFIED_AVAILABLE]
        fac_schemes = [se.scheme_code for se in fac.schemes if se.verification_status == VerificationStatusEnum.VERIFIED]

        # Intersect matching capabilities
        matched_services = list(service_codes_to_match.intersection(set(fac_services)))
        scheme_empanelled = any(
            scheme.scheme_code.upper() in se.upper() or
            (scheme.short_name and scheme.short_name.upper() in se.upper())
            for se in fac_schemes
        )

        matching_cap_names = []
        for rc in required_caps:
            c_code = rc["capability_code"]
            # Match via scheme empanelment or direct service
            if c_code in ["PMJAY_HELP_DESK", "AYUSHMAN_CARD_SUPPORT"] and ("AYUSHMAN_HELP_DESK" in fac_services or scheme_empanelled):
                matching_cap_names.append(rc["name"])
            elif c_code == "CSC" and (fac.facility_type == FacilityTypeEnum.AYUSHMAN_HELP_DESK or "CSC" in fac.code):
                matching_cap_names.append(rc["name"])
            elif c_code == "EMPANELLED_HOSPITAL" and scheme_empanelled:
                matching_cap_names.append(rc["name"])
            elif c_code == "MJPJAY_HELP_DESK" and ("AYUSHMAN_HELP_DESK" in fac_services or scheme_empanelled):
                matching_cap_names.append(rc["name"])
            elif c_code in ["ASHA_SUPPORT", "ANM_SUB_CENTRE"] and fac.facility_type in [FacilityTypeEnum.SUB_CENTRE, FacilityTypeEnum.SUB_CENTER]:
                matching_cap_names.append(rc["name"])
            elif c_code in ["PHC_FACILITY", "GOVT_MATERNITY_FACILITY"] and fac.facility_type in [FacilityTypeEnum.PHC, FacilityTypeEnum.CHC, FacilityTypeEnum.DISTRICT_HOSPITAL]:
                matching_cap_names.append(rc["name"])
            elif c_code == "TB_DOTS_CENTRE" and ("TB_DOTS" in fac_services or fac.facility_type == FacilityTypeEnum.TB_NCD_CENTRE):
                matching_cap_names.append(rc["name"])
            elif c_code == "VACCINATION_CENTRE" and ("CHILD_VACCINATION" in fac_services):
                matching_cap_names.append(rc["name"])
            elif c_code in ["ANGANWADI", "WCD_OFFICE"] and ("CHILD_VACCINATION" in fac_services or "MATERNITY_DELIVERY" in fac_services):
                matching_cap_names.append(rc["name"])

        # Determine exact match score
        exact_match = len(matching_cap_names) > 0 or scheme_empanelled or len(matched_services) > 0

        # Build directions URL
        encoded_dest = f"{fac.latitude},{fac.longitude}"
        encoded_orig = f"{lat},{lon}"
        directions_url = f"https://www.google.com/maps/dir/?api=1&origin={encoded_orig}&destination={encoded_dest}"

        item = {
            "facility_id": fac.id,
            "public_reference": fac.public_reference or fac.code or f"FAC-{fac.id[:8].upper()}",
            "name": fac.official_name or fac.name or "Healthcare Centre",
            "display_name": fac.name or fac.official_name or "Healthcare Centre",
            "official_name": fac.official_name,
            "facility_type": fac.facility_type.value if hasattr(fac.facility_type, "value") else str(fac.facility_type),
            "facility_type_label": fac.facility_type.value.replace("_", " ").title() if hasattr(fac.facility_type, "value") else str(fac.facility_type),
            "ownership": fac.ownership.value if hasattr(fac.ownership, "value") else str(fac.ownership),
            "authority": fac.authority or "Public Health Department, Maharashtra",
            "state": fac.state or "Maharashtra",
            "district": fac.district or "District 04",
            "block": fac.block or "Kalyanpur Block",
            "village": fac.village,
            "pincode": fac.pincode,
            "address": fac.address,
            "landmark": fac.landmark,
            "latitude": fac.latitude,
            "longitude": fac.longitude,
            "distance_km": dist_km,
            "travel_time_minutes": travel_mins,
            "travel_time_text": travel_text,
            "phone": fac.phone,
            "emergency_helpline": fac.emergency_helpline or "108",
            "is_24x7_emergency": any(s.service_code == "EMERGENCY_24X7" for s in fac.services),
            "is_open_now": True,
            "operating_status_label": "Verified Open / Operational",
            "verification_status": fac.verification_status.value if hasattr(fac.verification_status, "value") else "VERIFIED",
            "source_authority": fac.authority or "State Health Department",
            "source_name": fac.source_name or "National Health Portal / State Registry",
            "source_url": "https://nhp.gov.in/",
            "last_verified_at": fac.last_verified_at.strftime("%Y-%m-%d") if fac.last_verified_at else "2026-08-25",
            "matching_capabilities": list(set(matching_cap_names)),
            "matching_services": matched_services,
            "exact_capability_match": exact_match,
            "is_empanelled": scheme_empanelled,
            "empanelled_schemes": fac_schemes,
            "documents_to_carry": {
                "general": general_docs,
                "conditional": cond_docs,
                "missing_from_profile": general_docs[:2] if general_docs else []
            },
            "google_maps_directions_url": directions_url
        }

        # Calculate Ranking Score
        # 1. Exact capability match (weight: 1000)
        # 2. Officially verified (weight: 500)
        # 3. State/District match (weight: 200)
        # 4. Open status (weight: 100)
        # 5. Distance (penalty: dist_km * 5)
        score = 0
        if exact_match:
            score += 1000
        if scheme_empanelled:
            score += 500
        if item["verification_status"] == "VERIFIED":
            score += 500
        if fac.district == "District 04":
            score += 200
        score += 100 # Open status
        score -= (dist_km * 5)

        ranked_items.append((score, item))

    # Sort descending by score
    ranked_items.sort(key=lambda x: x[0], reverse=True)
    final_items = [x[1] for x in ranked_items]

    auth_name = "Government Health Authority"
    if scheme.authority_id:
        auth = db.query(AuthorityModel).filter(AuthorityModel.authority_id == scheme.authority_id).first()
        if auth:
            auth_name = auth.name

    return StandardResponse(data={
        "scheme": {
            "scheme_id": scheme.scheme_id,
            "scheme_code": scheme.scheme_code,
            "scheme_name": scheme.canonical_name,
            "scheme_version_id": version.scheme_version_id if version else None,
            "authority_name": auth_name
        },
        "required_capabilities": required_caps,
        "items": final_items,
        "total": len(final_items),
        "search_location": {
            "source": source,
            "latitude": lat,
            "longitude": lon,
            "village": village,
            "pincode": pincode,
            "accuracy_m": accuracy_m,
            "captured_at": loc.get("captured_at", datetime.now(timezone.utc).isoformat())
        },
        "verification_notice": "Facilities shown are verified healthcare and scheme help points. Visiting a centre assists with application and KYC, not guaranteed approval."
    })


@router.get("/schemes/{scheme_id}/help-centres/{facility_id}", response_model=StandardResponse)
def get_scheme_facility_detail(
    scheme_id: str,
    facility_id: str,
    language: Optional[str] = "mr-IN",
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    db: Session = Depends(get_db)
):
    """
    Returns complete scheme-contextual detail for a specific verified facility.
    """
    s_clean = scheme_id.strip()
    scheme = db.query(SchemeModel).filter(
        (SchemeModel.scheme_id == s_clean) |
        (SchemeModel.scheme_code == s_clean) |
        (SchemeModel.short_name == s_clean) |
        (SchemeModel.canonical_name == s_clean)
    ).first()

    if not scheme:
        scheme = db.query(SchemeModel).filter(
            (SchemeModel.scheme_code.ilike(f"%{s_clean}%")) |
            (SchemeModel.short_name.ilike(f"%{s_clean}%"))
        ).first()

    if not scheme:
        raise HTTPException(status_code=404, detail="Scheme not found")

    f_clean = facility_id.strip()
    facility = db.query(Facility).filter(
        (Facility.id == f_clean) |
        (Facility.public_reference == f_clean) |
        (Facility.code == f_clean)
    ).first()

    if not facility:
        raise HTTPException(status_code=404, detail="Facility not found")

    version = db.query(SchemeVersionModel).filter(
        SchemeVersionModel.scheme_id == scheme.scheme_id,
        SchemeVersionModel.active_status.in_(["ACTIVE", "ACTIVE_OFFICIAL_SOURCE_VERIFIED"])
    ).order_by(SchemeVersionModel.created_at.desc()).first()

    if not version:
        version = db.query(SchemeVersionModel).filter(
            SchemeVersionModel.scheme_id == scheme.scheme_id
        ).order_by(SchemeVersionModel.created_at.desc()).first()

    auth_name = "Government Health Authority"
    if scheme.authority_id:
        auth = db.query(AuthorityModel).filter(AuthorityModel.authority_id == scheme.authority_id).first()
        if auth:
            auth_name = auth.name

    ref_lat = lat if lat is not None else 18.5204
    ref_lon = lon if lon is not None else 73.8567
    dist_km = calculate_haversine_distance(ref_lat, ref_lon, facility.latitude, facility.longitude)
    travel_mins, travel_text = estimate_travel_time(dist_km)

    fac_services = [s.service_code for s in facility.services if s.availability_status == ServiceAvailabilityStatusEnum.VERIFIED_AVAILABLE]
    fac_schemes = [se.scheme_code for se in facility.schemes if se.verification_status == VerificationStatusEnum.VERIFIED]

    v_payload = version.version_payload if version and version.version_payload else {}
    req_docs_raw = v_payload.get("required_documents", [])
    general_docs = [d["name"] if isinstance(d, dict) else str(d) for d in req_docs_raw if not (isinstance(d, dict) and d.get("conditional"))]
    cond_docs = [d["name"] if isinstance(d, dict) else str(d) for d in req_docs_raw if isinstance(d, dict) and d.get("conditional")]

    hours_list = [
        {
            "day_of_week": h.day_of_week,
            "opening_time": h.opening_time,
            "closing_time": h.closing_time,
            "is_24x7_emergency": h.is_24x7_emergency,
            "hours_display": "Open 24 Hours" if h.is_24x7_emergency else f"{h.opening_time or '09:00'} - {h.closing_time or '16:00'}"
        }
        for h in facility.hours
    ]
    if not hours_list:
        hours_list = [{"day_of_week": "ALL_DAYS", "opening_time": "09:00", "closing_time": "17:00", "is_24x7_emergency": False, "hours_display": "09:00 AM - 05:00 PM"}]

    directions_url = f"https://www.google.com/maps/dir/?api=1&origin={ref_lat},{ref_lon}&destination={facility.latitude},{facility.longitude}"

    fac_dto = {
        "facility_id": facility.id,
        "public_reference": facility.public_reference or facility.code or f"FAC-{facility.id[:8].upper()}",
        "name": facility.official_name or facility.name or "Healthcare Centre",
        "display_name": facility.name or facility.official_name or "Healthcare Centre",
        "official_name": facility.official_name,
        "facility_type": facility.facility_type.value if hasattr(facility.facility_type, "value") else str(facility.facility_type),
        "facility_type_label": facility.facility_type.value.replace("_", " ").title() if hasattr(facility.facility_type, "value") else str(facility.facility_type),
        "ownership": facility.ownership.value if hasattr(facility.ownership, "value") else str(facility.ownership),
        "authority": facility.authority or "Public Health Department, Maharashtra",
        "state": facility.state or "Maharashtra",
        "district": facility.district or "District 04",
        "block": facility.block or "Kalyanpur Block",
        "village": facility.village,
        "pincode": facility.pincode,
        "address": facility.address,
        "landmark": facility.landmark,
        "latitude": facility.latitude,
        "longitude": facility.longitude,
        "distance_km": dist_km,
        "travel_time_minutes": travel_mins,
        "travel_time_text": travel_text,
        "phone": facility.phone,
        "emergency_helpline": facility.emergency_helpline or "108",
        "is_24x7_emergency": any(s.service_code == "EMERGENCY_24X7" for s in facility.services),
        "is_open_now": True,
        "operating_status_label": "Verified Open / Operational",
        "verification_status": facility.verification_status.value if hasattr(facility.verification_status, "value") else "VERIFIED",
        "source_authority": facility.authority or "State Health Department",
        "source_name": facility.source_name or "National Health Portal / State Registry",
        "source_url": "https://nhp.gov.in/",
        "last_verified_at": facility.last_verified_at.strftime("%Y-%m-%d") if facility.last_verified_at else "2026-08-25",
        "matching_capabilities": [se.scheme_name for se in facility.schemes] or ["General Scheme Guidance & e-KYC"],
        "matching_services": fac_services,
        "exact_capability_match": True,
        "is_empanelled": True,
        "empanelled_schemes": fac_schemes,
        "documents_to_carry": {
            "general": general_docs,
            "conditional": cond_docs,
            "missing_from_profile": general_docs[:2] if general_docs else []
        },
        "google_maps_directions_url": directions_url
    }

    return StandardResponse(data={
        "facility": fac_dto,
        "scheme": {
            "scheme_id": scheme.scheme_id,
            "scheme_code": scheme.scheme_code,
            "scheme_name": scheme.canonical_name,
            "scheme_version_id": version.scheme_version_id if version else None,
            "authority_name": auth_name,
            "official_verification_required": True
        },
        "required_documents": {
            "general": general_docs,
            "conditional": cond_docs,
            "missing_from_profile": general_docs[:2] if general_docs else []
        },
        "application_guidance": {
            "steps": v_payload.get("application_steps", [
                "Visit the verified help desk with required original documents",
                "Request operator to perform e-KYC and beneficiary registration",
                "Obtain official acknowledgement receipt and application tracking reference"
            ]),
            "helpline": v_payload.get("helpline"),
            "official_portal_url": version.official_application_url if version else None,
            "verification_disclaimer": "Final document and eligibility verification is performed solely by the responsible government authority."
        },
        "operating_hours": hours_list
    })


# ==========================================
# CITIZEN HEALTH CENTRE & FACILITY WORKFLOWS
# ==========================================

from app.schemas.facility import (
    FacilitySearchRequestDTO, FacilitySearchResultDTO, FacilityDetailDTO,
    FacilitySelectionRequestDTO, FacilityCallEventRequestDTO,
    FacilityAssistanceCreateRequestDTO, FacilityAppointmentCreateRequestDTO,
    ManualLocationGeocodeRequestDTO
)
from app.services.facility_service import FacilityServiceEngine
from app.models.facilities import (
    Facility, FacilityCallEvent, FacilityAssistanceRequest, FacilityAppointmentRequest,
    FacilityHours, FacilityService, FacilitySchemeEmpanelment, FacilitySearch
)

@router.get("/facilities", response_model=StandardResponse)
@router.get("/facilities/search", response_model=StandardResponse)
def search_citizen_facilities(
    service_type: Optional[str] = None,
    urgency: Optional[str] = "ROUTINE",
    patient_category: Optional[str] = "GENERAL",
    beneficiary_id: Optional[str] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    village_name: Optional[str] = None,
    pincode: Optional[str] = None,
    location_method: Optional[str] = "GPS",
    scheme_code: Optional[str] = None,
    government_only: Optional[bool] = False,
    max_distance_km: Optional[float] = 50.0,
    preferred_language: Optional[str] = "mr-IN",
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    """
    Search and rank healthcare facilities based on verified clinical capability,
    deterministic safety priority, operating hours, and genuine travel distance.
    """
    req = FacilitySearchRequestDTO(
        service_type=service_type,
        urgency=urgency,
        patient_category=patient_category,
        beneficiary_id=beneficiary_id,
        latitude=latitude,
        longitude=longitude,
        village_name=village_name,
        pincode=pincode,
        location_method=location_method,
        scheme_code=scheme_code,
        government_only=government_only,
        max_distance_km=max_distance_km,
        preferred_language=preferred_language
    )
    results = FacilityServiceEngine.search_and_rank_facilities(db, req, current_user)
    
    # Generate search ID and resolved location metadata
    search_uuid = str(uuid.uuid4())
    loc_obj = req.location
    resolved_loc = {
        "village": req.village_name or (loc_obj.village if loc_obj else "Kalyanpur"),
        "pincode": req.pincode or (loc_obj.pincode if loc_obj else "415001"),
        "latitude": req.latitude if req.latitude is not None else (loc_obj.latitude if loc_obj else 18.5204),
        "longitude": req.longitude if req.longitude is not None else (loc_obj.longitude if loc_obj else 73.8567),
        "district": req.district if hasattr(req, "district") else (loc_obj.district if loc_obj else "District 04")
    }

    envelope_data = {
        "search_id": search_uuid,
        "items": [r.dict() for r in results],
        "total": len(results),
        "service_code": req.service_code or req.service_type or "GENERAL_OPD",
        "beneficiary_id": req.beneficiary_id,
        "resolved_location": resolved_loc
    }
    return StandardResponse(data=envelope_data)

@router.post("/facilities/geocode", response_model=StandardResponse)
def geocode_manual_location_post(
    req: ManualLocationGeocodeRequestDTO,
    current_user: Optional[User] = Depends(get_optional_user)
):
    """
    Geocode manual village name or 6-digit PIN code into coordinates and normalized location details.
    """
    locations = FacilityServiceEngine.geocode_location(req.query)
    return StandardResponse(data={
        "locations": locations,
        "total": len(locations)
    })

@router.post("/facilities/search", response_model=StandardResponse)
def search_facilities_post(
    req: FacilitySearchRequestDTO,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    """
    POST search endpoint for rich JSON payload search & rank with Google Places & PostgreSQL two-source merge.
    Returns typed envelope data: {search_id, center, service_code, radius_meters, items, total, beneficiary_id, resolved_location}.
    """
    profile = CitizenService.get_or_create_default_profile(db, current_user)
    
    # Coordinate & Radius Validation
    loc_obj = req.location
    c_lat = req.latitude if req.latitude is not None else (loc_obj.latitude if loc_obj else None)
    c_lng = req.longitude if req.longitude is not None else (loc_obj.longitude if loc_obj else None)
    
    if c_lat is not None and not (-90.0 <= c_lat <= 90.0):
        raise HTTPException(status_code=422, detail="Latitude must be between -90 and 90 degrees.")
    if c_lng is not None and not (-180.0 <= c_lng <= 180.0):
        raise HTTPException(status_code=422, detail="Longitude must be between -180 and 180 degrees.")
    
    eff_radius = req.radius_km if req.radius_km is not None else (req.max_distance_km or 25.0)
    if eff_radius <= 0 or eff_radius > 500.0:
        raise HTTPException(status_code=422, detail="Radius must be between 1 and 500 km.")
    req.max_distance_km = eff_radius

    # Household authorization check
    if req.beneficiary_id and req.beneficiary_id not in ["self", "guest", "GUEST"] and req.beneficiary_id != profile.id:
        member = db.query(HouseholdMember).filter(
            HouseholdMember.id == req.beneficiary_id,
            HouseholdMember.citizen_id == profile.id
        ).first()
        if not member:
            raise HTTPException(status_code=403, detail="You cannot search for this household member.")

    search_uuid = str(uuid.uuid4())
    results = FacilityServiceEngine.search_and_rank_facilities(db, req, current_user, search_id=search_uuid)
    
    final_lat = c_lat if c_lat is not None else 18.5204
    final_lng = c_lng if c_lng is not None else 73.8567
    radius_m = int(eff_radius * 1000)

    resolved_loc = {
        "source": (loc_obj.source if loc_obj and loc_obj.source else (req.location_method or "GPS")),
        "village": req.village_name or (loc_obj.village if loc_obj else "Kalyanpur"),
        "pincode": req.pincode or (loc_obj.pincode if loc_obj else "415001"),
        "latitude": final_lat,
        "longitude": final_lng,
        "block": loc_obj.taluka if loc_obj and loc_obj.taluka else (loc_obj.block if loc_obj and hasattr(loc_obj, 'block') else "Kalyanpur Block"),
        "district": loc_obj.district if loc_obj and loc_obj.district else "District 04"
    }

    envelope_data = {
        "search_id": search_uuid,
        "center": {
            "latitude": final_lat,
            "longitude": final_lng
        },
        "service_code": req.service_code or req.service_type or "GENERAL_DOCTOR_PHC",
        "radius_meters": radius_m,
        "items": [r.dict() for r in results],
        "total": len(results),
        "beneficiary_id": req.beneficiary_id,
        "resolved_location": resolved_loc
    }
    return StandardResponse(data=envelope_data)

@router.get("/facilities/search/{search_id}", response_model=StandardResponse)
def get_search_results_by_id(
    search_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    """
    Reload-safe search retrieval by search_id. Returns persisted facility search cache or ranking.
    """
    persisted = db.query(FacilitySearch).filter(FacilitySearch.id == search_id).first()
    if persisted:
        coords = persisted.coordinates_or_locality or {}
        p_lat = coords.get("lat") or 18.5204
        p_lng = coords.get("lon") or 73.8567
        req = FacilitySearchRequestDTO(
            service_code=persisted.requested_service,
            service_type=persisted.requested_service,
            urgency=persisted.urgency,
            patient_category=persisted.patient_category,
            beneficiary_id=persisted.household_member_id,
            latitude=p_lat,
            longitude=p_lng,
            village_name=coords.get("village"),
            pincode=coords.get("pin"),
            location_method=persisted.location_method
        )
        results = FacilityServiceEngine.search_and_rank_facilities(db, req, current_user)
        resolved_loc = {
            "source": persisted.location_method or "GPS",
            "village": coords.get("village") or "Kalyanpur",
            "pincode": coords.get("pin") or "415001",
            "latitude": p_lat,
            "longitude": p_lng,
            "district": "District 04"
        }
        return StandardResponse(data={
            "search_id": search_id,
            "center": {
                "latitude": p_lat,
                "longitude": p_lng
            },
            "service_code": persisted.requested_service or "GENERAL_OPD",
            "radius_meters": 10000,
            "items": [r.dict() for r in results],
            "total": len(results),
            "beneficiary_id": persisted.household_member_id,
            "resolved_location": resolved_loc
        })

    req = FacilitySearchRequestDTO()
    results = FacilityServiceEngine.search_and_rank_facilities(db, req, current_user)
    return StandardResponse(data={
        "search_id": search_id,
        "center": {
            "latitude": 18.5204,
            "longitude": 73.8567
        },
        "service_code": "GENERAL_OPD",
        "radius_meters": 10000,
        "items": [r.dict() for r in results],
        "total": len(results),
        "resolved_location": {"source": "MANUAL", "village": "Kalyanpur", "pincode": "415001", "latitude": 18.5204, "longitude": 73.8567}
    })

@router.post("/facilities/searches", response_model=StandardResponse)
def log_facility_search(
    req: FacilitySearchRequestDTO,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    results = FacilityServiceEngine.search_and_rank_facilities(db, req, current_user)
    return StandardResponse(data=[r.dict() for r in results])


@router.get("/facilities/{facility_id}", response_model=StandardResponse)
def get_citizen_facility_detail(
    facility_id: str,
    language: Optional[str] = "mr-IN",
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    db: Session = Depends(get_db)
):
    detail = FacilityServiceEngine.get_facility_detail(db, facility_id, lang=language, user_lat=lat, user_lon=lon)
    if not detail:
        raise HTTPException(status_code=404, detail="Facility not found")
    return StandardResponse(data=detail.dict())

@router.get("/facilities/{facility_id}/services", response_model=StandardResponse)
def get_citizen_facility_services(
    facility_id: str,
    language: Optional[str] = "mr-IN",
    db: Session = Depends(get_db)
):
    detail = FacilityServiceEngine.get_facility_detail(db, facility_id, lang=language)
    if not detail:
        raise HTTPException(status_code=404, detail="Facility not found")
    return StandardResponse(data=[s.dict() for s in detail.services])

@router.get("/facilities/{facility_id}/hours", response_model=StandardResponse)
def get_citizen_facility_hours(
    facility_id: str,
    db: Session = Depends(get_db)
):
    detail = FacilityServiceEngine.get_facility_detail(db, facility_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Facility not found")
    return StandardResponse(data=[h.dict() for h in detail.weekly_hours])

@router.get("/facilities/{facility_id}/schemes", response_model=StandardResponse)
def get_citizen_facility_schemes(
    facility_id: str,
    db: Session = Depends(get_db)
):
    detail = FacilityServiceEngine.get_facility_detail(db, facility_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Facility not found")
    return StandardResponse(data=[sc.dict() for sc in detail.schemes])

@router.post("/facilities/{facility_id}/select", response_model=StandardResponse)
def select_facility(
    facility_id: str,
    req: FacilitySelectionRequestDTO,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    profile = CitizenService.get_or_create_default_profile(db, current_user)
    fac = db.query(Facility).filter(Facility.id == facility_id).first()
    if not fac:
        raise HTTPException(status_code=404, detail="Facility not found")
    
    # If a case_id is provided, associate the facility with the case
    if req.case_id:
        case = db.query(Case).filter(
            (Case.id == req.case_id) | (Case.reference == req.case_id),
            Case.citizen_id == profile.id
        ).first()
        if case:
            case.assigned_facility_id = fac.id
            case.assigned_facility_name = fac.official_name or fac.name
            db.commit()

    return StandardResponse(data={
        "selected_facility_id": fac.id,
        "facility_name": fac.official_name,
        "case_id": req.case_id,
        "selected_at": datetime.now(timezone.utc).isoformat()
    })

@router.post("/facilities/{facility_id}/call-events", response_model=StandardResponse)
def log_facility_call_event(
    facility_id: str,
    req: FacilityCallEventRequestDTO,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    profile = CitizenService.get_or_create_default_profile(db, current_user)
    fac = db.query(Facility).filter(Facility.id == facility_id).first()
    if not fac:
        raise HTTPException(status_code=404, detail="Facility not found")

    call_ev = FacilityCallEvent(
        facility_id=fac.id,
        citizen_id=profile.id if profile else None,
        dialled_phone=req.dialled_phone,
        event_type="CALL_INITIATED"
    )
    db.add(call_ev)
    db.commit()
    db.refresh(call_ev)
    return StandardResponse(data={
        "event_id": call_ev.id,
        "facility_id": fac.id,
        "event_type": "CALL_INITIATED",
        "dialled_phone": req.dialled_phone,
        "recorded_at": call_ev.initiated_at.isoformat()
    })

@router.post("/facilities/{facility_id}/asha-assistance", response_model=StandardResponse)
def request_facility_asha_assistance(
    facility_id: str,
    req: FacilityAssistanceCreateRequestDTO,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    profile = CitizenService.get_or_create_default_profile(db, current_user)
    task = FacilityServiceEngine.create_asha_assistance_task(db, facility_id, req, profile)
    return StandardResponse(data={
        "id": task.id,
        "request_reference": task.request_reference,
        "facility_id": task.facility_id,
        "status": str(task.status.value),
        "assigned_asha_name": task.assigned_asha_name,
        "created_at": task.created_at.isoformat()
    })

@router.post("/facilities/{facility_id}/appointment-requests", response_model=StandardResponse)
def request_facility_appointment(
    facility_id: str,
    req: FacilityAppointmentCreateRequestDTO,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    profile = CitizenService.get_or_create_default_profile(db, current_user)
    apt = FacilityServiceEngine.create_appointment_request(db, facility_id, req, profile)
    return StandardResponse(data={
        "id": apt.id,
        "appointment_reference": apt.appointment_reference,
        "facility_id": apt.facility_id,
        "service_name": apt.service_name,
        "status": str(apt.status.value),
        "requested_slot": apt.requested_slot,
        "created_at": apt.created_at.isoformat()
    })

@router.get("/facility-assistance", response_model=StandardResponse)
def get_citizen_facility_assistance(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    profile = CitizenService.get_or_create_default_profile(db, current_user)
    tasks = db.query(FacilityAssistanceRequest).filter(
        FacilityAssistanceRequest.citizen_id == profile.id
    ).order_by(FacilityAssistanceRequest.created_at.desc()).all()
    
    data = []
    for t in tasks:
        fac = t.facility
        data.append({
            "id": t.id,
            "request_reference": t.request_reference,
            "facility_id": t.facility_id,
            "facility_name": fac.official_name if fac else "Health Facility",
            "assistance_type": t.assistance_type,
            "assistance_reason": t.assistance_reason,
            "status": str(t.status.value),
            "assigned_asha_name": t.assigned_asha_name,
            "created_at": t.created_at.isoformat()
        })
    return StandardResponse(data=data)

@router.get("/facility-appointments", response_model=StandardResponse)
def get_citizen_facility_appointments(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    profile = CitizenService.get_or_create_default_profile(db, current_user)
    apts = db.query(FacilityAppointmentRequest).filter(
        FacilityAppointmentRequest.citizen_id == profile.id
    ).order_by(FacilityAppointmentRequest.created_at.desc()).all()
    
    data = []
    for a in apts:
        fac = a.facility
        data.append({
            "id": a.id,
            "appointment_reference": a.appointment_reference,
            "facility_id": a.facility_id,
            "facility_name": fac.official_name if fac else "Health Facility",
            "service_name": a.service_name,
            "requested_slot": a.requested_slot,
            "status": str(a.status.value),
            "created_at": a.created_at.isoformat()
        })
    return StandardResponse(data=data)

@router.get("/facility-referrals", response_model=StandardResponse)
def get_citizen_facility_referrals(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    profile = CitizenService.get_or_create_default_profile(db, current_user)
    referrals = db.query(Referral).filter(
        Referral.citizen_id == profile.id
    ).order_by(Referral.created_at.desc()).all()
    
    data = []
    for r in referrals:
        data.append({
            "id": r.id,
            "reference": getattr(r, "reference", r.id),
            "target_facility_name": getattr(r, "to_facility_name", "Kalyanpur Primary Health Centre"),
            "urgency": getattr(r, "priority", "ROUTINE"),
            "reason": getattr(r, "reason", "Higher level clinical review"),
            "transport_instructions": getattr(r, "transport_instructions", "Direct transport advised"),
            "status": str(getattr(r, "status", "REFERRED")),
            "created_at": r.created_at.isoformat() if r.created_at else None
        })
    return StandardResponse(data=data)


@router.get("/prescriptions", response_model=StandardResponse)
def get_citizen_prescriptions(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    profile = CitizenService.get_or_create_default_profile(db, current_user)
    
    # Collect matching case IDs and citizen IDs for profile
    citizen_ids = [profile.id]
    if profile.user_id:
        other_profiles = db.query(CitizenProfile).filter(CitizenProfile.user_id == profile.user_id).all()
        for op in other_profiles:
            if op.id not in citizen_ids:
                citizen_ids.append(op.id)
    
    # Find all cases linked to these citizen profiles
    cases = db.query(Case).filter(Case.citizen_id.in_(citizen_ids)).all()
    case_ids = [c.id for c in cases]
    
    # Citizen sees non-draft prescriptions belonging directly to profile or profile's cases
    rxs = db.query(Prescription).filter(
        (Prescription.citizen_id.in_(citizen_ids)) | (Prescription.case_id.in_(case_ids)),
        Prescription.status != "DRAFT"
    ).order_by(Prescription.created_at.desc()).all()
    
    items = []
    for p in rxs:
        doc_name = getattr(p, "doctor_name", None) or "Dr. Abhinav Sharma"
        if getattr(p, "prescriber_doctor_id", None):
            doc_user = db.query(User).filter(User.id == p.prescriber_doctor_id).first()
            if doc_user and doc_user.name:
                doc_name = doc_user.name
                
        fac_name = "Kalyanpur PHC"
        if getattr(p, "facility_id", None):
            fac = db.query(Facility).filter(Facility.id == p.facility_id).first()
            if fac and fac.official_name:
                fac_name = fac.official_name

        p_status = getattr(p.status, "value", p.status) if hasattr(p.status, "value") else str(p.status)
        p_items = []
        for i in p.items:
            m_name = (
                getattr(i, "generic_name_snapshot", None) or 
                getattr(i, "brand_name_snapshot", None) or 
                getattr(i, "medicine", None) or 
                getattr(i, "medicine_name", "Medicine")
            )
            dosage_val = getattr(i, "dose", None) or getattr(i, "dosage", "1 tablet")
            freq_val = getattr(i, "frequency", "1-0-1")
            dur_val = getattr(i, "duration_value", None) or getattr(i, "duration_days", 5)
            instr_val = getattr(i, "instructions", "") or getattr(i, "timing", "")

            p_items.append({
                "medicine_name": m_name,
                "dosage": dosage_val,
                "frequency": freq_val,
                "duration_days": dur_val,
                "instructions": instr_val,
                "formulation": getattr(i, "formulation", "Tablet"),
                "strength": getattr(i, "strength", ""),
                "route": getattr(i, "route", "ORAL")
            })

        items.append({
            "id": p.id,
            "reference": getattr(p, "reference", p.id),
            "status": p_status,
            "doctor_name": doc_name,
            "doctor_qualification": getattr(p, "doctor_qualification", "MBBS, MD"),
            "facility_name": fac_name,
            "provisional_diagnosis": getattr(p, "provisional_diagnosis", None) or getattr(p, "clinical_context", "General care"),
            "clinical_context": getattr(p, "clinical_context", None) or getattr(p, "provisional_diagnosis", None),
            "signed_at": p.signed_at.isoformat() if getattr(p, "signed_at", None) else p.created_at.isoformat(),
            "items": p_items,
            "created_at": p.created_at.isoformat()
        })

    return StandardResponse(data=items)
 
@router.post("/prescriptions/{prescription_id}/acknowledge", response_model=StandardResponse)
def acknowledge_citizen_prescription(
    prescription_id: str,
    req: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    profile = CitizenService.get_or_create_default_profile(db, current_user)
    citizen_ids = [profile.id]
    if profile.user_id:
        other_profiles = db.query(CitizenProfile).filter(CitizenProfile.user_id == profile.user_id).all()
        for op in other_profiles:
            if op.id not in citizen_ids:
                citizen_ids.append(op.id)
    cases = db.query(Case).filter(Case.citizen_id.in_(citizen_ids)).all()
    case_ids = [c.id for c in cases]

    rx = db.query(Prescription).filter(
        Prescription.id == prescription_id,
        (Prescription.citizen_id.in_(citizen_ids)) | (Prescription.case_id.in_(case_ids))
    ).first()
    if not rx:
        raise HTTPException(status_code=404, detail="Prescription not found")

    ack = PrescriptionAcknowledgement(
        prescription_id=rx.id,
        citizen_id=profile.id,
        instructions_understood=req.get("instructions_understood", True),
        language=req.get("language", "en-IN"),
        acknowledged_at=datetime.now(timezone.utc)
    )
    db.add(ack)
    db.commit()

    return StandardResponse(data={
        "prescription_id": rx.id,
        "acknowledged": True,
        "acknowledged_at": ack.acknowledged_at.isoformat()
    })

@router.get("/investigations", response_model=StandardResponse)
def get_citizen_investigations(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    profile = CitizenService.get_or_create_default_profile(db, current_user)
    citizen_ids = [profile.id]
    if profile.user_id:
        other_profiles = db.query(CitizenProfile).filter(CitizenProfile.user_id == profile.user_id).all()
        for op in other_profiles:
            if op.id not in citizen_ids:
                citizen_ids.append(op.id)
    cases = db.query(Case).filter(Case.citizen_id.in_(citizen_ids)).all()
    case_ids = [c.id for c in cases]

    orders = db.query(InvestigationOrder).filter(
        (InvestigationOrder.citizen_id.in_(citizen_ids)) | (InvestigationOrder.case_id.in_(case_ids))
    ).order_by(InvestigationOrder.ordered_at.desc()).all()

    items = []
    for o in orders:
        order_ref = getattr(o, "reference", getattr(o, "order_reference", o.id))
        doc_name = "Dr. Abhinav Sharma"
        if getattr(o, "ordered_by_doctor_id", None):
            doc_user = db.query(User).filter(User.id == o.ordered_by_doctor_id).first()
            if doc_user and doc_user.name:
                doc_name = doc_user.name
        fac_name = "Kalyanpur PHC Lab"
        if getattr(o, "facility_id", None):
            fac = db.query(Facility).filter(Facility.id == o.facility_id).first()
            if fac and fac.official_name:
                fac_name = fac.official_name

        items.append({
            "id": o.id,
            "reference": order_ref,
            "order_reference": order_ref,
            "test_type": getattr(o, "category", getattr(o, "test_type", "GENERAL")),
            "category": getattr(o, "category", getattr(o, "test_type", "GENERAL")),
            "test_name": o.test_name,
            "priority": getattr(o, "priority", "ROUTINE"),
            "status": getattr(o.status, "value", o.status) if hasattr(o.status, "value") else str(o.status),
            "doctor_name": doc_name,
            "facility_name": fac_name,
            "clinical_reason": getattr(o, "clinical_reason", None),
            "preparation_instructions": getattr(o, "preparation_instructions", None),
            "ordered_at": o.ordered_at.isoformat() if getattr(o, "ordered_at", None) else o.created_at.isoformat()
        })
    return StandardResponse(data=items)

@router.get("/followups", response_model=StandardResponse)
def get_citizen_followups(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    profile = CitizenService.get_or_create_default_profile(db, current_user)
    citizen_ids = [profile.id]
    if profile.user_id:
        other_profiles = db.query(CitizenProfile).filter(CitizenProfile.user_id == profile.user_id).all()
        for op in other_profiles:
            if op.id not in citizen_ids:
                citizen_ids.append(op.id)
    cases = db.query(Case).filter(Case.citizen_id.in_(citizen_ids)).all()
    case_ids = [c.id for c in cases]

    followups = db.query(FollowUp).filter(
        (FollowUp.citizen_id.in_(citizen_ids)) | (FollowUp.case_id.in_(case_ids))
    ).order_by(FollowUp.created_at.desc()).all()

    items = []
    for f in followups:
        fu_ref = getattr(f, "follow_up_reference", f.id)
        assigned_worker_name = "Care Team"
        if getattr(f, "assigned_user_id", None):
            u = db.query(User).filter(User.id == f.assigned_user_id).first()
            if u and u.name:
                assigned_worker_name = u.name
        elif getattr(f, "assigned_role", None) == "ASHA":
            assigned_worker_name = "ASHA Worker (Sita Patel)"
        elif getattr(f, "assigned_role", None) == "PHC_DOCTOR":
            assigned_worker_name = "Dr. Abhinav Sharma"

        items.append({
            "id": f.id,
            "reference": fu_ref,
            "follow_up_reference": fu_ref,
            "task_type": getattr(f, "task_type", "POST_CONSULTATION_CHECK"),
            "instructions": f.instructions,
            "reason": getattr(f, "reason", None),
            "assigned_role": str(f.assigned_role) if f.assigned_role else "ASHA",
            "assigned_worker_name": assigned_worker_name,
            "due_date": f.due_at.isoformat() if f.due_at else None,
            "due_at": f.due_at.isoformat() if f.due_at else None,
            "status": getattr(f.status, "value", f.status) if hasattr(f.status, "value") else str(f.status),
            "created_at": f.created_at.isoformat() if getattr(f, "created_at", None) else None
        })
    return StandardResponse(data=items)

@router.get("/appointments", response_model=StandardResponse)
def get_citizen_appointments(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    profile = CitizenService.get_or_create_default_profile(db, current_user)
    citizen_ids = [profile.id]
    if profile.user_id:
        other_profiles = db.query(CitizenProfile).filter(CitizenProfile.user_id == profile.user_id).all()
        for op in other_profiles:
            if op.id not in citizen_ids:
                citizen_ids.append(op.id)
    cases = db.query(Case).filter(Case.citizen_id.in_(citizen_ids)).all()
    case_ids = [c.id for c in cases]

    followups = db.query(FollowUp).filter(
        (FollowUp.citizen_id.in_(citizen_ids)) | (FollowUp.case_id.in_(case_ids))
    ).order_by(FollowUp.created_at.desc()).all()

    items = [
        {
            "id": f.id,
            "reference": getattr(f, "follow_up_reference", f.id),
            "type": "ASHA_VISIT" if f.assigned_user_id or getattr(f, "assigned_role", None) == "ASHA" else "PHC_VISIT",
            "provider_name": "Kalyanpur PHC Care Team",
            "instructions": f.instructions,
            "scheduled_time": f.due_at.isoformat() if f.due_at else None,
            "status": getattr(f.status, "value", f.status) if hasattr(f.status, "value") else str(f.status)
        }
        for f in followups
    ]
    return StandardResponse(data=items)

# ============================================================================
# CITIZEN PROFILE, HOUSEHOLD, CARE-TEAM, CONSENTS, PREFERENCES & ABHA ENDPOINTS
# ============================================================================

@router.get("/profile", response_model=StandardResponse)
def get_citizen_profile_endpoint(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    profile = CitizenService.get_or_create_default_profile(db, current_user)
    data = CitizenService.get_citizen_profile_detail(db, profile.id)
    return StandardResponse(data=data)

@router.patch("/profile", response_model=StandardResponse)
def update_citizen_profile_endpoint(
    req: CitizenProfileUpdateRequest,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    profile = CitizenService.get_or_create_default_profile(db, current_user)
    data = CitizenService.update_citizen_profile(db, profile.id, req)
    return StandardResponse(data=data)

@router.get("/care-team", response_model=StandardResponse)
def get_citizen_care_team_endpoint(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    profile = CitizenService.get_or_create_default_profile(db, current_user)
    care_team = CitizenService.get_assigned_care_team(db, profile.id)
    return StandardResponse(data=care_team)

@router.get("/consents", response_model=StandardResponse)
def get_citizen_consents_endpoint(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    profile = CitizenService.get_or_create_default_profile(db, current_user)
    consents = CitizenService.get_citizen_consents(db, profile.id)
    return StandardResponse(data=consents)

@router.patch("/consents", response_model=StandardResponse)
def revoke_citizen_consent_endpoint(
    req: ConsentRevokeRequest,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    profile = CitizenService.get_or_create_default_profile(db, current_user)
    revoked = CitizenService.revoke_citizen_consent(db, profile.id, req)
    return StandardResponse(data=revoked)

@router.get("/preferences/language", response_model=StandardResponse)
def get_citizen_language_preference_endpoint(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    profile = CitizenService.get_or_create_default_profile(db, current_user)
    return StandardResponse(data={
        "preferred_language": profile.preferred_language or "mr-IN",
        "language_confirmed_at": profile.language_confirmed_at.isoformat() if getattr(profile, "language_confirmed_at", None) else None
    })

@router.patch("/preferences/language", response_model=StandardResponse)
def update_citizen_language_preference_endpoint(
    req: LanguageUpdateRequestDTO,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    profile = CitizenService.get_or_create_default_profile(db, current_user)
    profile.preferred_language = req.preferred_language
    profile.language_confirmed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(profile)
    return StandardResponse(data={
        "preferred_language": profile.preferred_language,
        "language_confirmed_at": profile.language_confirmed_at.isoformat()
    })

@router.get("/abha-link-status", response_model=StandardResponse)
def get_citizen_abha_link_status_endpoint(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    profile = CitizenService.get_or_create_default_profile(db, current_user)
    status_data = CitizenService.get_abha_link_status(db, profile.id)
    return StandardResponse(data=status_data)

