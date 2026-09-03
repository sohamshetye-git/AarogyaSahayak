import logging
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, CitizenProfile, ServiceRequest
from app.dependencies import get_current_user, get_optional_user, require_staff
from app.schemas import StandardResponse
from app.schemas.doctor_chat import (
    DoctorChatMessageCreateDTO, DoctorChatMessageReadDTO,
    DoctorChatMessageDTO, DoctorChatThreadDTO, DoctorChatThreadEnvelopeDTO
)
from app.services.citizen_service import CitizenService
from app.services.doctor_chat_service import DoctorChatService

logger = logging.getLogger("aarogya-doctor-chat")

# Legacy/existing router prefix
router = APIRouter(prefix="/doctor-chat", tags=["Doctor Chat Advice"])

# Canonical routers
canonical_care_conv_router = APIRouter(prefix="/care-conversations", tags=["Care Conversations API"])
canonical_conv_router = APIRouter(prefix="/conversations", tags=["Conversations API"])
canonical_care_req_router = APIRouter(prefix="/care-requests", tags=["Care Requests API"])
canonical_citizen_doc_router = APIRouter(prefix="/citizen/doctor", tags=["Citizen Doctor Requests API"])


def _authorize_conversation_access(
    db: Session,
    conversation_id_or_ref: str,
    current_user: Optional[User],
    profile: Optional[CitizenProfile]
):
    """
    Ensures either:
    1. The authenticated citizen owns the conversation.
    2. An authenticated healthcare staff member (Doctor, ASHA, Admin) is accessing.
    Blocks any unauthorized citizen from accessing another citizen's conversation.
    """
    try:
        thread, srv_req, tele_req = DoctorChatService.resolve_canonical_thread(db, conversation_id_or_ref)
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Doctor consultation request/conversation '{conversation_id_or_ref}' was not found"
        )
    
    # If staff user (Doctor/Admin/ASHA)
    if current_user and current_user.role in ["PHC_DOCTOR", "DISTRICT_ADMIN", "SYSTEM_ADMIN", "ASHA_WORKER"]:
        return thread, srv_req, tele_req, "PHC_DOCTOR"

    citizen_id = srv_req.citizen_id or thread.citizen_id

    # If citizen is logged in with matching profile
    if current_user and current_user.citizen_profile and current_user.citizen_profile.id == citizen_id:
        return thread, srv_req, tele_req, "CITIZEN"

    if current_user and current_user.id == citizen_id:
        return thread, srv_req, tele_req, "CITIZEN"

    # If matching profile header/guest session
    if profile and profile.id == citizen_id:
        return thread, srv_req, tele_req, "CITIZEN"

    # If unauthenticated and no profile available
    if not current_user and not profile:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required to access this consultation conversation"
        )

    # If citizen profile is known and does NOT match, explicitly forbid access
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=f"Forbidden: You do not have permission to access conversation '{conversation_id_or_ref}'"
    )


# -------------------------------------------------------------
# Handler Implementations
# -------------------------------------------------------------

def _get_conversation_thread_handler(
    request_id: str,
    db: Session,
    current_user: Optional[User]
):
    try:
        profile = CitizenService.get_or_create_default_profile(db, current_user)
        thread, srv_req, tele_req, role = _authorize_conversation_access(db, request_id, current_user, profile)
        data = DoctorChatService.get_thread_envelope(db, thread.id, current_user, profile)
        return StandardResponse(data=data)
    except HTTPException:
        raise
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
    except Exception as e:
        logger.error(f"Error fetching conversation thread for '{request_id}': {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to load chat thread")


def _get_messages_handler(
    conversation_id: str,
    after: Optional[str],
    db: Session,
    current_user: Optional[User]
):
    try:
        profile = CitizenService.get_or_create_default_profile(db, current_user)
        thread, _, _, _ = _authorize_conversation_access(db, conversation_id, current_user, profile)
        msgs = DoctorChatService.get_messages(db, thread.id, after=after)
        return StandardResponse(data=msgs)
    except HTTPException:
        raise
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
    except Exception as e:
        logger.error(f"Error fetching messages for '{conversation_id}': {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to fetch chat messages")


def _post_message_handler(
    conversation_id: str,
    dto: DoctorChatMessageCreateDTO,
    db: Session,
    current_user: Optional[User]
):
    try:
        profile = CitizenService.get_or_create_default_profile(db, current_user)
        thread, srv_req, tele_req, detected_role = _authorize_conversation_access(db, conversation_id, current_user, profile)

        from app.services.recent_activity_service import normalize_actor_name
        # Determine sender role & identity
        if current_user and current_user.role in ["PHC_DOCTOR", "DISTRICT_ADMIN", "SYSTEM_ADMIN"]:
            sender_role = "PHC_DOCTOR"
            sender_id = current_user.id
            sender_name = normalize_actor_name(current_user.name, role="PHC_DOCTOR")
        else:
            sender_role = "CITIZEN"
            sender_id = profile.id if profile else (current_user.id if current_user else None)
            sender_name = profile.display_name if profile else "Citizen"

        msg_data = DoctorChatService.post_message(
            db=db,
            conversation_id=thread.id,
            sender_role=sender_role,
            sender_id=sender_id,
            sender_name=sender_name,
            body=dto.body,
            client_message_id=dto.client_message_id,
            message_type=dto.message_type or "TEXT"
        )
        return StandardResponse(data=msg_data)
    except HTTPException:
        raise
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        logger.error(f"Error posting chat message in '{conversation_id}': {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to post chat message")


def _mark_read_handler(
    conversation_id: str,
    dto: DoctorChatMessageReadDTO,
    db: Session,
    current_user: Optional[User]
):
    try:
        profile = CitizenService.get_or_create_default_profile(db, current_user)
        thread, _, _, detected_role = _authorize_conversation_access(db, conversation_id, current_user, profile)

        reader_role = "PHC_DOCTOR" if (current_user and current_user.role == "PHC_DOCTOR") else "CITIZEN"
        reader_id = current_user.id if current_user else (profile.id if profile else None)

        read_count = DoctorChatService.mark_messages_read(
            db=db,
            conversation_id=thread.id,
            reader_role=reader_role,
            reader_id=reader_id,
            up_to_message_id=dto.up_to_message_id,
            message_ids=dto.message_ids
        )
        return StandardResponse(data={"read_count": read_count, "conversation_id": thread.id})
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error marking messages read for '{conversation_id}': {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to mark messages read")


# -------------------------------------------------------------
# 1. Canonical Routes: /care-conversations & /conversations
# -------------------------------------------------------------
@canonical_care_conv_router.get("/{conversation_id}/messages", response_model=StandardResponse)
def get_care_conversation_messages(
    conversation_id: str,
    after: Optional[str] = Query(None, description="ISO timestamp to fetch only messages created after"),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    return _get_messages_handler(conversation_id, after, db, current_user)


@canonical_care_conv_router.post("/{conversation_id}/messages", response_model=StandardResponse)
def post_care_conversation_message(
    conversation_id: str,
    dto: DoctorChatMessageCreateDTO,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    return _post_message_handler(conversation_id, dto, db, current_user)


@canonical_care_conv_router.post("/{conversation_id}/read", response_model=StandardResponse)
def mark_care_conversation_read(
    conversation_id: str,
    dto: DoctorChatMessageReadDTO,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    return _mark_read_handler(conversation_id, dto, db, current_user)


@canonical_conv_router.get("/{conversation_id}/messages", response_model=StandardResponse)
def get_canonical_conversation_messages(
    conversation_id: str,
    after: Optional[str] = Query(None, description="ISO timestamp to fetch only messages created after"),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    return _get_messages_handler(conversation_id, after, db, current_user)


@canonical_conv_router.post("/{conversation_id}/messages", response_model=StandardResponse)
def post_canonical_conversation_message(
    conversation_id: str,
    dto: DoctorChatMessageCreateDTO,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    return _post_message_handler(conversation_id, dto, db, current_user)


@canonical_conv_router.post("/{conversation_id}/read", response_model=StandardResponse)
def mark_canonical_conversation_read(
    conversation_id: str,
    dto: DoctorChatMessageReadDTO,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    return _mark_read_handler(conversation_id, dto, db, current_user)


# -------------------------------------------------------------
# 2. Canonical Routes: /care-requests
# -------------------------------------------------------------
@canonical_care_req_router.get("/{request_id}/conversation", response_model=StandardResponse)
def get_care_request_conversation(
    request_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    return _get_conversation_thread_handler(request_id, db, current_user)


@canonical_care_req_router.get("/{request_id}/messages", response_model=StandardResponse)
def get_care_request_messages(
    request_id: str,
    after: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    return _get_messages_handler(request_id, after, db, current_user)


@canonical_care_req_router.post("/{request_id}/messages", response_model=StandardResponse)
def post_care_request_message(
    request_id: str,
    dto: DoctorChatMessageCreateDTO,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    return _post_message_handler(request_id, dto, db, current_user)


# -------------------------------------------------------------
# 3. Canonical Routes: /citizen/doctor
# -------------------------------------------------------------
@canonical_citizen_doc_router.get("/requests/{request_id}", response_model=StandardResponse)
def get_citizen_doctor_request_detail(
    request_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    return _get_conversation_thread_handler(request_id, db, current_user)


@canonical_citizen_doc_router.get("/requests/{request_id}/conversation", response_model=StandardResponse)
def get_citizen_doctor_request_conversation(
    request_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    return _get_conversation_thread_handler(request_id, db, current_user)


@canonical_citizen_doc_router.get("/requests/{request_id}/messages", response_model=StandardResponse)
def get_citizen_doctor_request_messages(
    request_id: str,
    after: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    return _get_messages_handler(request_id, after, db, current_user)


@canonical_citizen_doc_router.post("/requests/{request_id}/messages", response_model=StandardResponse)
def post_citizen_doctor_request_message(
    request_id: str,
    dto: DoctorChatMessageCreateDTO,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    return _post_message_handler(request_id, dto, db, current_user)


@canonical_citizen_doc_router.post("/requests/{request_id}/read", response_model=StandardResponse)
def mark_citizen_doctor_request_read(
    request_id: str,
    dto: DoctorChatMessageReadDTO,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    return _mark_read_handler(request_id, dto, db, current_user)


# -------------------------------------------------------------
# 4. Aliases: /doctor-chat
# -------------------------------------------------------------
@router.get("/requests/{request_id}/thread", response_model=StandardResponse)
def get_doctor_chat_thread(
    request_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    return _get_conversation_thread_handler(request_id, db, current_user)


@router.get("/conversations/{conversation_id}/messages", response_model=StandardResponse)
def get_doctor_chat_messages(
    conversation_id: str,
    after: Optional[str] = Query(None, description="ISO timestamp to fetch only messages created after"),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    return _get_messages_handler(conversation_id, after, db, current_user)


@router.post("/conversations/{conversation_id}/messages", response_model=StandardResponse)
def post_doctor_chat_message(
    conversation_id: str,
    dto: DoctorChatMessageCreateDTO,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    return _post_message_handler(conversation_id, dto, db, current_user)


@router.post("/conversations/{conversation_id}/read", response_model=StandardResponse)
def mark_doctor_chat_messages_read(
    conversation_id: str,
    dto: DoctorChatMessageReadDTO,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    return _mark_read_handler(conversation_id, dto, db, current_user)

