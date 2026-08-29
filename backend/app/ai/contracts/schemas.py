from typing import List, Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field

class CitizenIntentEnum(str, Enum):
    GREETING = "GREETING"
    THANKS = "THANKS"
    HELP = "HELP"
    CAPABILITIES = "CAPABILITIES"
    GENERAL_CONVERSATION = "GENERAL_CONVERSATION"
    HEALTH_INFORMATION = "HEALTH_INFORMATION"
    NEW_HEALTH_CONCERN = "NEW_HEALTH_CONCERN"
    SYMPTOM_UPDATE = "SYMPTOM_UPDATE"
    ANSWER_TO_QUESTION = "ANSWER_TO_QUESTION"
    FOLLOW_UP_QUESTION = "FOLLOW_UP_QUESTION"
    SELF_CARE_GUIDANCE_REQUEST = "SELF_CARE_GUIDANCE_REQUEST"
    MENTAL_HEALTH_SUPPORT = "MENTAL_HEALTH_SUPPORT"
    MENTAL_HEALTH_CRISIS = "MENTAL_HEALTH_CRISIS"
    DOCTOR_REQUEST = "DOCTOR_REQUEST"
    ASHA_REQUEST = "ASHA_REQUEST"
    FACILITY_SEARCH = "FACILITY_SEARCH"
    SCHEME_INFORMATION = "SCHEME_INFORMATION"
    SCHEME_ELIGIBILITY = "SCHEME_ELIGIBILITY"
    SCHEME_APPLICATION_HELP = "SCHEME_APPLICATION_HELP"
    MEDICINE_INFORMATION = "MEDICINE_INFORMATION"
    MEDICATION_SIDE_EFFECT = "MEDICATION_SIDE_EFFECT"
    VACCINATION_QUERY = "VACCINATION_QUERY"
    MATERNAL_HEALTH_QUERY = "MATERNAL_HEALTH_QUERY"
    CHILD_HEALTH_QUERY = "CHILD_HEALTH_QUERY"
    NCD_QUERY = "NCD_QUERY"
    CASE_STATUS_QUERY = "CASE_STATUS_QUERY"
    PRESCRIPTION_QUERY = "PRESCRIPTION_QUERY"
    INVESTIGATION_QUERY = "INVESTIGATION_QUERY"
    FOLLOWUP_STATUS_QUERY = "FOLLOWUP_STATUS_QUERY"
    EMERGENCY_HELP = "EMERGENCY_HELP"
    CORRECTION = "CORRECTION"
    CONFIRMATION = "CONFIRMATION"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"
    UNCLEAR = "UNCLEAR"

class ContextTransitionEnum(str, Enum):
    NEW_TOPIC = "NEW_TOPIC"
    CONTINUE_CURRENT_TOPIC = "CONTINUE_CURRENT_TOPIC"
    ANSWER_TO_PREVIOUS_QUESTION = "ANSWER_TO_PREVIOUS_QUESTION"
    ANSWER_AND_NEW_FACT = "ANSWER_AND_NEW_FACT"
    CORRECTION = "CORRECTION"
    NEGATION = "NEGATION"
    FOLLOW_UP_QUESTION = "FOLLOW_UP_QUESTION"
    REQUEST_ACTION = "REQUEST_ACTION"
    GENERAL_INFORMATION = "GENERAL_INFORMATION"
    CLOSE_CONVERSATION = "CLOSE_CONVERSATION"
    UNCLEAR = "UNCLEAR"

class CitizenNewFacts(BaseModel):
    person_reference: str = "SELF"
    symptoms: List[str] = Field(default_factory=list)
    body_location: Optional[str] = None
    duration: Optional[str] = None
    severity: Optional[str] = None
    associated_symptoms: List[str] = Field(default_factory=list)
    negated_symptoms: List[str] = Field(default_factory=list)
    temperature_c: Optional[float] = None
    temperature_f: Optional[float] = None
    location: Optional[str] = None
    requested_service: Optional[str] = None

class CitizenUnderstandingOutput(BaseModel):
    intent: CitizenIntentEnum = CitizenIntentEnum.GENERAL_CONVERSATION
    context_transition: ContextTransitionEnum = ContextTransitionEnum.NEW_TOPIC
    detected_language: str = "en"
    citizen_goal: Optional[str] = None
    answer_to_previous_question: Optional[Any] = None
    new_facts: CitizenNewFacts = Field(default_factory=CitizenNewFacts)
    corrections: List[str] = Field(default_factory=list)
    missing_information: List[str] = Field(default_factory=list)
    recommended_response_goal: str = "ACKNOWLEDGE_AND_CLARIFY"
    suggested_follow_up_question: Optional[str] = None
    confidence: float = 0.95

class CitizenDynamicResponseOutput(BaseModel):
    text: str
    language: str = "en"
    response_type: str = "DIRECT_ANSWER" # DIRECT_ANSWER, CLARIFYING_QUESTION, GUIDANCE, ACTION_OFFER, SAFETY_WARNING, CLOSING
    question: Optional[str] = None
    suggested_replies: List[str] = Field(default_factory=list)
    requested_action_types: List[str] = Field(default_factory=list)
    facts_used: List[str] = Field(default_factory=list)
    uncertainty_statement: Optional[str] = None

class NormalizedIntake(BaseModel):
    symptoms: List[str] = Field(description="List of extracted standardized clinical symptoms")
    duration: Optional[str] = Field(default=None, description="Reported duration of symptoms")
    severity_descriptors: List[str] = Field(default_factory=list, description="Descriptive severity qualifiers")
    is_pregnant: bool = Field(default=False, description="Whether patient is currently pregnant")
    gestational_weeks: Optional[int] = Field(default=None, description="Estimated gestational age in weeks")
    uncertain_fields: List[str] = Field(default_factory=list, description="Extracted elements requiring human clarification")
    clarification_questions: List[str] = Field(default_factory=list, description="Suggested questions for ASHA to ask citizen")

class ClinicalEvidenceSummary(BaseModel):
    summary_text: str = Field(description="Evidence-grounded, non-diagnostic synthesis for doctor review")
    key_findings: List[str] = Field(default_factory=list, description="Extracted salient clinical observations")
    guideline_citations: List[str] = Field(default_factory=list, description="Verifiable citation IDs from Milvus RAG")
    safety_notes: List[str] = Field(default_factory=list, description="Highlighted red flags and maternal safety reminders")
    disclaimer: str = Field(
        default="AI-assisted summary for clinical reference only. Diagnosis and prescription must be determined by the treating Medical Officer.",
        description="Mandatory clinical disclaimer"
    )

class SchemeExplanation(BaseModel):
    scheme_code: str
    scheme_name: str
    eligibility_status: str
    explanation: str
    actionable_steps: List[str]
    required_documents: List[str]

class SafetyCritique(BaseModel):
    is_safe: bool = Field(description="Whether the output complies with all medical safety invariants")
    violations: List[str] = Field(default_factory=list, description="Detected safety boundary violations")
    contains_unauthorized_diagnosis: bool = Field(default=False)
    contains_unauthorized_prescription: bool = Field(default=False)
    contains_leaked_pii: bool = Field(default=False)
    has_valid_citations: bool = Field(default=True)
    human_confirmation_mandated: bool = Field(default=True)

class CitizenClarifyingQuestion(BaseModel):
    question_id: str
    text: str
    expected_type: str = "TEXT" # TEXT, TEMPERATURE, YES_NO, SYMPTOM_CHECK

class CitizenProposedFacts(BaseModel):
    symptoms: List[str] = Field(default_factory=list)
    duration: Optional[str] = None
    vitals: Dict[str, Any] = Field(default_factory=dict)

class CitizenTurnAIOutput(BaseModel):
    intent: str
    language: str
    acknowledgement: str
    answer: str
    clarifying_questions: List[CitizenClarifyingQuestion] = Field(default_factory=list)
    suggested_actions: List[str] = Field(default_factory=list)
    proposed_facts: CitizenProposedFacts = Field(default_factory=CitizenProposedFacts)

class AgentExecutionResult(BaseModel):
    execution_id: str
    case_id: Optional[str] = None
    intake: Optional[NormalizedIntake] = None
    evidence_summary: Optional[ClinicalEvidenceSummary] = None
    schemes: List[SchemeExplanation] = Field(default_factory=list)
    critique: SafetyCritique
    provider_mode: str
    orchestrator: str
    latency_ms: float

class HandoffSymptomItem(BaseModel):
    code: str
    display: str
    status: str = "CONFIRMED" # CONFIRMED, NEGATED, UNCERTAIN
    source: str = "CITIZEN_REPORTED" # CITIZEN_REPORTED, AI_EXTRACTED_CITIZEN_CONFIRMED

class HandoffDuration(BaseModel):
    value: Optional[float] = None
    unit: str = "DAYS"
    status: str = "CONFIRMED"

class HandoffRelevantContext(BaseModel):
    age: Optional[int] = None
    gender: Optional[str] = None
    pregnancy_status: Optional[bool] = None
    gestational_weeks: Optional[int] = None
    chronic_conditions: List[str] = Field(default_factory=list)

class HandoffSafety(BaseModel):
    priority: str = "ROUTINE"
    triggered_rule_ids: List[str] = Field(default_factory=list)
    citizen_message: Optional[str] = None
    evaluated_at: str

class HandoffLocation(BaseModel):
    village: Optional[str] = None
    pincode: Optional[str] = None
    landmark: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

class HandoffSharingScope(BaseModel):
    share_structured_summary: bool = True
    share_recent_messages: bool = False
    share_profile: bool = True
    share_location: bool = True
    share_existing_health_records: bool = False

class CareHandoffPacket(BaseModel):
    handoff_id: str
    citizen_id: str
    beneficiary_id: Optional[str] = None
    beneficiary_name: Optional[str] = None
    chat_session_id: Optional[str] = None
    citizen_need_id: Optional[str] = None
    case_id: Optional[str] = None
    request_type: str # DOCTOR_CONSULTATION | ASHA_ASSISTANCE
    requested_channel: str = "CALLBACK" # AUDIO | VIDEO | CHAT | CALLBACK | HOME_VISIT
    preferred_language: str = "mr-IN"
    citizen_summary: str
    chief_concern: str
    symptoms: List[HandoffSymptomItem] = Field(default_factory=list)
    duration: Optional[HandoffDuration] = None
    severity: Optional[str] = None
    vitals: List[Dict[str, Any]] = Field(default_factory=list)
    associated_symptoms: List[str] = Field(default_factory=list)
    negated_symptoms: List[str] = Field(default_factory=list)
    medications_reported: List[str] = Field(default_factory=list)
    allergies_reported: List[str] = Field(default_factory=list)
    relevant_context: HandoffRelevantContext = Field(default_factory=HandoffRelevantContext)
    safety: HandoffSafety
    location: HandoffLocation = Field(default_factory=HandoffLocation)
    citizen_question: Optional[str] = None
    missing_information: List[str] = Field(default_factory=list)
    sharing_scope: HandoffSharingScope = Field(default_factory=HandoffSharingScope)
    consent_id: Optional[str] = None
    created_at: str
    version: int = 1
