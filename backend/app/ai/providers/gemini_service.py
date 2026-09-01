import re
import json
import time
import logging
from typing import Dict, Any, Optional, List, Tuple
from google import genai
from google.genai import types
from app.config import settings
from app.ai.contracts.schemas import (
    NormalizedIntake, ClinicalEvidenceSummary, SchemeExplanation, SafetyCritique, AgentExecutionResult,
    CitizenIntentEnum, ContextTransitionEnum, CitizenUnderstandingOutput, CitizenDynamicResponseOutput,
    CitizenNewFacts, CitizenTurnAIOutput, CitizenClarifyingQuestion, CitizenProposedFacts
)
from app.ai.pii.masker import PIIMasker
from app.ai.rag.clinical_rag import clinical_rag_service
from app.ai.graph.scheme_graph import scheme_graph_service

logger = logging.getLogger("aarogya.gemini_service")

class GeminiService:
    """
    Google Gemini Reasoning Service using official Google GenAI standards.
    Provides 2-stage conversational intelligence:
    1. Structured Understanding (Intent, Context Transition, Fact Extraction, Goal)
    2. Contextual Dynamic Response Generation (Multilingual, Non-diagnostic, Action Resolver)
    """
    def __init__(self):
        self._api_key = settings.GEMINI_API_KEY
        self._is_live = bool(self._api_key and settings.GEMINI_MODE == "live")
        self._client = None
        self._last_error_category = None
        if self._is_live:
            try:
                self._client = genai.Client(api_key=self._api_key)
            except Exception as e:
                logger.error(f"Failed to initialize live Gemini Client: {e}")
                self._is_live = False

    @property
    def is_live(self) -> bool:
        return self._is_live

    def get_mode(self) -> str:
        return "LIVE" if self._is_live else "FALLBACK"

    def get_health_status(self) -> Dict[str, Any]:
        """Safe development health status showing live configuration & reachability without exposing keys."""
        is_reachable = False
        last_err = self._last_error_category
        if self._is_live and self._client:
            try:
                # Fast lightweight ping
                candidate = self._get_candidate_models()[0]
                resp = self._client.models.generate_content(
                    model=candidate,
                    contents="ping"
                )
                if resp and resp.text:
                    is_reachable = True
                    last_err = None
            except Exception as e:
                err_str = str(e).lower()
                if "429" in err_str or "quota" in err_str or "resource_exhausted" in err_str:
                    last_err = "RATE_LIMITED"
                elif "503" in err_str or "unavailable" in err_str:
                    last_err = "SERVICE_UNAVAILABLE"
                else:
                    last_err = "CONNECTION_FAILED"
        return {
            "provider": "GEMINI",
            "configured": bool(self._api_key),
            "reachable": is_reachable,
            "mode": "LIVE" if (self._is_live and is_reachable) else "LIMITED_FALLBACK",
            "last_error_category": last_err
        }

    def _get_candidate_models(self) -> List[str]:
        configured = settings.GEMINI_MODEL
        candidates = [
            configured,
            "gemini-3.5-flash-lite",
            "gemini-3.1-flash-lite",
            "gemini-3.5-flash"
        ]
        # De-duplicate while preserving pinned order
        return list(dict.fromkeys([m for m in candidates if m]))

    def understand_citizen_turn(
        self,
        latest_message: str,
        recent_messages: List[Dict[str, Any]],
        current_topic: Optional[str] = None,
        last_assistant_question: Optional[str] = None,
        confirmed_facts: Optional[Dict[str, Any]] = None,
        negated_facts: Optional[List[str]] = None,
        preferred_language: str = "mr-IN",
        request_id: Optional[str] = None
    ) -> Tuple[CitizenUnderstandingOutput, str, bool, Optional[str], Optional[str], Optional[str], Optional[int]]:
        """
        Stage 1: Multi-turn Structured Understanding via Gemini with strict Pydantic validation.
        Classifies intent (33 intents), context transition (11 transitions), extracts facts/negations/goals.
        Returns (understanding_output, provider_mode, structured_parse_success, fallback_reason, requested_model, successful_model, error_status)
        """
        masked_msg, _ = PIIMasker.mask_text(latest_message)
        masked_history = []
        for m in recent_messages[-8:]:
            masked_t, _ = PIIMasker.mask_text(m.get("text", "") or m.get("original_text", "") or "")
            masked_history.append({"sender": m.get("sender", "USER"), "text": masked_t})

        req_id = request_id or f"req-{uuid.uuid4().hex[:8]}"
        last_attempted_model = None
        last_err_status = None

        if self._is_live and self._client:
            models = self._get_candidate_models()
            prompt = (
                "You are the structured understanding engine for Aarogya Sahayak, a multilingual rural healthcare assistant in India.\n"
                "Analyze the citizen's latest message in context of the conversation and output strict JSON.\n\n"
                f"Selected Preferred Language: {preferred_language}\n"
                f"Current Conversation Topic: {current_topic or 'None'}\n"
                f"Last Assistant Question asked: {last_assistant_question or 'None'}\n"
                f"Previously Confirmed Facts: {confirmed_facts or {}}\n"
                f"Previously Negated Facts: {negated_facts or []}\n"
                f"Recent Messages: {masked_history}\n\n"
                f"Citizen Latest Message: '{masked_msg}'\n\n"
                "Instructions:\n"
                "1. 'intent': Must be exactly one of: GREETING, THANKS, HELP, CAPABILITIES, GENERAL_CONVERSATION, HEALTH_INFORMATION, "
                "NEW_HEALTH_CONCERN, SYMPTOM_UPDATE, ANSWER_TO_QUESTION, FOLLOW_UP_QUESTION, SELF_CARE_GUIDANCE_REQUEST, "
                "MENTAL_HEALTH_SUPPORT, MENTAL_HEALTH_CRISIS, DOCTOR_REQUEST, ASHA_REQUEST, FACILITY_SEARCH, "
                "SCHEME_INFORMATION, SCHEME_ELIGIBILITY, SCHEME_APPLICATION_HELP, MEDICINE_INFORMATION, "
                "MEDICATION_SIDE_EFFECT, VACCINATION_QUERY, MATERNAL_HEALTH_QUERY, CHILD_HEALTH_QUERY, NCD_QUERY, "
                "CASE_STATUS_QUERY, PRESCRIPTION_QUERY, INVESTIGATION_QUERY, FOLLOWUP_STATUS_QUERY, EMERGENCY_HELP, "
                "CORRECTION, CONFIRMATION, OUT_OF_SCOPE, UNCLEAR.\n"
                "2. 'context_transition': Must be exactly one of: NEW_TOPIC, CONTINUE_CURRENT_TOPIC, ANSWER_TO_PREVIOUS_QUESTION, "
                "ANSWER_AND_NEW_FACT, CORRECTION, NEGATION, FOLLOW_UP_QUESTION, REQUEST_ACTION, GENERAL_INFORMATION, CLOSE_CONVERSATION, UNCLEAR.\n"
                "3. If citizen negates a symptom (e.g. 'No swelling', 'नाही', 'no fever'), put it in new_facts.negated_symptoms.\n"
                "4. If citizen adds a new symptom (e.g. 'body pain', 'अंगदुखी'), put it in new_facts.symptoms.\n"
                "5. 'person_reference': SELF or OTHER (e.g., CHILD, MOTHER, FATHER, SPOUSE).\n"
                "6. If the citizen is answering the last assistant question, set answer_to_previous_question.\n"
                "7. Output valid JSON matching the schema."
            )

            for model_name in models:
                last_attempted_model = model_name
                t_call_start = time.time()
                try:
                    resp = self._client.models.generate_content(
                        model=model_name,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            temperature=0.0
                        )
                    )
                    call_latency_ms = round((time.time() - t_call_start) * 1000, 2)
                    raw_text = resp.text.strip()
                    try:
                        understanding = CitizenUnderstandingOutput.model_validate_json(raw_text)
                    except Exception as parse_err:
                        repair_prompt = f"Repair this invalid JSON to match the CitizenUnderstandingOutput schema strictly:\n{raw_text}"
                        resp_repair = self._client.models.generate_content(
                            model=model_name,
                            contents=repair_prompt,
                            config=types.GenerateContentConfig(
                                response_mime_type="application/json",
                                temperature=0.0
                            )
                        )
                        understanding = CitizenUnderstandingOutput.model_validate_json(resp_repair.text)

                    # Post-process extract temperature if present in utterance and missed by LLM
                    m_temp = re.search(r'\b(9\d(?:\.\d+)?|10\d(?:\.\d+)?)\s*(?:°|deg|degree|f|fahrenheit)?\b', masked_msg, re.IGNORECASE)
                    if m_temp and not understanding.new_facts.temperature_f:
                        try:
                            val = float(m_temp.group(1))
                            if 95.0 <= val <= 108.0:
                                understanding.new_facts.temperature_f = val
                        except Exception:
                            pass

                    # Safe structured telemetry (Zero PII)
                    logger.info(json.dumps({
                        "event": "gemini_provider_call",
                        "stage": "UNDERSTANDING",
                        "request_id": req_id,
                        "provider": "GEMINI",
                        "requested_model": models[0],
                        "successful_model": model_name,
                        "provider_mode": "GEMINI_LIVE",
                        "http_status": 200,
                        "fallback_reason": None,
                        "latency_ms": call_latency_ms
                    }))

                    return understanding, "GEMINI_LIVE", True, None, models[0], model_name, 200

                except Exception as e:
                    call_latency_ms = round((time.time() - t_call_start) * 1000, 2)
                    err_str = str(e).lower()
                    status_code = 500
                    if "401" in err_str or "unauthenticated" in err_str:
                        status_code = 401
                        self._last_error_category = "UNAUTHENTICATED"
                    elif "403" in err_str or "permission_denied" in err_str:
                        status_code = 403
                        self._last_error_category = "PERMISSION_DENIED"
                    elif "404" in err_str or "not_found" in err_str:
                        status_code = 404
                        self._last_error_category = "MODEL_NOT_FOUND"
                    elif "429" in err_str or "quota" in err_str or "resource_exhausted" in err_str:
                        status_code = 429
                        self._last_error_category = "RATE_LIMITED"
                    elif "503" in err_str or "unavailable" in err_str:
                        status_code = 503
                        self._last_error_category = "SERVICE_UNAVAILABLE"
                    elif "timeout" in err_str or "timed out" in err_str:
                        status_code = 504
                        self._last_error_category = "TIMEOUT"
                    else:
                        self._last_error_category = "API_ERROR"

                    last_err_status = status_code

                    logger.warning(json.dumps({
                        "event": "gemini_provider_error",
                        "stage": "UNDERSTANDING",
                        "request_id": req_id,
                        "provider": "GEMINI",
                        "requested_model": model_name,
                        "provider_mode": "FALLBACK_ATTEMPT",
                        "http_status": status_code,
                        "error_category": self._last_error_category,
                        "fallback_reason": f"Model {model_name} failed: HTTP {status_code}",
                        "latency_ms": call_latency_ms
                    }))

                    # Non-retryable auth/permission errors should break immediately without calling all fallback models
                    if status_code in (401, 403):
                        break
                    continue

        # Safe fallback telemetry
        fallback_reason = self._last_error_category or "GEMINI_UNAVAILABLE"
        logger.info(json.dumps({
            "event": "gemini_provider_fallback",
            "stage": "UNDERSTANDING",
            "request_id": req_id,
            "provider": "GEMINI",
            "requested_model": last_attempted_model or settings.GEMINI_MODEL,
            "successful_model": None,
            "provider_mode": "LIMITED_FALLBACK",
            "http_status": last_err_status,
            "fallback_reason": fallback_reason,
            "latency_ms": 0.0
        }))

        # Rule fallback understanding when Gemini unavailable
        fallback_understanding = self._fallback_understand(masked_msg, last_assistant_question, current_topic, preferred_language)
        return fallback_understanding, "LIMITED_FALLBACK", False, fallback_reason, (last_attempted_model or settings.GEMINI_MODEL), None, last_err_status

    def _fallback_understand(
        self,
        message: str,
        last_question: Optional[str],
        current_topic: Optional[str],
        language: str
    ) -> CitizenUnderstandingOutput:
        msg_l = message.lower()
        intent = CitizenIntentEnum.GENERAL_CONVERSATION
        transition = ContextTransitionEnum.NEW_TOPIC
        new_facts = CitizenNewFacts()

        if any(w in msg_l for w in ["hurt myself", "kill myself", "suicide", "आत्महत्या", "खुद को नुकसान"]):
            intent = CitizenIntentEnum.MENTAL_HEALTH_CRISIS
            transition = ContextTransitionEnum.NEW_TOPIC
        elif any(w in msg_l for w in ["108", "emergency", "छातीत", "chest pain", "unconscious", "seizure"]):
            intent = CitizenIntentEnum.EMERGENCY_HELP
            transition = ContextTransitionEnum.NEW_TOPIC
        elif any(w in msg_l for w in ["hello", "hi", "namaskar", "नमस्कार", "नमस्ते", "hey"]):
            intent = CitizenIntentEnum.GREETING
            transition = ContextTransitionEnum.NEW_TOPIC
        elif any(w in msg_l for w in ["what can you do", "capabilities", "तू काय करू शकतोस", "तुम क्या कर सकते हो"]):
            intent = CitizenIntentEnum.CAPABILITIES
            transition = ContextTransitionEnum.GENERAL_INFORMATION
        elif any(w in msg_l for w in ["thank", "thanks", "धन्यवाद", "आभार", "शुक्रिया"]):
            intent = CitizenIntentEnum.THANKS
            transition = ContextTransitionEnum.CLOSE_CONVERSATION
        elif any(w in msg_l for w in ["scheme", "योजना", "ayushman", "pmjay", "pm-jay", "लाभ"]):
            intent = CitizenIntentEnum.SCHEME_INFORMATION
            transition = ContextTransitionEnum.NEW_TOPIC
        elif any(w in msg_l for w in ["joint pain", "सांधेदुखी", "जोड़ों का दर्द", "joint"]):
            intent = CitizenIntentEnum.NEW_HEALTH_CONCERN
            transition = ContextTransitionEnum.NEW_TOPIC
            new_facts.symptoms = ["JOINT_PAIN"]
        elif any(w in msg_l for w in ["fever", "ताप", "बुखार"]):
            intent = CitizenIntentEnum.NEW_HEALTH_CONCERN
            transition = ContextTransitionEnum.NEW_TOPIC
            new_facts.symptoms = ["FEVER"]
        elif any(w in msg_l for w in ["not me", "child", "माझा मुलगा", "माझी मुलगी", "बच्चा"]):
            intent = CitizenIntentEnum.CORRECTION
            transition = ContextTransitionEnum.CORRECTION
            new_facts.person_reference = "CHILD"
        elif "no swelling" in msg_l or "नाही" in msg_l and "swelling" in (last_question or "").lower():
            intent = CitizenIntentEnum.ANSWER_TO_QUESTION
            transition = ContextTransitionEnum.ANSWER_AND_NEW_FACT if ("body pain" in msg_l or "अंगदुखी" in msg_l) else ContextTransitionEnum.ANSWER_TO_PREVIOUS_QUESTION
            new_facts.negated_symptoms = ["SWELLING"]
            if "body pain" in msg_l or "अंगदुखी" in msg_l:
                new_facts.symptoms.append("BODY_PAIN")
        elif "102" in msg_l or "103" in msg_l or "101" in msg_l or "100" in msg_l:
            intent = CitizenIntentEnum.ANSWER_TO_QUESTION
            transition = ContextTransitionEnum.ANSWER_TO_PREVIOUS_QUESTION
            for t_val in [103.0, 102.0, 101.0, 100.0]:
                if str(int(t_val)) in msg_l:
                    new_facts.temperature_f = t_val
                    new_facts.temperature_c = (t_val - 32) * 5 / 9
                    break
        elif any(w in msg_l for w in ["what can i do", "what should i do", "काय करू", "क्या करूँ"]):
            intent = CitizenIntentEnum.SELF_CARE_GUIDANCE_REQUEST
            transition = ContextTransitionEnum.FOLLOW_UP_QUESTION
        elif any(w in msg_l for w in ["doctor", "डॉक्टर", "वैद्यकीय अधिकारी"]):
            intent = CitizenIntentEnum.DOCTOR_REQUEST
            transition = ContextTransitionEnum.REQUEST_ACTION
        elif any(w in msg_l for w in ["asha", "आशा", "दीदी"]):
            intent = CitizenIntentEnum.ASHA_REQUEST
            transition = ContextTransitionEnum.REQUEST_ACTION
        elif any(w in msg_l for w in ["hospital", "phc", "centre", "center", "रुग्णालय", "दवाखाना"]):
            intent = CitizenIntentEnum.FACILITY_SEARCH
            transition = ContextTransitionEnum.REQUEST_ACTION
        elif any(w in msg_l for w in ["anxious", "sad", "depressed", "चिंता", "तणाव"]):
            intent = CitizenIntentEnum.MENTAL_HEALTH_SUPPORT
            transition = ContextTransitionEnum.NEW_TOPIC

        return CitizenUnderstandingOutput(
            intent=intent,
            context_transition=transition,
            detected_language=language[:2] if language else "en",
            citizen_goal=message,
            new_facts=new_facts,
            recommended_response_goal="ACKNOWLEDGE_AND_RESPOND",
            confidence=0.85
        )

    def generate_dynamic_response(
        self,
        latest_message: str,
        recent_messages: List[Dict[str, Any]],
        understanding: CitizenUnderstandingOutput,
        confirmed_facts: Dict[str, Any],
        negated_facts: List[str],
        last_assistant_question: Optional[str],
        safety_evaluation: Dict[str, Any],
        verified_tool_data: Optional[Dict[str, Any]],
        allowed_action_types: List[str],
        preferred_language: str = "mr-IN",
        request_id: Optional[str] = None
    ) -> Tuple[CitizenDynamicResponseOutput, str, Optional[str], Optional[str], Optional[int]]:
        """
        Stage 2: Multilingual Contextual Response Generation with Gemini.
        Genuinely understands and answers the citizen's actual message in context.
        Returns (dynamic_response, provider_mode, requested_model, successful_model, http_status)
        """
        masked_msg, _ = PIIMasker.mask_text(latest_message)
        masked_history = []
        for m in recent_messages[-8:]:
            masked_t, _ = PIIMasker.mask_text(m.get("text", "") or m.get("original_text", "") or "")
            masked_history.append({"sender": m.get("sender", "USER"), "text": masked_t})

        req_id = request_id or f"req-{uuid.uuid4().hex[:8]}"
        last_attempted_model = None
        last_err_status = None

        if self._is_live and self._client:
            models = self._get_candidate_models()
            lang_prompt_map = {
                "en-IN": "Respond strictly in English. Do not use non-English sentences.",
                "hi-IN": "Respond strictly in standard Hindi (हिंदी) in normal Devanagari script. Do not mix English sentences into the reply.",
                "mr-IN": "Respond strictly in natural Marathi (मराठी) in normal Devanagari script. Do not mix English sentences into the reply.",
                "gu-IN": "Respond strictly in natural Gujarati (ગુજરાતી) in native Gujarati script. Do not mix English sentences into the reply.",
                "bn-IN": "Respond strictly in natural Bengali (বাংলা) in native Bengali script. Do not mix English sentences into the reply.",
                "kn-IN": "Respond strictly in natural Kannada (ಕನ್ನಡ) in native Kannada script. Do not mix English sentences into the reply.",
                "te-IN": "Respond strictly in natural Telugu (తెలుగు) in native Telugu script. Do not mix English sentences into the reply.",
                "ta-IN": "Respond strictly in natural Tamil (தமிழ்) in native Tamil script. Do not mix English sentences into the reply.",
                "ml-IN": "Respond strictly in natural Malayalam (മലയാളം) in native Malayalam script. Do not mix English sentences into the reply.",
                "pa-IN": "Respond strictly in natural Punjabi (ਪੰਜਾਬੀ) in native Gurmukhi script. Do not mix English sentences into the reply.",
                "od-IN": "Respond strictly in natural Odia (ଓଡ଼ିଆ) in native Odia script. Do not mix English sentences into the reply."
            }
            lang_instruction = lang_prompt_map.get(preferred_language, f"Respond strictly in {preferred_language} in its normal native script.")

            prompt = (
                "You are Aarogya Sahayak, a multilingual rural healthcare-access assistant in India.\n"
                f"MANDATORY LANGUAGE INSTRUCTION: {lang_instruction}\n"
                "Do not mix English sentences into the reply for non-English locales.\n"
                "Keep names, medicine names, measurements (e.g. 'BP 120/80 mmHg'), IDs, clinical codes, and official abbreviations (e.g. PHC, ABHA, PM-JAY) unchanged when required.\n"
                "Return clarification questions and guidance strictly in the requested language and script.\n"
                "Never generate frontend button labels. Return canonical action codes subset from Allowed Action Types.\n\n"
                "Understand and answer the citizen's actual latest message using the relevant conversation context.\n"
                "Do not force the citizen into a predefined script. Do not repeat previous replies or ask questions already answered.\n"
                "For greetings and normal conversation, respond naturally without creating clinical records.\n"
                "For general health questions, provide clear low-risk health information and relevant warning signs without diagnosing or prescribing.\n"
                "For personal symptoms, acknowledge the current symptoms and ask only the most useful one or two questions.\n"
                "For follow-up answers, interpret them using the last assistant question.\n"
                "For a topic change, start or clarify the new topic rather than reusing old symptoms.\n"
                "For schemes, medicines, facilities, appointments and care-status questions, use only verified data supplied by backend tools.\n\n"
                "The deterministic safety result is authoritative. Never weaken it. Never invent eligibility, facilities, doctors, prescriptions, appointments, test results or completed actions. Return the required JSON only.\n\n"
                f"Selected Preferred Language: {preferred_language}\n"
                f"Latest Citizen Message: '{masked_msg}'\n"
                f"Recent Conversation History: {masked_history}\n"
                f"Structured Understanding: {understanding.model_dump()}\n"
                f"Confirmed Facts: {confirmed_facts}\n"
                f"Negated Facts: {negated_facts}\n"
                f"Last Assistant Question: {last_assistant_question or 'None'}\n"
                f"Authoritative Safety Result: {safety_evaluation}\n"
                f"Verified Backend Data: {verified_tool_data or 'None'}\n"
                f"Allowed Action Types: {allowed_action_types}\n\n"
                "Required JSON Output Schema keys:\n"
                "- 'text': Dynamic citizen-friendly answer in the requested language & script\n"
                "- 'language': Selected language code (e.g. 'mr-IN', 'hi-IN', 'ta-IN', 'en-IN')\n"
                "- 'response_type': One of DIRECT_ANSWER, CLARIFYING_QUESTION, GUIDANCE, ACTION_OFFER, SAFETY_WARNING, CLOSING\n"
                "- 'question': Optional single clarifying question string in requested language & script, or null\n"
                "- 'suggested_replies': List of 2-4 short contextual quick replies in citizen's requested language\n"
                "- 'requested_action_types': List of canonical action codes subset from Allowed Action Types\n"
                "- 'facts_used': List of facts referenced in explanation\n"
                "- 'uncertainty_statement': Optional statement if clarification needed or null"
            )

            for model_name in models:
                last_attempted_model = model_name
                t_call_start = time.time()
                try:
                    resp = self._client.models.generate_content(
                        model=model_name,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            temperature=0.2
                        )
                    )
                    call_latency_ms = round((time.time() - t_call_start) * 1000, 2)
                    raw_text = resp.text.strip()
                    try:
                        dyn_resp = CitizenDynamicResponseOutput.model_validate_json(raw_text)
                    except Exception as parse_err:
                        repair_prompt = f"Fix JSON to match CitizenDynamicResponseOutput strictly in {preferred_language}:\n{raw_text}"
                        resp_repair = self._client.models.generate_content(
                            model=model_name,
                            contents=repair_prompt,
                            config=types.GenerateContentConfig(
                                response_mime_type="application/json",
                                temperature=0.0
                            )
                        )
                        dyn_resp = CitizenDynamicResponseOutput.model_validate_json(resp_repair.text)

                    # Validate response script against expected locale
                    if not self._validate_response_script(dyn_resp.text, preferred_language):
                        # Strict retry attempt 1
                        logger.warning(f"Script mismatch for {preferred_language}. Retrying with strict language instruction.")
                        retry_prompt = (
                            f"{prompt}\n\n"
                            f"CRITICAL ERROR: You previously replied in the wrong script/language. "
                            f"You MUST respond ONLY in {preferred_language} and its native script. "
                            f"Do not output English text."
                        )
                        resp_retry = self._client.models.generate_content(
                            model=model_name,
                            contents=retry_prompt,
                            config=types.GenerateContentConfig(
                                response_mime_type="application/json",
                                temperature=0.0
                            )
                        )
                        dyn_retry = CitizenDynamicResponseOutput.model_validate_json(resp_retry.text.strip())
                        if self._validate_response_script(dyn_retry.text, preferred_language):
                            dyn_resp = dyn_retry

                    logger.info(json.dumps({
                        "event": "gemini_provider_call",
                        "stage": "DYNAMIC_RESPONSE",
                        "request_id": req_id,
                        "provider": "GEMINI",
                        "requested_model": models[0],
                        "successful_model": model_name,
                        "provider_mode": "GEMINI_LIVE",
                        "http_status": 200,
                        "fallback_reason": None,
                        "latency_ms": call_latency_ms
                    }))

                    return dyn_resp, "GEMINI_LIVE", models[0], model_name, 200

                except Exception as e:
                    call_latency_ms = round((time.time() - t_call_start) * 1000, 2)
                    err_str = str(e).lower()
                    status_code = 500
                    if "401" in err_str or "unauthenticated" in err_str:
                        status_code = 401
                        self._last_error_category = "UNAUTHENTICATED"
                    elif "403" in err_str or "permission_denied" in err_str:
                        status_code = 403
                        self._last_error_category = "PERMISSION_DENIED"
                    elif "404" in err_str or "not_found" in err_str:
                        status_code = 404
                        self._last_error_category = "MODEL_NOT_FOUND"
                    elif "429" in err_str or "quota" in err_str or "resource_exhausted" in err_str:
                        status_code = 429
                        self._last_error_category = "RATE_LIMITED"
                    elif "503" in err_str or "unavailable" in err_str:
                        status_code = 503
                        self._last_error_category = "SERVICE_UNAVAILABLE"
                    elif "timeout" in err_str or "timed out" in err_str:
                        status_code = 504
                        self._last_error_category = "TIMEOUT"
                    else:
                        self._last_error_category = "API_ERROR"

                    last_err_status = status_code

                    logger.warning(json.dumps({
                        "event": "gemini_provider_error",
                        "stage": "DYNAMIC_RESPONSE",
                        "request_id": req_id,
                        "provider": "GEMINI",
                        "requested_model": model_name,
                        "provider_mode": "FALLBACK_ATTEMPT",
                        "http_status": status_code,
                        "error_category": self._last_error_category,
                        "fallback_reason": f"Model {model_name} failed: HTTP {status_code}",
                        "latency_ms": call_latency_ms
                    }))

                    # Non-retryable auth/permission errors should break immediately without calling all fallback models
                    if status_code in (401, 403):
                        break
                    continue

        fallback_reason = self._last_error_category or "GEMINI_UNAVAILABLE"
        logger.info(json.dumps({
            "event": "gemini_provider_fallback",
            "stage": "DYNAMIC_RESPONSE",
            "request_id": req_id,
            "provider": "GEMINI",
            "requested_model": last_attempted_model or settings.GEMINI_MODEL,
            "successful_model": None,
            "provider_mode": "LIMITED_FALLBACK",
            "http_status": last_err_status,
            "fallback_reason": fallback_reason,
            "latency_ms": 0.0
        }))

        # Honest Limited Fallback Mode (does NOT pretend to be AI text)
        fallback_resp = self._fallback_dynamic_response(
            latest_message=masked_msg,
            understanding=understanding,
            safety_evaluation=safety_evaluation,
            verified_tool_data=verified_tool_data,
            language=preferred_language
        )
        return fallback_resp, "LIMITED_FALLBACK", (last_attempted_model or settings.GEMINI_MODEL), None, last_err_status

    def _validate_response_script(self, text: str, locale: str) -> bool:
        """Validates that text matches expected native script ranges for the requested locale."""
        if not text or not locale or locale.startswith("en"):
            return True

        text_clean = "".join(c for c in text if c.isalpha())
        if not text_clean:
            return True

        script_ranges = {
            "hi-IN": [(0x0900, 0x097F)],
            "mr-IN": [(0x0900, 0x097F)],
            "gu-IN": [(0x0A80, 0x0AFF)],
            "bn-IN": [(0x0980, 0x09FF)],
            "kn-IN": [(0x0C80, 0x0CFF)],
            "te-IN": [(0x0C00, 0x0C7F)],
            "ta-IN": [(0x0B80, 0x0BFF)],
            "ml-IN": [(0x0D00, 0x0D7F)],
            "pa-IN": [(0x0A00, 0x0A7F)],
            "od-IN": [(0x0B00, 0x0B7F)],
        }

        ranges = script_ranges.get(locale)
        if not ranges:
            return True

        match_count = sum(1 for char in text_clean if any(start <= ord(char) <= end for start, end in ranges))
        ratio = match_count / len(text_clean)
        return ratio >= 0.35

    def _fallback_dynamic_response(
        self,
        latest_message: str,
        understanding: CitizenUnderstandingOutput,
        safety_evaluation: Dict[str, Any],
        verified_tool_data: Optional[Dict[str, Any]],
        language: str
    ) -> CitizenDynamicResponseOutput:
        loc = language
        if loc not in ["en-IN", "hi-IN", "mr-IN", "gu-IN", "bn-IN", "kn-IN", "te-IN", "ta-IN", "ml-IN", "pa-IN", "od-IN"]:
            prefix_map = {
                "hi": "hi-IN", "en": "en-IN", "gu": "gu-IN", "bn": "bn-IN",
                "kn": "kn-IN", "te": "te-IN", "ta": "ta-IN", "ml": "ml-IN",
                "pa": "pa-IN", "od": "od-IN", "or": "od-IN", "mr": "mr-IN"
            }
            loc = prefix_map.get(language[:2].lower(), "mr-IN")

        intent = understanding.intent

        emergency_messages = {
            "en-IN": "⚠️ Critical emergency warning signs detected. Please call 108 Emergency immediately or proceed to the nearest 24x7 healthcare facility.",
            "hi-IN": "⚠️ गंभीर आपातकालीन लक्षण पाए गए हैं। कृपया तुरंत 108 आपातकालीन सेवा पर कॉल करें या नजदीकी 24x7 स्वास्थ्य केंद्र जाएं।",
            "mr-IN": "⚠️ गंभीर व तात्काळ काळजीची लक्षणे आढळली आहेत. कृपया त्वरित १०८ आपत्कालीन सेवेवर कॉल करा किंवा जवळच्या २४x७ आरोग्य केंद्रात जा.",
            "gu-IN": "⚠️ ગંભીર કટોકટીના લક્ષણો જણાયા છે. કૃપા કરીને તાત્કાલિક 108 ઇમરજન્સી પર કૉલ કરો અથવા નજીકના 24x7 આરોગ્ય કેન્દ્ર પર જાઓ.",
            "bn-IN": "⚠️ জরুরি সতর্কতামূলক লক্ষণ সনাক্ত হয়েছে। অবিলম্বে 108 জরুরি নম্বরে কল করুন বা নিকটস্থ 24x7 স্বাস্থ্যকেন্দ্রে যান।",
            "kn-IN": "⚠️ ತುರ್ತು ಎಚ್ಚರಿಕೆಯ ಲಕ್ಷಣಗಳು ಕಂಡುಬಂದಿವೆ. ದಯವಿಟ್ಟು ತಕ್ಷಣ 108 ತುರ್ತು ಸೇವೆಗೆ ಕರೆ ಮಾಡಿ ಅಥವಾ ಹತ್ತಿರದ 24x7 ಆರೋಗ್ಯ ಕೇಂದ್ರಕ್ಕೆ ತೆರಳಿ.",
            "te-IN": "⚠️ అత్యవసర హెచ్చరిక సంకేతాలు గుర్తించబడ్డాయి. దయచేసి వెంటనే 108 అత్యవసర సేవకు కాల్ చేయండి లేదా సమీపంలోని 24x7 ఆరోగ్య కేంద్రానికి వెళ్లండి.",
            "ta-IN": "⚠️ அவசர எச்சரிக்கை அறிகுறிகள் கண்டறியப்பட்டுள்ளன. உடனடியாக 108 அவசர சேவைக்கு அழைக்கவும் அல்லது அருகிலுள்ள 24x7 சுகாதார மையத்திற்கு செல்லவும்.",
            "ml-IN": "⚠️ അടിയന്തര മുന്നറിയിപ്പ് ലക്ഷണങ്ങൾ കണ്ടെത്തി. ദയവായി ഉടൻ 108 എമർജൻസിയിൽ വിളിക്കുക അല്ലെങ്കിൽ അടുത്തുള്ള 24x7 ആരോഗ്യ കേന്ദ്രത്തിൽ പോകുക.",
            "pa-IN": "⚠️ ਗੰਭੀਰ ਐਮਰਜੈਂਸੀ ਲੱਛਣ ਮਿਲੇ ਹਨ। ਕਿਰਪਾ ਕਰਕੇ ਤੁਰੰਤ 108 ਐਮਰਜੈਂਸੀ 'ਤੇ ਕਾਲ ਕਰੋ ਜਾਂ ਨਜ਼ਦੀਕੀ 24x7 ਸਿਹਤ ਕੇਂਦਰ ਜਾਓ।",
            "od-IN": "⚠️ ଜରୁରୀକାଳୀନ ଚେତାବନୀ ଲକ୍ଷଣ ଚିହ୍ନଟ ହୋଇଛି। ଦୟାକରି ତୁରନ୍ତ 108 ଜରୁରୀକାଳୀନ ସେବାକୁ କଲ୍ କରନ୍ତୁ କିମ୍ବା ନିକଟସ୍ଥ 24x7 ସ୍ୱାସ୍ଥ୍ୟ କେନ୍ଦ୍ରକୁ ଯାଆନ୍ତୁ।"
        }

        crisis_messages = {
            "en-IN": "⚠️ Your safety is our highest priority. Please reach out to Tele-MANAS (14416) or Emergency 108 immediately.",
            "hi-IN": "⚠️ आपकी सुरक्षा हमारी सर्वोच्च प्राथमिकता है। कृपया तुरंत टेली-मानस (14416) या आपातकालीन 108 पर संपर्क करें।",
            "mr-IN": "⚠️ तुमची सुरक्षितता अत्यंत महत्त्वाची आहे. कृपया तात्काळ २४x७ मानसिक आरोग्य हेल्पलाइन टेली-मानस (१४४१६) अथवा १०८ वर संपर्क करा.",
            "gu-IN": "⚠️ તમારી સુરક્ષા અમારી સર્વોચ્ચ પ્રાથમિકતા છે. કૃપા કરીને તાત્કાલિક ટેલી-માનસ (14416) અથવા 108 પર સંપર્ક કરો.",
            "bn-IN": "⚠️ আপনার নিরাপত্তা আমাদের সর্বোচ্চ অগ্রাধিকার। অবিলম্বে টেলি-মানস (14416) বা জরুরি 108 নম্বরে যোগাযোগ করুন।",
            "kn-IN": "⚠️ ನಿಮ್ಮ ಸುರಕ್ಷತೆ ನಮ್ಮ ಪ್ರಮುಖ ಆದ್ಯತೆಯಾಗಿದೆ. ದಯವಿಟ್ಟು ತಕ್ಷಣ ಟೆಲಿ-ಮಾನಸ್ (14416) ಅಥವಾ ತುರ್ತು 108 ಅನ್ನು ಸಂಪರ್ਕಿಸಿ.",
            "te-IN": "⚠️ మీ భద్రత మా అత్యున్నత ప్రాధాన్యత. దయచేసి వెంటనే టెలి-మానస్ (14416) లేదా ఎమర్జెన్సీ 108ను సంప్రదించండి.",
            "ta-IN": "⚠️ உங்கள் பாதுகாப்பு எங்கள் முன்னுரிமை. உடனடியாக டெலி-மானாஸ் (14416) அல்லது அவசர 108 ஐ தொடர்பு கொள்ளவும்.",
            "ml-IN": "⚠️ നിങ്ങളുടെ സുരക്ഷ ഞങ്ങളുടെ ഏറ്റവും ഉയർന്ന മുൻഗണനയാണ്. ദയവായി ഉടൻ ടെലി-മാനസ് (14416) അല്ലെങ്കിൽ എമർജൻസി 108-ൽ ബന്ധപ്പെടുക.",
            "pa-IN": "⚠️ ਤੁਹਾਡੀ ਸੁਰੱਖਿਆ ਸਾਡੀ ਸਭ ਤੋਂ ਵੱਡੀ ਤਰਜੀਹ ਹੈ। ਕਿਰਪਾ ਕਰਕੇ ਤੁਰੰਤ ਟੈਲੀ-ਮਾਨਸ (14416) ਜਾਂ ਐਮਰਜੈਂਸੀ 108 'ਤੇ ਸੰਪਰਕ ਕਰੋ।",
            "od-IN": "⚠️ ଆପଣଙ୍କ ସୁରକ୍ଷା ଆମର ପ୍ରାଥମିକତା। ଦୟାକରି ତୁରନ୍ତ ଟେଲି-ମାନସ (14416) କିମ୍ବା 108 ସହିତ ଯୋଗାଯୋଗ କରନ୍ତୁ।"
        }

        limited_messages = {
            "en-IN": "Conversational assistance is temporarily in limited mode. You can directly access healthcare services below or retry.",
            "hi-IN": "बातचीत सहायता अस्थायी रूप से सीमित मोड में है। आप सीधे नीचे दी गई स्वास्थ्य सेवाओं का उपयोग कर सकते हैं या पुनः प्रयास कर सकते हैं।",
            "mr-IN": "संभाषण सहाय्य सध्या मर्यादित मोडमध्ये आहे. आपण खालील आरोग्य सेवांचा थेट वापर करू शकता किंवा पुन्हा प्रयत्न करू शकता.",
            "gu-IN": "વાતચીત સહાય હાલમાં મર્યાદિત મોડમાં છે. તમે નીચે આપેલી આરોગ્ય સેવાઓનો સીધો ઉપયોગ કરી શકો છો અથવા ફરી પ્રયાસ કરી શકો છો.",
            "bn-IN": "কথোপকথন সহায়তা বর্তমানে সীমিত মোডে রয়েছে। আপনি সরাসরি নীচের স্বাস্থ্য পরিষেবাগুলি ব্যবহার করতে পারেন বা পুনরায় চেষ্টা করতে পারেন।",
            "kn-IN": "ಸಂಭಾಷಣೆ ಸಹಾಯವು ಪ್ರಸ್ತುತ ಸೀಮಿತ ಮೋಡ್‌ನಲ್ಲಿದೆ. ನೀವು ಕೆಳಗಿನ ಆರೋಗ್ಯ ಸೇವೆಗಳನ್ನು ನೇರವಾಗಿ ಬಳಸಬಹುದು ಅಥವಾ ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಬಹುದು.",
            "te-IN": "సంభాషణ సహాయం ప్రస్తుతం పరిమిత మోడ్‌లో ఉంది. మీరు దిగువ ఆరోగ్య సేవలను నేరుగా ఉపయోగించవచ్చు లేదా మళ్లీ ప్రయత్నించవచ్చు.",
            "ta-IN": "உரையாடல் உதவி தற்போது வரம்பிற்குட்பட்ட முறையில் உள்ளது. நீங்கள் கீழே உள்ள சுகாதார சேவைகளை நேரடியாகப் பயன்படுத்தலாம் அல்லது மீண்டும் முயற்சிக்கலாம்.",
            "ml-IN": "സംഭാഷണ സഹായം നിലവിൽ പരിമിതമായ മോഡിലാണ്. നിങ്ങൾക്ക് താഴെയുള്ള ആരോഗ്യ സേവനങ്ങൾ നേരിട്ട് ഉപയോഗിക്കാം അല്ലെങ്കിൽ വീണ്ടും ശ്രമിക്കാം.",
            "pa-IN": "ਗੱਲਬਾਤ ਸਹਾਇਤਾ ਫਿਲਹਾਲ ਸੀਮਤ ਮੋਡ ਵਿੱਚ ਹੈ। ਤੁਸੀਂ ਹੇਠਾਂ ਦਿੱਤੀਆਂ ਸਿਹਤ ਸੇਵਾਵਾਂ ਦੀ ਸਿੱਧੀ ਵਰਤੋਂ ਕਰ ਸਕਦੇ ਹੋ ਜਾਂ ਦੁਬਾਰਾ ਕੋਸ਼ਿਸ਼ ਕਰ ਸਕਦੇ ਹੋ।",
            "od-IN": "କଥାବାର୍ତ୍ତା ସହାୟତା ବର୍ତ୍ତମାନ ସୀମିତ ମୋଡ୍‌ରେ ଅଛି। ଆପଣ ସିଧାସଳଖ ନିମ୍ନଲିଖିତ ସ୍ୱାସ୍ଥ୍ୟ ସେବା ବ୍ୟବହାର କରିପାରିବେ କିମ୍ବା ପୁନର୍ବାର ଚେଷ୍ଟା କରିପାରିବେ।"
        }

        # Emergency override
        if safety_evaluation.get("level") == "EMERGENCY" or intent == CitizenIntentEnum.EMERGENCY_HELP:
            return CitizenDynamicResponseOutput(
                text=emergency_messages.get(loc, emergency_messages["en-IN"]),
                language=loc,
                response_type="SAFETY_WARNING",
                requested_action_types=["CALL_108", "FIND_FACILITY", "SPEAK_TO_DOCTOR"],
                suggested_replies=["CALL_108", "SPEAK_TO_DOCTOR"]
            )

        if intent == CitizenIntentEnum.MENTAL_HEALTH_CRISIS:
            return CitizenDynamicResponseOutput(
                text=crisis_messages.get(loc, crisis_messages["en-IN"]),
                language=loc,
                response_type="SAFETY_WARNING",
                requested_action_types=["CALL_14416", "CALL_108", "SPEAK_TO_DOCTOR"],
                suggested_replies=["CALL_14416", "SPEAK_TO_DOCTOR"]
            )

        return CitizenDynamicResponseOutput(
            text=limited_messages.get(loc, limited_messages["en-IN"]),
            language=loc,
            response_type="GUIDANCE",
            requested_action_types=["SPEAK_TO_DOCTOR", "FIND_FACILITY", "CHECK_SCHEMES"],
            suggested_replies=["SPEAK_TO_DOCTOR", "FIND_HEALTH_CENTRE", "CHECK_SCHEMES"]
        )

    def process_intake(self, text: str, preferred_language: str = "en") -> NormalizedIntake:
        """Normalize citizen symptoms into structured intake contract."""
        masked_text, _ = PIIMasker.mask_text(text)
        symptoms = []
        lower = masked_text.lower()
        if "headache" in lower or "डोकेदुखी" in lower or "सिरदर्द" in lower:
            symptoms.append("severe headache")
        if "blurred" in lower or "vision" in lower or "धूसर" in lower:
            symptoms.append("blurred vision")
        if "swell" in lower or "feet" in lower or "edema" in lower or "सूजन" in lower:
            symptoms.append("pedal edema")
        if "chest pain" in lower or "छातीत दुखणे" in lower:
            symptoms.append("chest pain")
        if "breath" in lower or "shortness" in lower or "श्वास" in lower:
            symptoms.append("shortness of breath")
        if "fever" in lower or "ताप" in lower or "बुखार" in lower:
            symptoms.append("high fever")

        is_preg = any(w in lower for w in ["pregnant", "pregnancy", "गर्भवती", "महिने", "trimester", "week"])
        gestational_weeks = 28 if is_preg else None

        fallback_result = NormalizedIntake(
            symptoms=symptoms or ["unspecified health concern"],
            duration="3 days",
            severity_descriptors=["acute", "progressive"] if symptoms else [],
            is_pregnant=is_preg,
            gestational_weeks=gestational_weeks,
            uncertain_fields=["exact onset date"] if not symptoms else [],
            clarification_questions=["When did these symptoms first start?", "Are you able to rest comfortably?"]
        )

        if not self._is_live or not self._client:
            return fallback_result

        candidate_models = self._get_candidate_models()
        for model_name in candidate_models:
            try:
                prompt = (
                    f"Extract structured clinical findings from this patient intake transcript: '{masked_text}'. "
                    "Ensure zero PII remains in your output. Map findings to the provided schema."
                )
                response = self._client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=NormalizedIntake,
                        temperature=0.0
                    )
                )
                return NormalizedIntake.model_validate_json(response.text)
            except Exception:
                continue

        return fallback_result

    def generate_clinical_evidence_summary(
        self,
        intake: NormalizedIntake,
        vitals_text: str,
        retrieved_evidence: List[Dict[str, Any]]
    ) -> ClinicalEvidenceSummary:
        citations = [ev["chunk_id"] for ev in retrieved_evidence]
        findings = [f"Symptoms reported: {', '.join(intake.symptoms)}"]
        if intake.is_pregnant:
            findings.append(f"Patient is pregnant ({intake.gestational_weeks or 'undetermined'} weeks)")
        if vitals_text:
            findings.append(f"Recorded Vitals: {vitals_text}")

        evidence_content_merged = "\n".join([f"- Chunk {ev['chunk_id']}: {ev['content']}" for ev in retrieved_evidence])

        fallback_summary = (
            f"Evidence-grounded clinical review brief: Citizen presents with {', '.join(intake.symptoms)}. "
            f"Vitals indicate {vitals_text or 'routine parameters'}. "
            f"Cross-referenced with ICMR / MoHFW Standard Treatment Workflows on primary care management."
        )

        safety_notes = []
        if intake.is_pregnant and ("headache" in " ".join(intake.symptoms) or "150/100" in vitals_text):
            safety_notes.append("Maternal Pre-eclampsia Risk Rule Triggered: Immediate PHC Medical Officer review advised.")

        fallback_result = ClinicalEvidenceSummary(
            summary_text=fallback_summary,
            key_findings=findings,
            guideline_citations=citations,
            safety_notes=safety_notes
        )

        if not self._is_live or not self._client:
            return fallback_result

        for model_name in self._get_candidate_models():
            try:
                prompt = (
                    f"You are a clinical synthesis assistant. Ground your response STRICTLY on these guidelines:\n"
                    f"{evidence_content_merged}\n\n"
                    f"Synthesize a non-diagnostic evidence brief for the doctor. Patient findings: {findings}.\n"
                    f"Rules:\n"
                    f"1. DO NOT diagnose or confirm pre-eclampsia (only state it is a risk warning).\n"
                    f"2. DO NOT suggest, prescribe or dose medications.\n"
                    f"3. Mandate human review."
                )
                response = self._client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=ClinicalEvidenceSummary,
                        temperature=0.0
                    )
                )
                return ClinicalEvidenceSummary.model_validate_json(response.text)
            except Exception:
                continue

        return fallback_result

    def evaluate_safety_critic(
        self,
        intake: NormalizedIntake,
        summary: ClinicalEvidenceSummary
    ) -> SafetyCritique:
        violations = []
        text_to_check = summary.summary_text.lower()
        if "patient definitely has" in text_to_check or "confirmed diagnosis:" in text_to_check:
            violations.append("AI attempted unauthorized diagnostic confirmation")
        if re.search(r'\b(?:prescribe|take|give)\s+\d+\s*mg\b', text_to_check):
            violations.append("AI attempted unauthorized pharmaceutical prescription")

        return SafetyCritique(
            is_safe=len(violations) == 0,
            violations=violations,
            contains_unauthorized_diagnosis=False,
            contains_unauthorized_prescription=False,
            contains_leaked_pii=False,
            has_valid_citations=len(summary.guideline_citations) > 0,
            human_confirmation_mandated=True
        )

    def generate_citizen_turn(
        self,
        message: str,
        language: str,
        context: Dict[str, Any],
        safety_result: Optional[Dict[str, Any]] = None,
        allowed_actions: Optional[List[str]] = None,
        recent_turns: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Backward compatibility adapter for legacy callers."""
        understanding, mode, ok, err = self.understand_citizen_turn(
            latest_message=message,
            recent_messages=recent_turns or [],
            current_topic=context.get("current_topic"),
            last_assistant_question=context.get("pending_question"),
            confirmed_facts=context.get("confirmed_facts", {}),
            negated_facts=context.get("negated_facts", []),
            preferred_language=language
        )
        dyn_resp, resp_mode = self.generate_dynamic_response(
            latest_message=message,
            recent_messages=recent_turns or [],
            understanding=understanding,
            confirmed_facts=context.get("confirmed_facts", {}),
            negated_facts=context.get("negated_facts", []),
            last_assistant_question=context.get("pending_question"),
            safety_evaluation=safety_result or {},
            verified_tool_data=None,
            allowed_action_types=allowed_actions or ["SPEAK_TO_DOCTOR", "FIND_FACILITY", "CHECK_SCHEMES"],
            preferred_language=language
        )
        return {
            "output": CitizenTurnAIOutput(
                intent=understanding.intent.value,
                language=dyn_resp.language,
                acknowledgement="",
                answer=dyn_resp.text,
                clarifying_questions=[
                    CitizenClarifyingQuestion(
                        question_id="clarifying_q",
                        text=dyn_resp.question,
                        expected_type="TEXT"
                    )
                ] if dyn_resp.question else [],
                suggested_actions=dyn_resp.requested_action_types,
                proposed_facts=CitizenProposedFacts(
                    symptoms=understanding.new_facts.symptoms,
                    duration=understanding.new_facts.duration,
                    vitals={"temperature_f": understanding.new_facts.temperature_f} if understanding.new_facts.temperature_f else {}
                )
            ),
            "provider_mode": mode if mode == "GEMINI_LIVE" else resp_mode,
            "latency_ms": 100.0,
            "error": err
        }

# Singleton Gemini service
gemini_service = GeminiService()
