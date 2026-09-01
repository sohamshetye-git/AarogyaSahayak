import uuid
import re
import html
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from app.models import (
    User, CitizenProfile, HouseholdMember, ServiceRequest, TeleconsultationRequest,
    TeleconsultationMessage, DoctorChatThread, DoctorChatMessage, Facility, Case, utc_now
)
from app.services.event_bus import publish_domain_event


class DoctorChatService:

    @staticmethod
    def sanitize_message_body(text: str) -> str:
        """
        Sanitizes message text to prevent XSS and script injection.
        Disallows empty/whitespace-only messages, strips HTML tags, and truncates to 4000 characters.
        """
        if not text:
            raise ValueError("Message body cannot be empty")
        
        trimmed = text.strip()
        if not trimmed:
            raise ValueError("Message body cannot be whitespace only")

        # Reject or sanitize script tags
        cleaned = re.sub(r"<\s*script[^>]*>.*?<\s*/\s*script\s*>", "", trimmed, flags=re.IGNORECASE | re.DOTALL)
        cleaned = re.sub(r"<\s*style[^>]*>.*?<\s*/\s*style\s*>", "", cleaned, flags=re.IGNORECASE | re.DOTALL)
        cleaned = re.sub(r"<[^>]+>", "", cleaned)
        cleaned = html.escape(cleaned.strip())
        
        # Unescape basic punctuation that html.escape might turn into entities to keep user readability clean
        cleaned = cleaned.replace("&quot;", '"').replace("&#x27;", "'").replace("&amp;", "&")

        if not cleaned.strip():
            raise ValueError("Message body contains invalid content")

        if len(cleaned) > 4000:
            cleaned = cleaned[:4000]

        return cleaned

    @staticmethod
    def resolve_canonical_thread(
        db: Session,
        request_ref: str,
        citizen_profile_id: Optional[str] = None
    ) -> Tuple[DoctorChatThread, ServiceRequest, Optional[TeleconsultationRequest]]:
        """
        Resolves or creates the canonical DoctorChatThread for any request reference
        (DoctorChatThread.id, ServiceRequest.id, ServiceRequest.request_reference,
         TeleconsultationRequest.id, TeleconsultationRequest.public_reference, or Case.id).
        """
        db.expire_all()

        # 1. Direct match on DoctorChatThread.id
        thread = db.query(DoctorChatThread).filter(DoctorChatThread.id == request_ref).first()

        srv_req: Optional[ServiceRequest] = None
        tele_req: Optional[TeleconsultationRequest] = None

        if thread:
            srv_req = db.query(ServiceRequest).filter(ServiceRequest.id == thread.service_request_id).first()
            tele_req = db.query(TeleconsultationRequest).filter(
                (TeleconsultationRequest.service_request_id == thread.service_request_id) |
                (TeleconsultationRequest.id == thread.id)
            ).first()

        # 2. Match via ServiceRequest
        if not srv_req:
            srv_req = db.query(ServiceRequest).filter(
                (ServiceRequest.id == request_ref) |
                (ServiceRequest.request_reference == request_ref)
            ).first()

        # 3. Match via TeleconsultationRequest
        if not tele_req:
            tele_req = db.query(TeleconsultationRequest).filter(
                (TeleconsultationRequest.id == request_ref) |
                (TeleconsultationRequest.public_reference == request_ref) |
                (TeleconsultationRequest.service_request_id == request_ref)
            ).first()

        # 4. Match via Case ID or Case reference
        if not srv_req and not tele_req:
            case = db.query(Case).filter(
                (Case.id == request_ref) |
                (Case.reference == request_ref)
            ).first()
            if case:
                srv_req = db.query(ServiceRequest).filter(
                    ServiceRequest.case_id == case.id,
                    ServiceRequest.request_type == "DOCTOR_CONSULTATION"
                ).first()

        # Cross-link ServiceRequest and TeleconsultationRequest
        if srv_req and not tele_req:
            filters = [TeleconsultationRequest.service_request_id == srv_req.id]
            if srv_req.case_id:
                filters.append(TeleconsultationRequest.case_id == srv_req.case_id)
            if srv_req.request_reference:
                filters.append(TeleconsultationRequest.public_reference == srv_req.request_reference)
            tele_req = db.query(TeleconsultationRequest).filter(or_(*filters)).first()


        if tele_req and not srv_req and tele_req.service_request_id:
            srv_req = db.query(ServiceRequest).filter(ServiceRequest.id == tele_req.service_request_id).first()

        created_or_updated = False
        # If only tele_req exists without ServiceRequest, create ServiceRequest
        if tele_req and not srv_req:
            srv_ref = f"REQ-DOC-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:4]}"
            srv_req = ServiceRequest(
                request_reference=srv_ref,
                citizen_id=tele_req.citizen_id,
                beneficiary_id=tele_req.household_member_id,
                need_id=tele_req.citizen_need_id,
                citizen_need_id=tele_req.citizen_need_id,
                case_id=tele_req.case_id,
                request_type="DOCTOR_CONSULTATION",
                requested_channel="CHAT",
                status=tele_req.status or "WAITING_FOR_DOCTOR",
                priority=tele_req.priority or "ROUTINE",
                assigned_user_id=tele_req.assigned_doctor_id,
                assigned_facility_id=tele_req.facility_id or "PHC-09",
                details={
                    "chief_complaint": tele_req.chief_complaint,
                    "symptoms": tele_req.symptoms or [],
                    "mode": "CHAT"
                }
            )
            db.add(srv_req)
            db.flush()
            tele_req.service_request_id = srv_req.id
            created_or_updated = True

        # If only srv_req exists without TeleconsultationRequest, create TeleconsultationRequest
        if srv_req and not tele_req:
            tele_req = TeleconsultationRequest(
                public_reference=srv_req.request_reference,
                citizen_id=srv_req.citizen_id,
                household_member_id=srv_req.beneficiary_id,
                citizen_need_id=srv_req.need_id or srv_req.citizen_need_id,
                service_request_id=srv_req.id,
                case_id=srv_req.case_id,
                mode="CHAT",
                status=srv_req.status or "WAITING_FOR_DOCTOR",
                priority=srv_req.priority or "ROUTINE",
                facility_id=srv_req.assigned_facility_id or "PHC-09",
                assigned_doctor_id=srv_req.assigned_user_id,
                chief_complaint=srv_req.details.get("chief_complaint", "Doctor consultation requested") if srv_req.details else "Doctor consultation requested"
            )
            db.add(tele_req)
            db.flush()
            created_or_updated = True

        if not srv_req:
            raise ValueError(f"Could not resolve Doctor consultation request for '{request_ref}'")

        # Now ensure DoctorChatThread exists and is linked
        if not thread:
            thread = db.query(DoctorChatThread).filter(
                (DoctorChatThread.service_request_id == srv_req.id) |
                ((DoctorChatThread.id == tele_req.id) if tele_req else False)
            ).first()

        if not thread:
            thread_id = tele_req.id if tele_req else str(uuid.uuid4())
            # Ensure no ID collision
            existing_id_thread = db.query(DoctorChatThread).filter(DoctorChatThread.id == thread_id).first()
            if existing_id_thread:
                thread = existing_id_thread
            else:
                thread = DoctorChatThread(
                    id=thread_id,
                    service_request_id=srv_req.id,
                    citizen_id=srv_req.citizen_id,
                    doctor_id=srv_req.assigned_user_id,
                    facility_id=srv_req.assigned_facility_id or "PHC-09",
                    channel="DOCTOR_CHAT",
                    status=srv_req.status or "WAITING_FOR_DOCTOR"
                )
                db.add(thread)
                db.flush()
                created_or_updated = True

        # Keep thread attributes synced with latest request status & assigned doctor
        if thread.status != srv_req.status:
            thread.status = srv_req.status
            created_or_updated = True
        if srv_req.assigned_user_id and thread.doctor_id != srv_req.assigned_user_id:
            thread.doctor_id = srv_req.assigned_user_id
            created_or_updated = True

        if created_or_updated:
            thread.updated_at = datetime.now(timezone.utc)
            db.add(thread)
            db.commit()
            db.refresh(thread)
            db.refresh(srv_req)
            if tele_req:
                db.refresh(tele_req)

        return thread, srv_req, tele_req


    @staticmethod
    def get_thread_envelope(
        db: Session,
        request_ref: str,
        current_user: Optional[User] = None,
        citizen_profile: Optional[CitizenProfile] = None
    ) -> Dict[str, Any]:
        """
        Retrieves thread details along with full message history and request metadata.
        """
        thread, srv_req, tele_req = DoctorChatService.resolve_canonical_thread(db, request_ref)

        # Beneficiary / Patient info
        citizen = srv_req.citizen or (db.query(CitizenProfile).filter(CitizenProfile.id == srv_req.citizen_id).first())
        beneficiary = None
        if srv_req.beneficiary_id and srv_req.beneficiary_id != srv_req.citizen_id:
            beneficiary = srv_req.beneficiary or (db.query(HouseholdMember).filter(HouseholdMember.id == srv_req.beneficiary_id).first())

        patient_name = "Citizen"
        patient_relation = "SELF"
        if beneficiary and beneficiary.full_name and beneficiary.full_name.strip().lower() not in ["self", "myself"]:
            patient_name = beneficiary.full_name
            patient_relation = beneficiary.relationship_type or "FAMILY"
        elif citizen and citizen.display_name and citizen.display_name.strip().lower() not in ["self", "myself"]:
            patient_name = citizen.display_name
        elif citizen and citizen.user and citizen.user.name:
            patient_name = citizen.user.name

        citizen_name = citizen.display_name if citizen else "Citizen"
        doctor = srv_req.assigned_user or (db.query(User).filter(User.id == srv_req.assigned_user_id).first() if srv_req.assigned_user_id else None)
        doctor_name = doctor.name if doctor else (tele_req.assigned_doctor.name if tele_req and tele_req.assigned_doctor else None)

        chief_complaint = None
        if srv_req.details and isinstance(srv_req.details, dict):
            chief_complaint = srv_req.details.get("chief_complaint")
        if not chief_complaint and tele_req:
            chief_complaint = tele_req.chief_complaint

        # Fetch all messages for this canonical thread
        messages = DoctorChatService.get_messages(db, thread.id)

        thread_dto = {
            "id": thread.id,
            "conversation_id": thread.id,
            "service_request_id": srv_req.id,
            "request_reference": srv_req.request_reference,
            "public_reference": tele_req.public_reference if tele_req else srv_req.request_reference,
            "citizen_id": srv_req.citizen_id,
            "citizen_name": citizen_name,
            "beneficiary_id": srv_req.beneficiary_id,
            "beneficiary_name": patient_name,
            "doctor_id": srv_req.assigned_user_id,
            "doctor_name": doctor_name,
            "facility_id": srv_req.assigned_facility_id or "PHC-09",
            "facility_name": "Kalyanpur Primary Health Centre (PHC-09)",
            "channel": "DOCTOR_CHAT",
            "status": srv_req.status or thread.status,
            "chief_complaint": chief_complaint or "Doctor chat advice consultation",
            "created_at": thread.created_at.isoformat() if thread.created_at else "",
            "updated_at": thread.updated_at.isoformat() if thread.updated_at else None,
            "messages": messages
        }

        return {
            "thread": thread_dto,
            "messages": messages,
            "request_details": {
                "id": srv_req.id,
                "service_request_id": srv_req.id,
                "conversation_id": thread.id,
                "request_reference": srv_req.request_reference,
                "channel": srv_req.requested_channel or "CHAT",
                "requested_channel": srv_req.requested_channel or "CHAT",
                "status": srv_req.status,
                "priority": srv_req.priority,
                "case_id": srv_req.case_id,
                "submitted_at": srv_req.submitted_at.isoformat() if srv_req.submitted_at else None,
                "acknowledged_at": srv_req.acknowledged_at.isoformat() if srv_req.acknowledged_at else None,
                "completed_at": srv_req.completed_at.isoformat() if srv_req.completed_at else None,
                "patient": {
                    "id": srv_req.beneficiary_id or srv_req.citizen_id,
                    "name": patient_name,
                    "phone": citizen.phone if citizen else None,
                    "relationship": patient_relation
                }
            }
        }

    @staticmethod
    def get_messages(db: Session, thread_id: str, after: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Retrieves all messages for a thread, merging canonical doctor_chat_messages and any
        matching teleconsultation_messages seamlessly.
        """
        thread, srv_req, tele_req = DoctorChatService.resolve_canonical_thread(db, thread_id)
        canonical_thread_id = thread.id if thread else thread_id
        srv_id = srv_req.id if srv_req else (thread.service_request_id if thread else None)
        tele_id = tele_req.id if tele_req else None

        # 1. Fetch canonical messages
        q_canonical = db.query(DoctorChatMessage).filter(
            (DoctorChatMessage.conversation_id == canonical_thread_id) |
            ((DoctorChatMessage.service_request_id == srv_id) if srv_id else False)
        )
        if after:
            try:
                after_dt = datetime.fromisoformat(after.replace("Z", "+00:00"))
                q_canonical = q_canonical.filter(DoctorChatMessage.created_at > after_dt)
            except Exception:
                pass
        canonical_msgs = q_canonical.order_by(DoctorChatMessage.created_at.asc()).all()

        # 2. Fetch any legacy messages that may have been created directly in teleconsultation_messages
        legacy_msgs = []
        if tele_id:
            q_leg = db.query(TeleconsultationMessage).filter(
                TeleconsultationMessage.request_id == tele_id
            )
            if after:
                try:
                    after_dt = datetime.fromisoformat(after.replace("Z", "+00:00"))
                    q_leg = q_leg.filter(TeleconsultationMessage.created_at > after_dt)
                except Exception:
                    pass
            legacy_msgs = q_leg.order_by(TeleconsultationMessage.created_at.asc()).all()

        # Deduplicate and combine by client_message_id or message body + timestamp
        seen_client_ids = set()
        seen_ids = set()
        seen_texts = set()
        results: List[Dict[str, Any]] = []

        # Process canonical first
        for m in canonical_msgs:
            if m.client_message_id:
                seen_client_ids.add(m.client_message_id)
            seen_ids.add(m.id)
            if m.body:
                seen_texts.add((m.body.strip(), m.sender_role))
            deliv_status = getattr(m, "delivery_status", None) or m.status or "DELIVERED"
            results.append({
                "id": m.id,
                "conversation_id": m.conversation_id,
                "service_request_id": m.service_request_id or srv_id,
                "sender_role": m.sender_role,
                "sender_user_id": m.sender_user_id or m.sender_id,
                "sender_id": m.sender_id or m.sender_user_id,
                "sender_name": m.sender_name,
                "body": m.body,
                "message_text": m.body,
                "client_message_id": m.client_message_id,
                "status": m.status,
                "delivery_status": deliv_status,
                "created_at": m.created_at.isoformat() if m.created_at else "",
                "delivered_at": m.delivered_at.isoformat() if m.delivered_at else None,
                "read_at": m.read_at.isoformat() if m.read_at else None,
                "sender_type": "DOCTOR" if m.sender_role == "PHC_DOCTOR" else "CITIZEN"
            })

        # Process legacy, adding any that are not already in canonical
        for lm in legacy_msgs:
            c_id = getattr(lm, "client_message_id", None) or lm.id
            role = "PHC_DOCTOR" if lm.sender_type == "DOCTOR" else "CITIZEN"
            text_sig = ((lm.message_text or "").strip(), role)
            if (c_id and c_id in seen_client_ids) or (lm.id in seen_ids) or (text_sig in seen_texts):
                continue
            if c_id:
                seen_client_ids.add(c_id)
            seen_ids.add(lm.id)
            if lm.message_text:
                seen_texts.add(text_sig)
            results.append({
                "id": lm.id,
                "conversation_id": thread_id,
                "service_request_id": srv_id,
                "sender_role": role,
                "sender_user_id": lm.sender_id if role == "PHC_DOCTOR" else None,
                "sender_id": lm.sender_id,
                "sender_name": lm.sender_name,
                "body": lm.message_text or "",
                "message_text": lm.message_text or "",
                "client_message_id": c_id,
                "status": "DELIVERED",
                "delivery_status": "DELIVERED",
                "created_at": lm.created_at.isoformat() if lm.created_at else "",
                "delivered_at": lm.created_at.isoformat() if lm.created_at else None,
                "read_at": None,
                "sender_type": lm.sender_type
            })

        # Sort all by created_at
        results.sort(key=lambda x: x.get("created_at") or "")
        return results

    @staticmethod
    def post_message(
        db: Session,
        conversation_id: str,
        sender_role: str,
        sender_id: Optional[str],
        sender_name: Optional[str],
        body: str,
        client_message_id: str,
        message_type: str = "TEXT"
    ) -> Dict[str, Any]:
        """
        Persists a message into the canonical DoctorChatThread, validates lifecycle & permissions,
        and broadcasts realtime events across WebSocket topics.
        """
        thread, srv_req, tele_req = DoctorChatService.resolve_canonical_thread(db, conversation_id)

        # 1. Clinical Lifecycle Validation
        if (
            (srv_req and srv_req.status in ["COMPLETED", "CANCELLED", "EXPIRED"]) or
            (thread and thread.status in ["COMPLETED", "CANCELLED", "EXPIRED"]) or
            (tele_req and tele_req.status in ["COMPLETED", "CANCELLED", "EXPIRED"])
        ):
            status_val = srv_req.status if (srv_req and srv_req.status in ["COMPLETED", "CANCELLED", "EXPIRED"]) else (thread.status if thread else "COMPLETED")
            raise ValueError(f"Cannot send message: Consultation is in terminal state '{status_val}'")

        # 2. Doctor Role & Assignment Validation
        if sender_role == "PHC_DOCTOR":
            if srv_req.status == "WAITING_FOR_DOCTOR":
                # Automatically transition to DOCTOR_ACCEPTED if the doctor hasn't explicitly clicked accept yet
                srv_req.status = "DOCTOR_ACCEPTED"
                srv_req.assigned_user_id = sender_id
                srv_req.acknowledged_at = datetime.now(timezone.utc)
                if tele_req:
                    tele_req.status = "DOCTOR_ACCEPTED"
                    tele_req.assigned_doctor_id = sender_id
                    tele_req.accepted_at = datetime.now(timezone.utc)
                thread.status = "DOCTOR_ACCEPTED"
                thread.doctor_id = sender_id

            elif srv_req.assigned_user_id and sender_id and srv_req.assigned_user_id != sender_id:
                # If assigned to a different doctor, prevent cross-doctor message hijacking
                raise ValueError("This consultation is currently assigned to another doctor")

        # 3. Clean & Sanitize Body
        cleaned_body = DoctorChatService.sanitize_message_body(body)

        # 4. Idempotency Check by client_message_id
        existing_msg = db.query(DoctorChatMessage).filter(
            DoctorChatMessage.client_message_id == client_message_id
        ).first()
        if existing_msg:
            return {
                "id": existing_msg.id,
                "conversation_id": thread.id,
                "service_request_id": srv_req.id,
                "sender_role": existing_msg.sender_role,
                "sender_user_id": existing_msg.sender_user_id or existing_msg.sender_id,
                "sender_id": existing_msg.sender_id or existing_msg.sender_user_id,
                "sender_name": existing_msg.sender_name,
                "body": existing_msg.body,
                "message_text": existing_msg.body,
                "client_message_id": existing_msg.client_message_id,
                "status": existing_msg.status,
                "delivery_status": getattr(existing_msg, "delivery_status", None) or existing_msg.status or "DELIVERED",
                "created_at": existing_msg.created_at.isoformat() if existing_msg.created_at else "",
                "delivered_at": existing_msg.delivered_at.isoformat() if existing_msg.delivered_at else None,
                "read_at": existing_msg.read_at.isoformat() if existing_msg.read_at else None,
                "sender_type": "DOCTOR" if existing_msg.sender_role == "PHC_DOCTOR" else "CITIZEN"
            }

        # 5. Insert canonical DoctorChatMessage
        now_dt = datetime.now(timezone.utc)
        msg_id = str(uuid.uuid4())
        canonical_msg = DoctorChatMessage(
            id=msg_id,
            conversation_id=thread.id,
            service_request_id=srv_req.id,
            sender_role=sender_role,
            sender_user_id=sender_id,
            sender_id=sender_id,
            sender_name=sender_name,
            body=cleaned_body,
            client_message_id=client_message_id,
            status="DELIVERED",
            delivery_status="DELIVERED",
            created_at=now_dt,
            delivered_at=now_dt
        )
        db.add(canonical_msg)

        # 6. Mirror to TeleconsultationMessage for backwards compatibility
        if tele_req:
            legacy_msg = TeleconsultationMessage(
                id=msg_id,
                request_id=tele_req.id,
                sender_type="DOCTOR" if sender_role == "PHC_DOCTOR" else "CITIZEN",
                sender_id=sender_id,
                sender_name=sender_name,
                message_text=cleaned_body,
                created_at=now_dt
            )
            db.add(legacy_msg)

        thread.updated_at = now_dt
        db.add(thread)
        db.commit()
        db.refresh(canonical_msg)

        # 7. Realtime Synchronization Event Payloads
        event_payload = {
            "id": canonical_msg.id,
            "message_id": canonical_msg.id,
            "conversation_id": thread.id,
            "request_id": thread.id,
            "service_request_id": srv_req.id,
            "request_reference": srv_req.request_reference,
            "sender_role": sender_role,
            "sender_type": "DOCTOR" if sender_role == "PHC_DOCTOR" else "CITIZEN",
            "sender_user_id": sender_id,
            "sender_id": sender_id,
            "sender_name": sender_name,
            "body": cleaned_body,
            "message_text": cleaned_body,
            "client_message_id": client_message_id,
            "status": canonical_msg.status,
            "delivery_status": canonical_msg.delivery_status or "DELIVERED",
            "created_at": canonical_msg.created_at.isoformat(),
            "delivered_at": canonical_msg.delivered_at.isoformat() if canonical_msg.delivered_at else None
        }

        # Publish canonical and backward-compatible domain events
        publish_domain_event("conversation.message.created", event_payload)
        publish_domain_event("doctor_chat.message_created", event_payload)
        publish_domain_event("CHAT_MESSAGE_CREATED", event_payload)
        publish_domain_event("DOCTOR_REQUEST_MESSAGE_SENT", event_payload)

        return {
            "id": canonical_msg.id,
            "conversation_id": thread.id,
            "service_request_id": srv_req.id,
            "sender_role": canonical_msg.sender_role,
            "sender_user_id": canonical_msg.sender_user_id or canonical_msg.sender_id,
            "sender_id": canonical_msg.sender_id or canonical_msg.sender_user_id,
            "sender_name": canonical_msg.sender_name,
            "body": canonical_msg.body,
            "message_text": canonical_msg.body,
            "client_message_id": canonical_msg.client_message_id,
            "status": canonical_msg.status,
            "delivery_status": canonical_msg.delivery_status or "DELIVERED",
            "created_at": canonical_msg.created_at.isoformat(),
            "delivered_at": canonical_msg.delivered_at.isoformat() if canonical_msg.delivered_at else None,
            "read_at": canonical_msg.read_at.isoformat() if canonical_msg.read_at else None,
            "sender_type": "DOCTOR" if canonical_msg.sender_role == "PHC_DOCTOR" else "CITIZEN"
        }


    @staticmethod
    def mark_messages_read(
        db: Session,
        conversation_id: str,
        reader_role: str,
        reader_id: Optional[str] = None,
        up_to_message_id: Optional[str] = None,
        message_ids: Optional[List[str]] = None
    ) -> int:
        """
        Marks unread messages in the thread as READ.
        """
        thread, srv_req, _ = DoctorChatService.resolve_canonical_thread(db, conversation_id)
        now_dt = datetime.now(timezone.utc)

        # Identify messages sent by the counter-party
        target_role = "CITIZEN" if reader_role == "PHC_DOCTOR" else "PHC_DOCTOR"

        q = db.query(DoctorChatMessage).filter(
            DoctorChatMessage.conversation_id == thread.id,
            DoctorChatMessage.sender_role == target_role,
            DoctorChatMessage.status != "READ"
        )

        if message_ids:
            q = q.filter(DoctorChatMessage.id.in_(message_ids))
        elif up_to_message_id:
            ref_msg = db.query(DoctorChatMessage).filter(DoctorChatMessage.id == up_to_message_id).first()
            if ref_msg:
                q = q.filter(DoctorChatMessage.created_at <= ref_msg.created_at)

        unread_msgs = q.all()
        count = len(unread_msgs)

        for m in unread_msgs:
            m.status = "READ"
            m.read_at = now_dt
            db.add(m)

        # Also update matching legacy messages
        if count > 0:
            msg_ids = [m.id for m in unread_msgs]
            legacy_unread = db.query(TeleconsultationMessage).filter(
                TeleconsultationMessage.id.in_(msg_ids)
            ).all()
            for lm in legacy_unread:
                lm.status = "READ"
                lm.read_at = now_dt
                db.add(lm)

            db.commit()

            publish_domain_event("doctor_chat.message_read", {
                "conversation_id": thread.id,
                "reader_role": reader_role,
                "reader_id": reader_id,
                "message_ids": msg_ids,
                "read_at": now_dt.isoformat()
            })
            publish_domain_event("CHAT_MESSAGE_READ", {
                "conversation_id": thread.id,
                "message_id": msg_ids[-1] if msg_ids else None,
                "reader_role": reader_role,
                "read_at": now_dt.isoformat()
            })

        return count
