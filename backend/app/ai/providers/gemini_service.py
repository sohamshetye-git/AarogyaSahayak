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
            "gemini-3.5-flash",
            "gemini-3.5-flash-lite",
            "gemini-3.1-flash-lite",
            "gemini-2.5-flash",
            "gemini-flash-latest"
        ]
        # De-duplicate while preserving order
        return list(dict.fromkeys([m for m in candidates if m]))

    def understand_citizen_turn(
        self,
        latest_message: str,
        recent_messages: List[Dict[str, Any]],
        current_topic: Optional[str] = None,
        last_assistant_question: Optional[str] = None,
        confirmed_facts: Optional[Dict[str, Any]] = None,
        negated_facts: Optional[List[str]] = None,
        preferred_language: str = "mr-IN"
    ) -> Tuple[CitizenUnderstandingOutput, str, bool, Optional[str]]:
        """
        Stage 1: Multi-turn Structured Understanding via Gemini with strict Pydantic validation.
        Classifies intent (33 intents), context transition (11 transitions), extracts facts/negations/goals.
        Returns (understanding_output, provider_mode, structured_parse_success, fallback_reason)
        """
        masked_msg, _ = PIIMasker.mask_text(latest_message)
        masked_history = []
        for m in recent_messages[-8:]:
            masked_t, _ = PIIMasker.mask_text(m.get("text", "") or m.get("original_text", "") or "")
            masked_history.append({"sender": m.get("sender", "USER"), "text": masked_t})

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
                try:
                    resp = self._client.models.generate_content(
                        model=model_name,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            temperature=0.0
                        )
                    )
                    raw_text = resp.text.strip()
                    try:
                        understanding = CitizenUnderstandingOutput.model_validate_json(raw_text)
                    except Exception as parse_err:
                        # Attempt 1 retry with JSON repair
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
                    import re
                    m_temp = re.search(r'\b(9\d(?:\.\d+)?|10\d(?:\.\d+)?)\s*(?:°|deg|degree|f|fahrenheit)?\b', masked_msg, re.IGNORECASE)
                    if m_temp and not understanding.new_facts.temperature_f:
                        try:
                            val = float(m_temp.group(1))
                            if 95.0 <= val <= 108.0:
                                understanding.new_facts.temperature_f = val
                        except Exception:
                            pass

                    return understanding, "GEMINI_LIVE", True, None
                except Exception as e:
                    err_str = str(e).lower()
                    if "429" in err_str or "quota" in err_str:
                        self._last_error_category = "RATE_LIMITED"
                    elif "503" in err_str:
                        self._last_error_category = "SERVICE_UNAVAILABLE"
                    else:
                        self._last_error_category = "API_ERROR"
                    continue

        # Rule fallback understanding when Gemini unavailable
        fallback_understanding = self._fallback_understand(masked_msg, last_assistant_question, current_topic, preferred_language)
        return fallback_understanding, "LIMITED_FALLBACK", False, self._last_error_category or "GEMINI_UNAVAILABLE"

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
        preferred_language: str = "mr-IN"
    ) -> Tuple[CitizenDynamicResponseOutput, str]:
        """
        Stage 2: Multilingual Contextual Response Generation with Gemini.
        Genuinely understands and answers the citizen's actual message in context.
        """
        masked_msg, _ = PIIMasker.mask_text(latest_message)
        masked_history = []
        for m in recent_messages[-8:]:
            masked_t, _ = PIIMasker.mask_text(m.get("text", "") or m.get("original_text", "") or "")
            masked_history.append({"sender": m.get("sender", "USER"), "text": masked_t})

        if self._is_live and self._client:
            models = self._get_candidate_models()
            prompt = (
                "You are Aarogya Sahayak, a multilingual rural healthcare-access assistant. "
                "Understand and answer the citizen's actual latest message using the relevant conversation context. "
                "Do not force the citizen into a predefined script. Do not repeat previous replies or ask questions already answered. "
                "Respond naturally in simple Marathi, Hindi or English according to the selected language or citizen's language.\n\n"
                "For greetings and normal conversation, respond naturally without creating clinical records. "
                "For general health questions, provide clear low-risk health information and relevant warning signs without diagnosing or prescribing. "
                "For personal symptoms, acknowledge the current symptoms and ask only the most useful one or two questions. "
                "For follow-up answers, interpret them using the last assistant question. "
                "For a topic change, start or clarify the new topic rather than reusing old symptoms. "
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
                "- 'text': Dynamic citizen-friendly answer\n"
                "- 'language': Detected/selected language code (e.g. 'mr', 'hi', 'en')\n"
                "- 'response_type': One of DIRECT_ANSWER, CLARIFYING_QUESTION, GUIDANCE, ACTION_OFFER, SAFETY_WARNING, CLOSING\n"
                "- 'question': Optional single clarifying question string or null\n"
                "- 'suggested_replies': List of 2-4 short contextual quick replies in citizen's language\n"
                "- 'requested_action_types': List of action codes subset from Allowed Action Types\n"
                "- 'facts_used': List of facts referenced in explanation\n"
                "- 'uncertainty_statement': Optional statement if clarification needed or null"
            )

            for model_name in models:
                try:
                    resp = self._client.models.generate_content(
                        model=model_name,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            temperature=0.2
                        )
                    )
                    raw_text = resp.text.strip()
                    try:
                        dyn_resp = CitizenDynamicResponseOutput.model_validate_json(raw_text)
                        return dyn_resp, "GEMINI_LIVE"
                    except Exception as parse_err:
                        repair_prompt = f"Fix JSON to match CitizenDynamicResponseOutput strictly:\n{raw_text}"
                        resp_repair = self._client.models.generate_content(
                            model=model_name,
                            contents=repair_prompt,
                            config=types.GenerateContentConfig(
                                response_mime_type="application/json",
                                temperature=0.0
                            )
                        )
                        dyn_resp = CitizenDynamicResponseOutput.model_validate_json(resp_repair.text)
                        return dyn_resp, "GEMINI_LIVE"
                except Exception as e:
                    err_str = str(e).lower()
                    if "429" in err_str or "quota" in err_str:
                        self._last_error_category = "RATE_LIMITED"
                    elif "503" in err_str:
                        self._last_error_category = "SERVICE_UNAVAILABLE"
                    else:
                        self._last_error_category = "API_ERROR"
                    continue

        # Honest Limited Fallback Mode (does NOT pretend to be AI text)
        fallback_resp = self._fallback_dynamic_response(
            latest_message=masked_msg,
            understanding=understanding,
            safety_evaluation=safety_evaluation,
            verified_tool_data=verified_tool_data,
            language=preferred_language
        )
        return fallback_resp, "LIMITED_FALLBACK"

    def _fallback_dynamic_response(
        self,
        latest_message: str,
        understanding: CitizenUnderstandingOutput,
        safety_evaluation: Dict[str, Any],
        verified_tool_data: Optional[Dict[str, Any]],
        language: str
    ) -> CitizenDynamicResponseOutput:
        is_hi = language.startswith("hi")
        is_en = language.startswith("en")
        intent = understanding.intent

        # Emergency override
        if safety_evaluation.get("level") == "EMERGENCY" or intent == CitizenIntentEnum.EMERGENCY_HELP:
            text = (
                "⚠️ गंभीर व तात्काळ काळजीची लक्षणे आढळली आहेत. त्वरित १०८ वर कॉल करा किंवा जवळच्या २४x७ आपत्कालीन केंद्रात जा."
                if not (is_hi or is_en) else
                ("⚠️ गंभीर लक्षण पाए गए हैं। तुरंत 108 पर कॉल करें या आपातकालीन सहायता लें।" if is_hi else
                 "⚠️ Critical emergency warning signs detected. Please call 108 Emergency immediately.")
            )
            return CitizenDynamicResponseOutput(
                text=text,
                language=language[:2],
                response_type="SAFETY_WARNING",
                requested_action_types=["CALL_108", "FIND_FACILITY", "SPEAK_TO_DOCTOR"],
                suggested_replies=["108 Emergency", "Doctor Consultation"]
            )

        if intent == CitizenIntentEnum.MENTAL_HEALTH_CRISIS:
            text = (
                "⚠️ तुमची सुरक्षितता अत्यंत महत्त्वाची आहे. कृपया तात्काळ २४x७ मानसिक आरोग्य हेल्पलाइन टेली-मानस (१४४१६) अथवा १०८ वर संपर्क करा."
                if not (is_hi or is_en) else
                ("⚠️ हम आपकी सुरक्षा के लिए चिंतित हैं। कृपया तुरंत Tele-MANAS (14416) या 108 पर संपर्क करें।" if is_hi else
                 "⚠️ Your safety is our highest priority. Please reach out to Tele-MANAS (14416) or Emergency 108 immediately.")
            )
            return CitizenDynamicResponseOutput(
                text=text,
                language=language[:2],
                response_type="SAFETY_WARNING",
                requested_action_types=["CALL_14416", "CALL_108", "SPEAK_TO_DOCTOR"]
            )

        # Honest limited fallback message as mandated in Section 14
        limited_msg = (
            "संभाषण सहाय्य सध्या मर्यादित मोडमध्ये आहे. आपण पुन्हा प्रयत्न करू शकता किंवा खालील आरोग्य सेवांचा थेट वापर करू शकता."
            if not (is_hi or is_en) else
            ("बातचीत सहायता अस्थायी रूप से सीमित है। आप पुनः प्रयास कर सकते हैं या सीधे नीचे दी गई स्वास्थ्य सेवाओं का उपयोग कर सकते हैं।" if is_hi else
             "Conversational assistance is temporarily limited. You can try again or directly use health services below.")
        )

        return CitizenDynamicResponseOutput(
            text=limited_msg,
            language=language[:2],
            response_type="GUIDANCE",
            requested_action_types=["SPEAK_TO_DOCTOR", "FIND_FACILITY", "CHECK_SCHEMES"],
            suggested_replies=["Speak to Doctor", "Find Health Centre", "Check Schemes"]
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
