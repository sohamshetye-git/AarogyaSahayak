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
    TeleconsultationMessage, TeleconsultationAttachment, InformationSourceEnum
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
        patient_name = "Self"
        patient_relation = "SELF"
        patient_age = None
        patient_gender = None
        patient_context = "GENERAL"

        if req.household_member_id:
            hm = db.query(HouseholdMember).filter(HouseholdMember.id == req.household_member_id).first()
            if hm:
                patient_name = hm.full_name
                patient_relation = hm.relationship_type
                patient_age = hm.age
                patient_gender = hm.sex
                if hm.is_pregnant:
                    patient_context = "MATERNAL"
                elif hm.age and hm.age <= 12:
                    patient_context = "CHILD"
        else:
            profile = db.query(CitizenProfile).filter(CitizenProfile.id == req.citizen_id).first()
            if profile:
                patient_name = profile.display_name
                patient_age = profile.age_estimate
                patient_gender = profile.sex
                if profile.is_pregnant:
                    patient_context = "MATERNAL"

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
            "public_reference": req.public_reference,
            "status": req.status,
            "priority": req.priority,
            "mode": req.mode,
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
            "service_request_id": req.id,
            "patient_profile_id": req.citizen_id,
            "patient_id": req.citizen_id,
            "citizen_id": req.citizen_id,
            "beneficiary_id": req.household_member_id,
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
                    "sender_type": m.sender_type,
                    "sender_name": m.sender_name,
                    "message_text": m.message_text,
                    "created_at": m.created_at.isoformat() if m.created_at else ""
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
    def send_message(db: Session, request_id: str, sender_type: str, sender_name: str, message_text: str, sender_id: Optional[str] = None) -> TeleconsultationMessage:
        msg = TeleconsultationMessage(
            request_id=request_id,
            sender_type=sender_type,
            sender_id=sender_id,
            sender_name=sender_name,
            message_text=message_text
        )
        db.add(msg)
        db.commit()
        db.refresh(msg)
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
        req = db.query(TeleconsultationRequest).filter(TeleconsultationRequest.id == request_id).first()
        if not req:
            raise ValueError("Teleconsultation request not found")

        old_status = req.status
        req.status = "DOCTOR_ACCEPTED"
        req.assigned_doctor_id = doctor_user.id
        req.accepted_at = datetime.now(timezone.utc)
        req.version += 1

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

        publish_domain_event("DOCTOR_REQUEST_ACCEPTED", {
            "request_id": req.id,
            "doctor_name": doctor_user.name
        })

        return TeleconsultationService.get_request_detail(db, req.id)

    @staticmethod
    def doctor_start_consultation(db: Session, request_id: str, doctor_user: User) -> Dict[str, Any]:
        req = db.query(TeleconsultationRequest).filter(TeleconsultationRequest.id == request_id).first()
        if not req:
            raise ValueError("Teleconsultation request not found")

        old_status = req.status
        req.status = "IN_CONSULTATION"
        req.started_at = datetime.now(timezone.utc)
        req.assigned_doctor_id = doctor_user.id
        req.version += 1

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

        publish_domain_event("CONSULTATION_STARTED", {"request_id": req.id})
        return TeleconsultationService.get_request_detail(db, req.id)

    @staticmethod
    def doctor_complete_consultation(db: Session, request_id: str, doctor_user: User, dto: DoctorCompleteTeleconsultationDTO) -> Dict[str, Any]:
        req = db.query(TeleconsultationRequest).filter(TeleconsultationRequest.id == request_id).first()
        if not req:
            raise ValueError("Teleconsultation request not found")

        old_status = req.status
        req.status = "COMPLETED"
        req.completed_at = datetime.now(timezone.utc)
        req.clinical_notes = dto.clinical_summary or dto.provisional_diagnosis
        req.disposition = dto.disposition
        req.patient_guidance = dto.patient_guidance or "Follow the prescribed care plan and take rest."
        req.version += 1

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
                order_reference=inv_ref,
                citizen_id=req.citizen_id,
                case_id=req.case_id,
                consultation_id=consultation.id,
                ordering_doctor_id=doctor_user.id,
                ordering_doctor_name=f"Dr. {doctor_user.name}",
                facility_id="PHC-09",
                test_name=inv_dto.get("test_name", "Complete Blood Count (CBC)"),
                test_category=inv_dto.get("category", "PATHOLOGY"),
                urgency=inv_dto.get("urgency", "ROUTINE"),
                clinical_indication=dto.provisional_diagnosis,
                status="ORDERED",
                patient_preparation_instructions=inv_dto.get("instructions", "Fasting not required")
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
