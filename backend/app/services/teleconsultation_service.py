import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from app.models import (
    User, CitizenProfile, HouseholdMember, CitizenNeed, ServiceRequest, Case,
    CasePriorityEnum, CaseStatusEnum, Consultation, Prescription, PrescriptionItem,
    InvestigationOrder, FollowUp, Notification, Facility, AuditLog, utc_now,
    TeleconsultationRequest, TeleconsultationConsent, TeleconsultationStatusHistory,
    TeleconsultationMessage, TeleconsultationAttachment, InformationSourceEnum,
    DoctorChatThread, DoctorChatMessage
)
from app.schemas.teleconsultation import (
    TeleconsultationDraftCreateDTO, TeleconsultationIntakeUpdateDTO,
    TeleconsultationSubmitDTO, DoctorCompleteTeleconsultationDTO,
    DoctorDeclineRequestDTO, DoctorRequestInfoDTO
)
from app.safety.emergency_rules import EmergencyRuleEvaluator
from app.services.event_bus import publish_domain_event

class TeleconsultationService:

    @staticmethod
    def create_draft(db: Session, citizen_id: str, dto: TeleconsultationDraftCreateDTO) -> TeleconsultationRequest:
        profile = db.query(CitizenProfile).filter(CitizenProfile.id == citizen_id).first()
        if not profile:
            raise ValueError("Citizen profile not found")

        ref = f"TR-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        req = TeleconsultationRequest(
            public_reference=ref,
            citizen_id=citizen_id,
            household_member_id=dto.household_member_id,
            language_code=dto.language_code,
            mode=dto.mode,
            status="DRAFT",
            priority="ROUTINE",
            facility_id="PHC-09"
        )
        db.add(req)
        db.flush()

        # Log status history
        hist = TeleconsultationStatusHistory(
            request_id=req.id,
            from_status=None,
            to_status="DRAFT",
            changed_by_role="CITIZEN",
            notes="Draft initiated by citizen"
        )
        db.add(hist)
        db.commit()
        db.refresh(req)
        return req

    @staticmethod
    def update_draft_intake(db: Session, request_id: str, citizen_id: str, dto: TeleconsultationIntakeUpdateDTO) -> TeleconsultationRequest:
        req = db.query(TeleconsultationRequest).filter(
            TeleconsultationRequest.id == request_id,
            TeleconsultationRequest.citizen_id == citizen_id
        ).first()
        if not req:
            raise ValueError("Teleconsultation request not found")

        if req.status != "DRAFT":
            raise ValueError(f"Cannot edit intake for request in status '{req.status}'")

        if dto.chief_complaint:
            req.chief_complaint = dto.chief_complaint
        if dto.symptoms:
            req.symptoms = dto.symptoms
        if dto.duration_text:
            req.duration_text = dto.duration_text
        if dto.severity_level:
            req.severity_level = dto.severity_level
        if dto.mode:
            req.mode = dto.mode
        if dto.language_code:
            req.language_code = dto.language_code

        # Structured intake storage
        req.structured_intake = {
            "chief_complaint": req.chief_complaint,
            "symptoms": req.symptoms,
            "duration_text": req.duration_text,
            "severity_level": req.severity_level,
            "progression": dto.progression or "STABLE",
            "relevant_conditions": dto.relevant_conditions,
            "raw_audio_deleted": dto.raw_audio_deleted
        }

        # Deterministic Clinical Safety Screening
        # Determine patient pregnancy context
        is_pregnant = False
        gestational_weeks = None
        if req.household_member_id:
            hm = db.query(HouseholdMember).filter(HouseholdMember.id == req.household_member_id).first()
            if hm:
                is_pregnant = hm.is_pregnant
                gestational_weeks = hm.gestational_weeks
        else:
            profile = db.query(CitizenProfile).filter(CitizenProfile.id == citizen_id).first()
            if profile:
                is_pregnant = profile.is_pregnant
                gestational_weeks = profile.gestational_weeks

        symptom_list = [s.lower() for s in (req.symptoms or [])]
        if req.chief_complaint and not symptom_list:
            symptom_list = [req.chief_complaint.lower()]

        priority, triggered, reason, guidance = EmergencyRuleEvaluator.evaluate(
            symptoms=symptom_list,
            is_pregnant=is_pregnant,
            gestational_weeks=gestational_weeks
        )

        canonical_priority = "EMERGENCY" if priority == CasePriorityEnum.URGENT else ("HIGH" if priority == CasePriorityEnum.HIGH else "ROUTINE")
        req.priority = canonical_priority
        req.safety_rule_triggered = triggered
        req.safety_rule_ids = ["EMERGENCY-RULE-01"] if triggered else []
        req.safety_reason = reason

        db.commit()
        db.refresh(req)
        return req

    @staticmethod
    def submit_request(db: Session, request_id: str, citizen_id: str, dto: TeleconsultationSubmitDTO) -> Dict[str, Any]:
        # Idempotency check
        if dto.idempotency_key:
            existing = db.query(TeleconsultationRequest).filter(
                TeleconsultationRequest.idempotency_key == dto.idempotency_key
            ).first()
            if existing:
                return TeleconsultationService.get_request_detail(db, existing.id, citizen_id)

        req = db.query(TeleconsultationRequest).filter(
            TeleconsultationRequest.id == request_id,
            TeleconsultationRequest.citizen_id == citizen_id
        ).first()
        if not req:
            raise ValueError("Teleconsultation request not found")

        if req.status not in ["DRAFT", "SUBMITTED"]:
            raise ValueError(f"Request already processed (Status: {req.status})")

        profile = db.query(CitizenProfile).filter(CitizenProfile.id == citizen_id).first()
        
        # Save Consents
        if dto.consents:
            consent_record = TeleconsultationConsent(
                request_id=req.id,
                share_concern=dto.consents.share_concern,
                share_medical_history=dto.consents.share_medical_history,
                audio_video_consent=dto.consents.audio_video_consent,
                store_transcript_consent=dto.consents.store_transcript_consent,
                share_location_consent=dto.consents.share_location_consent
            )
            db.add(consent_record)

        # 1. Create / Link CitizenNeed
        need_ref = f"NEED-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:4]}"
        need = CitizenNeed(
            need_reference=need_ref,
            citizen_id=citizen_id,
            person_affected_id=req.household_member_id,
            primary_intent="DOCTOR_CONSULTATION",
            secondary_intents=["HEALTH_CONCERN"],
            requested_service="TELECONSULTATION",
            detected_language=req.language_code,
            confirmed_summary=req.chief_complaint or "Teleconsultation requested",
            urgency=req.priority,
            status="CONFIRMED"
        )
        db.add(need)
        db.flush()
        req.citizen_need_id = need.id

        # 2. Create Clinical Case
        case_ref = f"AC-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        case = Case(
            reference=case_ref,
            citizen_id=citizen_id,
            primary_concern=req.chief_complaint or "Doctor consultation request",
            priority=CasePriorityEnum.URGENT if req.priority == "EMERGENCY" else CasePriorityEnum.ROUTINE,
            status=CaseStatusEnum.NEW,
            preferred_language=req.language_code,
            safety_rule_triggered=req.safety_rule_triggered,
            safety_rule_reason=req.safety_reason,
            assigned_asha_name="Sita Patel (Kalyanpur)",
            assigned_facility_name="Kalyanpur PHC"
        )
        db.add(case)
        db.flush()
        req.case_id = case.id

        # 3. Create ServiceRequest
        srv_ref = f"REQ-DOC-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        srv_req = ServiceRequest(
            request_reference=srv_ref,
            citizen_id=citizen_id,
            need_id=need.id,
            case_id=case.id,
            assigned_facility_id=req.facility_id or "FAC-PHC-001",
            request_type="DOCTOR_CONSULTATION",
            status="PENDING",
            priority=req.priority,
            details={
                "chief_complaint": req.chief_complaint,
                "symptoms": req.symptoms,
                "mode": req.mode
            },
            idempotency_key=dto.idempotency_key
        )
        db.add(srv_req)
        db.flush()
        req.service_request_id = srv_req.id

        # Lifecycle transition: SUBMITTED -> WAITING_FOR_DOCTOR
        req.status = "WAITING_FOR_DOCTOR"
        req.submitted_at = datetime.now(timezone.utc)
        req.queue_position = 1
        req.estimated_wait_minutes = 5
        req.idempotency_key = dto.idempotency_key
        req.version += 1

        # Status history
        hist = TeleconsultationStatusHistory(
            request_id=req.id,
            from_status="DRAFT",
            to_status="WAITING_FOR_DOCTOR",
            changed_by_role="CITIZEN",
            notes="Request submitted by citizen and queued for PHC Doctor"
        )
        db.add(hist)

        db.commit()
        db.refresh(req)

        # Publish WebSocket Event
        publish_domain_event("DOCTOR_REQUEST_CREATED", {
            "request_id": req.id,
            "reference": req.public_reference,
            "priority": req.priority,
            "facility_id": req.facility_id
        })

        return TeleconsultationService.get_request_detail(db, req.id, citizen_id)

    @staticmethod
    def get_request_detail(db: Session, request_id: str, citizen_id: Optional[str] = None) -> Dict[str, Any]:
        query = db.query(TeleconsultationRequest).filter(TeleconsultationRequest.id == request_id)
        if citizen_id:
            query = query.filter(TeleconsultationRequest.citizen_id == citizen_id)
        req = query.first()
        if not req:
            raise ValueError("Teleconsultation request not found")

        # Patient Info
        patient_name = "Patient"
        patient_relation = "SELF"
        patient_age = None
        patient_gender = None
        patient_context = "GENERAL"

        hm = None
        if req.household_member_id and req.household_member_id != req.citizen_id:
            hm = db.query(HouseholdMember).filter(HouseholdMember.id == req.household_member_id).first()

        if hm:
            patient_name = hm.full_name
            patient_relation = hm.relationship_type or "FAMILY"
            patient_age = hm.age
            patient_gender = hm.sex
            if hm.is_pregnant:
                patient_context = "MATERNAL"
            elif hm.age and hm.age <= 12:
                patient_context = "CHILD"
        else:
            profile = db.query(CitizenProfile).filter(CitizenProfile.id == req.citizen_id).first()
            if profile:
                patient_name = profile.display_name or "Citizen"
                patient_age = profile.age_estimate
                patient_gender = profile.sex
                if profile.is_pregnant:
                    patient_context = "MATERNAL"

        if patient_name.strip().lower() in ["self", "myself", ""] and req.citizen_id:
            profile = db.query(CitizenProfile).filter(CitizenProfile.id == req.citizen_id).first()
            if profile and profile.display_name:
                patient_name = profile.display_name

        # Doctor Info
        doc_name = "Kalyanpur PHC Doctor"
        doc_specialty = "Medical Officer (MBBS)"
        if req.assigned_doctor:
            doc_name = req.assigned_doctor.name
            doc_specialty = "Medical Officer"

        # Messages
        msgs = db.query(TeleconsultationMessage).filter(
            TeleconsultationMessage.request_id == req.id
        ).order_by(TeleconsultationMessage.created_at.asc()).all()

        return {
            "id": req.id,
            "conversation_id": req.id,
            "public_reference": req.public_reference,
            "request_reference": req.public_reference,
            "status": req.status,
            "priority": req.priority,
            "mode": req.mode,
            "requested_channel": req.mode,
            "channel": req.mode,
            "language_code": req.language_code,
            "chief_complaint": req.chief_complaint,
            "symptoms": req.symptoms or [],
            "duration_text": req.duration_text,
            "structured_intake": req.structured_intake or {},
            "safety_rule_triggered": req.safety_rule_triggered,
            "safety_reason": req.safety_reason,
            "queue_position": req.queue_position,
            "estimated_wait_minutes": req.estimated_wait_minutes,
            "submitted_at": req.submitted_at.isoformat() if req.submitted_at else None,
            "accepted_at": req.accepted_at.isoformat() if req.accepted_at else None,
            "started_at": req.started_at.isoformat() if req.started_at else None,
            "service_request_id": req.service_request_id or req.id,
            "patient_profile_id": req.citizen_id,
            "patient_id": req.citizen_id,
            "citizen_id": req.citizen_id,
            "beneficiary_id": req.household_member_id,
            "beneficiary_name": patient_name,
            "beneficiary": {
                "id": req.household_member_id or req.citizen_id,
                "name": patient_name,
                "displayName": patient_name,
                "relationship": patient_relation,
                "age": patient_age,
                "gender": patient_gender
            },
            "chief_concern": req.chief_complaint,
            "facility_name": "Kalyanpur Primary Health Centre (PHC-09)",
            "patient": {
                "patient_profile_id": req.citizen_id,
                "name": patient_name,
                "relationship": patient_relation,
                "age": patient_age,
                "gender": patient_gender,
                "context": patient_context
            },
            "doctor": {
                "id": req.assigned_doctor_id,
                "name": doc_name,
                "specialty": doc_specialty,
                "available": True
            },
            "messages": [
                {
                    "id": m.id,
                    "conversation_id": getattr(m, "conversation_id", None) or getattr(m, "request_id", None) or req.id,
                    "service_request_id": getattr(m, "service_request_id", None) or req.service_request_id,
                    "sender_user_id": getattr(m, "sender_user_id", None) or getattr(m, "sender_id", None),
                    "sender_role": getattr(m, "sender_role", None) or ("PHC_DOCTOR" if getattr(m, "sender_type", None) == "DOCTOR" else "CITIZEN"),
                    "sender_type": getattr(m, "sender_type", None) or ("DOCTOR" if getattr(m, "sender_role", None) == "PHC_DOCTOR" else "CITIZEN"),
                    "sender_name": getattr(m, "sender_name", None) or (doc_name if (getattr(m, "sender_role", None) == "PHC_DOCTOR" or getattr(m, "sender_type", None) == "DOCTOR") else patient_name),
                    "message_type": getattr(m, "message_type", None) or "TEXT",
                    "body": getattr(m, "body", None) or getattr(m, "message_text", None) or "",
                    "message_text": getattr(m, "message_text", None) or getattr(m, "body", None) or "",
                    "client_message_id": getattr(m, "client_message_id", None),
                    "status": getattr(m, "status", None) or "DELIVERED",
                    "created_at": m.created_at.isoformat() if getattr(m, "created_at", None) else "",
                    "delivered_at": m.delivered_at.isoformat() if getattr(m, "delivered_at", None) else None,
                    "read_at": m.read_at.isoformat() if getattr(m, "read_at", None) else None
                }
                for m in msgs
            ]
        }

    @staticmethod
    def cancel_request(db: Session, request_id: str, citizen_id: str, reason: Optional[str] = None) -> Dict[str, Any]:
        req = db.query(TeleconsultationRequest).filter(
            TeleconsultationRequest.id == request_id,
            TeleconsultationRequest.citizen_id == citizen_id
        ).first()
        if not req:
            raise ValueError("Request not found")

        old_status = req.status
        req.status = "CANCELLED"
        req.cancellation_reason = reason or "Cancelled by citizen"
        
        hist = TeleconsultationStatusHistory(
            request_id=req.id,
            from_status=old_status,
            to_status="CANCELLED",
            changed_by_role="CITIZEN",
            notes=req.cancellation_reason
        )
        db.add(hist)
        db.commit()
        return {"status": "CANCELLED", "id": req.id}

    @staticmethod
    def resolve_canonical_request(db: Session, request_ref: str) -> tuple[Optional[TeleconsultationRequest], Optional[ServiceRequest]]:
        """
        Canonical resolver that resolves UUID, public reference (DOCREQ-..., TR-..., REQ-DOC-...),
        case_id, or service_request_id to both TeleconsultationRequest and ServiceRequest.
        Always ensures a persistent canonical TeleconsultationRequest conversation exists.
        """
        # 1. Search TeleconsultationRequest directly
        tele_req = db.query(TeleconsultationRequest).filter(
            (TeleconsultationRequest.id == request_ref) |
            (TeleconsultationRequest.public_reference == request_ref) |
            (TeleconsultationRequest.service_request_id == request_ref) |
            (TeleconsultationRequest.case_id == request_ref)
        ).first()

        # 2. Search ServiceRequest directly
        srv_req = db.query(ServiceRequest).filter(
            (ServiceRequest.id == request_ref) |
            (ServiceRequest.request_reference == request_ref) |
            (ServiceRequest.case_id == request_ref)
        ).first()

        # Cross-link if only one was found
        if tele_req and not srv_req and tele_req.service_request_id:
            srv_req = db.query(ServiceRequest).filter(ServiceRequest.id == tele_req.service_request_id).first()

        if srv_req and not tele_req:
            tele_req = db.query(TeleconsultationRequest).filter(
                (TeleconsultationRequest.service_request_id == srv_req.id) |
                (TeleconsultationRequest.case_id == srv_req.case_id) |
                (TeleconsultationRequest.public_reference == srv_req.request_reference)
            ).first()

        # If ServiceRequest exists without a canonical TeleconsultationRequest conversation, create it now
        if srv_req and not tele_req:
            tele_req = TeleconsultationRequest(
                public_reference=srv_req.request_reference,
                citizen_id=srv_req.citizen_id,
                household_member_id=srv_req.beneficiary_id,
                citizen_need_id=srv_req.need_id or srv_req.citizen_need_id,
                service_request_id=srv_req.id,
                case_id=srv_req.case_id,
                mode=srv_req.requested_channel or "CHAT",
                status=srv_req.status or "WAITING_FOR_DOCTOR",
                priority=srv_req.priority or "ROUTINE",
                facility_id="PHC-09",
                chief_complaint=srv_req.details.get("chief_complaint", "Doctor consultation requested") if srv_req.details else "Doctor consultation requested"
            )
            db.add(tele_req)
            db.flush()

        return tele_req, srv_req

    @staticmethod
    def send_message(
        db: Session,
        request_id: str,
        sender_type: str,
        sender_name: str,
        message_text: str,
        sender_id: Optional[str] = None,
        sender_role: Optional[str] = None,
        client_message_id: Optional[str] = None,
        message_type: str = "TEXT"
    ) -> TeleconsultationMessage:
        # Sanitize and truncate message length
        clean_text = (message_text or "").strip()
        if not clean_text:
            raise ValueError("Message body cannot be empty")
        if len(clean_text) > 4000:
            clean_text = clean_text[:4000]

        tele_req, srv_req = TeleconsultationService.resolve_canonical_request(db, request_id)
        if not tele_req and not srv_req:
            raise ValueError(f"Could not resolve request '{request_id}'")

        role = sender_role or ("PHC_DOCTOR" if sender_type.upper() in ["DOCTOR", "PHC_DOCTOR"] else "CITIZEN")
        srv_id = srv_req.id if srv_req else (tele_req.service_request_id if tele_req else None)
        tele_id = tele_req.id if tele_req else None
        cli_id = client_message_id or f"msg-{uuid.uuid4().hex[:12]}"

        from app.services.recent_activity_service import normalize_actor_name
        if role == "PHC_DOCTOR":
            sender_name = normalize_actor_name(sender_name, role="PHC_DOCTOR")

        # 1. Check idempotency in DoctorChatMessage if client_message_id provided
        if client_message_id:
            from app.models import DoctorChatMessage
            existing_doc_msg = db.query(DoctorChatMessage).filter(DoctorChatMessage.client_message_id == client_message_id).first()
            if existing_doc_msg:
                return existing_doc_msg

        # 2. Insert into DoctorChatMessage if thread exists
        from app.models import DoctorChatThread, DoctorChatMessage
        doc_msg = None
        thread = None
        if srv_id:
            thread = db.query(DoctorChatThread).filter(DoctorChatThread.service_request_id == srv_id).first()
        if not thread and tele_id:
            thread = db.query(DoctorChatThread).filter(DoctorChatThread.id == tele_id).first()

        now_dt = datetime.now(timezone.utc)
        msg_id = str(uuid.uuid4())

        if thread:
            doc_msg = DoctorChatMessage(
                id=msg_id,
                conversation_id=thread.id,
                service_request_id=srv_id,
                sender_role=role,
                sender_user_id=sender_id,
                sender_id=sender_id,
                sender_name=sender_name,
                body=clean_text,
                client_message_id=cli_id,
                status="DELIVERED",
                delivery_status="DELIVERED",
                created_at=now_dt,
                delivered_at=now_dt
            )
            db.add(doc_msg)

        # 3. Insert into TeleconsultationMessage if tele_req exists
        tele_msg = None
        if tele_id:
            tele_msg = TeleconsultationMessage(
                id=msg_id,
                request_id=tele_id,
                sender_type="DOCTOR" if role == "PHC_DOCTOR" else "CITIZEN",
                sender_id=sender_id,
                sender_name=sender_name,
                message_text=clean_text,
                created_at=now_dt
            )
            db.add(tele_msg)

        db.commit()

        return_msg = doc_msg or tele_msg

        # Broadcast realtime domain events for both naming conventions
        event_payload = {
            "id": return_msg.id if return_msg else str(uuid.uuid4()),
            "message_id": return_msg.id if return_msg else str(uuid.uuid4()),
            "conversation_id": thread.id if thread else (tele_id or srv_id),
            "request_id": tele_id or srv_id,
            "service_request_id": srv_id,
            "request_reference": srv_req.request_reference if srv_req else (tele_req.public_reference if tele_req else ""),
            "sender_user_id": sender_id,
            "sender_role": role,
            "sender_type": "DOCTOR" if role == "PHC_DOCTOR" else "CITIZEN",
            "sender_name": sender_name,
            "message_type": message_type,
            "body": clean_text,
            "message_text": clean_text,
            "client_message_id": cli_id,
            "status": "DELIVERED",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "delivered_at": datetime.now(timezone.utc).isoformat()
        }

        publish_domain_event("CHAT_MESSAGE_CREATED", event_payload)
        publish_domain_event("DOCTOR_REQUEST_MESSAGE_SENT", event_payload)

        return return_msg

    @staticmethod
    def mark_message_read(db: Session, message_id: str, reader_user_id: Optional[str] = None, reader_role: Optional[str] = None) -> Optional[Any]:
        # 1. Check DoctorChatMessage
        doc_msg = db.query(DoctorChatMessage).filter(DoctorChatMessage.id == message_id).first()
        if doc_msg:
            doc_msg.status = "READ"
            doc_msg.read_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(doc_msg)
            publish_domain_event("CHAT_MESSAGE_READ", {
                "message_id": doc_msg.id,
                "conversation_id": doc_msg.conversation_id,
                "reader_user_id": reader_user_id,
                "reader_role": reader_role,
                "read_at": doc_msg.read_at.isoformat()
            })
            return doc_msg

        # 2. Check TeleconsultationMessage
        msg = db.query(TeleconsultationMessage).filter(TeleconsultationMessage.id == message_id).first()
        if not msg:
            return None

        msg.status = "READ"
        msg.read_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(msg)

        publish_domain_event("CHAT_MESSAGE_READ", {
            "message_id": msg.id,
            "conversation_id": getattr(msg, "conversation_id", None) or msg.request_id,
            "reader_user_id": reader_user_id,
            "reader_role": reader_role,
            "read_at": msg.read_at.isoformat()
        })
        return msg

    @staticmethod
    def list_doctor_requests(db: Session, status_filter: Optional[str] = None, doctor_id: Optional[str] = None) -> List[Dict[str, Any]]:
        query = db.query(TeleconsultationRequest).filter(TeleconsultationRequest.status != "DRAFT")
        
        if status_filter and status_filter.upper() != "ALL":
            sf = status_filter.upper()
            if sf == "NEW":
                query = query.filter(TeleconsultationRequest.status.in_(["SUBMITTED", "WAITING_FOR_DOCTOR"]))
            elif sf == "URGENT":
                query = query.filter(TeleconsultationRequest.priority.in_(["EMERGENCY", "URGENT", "HIGH"]))
            elif sf == "ACCEPTED":
                query = query.filter(TeleconsultationRequest.status == "DOCTOR_ACCEPTED")
            elif sf == "IN_CONSULTATION":
                query = query.filter(TeleconsultationRequest.status == "IN_CONSULTATION")
            elif sf == "COMPLETED":
                query = query.filter(TeleconsultationRequest.status == "COMPLETED")
            elif sf == "ASSIGNED_TO_ME" and doctor_id:
                query = query.filter(TeleconsultationRequest.assigned_doctor_id == doctor_id)

        items = query.order_by(TeleconsultationRequest.submitted_at.desc()).all()
        return [TeleconsultationService.get_request_detail(db, r.id) for r in items]

    @staticmethod
    def doctor_accept_request(db: Session, request_id: str, doctor_user: User) -> Dict[str, Any]:
        req, srv = TeleconsultationService.resolve_canonical_request(db, request_id)
        if not req:
            raise ValueError("Teleconsultation request not found")

        old_status = req.status
        req.status = "DOCTOR_ACCEPTED"
        req.assigned_doctor_id = doctor_user.id
        req.accepted_at = datetime.now(timezone.utc)
        req.version += 1

        if srv:
            srv.status = "DOCTOR_ACCEPTED"
            srv.assigned_user_id = doctor_user.id
            srv.acknowledged_at = datetime.now(timezone.utc)
            db.add(srv)

        # Update linked case if exists
        if req.case_id:
            case = db.query(Case).filter(Case.id == req.case_id).first()
            if case:
                case.status = CaseStatusEnum.DOCTOR_ACKNOWLEDGED

        hist = TeleconsultationStatusHistory(
            request_id=req.id,
            from_status=old_status,
            to_status="DOCTOR_ACCEPTED",
            changed_by_user_id=doctor_user.id,
            changed_by_role="DOCTOR",
            notes=f"Accepted by Dr. {doctor_user.name}"
        )
        db.add(hist)
        db.commit()
        db.refresh(req)

        event_payload = {
            "request_id": req.id,
            "conversation_id": req.id,
            "service_request_id": srv.id if srv else req.service_request_id,
            "request_reference": srv.request_reference if srv else req.public_reference,
            "status": "DOCTOR_ACCEPTED",
            "doctor_id": doctor_user.id,
            "doctor_name": doctor_user.name
        }
        publish_domain_event("DOCTOR_REQUEST_ACCEPTED", event_payload)
        publish_domain_event("DOCTOR_DIRECT_REQUEST_STATUS_UPDATED", event_payload)

        return TeleconsultationService.get_request_detail(db, req.id)

    @staticmethod
    def doctor_start_consultation(db: Session, request_id: str, doctor_user: User) -> Dict[str, Any]:
        req, srv = TeleconsultationService.resolve_canonical_request(db, request_id)
        if not req:
            raise ValueError("Teleconsultation request not found")

        old_status = req.status
        req.status = "IN_CONSULTATION"
        req.started_at = datetime.now(timezone.utc)
        req.assigned_doctor_id = doctor_user.id
        req.version += 1

        if srv:
            srv.status = "IN_CONSULTATION"
            srv.assigned_user_id = doctor_user.id
            srv.details["consultation_started_at"] = datetime.now(timezone.utc).isoformat()
            db.add(srv)

        # Update linked case
        if req.case_id:
            case = db.query(Case).filter(Case.id == req.case_id).first()
            if case:
                case.status = CaseStatusEnum.CONSULTATION_IN_PROGRESS

        hist = TeleconsultationStatusHistory(
            request_id=req.id,
            from_status=old_status,
            to_status="IN_CONSULTATION",
            changed_by_user_id=doctor_user.id,
            changed_by_role="DOCTOR",
            notes=f"Consultation started by Dr. {doctor_user.name}"
        )
        db.add(hist)
        db.commit()
        db.refresh(req)

        event_payload = {
            "request_id": req.id,
            "conversation_id": req.id,
            "service_request_id": srv.id if srv else req.service_request_id,
            "request_reference": srv.request_reference if srv else req.public_reference,
            "status": "IN_CONSULTATION",
            "doctor_id": doctor_user.id,
            "doctor_name": doctor_user.name
        }
        publish_domain_event("CONSULTATION_STARTED", event_payload)
        publish_domain_event("DOCTOR_DIRECT_REQUEST_STATUS_UPDATED", event_payload)

        return TeleconsultationService.get_request_detail(db, req.id)

    @staticmethod
    def doctor_complete_consultation(db: Session, request_id: str, doctor_user: User, dto: DoctorCompleteTeleconsultationDTO) -> Dict[str, Any]:
        req, srv = TeleconsultationService.resolve_canonical_request(db, request_id)
        if not req:
            raise ValueError("Teleconsultation request not found")

        old_status = req.status
        req.status = "COMPLETED"
        req.completed_at = datetime.now(timezone.utc)
        req.clinical_notes = dto.clinical_summary or dto.provisional_diagnosis
        req.disposition = dto.disposition
        req.patient_guidance = dto.patient_guidance or "Follow the prescribed care plan and take rest."
        req.version += 1

        if srv:
            srv.status = "COMPLETED"
            srv.completed_at = datetime.now(timezone.utc)
            srv.details["provisional_diagnosis"] = dto.provisional_diagnosis
            srv.details["patient_guidance"] = dto.patient_guidance
            srv.details["clinical_summary"] = dto.clinical_summary
            db.add(srv)

        # 1. Create Consultation Record
        cons_ref = f"CONS-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        consultation = Consultation(
            reference=cons_ref,
            case_id=req.case_id,
            doctor_id=doctor_user.id,
            doctor_name=f"Dr. {doctor_user.name}",
            facility_id="PHC-09",
            consultation_type="TELECONSULTATION",
            status="COMPLETED",
            provisional_diagnosis=dto.provisional_diagnosis,
            clinical_summary=dto.clinical_summary,
            care_plan_summary=dto.care_plan_summary,
            asha_followup_instructions=dto.asha_instructions,
            started_at=req.started_at or utc_now(),
            completed_at=utc_now(),
            signed_at=utc_now()
        )
        db.add(consultation)
        db.flush()
        req.consultation_id = consultation.id

        # 2. Signed Prescription Creation
        if dto.prescriptions:
            rx_ref = f"RX-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:4].upper()}"
            rx = Prescription(
                reference=rx_ref,
                citizen_id=req.citizen_id,
                case_id=req.case_id,
                consultation_id=consultation.id,
                prescriber_doctor_id=doctor_user.id,
                doctor_id=doctor_user.id,
                facility_id="PHC-09",
                status="SIGNED"
            )
            db.add(rx)
            db.flush()

            for item_dto in dto.prescriptions:
                p_item = PrescriptionItem(
                    prescription_id=rx.id,
                    generic_name_snapshot=item_dto.get("medicine_name", "Paracetamol 500mg"),
                    medicine=item_dto.get("medicine_name", "Paracetamol 500mg"),
                    formulation=item_dto.get("formulation", "Tablet"),
                    dose=item_dto.get("dosage", "1"),
                    frequency=item_dto.get("frequency", "1-0-1"),
                    timing=item_dto.get("timing", "After food"),
                    duration_value=item_dto.get("duration_days", 3),
                    instructions=item_dto.get("instructions", "Take after food with water")
                )
                db.add(p_item)

        # 3. Investigation Orders
        for inv_dto in dto.investigation_orders:
            inv_ref = f"LAB-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:4].upper()}"
            inv = InvestigationOrder(
                reference=inv_ref,
                citizen_id=req.citizen_id,
                case_id=req.case_id,
                consultation_id=consultation.id,
                ordered_by_doctor_id=doctor_user.id,
                facility_id="PHC-09",
                test_name=inv_dto.get("test_name", "Complete Blood Count (CBC)"),
                category=inv_dto.get("category", "PATHOLOGY"),
                priority=inv_dto.get("urgency", inv_dto.get("priority", "ROUTINE")),
                clinical_reason=dto.provisional_diagnosis,
                status="ORDERED",
                preparation_instructions=inv_dto.get("instructions", "Fasting not required")
            )
            db.add(inv)

        # 4. ASHA Follow-up Directive Assignment
        if dto.assign_asha_followup:
            follow_due = datetime.now(timezone.utc) + timedelta(days=dto.asha_due_days or 3)
            fu = FollowUp(
                case_id=req.case_id,
                citizen_id=req.citizen_id,
                consultation_id=consultation.id,
                created_by_id=doctor_user.id,
                created_by_role="DOCTOR",
                source="DOCTOR_ASSIGNED",
                task_type=dto.asha_task_type or "POST_CONSULTATION_CHECK",
                reason=dto.provisional_diagnosis,
                instructions=dto.asha_instructions or "Visit citizen home, check BP and medication compliance.",
                escalation_conditions=dto.asha_escalation_conditions or "Escalate if symptoms worsen or BP > 140/90.",
                due_at=follow_due,
                status="PENDING"
            )
            db.add(fu)

        # Update linked case status
        if req.case_id:
            case = db.query(Case).filter(Case.id == req.case_id).first()
            if case:
                case.status = CaseStatusEnum.COMPLETED if not dto.assign_asha_followup else CaseStatusEnum.FOLLOW_UP_REQUIRED
                case.citizen_guidance_text = dto.patient_guidance

        hist = TeleconsultationStatusHistory(
            request_id=req.id,
            from_status=old_status,
            to_status="COMPLETED",
            changed_by_user_id=doctor_user.id,
            changed_by_role="DOCTOR",
            notes=f"Consultation completed by Dr. {doctor_user.name}"
        )
        db.add(hist)

        db.commit()
        db.refresh(req)

        publish_domain_event("CONSULTATION_COMPLETED", {"request_id": req.id, "case_id": req.case_id})
        return TeleconsultationService.get_request_detail(db, req.id)
