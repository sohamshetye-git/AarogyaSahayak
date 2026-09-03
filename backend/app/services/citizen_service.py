import uuid
import time
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any
from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

logger = logging.getLogger("aarogya.citizen_service")

from app.models import (
    User, CitizenProfile, HouseholdMember, CitizenChatSession,
    CitizenChatMessage, CitizenNeed, ServiceRequest, Case, Referral,
    CasePriorityEnum, CaseStatusEnum, UserRoleEnum, Consultation, Prescription, InvestigationOrder,
    FollowUp, Notification, Facility, WorkerProfile, AuditLog, utc_now,
    CareHandoff, SharingConsent, ServiceRequestStatusHistory,
    TeleconsultationRequest, TeleconsultationMessage, TeleconsultationStatusHistory,
    DoctorChatThread, DoctorChatMessage
)
from app.schemas.citizen import (
    HouseholdMemberCreateRequest, HouseholdMemberUpdateRequest, StartChatSessionRequest,
    ChatMessageCreateRequest, TranscriptConfirmationRequest,
    UnderstandingConfirmationRequest, CitizenNeedCreateRequest,
    DoctorRequestCreateDTO, AshaRequestCreateDTO, SchemeScreeningRequest,
    FacilitySearchRequest, CitizenHomeSummaryDTO, CitizenTimelineEventDTO,
    HandoffPreviewRequest, ServiceRequestUpdateDTO, ServiceRequestCancelDTO,
    CitizenProfileUpdateRequest
)
from app.safety.emergency_rules import EmergencyRuleEvaluator

class CitizenService:

    @staticmethod
    def get_or_create_default_profile(db: Session, user: Optional[User] = None) -> CitizenProfile:
        if user:
            if user.citizen_profile:
                return user.citizen_profile
            existing = db.query(CitizenProfile).filter(CitizenProfile.user_id == user.id).first()
            if existing:
                return existing
            profile = CitizenProfile(
                user_id=user.id,
                display_name=user.name or "Citizen",
                legal_name=user.name or "Citizen",
                preferred_name=user.name or "Citizen",
                phone=user.phone,
                preferred_language=user.preferred_language or "mr-IN",
                village_name="Kalyanpur"
            )
            db.add(profile)
            db.commit()
            db.refresh(profile)
            return profile

        profile = db.query(CitizenProfile).filter(CitizenProfile.user_id.is_(None)).first()
        if not profile:
            profile = db.query(CitizenProfile).first()
        if not profile:
            profile = CitizenProfile(
                display_name="Sunita Devi",
                age_estimate=28,
                sex="Female",
                preferred_language="mr-IN",
                village_name="Kalyanpur",
                is_pregnant=True,
                gestational_weeks=28
            )
            db.add(profile)
            db.commit()
            db.refresh(profile)

            # Seed a self household member
            self_member = HouseholdMember(
                citizen_id=profile.id,
                full_name=profile.display_name,
                relationship_type="SELF",
                age=28,
                sex="Female",
                is_pregnant=True,
                gestational_weeks=28
            )
            db.add(self_member)
            db.commit()

        return profile


    @staticmethod
    def update_language(db: Session, citizen_id: str, preferred_language: str) -> CitizenProfile:
        profile = db.query(CitizenProfile).filter(CitizenProfile.id == citizen_id).first()
        if not profile:
            raise ValueError("Citizen profile not found")
        
        profile.preferred_language = preferred_language
        profile.language_confirmed_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(profile)
        return profile

    @staticmethod
    def get_home_summary(db: Session, citizen_id: str) -> Dict[str, Any]:
        profile = db.query(CitizenProfile).filter(CitizenProfile.id == citizen_id).first()
        if not profile:
            return {}

        active_case = db.query(Case).filter(
            Case.citizen_id == citizen_id,
            Case.status != CaseStatusEnum.COMPLETED
        ).order_by(Case.created_at.desc()).first()

        active_case_dto = None
        responsible_person = None
        if active_case:
            # Citizen friendly status translation
            status_map = {
                "NEW": "Your concern was received",
                "ASHA_ASSIGNED": "Assigned to ASHA worker",
                "ASHA_ACKNOWLEDGED": "Your ASHA worker accepted the request",
                "CITIZEN_CONTACTED": "ASHA worker contacted you",
                "VISIT_SCHEDULED": "Home visit scheduled",
                "VISIT_IN_PROGRESS": "Home visit in progress",
                "REFERRED_TO_PHC": "Your information was sent to the PHC",
                "DOCTOR_ACKNOWLEDGED": "A Doctor is reviewing your case",
                "PATIENT_ARRIVED": "Arrived at PHC",
                "CONSULTATION_IN_PROGRESS": "In Consultation with Doctor",
                "FOLLOW_UP_REQUIRED": "A follow-up visit is required",
                "COMPLETED": "This care episode is completed"
            }

            active_case_dto = {
                "id": active_case.id,
                "reference": active_case.reference,
                "primary_concern": active_case.primary_concern,
                "status": active_case.status.value,
                "display_status": status_map.get(active_case.status.value, active_case.status.value),
                "next_action": active_case.citizen_guidance_text or "Await update from your healthcare provider",
                "created_at": active_case.created_at.isoformat(),
                "updated_at": active_case.updated_at.isoformat()
            }

            if active_case.assigned_asha_name:
                responsible_person = {
                    "role": "ASHA Worker",
                    "name": active_case.assigned_asha_name,
                    "phone": profile.assigned_asha_id or "9876543210"
                }

        unread_count = db.query(Notification).filter(
            Notification.recipient_user_id == profile.user_id if profile.user_id else False,
            Notification.read == False
        ).count() if profile.user_id else 0

        # Prescriptions
        recent_prescriptions = db.query(Prescription).filter(
            Prescription.citizen_id == citizen_id
        ).order_by(Prescription.created_at.desc()).limit(3).all()

        rx_items = [
            {
                "id": p.id,
                "reference": getattr(p, "reference", p.id),
                "doctor_name": getattr(p, "doctor_name", "Dr. Abhinav Sharma"),
                "diagnosis": getattr(p, "provisional_diagnosis", "Routine consultation"),
                "date": p.created_at.strftime("%Y-%m-%d") if p.created_at else ""
            }
            for p in recent_prescriptions
        ]

        # Followups/Appointments
        upcoming_followups = db.query(FollowUp).filter(
            FollowUp.citizen_id == citizen_id,
            FollowUp.status != "COMPLETED"
        ).order_by(FollowUp.due_at.asc()).limit(3).all()

        appts = [
            {
                "id": f.id,
                "reference": getattr(f, "follow_up_reference", f.id),
                "instructions": f.instructions,
                "due_date": f.due_at.strftime("%Y-%m-%d") if f.due_at else "",
                "status": f.status
            }
            for f in upcoming_followups
        ]

        quick_actions = [
            {"id": "doctor", "label": "Speak to Doctor Now", "icon": "stethoscope", "route": "/citizen/doctor"},
            {"id": "emergency", "label": "Emergency Help", "icon": "alert", "route": "/citizen/emergency"},
            {"id": "asha", "label": "Call/Request ASHA", "icon": "user-check", "route": "/citizen/asha"},
            {"id": "facility", "label": "Find Health Centre", "icon": "map-pin", "route": "/citizen/facilities"},
            {"id": "scheme", "label": "Check Government Scheme", "icon": "file-text", "route": "/citizen/schemes"},
            {"id": "medicines", "label": "My Medicines and Tests", "icon": "pill", "route": "/citizen/medicines"}
        ]

        return {
            "citizen_name": profile.display_name,
            "preferred_language": profile.preferred_language or "mr-IN",
            "unread_notifications_count": unread_count,
            "active_case": active_case_dto,
            "responsible_person": responsible_person,
            "quick_actions": quick_actions,
            "recent_prescriptions": rx_items,
            "upcoming_appointments": appts
        }

    @staticmethod
    def start_chat_session(db: Session, citizen_id: str, req: StartChatSessionRequest) -> CitizenChatSession:
        ref = f"SESS-{int(datetime.now(timezone.utc).timestamp())}-{uuid.uuid4().hex[:6]}"
        session = CitizenChatSession(
            session_reference=ref,
            citizen_id=citizen_id,
            person_affected_id=req.person_affected_id,
            preferred_language=req.preferred_language,
            channel=req.channel,
            current_state="STARTED",
            device_id=req.device_id,
            offline_created=req.offline_created
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        return session

    @staticmethod
    def add_chat_message(db: Session, session_id: str, req: ChatMessageCreateRequest) -> CitizenChatMessage:
        session = db.query(CitizenChatSession).filter(CitizenChatSession.id == session_id).first()
        if not session:
            raise ValueError("Chat session not found")

        # Check idempotency
        if req.idempotency_key:
            existing = db.query(CitizenChatMessage).filter(
                CitizenChatMessage.session_id == session_id,
                CitizenChatMessage.idempotency_key == req.idempotency_key
            ).first()
            if existing:
                return existing

        # Determine sequence
        seq = db.query(CitizenChatMessage).filter(CitizenChatMessage.session_id == session_id).count() + 1

        msg = CitizenChatMessage(
            session_id=session_id,
            sequence_number=seq,
            sender="CITIZEN",
            input_type=req.input_type,
            original_text=req.original_text,
            confirmed_text=req.original_text, # default
            language=req.language,
            message_type="TRANSCRIPT",
            confirmation_status="PENDING",
            in_reply_to_question_id=req.in_reply_to_question_id or session.current_question_id,
            idempotency_key=req.idempotency_key,
            temporary_audio_reference=req.temporary_audio_reference,
            audio_consent_at=utc_now() if req.temporary_audio_reference else None
        )
        db.add(msg)

        session.current_state = "AWAITING_TRANSCRIPT_CONFIRMATION"
        session.last_activity_at = utc_now()
        db.commit()
        db.refresh(msg)
        return msg

    @staticmethod
    def confirm_transcript(db: Session, session_id: str, req: TranscriptConfirmationRequest) -> Dict[str, Any]:
        session = db.query(CitizenChatSession).filter(CitizenChatSession.id == session_id).first()
        if not session:
            raise ValueError("Chat session not found")

        last_msg = db.query(CitizenChatMessage).filter(
            CitizenChatMessage.session_id == session_id,
            CitizenChatMessage.sender == "CITIZEN"
        ).order_by(CitizenChatMessage.sequence_number.desc()).first()

        if last_msg:
            last_msg.confirmed_text = req.confirmed_text
            last_msg.confirmation_status = "CONFIRMED"
            if req.in_reply_to_question_id:
                last_msg.in_reply_to_question_id = req.in_reply_to_question_id

        session.current_state = "PROCESSING"
        session.last_activity_at = utc_now()
        db.commit()

        # Run multi-turn conversation intelligence engine
        return CitizenService.process_conversational_turn(db, session_id, req.confirmed_text)

    @staticmethod
    def process_conversational_turn(db: Session, session_id: str, confirmed_text: str) -> Dict[str, Any]:
        import json
        from app.services.conversation_intelligence import (
            ConversationEngine, MessagePurposeEnum, UIBlockType, UIBlock, QuestionManager, SafetyEvaluationResult
        )
        from app.ai.providers.gemini_service import gemini_service
        from app.ai.contracts.schemas import CitizenIntentEnum, ContextTransitionEnum, CitizenUnderstandingOutput, CitizenDynamicResponseOutput
        from app.models import CitizenConversationState

        session = db.query(CitizenChatSession).filter(CitizenChatSession.id == session_id).first()
        if not session:
            raise ValueError("Chat session not found")

        turn_start_time = time.time()
        request_id = f"req-{uuid.uuid4().hex[:8]}"

        # Load session conversation state
        conv_state = db.query(CitizenConversationState).filter(CitizenConversationState.session_id == session_id).first()
        if not conv_state:
            conv_state = CitizenConversationState(
                session_id=session_id,
                current_topic=session.current_topic or "GENERAL",
                confirmed_facts={},
                negated_facts=[],
                uncertain_facts=[],
                asked_question_keys=[]
            )
            db.add(conv_state)
            db.flush()

        msgs = db.query(CitizenChatMessage).filter(
            CitizenChatMessage.session_id == session_id
        ).order_by(CitizenChatMessage.sequence_number.asc()).all()

        profile = db.query(CitizenProfile).filter(CitizenProfile.id == session.citizen_id).first()
        person_name = profile.display_name if profile else "Self"
        if session.person_affected_id:
            pm = db.query(HouseholdMember).filter(HouseholdMember.id == session.person_affected_id).first()
            if pm:
                person_name = f"{pm.full_name} ({pm.relationship_type})"

        recent_msgs_list = [
            {"sender": m.sender, "text": m.confirmed_text or m.original_text or ""}
            for m in msgs[-12:]
        ]

        # Stage 1: Structured Understanding via Gemini / Rule Fallback
        understanding, under_mode, parse_ok, fallback_reason, req_model_u, succ_model_u, err_status_u = gemini_service.understand_citizen_turn(
            latest_message=confirmed_text,
            recent_messages=recent_msgs_list,
            current_topic=conv_state.current_topic,
            last_assistant_question=conv_state.last_assistant_question,
            confirmed_facts=conv_state.confirmed_facts or {},
            negated_facts=conv_state.negated_facts or [],
            preferred_language=session.preferred_language or "mr-IN",
            request_id=request_id
        )

        intent = understanding.intent
        context_trans = understanding.context_transition

        # Stage 2: Merge Facts Safely based on context transition & persona
        confirmed_facts = dict(conv_state.confirmed_facts or {})
        negated_facts = list(conv_state.negated_facts or [])
        uncertain_facts = list(conv_state.uncertain_facts or [])
        symptoms_list = list(confirmed_facts.get("symptoms", []))
        vitals = dict(confirmed_facts.get("vitals", {}))
        duration = confirmed_facts.get("duration", "2 days")

        # Handle beneficiary persona correction (e.g. "Not me, my child")
        if understanding.new_facts.person_reference == "CHILD" or intent == CitizenIntentEnum.CORRECTION:
            child_member = db.query(HouseholdMember).filter(
                HouseholdMember.citizen_id == session.citizen_id,
                HouseholdMember.relationship_type == "CHILD"
            ).first()
            if child_member:
                session.person_affected_id = child_member.id
                person_name = f"{child_member.full_name} (Child)"

        # Handle topic transition
        if context_trans == ContextTransitionEnum.NEW_TOPIC:
            if intent in [CitizenIntentEnum.NEW_HEALTH_CONCERN, CitizenIntentEnum.HEALTH_INFORMATION]:
                # If citizen shifts to a distinctly new health concern, reset previous symptoms to avoid cross-contamination
                conv_state.previous_topic = conv_state.current_topic
                conv_state.current_topic = ", ".join(understanding.new_facts.symptoms) if understanding.new_facts.symptoms else "Health Concern"
                symptoms_list = list(understanding.new_facts.symptoms)
                negated_facts = list(understanding.new_facts.negated_symptoms)
            elif intent in [CitizenIntentEnum.SCHEME_INFORMATION, CitizenIntentEnum.SCHEME_ELIGIBILITY, CitizenIntentEnum.FACILITY_SEARCH]:
                conv_state.previous_topic = conv_state.current_topic
                conv_state.current_topic = intent.value

        # Extract new confirmed symptoms from Gemini understanding
        for s in understanding.new_facts.symptoms:
            if s not in symptoms_list:
                symptoms_list.append(s)

        # Deterministic emergency symptom booster: Ensure Marathi/Hindi/English chest pain, breathlessness, etc. are always captured
        raw_lower = confirmed_text.lower()
        if any(w in raw_lower for w in ["chest pain", "छातीत", "सीने में", "दुखत", "छातीत दुखत"]) and "Chest Pain" not in symptoms_list:
            symptoms_list.append("Chest Pain")
        if any(w in raw_lower for w in ["breath", "दम", "सांस", "shortness", "श्वास", "धाप", "त्रास"]) and "Breathing Difficulty" not in symptoms_list:
            symptoms_list.append("Breathing Difficulty")
        if any(w in raw_lower for w in ["fever", "ताप", "बुखार"]) and "Fever" not in symptoms_list:
            symptoms_list.append("Fever")
        if any(w in raw_lower for w in ["headache", "डोकेदुखी", "सिरदर्द"]) and "Headache" not in symptoms_list:
            symptoms_list.append("Headache")

        # Extract negated symptoms
        for ns in understanding.new_facts.negated_symptoms:
            if ns not in negated_facts:
                negated_facts.append(ns)
            if ns in symptoms_list:
                symptoms_list.remove(ns)

        # Extract temperature
        if understanding.new_facts.temperature_f:
            vitals["temperature_f"] = understanding.new_facts.temperature_f
        if understanding.new_facts.duration:
            duration = understanding.new_facts.duration

        # Stage 3: Deterministic Emergency Rule Evaluation (Authoritative)
        temp_c = None
        if "temperature_f" in vitals and vitals["temperature_f"]:
            temp_c = (vitals["temperature_f"] - 32) * 5 / 9

        priority, triggered, reason, guidance = EmergencyRuleEvaluator.evaluate(
            symptoms=[s.lower() for s in symptoms_list],
            is_pregnant=profile.is_pregnant if profile else False,
            gestational_weeks=profile.gestational_weeks if profile else None,
            temperature_c=temp_c
        )
        safety_level = "EMERGENCY" if (priority == CasePriorityEnum.URGENT or intent in [CitizenIntentEnum.EMERGENCY_HELP, CitizenIntentEnum.MENTAL_HEALTH_CRISIS]) else ("HIGH_RISK" if priority == CasePriorityEnum.HIGH else "NORMAL")
        if intent == CitizenIntentEnum.MENTAL_HEALTH_CRISIS:
            reason = reason or "Crisis warning: thoughts of self-harm detected."
            triggered = True

        confirmed_facts["symptoms"] = symptoms_list
        confirmed_facts["duration"] = duration
        confirmed_facts["vitals"] = vitals
        confirmed_facts["safety_level"] = safety_level

        # Stage 4: Authoritative Backend Tools based on intent
        verified_tool_data: Optional[Dict[str, Any]] = None
        need = None
        if session.linked_need_id:
            need = db.query(CitizenNeed).filter(CitizenNeed.id == session.linked_need_id).first()
        if not need:
            need = db.query(CitizenNeed).filter(CitizenNeed.session_id == session_id).first()

        if intent in [CitizenIntentEnum.NEW_HEALTH_CONCERN, CitizenIntentEnum.SYMPTOM_UPDATE, CitizenIntentEnum.SELF_CARE_GUIDANCE_REQUEST]:
            if not need:
                need_ref = f"ND-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:4]}"
                need = CitizenNeed(
                    need_reference=need_ref,
                    session_id=session_id,
                    citizen_id=session.citizen_id,
                    person_affected_id=session.person_affected_id,
                    primary_intent="HEALTH_CONCERN",
                    confirmed_summary=", ".join(symptoms_list) if symptoms_list else confirmed_text,
                    structured_facts=confirmed_facts,
                    facts_version=1,
                    urgency=priority.value,
                    status="CONFIRMED"
                )
                db.add(need)
                db.flush()
                session.linked_need_id = need.id
                conv_state.active_need_id = need.id
            else:
                need.structured_facts = confirmed_facts
                need.facts_version = (need.facts_version or 1) + 1
                need.urgency = priority.value
                need.confirmed_summary = ", ".join(symptoms_list) if symptoms_list else need.confirmed_summary

        elif intent in [CitizenIntentEnum.SCHEME_INFORMATION, CitizenIntentEnum.SCHEME_ELIGIBILITY]:
            verified_tool_data = {
                "available_schemes": [
                    {"code": "PM-JAY", "name": "Ayushman Bharat PM-JAY", "coverage": "Up to ₹5,00,000 cashless secondary/tertiary care"},
                    {"code": "PMMVY", "name": "Pradhan Mantri Matru Vandana Yojana", "coverage": "Maternity financial assistance"},
                    {"code": "JSY", "name": "Janani Suraksha Yojana", "coverage": "Institutional delivery incentive"},
                    {"code": "RBSK", "name": "Rashtriya Bal Swasthya Karyakram", "coverage": "Child health screening and early intervention"}
                ]
            }

        elif intent == CitizenIntentEnum.FACILITY_SEARCH:
            verified_tool_data = {
                "facilities": [
                    {"id": "fac-2026-002", "name": "Kalyanpur Primary Health Centre (PHC)", "distance_km": 2.8, "services": ["General OPD", "24x7 Delivery", "Basic Lab"]},
                    {"id": "fac-2026-003", "name": "Kalyanpur Community Health Centre (CHC)", "distance_km": 8.5, "services": ["Emergency", "Inpatient", "Surgery"]}
                ]
            }

        elif intent in [CitizenIntentEnum.FOLLOWUP_STATUS_QUERY, CitizenIntentEnum.CASE_STATUS_QUERY, CitizenIntentEnum.PRESCRIPTION_QUERY]:
            followups = db.query(FollowUp).filter(FollowUp.citizen_id == session.citizen_id).order_by(FollowUp.due_at.asc()).all()
            due_str = followups[0].due_at.strftime("%d %b %Y") if followups and followups[0].due_at else "Upcoming Week"
            verified_tool_data = {"next_followup_due": due_str, "status": "SCHEDULED_WITH_DOCTOR"}

        elif intent == CitizenIntentEnum.DOCTOR_REQUEST:
            # Check or create single idempotent ServiceRequest
            existing_sr = db.query(ServiceRequest).filter(
                ServiceRequest.citizen_id == session.citizen_id,
                ServiceRequest.request_type == "DOCTOR_CONSULTATION",
                ServiceRequest.status == "PENDING"
            ).first()
            if not existing_sr:
                existing_sr = ServiceRequest(
                    request_reference=f"SR-DOC-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:4]}",
                    citizen_id=session.citizen_id,
                    need_id=need.id if need else None,
                    request_type="DOCTOR_CONSULTATION",
                    status="PENDING",
                    priority="HIGH" if safety_level == "EMERGENCY" else "ROUTINE",
                    details={"symptoms": symptoms_list}
                )
                db.add(existing_sr)
                db.flush()
            verified_tool_data = {"service_request_id": existing_sr.id, "reference": existing_sr.request_reference, "status": existing_sr.status}

        elif intent == CitizenIntentEnum.ASHA_REQUEST:
            existing_sr = db.query(ServiceRequest).filter(
                ServiceRequest.citizen_id == session.citizen_id,
                ServiceRequest.request_type == "ASHA_ASSISTANCE",
                ServiceRequest.status == "PENDING"
            ).first()
            if not existing_sr:
                existing_sr = ServiceRequest(
                    request_reference=f"SR-ASHA-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:4]}",
                    citizen_id=session.citizen_id,
                    need_id=need.id if need else None,
                    request_type="ASHA_ASSISTANCE",
                    status="PENDING",
                    priority="ROUTINE",
                    details={"symptoms": symptoms_list}
                )
                db.add(existing_sr)
                db.flush()
            verified_tool_data = {"service_request_id": existing_sr.id, "reference": existing_sr.request_reference, "assigned_asha": "Sita Patel (Kalyanpur PHC)"}

        # Stage 5: Dynamic Gemini Response Generation
        allowed_actions = [a["action"] for a in ConversationEngine.build_dynamic_actions(intent, session.preferred_language or "mr-IN")]
        dyn_response, resp_mode, req_model_r, succ_model_r, err_status_r = gemini_service.generate_dynamic_response(
            latest_message=confirmed_text,
            recent_messages=recent_msgs_list,
            understanding=understanding,
            confirmed_facts=confirmed_facts,
            negated_facts=negated_facts,
            last_assistant_question=conv_state.last_assistant_question,
            safety_evaluation={"level": safety_level, "reason": reason, "triggered": triggered},
            verified_tool_data=verified_tool_data,
            allowed_action_types=allowed_actions,
            preferred_language=session.preferred_language or "mr-IN",
            request_id=request_id
        )

        final_text = dyn_response.text
        suggested_replies = dyn_response.suggested_replies or []
        provider_mode = under_mode if under_mode == "GEMINI_LIVE" else resp_mode
        fallback_used = provider_mode != "GEMINI_LIVE"
        successful_model = succ_model_r or succ_model_u

        # Construct intent-tailored UI blocks
        blocks: List[Dict[str, Any]] = []
        action_choices = ConversationEngine.build_dynamic_actions(intent, session.preferred_language or "mr-IN")

        if safety_level == "EMERGENCY" or intent in [CitizenIntentEnum.EMERGENCY_HELP, CitizenIntentEnum.MENTAL_HEALTH_CRISIS]:
            blocks.append({
                "type": UIBlockType.SAFETY_ALERT.value,
                "block_type": UIBlockType.SAFETY_ALERT.value,
                "title": "Emergency Alert (108)" if intent == CitizenIntentEnum.EMERGENCY_HELP else "Crisis Support (14416)",
                "content": final_text,
                "data": {"level": safety_level, "reason": reason, "symptoms": symptoms_list}
            })
        else:
            blocks.append({
                "type": UIBlockType.TEXT.value,
                "block_type": UIBlockType.TEXT.value,
                "content": final_text,
                "text": final_text
            })

        if dyn_response.question:
            blocks.append({
                "type": UIBlockType.CLARIFYING_QUESTION.value,
                "block_type": UIBlockType.CLARIFYING_QUESTION.value,
                "title": "Clarification",
                "text": dyn_response.question,
                "content": dyn_response.question,
                "question_id": f"q_{intent.value.lower()}"
            })
            conv_state.last_assistant_question = dyn_response.question
            session.last_assistant_question = dyn_response.question
            session.awaiting_answer = True
            session.current_question_id = f"q_{intent.value.lower()}"
        else:
            session.awaiting_answer = False
            session.current_question_id = None
            conv_state.last_assistant_question = None

        if action_choices:
            blocks.append({
                "type": UIBlockType.ACTION_CHOICES.value,
                "block_type": UIBlockType.ACTION_CHOICES.value,
                "actions": action_choices
            })

        all_actions = [a for b in blocks if b.get("actions") for a in b.get("actions", [])]

        # Stage 6: Update Conversation State & Session
        conv_state.confirmed_facts = confirmed_facts
        conv_state.negated_facts = negated_facts
        conv_state.uncertain_facts = uncertain_facts
        conv_state.last_intent = intent.value
        conv_state.context_transition = context_trans.value
        conv_state.compact_summary = f"Topic: {conv_state.current_topic}. Symptoms: {', '.join(symptoms_list)}. Negated: {', '.join(negated_facts)}"

        session.current_topic = conv_state.current_topic
        session.previous_topic = conv_state.previous_topic
        session.last_intent = intent.value
        session.context_transition = context_trans.value
        session.context_state = {
            "symptoms": symptoms_list,
            "negated": negated_facts,
            "vitals": vitals,
            "duration": duration,
            "safety_level": safety_level,
            "last_intent": intent.value
        }

        # Stage 7: Persist Assistant Message
        assistant_msg = CitizenChatMessage(
            session_id=session_id,
            sequence_number=len(msgs) + 1,
            sender="ASSISTANT",
            input_type="SYSTEM",
            original_text=final_text,
            confirmed_text=final_text,
            language=session.preferred_language,
            message_type="RESPONSE",
            intent_classification=intent.value,
            structured_payload={
                "purpose": intent.value,
                "blocks": blocks,
                "understanding": {
                    "intent": intent.value,
                    "context_transition": context_trans.value,
                    "confidence": understanding.confidence,
                    "person": person_name,
                    "symptoms": symptoms_list,
                    "negated_symptoms": negated_facts
                },
                "safety": {
                    "level": safety_level,
                    "reason": reason,
                    "triggered_rules": ["EMERGENCY-RULE-01"] if triggered else []
                },
                "actions": all_actions
            }
        )
        db.add(assistant_msg)
        session.current_state = "AWAITING_ACTION_SELECTION" if all_actions else "ACTIVE"
        session.last_activity_at = utc_now()
        db.commit()

        turn_latency_ms = round((time.time() - turn_start_time) * 1000, 2)

        # Structured Development Diagnostic Telemetry (Zero PII, Zero credentials)
        telemetry = {
            "request_id": request_id,
            "session_id": session.id,
            "provider": "GEMINI",
            "requested_model": req_model_r or req_model_u or settings.GEMINI_MODEL,
            "successful_model": successful_model,
            "provider_mode": provider_mode,
            "http_status": 200 if provider_mode == "GEMINI_LIVE" else (err_status_r or err_status_u or 500),
            "fallback_reason": fallback_reason,
            "latency_ms": turn_latency_ms,
            "intent": intent.value,
            "context_transition": context_trans.value,
            "structured_parse_success": parse_ok,
            "response_strategy": dyn_response.response_type,
            "active_need_id": need.id if need else None
        }
        logger.info(f"[CITIZEN_CONVERSATION_TELEMETRY] {json.dumps(telemetry)}")

        return {
            "request_id": request_id,
            "session_id": session.id,
            "message_id": assistant_msg.id,
            "state": session.current_state,
            "language": session.preferred_language,
            "purpose": intent.value,
            "text": final_text,
            "message": final_text,
            "assistant_message": {
                "text": final_text,
                "language": session.preferred_language,
                "response_type": dyn_response.response_type
            },
            "blocks": blocks,
            "understanding": {
                "intent": intent.value,
                "context_transition": context_trans.value,
                "confidence": understanding.confidence,
                "person": person_name,
                "symptoms": symptoms_list,
                "negated_symptoms": negated_facts,
                "duration": duration,
                "vitals": vitals,
                "confirmed_facts": confirmed_facts,
                "negated_facts": negated_facts
            },
            "safety": {
                "level": safety_level,
                "priority": "URGENT" if safety_level == "EMERGENCY" else ("HIGH" if safety_level == "HIGH_RISK" else "ROUTINE"),
                "triggered_rules": ["EMERGENCY-RULE-01"] if triggered else [],
                "reason": reason
            },
            "active_need_id": need.id if need else None,
            "case_id": session.linked_case_id,
            "need_version": need.facts_version if need else 1,
            "actions": all_actions,
            "suggested_replies": suggested_replies,
            "provider": {
                "name": "GEMINI",
                "mode": provider_mode,
                "requested_model": req_model_r or req_model_u or settings.GEMINI_MODEL,
                "successful_model": successful_model,
                "fallback_used": fallback_used,
                "fallback_reason": fallback_reason,
                "latency_ms": turn_latency_ms
            }
        }

    @staticmethod
    def get_active_chat_session(db: Session, citizen_id: str) -> Optional[Dict[str, Any]]:
        session = db.query(CitizenChatSession).filter(
            CitizenChatSession.citizen_id == citizen_id,
            CitizenChatSession.status == "ACTIVE"
        ).order_by(CitizenChatSession.last_activity_at.desc()).first()
        if not session:
            return None
        return CitizenService.get_chat_history(db, session.id)

    @staticmethod
    def get_chat_history(db: Session, session_id: str) -> Dict[str, Any]:
        session = db.query(CitizenChatSession).filter(CitizenChatSession.id == session_id).first()
        if not session:
            raise ValueError("Chat session not found")

        msgs = db.query(CitizenChatMessage).filter(
            CitizenChatMessage.session_id == session_id
        ).order_by(CitizenChatMessage.sequence_number.asc()).all()

        return {
            "session_id": session.id,
            "session_reference": session.session_reference,
            "current_state": session.current_state,
            "preferred_language": session.preferred_language,
            "status": session.status,
            "last_activity_at": session.last_activity_at.isoformat() if session.last_activity_at else None,
            "messages": [
                {
                    "id": m.id,
                    "sequence_number": m.sequence_number,
                    "sender": m.sender,
                    "input_type": m.input_type,
                    "original_text": m.original_text,
                    "confirmed_text": m.confirmed_text,
                    "language": m.language,
                    "message_type": m.message_type,
                    "structured_payload": m.structured_payload,
                    "confirmation_status": m.confirmation_status,
                    "created_at": m.created_at.isoformat() if m.created_at else None
                }
                for m in msgs
            ]
        }

    @staticmethod
    def transcribe_citizen_voice(audio_base64: Optional[str], language: str = "mr-IN") -> Dict[str, Any]:
        if not audio_base64 or len(audio_base64.strip()) == 0:
            return {
                "transcript": "",
                "detected_language": language,
                "confidence": 0.0,
                "provider": "NONE",
                "status": "NO_AUDIO",
                "error": "No audio content provided."
            }

        import base64
        import tempfile
        import os
        from app.ai.providers.sarvam_service import sarvam_voice_provider
        from app.ai.providers.gemini_service import gemini_service

        temp_file_path = None
        try:
            audio_bytes = base64.b64decode(audio_base64)
            if len(audio_bytes) < 32:
                return {
                    "transcript": "",
                    "detected_language": language,
                    "confidence": 0.0,
                    "provider": "NONE",
                    "status": "EMPTY_AUDIO",
                    "error": "Audio recording contains no valid sound data."
                }

            with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as temp_file:
                temp_file.write(audio_bytes)
                temp_file_path = temp_file.name

            # 1. Try Sarvam Voice STT if enabled and key present
            if sarvam_voice_provider.enabled and sarvam_voice_provider.api_key:
                try:
                    res = sarvam_voice_provider.transcribe_audio(temp_file_path, language=language)
                    if res.get("status") == "LIVE_VERIFIED" and res.get("transcript"):
                        return {
                            "transcript": res["transcript"],
                            "detected_language": res.get("language_code", language),
                            "confidence": 0.95,
                            "provider": "SARVAM_LIVE",
                            "status": "SUCCESS"
                        }
                except Exception as e:
                    import logging
                    logging.getLogger("citizen-voice").warning(f"Sarvam STT failed: {e}")

            # 2. Return provider unavailable without hardcoding fake text
            return {
                "transcript": "",
                "detected_language": language,
                "confidence": 0.0,
                "provider": "BACKEND_UNAVAILABLE",
                "status": "PROVIDER_UNAVAILABLE",
                "message": "Live STT service unavailable. Please use browser speech recognition or type your message."
            }
        except Exception as err:
            return {
                "transcript": "",
                "detected_language": language,
                "confidence": 0.0,
                "provider": "ERROR",
                "status": "FAILED",
                "error": str(err)
            }
        finally:
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.remove(temp_file_path)
                except Exception:
                    pass

    @staticmethod
    def process_understanding_and_safety(db: Session, session_id: str) -> Dict[str, Any]:
        """Backward compatible delegator to process_conversational_turn."""
        last_msg = db.query(CitizenChatMessage).filter(
            CitizenChatMessage.session_id == session_id,
            CitizenChatMessage.sender == "CITIZEN"
        ).order_by(CitizenChatMessage.sequence_number.desc()).first()

        text = last_msg.confirmed_text or last_msg.original_text if last_msg else ""
        return CitizenService.process_conversational_turn(db, session_id, text)

    @staticmethod
    def create_citizen_need(db: Session, citizen_id: str, req: CitizenNeedCreateRequest) -> CitizenNeed:
        ref = f"NEED-{int(datetime.now(timezone.utc).timestamp())}-{uuid.uuid4().hex[:6]}"
        need = CitizenNeed(
            need_reference=ref,
            session_id=req.session_id,
            citizen_id=citizen_id,
            person_affected_id=req.person_affected_id,
            primary_intent=req.primary_intent,
            secondary_intents=req.secondary_intents,
            requested_service=req.requested_service,
            detected_language=req.detected_language,
            confirmed_summary=req.confirmed_summary,
            location=req.location,
            special_context=req.special_context,
            urgency=req.urgency,
            status="CONFIRMED"
        )
        db.add(need)
        db.commit()
        db.refresh(need)
        return need

    @staticmethod
    def preview_handoff_packet(db: Session, citizen_id: str, req: HandoffPreviewRequest) -> Dict[str, Any]:
        profile = db.query(CitizenProfile).filter(CitizenProfile.id == citizen_id).first()
        if not profile:
            raise ValueError("Citizen profile not found")

        # Resolve Beneficiary
        beneficiary_id = req.beneficiary_id
        beneficiary_name = profile.display_name
        age = profile.age_estimate or 28
        gender = profile.sex or "FEMALE"
        is_pregnant = profile.is_pregnant
        gestational_weeks = profile.gestational_weeks
        chronic_conditions = list(profile.chronic_conditions or [])

        if beneficiary_id:
            hm = db.query(HouseholdMember).filter(HouseholdMember.id == beneficiary_id, HouseholdMember.citizen_id == citizen_id).first()
            if hm:
                beneficiary_name = f"{hm.full_name} ({hm.relationship_type})"
                age = hm.age or age
                gender = hm.sex or gender
                is_pregnant = hm.is_pregnant
                gestational_weeks = hm.gestational_weeks
                chronic_conditions = list(hm.chronic_conditions or [])

        # Retrieve facts from active session or need
        session = None
        if req.session_id:
            session = db.query(CitizenChatSession).filter(
                CitizenChatSession.id == req.session_id,
                CitizenChatSession.citizen_id == citizen_id
            ).first()
        
        need = None
        if req.need_id:
            need = db.query(CitizenNeed).filter(
                CitizenNeed.id == req.need_id,
                CitizenNeed.citizen_id == citizen_id
            ).first()
        elif session and session.linked_need_id:
            need = db.query(CitizenNeed).filter(
                CitizenNeed.id == session.linked_need_id,
                CitizenNeed.citizen_id == citizen_id
            ).first()
        elif session:
            # Look for need specifically associated with this session
            need = db.query(CitizenNeed).filter(
                CitizenNeed.session_id == session.id,
                CitizenNeed.citizen_id == citizen_id
            ).order_by(CitizenNeed.created_at.desc()).first()

        confirmed_symptoms = []
        negated_symptoms = []
        vitals_list = []
        duration_val = 2.0
        duration_unit = "DAYS"
        missing_info = []

        # Also extract any symptoms directly from the session context state if need is not yet committed
        session_facts = (session.context_state or {}) if session else {}
        facts = (need.structured_facts or {}) if need else session_facts

        # Combine facts symptoms with any explicit symptoms passed in request
        s_list = []
        if getattr(req, "symptoms", None):
            s_list.extend(req.symptoms)
        if facts.get("symptoms"):
            s_list.extend(facts.get("symptoms", []))

        # Clean whitespace and deduplicate case-insensitively
        seen_symptom_keys = set()
        for s in s_list:
            if not s or not isinstance(s, str):
                continue
            clean_s = " ".join(s.strip().split())
            if not clean_s:
                continue
            lower_key = clean_s.lower()
            if lower_key in seen_symptom_keys:
                continue
            seen_symptom_keys.add(lower_key)
            display_str = clean_s.title()
            code_str = clean_s.upper().replace(" ", "_")
            confirmed_symptoms.append({
                "code": code_str,
                "display": display_str,
                "status": "CONFIRMED",
                "source": "CITIZEN_REPORTED"
            })
        
        neg_list = facts.get("negated_symptoms", []) or facts.get("negated", []) or []
        for ns in neg_list:
            if ns and isinstance(ns, str):
                clean_ns = " ".join(ns.strip().split())
                if clean_ns and clean_ns.lower() not in seen_symptom_keys:
                    negated_symptoms.append(clean_ns.title())
        
        v_dict = facts.get("vitals", {}) or {}
        if "temperature_f" in v_dict and v_dict["temperature_f"]:
            vitals_list.append({"type": "TEMPERATURE", "value": v_dict["temperature_f"], "unit": "°F"})
        else:
            missing_info.append("measured_temperature")

        dur_str = facts.get("duration", "2 days")
        import re
        m = re.search(r'(\d+)', str(dur_str))
        if m:
            duration_val = float(m.group(1))

        # Explicit chief concern handling
        passed_concern = getattr(req, "chief_concern", None)
        if passed_concern and isinstance(passed_concern, str) and passed_concern.strip():
            chief_concern = " ".join(passed_concern.strip().split())
        elif need and need.confirmed_summary and need.confirmed_summary.strip():
            chief_concern = " ".join(need.confirmed_summary.strip().split())
        elif confirmed_symptoms:
            chief_concern = confirmed_symptoms[0]["display"]
        else:
            chief_concern = "General health checkup / care guidance"

        # Populate chief concern and confirmed symptoms
        if not confirmed_symptoms:
            confirmed_symptoms.append({
                "code": "HEALTH_CONCERN",
                "display": chief_concern,
                "status": "CONFIRMED",
                "source": "CITIZEN_REPORTED"
            })

        # Deterministic Emergency Rules Evaluation
        temp_c = None
        for v in vitals_list:
            if v["type"] == "TEMPERATURE" and v["value"]:
                temp_c = (float(v["value"]) - 32) * 5 / 9

        # Evaluate triage priority using all confirmed symptoms + chief concern
        eval_symptoms = [s["display"].lower() for s in confirmed_symptoms]
        if chief_concern and chief_concern.lower() not in eval_symptoms:
            eval_symptoms.append(chief_concern.lower())

        priority, triggered, reason, guidance = EmergencyRuleEvaluator.evaluate(
            symptoms=eval_symptoms,
            is_pregnant=is_pregnant,
            gestational_weeks=gestational_weeks,
            temperature_c=temp_c
        )
        citizen_summary = f"{beneficiary_name} reports {chief_concern} since {int(duration_val)} {duration_unit.lower()}."
        if negated_symptoms:
            citizen_summary += f" Explicitly denied: {', '.join(negated_symptoms)}."

        handoff_packet = {
            "handoff_id": f"hnd-{uuid.uuid4().hex[:12]}",
            "citizen_id": citizen_id,
            "beneficiary_id": beneficiary_id,
            "beneficiary_name": beneficiary_name,
            "chat_session_id": session.id if session else None,
            "citizen_need_id": need.id if need else None,
            "case_id": session.linked_case_id if session else None,
            "request_type": req.request_type,
            "requested_channel": req.requested_channel or "CALLBACK",
            "preferred_language": profile.preferred_language or "mr-IN",
            "citizen_summary": citizen_summary,
            "chief_concern": chief_concern,
            "symptoms": confirmed_symptoms,
            "duration": {
                "value": duration_val,
                "unit": duration_unit,
                "status": "CONFIRMED"
            },
            "severity": None,
            "vitals": vitals_list,
            "associated_symptoms": [],
            "negated_symptoms": negated_symptoms,
            "medications_reported": [],
            "allergies_reported": list(profile.allergies or []),
            "relevant_context": {
                "age": age,
                "gender": gender,
                "pregnancy_status": is_pregnant,
                "gestational_weeks": gestational_weeks,
                "chronic_conditions": chronic_conditions
            },
            "safety": {
                "priority": priority.value,
                "triggered_rule_ids": ["EMERGENCY-RULE-01"] if triggered else [],
                "citizen_message": guidance,
                "evaluated_at": utc_now().isoformat()
            },
            "location": {
                "village": profile.village_name or "Kalyanpur",
                "pincode": profile.pincode or "415001",
                "landmark": None,
                "latitude": None,
                "longitude": None
            },
            "citizen_question": "What should I do?",
            "missing_information": missing_info,
            "sharing_scope": {
                "share_structured_summary": True,
                "share_recent_messages": False,
                "share_profile": True,
                "share_location": True,
                "share_existing_health_records": False
            },
            "consent_id": None,
            "created_at": utc_now().isoformat(),
            "version": 1
        }
        return handoff_packet

    @staticmethod
    def create_doctor_request(db: Session, citizen_id: str, req: DoctorRequestCreateDTO) -> Dict[str, Any]:
        # Idempotency / Duplicate Request Check
        if req.idempotency_key:
            existing = db.query(ServiceRequest).filter(ServiceRequest.idempotency_key == req.idempotency_key).first()
            if existing:
                thread = db.query(DoctorChatThread).filter(DoctorChatThread.service_request_id == existing.id).first()
                conv_id = thread.id if thread else existing.id
                return {
                    "reused_existing_request": True,
                    "id": existing.id,
                    "service_request_id": existing.id,
                    "request_id": existing.id,
                    "reference": existing.request_reference,
                    "request_reference": existing.request_reference,
                    "conversation_id": conv_id,
                    "citizen_id": existing.citizen_id or citizen_id,
                    "assigned_doctor_id": existing.assigned_user_id,
                    "channel": existing.requested_channel or "CHAT",
                    "requested_channel": existing.requested_channel or "CHAT",
                    "status": existing.status,
                    "case_id": existing.case_id,
                    "case_reference": existing.case.reference if existing.case else None,
                    "priority": existing.priority,
                    "assigned_facility": "Kalyanpur Primary Health Centre (PHC)",
                    "message": "Doctor consultation request already submitted (Idempotent)",
                    "created_at": existing.created_at.isoformat()
                }

        # Check if an equivalent active Doctor request already exists for this citizen/beneficiary/need
        target_need_id = req.citizen_need_id or req.need_id
        if target_need_id:
            active_dup = db.query(ServiceRequest).filter(
                ServiceRequest.citizen_id == citizen_id,
                ServiceRequest.request_type == "DOCTOR_CONSULTATION",
                ServiceRequest.status.in_(["WAITING_FOR_DOCTOR", "PENDING", "SUBMITTED", "DOCTOR_ACCEPTED", "IN_CONSULTATION"]),
                (ServiceRequest.citizen_need_id == target_need_id) | (ServiceRequest.need_id == target_need_id)
            ).first()
            if active_dup:
                thread = db.query(DoctorChatThread).filter(DoctorChatThread.service_request_id == active_dup.id).first()
                conv_id = thread.id if thread else active_dup.id
                return {
                    "reused_existing_request": True,
                    "id": active_dup.id,
                    "service_request_id": active_dup.id,
                    "request_id": active_dup.id,
                    "reference": active_dup.request_reference,
                    "request_reference": active_dup.request_reference,
                    "conversation_id": conv_id,
                    "citizen_id": active_dup.citizen_id or citizen_id,
                    "assigned_doctor_id": active_dup.assigned_user_id,
                    "channel": active_dup.requested_channel or "CHAT",
                    "requested_channel": active_dup.requested_channel or "CHAT",
                    "status": active_dup.status,
                    "case_id": active_dup.case_id,
                    "case_reference": active_dup.case.reference if active_dup.case else None,
                    "priority": active_dup.priority,
                    "assigned_facility": "Kalyanpur Primary Health Centre (PHC)",
                    "message": "Active doctor request already exists for this concern",
                    "created_at": active_dup.created_at.isoformat()
                }

        profile = db.query(CitizenProfile).filter(CitizenProfile.id == citizen_id).first()
        if not profile:
            raise ValueError("Citizen profile not found")

        # 1. Search or create compatible Case for same health need
        case = None
        if req.case_id:
            case = db.query(Case).filter(Case.id == req.case_id).first()
        
        # Check if active compatible case already exists for this citizen / need
        if not case and req.need_id:
            need_obj = db.query(CitizenNeed).filter(CitizenNeed.id == req.need_id).first()
            if need_obj and need_obj.session_id:
                sess = db.query(CitizenChatSession).filter(CitizenChatSession.id == need_obj.session_id).first()
        # Validate channel for new citizen doctor requests
        requested_channel_val = (req.channel or "CALLBACK").upper()
        if requested_channel_val in ["AUDIO", "VIDEO"]:
            raise HTTPException(
                status_code=400,
                detail="Audio and Video consultations are temporarily unavailable. Please select Doctor Phone Callback or Doctor Chat Advice."
            )
        if requested_channel_val not in ["CALLBACK", "CHAT", "IN_PERSON_PHC", "HOME_VISIT"]:
            requested_channel_val = "CALLBACK"

        packet = req.handoff_packet or {}
        raw_symptoms = [s["display"] if isinstance(s, dict) else str(s) for s in packet.get("symptoms", [])] or req.symptoms or []
        # Normalize and deduplicate symptoms
        symptoms_list = []
        seen_syms = set()
        for s in raw_symptoms:
            if s and isinstance(s, str):
                c_s = " ".join(s.strip().split())
                if c_s and c_s.lower() not in seen_syms:
                    seen_syms.add(c_s.lower())
                    symptoms_list.append(c_s.title())

        chief_complaint = " ".join((packet.get("chief_concern") or req.chief_complaint or (symptoms_list[0] if symptoms_list else "Doctor consultation requested")).strip().split())
        
        # Deterministic emergency evaluation
        eval_symptoms = [s.lower() for s in symptoms_list]
        if chief_complaint and chief_complaint.lower() not in eval_symptoms:
            eval_symptoms.append(chief_complaint.lower())

        is_preg = profile.is_pregnant
        gest_w = profile.gestational_weeks
        if req.beneficiary_id:
            hm = db.query(HouseholdMember).filter(HouseholdMember.id == req.beneficiary_id, HouseholdMember.citizen_id == citizen_id).first()
            if hm:
                is_preg = hm.is_pregnant
                gest_w = hm.gestational_weeks

        calc_priority, is_trig, trig_reason, trig_guidance = EmergencyRuleEvaluator.evaluate(
            symptoms=eval_symptoms,
            is_pregnant=is_preg,
            gestational_weeks=gest_w
        )
        priority_val = calc_priority.value
        guidance = trig_guidance if is_trig else "Please stay calm and monitor your symptoms."
        safety_data = {
            "priority": priority_val,
            "triggered_rule_ids": ["EMERGENCY-RULE-01"] if is_trig else [],
            "citizen_message": guidance,
            "evaluated_at": utc_now().isoformat()
        }

        if not case:
            case_priority = CasePriorityEnum.URGENT if priority_val == "URGENT" else (CasePriorityEnum.HIGH if priority_val == "HIGH" else CasePriorityEnum.ROUTINE)
            case_ref = f"DOCREQ-CASE-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:4].upper()}"
            case = Case(
                reference=case_ref,
                citizen_id=citizen_id,
                primary_concern=chief_complaint,
                priority=case_priority,
                status=CaseStatusEnum.NEW,
                preferred_language=req.preferred_language or profile.preferred_language or "mr-IN",
                safety_rule_triggered=is_trig,
                safety_rule_reason=trig_reason,
                citizen_guidance_text=guidance,
                assigned_facility_name="Kalyanpur Primary Health Centre (PHC)",
                assigned_facility_id="PHC-09"
            )
            db.add(case)
            db.flush()

        # 2. Record Explicit Consent
        consent = SharingConsent(
            citizen_id=citizen_id,
            beneficiary_id=req.beneficiary_id,
            recipient_role="PHC_DOCTOR",
            purpose="CARE_HANDOFF",
            scope=req.sharing_scope or packet.get("sharing_scope", {}),
            policy_version="v1.0",
            consent_text="I agree to share the information shown with the PHC doctor for this care request.",
            consented_at=utc_now()
        )
        db.add(consent)
        db.flush()

        # 3. Create ServiceRequest in WAITING_FOR_DOCTOR status
        req_ref = f"DOCREQ-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:4].upper()}"
        srv_req = ServiceRequest(
            request_reference=req_ref,
            citizen_id=citizen_id,
            beneficiary_id=req.beneficiary_id,
            citizen_need_id=req.citizen_need_id or req.need_id,
            need_id=req.citizen_need_id or req.need_id,
            chat_session_id=req.chat_session_id,
            case_id=case.id,
            request_type="DOCTOR_CONSULTATION",
            requested_channel=requested_channel_val,
            status="WAITING_FOR_DOCTOR",
            priority=priority_val,
            assigned_role="PHC_DOCTOR",
            assigned_facility_id="PHC-09",
            submitted_at=utc_now(),
            details={
                "chief_complaint": chief_complaint,
                "symptoms": symptoms_list,
                "channel": requested_channel_val,
                "request_type": req.request_type
            },
            idempotency_key=req.idempotency_key
        )
        db.add(srv_req)
        db.flush()

        # 4. Save Canonical CareHandoff Packet v1
        packet["handoff_id"] = f"hnd-{uuid.uuid4().hex[:12]}"
        packet["service_request_id"] = srv_req.id
        packet["case_id"] = case.id
        packet["consent_id"] = consent.id
        packet["version"] = 1
        handoff = CareHandoff(
            version=1,
            service_request_id=srv_req.id,
            citizen_id=citizen_id,
            beneficiary_id=req.beneficiary_id,
            chat_session_id=req.chat_session_id,
            citizen_need_id=req.citizen_need_id or req.need_id,
            case_id=case.id,
            consent_id=consent.id,
            request_type="DOCTOR_CONSULTATION",
            requested_channel=requested_channel_val,
            recipient_role="PHC_DOCTOR",
            source="CITIZEN_CHAT" if req.chat_session_id else "CITIZEN_HOME",
            citizen_summary=packet.get("citizen_summary") or f"{chief_complaint} reported by citizen.",
            chief_concern=chief_complaint,
            structured_payload=packet,
            safety_snapshot=safety_data,
            created_at=utc_now()
        )
        db.add(handoff)
        db.flush()

        srv_req.handoff_id = handoff.id

        # 5. Atomically create canonical DoctorChatThread
        thread_id = str(uuid.uuid4())
        thread = DoctorChatThread(
            id=thread_id,
            service_request_id=srv_req.id,
            citizen_id=citizen_id,
            doctor_id=srv_req.assigned_user_id,
            facility_id=srv_req.assigned_facility_id or "PHC-09",
            channel="DOCTOR_CHAT",
            status=srv_req.status
        )
        db.add(thread)
        db.flush()

        # 6. Atomically create companion TeleconsultationRequest
        tele_req = TeleconsultationRequest(
            id=thread_id,
            public_reference=srv_req.request_reference,
            citizen_id=citizen_id,
            household_member_id=req.beneficiary_id if req.beneficiary_id != citizen_id else None,
            citizen_need_id=srv_req.citizen_need_id or srv_req.need_id,
            service_request_id=srv_req.id,
            case_id=case.id,
            facility_id=srv_req.assigned_facility_id or "PHC-09",
            assigned_doctor_id=srv_req.assigned_user_id,
            mode=requested_channel_val,
            status=srv_req.status,
            priority=priority_val,
            chief_complaint=chief_complaint,
            symptoms=symptoms_list,
            submitted_at=utc_now(),
            idempotency_key=req.idempotency_key
        )
        db.add(tele_req)
        db.flush()

        # 7. ServiceRequest Status History
        hist = ServiceRequestStatusHistory(
            service_request_id=srv_req.id,
            from_status="DRAFT",
            to_status="WAITING_FOR_DOCTOR",
            actor_role="CITIZEN",
            actor_id=citizen_id,
            reason="Citizen requested doctor teleconsultation with confirmed consent."
        )
        db.add(hist)

        # 8. Publish Domain Event
        from app.services.event_bus import publish_domain_event
        publish_domain_event(
            event_name="CITIZEN_DOCTOR_REQUEST_SUBMITTED",
            payload={
                "event_id": f"evt-{uuid.uuid4().hex[:8]}",
                "service_request_id": srv_req.id,
                "request_reference": srv_req.request_reference,
                "conversation_id": thread.id,
                "case_id": case.id,
                "citizen_id": citizen_id,
                "beneficiary_id": req.beneficiary_id,
                "recipient_role": "PHC_DOCTOR",
                "priority": priority_val,
                "timestamp": utc_now().isoformat()
            }
        )
        publish_domain_event(
            event_name="DOCTOR_REQUEST_CREATED",
            payload={
                "request_id": thread.id,
                "conversation_id": thread.id,
                "service_request_id": srv_req.id,
                "reference": srv_req.request_reference,
                "request_reference": srv_req.request_reference,
                "priority": priority_val,
                "facility_id": "PHC-09"
            }
        )

        db.commit()
        db.refresh(srv_req)
        db.refresh(thread)
        db.refresh(case)

        return {
            "id": srv_req.id,
            "service_request_id": srv_req.id,
            "request_id": srv_req.id,
            "request_reference": srv_req.request_reference,
            "reference": srv_req.request_reference,
            "conversation_id": thread.id,
            "citizen_id": citizen_id,
            "assigned_doctor_id": srv_req.assigned_user_id,
            "channel": srv_req.requested_channel,
            "requested_channel": srv_req.requested_channel,
            "status": srv_req.status,
            "case_id": case.id,
            "case_reference": case.reference,
            "priority": priority_val,
            "handoff_id": handoff.id,
            "assigned_facility": "Kalyanpur Primary Health Centre (PHC)",
            "guidance": guidance,
            "created_at": srv_req.created_at.isoformat()
        }

    @staticmethod
    def create_asha_request(db: Session, citizen_id: str, req: AshaRequestCreateDTO) -> Dict[str, Any]:
        # 1. Idempotency Check by Idempotency-Key
        if req.idempotency_key:
            existing = db.query(ServiceRequest).filter(ServiceRequest.idempotency_key == req.idempotency_key).first()
            if existing:
                return {
                    "service_request_id": existing.id,
                    "request_id": existing.id,
                    "request_reference": existing.request_reference,
                    "reference": existing.request_reference,
                    "status": existing.status,
                    "case_id": existing.case_id,
                    "assigned_asha": existing.details.get("assigned_asha", "Local ASHA Worker"),
                    "message": "ASHA request already submitted (Idempotent)",
                    "reused_existing_request": True,
                    "created_at": existing.created_at.isoformat()
                }

        # 2. Duplicate Check for Active/Pending Requests
        # Active open statuses where a citizen already has a pending or in-progress ASHA request
        open_statuses = [
            "SUBMITTED", "ASSIGNMENT_PENDING", "ASHA_ASSIGNED",
            "ASHA_ACKNOWLEDGED", "CITIZEN_CONTACTED", "VISIT_SCHEDULED",
            "VISIT_IN_PROGRESS"
        ]
        
        need_id_to_check = req.citizen_need_id or req.need_id
        duplicate_query = db.query(ServiceRequest).filter(
            ServiceRequest.citizen_id == citizen_id,
            ServiceRequest.request_type == "ASHA_ASSISTANCE",
            ServiceRequest.status.in_(open_statuses)
        )
        if req.beneficiary_id:
            duplicate_query = duplicate_query.filter(ServiceRequest.beneficiary_id == req.beneficiary_id)
        else:
            duplicate_query = duplicate_query.filter(ServiceRequest.beneficiary_id.is_(None))

        if need_id_to_check:
            # Check if an existing active request has this need_id
            existing_need_req = duplicate_query.filter(
                (ServiceRequest.citizen_need_id == need_id_to_check) |
                (ServiceRequest.need_id == need_id_to_check)
            ).first()
            if existing_need_req:
                return {
                    "service_request_id": existing_need_req.id,
                    "request_id": existing_need_req.id,
                    "request_reference": existing_need_req.request_reference,
                    "reference": existing_need_req.request_reference,
                    "status": existing_need_req.status,
                    "case_id": existing_need_req.case_id,
                    "assigned_asha": existing_need_req.details.get("assigned_asha", "Local ASHA Worker"),
                    "message": "Reused existing active ASHA request for this need",
                    "reused_existing_request": True,
                    "created_at": existing_need_req.created_at.isoformat()
                }
        else:
            # Check if there is an active open request with identical chief concern / assistance type created recently
            packet = req.handoff_packet or {}
            reason_text = req.reason or packet.get("chief_concern")
            existing_open = duplicate_query.order_by(ServiceRequest.created_at.desc()).first()
            if existing_open and reason_text and existing_open.details.get("reason") == reason_text:
                return {
                    "service_request_id": existing_open.id,
                    "request_id": existing_open.id,
                    "request_reference": existing_open.request_reference,
                    "reference": existing_open.request_reference,
                    "status": existing_open.status,
                    "case_id": existing_open.case_id,
                    "assigned_asha": existing_open.details.get("assigned_asha", "Local ASHA Worker"),
                    "message": "Reused existing active ASHA request with identical concern",
                    "reused_existing_request": True,
                    "created_at": existing_open.created_at.isoformat()
                }

        profile = db.query(CitizenProfile).filter(CitizenProfile.id == citizen_id).first()
        if not profile:
            raise ValueError("Citizen profile not found")

        # 1. Resolve Jurisdiction ASHA
        assigned_asha_user = None
        assigned_asha_name = "Assignment Pending"
        init_status = "ASSIGNMENT_PENDING"

        if profile.assigned_asha_id:
            assigned_asha_user = db.query(User).filter(User.id == profile.assigned_asha_id).first()
            if assigned_asha_user:
                assigned_asha_name = f"{assigned_asha_user.name} ({profile.village_name or 'Kalyanpur'})"
                init_status = "ASHA_ASSIGNED"
        
        if not assigned_asha_user:
            # Check village mapping for ASHA
            mapped_asha = db.query(User).filter(or_(User.role == "ASHA_WORKER", User.role == "ASHA"), User.is_active == True).first()
            if mapped_asha and ((profile.village_name and "Kalyanpur" in profile.village_name) or not profile.village_name):
                assigned_asha_user = mapped_asha
                assigned_asha_name = f"{mapped_asha.name} (Kalyanpur)"
                init_status = "ASHA_ASSIGNED"

        # 2. Search or create compatible Case
        case = None
        if req.case_id:
            case = db.query(Case).filter(Case.id == req.case_id).first()

        packet = req.handoff_packet or {}
        reason_text = req.reason or packet.get("chief_concern") or "ASHA home assistance requested"
        safety_data = packet.get("safety", {})
        priority_val = req.urgency or safety_data.get("priority", "ROUTINE")

        if not case:
            case_ref = f"ASHAREQ-CASE-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:4]}"
            case = Case(
                reference=case_ref,
                citizen_id=citizen_id,
                primary_concern=reason_text,
                priority=CasePriorityEnum.ROUTINE,
                status=CaseStatusEnum.ASHA_ASSIGNED if assigned_asha_user else CaseStatusEnum.NEW,
                preferred_language=profile.preferred_language or "mr-IN",
                assigned_asha_id=assigned_asha_user.id if assigned_asha_user else None,
                assigned_asha_name=assigned_asha_name,
                assigned_facility_name="Kalyanpur PHC"
            )
            db.add(case)
            db.flush()

        # 3. Save Consent
        consent = SharingConsent(
            citizen_id=citizen_id,
            beneficiary_id=req.beneficiary_id,
            recipient_role="ASHA_WORKER",
            purpose="CARE_HANDOFF",
            scope=req.sharing_scope or packet.get("sharing_scope", {}),
            policy_version="v1.0",
            consent_text="I agree to share the information shown with the local ASHA worker for home visit support.",
            consented_at=utc_now()
        )
        db.add(consent)
        db.flush()

        # 4. Create ServiceRequest
        req_ref = f"ASHAREQ-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:4]}"
        srv_req = ServiceRequest(
            request_reference=req_ref,
            citizen_id=citizen_id,
            beneficiary_id=req.beneficiary_id,
            citizen_need_id=req.citizen_need_id or req.need_id,
            need_id=req.citizen_need_id or req.need_id,
            chat_session_id=req.chat_session_id,
            case_id=case.id,
            request_type="ASHA_ASSISTANCE",
            requested_channel="HOME_VISIT" if req.assistance_type == "HOME_VISIT" else "CALLBACK",
            status=init_status,
            priority=priority_val,
            assigned_role="ASHA_WORKER",
            assigned_user_id=assigned_asha_user.id if assigned_asha_user else None,
            submitted_at=utc_now(),
            details={
                "assistance_type": req.assistance_type,
                "preferred_date": req.preferred_date,
                "preferred_time_window": req.preferred_time_window,
                "location": req.location or packet.get("location", {}),
                "landmark": req.landmark or packet.get("location", {}).get("landmark"),
                "mobility_or_accessibility_note": req.mobility_or_accessibility_note,
                "reason": reason_text,
                "assigned_asha": assigned_asha_name
            },
            idempotency_key=req.idempotency_key
        )
        db.add(srv_req)
        db.flush()

        # 5. Create Canonical CareHandoff Packet v1
        packet["handoff_id"] = f"hnd-{uuid.uuid4().hex[:12]}"
        packet["service_request_id"] = srv_req.id
        packet["case_id"] = case.id
        packet["consent_id"] = consent.id
        packet["version"] = 1
        handoff = CareHandoff(
            version=1,
            service_request_id=srv_req.id,
            citizen_id=citizen_id,
            beneficiary_id=req.beneficiary_id,
            chat_session_id=req.chat_session_id,
            citizen_need_id=req.citizen_need_id or req.need_id,
            case_id=case.id,
            consent_id=consent.id,
            request_type="ASHA_ASSISTANCE",
            requested_channel="HOME_VISIT",
            recipient_role="ASHA_WORKER",
            source="CITIZEN_CHAT",
            citizen_summary=packet.get("citizen_summary") or f"{reason_text} reported for ASHA visit.",
            chief_concern=reason_text,
            structured_payload=packet,
            safety_snapshot=safety_data,
            created_at=utc_now()
        )
        db.add(handoff)
        db.flush()

        srv_req.handoff_id = handoff.id

        # 6. ServiceRequest Status History
        hist = ServiceRequestStatusHistory(
            service_request_id=srv_req.id,
            from_status="DRAFT",
            to_status=init_status,
            actor_role="CITIZEN",
            actor_id=citizen_id,
            reason="Citizen requested ASHA assistance with confirmed consent."
        )
        db.add(hist)

        # 7. Create linked FollowUp / Task for ASHA Worker
        due_date = utc_now() + timedelta(days=1)
        if req.preferred_date:
            try:
                due_date = datetime.fromisoformat(req.preferred_date)
            except Exception:
                pass

        follow_up = FollowUp(
            case_id=case.id,
            citizen_id=citizen_id,
            created_by_role="CITIZEN",
            source="CITIZEN_CHAT",
            task_type="ASHA_HOME_VISIT" if req.assistance_type == "HOME_VISIT" else "ASHA_ASSISTANCE",
            reason=reason_text,
            assigned_role=UserRoleEnum.ASHA_WORKER,
            assigned_user_id=assigned_asha_user.id if assigned_asha_user else None,
            instructions=f"Citizen requested {req.assistance_type}. Landmark: {req.landmark or 'Village'}. Preferred: {req.preferred_time_window}",
            priority=CasePriorityEnum.ROUTINE if priority_val == "ROUTINE" else CasePriorityEnum.HIGH,
            due_at=due_date,
            status="PENDING"
        )
        db.add(follow_up)

        # 8. Publish Domain Event
        from app.services.event_bus import publish_domain_event
        publish_domain_event(
            event_name="CITIZEN_ASHA_REQUEST_SUBMITTED",
            payload={
                "event_id": f"evt-{uuid.uuid4().hex[:8]}",
                "service_request_id": srv_req.id,
                "request_reference": srv_req.request_reference,
                "case_id": case.id,
                "citizen_id": citizen_id,
                "beneficiary_id": req.beneficiary_id,
                "assigned_asha_id": assigned_asha_user.id if assigned_asha_user else None,
                "recipient_role": "ASHA_WORKER",
                "status": init_status,
                "timestamp": utc_now().isoformat()
            }
        )

        db.commit()
        db.refresh(srv_req)

        return {
            "service_request_id": srv_req.id,
            "request_id": srv_req.id,
            "request_reference": srv_req.request_reference,
            "reference": srv_req.request_reference,
            "case_id": case.id,
            "handoff_id": handoff.id,
            "beneficiary_id": req.beneficiary_id,
            "request_type": srv_req.request_type,
            "status": srv_req.status,
            "assigned_asha": assigned_asha_name,
            "created_at": srv_req.created_at.isoformat()
        }

    @staticmethod
    def get_citizen_service_requests(db: Session, citizen_id: str) -> List[Dict[str, Any]]:
        reqs = db.query(ServiceRequest).filter(
            ServiceRequest.citizen_id == citizen_id
        ).order_by(ServiceRequest.created_at.desc()).all()

        results = []
        for r in reqs:
            handoff = db.query(CareHandoff).filter(CareHandoff.service_request_id == r.id).order_by(CareHandoff.version.desc()).first()
            results.append({
                "id": r.id,
                "request_reference": r.request_reference,
                "request_type": r.request_type,
                "requested_channel": r.requested_channel,
                "status": r.status,
                "priority": r.priority,
                "assigned_role": r.assigned_role,
                "assigned_user_id": r.assigned_user_id,
                "assigned_worker_name": r.details.get("assigned_asha") or ("Dr. Abhinav Sharma" if r.assigned_role == "PHC_DOCTOR" else "Care Team"),
                "chief_concern": handoff.chief_concern if handoff else (r.details.get("chief_complaint") or r.details.get("reason") or "Care Request"),
                "citizen_summary": handoff.citizen_summary if handoff else None,
                "handoff_version": handoff.version if handoff else 1,
                "handoff_packet": handoff.structured_payload if handoff else {},
                "case_id": r.case_id,
                "case_reference": r.case.reference if r.case else None,
                "submitted_at": r.submitted_at.isoformat() if r.submitted_at else r.created_at.isoformat(),
                "created_at": r.created_at.isoformat()
            })
        return results

    @staticmethod
    def get_citizen_service_request_detail(db: Session, citizen_id: str, request_id: str) -> Optional[Dict[str, Any]]:
        r = db.query(ServiceRequest).filter(
            (ServiceRequest.id == request_id) | (ServiceRequest.request_reference == request_id),
            ServiceRequest.citizen_id == citizen_id
        ).first()
        if not r:
            return None

        handoffs = db.query(CareHandoff).filter(CareHandoff.service_request_id == r.id).order_by(CareHandoff.version.asc()).all()
        latest_handoff = handoffs[-1] if handoffs else None
        history = db.query(ServiceRequestStatusHistory).filter(ServiceRequestStatusHistory.service_request_id == r.id).order_by(ServiceRequestStatusHistory.occurred_at.asc()).all()

        # Retrieve Doctor Consultation Outcome details if available
        consultation_data = None
        prescriptions_data = []
        investigations_data = []
        followups_data = []

        if r.case_id:
            # 1. Fetch Consultation
            cons = db.query(Consultation).filter(Consultation.case_id == r.case_id).order_by(Consultation.created_at.desc()).first()
            if cons:
                facility_name = "Kalyanpur Primary Health Centre (PHC-09)"
                if cons.facility_id:
                    fac_rec = db.query(Facility).filter(Facility.id == cons.facility_id).first()
                    if fac_rec and fac_rec.official_name:
                        facility_name = fac_rec.official_name

                consultation_data = {
                    "consultation_id": cons.id,
                    "consultation_reference": cons.reference,
                    "doctor_name": cons.doctor_name or "Dr. Abhinav Sharma",
                    "facility_name": facility_name,
                    "provisional_diagnosis": cons.provisional_diagnosis or r.details.get("provisional_diagnosis"),
                    "confirmed_diagnosis": cons.confirmed_diagnosis or cons.provisional_diagnosis or r.details.get("provisional_diagnosis"),
                    "clinical_summary": cons.clinical_summary or r.details.get("clinical_summary"),
                    "care_plan_summary": cons.care_plan_summary or r.details.get("patient_guidance"),
                    "examination_notes": cons.examination_notes,
                    "status": cons.status,
                    "started_at": cons.started_at.isoformat() if cons.started_at else None,
                    "completed_at": cons.completed_at.isoformat() if cons.completed_at else None
                }

            # 2. Fetch Prescriptions
            rxs = db.query(Prescription).filter(
                Prescription.case_id == r.case_id,
                Prescription.status != "DRAFT"
            ).order_by(Prescription.created_at.desc()).all()
            for rx in rxs:
                rx_doctor_name = "Dr. Abhinav Sharma"
                if rx.prescriber_doctor_id:
                    doc_user = db.query(User).filter(User.id == rx.prescriber_doctor_id).first()
                    if doc_user:
                        rx_doctor_name = doc_user.name
                elif getattr(rx, "doctor_name", None):
                    rx_doctor_name = rx.doctor_name

                prescriptions_data.append({
                    "prescription_id": rx.id,
                    "reference": rx.reference,
                    "status": rx.status,
                    "doctor_name": rx_doctor_name,
                    "clinical_context": rx.clinical_context or getattr(rx, "provisional_diagnosis", None),
                    "signed_at": rx.signed_at.isoformat() if rx.signed_at else rx.created_at.isoformat(),
                    "items": [
                        {
                            "medicine_name": getattr(it, "generic_name_snapshot", None) or getattr(it, "brand_name_snapshot", None) or getattr(it, "medicine", "Medicine"),
                            "dosage": getattr(it, "dose", None) or getattr(it, "dosage", "1 tablet"),
                            "frequency": it.frequency,
                            "duration_days": getattr(it, "duration_value", None) or getattr(it, "duration_days", 5),
                            "instructions": it.instructions
                        }
                        for it in rx.items
                    ]
                })

            # 3. Fetch Investigations
            invs = db.query(InvestigationOrder).filter(InvestigationOrder.case_id == r.case_id).order_by(InvestigationOrder.ordered_at.desc()).all()
            for inv in invs:
                investigations_data.append({
                    "investigation_id": inv.id,
                    "order_reference": getattr(inv, "reference", getattr(inv, "order_reference", inv.id)),
                    "reference": getattr(inv, "reference", getattr(inv, "order_reference", inv.id)),
                    "test_name": inv.test_name,
                    "test_type": getattr(inv, "category", getattr(inv, "test_type", "GENERAL")),
                    "category": getattr(inv, "category", getattr(inv, "test_type", "GENERAL")),
                    "priority": inv.priority,
                    "status": inv.status,
                    "ordered_at": inv.ordered_at.isoformat() if inv.ordered_at else inv.created_at.isoformat()
                })

            # 4. Fetch Follow-ups
            fu_records = db.query(FollowUp).filter(FollowUp.case_id == r.case_id).order_by(FollowUp.created_at.desc()).all()
            for fu in fu_records:
                followups_data.append({
                    "followup_id": fu.id,
                    "follow_up_reference": getattr(fu, "follow_up_reference", fu.id),
                    "task_type": fu.task_type,
                    "instructions": fu.instructions,
                    "assigned_role": str(fu.assigned_role),
                    "due_at": fu.due_at.isoformat() if fu.due_at else None,
                    "status": fu.status
                })

        # 5. Fetch linked messages if any
        messages_data = []
        t_req = db.query(TeleconsultationRequest).filter(
            (TeleconsultationRequest.service_request_id == r.id) | (TeleconsultationRequest.case_id == r.case_id)
        ).first()
        if t_req:
            msgs = db.query(TeleconsultationMessage).filter(TeleconsultationMessage.request_id == t_req.id).order_by(TeleconsultationMessage.created_at.asc()).all()
            for m in msgs:
                messages_data.append({
                    "id": m.id,
                    "sender_type": m.sender_type,
                    "sender_name": m.sender_name,
                    "message_text": m.message_text,
                    "created_at": m.created_at.isoformat()
                })

        beneficiary_name = "Myself"
        if r.beneficiary:
            beneficiary_name = r.beneficiary.full_name
        elif r.citizen:
            beneficiary_name = r.citizen.display_name

        return {
            "id": r.id,
            "service_request_id": r.id,
            "request_reference": r.request_reference,
            "request_type": r.request_type,
            "requested_channel": r.requested_channel,
            "channel": r.requested_channel,
            "mode": r.requested_channel,
            "status": r.status,
            "priority": r.priority,
            "assigned_role": r.assigned_role,
            "assigned_worker_name": r.details.get("assigned_asha") or ("Dr. Abhinav Sharma" if r.assigned_role == "PHC_DOCTOR" else "Care Team"),
            "beneficiary": {
                "id": r.beneficiary_id or r.citizen_id,
                "name": beneficiary_name,
                "displayName": beneficiary_name,
                "relationship": r.beneficiary.relationship_type if r.beneficiary else "SELF"
            },
            "citizen": {
                "id": r.citizen_id,
                "phone": r.citizen.phone if r.citizen else ""
            },
            "messages": messages_data,
            "details": r.details,
            "chief_concern": latest_handoff.chief_concern if latest_handoff else r.details.get("chief_complaint"),
            "chief_complaint": latest_handoff.chief_concern if latest_handoff else r.details.get("chief_complaint"),
            "citizen_summary": latest_handoff.citizen_summary if latest_handoff else None,
            "current_handoff_version": latest_handoff.version if latest_handoff else 1,
            "handoff_packet": latest_handoff.structured_payload if latest_handoff else {},
            "case_id": r.case_id,
            "case_reference": r.case.reference if r.case else None,
            "consultation": consultation_data,
            "prescriptions": prescriptions_data,
            "investigations": investigations_data,
            "followups": followups_data,
            "status_history": [
                {
                    "from_status": h.from_status,
                    "to_status": h.to_status,
                    "actor_role": h.actor_role,
                    "reason": h.reason,
                    "occurred_at": h.occurred_at.isoformat()
                }
                for h in history
            ],
            "submitted_at": r.submitted_at.isoformat() if r.submitted_at else r.created_at.isoformat(),
            "created_at": r.created_at.isoformat()
        }

    @staticmethod
    def update_service_request_handoff(db: Session, citizen_id: str, request_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        r = db.query(ServiceRequest).filter(
            (ServiceRequest.id == request_id) | (ServiceRequest.request_reference == request_id),
            ServiceRequest.citizen_id == citizen_id
        ).first()
        if not r:
            raise ValueError("Service request not found")

        latest_handoff = db.query(CareHandoff).filter(CareHandoff.service_request_id == r.id).order_by(CareHandoff.version.desc()).first()
        new_version = (latest_handoff.version + 1) if latest_handoff else 2
        
        # Clone structured payload and append new information
        payload = dict(latest_handoff.structured_payload) if (latest_handoff and latest_handoff.structured_payload) else {}
        additional_info = update_data.get("new_information", "")
        updated_symptoms = update_data.get("updated_symptoms", [])

        # Update symptoms in payload
        if updated_symptoms:
            existing_syms = payload.get("symptoms", [])
            for sym in updated_symptoms:
                if not any(s.get("code") == sym.upper().replace(" ", "_") for s in existing_syms):
                    existing_syms.append({
                        "code": sym.upper().replace(" ", "_"),
                        "display": sym.title(),
                        "status": "CONFIRMED",
                        "source": "CITIZEN_REPORTED"
                    })
            payload["symptoms"] = existing_syms

        if additional_info:
            payload["citizen_summary"] = (payload.get("citizen_summary", "") + f" Update (v{new_version}): {additional_info}").strip()

        # Deterministic safety re-evaluation
        symptom_names = [s.get("display", "").lower() for s in payload.get("symptoms", [])]
        priority, triggered, reason, guidance = EmergencyRuleEvaluator.evaluate(
            symptoms=symptom_names,
            is_pregnant=payload.get("relevant_context", {}).get("pregnancy_status", False),
            gestational_weeks=payload.get("relevant_context", {}).get("gestational_weeks")
        )
        payload["safety"] = {
            "priority": priority.value,
            "triggered_rule_ids": ["EMERGENCY-RULE-UPDATED"] if triggered else [],
            "citizen_message": guidance,
            "evaluated_at": utc_now().isoformat()
        }

        # Create CareHandoff version 2 (immutable snapshot)
        new_handoff = CareHandoff(
            version=new_version,
            service_request_id=r.id,
            citizen_id=citizen_id,
            beneficiary_id=r.beneficiary_id,
            chat_session_id=r.chat_session_id,
            citizen_need_id=r.citizen_need_id,
            case_id=r.case_id,
            consent_id=latest_handoff.consent_id if latest_handoff else None,
            request_type=r.request_type,
            requested_channel=r.requested_channel,
            recipient_role=r.assigned_role or "PHC_DOCTOR",
            source="CITIZEN_CHAT",
            citizen_summary=payload.get("citizen_summary", ""),
            chief_concern=payload.get("chief_concern") or r.details.get("chief_complaint"),
            structured_payload=payload,
            safety_snapshot=payload["safety"],
            supersedes_handoff_id=latest_handoff.id if latest_handoff else None,
            created_at=utc_now()
        )
        db.add(new_handoff)
        db.flush()

        r.handoff_id = new_handoff.id
        r.priority = priority.value

        # Status history entry
        hist = ServiceRequestStatusHistory(
            service_request_id=r.id,
            from_status=r.status,
            to_status=r.status,
            actor_role="CITIZEN",
            actor_id=citizen_id,
            reason=f"Citizen submitted updated health facts (CareHandoff v{new_version})."
        )
        db.add(hist)

        # Emit domain events
        from app.services.event_bus import publish_domain_event
        publish_domain_event(
            event_name="CARE_HANDOFF_UPDATED",
            payload={
                "event_id": f"evt-{uuid.uuid4().hex[:8]}",
                "service_request_id": r.id,
                "request_reference": r.request_reference,
                "case_id": r.case_id,
                "citizen_id": citizen_id,
                "handoff_version": new_version,
                "recipient_role": r.assigned_role,
                "timestamp": utc_now().isoformat()
            }
        )

        if priority.value != latest_handoff.safety_snapshot.get("priority"):
            publish_domain_event(
                event_name="SAFETY_PRIORITY_CHANGED",
                payload={
                    "event_id": f"evt-{uuid.uuid4().hex[:8]}",
                    "service_request_id": r.id,
                    "case_id": r.case_id,
                    "new_priority": priority.value,
                    "recipient_role": r.assigned_role,
                    "timestamp": utc_now().isoformat()
                }
            )

        db.commit()
        return {
            "service_request_id": r.id,
            "handoff_id": new_handoff.id,
            "version": new_version,
            "priority": priority.value,
            "message": "Care handoff updated successfully"
        }

    @staticmethod
    def cancel_service_request(db: Session, citizen_id: str, request_id: str, reason: str) -> Dict[str, Any]:
        r = db.query(ServiceRequest).filter(
            (ServiceRequest.id == request_id) | (ServiceRequest.request_reference == request_id),
            ServiceRequest.citizen_id == citizen_id
        ).first()
        if not r:
            raise ValueError("Service request not found")

        prev_status = r.status
        r.status = "CANCELLED"
        r.cancellation_reason = reason

        hist = ServiceRequestStatusHistory(
            service_request_id=r.id,
            from_status=prev_status,
            to_status="CANCELLED",
            actor_role="CITIZEN",
            actor_id=citizen_id,
            reason=reason
        )
        db.add(hist)

        from app.services.event_bus import publish_domain_event
        publish_domain_event(
            event_name="SERVICE_REQUEST_CANCELLED",
            payload={
                "event_id": f"evt-{uuid.uuid4().hex[:8]}",
                "service_request_id": r.id,
                "request_reference": r.request_reference,
                "case_id": r.case_id,
                "citizen_id": citizen_id,
                "recipient_role": r.assigned_role,
                "reason": reason,
                "timestamp": utc_now().isoformat()
            }
        )

        db.commit()
        return {
            "service_request_id": r.id,
            "status": "CANCELLED",
            "message": "Service request cancelled successfully"
        }

    @staticmethod
    def get_citizen_timeline(db: Session, citizen_id: str, case_id: str) -> List[Dict[str, Any]]:
        case = db.query(Case).filter(Case.id == case_id, Case.citizen_id == citizen_id).first()
        if not case:
            return []

        # Construct citizen-safe timeline (masking internal doctor notes/staff alerts)
        events = []

        # 1. Intake event
        events.append({
            "id": f"evt-1-{case.id}",
            "event_type": "CONCERN_RECEIVED",
            "title": "Health Concern Received",
            "description": f"Concern reported: {case.primary_concern}",
            "status_label": "Received",
            "actor_role": "Citizen",
            "timestamp": case.created_at.isoformat(),
            "is_citizen_safe": True
        })

        # 2. ASHA assignment / acknowledgment
        if case.status in [CaseStatusEnum.ASHA_ACKNOWLEDGED, CaseStatusEnum.REFERRED_TO_PHC, CaseStatusEnum.DOCTOR_ACKNOWLEDGED, CaseStatusEnum.COMPLETED]:
            events.append({
                "id": f"evt-2-{case.id}",
                "event_type": "ASHA_ASSIGNED",
                "title": "ASHA Worker Assigned",
                "description": f"Assigned to {case.assigned_asha_name or 'Local ASHA Worker'}",
                "status_label": "ASHA Assigned",
                "actor_role": "ASHA Worker",
                "timestamp": (case.created_at + timedelta(minutes=15)).isoformat(),
                "is_citizen_safe": True
            })

        # 3. PHC Referral / Doctor Review
        if case.status in [CaseStatusEnum.REFERRED_TO_PHC, CaseStatusEnum.DOCTOR_ACKNOWLEDGED, CaseStatusEnum.COMPLETED]:
            events.append({
                "id": f"evt-3-{case.id}",
                "event_type": "PHC_REFERRAL",
                "title": "Referred to Health Centre",
                "description": "Your details were sent to Kalyanpur PHC for Doctor review",
                "status_label": "PHC Review",
                "actor_role": "PHC Doctor",
                "timestamp": (case.created_at + timedelta(hours=1)).isoformat(),
                "is_citizen_safe": True
            })

        # 4. Completion
        if case.status == CaseStatusEnum.COMPLETED:
            events.append({
                "id": f"evt-4-{case.id}",
                "event_type": "CARE_COMPLETED",
                "title": "Care Episode Completed",
                "description": "Care plan and guidance provided successfully",
                "status_label": "Completed",
                "actor_role": "Healthcare Provider",
                "timestamp": case.updated_at.isoformat(),
                "is_citizen_safe": True
            })

        return events

    @staticmethod
    def get_beneficiaries(db: Session, citizen_id: str) -> List[Dict[str, Any]]:
        profile = db.query(CitizenProfile).filter(CitizenProfile.id == citizen_id).first()
        if not profile:
            return []

        # Look for active case for SELF if any
        self_active_case = db.query(Case).filter(
            Case.citizen_id == citizen_id,
            Case.status != CaseStatusEnum.COMPLETED
        ).order_by(Case.created_at.desc()).first()

        results: List[Dict[str, Any]] = [
            {
                "id": profile.id,
                "beneficiary_id": profile.id,
                "beneficiaryId": profile.id,
                "citizen_id": profile.id,
                "citizenId": profile.id,
                "household_member_id": None,
                "householdMemberId": None,
                "profile_id": profile.id,
                "profileId": profile.id,
                "full_name": profile.display_name,
                "display_name": profile.display_name,
                "displayName": profile.display_name,
                "relationship": "SELF",
                "relationship_type": "SELF",
                "age": profile.age_estimate or 28,
                "gender": (profile.sex or "FEMALE").upper(),
                "sex": (profile.sex or "FEMALE").upper(),
                "is_registered_patient": True,
                "isRegisteredPatient": True,
                "existing_case_id": self_active_case.id if self_active_case else None,
                "existingCaseId": self_active_case.id if self_active_case else None
            }
        ]

        seen_beneficiary_ids = {str(profile.id)}

        members = db.query(HouseholdMember).filter(
            HouseholdMember.citizen_id == citizen_id,
            HouseholdMember.is_active == True
        ).all()

        for m in members:
            # Skip if this household record represents the authenticated citizen profile (SELF)
            if (
                str(m.id) in seen_beneficiary_ids or
                str(m.id) == str(profile.id) or
                (getattr(m, "linked_citizen_profile_id", None) and str(m.linked_citizen_profile_id) == str(profile.id)) or
                getattr(m, "is_self", False) or
                (m.relationship_type and m.relationship_type.upper() == "SELF")
            ):
                continue

            rel = (m.relationship_type or "OTHER").upper()
            if rel not in ["SELF", "CHILD", "SPOUSE", "PARENT", "OTHER"]:
                if rel in ["MOTHER", "FATHER"]:
                    rel = "PARENT"
                elif rel in ["DAUGHTER", "SON"]:
                    rel = "CHILD"
                elif rel in ["HUSBAND", "WIFE"]:
                    rel = "SPOUSE"
                else:
                    rel = "OTHER"

            seen_beneficiary_ids.add(str(m.id))
            results.append({
                "id": str(m.id),
                "beneficiary_id": str(m.id),
                "beneficiaryId": str(m.id),
                "citizen_id": str(profile.id),
                "citizenId": str(profile.id),
                "household_member_id": str(m.id),
                "householdMemberId": str(m.id),
                "profile_id": None,
                "profileId": None,
                "full_name": m.full_name,
                "display_name": m.full_name,
                "displayName": m.full_name,
                "relationship": rel,
                "relationship_type": rel,
                "age": m.age,
                "gender": (m.sex or "UNKNOWN").upper(),
                "sex": (m.sex or "UNKNOWN").upper(),
                "is_registered_patient": True,
                "isRegisteredPatient": True,
                "existing_case_id": None,
                "existingCaseId": None
            })

        return results

    @staticmethod
    def update_doctor_request_symptoms(
        db: Session,
        citizen_id: str,
        request_id: str,
        new_symptoms: List[str],
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Updates symptoms and recalculates triage priority for an active Doctor Consultation request.
        - Resolves canonical request (UUID, DOCREQ-*, TR-*, case_id).
        - Validates and normalizes symptoms without case-insensitive duplicates.
        - Creates a new version of CareHandoff for audit history preservation.
        - Evaluates deterministic safety rules and updates priority.
        - Appends a SYMPTOMS_UPDATED audit event and broadcasts realtime events.
        """
        from app.services.teleconsultation_service import TeleconsultationService
        from app.safety.emergency_rules import EmergencyRuleEvaluator
        from app.services.event_bus import publish_domain_event

        tele_req, srv_req = TeleconsultationService.resolve_canonical_request(db, request_id)
        if not srv_req and not tele_req:
            raise HTTPException(status_code=404, detail=f"Doctor consultation request '{request_id}' not found")

        # Validate input symptoms
        if not new_symptoms:
            raise HTTPException(status_code=400, detail="At least one symptom is required.")

        normalized_inputs = []
        for s in new_symptoms:
            if s and isinstance(s, str):
                clean = " ".join(s.strip().split())
                if clean:
                    normalized_inputs.append(clean)

        if not normalized_inputs:
            raise HTTPException(status_code=400, detail="Please enter a valid non-empty symptom.")

        profile = db.query(CitizenProfile).filter(CitizenProfile.id == citizen_id).first()

        # Extract current existing symptoms
        existing_symptoms = []
        if srv_req and srv_req.details and isinstance(srv_req.details.get("symptoms"), list):
            existing_symptoms = list(srv_req.details["symptoms"])
        elif tele_req and isinstance(tele_req.symptoms, list):
            existing_symptoms = list(tele_req.symptoms)

        # Append new symptoms without case-insensitive duplicates
        seen_syms = {s.lower() for s in existing_symptoms}
        merged_symptoms = list(existing_symptoms)
        for sym in normalized_inputs:
            if sym.lower() not in seen_syms:
                seen_syms.add(sym.lower())
                merged_symptoms.append(sym.title())

        # Determine maternal/pregnancy context for emergency triage
        is_pregnant = profile.is_pregnant if profile else False
        gestational_weeks = profile.gestational_weeks if profile else None
        target_ben_id = (srv_req.beneficiary_id if srv_req else None) or (tele_req.household_member_id if tele_req else None)
        if target_ben_id and target_ben_id != citizen_id:
            hm = db.query(HouseholdMember).filter(HouseholdMember.id == target_ben_id).first()
            if hm:
                is_pregnant = hm.is_pregnant
                gestational_weeks = hm.gestational_weeks

        # Run deterministic re-triage rules
        chief_complaint = (
            (srv_req.details.get("chief_complaint") if srv_req and srv_req.details else None) or
            (tele_req.chief_complaint if tele_req else None) or
            merged_symptoms[0]
        )
        eval_symptoms = [s.lower() for s in merged_symptoms]
        if chief_complaint and chief_complaint.lower() not in eval_symptoms:
            eval_symptoms.append(chief_complaint.lower())

        calc_priority, is_trig, trig_reason, trig_guidance = EmergencyRuleEvaluator.evaluate(
            symptoms=eval_symptoms,
            is_pregnant=is_pregnant,
            gestational_weeks=gestational_weeks
        )
        priority_val = calc_priority.value
        guidance = trig_guidance if is_trig else "Please stay calm and monitor your symptoms."

        # Version CareHandoff
        target_srv_id = srv_req.id if srv_req else (tele_req.service_request_id if tele_req else None)
        latest_handoff = None
        new_version = 1
        if target_srv_id:
            latest_handoff = db.query(CareHandoff).filter(
                CareHandoff.service_request_id == target_srv_id
            ).order_by(CareHandoff.version.desc()).first()
            if latest_handoff:
                new_version = latest_handoff.version + 1

        new_handoff = CareHandoff(
            version=new_version,
            service_request_id=target_srv_id,
            citizen_id=citizen_id,
            beneficiary_id=target_ben_id,
            chat_session_id=srv_req.chat_session_id if srv_req else None,
            citizen_need_id=(srv_req.citizen_need_id or srv_req.need_id) if srv_req else None,
            case_id=srv_req.case_id if srv_req else (tele_req.case_id if tele_req else None),
            consent_id=latest_handoff.consent_id if latest_handoff else None,
            request_type="DOCTOR_CONSULTATION",
            requested_channel=(srv_req.requested_channel if srv_req else (tele_req.mode if tele_req else "CHAT")),
            recipient_role="PHC_DOCTOR",
            source="CITIZEN_UPDATE",
            citizen_summary=f"Updated symptoms: {', '.join(merged_symptoms)}.",
            chief_concern=chief_complaint,
            structured_payload={
                **(latest_handoff.structured_payload if latest_handoff and latest_handoff.structured_payload else {}),
                "symptoms": [{"code": s.upper().replace(" ", "_"), "display": s, "status": "CONFIRMED"} for s in merged_symptoms],
                "version": new_version,
                "notes": notes,
                "updated_at": datetime.now(timezone.utc).isoformat()
            },
            safety_snapshot={
                "priority": priority_val,
                "triggered_rule_ids": ["EMERGENCY-RULE-01"] if is_trig else [],
                "citizen_message": guidance,
                "evaluated_at": datetime.now(timezone.utc).isoformat()
            },
            created_at=datetime.now(timezone.utc)
        )
        db.add(new_handoff)
        db.flush()

        # Update ServiceRequest
        if srv_req:
            srv_req.priority = priority_val
            srv_req.handoff_id = new_handoff.id
            if not srv_req.details:
                srv_req.details = {}
            srv_req.details["symptoms"] = merged_symptoms
            srv_req.details["chief_complaint"] = chief_complaint
            srv_req.details["updated_at"] = datetime.now(timezone.utc).isoformat()

            # Record status/audit event
            hist = ServiceRequestStatusHistory(
                service_request_id=srv_req.id,
                from_status=srv_req.status,
                to_status=srv_req.status,
                actor_role="CITIZEN",
                actor_id=citizen_id,
                reason=f"SYMPTOMS_UPDATED: Added {', '.join(normalized_inputs)}. Priority recalculated to {priority_val}."
            )
            db.add(hist)

        # Update TeleconsultationRequest
        if tele_req:
            tele_req.priority = priority_val
            tele_req.symptoms = merged_symptoms
            tele_req.safety_rule_triggered = is_trig
            tele_req.safety_reason = trig_reason
            tele_req.version = (tele_req.version or 1) + 1

            thist = TeleconsultationStatusHistory(
                request_id=tele_req.id,
                from_status=tele_req.status,
                to_status=tele_req.status,
                changed_by_user_id=citizen_id,
                changed_by_role="CITIZEN",
                notes=f"SYMPTOMS_UPDATED: Added {', '.join(normalized_inputs)}. Priority recalculated to {priority_val}."
            )
            db.add(thist)

        # Sync Case priority
        target_case_id = (srv_req.case_id if srv_req else None) or (tele_req.case_id if tele_req else None)
        if target_case_id:
            case_obj = db.query(Case).filter(Case.id == target_case_id).first()
            if case_obj:
                case_obj.priority = CasePriorityEnum.URGENT if priority_val == "URGENT" else (CasePriorityEnum.HIGH if priority_val == "HIGH" else CasePriorityEnum.ROUTINE)
                case_obj.safety_rule_triggered = is_trig
                case_obj.safety_rule_reason = trig_reason

        db.commit()
        if srv_req:
            db.refresh(srv_req)
        if tele_req:
            db.refresh(tele_req)

        # Realtime notification dispatch
        event_data = {
            "service_request_id": srv_req.id if srv_req else (tele_req.service_request_id if tele_req else None),
            "request_id": tele_req.id if tele_req else (srv_req.id if srv_req else None),
            "conversation_id": tele_req.id if tele_req else (srv_req.id if srv_req else None),
            "request_reference": srv_req.request_reference if srv_req else (tele_req.public_reference if tele_req else None),
            "case_id": target_case_id,
            "citizen_id": citizen_id,
            "beneficiary_id": target_ben_id,
            "symptoms": merged_symptoms,
            "new_symptoms": normalized_inputs,
            "priority": priority_val,
            "safety_rule_triggered": is_trig,
            "safety_reason": trig_reason,
            "handoff_version": new_version,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        publish_domain_event("REQUEST_CONTEXT_UPDATED", event_data)
        publish_domain_event("CARE_HANDOFF_UPDATED", event_data)
        publish_domain_event("DOCTOR_DIRECT_REQUEST_STATUS_UPDATED", event_data)

        return {
            "id": tele_req.id if tele_req else (srv_req.id if srv_req else request_id),
            "service_request_id": srv_req.id if srv_req else (tele_req.service_request_id if tele_req else None),
            "request_reference": srv_req.request_reference if srv_req else (tele_req.public_reference if tele_req else None),
            "priority": priority_val,
            "symptoms": merged_symptoms,
            "safety_rule_triggered": is_trig,
            "safety_reason": trig_reason,
            "handoff_version": new_version,
            "status": srv_req.status if srv_req else (tele_req.status if tele_req else "WAITING_FOR_DOCTOR")
        }

    @staticmethod
    def get_citizen_profile_detail(db: Session, citizen_id: str) -> Dict[str, Any]:
        profile = db.query(CitizenProfile).filter(CitizenProfile.id == citizen_id).first()
        if not profile:
            raise ValueError("Citizen profile not found")

        # Count active household members
        household_count = db.query(HouseholdMember).filter(
            HouseholdMember.citizen_id == citizen_id,
            HouseholdMember.is_active == True
        ).count()
        if household_count == 0:
            household_count = 1

        # Determine ABHA status
        abha_status = "NOT_LINKED"
        abha_status_label = "Not Linked"
        if profile.abha_reference:
            if "DEMO" in profile.abha_reference or "SANDBOX" in profile.abha_reference:
                abha_status = "VERIFIED_SANDBOX"
                abha_status_label = "Demo / Sandbox link (Not officially verified)"
            else:
                abha_status = "LINKED_UNVERIFIED"
                abha_status_label = "Linked (Pending live verification)"

        # Mask ABHA for privacy (e.g. 91-XXXX-XXXX-1234 or ABHA-***-001)
        abha_masked = None
        if profile.abha_reference:
            raw = profile.abha_reference
            if len(raw) > 6:
                abha_masked = f"{raw[:3]}...{raw[-4:]}"
            else:
                abha_masked = raw

        # Compute age from date_of_birth if present
        computed_age = profile.age_estimate
        if profile.date_of_birth:
            try:
                dob = datetime.strptime(profile.date_of_birth, "%Y-%m-%d")
                today = datetime.now(timezone.utc).date()
                computed_age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
            except Exception:
                pass

        return {
            "id": profile.id,
            "user_id": profile.user_id,
            "display_name": profile.display_name,
            "legal_name": profile.legal_name or profile.display_name,
            "preferred_name": profile.preferred_name or profile.display_name,
            "date_of_birth": profile.date_of_birth,
            "age": computed_age,
            "sex": profile.sex or "Female",
            "phone": profile.phone or "9876543210",
            "alternate_phone": profile.alternate_phone,
            "is_phone_verified": True,
            "emergency_contact_name": profile.emergency_contact_name or "Ramesh Devi",
            "emergency_contact_phone": profile.emergency_contact_phone or "9876500000",
            "emergency_contact_relation": profile.emergency_contact_relation or "SPOUSE",
            "address": profile.address or "House 42, Main Road, Kalyanpur",
            "current_care_location": profile.current_care_location or "Kalyanpur Village, Block 04",
            "village_name": profile.village_name or "Kalyanpur",
            "gram_panchayat": profile.gram_panchayat or "Kalyanpur GP",
            "block_taluka": profile.block_taluka or "Kalyanpur Block",
            "district": profile.district or "District 04",
            "state": profile.state or "Maharashtra",
            "pincode": profile.pincode or "411001",
            "preferred_language": profile.preferred_language or "mr-IN",
            "abha_reference": profile.abha_reference,
            "abha_masked": abha_masked,
            "abha_status": abha_status,
            "abha_status_label": abha_status_label,
            "blood_group": profile.blood_group or "O+",
            "allergies": profile.allergies or [],
            "chronic_conditions": profile.chronic_conditions or [],
            "is_pregnant": bool(profile.is_pregnant),
            "gestational_weeks": profile.gestational_weeks,
            "updated_at": profile.updated_at or profile.created_at,
            "household_count": household_count
        }

    @staticmethod
    def update_citizen_profile(db: Session, citizen_id: str, req: CitizenProfileUpdateRequest) -> Dict[str, Any]:
        profile = db.query(CitizenProfile).filter(CitizenProfile.id == citizen_id).first()
        if not profile:
            raise ValueError("Citizen profile not found")

        if req.display_name is not None:
            profile.display_name = req.display_name.strip()
        if req.legal_name is not None:
            profile.legal_name = req.legal_name.strip()
        if req.preferred_name is not None:
            profile.preferred_name = req.preferred_name.strip()
        if req.date_of_birth is not None:
            profile.date_of_birth = req.date_of_birth
            try:
                dob = datetime.strptime(req.date_of_birth, "%Y-%m-%d")
                today = datetime.now(timezone.utc).date()
                profile.age_estimate = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
            except Exception:
                pass
        if req.age is not None:
            profile.age_estimate = req.age
        if req.sex is not None:
            profile.sex = req.sex
        if req.phone is not None:
            profile.phone = req.phone.strip()
        if req.alternate_phone is not None:
            profile.alternate_phone = req.alternate_phone.strip()
        if req.emergency_contact_name is not None:
            profile.emergency_contact_name = req.emergency_contact_name.strip()
        if req.emergency_contact_phone is not None:
            profile.emergency_contact_phone = req.emergency_contact_phone.strip()
        if req.emergency_contact_relation is not None:
            profile.emergency_contact_relation = req.emergency_contact_relation.strip()
        if req.address is not None:
            profile.address = req.address.strip()
        if req.current_care_location is not None:
            profile.current_care_location = req.current_care_location.strip()
        if req.village_name is not None:
            profile.village_name = req.village_name.strip()
        if req.gram_panchayat is not None:
            profile.gram_panchayat = req.gram_panchayat.strip()
        if req.block_taluka is not None:
            profile.block_taluka = req.block_taluka.strip()
        if req.district is not None:
            profile.district = req.district.strip()
        if req.state is not None:
            profile.state = req.state.strip()
        if req.pincode is not None:
            profile.pincode = req.pincode.strip()
        if req.preferred_language is not None:
            profile.preferred_language = req.preferred_language.strip()
        if req.blood_group is not None:
            profile.blood_group = req.blood_group.strip()
        if req.allergies is not None:
            profile.allergies = req.allergies
        if req.chronic_conditions is not None:
            profile.chronic_conditions = req.chronic_conditions
        if req.is_pregnant is not None:
            profile.is_pregnant = req.is_pregnant
        if req.gestational_weeks is not None:
            profile.gestational_weeks = req.gestational_weeks

        profile.updated_at = datetime.now(timezone.utc)

        # Also keep SELF household member in sync if present
        self_member = db.query(HouseholdMember).filter(
            HouseholdMember.citizen_id == citizen_id,
            HouseholdMember.relationship_type == "SELF"
        ).first()
        if self_member:
            if req.display_name:
                self_member.full_name = profile.display_name
            if req.age:
                self_member.age = profile.age_estimate
            if req.sex:
                self_member.sex = profile.sex
            if req.is_pregnant is not None:
                self_member.is_pregnant = profile.is_pregnant
            if req.gestational_weeks is not None:
                self_member.gestational_weeks = profile.gestational_weeks
            if req.blood_group:
                self_member.blood_group = profile.blood_group
            self_member.updated_at = datetime.now(timezone.utc)

        # Record audit log
        audit = AuditLog(
            actor_user_id=profile.user_id,
            actor_role="CITIZEN",
            action="PROFILE_UPDATED",
            resource_type="CITIZEN_PROFILE",
            resource_id=profile.id,
            outcome="SUCCESS",
            metadata_json={"changes": "Updated citizen personal and contact details"}
        )
        db.add(audit)

        db.commit()
        db.refresh(profile)
        return CitizenService.get_citizen_profile_detail(db, citizen_id)

    @staticmethod
    def get_household_members(db: Session, citizen_id: str) -> List[Dict[str, Any]]:
        # Ensure SELF exists
        profile = db.query(CitizenProfile).filter(CitizenProfile.id == citizen_id).first()
        if not profile:
            return []

        # Check if SELF member exists
        self_member = db.query(HouseholdMember).filter(
            HouseholdMember.citizen_id == citizen_id,
            HouseholdMember.relationship_type == "SELF",
            HouseholdMember.is_active == True
        ).first()

        if not self_member:
            # Seed SELF member if missing
            self_member = HouseholdMember(
                citizen_id=profile.id,
                full_name=profile.display_name,
                relationship_type="SELF",
                age=profile.age_estimate,
                sex=profile.sex,
                is_pregnant=profile.is_pregnant,
                gestational_weeks=profile.gestational_weeks,
                blood_group=profile.blood_group,
                phone=profile.phone,
                abha_reference=profile.abha_reference,
                is_active=True
            )
            db.add(self_member)
            db.commit()
            db.refresh(self_member)

        members = db.query(HouseholdMember).filter(
            HouseholdMember.citizen_id == citizen_id,
            HouseholdMember.is_active == True
        ).order_by(HouseholdMember.created_at.asc()).all()

        from app.mappers.household_mapper import map_household_member_to_dto
        return [map_household_member_to_dto(m) for m in members]

    @staticmethod
    def get_household_member_detail(db: Session, citizen_id: str, member_id: str) -> Dict[str, Any]:
        from app.mappers.household_mapper import map_household_member_to_dto
        member = db.query(HouseholdMember).filter(
            HouseholdMember.id == member_id,
            HouseholdMember.citizen_id == citizen_id
        ).first()
        if not member:
            raise ValueError("Household member not found")

        # Check existing clinical cases
        clinical_cases_count = db.query(Case).filter(
            or_(
                Case.citizen_id == member.linked_citizen_profile_id if member.linked_citizen_profile_id else False,
                Case.citizen_id == citizen_id
            )
        ).count()

        dto = map_household_member_to_dto(member)
        dto["has_clinical_records"] = clinical_cases_count > 0
        return dto

    @staticmethod
    def add_household_member(db: Session, citizen_id: str, req: HouseholdMemberCreateRequest) -> Dict[str, Any]:
        full_name = req.full_name.strip() if req.full_name else ""
        if not full_name:
            raise ValueError("Member full name is required.")

        rel_type = (req.relationship_type or "").strip().upper()
        if not rel_type:
            raise ValueError("Relationship type is required.")

        # Age validation if provided
        if req.age is not None and (req.age < 0 or req.age > 125):
            raise ValueError("Age must be between 0 and 125 years.")

        # Duplicate detection within citizen's active household
        existing = db.query(HouseholdMember).filter(
            HouseholdMember.citizen_id == citizen_id,
            HouseholdMember.full_name.ilike(full_name),
            HouseholdMember.relationship_type == rel_type,
            HouseholdMember.is_active == True
        ).first()
        if existing:
            raise ValueError(f"Household member '{full_name}' with relation '{rel_type}' already exists in your household.")

        member = HouseholdMember(
            citizen_id=citizen_id,
            full_name=full_name,
            relationship_type=rel_type,
            age=req.age,
            sex=req.sex or ("Female" if req.is_pregnant else None),
            phone=req.phone.strip() if req.phone and req.phone.strip() else None,
            abha_reference=req.abha_reference.strip() if req.abha_reference and req.abha_reference.strip() else None,
            is_pregnant=bool(req.is_pregnant),
            gestational_weeks=req.gestational_weeks,
            blood_group=req.blood_group if req.blood_group and req.blood_group.strip() else None,
            chronic_conditions=req.chronic_conditions or [],
            health_notes=req.health_notes.strip() if req.health_notes and req.health_notes.strip() else None,
            is_active=True
        )
        db.add(member)
        db.flush()

        # Audit
        audit = AuditLog(
            actor_user_id=citizen_id,
            actor_role="CITIZEN",
            action="HOUSEHOLD_MEMBER_ADDED",
            resource_type="HOUSEHOLD_MEMBER",
            resource_id=member.id,
            outcome="SUCCESS",
            metadata_json={"full_name": full_name, "relation": rel_type}
        )
        db.add(audit)

        db.commit()
        db.refresh(member)
        return CitizenService.get_household_member_detail(db, citizen_id, member.id)

    @staticmethod
    def update_household_member(db: Session, citizen_id: str, member_id: str, req: HouseholdMemberUpdateRequest) -> Dict[str, Any]:
        member = db.query(HouseholdMember).filter(
            HouseholdMember.id == member_id,
            HouseholdMember.citizen_id == citizen_id
        ).first()
        if not member:
            raise ValueError("Household member not found")

        if req.full_name is not None:
            member.full_name = req.full_name.strip()
        if req.relationship_type is not None:
            member.relationship_type = req.relationship_type
        if req.age is not None:
            member.age = req.age
        if req.sex is not None:
            member.sex = req.sex
        if req.phone is not None:
            member.phone = req.phone.strip()
        if req.abha_reference is not None:
            member.abha_reference = req.abha_reference.strip()
        if req.is_pregnant is not None:
            member.is_pregnant = req.is_pregnant
        if req.gestational_weeks is not None:
            member.gestational_weeks = req.gestational_weeks
        if req.blood_group is not None:
            member.blood_group = req.blood_group
        if req.chronic_conditions is not None:
            member.chronic_conditions = req.chronic_conditions
        if req.health_notes is not None:
            member.health_notes = req.health_notes
        if req.is_active is not None:
            member.is_active = req.is_active

        member.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(member)
        return CitizenService.get_household_member_detail(db, citizen_id, member.id)

    @staticmethod
    def delete_household_member(db: Session, citizen_id: str, member_id: str) -> Dict[str, Any]:
        member = db.query(HouseholdMember).filter(
            HouseholdMember.id == member_id,
            HouseholdMember.citizen_id == citizen_id
        ).first()
        if not member:
            raise ValueError("Household member not found")

        if member.relationship_type == "SELF":
            raise ValueError("Primary citizen profile (SELF) cannot be removed from household.")

        # Check if linked to clinical cases or service requests
        has_cases = db.query(Case).filter(
            Case.citizen_id == member.linked_citizen_profile_id if member.linked_citizen_profile_id else False
        ).first() is not None

        if has_cases:
            # Safe deactivation instead of hard deletion to preserve clinical history
            member.is_active = False
            member.updated_at = datetime.now(timezone.utc)
            db.commit()
            return {"success": True, "message": "Household member has clinical records and has been deactivated/unlinked safely.", "deactivated": True}

        db.delete(member)
        db.commit()
        return {"success": True, "message": "Household member deleted successfully.", "deleted": True}

    @staticmethod
    def get_assigned_care_team(db: Session, citizen_id: str) -> Dict[str, Any]:
        profile = db.query(CitizenProfile).filter(CitizenProfile.id == citizen_id).first()
        if not profile:
            raise ValueError("Citizen profile not found")

        # 1. Resolve ASHA Worker from jurisdictional assignment
        asha_member = None
        if profile.assigned_asha_id:
            asha_user = db.query(User).filter(User.id == profile.assigned_asha_id).first()
            if asha_user:
                asha_member = {
                    "id": asha_user.id,
                    "role": "ASHA_WORKER",
                    "name": asha_user.name or "Sita Patel",
                    "designation": "Assigned ASHA Community Health Worker",
                    "facility_name": "Kalyanpur Gram Panchayat Health Post",
                    "phone": asha_user.phone or "9876543210",
                    "action_type": "CALL",
                    "is_verified": True,
                    "operating_hours": "Mon - Sat: 8:00 AM - 5:00 PM",
                    "address": f"{profile.village_name or 'Kalyanpur'}, {profile.district or 'District 04'}"
                }

        if not asha_member:
            # Look up any active ASHA worker profile for this village/district
            asha_worker = db.query(WorkerProfile).filter(WorkerProfile.worker_type == "ASHA").first()
            if asha_worker and asha_worker.user:
                asha_member = {
                    "id": asha_worker.user.id,
                    "role": "ASHA_WORKER",
                    "name": asha_worker.user.name or "Sita Patel",
                    "designation": "Community ASHA Worker",
                    "facility_name": asha_worker.facility_name or "Kalyanpur Sub-Centre",
                    "phone": asha_worker.user.phone or "9876543210",
                    "action_type": "CALL",
                    "is_verified": True,
                    "operating_hours": "Mon - Sat: 8:00 AM - 5:00 PM",
                    "address": f"{profile.village_name or 'Kalyanpur'}, {profile.district or 'District 04'}"
                }

        # 2. Resolve Assigned PHC Facility
        phc_member = None
        phc_facility = None
        if profile.assigned_facility_id:
            phc_facility = db.query(Facility).filter(Facility.id == profile.assigned_facility_id).first()
        if not phc_facility:
            phc_facility = db.query(Facility).filter(Facility.facility_type.in_(["PHC", "CHC"])).first()

        if phc_facility:
            phc_member = {
                "id": phc_facility.id,
                "role": "PHC_FACILITY",
                "name": phc_facility.name,
                "designation": f"Government {phc_facility.facility_type}",
                "facility_name": phc_facility.name,
                "facility_id": phc_facility.id,
                "phone": getattr(phc_facility, "phone", None) or getattr(phc_facility, "contact_phone", None) or "020-25678901",
                "action_type": "CALL",
                "is_verified": True,
                "operating_hours": "24x7 Emergency • OPD 9:00 AM - 4:00 PM",
                "address": getattr(phc_facility, "address", "Main Road, Kalyanpur")
            }

        # 3. Resolve Assigned Doctor
        doc_member = None
        doc_worker = db.query(WorkerProfile).filter(WorkerProfile.worker_type == "DOCTOR").first()
        if doc_worker and doc_worker.user:
            doc_member = {
                "id": doc_worker.user.id,
                "role": "PHC_DOCTOR",
                "name": doc_worker.user.name or "Dr. Abhinav Sharma",
                "designation": "Medical Officer (MBBS)",
                "facility_name": doc_worker.facility_name or (phc_facility.name if phc_facility else "Kalyanpur PHC"),
                "facility_id": doc_worker.facility_id or (phc_facility.id if phc_facility else None),
                "phone": doc_worker.user.phone or "020-25678902",
                "action_type": "TELECONSULT",
                "is_verified": True,
                "operating_hours": "Mon - Sat: 9:00 AM - 2:00 PM",
                "address": doc_worker.facility_name or "Kalyanpur PHC OPD 1"
            }

        return {
            "assigned_asha": asha_member,
            "assigned_phc": phc_member,
            "assigned_doctor": doc_member,
            "emergency_contact_108": {
                "service_name": "Maharashtra Emergency Medical Services (MEMS)",
                "ambulance_helpline": "108",
                "women_helpline": "1091",
                "national_health_helpline": "104",
                "disclaimer": "Emergency calls directly connect to the Government 108 central dispatch."
            }
        }

    @staticmethod
    def get_citizen_consents(db: Session, citizen_id: str) -> List[Dict[str, Any]]:
        consents = db.query(SharingConsent).filter(
            SharingConsent.citizen_id == citizen_id
        ).order_by(SharingConsent.consented_at.desc()).all()

        if not consents:
            # Seed default care handoff consents if none exist
            c1 = SharingConsent(
                citizen_id=citizen_id,
                recipient_role="ASHA_WORKER",
                purpose="COMMUNITY_CARE_COORDINATION",
                scope={"share_profile": True, "share_location": True, "share_clinical_needs": True},
                policy_version="v1.0",
                consent_text="Consented to share health profile and home location with assigned ASHA worker for outreach."
            )
            c2 = SharingConsent(
                citizen_id=citizen_id,
                recipient_role="PHC_DOCTOR",
                purpose="TELECONSULTATION_AND_RECORDS",
                scope={"share_profile": True, "share_prescriptions": True, "share_symptoms": True},
                policy_version="v1.0",
                consent_text="Consented to share symptom assessments, lab results and medical notes with PHC Medical Officer."
            )
            db.add_all([c1, c2])
            db.commit()
            db.refresh(c1)
            db.refresh(c2)
            consents = [c1, c2]

        purpose_labels = {
            "COMMUNITY_CARE_COORDINATION": "Community ASHA Outreach & Follow-up",
            "TELECONSULTATION_AND_RECORDS": "PHC Doctor Teleconsultation & Diagnosis",
            "CARE_HANDOFF": "Healthcare Handoff and Referral Sharing"
        }

        results = []
        for c in consents:
            is_revoked = c.revoked_at is not None
            results.append({
                "id": c.id,
                "recipient_role": c.recipient_role,
                "recipient_name": "Assigned ASHA Worker" if c.recipient_role == "ASHA_WORKER" else "PHC Medical Officer",
                "purpose": c.purpose,
                "purpose_label": purpose_labels.get(c.purpose, c.purpose),
                "scope": c.scope or {},
                "policy_version": c.policy_version,
                "consent_text": c.consent_text,
                "consented_at": c.consented_at.isoformat() if c.consented_at else None,
                "expires_at": (c.consented_at + timedelta(days=365)).isoformat() if c.consented_at else None,
                "is_revoked": is_revoked,
                "revoked_at": c.revoked_at.isoformat() if c.revoked_at else None,
                "can_revoke": not is_revoked
            })
        return results

    @staticmethod
    def revoke_citizen_consent(db: Session, citizen_id: str, consent_id: str, reason: Optional[str] = None) -> Dict[str, Any]:
        consent = db.query(SharingConsent).filter(
            SharingConsent.id == consent_id,
            SharingConsent.citizen_id == citizen_id
        ).first()
        if not consent:
            raise ValueError("Consent record not found")

        consent.revoked_at = datetime.now(timezone.utc)

        # Write immutable audit event
        audit = AuditLog(
            actor_user_id=citizen_id,
            actor_role="CITIZEN",
            action="CONSENT_REVOKED",
            resource_type="SHARING_CONSENT",
            resource_id=consent.id,
            outcome="SUCCESS",
            metadata_json={"recipient_role": consent.recipient_role, "purpose": consent.purpose, "reason": reason or "User revoked via Privacy Settings"}
        )
        db.add(audit)

        db.commit()
        db.refresh(consent)
        return {
            "success": True,
            "consent_id": consent.id,
            "is_revoked": True,
            "revoked_at": consent.revoked_at.isoformat(),
            "revocation_reason": reason or "User revoked via Privacy Settings"
        }

    @staticmethod
    def get_abha_link_status(db: Session, citizen_id: str) -> Dict[str, Any]:
        profile = db.query(CitizenProfile).filter(CitizenProfile.id == citizen_id).first()
        if not profile:
            raise ValueError("Citizen profile not found")

        status = "NOT_LINKED"
        status_label = "Not Linked"
        status_badge_color = "#64748B"
        is_live = False
        masked_number = None

        if profile.abha_reference:
            raw = profile.abha_reference
            if len(raw) > 6:
                masked_number = f"{raw[:3]}...{raw[-4:]}"
            else:
                masked_number = raw

            if "DEMO" in raw or "SANDBOX" in raw:
                status = "VERIFIED_SANDBOX"
                status_label = "Demo / Sandbox Link (Not Officially Live)"
                status_badge_color = "#2563EB"
            else:
                status = "LINKED_UNVERIFIED"
                status_label = "Linked (Self-Declared / Pending ABDM Verification)"
                status_badge_color = "#D97706"

        return {
            "status": status,
            "status_label": status_label,
            "status_badge_color": status_badge_color,
            "is_verified": status in ["VERIFIED_SANDBOX", "VERIFIED_LIVE"],
            "abha_number_masked": masked_number,
            "abha_address": f"{profile.display_name.lower().replace(' ', '')}@abdm" if profile.abha_reference else None,
            "is_live_abdm": is_live,
            "verification_mode": "SANDBOX_MOCK" if status == "VERIFIED_SANDBOX" else "NONE",
            "disclaimer": "Live ABDM verification is operated in Sandbox Mode for rural demonstration integrity. Actual government validation requires OTP verification."
        }

    @staticmethod
    def search_facilities(db: Session, req: FacilitySearchRequest) -> List[Dict[str, Any]]:
        facilities = db.query(Facility).all()
        if not facilities:
            return [
                {
                    "id": "fac-001",
                    "name": "Kalyanpur Primary Health Centre (PHC)",
                    "facility_type": "PHC",
                    "distance_km": 2.5,
                    "address": "Kalyanpur Main Road",
                    "phone": "+91 98765 43210",
                    "emergency_available_24x7": True,
                    "open_hours": "8:00 AM - 4:00 PM"
                }
            ]

        return [
            {
                "id": f.id,
                "name": f.name,
                "facility_type": f.facility_type,
                "distance_km": 3.0,
                "address": getattr(f, "address", None) or "Kalyanpur Block",
                "phone": getattr(f, "phone", None) or getattr(f, "contact_phone", None) or "+91 98765 43210",
                "emergency_available_24x7": True if f.facility_type in ["PHC", "CHC", "HOSPITAL"] else False,
                "open_hours": "8:00 AM - 4:00 PM"
            }
            for f in facilities
        ]

