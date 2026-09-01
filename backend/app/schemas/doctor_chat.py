from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class DoctorChatMessageCreateDTO(BaseModel):
    body: str = Field(..., min_length=1, max_length=4000, description="Message text content")
    client_message_id: str = Field(..., min_length=1, max_length=100, description="Client-generated unique message idempotency ID")
    message_type: Optional[str] = "TEXT"

class DoctorChatMessageReadDTO(BaseModel):
    message_ids: Optional[List[str]] = None
    up_to_message_id: Optional[str] = None

class DoctorChatMessageDTO(BaseModel):
    id: str
    conversation_id: str
    service_request_id: Optional[str] = None
    sender_role: str # CITIZEN, PHC_DOCTOR, SYSTEM
    sender_id: Optional[str] = None
    sender_user_id: Optional[str] = None
    sender_name: Optional[str] = None
    body: str
    client_message_id: str
    status: str # SENDING, SENT, DELIVERED, READ, FAILED
    delivery_status: Optional[str] = "DELIVERED"
    created_at: str
    delivered_at: Optional[str] = None
    read_at: Optional[str] = None
    # Compatibility aliases
    message_text: Optional[str] = None
    sender_type: Optional[str] = None

class DoctorChatThreadDTO(BaseModel):
    id: str
    conversation_id: str
    service_request_id: str
    request_reference: Optional[str] = None
    public_reference: Optional[str] = None
    citizen_id: str
    citizen_name: Optional[str] = None
    beneficiary_id: Optional[str] = None
    beneficiary_name: Optional[str] = None
    doctor_id: Optional[str] = None
    doctor_name: Optional[str] = None
    facility_id: str
    facility_name: Optional[str] = None
    channel: str # DOCTOR_CHAT
    status: str # WAITING_FOR_DOCTOR, DOCTOR_ACCEPTED, IN_CONSULTATION, COMPLETED, CANCELLED
    chief_complaint: Optional[str] = None
    created_at: str
    updated_at: Optional[str] = None
    messages: List[DoctorChatMessageDTO] = []

class DoctorChatThreadEnvelopeDTO(BaseModel):
    thread: DoctorChatThreadDTO
    messages: List[DoctorChatMessageDTO] = []
    request_details: Optional[Dict[str, Any]] = None
