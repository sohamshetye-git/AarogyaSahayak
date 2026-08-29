"""
Aarogya Sahayak - Citizen Conversation Intelligence Engine
Provides multi-turn intent classification, response block planning, versioned facts maintenance,
controlled question management, and deterministic emergency safety evaluation.
"""
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
from pydantic import BaseModel, Field
import re
from datetime import datetime, timezone

from app.models import (
    CitizenChatSession, CitizenChatMessage, CitizenNeed, Case, CasePriorityEnum,
    HouseholdMember, CitizenProfile
)
from app.safety.emergency_rules import EmergencyRuleEvaluator
from app.ai.pii.masker import PIIMasker
from app.ai.providers.gemini_service import gemini_service
from app.ai.contracts.schemas import CitizenIntentEnum


# Alias for backward compatibility
MessagePurposeEnum = CitizenIntentEnum


class UIBlockType(str, Enum):
    TEXT = "TEXT"
    ACKNOWLEDGEMENT = "ACKNOWLEDGEMENT"
    CLARIFYING_QUESTION = "CLARIFYING_QUESTION"
    UNDERSTANDING_CONFIRMATION = "UNDERSTANDING_CONFIRMATION"
    SAFE_GUIDANCE = "SAFE_GUIDANCE"
    SAFETY_ALERT = "SAFETY_ALERT"
    ACTION_CHOICES = "ACTION_CHOICES"
    DOCTOR_REQUEST_CARD = "DOCTOR_REQUEST_CARD"
    ASHA_REQUEST_CARD = "ASHA_REQUEST_CARD"
    FACILITY_RESULTS = "FACILITY_RESULTS"
    SCHEME_RESULTS = "SCHEME_RESULTS"
    MEDICINE_INFORMATION = "MEDICINE_INFORMATION"
    SERVICE_STATUS = "SERVICE_STATUS"
    CARE_SUMMARY = "CARE_SUMMARY"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"


class ActionChoice(BaseModel):
    action: str
    label: str
    style: Optional[str] = "PRIMARY" # PRIMARY, SECONDARY, DANGER, OUTLINE
    type: Optional[str] = None # For frontend backward compatibility


class UIBlock(BaseModel):
    type: UIBlockType
    block_type: Optional[str] = None # For compatibility
    title: Optional[str] = None
    content: Optional[str] = None
    text: Optional[str] = None
    question_id: Optional[str] = None
    expected_answer: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    actions: Optional[List[Dict[str, Any]]] = None

    def model_post_init(self, __context: Any) -> None:
        if not self.block_type:
            self.block_type = self.type.value


class SafetyEvaluationResult(BaseModel):
    level: str = "INSUFFICIENT_INFORMATION" # EMERGENCY, URGENT, PRIORITY, ROUTINE, INSUFFICIENT_INFORMATION
    triggered_rule_ids: List[str] = []
    reason: Optional[str] = None
    guidance: Optional[str] = None


class ChatTurnResponse(BaseModel):
    session_id: str
    message_id: str
    purpose: CitizenIntentEnum
    language: str = "mr-IN"
    text: str
    read_aloud_text: Optional[str] = None
    blocks: List[UIBlock]
    safety: SafetyEvaluationResult
    active_need_id: Optional[str] = None
    case_id: Optional[str] = None
    need_version: int = 1
    state: Optional[str] = None
    understanding: Optional[Dict[str, Any]] = None
    actions: Optional[List[Dict[str, Any]]] = None


class ClassificationResult(BaseModel):
    purpose: CitizenIntentEnum
    extracted_symptoms: List[str] = []
    duration: Optional[str] = None
    temperature_f: Optional[float] = None
    temperature_c: Optional[float] = None
    answered_question_id: Optional[str] = None
    is_emergency: bool = False
    confidence: float = 1.0


class QuestionManager:
    """
    Manages controlled clinical clarification questions one at a time.
    Tracks question IDs, expected answer types, and validates answers.
    """

    FEVER_QUESTIONS = [
        {
            "id": "fever_temperature",
            "expected_type": "TEMPERATURE",
            "text": {
                "mr": "कृपया सांगा: आपण तापमापीने (थर्मामीटर) शरीराचे तापमान मोजले आहे का? किती तापमान आहे?",
                "hi": "कृपया बताएं: क्या आपने थर्मामीटर से तापमान मापा है? तापमान कितना है?",
                "en": "What is your measured body temperature, if checked with a thermometer?"
            },
            "quick_options": [
                {"label": "100°F - 101°F", "value": "101°F"},
                {"label": "102°F - 103°F", "value": "103°F"},
                {"label": "Not measured", "value": "Not measured"}
            ]
        },
        {
            "id": "fever_breathing",
            "expected_type": "YES_NO",
            "text": {
                "mr": "तुम्हाला श्वास घेण्यास काही त्रास किंवा धाप लागत आहे का?",
                "hi": "क्या आपको सांस लेने में कोई तकलीफ या भारीपन महसूस हो रहा है?",
                "en": "Are you experiencing any difficulty breathing or shortness of breath?"
            },
            "quick_options": [
                {"label": "No breathing difficulty", "value": "No"},
                {"label": "Yes, having difficulty", "value": "Yes, having difficulty breathing"}
            ]
        },
        {
            "id": "fever_fluid_intake",
            "expected_type": "YES_NO",
            "text": {
                "mr": "आपण पाणी किंवा पातळ पदार्थ सहज पिऊ शकत आहात का? सतत उलट्या होत आहेत का?",
                "hi": "क्या आप पानी या तरल पदार्थ ठीक से पी पा रहे हैं? क्या बार-बार उल्टी हो रही है?",
                "en": "Are you able to drink fluids, or experiencing repeated vomiting?"
            },
            "quick_options": [
                {"label": "Can drink fluids well", "value": "Can drink water"},
                {"label": "Cannot drink / vomiting", "value": "Cannot drink / vomiting"}
            ]
        }
    ]

    MATERNAL_QUESTIONS = [
        {
            "id": "maternal_bp_headache",
            "expected_type": "SYMPTOM_CHECK",
            "text": {
                "mr": "गरोदरपणात तीव्र डोकेदुखी, डोळ्यासमोर अंधारी येणे किंवा पायांवर सूज आहे का?",
                "hi": "गर्भावस्था में तेज सिरदर्द, आंखों के आगे धुंधलापन या पैरों में सूजन है क्या?",
                "en": "Are you having severe headache, blurred vision, or swelling in feet/face?"
            }
        },
        {
            "id": "maternal_fetal_movement",
            "expected_type": "YES_NO",
            "text": {
                "mr": "बाळाची हालचाल नेहमीप्रमाणे जाणवत आहे का?",
                "hi": "क्या शिशु की हलचल सामान्य रूप से महसूस हो रही है?",
                "en": "Are you feeling the baby's movements normally?"
            }
        }
    ]

    @classmethod
    def get_next_question(
        cls,
        session: CitizenChatSession,
        symptoms: List[str],
        is_pregnant: bool = False,
        answered_ids: List[str] = []
    ) -> Optional[Dict[str, Any]]:
        """
        Determines the next single priority question to ask.
        """
        question_pool = []
        if is_pregnant:
            question_pool.extend(cls.MATERNAL_QUESTIONS)
        
        # Check fever context
        if any("fever" in s.lower() or "ताप" in s.lower() or "बुखार" in s.lower() for s in symptoms):
            question_pool.extend(cls.FEVER_QUESTIONS)

        for q in question_pool:
            if q["id"] not in answered_ids:
                return q
        return None

    @classmethod
    def parse_temperature_answer(cls, text: str) -> Optional[Tuple[float, str]]:
        """
        Extracts and normalizes temperature value and unit (F or C).
        """
        t = text.lower().strip()
        
        # Explicit Celsius match: 38.5 C / 39 डिग्री सेल्सिअस
        c_match = re.search(r"(\d{2}(?:\.\d)?)\s*(?:c|°c|celsius|सेल्सिअस)", t)
        if c_match:
            try:
                val = float(c_match.group(1))
                if 35.0 <= val <= 43.0:
                    f_val = round((val * 9 / 5) + 32, 1)
                    return f_val, "C"
            except ValueError:
                pass

        # Fahrenheit match or naked number: 103, 102.5, 99.8 F, 103 डिग्री
        f_match = re.search(r"(\d{2,3}(?:\.\d)?)\s*(?:f|°f|fahrenheit|डिग्री|फैरेनहाइट)?", t)
        if f_match:
            try:
                val = float(f_match.group(1))
                if 95.0 <= val <= 108.0:
                    return val, "F"
                elif 36.0 <= val <= 42.0: # Likely Celsius given without unit
                    f_val = round((val * 9 / 5) + 32, 1)
                    return f_val, "C"
            except ValueError:
                pass

        return None


class ConversationEngine:
    """
    Stateful conversational orchestrator for Citizen Health Assistant.
    """

    @staticmethod
    def build_dynamic_actions(intent: CitizenIntentEnum, lang: str = "mr-IN") -> List[Dict[str, Any]]:
        """
        Constructs authorized, dynamic action buttons based on strict intent and citizen requirements.
        FastAPI is the sole authority for constructing these actions.
        """
        is_hi = lang.startswith("hi")
        is_en = lang.startswith("en")

        if intent == CitizenIntentEnum.EMERGENCY_HELP or intent == CitizenIntentEnum.MENTAL_HEALTH_CRISIS:
            return [
                {
                    "type": "EMERGENCY_HELP",
                    "action": "CALL_108",
                    "label": "108 पर कॉल करें (Call 108)" if is_hi else ("Call 108 Emergency" if is_en else "१०८ रुग्णवाहिका कॉल करा"),
                    "style": "DANGER"
                },
                {
                    "type": "SPEAK_TO_DOCTOR",
                    "action": "SPEAK_TO_DOCTOR",
                    "label": "डॉक्टर से तुरंत बात करें" if is_hi else ("Speak to Doctor Now" if is_en else "डॉक्टरांशी तातडीने बोला"),
                    "style": "PRIMARY"
                },
                {
                    "type": "FIND_FACILITY",
                    "action": "FIND_FACILITY",
                    "label": "आपातकालीन केंद्र खोजें" if is_hi else ("Find Emergency Facility" if is_en else "२४x७ आपत्कालीन केंद्र शोधा"),
                    "style": "SECONDARY"
                }
            ]

        if intent == CitizenIntentEnum.MENTAL_HEALTH_SUPPORT:
            return [
                {
                    "type": "SPEAK_TO_DOCTOR",
                    "action": "SPEAK_TO_DOCTOR",
                    "label": "परामर्शदाता / डॉक्टर से बात करें" if is_hi else ("Speak with Counselor / Doctor" if is_en else "डॉक्टर / समुपदेशकांशी बोला"),
                    "style": "PRIMARY"
                },
                {
                    "type": "REQUEST_ASHA",
                    "action": "REQUEST_ASHA",
                    "label": "आशा कार्यकर्ता सहायता" if is_hi else ("Request ASHA Support" if is_en else "आशा ताईंची मदत घ्या"),
                    "style": "SECONDARY"
                }
            ]

        if intent == CitizenIntentEnum.GREETING or intent == CitizenIntentEnum.HELP or intent == CitizenIntentEnum.CAPABILITIES:
            return [
                {
                    "type": "HEALTH_HELP",
                    "action": "HEALTH_HELP",
                    "label": "स्वास्थ्य समस्या बताएं" if is_hi else ("Health Help & Guidance" if is_en else "आरोग्य मार्गदर्शन मिळवा"),
                    "style": "PRIMARY"
                },
                {
                    "type": "SPEAK_TO_DOCTOR",
                    "action": "SPEAK_TO_DOCTOR",
                    "label": "डॉक्टर परामर्श" if is_hi else ("Speak to Doctor" if is_en else "डॉक्टरांशी बोला"),
                    "style": "SECONDARY"
                },
                {
                    "type": "FIND_FACILITY",
                    "action": "FIND_FACILITY",
                    "label": "स्वास्थ्य केंद्र खोजें" if is_hi else ("Find Health Centre" if is_en else "जवळचे आरोग्य केंद्र"),
                    "style": "OUTLINE"
                },
                {
                    "type": "CHECK_SCHEMES",
                    "action": "CHECK_SCHEMES",
                    "label": "सरकारी योजनाएं" if is_hi else ("Govt Health Benefits" if is_en else "शासकीय योजना"),
                    "style": "OUTLINE"
                }
            ]

        if intent == CitizenIntentEnum.DOCTOR_REQUEST:
            return [
                {
                    "type": "SPEAK_TO_DOCTOR",
                    "action": "SPEAK_TO_DOCTOR",
                    "label": "डॉक्टर से जुड़ें" if is_hi else ("Connect to Doctor" if is_en else "डॉक्टरांशी जोडा"),
                    "style": "PRIMARY"
                },
                {
                    "type": "REQUEST_ASHA",
                    "action": "REQUEST_ASHA",
                    "label": "आशा दीदी से मिलें" if is_hi else ("Request ASHA Visit" if is_en else "आशा ताईंची भेट"),
                    "style": "OUTLINE"
                }
            ]

        if intent == CitizenIntentEnum.ASHA_REQUEST:
            return [
                {
                    "type": "REQUEST_ASHA",
                    "action": "REQUEST_ASHA",
                    "label": "आशा गृह भेंट अनुरोध" if is_hi else ("Request ASHA Home Visit" if is_en else "आशा ताईंना गृहभेटीचा अनुरोध"),
                    "style": "PRIMARY"
                },
                {
                    "type": "CALL_ASHA",
                    "action": "CALL_ASHA",
                    "label": "आशा कार्यकर्ता को कॉल करें" if is_hi else ("Call Assigned ASHA" if is_en else "आशा ताईंना कॉल करा"),
                    "style": "SECONDARY"
                }
            ]

        if intent == CitizenIntentEnum.FACILITY_SEARCH or intent == CitizenIntentEnum.MATERNAL_HEALTH_QUERY:
            return [
                {
                    "type": "FIND_FACILITY",
                    "action": "FIND_FACILITY",
                    "label": "नजदीकी केंद्र देखें" if is_hi else ("Find Suitable Health Centre" if is_en else "योग्य आरोग्य केंद्र शोधा"),
                    "style": "PRIMARY"
                },
                {
                    "type": "REQUEST_ASHA",
                    "action": "REQUEST_ASHA",
                    "label": "आशा सहायता" if is_hi else ("Request ASHA Assistance" if is_en else "आशा ताईंची मदत"),
                    "style": "OUTLINE"
                }
            ]

        if intent in [CitizenIntentEnum.SCHEME_INFORMATION, CitizenIntentEnum.SCHEME_ELIGIBILITY, CitizenIntentEnum.SCHEME_APPLICATION_HELP]:
            return [
                {
                    "type": "CHECK_SCHEMES",
                    "action": "CHECK_SCHEMES",
                    "label": "पात्रता जांचें (Check Eligibility)" if is_hi else ("Check Scheme Eligibility" if is_en else "योजना पात्रता तपासा"),
                    "style": "PRIMARY"
                },
                {
                    "type": "VIEW_DOCUMENTS",
                    "action": "VIEW_DOCUMENTS",
                    "label": "जरूरी दस्तावेज देखें" if is_hi else ("View Required Documents" if is_en else "आवश्यक कागदपत्रे पहा"),
                    "style": "SECONDARY"
                }
            ]

        if intent in [CitizenIntentEnum.CASE_STATUS_QUERY, CitizenIntentEnum.FOLLOWUP_STATUS_QUERY, CitizenIntentEnum.PRESCRIPTION_QUERY, CitizenIntentEnum.INVESTIGATION_QUERY]:
            return [
                {
                    "type": "VIEW_CARE_RECORD",
                    "action": "VIEW_CARE_RECORD",
                    "label": "मेरी देखभाल विवरण खोलें" if is_hi else ("Open My Care Record" if is_en else "माझे उपचार रेकॉर्ड उघडा"),
                    "style": "PRIMARY"
                },
                {
                    "type": "SPEAK_TO_DOCTOR",
                    "action": "SPEAK_TO_DOCTOR",
                    "label": "फॉलो-अप डॉक्टर से बात करें" if is_hi else ("Consult Doctor" if is_en else "डॉक्टरांशी बोला"),
                    "style": "OUTLINE"
                }
            ]

        if intent in [CitizenIntentEnum.NEW_HEALTH_CONCERN, CitizenIntentEnum.SYMPTOM_UPDATE, CitizenIntentEnum.SELF_CARE_GUIDANCE_REQUEST, CitizenIntentEnum.ANSWER_TO_QUESTION, CitizenIntentEnum.FOLLOW_UP_QUESTION]:
            return [
                {
                    "type": "SPEAK_TO_DOCTOR",
                    "action": "SPEAK_TO_DOCTOR",
                    "label": "डॉक्टर से सलाह लें" if is_hi else ("Speak to Doctor" if is_en else "डॉक्टरांचा सल्ला घ्या"),
                    "style": "PRIMARY"
                },
                {
                    "type": "REQUEST_ASHA",
                    "action": "REQUEST_ASHA",
                    "label": "आशा ताईंची भेट" if not is_hi and not is_en else ("आशा गृह भेंट" if is_hi else "Request ASHA Visit"),
                    "style": "SECONDARY"
                },
                {
                    "type": "FIND_FACILITY",
                    "action": "FIND_FACILITY",
                    "label": "स्वास्थ्य केंद्र खोजें" if is_hi else ("Find Health Centre" if is_en else "आरोग्य केंद्र शोधा"),
                    "style": "OUTLINE"
                }
            ]

        # For THANKS, OUT_OF_SCOPE, UNCLEAR: no forced clinical action array
        return []

    @staticmethod
    def classify_intent_deterministic(text: str, session: CitizenChatSession) -> Optional[ClassificationResult]:
        t = text.lower().strip()

        # 1. Immediate Safety Overrides: Mental Health Crisis & 108 Emergency
        if any(w in t for w in ["hurt myself", "kill myself", "suicide", "आत्महत्या", "स्वतःला संपवणे", "खुद को मारना", "खुद को नुकसान"]):
            return ClassificationResult(purpose=CitizenIntentEnum.MENTAL_HEALTH_CRISIS, is_emergency=True)
        if any(w in t for w in ["108", "emergency", "रुग्णवाहिका", "आपातकालीन", "ambulance", "heart attack", "हार्ट अटॅक", "severe breathlessness", "unconscious", "seizure", "heavy bleeding", "छातीत तीव्र", "श्वास घेण्यास", "सांस लेने में", "difficulty breathing", "shortness of breath", "chest pain", "छातीत दुखत"]):
            return ClassificationResult(purpose=CitizenIntentEnum.EMERGENCY_HELP, is_emergency=True)

        # 2. Out of scope / Unrelated queries (Check early before generic question words)
        if any(w in t for w in ["cricket", "match", "movie", "cinema", "politics", "हवामान", "चित्रपट", "गाणी", "राजकारण", "who won", "score"]):
            return ClassificationResult(purpose=CitizenIntentEnum.OUT_OF_SCOPE)

        # 3. Capabilities / Bot Help / Greetings / Gratitude
        if any(w in t for w in ["what can you do", "capabilities", "तू काय करू शकतोस", "तू काय करू शकतेस", "तुम क्या कर सकते हो", "तुझी माहिती"]):
            return ClassificationResult(purpose=CitizenIntentEnum.CAPABILITIES)
        if any(w in t for w in ["thank", "thanks", "धन्यवाद", "आभार", "शुक्रिया"]):
            return ClassificationResult(purpose=CitizenIntentEnum.THANKS)
        if t in ["hello", "hi", "namaskar", "नमस्कार", "नमस्ते", "हाय", "good morning", "good evening", "hey", "halo", "helloo"]:
            return ClassificationResult(purpose=CitizenIntentEnum.GREETING)

        # 4. Mental Health Support
        if any(w in t for w in ["anxious", "anxiety", "depressed", "depression", "feeling low", "चिंता", "तणाव", "घबराहट", "उदासीन", "भीती"]) and not any(w in t for w in ["hurt myself", "suicide", "kill"]):
            return ClassificationResult(purpose=CitizenIntentEnum.MENTAL_HEALTH_SUPPORT)

        # 5. Direct Doctor Request
        if any(w in t for w in ["speak to doctor", "consult doctor", "doctor consultation", "want a doctor", "need a doctor", "डॉक्टर", "doctor", "डॉक्टरांशी", "वैद्य", "appointment", "teleconsultation"]):
            return ClassificationResult(purpose=CitizenIntentEnum.DOCTOR_REQUEST)

        # 6. Direct ASHA Request
        if any(w in t for w in ["asha", "आशा ताई", "आशा", "home visit", "आशा दीदी", "tai", "asha worker", "आशा भेट"]):
            return ClassificationResult(purpose=CitizenIntentEnum.ASHA_REQUEST)

        # 7. Facility Search (including Maternity)
        if any(w in t for w in ["hospital", "phc", "chc", "maternity", "दवाखाना", "रुग्णालय", "क्लिनिक", "center", "centre", "dispensary", "प्रसूती रुग्णालय", "प्रसूती केंद्र"]):
            return ClassificationResult(purpose=CitizenIntentEnum.FACILITY_SEARCH)

        # 8. Scheme Queries (Eligibility vs General Info)
        if any(w in t for w in ["can i get", "eligible", "पात्रता", "पात्र आहे का", "पात्रता काय", "योजना मिळेल का", "ayushman bharat", "pmjay", "योजनेचा लाभ", "ayushman"]):
            return ClassificationResult(purpose=CitizenIntentEnum.SCHEME_ELIGIBILITY)
        if any(w in t for w in ["scheme", "yojana", "योजना", "लाभ", "आरोग्य योजना", "matritva vandana"]):
            return ClassificationResult(purpose=CitizenIntentEnum.SCHEME_INFORMATION)

        # 9. Health Programs & Care Status
        if any(w in t for w in ["vaccin", "लसीकरण", "लस", "टीकाकरण", "polio", "bcg"]):
            return ClassificationResult(purpose=CitizenIntentEnum.VACCINATION_QUERY)
        if any(w in t for w in ["pregnant", "pregnancy", "गरोदर", "गर्भवती", "प्रसूती", "anc", "delivery"]):
            return ClassificationResult(purpose=CitizenIntentEnum.MATERNAL_HEALTH_QUERY)
        if any(w in t for w in ["when is my follow-up", "follow-up", "followup", "पुढील भेट", "अपॉइंटमेंट", "फॉलो-अप"]):
            return ClassificationResult(purpose=CitizenIntentEnum.FOLLOWUP_STATUS_QUERY)
        if any(w in t for w in ["prescription", "औषधे", "गोळ्या", "दवा पर्ची"]):
            return ClassificationResult(purpose=CitizenIntentEnum.PRESCRIPTION_QUERY)

        # 10. Guidance / What should I do queries
        if any(w in t for w in ["what should i do", "what to do", "what can i do", "how to reduce", "give suggestion", "give suggestions", "what should", "what do i do", "काय करावे", "काय करू", "उपाय", "क्या करूं", "घरेलू उपाय", "remedy", "guidance", "care", "reduce fever", "ताप कमी", "advice", "what to do now"]):
            return ClassificationResult(purpose=CitizenIntentEnum.SELF_CARE_GUIDANCE_REQUEST)

        # 11. Vital Measurement & Question Answering
        parsed_temp = QuestionManager.parse_temperature_answer(t)
        if parsed_temp:
            return ClassificationResult(
                purpose=CitizenIntentEnum.ANSWER_TO_QUESTION,
                temperature_f=parsed_temp[0],
                answered_question_id=session.current_question_id or "Q_TEMP_CHECK"
            )

        tokens = set(t.split())
        if session.awaiting_answer and session.current_question_id:
            if any(w in t for w in ["not measured", "मोजला नाही", "नाही मोजला", "not yet"]) or tokens.intersection({"no", "नाही", "nahi"}):
                return ClassificationResult(
                    purpose=CitizenIntentEnum.ANSWER_TO_QUESTION,
                    answered_question_id=session.current_question_id
                )
            if any(w in t for w in ["yes i do", "yes i have", "होय आहे"]) or tokens.intersection({"yes", "होय", "हो", "आहे", "ho", "haa", "ha"}):
                return ClassificationResult(
                    purpose=CitizenIntentEnum.ANSWER_TO_QUESTION,
                    answered_question_id=session.current_question_id
                )

        # 12. Symptom Updates (if active need exists)
        if session.linked_need_id:
            if any(w in t for w in ["cold", "खोकला", "सर्दी", "cough", "headache", "डोकेदुखी", "pain", "दुखत", "कमजोरी", "weakness", "now", "आता", "अब", "अजून", "also", "तसेच", "भी"]):
                return ClassificationResult(purpose=CitizenIntentEnum.SYMPTOM_UPDATE)

        # 13. Questions with question marks
        if "?" in t or any(w in t for w in ["what", "how", "why", "when", "का", "कधी", "कसे", "क्या", "कब", "कैसे", "should i", "can i"]):
            return ClassificationResult(purpose=CitizenIntentEnum.SELF_CARE_GUIDANCE_REQUEST)

        # 14. Initial Health Concern
        if any(w in t for w in ["fever", "ताप", "बुखार", "pain", "दुखत", "दर्द", "weakness", "अशक्तपणा", "headache", "डोकेदुखी", "उल्टी", "vomiting", "cough", "खोकला", "cold", "sore throat", "चक्कर", "दोन दिवस", "त्रास"]):
            return ClassificationResult(purpose=CitizenIntentEnum.NEW_HEALTH_CONCERN)

        return None

    @staticmethod
    def classify_with_gemini(text: str, session: CitizenChatSession) -> ClassificationResult:
        # First check deterministic rules
        det = ConversationEngine.classify_intent_deterministic(text, session)
        if det:
            return det

        # If live Gemini is active, use GenAI for structured NLU classification
        if gemini_service.is_live:
            try:
                masked_text, _ = PIIMasker.mask_text(text)
                res = gemini_service.generate_citizen_turn(
                    message=masked_text,
                    language=session.preferred_language or "mr-IN",
                    context={},
                    recent_turns=[]
                )
                if res and "output" in res and res["output"]:
                    out = res["output"]
                    intent_str = out.intent
                    intent_val = CitizenIntentEnum.SELF_CARE_GUIDANCE_REQUEST
                    for mem in CitizenIntentEnum:
                        if mem.value == intent_str:
                            intent_val = mem
                            break

                    return ClassificationResult(
                        purpose=intent_val,
                        extracted_symptoms=out.proposed_facts.symptoms or [],
                        duration=out.proposed_facts.duration
                    )
            except Exception as e:
                pass

        # Fallback heuristic
        lowered = text.lower()
        if "?" in text or any(w in lowered for w in ["what", "how", "काय", "क्या"]):
            return ClassificationResult(purpose=CitizenIntentEnum.SELF_CARE_GUIDANCE_REQUEST)
        if session.awaiting_answer:
            return ClassificationResult(purpose=CitizenIntentEnum.ANSWER_TO_QUESTION, answered_question_id=session.current_question_id)
        if session.linked_need_id:
            return ClassificationResult(purpose=CitizenIntentEnum.FOLLOW_UP_QUESTION)
        return ClassificationResult(purpose=CitizenIntentEnum.SELF_CARE_GUIDANCE_REQUEST)

    @staticmethod
    def get_fever_safe_guidance(lang: str) -> Dict[str, Any]:
        """
        Non-diagnostic, medically reviewed general fever guidance.
        """
        if lang.startswith("hi"):
            return {
                "title": "बुखार के लिए सुरक्षित सामान्य देखभाल",
                "points": [
                    "पर्याप्त आराम करें और शारीरिक परिश्रम से बचें।",
                    "खूब पानी, ओआरएस या सुरक्षित तरल पदार्थ पिएं।",
                    "हल्का और ताजा भोजन लें।",
                    "थर्मामीटर से तापमान मापें और समय-समय पर नोट करें।",
                    "डॉक्टर की सलाह के बिना कोई एंटीबायोटिक या नई दवा शुरू न करें।"
                ],
                "warning": "यदि तापमान 102°F से अधिक हो, सांस लेने में तकलीफ हो या उल्टी हो, तो तुरंत डॉक्टर से संपर्क करें।"
            }
        elif lang.startswith("en"):
            return {
                "title": "Safe General Fever Guidance",
                "points": [
                    "Get adequate rest and avoid strenuous physical effort.",
                    "Drink plenty of safe fluids (water, ORS, broths) to maintain hydration.",
                    "Eat light, easily digestible, fresh meals.",
                    "Regularly measure and record your body temperature with a thermometer.",
                    "Do not start antibiotics or unprescribed medications without a doctor."
                ],
                "warning": "If temperature exceeds 102°F, or if you experience breathing difficulty or severe weakness, consult a doctor immediately."
            }
        else: # Marathi
            return {
                "title": "तापासाठी सुरक्षित घरगुती काळजी मार्गदर्शन",
                "points": [
                    "पुरेशी विश्रांती घ्या आणि शारीरिक श्रम टाळा.",
                    "शरीरात पाण्याचे प्रमाण टिकवण्यासाठी भरपूर पाणी, ओआरएस किंवा पातळ पदार्थ प्या.",
                    "हलका, ताजा आणि पचायला सोपा आहार घ्या.",
                    "थर्मामीटरने नियमित शरीराचे तापमान मोजा आणि नोंद ठेवा.",
                    "डॉक्टरांच्या सल्ल्याशिवाय कोणतेही अँटिबायोटिक किंवा नवीन औषध परस्पर घेऊ नका."
                ],
                "warning": "ताप १०२°F पेक्षा जास्त असल्यास, श्वास घेण्यास त्रास होत असल्यास, किंवा उलट्या सुरू असल्यास त्वरित डॉक्टरांचा सल्ला घ्या."
            }

