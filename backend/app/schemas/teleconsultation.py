from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class TeleconsultationDraftCreateDTO(BaseModel):
    household_member_id: Optional[str] = None
    language_code: str = "mr-IN"
    mode: str = "AUDIO" # AUDIO, VIDEO, CHAT, CALLBACK, SCHEDULED, IN_PERSON_PHC

class TeleconsultationIntakeUpdateDTO(BaseModel):
    chief_complaint: Optional[str] = None
    symptoms: List[str] = []
    duration_text: Optional[str] = None
    severity_level: Optional[str] = None
    progression: Optional[str] = None
    relevant_conditions: List[str] = []
    mode: Optional[str] = None
    language_code: Optional[str] = None
    raw_audio_reference: Optional[str] = None
    raw_audio_deleted: bool = True

class TeleconsultationConsentDTO(BaseModel):
    share_concern: bool = True
    share_medical_history: bool = True
    audio_video_consent: bool = True
    store_transcript_consent: bool = True
    share_location_consent: bool = False

class TeleconsultationSubmitDTO(BaseModel):
    idempotency_key: Optional[str] = None
    consents: Optional[TeleconsultationConsentDTO] = None

class TeleconsultationMessageCreateDTO(BaseModel):
    message_text: Optional[str] = None
    body: Optional[str] = None
    client_message_id: Optional[str] = None
    message_type: str = "TEXT"

class ChatMessageResponseDTO(BaseModel):
    id: str
    conversation_id: Optional[str] = None
    service_request_id: Optional[str] = None
    sender_user_id: Optional[str] = None
    sender_role: str
    sender_name: Optional[str] = None
    message_type: str
    body: str
    client_message_id: Optional[str] = None
    status: str
    created_at: str
    delivered_at: Optional[str] = None
    read_at: Optional[str] = None
    # Backward compatibility
    sender_type: Optional[str] = None
    message_text: Optional[str] = None

class ChatConversationResponseDTO(BaseModel):
    conversation_id: str
    service_request_id: Optional[str] = None
    request_reference: Optional[str] = None
    citizen_id: str
    beneficiary_id: Optional[str] = None
    beneficiary_name: Optional[str] = None
    assigned_doctor_id: Optional[str] = None
    assigned_doctor_name: Optional[str] = None
    facility_id: Optional[str] = "PHC-09"
    status: str
    channel: str
    created_at: str
    closed_at: Optional[str] = None
    messages: List[ChatMessageResponseDTO] = []

class TeleconsultationSymptomsUpdateDTO(BaseModel):
    new_symptoms: List[str]
    notes: Optional[str] = None

class DoctorCompleteTeleconsultationDTO(BaseModel):
    provisional_diagnosis: str
    clinical_summary: Optional[str] = None
    care_plan_summary: Optional[str] = None
    patient_guidance: Optional[str] = None
    disposition: str = "COMPLETED" # COMPLETED, FOLLOW_UP_REQUIRED, REFERRED_TO_PHC, REFERRED_TO_DISTRICT_HOSPITAL
    
    # Prescriptions
    prescriptions: List[Dict[str, Any]] = [] # [{medicine_name, dosage, frequency, duration_days, instructions}]
    
    # Investigations
    investigation_orders: List[Dict[str, Any]] = [] # [{test_name, category, urgency, instructions}]
    
    # ASHA Follow-up Directive
    assign_asha_followup: bool = False
    asha_task_type: str = "POST_CONSULTATION_CHECK"
    asha_due_days: int = 3
    asha_instructions: Optional[str] = None
    asha_escalation_conditions: Optional[str] = None

class DoctorDeclineRequestDTO(BaseModel):
    reason: str

class DoctorRequestInfoDTO(BaseModel):
    questions: List[str]
    notes: Optional[str] = None
