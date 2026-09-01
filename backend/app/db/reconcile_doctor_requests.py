import logging
import uuid
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models import (
    ServiceRequest, TeleconsultationRequest, DoctorChatThread,
    CareHandoff, Case, SharingConsent, AuditLog, CitizenProfile, utc_now
)

logger = logging.getLogger("aarogya.reconciliation")


def reconcile_existing_doctor_requests(db: Session, target_facility_id: str = "PHC-09"):
    """
    Idempotent repair and reconciliation for all Doctor Consultation ServiceRequests.
    Guarantees:
    1. Every DOCTOR_CONSULTATION request is linked to a valid facility queue (defaulting to target_facility_id).
    2. Companion DoctorChatThread and TeleconsultationRequest exist for seamless real-time messaging & queue visibility.
    3. Audit logs record any reconciliation action taken.
    """
    try:
        requests = db.query(ServiceRequest).filter(
            ServiceRequest.request_type == "DOCTOR_CONSULTATION"
        ).all()

        repaired_count = 0

        for r in requests:
            changes_made = False

            # 1. Ensure facility linkage
            if not r.assigned_facility_id:
                r.assigned_facility_id = target_facility_id
                changes_made = True

            # 2. Reconcile legacy status names to canonical status enum
            if r.status in ["PENDING", "SUBMITTED"]:
                r.status = "WAITING_FOR_DOCTOR"
                changes_made = True

            # 3. Ensure companion DoctorChatThread
            thread = db.query(DoctorChatThread).filter(
                (DoctorChatThread.service_request_id == r.id) |
                (DoctorChatThread.id == r.id)
            ).first()

            if not thread:
                thread = DoctorChatThread(
                    id=str(uuid.uuid4()),
                    service_request_id=r.id,
                    citizen_id=r.citizen_id,
                    doctor_id=r.assigned_user_id,
                    facility_id=r.assigned_facility_id or target_facility_id,
                    channel="DOCTOR_CHAT" if (r.requested_channel or "CHAT").upper() in ["CHAT", "DOCTOR_CHAT", "CHAT_ADVICE"] else (r.requested_channel or "CALLBACK"),
                    status=r.status
                )
                db.add(thread)
                db.flush()
                changes_made = True

            # 4. Ensure companion TeleconsultationRequest
            tele_req = db.query(TeleconsultationRequest).filter(
                (TeleconsultationRequest.service_request_id == r.id) |
                (TeleconsultationRequest.id == thread.id) |
                (TeleconsultationRequest.public_reference == r.request_reference)
            ).first()

            if not tele_req:
                tele_req = TeleconsultationRequest(
                    id=thread.id,
                    public_reference=r.request_reference,
                    citizen_id=r.citizen_id,
                    household_member_id=r.beneficiary_id if r.beneficiary_id != r.citizen_id else None,
                    citizen_need_id=r.citizen_need_id or r.need_id,
                    service_request_id=r.id,
                    case_id=r.case_id,
                    facility_id=r.assigned_facility_id or target_facility_id,
                    assigned_doctor_id=r.assigned_user_id,
                    mode=r.requested_channel or "CHAT",
                    status=r.status,
                    priority=r.priority or "ROUTINE",
                    chief_complaint=r.details.get("chief_complaint", "Doctor consultation request") if r.details else "Doctor consultation request",
                    symptoms=r.details.get("symptoms", []) if r.details else [],
                    submitted_at=r.submitted_at or r.created_at or utc_now()
                )
                db.add(tele_req)
                db.flush()
                changes_made = True

            # 5. Ensure companion CareHandoff
            handoff = db.query(CareHandoff).filter(CareHandoff.service_request_id == r.id).first()
            if not handoff:
                chief_concern = r.details.get("chief_complaint", "General health checkup / care guidance") if r.details else "General health checkup / care guidance"
                handoff = CareHandoff(
                    version=1,
                    service_request_id=r.id,
                    citizen_id=r.citizen_id,
                    beneficiary_id=r.beneficiary_id,
                    citizen_need_id=r.citizen_need_id or r.need_id,
                    case_id=r.case_id,
                    request_type="DOCTOR_CONSULTATION",
                    requested_channel=r.requested_channel or "CHAT",
                    recipient_role="PHC_DOCTOR",
                    source="CITIZEN_HOME",
                    citizen_summary=f"{chief_concern} reported by citizen.",
                    chief_concern=chief_concern,
                    structured_payload=r.details or {},
                    created_at=r.created_at or utc_now()
                )
                db.add(handoff)
                db.flush()
                r.handoff_id = handoff.id
                changes_made = True

            if changes_made:
                repaired_count += 1
                audit = AuditLog(
                    id=str(uuid.uuid4()),
                    actor_role="SYSTEM",
                    actor_id="RECONCILIATION_SCRIPT",
                    action_type="DOCTOR_REQUEST_RECONCILED",
                    entity_type="service_requests",
                    entity_id=r.id,
                    facility_id=r.assigned_facility_id or target_facility_id,
                    details={
                        "request_reference": r.request_reference,
                        "status": r.status,
                        "facility_id": r.assigned_facility_id,
                        "thread_id": thread.id,
                        "reconciled_at": utc_now().isoformat()
                    }
                )
                db.add(audit)

        db.commit()
        if repaired_count > 0:
            logger.info(f"[Reconciliation] Successfully reconciled {repaired_count} Doctor Consultation records.")
        return repaired_count
    except Exception as e:
        db.rollback()
        logger.error(f"[Reconciliation] Error reconciling doctor requests: {e}", exc_info=True)
        return 0
