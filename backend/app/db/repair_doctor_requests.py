import os
import sys
import uuid
from datetime import datetime, timezone

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from app.database import SessionLocal
from app.models import (
    ServiceRequest, CareHandoff, TeleconsultationRequest,
    DoctorChatThread, CitizenProfile, User, AuditLog, Case, Facility
)

def utc_now():
    return datetime.now(timezone.utc)

def repair_doctor_citizen_requests(db=None):
    """
    Idempotent repair script:
    1. Scans all ServiceRequests of type DOCTOR_CONSULTATION.
    2. Ensures assigned_facility_id is set (mapping from citizen care location / default PHC-09).
    3. Ensures companion DoctorChatThread and TeleconsultationRequest exist and have matching status.
    4. Writes AuditLog entry for each repaired record.
    """
    close_db_at_end = False
    if db is None:
        db = SessionLocal()
        close_db_at_end = True

    try:
        repaired_count = 0
        requests = db.query(ServiceRequest).filter(
            ServiceRequest.request_type == "DOCTOR_CONSULTATION"
        ).all()

        print(f"[REPAIR] Auditing {len(requests)} doctor consultation service requests...")

        # Ensure default facility exists
        default_fac = db.query(Facility).filter(Facility.id == "PHC-09").first()
        if not default_fac:
            default_fac = Facility(
                id="PHC-09",
                name="Kalyanpur Primary Health Centre",
                type="PHC",
                district="District 04",
                is_active=True
            )
            db.add(default_fac)
            db.flush()

        for srv in requests:
            repaired_fields = []

            # 1. Check & Repair facility_id
            if not srv.assigned_facility_id:
                # Infer from citizen or default to PHC-09
                target_fac = "PHC-09"
                if srv.citizen and srv.citizen.assigned_facility_id:
                    target_fac = srv.citizen.assigned_facility_id
                srv.assigned_facility_id = target_fac
                repaired_fields.append(f"assigned_facility_id->{target_fac}")

            # 2. Check & Repair assigned_role
            if not srv.assigned_role:
                srv.assigned_role = "PHC_DOCTOR"
                repaired_fields.append("assigned_role->PHC_DOCTOR")

            # 3. Check status validity
            if srv.status in ["PENDING", "ASSIGNMENT_PENDING", "SUBMITTED"]:
                srv.status = "WAITING_FOR_DOCTOR"
                repaired_fields.append(f"status->WAITING_FOR_DOCTOR")

            # 4. Check / Create companion CareHandoff
            handoff = db.query(CareHandoff).filter(CareHandoff.service_request_id == srv.id).first()
            if not handoff:
                chief = (srv.details or {}).get("chief_complaint") or "Teleconsultation direct request"
                handoff = CareHandoff(
                    id=str(uuid.uuid4()),
                    version=1,
                    service_request_id=srv.id,
                    citizen_id=srv.citizen_id,
                    beneficiary_id=srv.beneficiary_id,
                    chat_session_id=srv.chat_session_id,
                    citizen_need_id=srv.citizen_need_id or srv.need_id,
                    case_id=srv.case_id,
                    request_type="DOCTOR_CONSULTATION",
                    requested_channel=srv.requested_channel or "CALLBACK",
                    recipient_role="PHC_DOCTOR",
                    source="CITIZEN_HOME",
                    citizen_summary=f"{chief} (Citizen Care Handoff)",
                    chief_concern=chief,
                    structured_payload={
                        "chief_concern": chief,
                        "symptoms": (srv.details or {}).get("symptoms", []),
                        "channel": srv.requested_channel or "CALLBACK"
                    },
                    created_at=srv.created_at or utc_now()
                )
                db.add(handoff)
                db.flush()
                srv.handoff_id = handoff.id
                repaired_fields.append(f"created CareHandoff:{handoff.id}")

            # 5. Check / Synchronize companion TeleconsultationRequest
            tele_req = db.query(TeleconsultationRequest).filter(
                (TeleconsultationRequest.service_request_id == srv.id) |
                (TeleconsultationRequest.public_reference == srv.request_reference)
            ).first()

            if not tele_req:
                tele_req = TeleconsultationRequest(
                    id=str(uuid.uuid4()),
                    public_reference=srv.request_reference,
                    citizen_id=srv.citizen_id,
                    household_member_id=srv.beneficiary_id if srv.beneficiary_id != srv.citizen_id else None,
                    citizen_need_id=srv.citizen_need_id or srv.need_id,
                    service_request_id=srv.id,
                    case_id=srv.case_id,
                    facility_id=srv.assigned_facility_id,
                    assigned_doctor_id=srv.assigned_user_id,
                    mode=srv.requested_channel or "CALLBACK",
                    status=srv.status,
                    priority=srv.priority or "ROUTINE",
                    chief_complaint=(srv.details or {}).get("chief_complaint") or handoff.chief_concern,
                    symptoms=(srv.details or {}).get("symptoms", []),
                    submitted_at=srv.submitted_at or srv.created_at or utc_now(),
                    idempotency_key=srv.idempotency_key
                )
                db.add(tele_req)
                db.flush()
                repaired_fields.append(f"created TeleconsultationRequest:{tele_req.id}")
            else:
                # Sync status and facility if out of sync
                if tele_req.status != srv.status:
                    tele_req.status = srv.status
                    repaired_fields.append(f"tele_req.status->{srv.status}")
                if tele_req.facility_id != srv.assigned_facility_id:
                    tele_req.facility_id = srv.assigned_facility_id
                    repaired_fields.append(f"tele_req.facility_id->{srv.assigned_facility_id}")
                if tele_req.assigned_doctor_id != srv.assigned_user_id:
                    tele_req.assigned_doctor_id = srv.assigned_user_id
                    repaired_fields.append(f"tele_req.assigned_doctor_id->{srv.assigned_user_id}")

            # 6. Check / Synchronize companion DoctorChatThread
            thread = db.query(DoctorChatThread).filter(
                (DoctorChatThread.service_request_id == srv.id) |
                (DoctorChatThread.id == tele_req.id)
            ).first()

            if not thread:
                thread = DoctorChatThread(
                    id=tele_req.id,
                    service_request_id=srv.id,
                    citizen_id=srv.citizen_id,
                    doctor_id=srv.assigned_user_id,
                    facility_id=srv.assigned_facility_id,
                    channel="DOCTOR_CHAT",
                    status=srv.status
                )
                db.add(thread)
                repaired_fields.append(f"created DoctorChatThread:{thread.id}")
            else:
                if thread.status != srv.status:
                    thread.status = srv.status
                    repaired_fields.append(f"thread.status->{srv.status}")
                if thread.doctor_id != srv.assigned_user_id:
                    thread.doctor_id = srv.assigned_user_id
                    repaired_fields.append(f"thread.doctor_id->{srv.assigned_user_id}")

            # If repairs were made, log audit record
            if repaired_fields:
                repaired_count += 1
                audit = AuditLog(
                    actor_user_id="SYSTEM_MIGRATION",
                    actor_role="SYSTEM",
                    action="REPAIR_DOCTOR_SERVICE_REQUEST",
                    resource_type="service_requests",
                    resource_id=srv.id,
                    outcome="SUCCESS",
                    metadata_json={
                        "request_reference": srv.request_reference,
                        "repaired_fields": repaired_fields,
                        "timestamp": utc_now().isoformat()
                    }
                )
                db.add(audit)
                print(f"  [REPAIRED] SR {srv.request_reference}: {', '.join(repaired_fields)}")

        db.commit()
        print(f"[REPAIR COMPLETE] Repaired and reconciled {repaired_count} records.")
        return repaired_count
    finally:
        if close_db_at_end:
            db.close()

if __name__ == "__main__":
    repair_doctor_citizen_requests()
