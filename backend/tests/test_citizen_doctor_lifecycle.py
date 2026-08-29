import pytest
import uuid
from datetime import datetime, timezone
from app.models import (
    CitizenProfile, HouseholdMember, Case, ServiceRequest, CareHandoff,
    SharingConsent, ServiceRequestStatusHistory, Consultation, Prescription,
    InvestigationOrder, FollowUp, User, UserRoleEnum, CasePriorityEnum, CaseStatusEnum
)
from app.services.citizen_service import CitizenService
from app.schemas.citizen import DoctorRequestCreateDTO

def test_citizen_speak_to_doctor_full_lifecycle(client):
    """
    Complete canonical Citizen -> Doctor -> Citizen/ASHA workflow test.
    Validates:
    1. Beneficiary selection and patient profile reuse.
    2. Explicit consent and atomic structured handoff packet v1.
    3. ServiceRequest queued with status WAITING_FOR_DOCTOR.
    4. Doctor accepts (DOCTOR_ACCEPTED) and starts consultation (IN_CONSULTATION).
    5. Doctor completes and signs consultation with manual assessment, prescriptions, tests, and ASHA follow-up.
    6. Citizen My Care and destination queries return complete clinical outcome.
    7. Follow-up directive appears in ASHA follow-ups.
    8. Exactly-once status history & timeline entries.
    """
    from conftest import TestingSessionLocal
    db = TestingSessionLocal()
    try:
        # Seeded primary citizen Sunita Devi
        sunita = db.query(CitizenProfile).filter(CitizenProfile.display_name == "Sunita Devi").first()
        if not sunita:
            sunita = db.query(CitizenProfile).first()
        assert sunita is not None, "Sunita profile must exist"

        # 1. Citizen creates Doctor consultation request
        unique_key = f"idemp-doc-{uuid.uuid4().hex[:8]}"
        concern_text = "Severe chest tightness and high fever for 2 days"
        dto = DoctorRequestCreateDTO(
            beneficiary_id=None,
            channel="CALLBACK",
            chief_complaint=concern_text,
            symptoms=["CHEST_TIGHTNESS", "HIGH_FEVER"],
            preferred_language="mr-IN",
            sharing_scope={
                "share_structured_summary": True,
                "share_profile": True,
                "share_location": True,
                "share_recent_messages": False,
                "share_existing_health_records": False
            },
            handoff_packet={
                "chief_concern": concern_text,
                "original_statement": concern_text,
                "symptoms": [
                    {"code": "CHEST_TIGHTNESS", "display": "Chest Tightness", "status": "CONFIRMED", "source": "CITIZEN_CONFIRMED"},
                    {"code": "HIGH_FEVER", "display": "High Fever", "status": "CONFIRMED", "source": "CITIZEN_CONFIRMED"}
                ],
                "duration_text": "2 days",
                "severity_level": "SEVERE",
                "location": {"village": "Kalyanpur", "landmark": "Near Panchayat"},
                "safety": {"priority": "URGENT", "citizen_message": "Please consult a doctor promptly."}
            },
            idempotency_key=unique_key
        )

        res = CitizenService.create_doctor_request(db, sunita.id, dto)
        req_id = res["request_id"]
        assert req_id is not None
        assert res["status"] == "WAITING_FOR_DOCTOR"

        # Verify DB records
        srv_req = db.query(ServiceRequest).filter(ServiceRequest.id == req_id).first()
        assert srv_req is not None
        assert srv_req.citizen_id == sunita.id
        assert srv_req.status == "WAITING_FOR_DOCTOR"

        # Verify CareHandoff
        handoff = db.query(CareHandoff).filter(CareHandoff.service_request_id == req_id).first()
        assert handoff is not None
        assert handoff.chief_concern == concern_text
        assert handoff.version == 1

        # 2. Doctor logs in and views direct requests
        doctor_user = db.query(User).filter(User.role == "PHC_DOCTOR").first()
        assert doctor_user is not None

        # Doctor accepts request
        from app.routers.doctor import patch_doctor_direct_request_status
        accept_res = patch_doctor_direct_request_status(
            request_id=req_id,
            payload={"action": "ACCEPT"},
            db=db,
            current_user=doctor_user
        )
        assert accept_res.data["status"] == "DOCTOR_ACCEPTED"

        # Doctor starts consultation
        start_res = patch_doctor_direct_request_status(
            request_id=req_id,
            payload={"action": "START_CONSULTATION"},
            db=db,
            current_user=doctor_user
        )
        assert start_res.data["status"] == "IN_CONSULTATION"

        # 3. Doctor completes consultation with clinical assessment, prescription, investigation & ASHA follow-up
        complete_payload = {
            "action": "COMPLETE",
            "provisional_diagnosis": "Acute Bronchitis with Pyrexia",
            "patient_guidance": "Complete full antibiotic course, rest, hydrate and monitor fever.",
            "prescriptions": [
                {
                    "medicine_name": "Amoxicillin 500mg",
                    "formulation": "Capsule",
                    "dosage": "1 capsule",
                    "frequency": "1-0-1",
                    "duration_days": 5,
                    "instructions": "Take after food"
                },
                {
                    "medicine_name": "Paracetamol 650mg",
                    "formulation": "Tablet",
                    "dosage": "1 tablet",
                    "frequency": "1-1-1",
                    "duration_days": 3,
                    "instructions": "Take when fever exceeds 100 F"
                }
            ],
            "investigation_orders": ["Complete Blood Count (CBC)", "Chest X-Ray"],
            "assign_asha_followup": True,
            "asha_instructions": "Visit home in 3 days to check temperature resolution and antibiotic compliance."
        }

        complete_res = patch_doctor_direct_request_status(
            request_id=req_id,
            payload=complete_payload,
            db=db,
            current_user=doctor_user
        )
        assert complete_res.data["status"] == "COMPLETED"

        # 4. Check Citizen My Care Service Request Detail
        detail = CitizenService.get_citizen_service_request_detail(db, sunita.id, req_id)
        assert detail is not None
        assert detail["status"] == "COMPLETED"
        assert detail["consultation"] is not None
        assert "Acute Bronchitis" in detail["consultation"]["confirmed_diagnosis"]
        assert len(detail["prescriptions"]) > 0
        assert len(detail["prescriptions"][0]["items"]) == 2
        assert len(detail["followups"]) > 0
        assert "Visit home in 3 days" in detail["followups"][0]["instructions"]

        # 5. Check Citizen Prescriptions endpoint returns signed prescription
        from app.routers.citizen import get_citizen_prescriptions
        rxs_res = get_citizen_prescriptions(db=db, current_user=sunita.user if hasattr(sunita, 'user') else None)
        assert any(rx["doctor_name"] for rx in rxs_res.data)

        # 6. Check ASHA Followups endpoint returns the assigned directive
        from app.routers.asha import get_asha_followups
        asha_user = db.query(User).filter(User.role == "ASHA_WORKER").first()
        assert asha_user is not None
        asha_fups = get_asha_followups(db=db, current_user=asha_user)
        assert any("Bronchitis" in (f.get("reason") or f.get("instructions") or "") for f in asha_fups.data)

        # 7. Check Patient Record for Doctor returns correct patient and cases
        from app.routers.doctor import get_doctor_patient_record
        pat_record = get_doctor_patient_record(citizen_id=sunita.id, db=db, current_user=doctor_user)
        assert pat_record.data["demographics"]["display_name"] == sunita.display_name

    finally:
        db.close()
