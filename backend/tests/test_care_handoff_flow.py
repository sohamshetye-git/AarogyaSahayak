import pytest
from app.models import (
    CitizenProfile, HouseholdMember, Case, ServiceRequest, CareHandoff,
    SharingConsent, ServiceRequestStatusHistory
)
from app.services.patient_resolution_service import PatientResolutionService
from app.services.citizen_service import CitizenService
from app.schemas.citizen import (
    DoctorRequestCreateDTO, AshaRequestCreateDTO, HandoffPreviewRequest
)
from datetime import datetime, timezone

def test_patient_resolution_existing_primary_citizen(client):
    """Test resolving candidate when candidate is the primary citizen."""
    from conftest import TestingSessionLocal
    db = TestingSessionLocal()
    try:
        # Sunita Devi is seeded with phone +919876543210
        primary = db.query(CitizenProfile).first()
        assert primary is not None

        res = PatientResolutionService.resolve_candidate(
            db=db,
            logged_in_citizen_id=primary.id,
            candidate_name="Sunita Devi",
            phone=primary.phone
        )

        assert res["resolution_type"] == "PRIMARY_CITIZEN"
        assert res["citizen_id"] == primary.id
        assert res["requires_duplicate_confirmation"] is False
    finally:
        db.close()

def test_patient_resolution_potential_duplicate_detection(client):
    """Test duplicate detection warns and requires confirmation when candidate matches an existing citizen."""
    from conftest import TestingSessionLocal
    db = TestingSessionLocal()
    try:
        primary = db.query(CitizenProfile).first()
        assert primary is not None

        # Resolve candidate with matching phone but not explicitly confirmed
        res = PatientResolutionService.resolve_candidate(
            db=db,
            logged_in_citizen_id=primary.id,
            candidate_name="Sunita Devi",
            phone=primary.phone,
            village_name=primary.village_name,
            confirm_register_new_duplicate=False
        )

        assert res["requires_duplicate_confirmation"] is False

        # Try a candidate with same phone as another profile but different name
        res_dup = PatientResolutionService.resolve_candidate(
            db=db,
            logged_in_citizen_id=primary.id,
            candidate_name="Anita Devi",
            phone=primary.phone,
            confirm_register_new_duplicate=False
        )

        assert res_dup["resolution_type"] == "POTENTIAL_DUPLICATE"
        assert res_dup["requires_duplicate_confirmation"] is True
        assert len(res_dup["potential_matches"]) > 0
        assert res_dup["potential_matches"][0]["masked_phone"].endswith("10")

        # Now confirm duplicate registration
        res_confirmed = PatientResolutionService.resolve_candidate(
            db=db,
            logged_in_citizen_id=primary.id,
            candidate_name="Anita Devi",
            phone=primary.phone,
            confirm_register_new_duplicate=True
        )
        assert res_confirmed["resolution_type"] == "NEW_PERSON"
        assert res_confirmed["requires_duplicate_confirmation"] is False
    finally:
        db.close()

def test_care_handoff_atomic_creation_doctor_request(client):
    """Test end-to-end atomic creation of Doctor consultation request from Citizen flow."""
    from conftest import TestingSessionLocal
    db = TestingSessionLocal()
    try:
        primary = db.query(CitizenProfile).first()
        assert primary is not None

        dto = DoctorRequestCreateDTO(
            channel="CALLBACK",
            chief_complaint="High fever and severe throat irritation",
            symptoms=["FEVER", "SORE_THROAT"],
            preferred_language="mr-IN",
            sharing_scope={
                "share_structured_summary": True,
                "share_profile": True,
                "share_location": True,
                "share_recent_messages": False,
                "share_existing_health_records": False
            },
            handoff_packet={
                "chief_concern": "High fever and severe throat irritation",
                "symptoms": [{"code": "FEVER", "display": "Fever", "status": "CONFIRMED", "source": "AI_STRUCTURED_CITIZEN_CONFIRMED"}]
            },
            idempotency_key="idemp-doc-test-12345"
        )

        res = CitizenService.create_doctor_request(db, primary.id, dto)

        assert "request_id" in res
        assert "case_id" in res
        assert "handoff_id" in res
        assert res["status"] in ["SUBMITTED", "WAITING_FOR_DOCTOR"]

        # Verify DB records
        srv_req = db.query(ServiceRequest).filter(ServiceRequest.id == res["request_id"]).first()
        assert srv_req is not None
        assert srv_req.citizen_id == primary.id
        assert srv_req.case_id == res["case_id"]
        assert srv_req.request_type == "DOCTOR_CONSULTATION"

        # Verify CareHandoff
        handoff = db.query(CareHandoff).filter(CareHandoff.service_request_id == srv_req.id).first()
        assert handoff is not None
        assert handoff.case_id == res["case_id"]
        assert handoff.citizen_id == primary.id
        assert handoff.version == 1

        # Verify SharingConsent
        consent = db.query(SharingConsent).filter(
            SharingConsent.citizen_id == primary.id,
            SharingConsent.recipient_role == "PHC_DOCTOR"
        ).order_by(SharingConsent.consented_at.desc()).first()
        assert consent is not None
        assert consent.recipient_role == "PHC_DOCTOR"
        assert consent.scope.get("share_structured_summary") is True

        # Test idempotency replay
        res_replay = CitizenService.create_doctor_request(db, primary.id, dto)
        assert res_replay["request_id"] == res["request_id"]
        assert res_replay["case_id"] == res["case_id"]
    finally:
        db.close()

def test_care_handoff_atomic_creation_asha_request(client):
    """Test atomic creation of ASHA assistance request with jurisdiction matching."""
    from conftest import TestingSessionLocal
    db = TestingSessionLocal()
    try:
        primary = db.query(CitizenProfile).first()
        assert primary is not None

        dto = AshaRequestCreateDTO(
            assistance_type="HOME_VISIT",
            preferred_time_window="MORNING",
            landmark="Near Kalyanpur Gram Panchayat",
            reason="Maternal wellness follow-up and blood pressure check",
            urgency="ROUTINE",
            sharing_scope={
                "share_structured_summary": True,
                "share_profile": True,
                "share_location": True,
                "share_recent_messages": False,
                "share_existing_health_records": False
            },
            handoff_packet={
                "chief_concern": "Maternal wellness follow-up",
                "location": {"landmark": "Near Kalyanpur Gram Panchayat"}
            },
            idempotency_key="idemp-asha-test-67890"
        )

        res = CitizenService.create_asha_request(db, primary.id, dto)

        assert "request_id" in res
        assert "case_id" in res
        assert "assigned_asha" in res

        srv_req = db.query(ServiceRequest).filter(ServiceRequest.id == res["request_id"]).first()
        assert srv_req is not None
        assert srv_req.request_type == "ASHA_ASSISTANCE"
        assert srv_req.assigned_role == "ASHA_WORKER"
    finally:
        db.close()

def test_cross_role_status_transitions_and_reconciliation(client):
    """Test ASHA and Doctor status transitions and cross-role case reconciliation."""
    from conftest import TestingSessionLocal
    db = TestingSessionLocal()
    try:
        primary = db.query(CitizenProfile).first()
        assert primary is not None

        dto = DoctorRequestCreateDTO(
            channel="CALLBACK",
            chief_complaint="Persistent abdominal pain",
            symptoms=["ABDOMINAL_PAIN"],
            sharing_scope={"share_structured_summary": True},
            idempotency_key="idemp-cross-role-9999"
        )

        res = CitizenService.create_doctor_request(db, primary.id, dto)
        req_id = res["request_id"]
        case_id = res["case_id"]

        # Doctor accepts request
        from app.routers.doctor import patch_doctor_direct_request_status
        from app.models import User
        doc_user = db.query(User).filter(User.role == "PHC_DOCTOR").first() or User(id="doc-1", name="Dr. Sharma", role="PHC_DOCTOR", username="doctor1")

        doc_accept = patch_doctor_direct_request_status(
            request_id=req_id,
            payload={"action": "ACCEPT"},
            db=db,
            current_user=doc_user
        )
        assert doc_accept.data["status"] == "DOCTOR_ACCEPTED"

        # Doctor completes request with diagnosis and prescription
        doc_complete = patch_doctor_direct_request_status(
            request_id=req_id,
            payload={
                "action": "COMPLETE",
                "provisional_diagnosis": "Acute Gastritis",
                "patient_guidance": "Avoid spicy foods and take antacids after meals.",
                "prescriptions": [
                    {
                        "medicine_name": "Pantoprazole 40mg",
                        "formulation": "Tablet",
                        "dosage": "1 tablet",
                        "frequency": "1-0-0",
                        "duration_days": 5,
                        "instructions": "Take before breakfast"
                    }
                ],
                "assign_asha_followup": True
            },
            db=db,
            current_user=doc_user
        )
        assert doc_complete.data["status"] == "COMPLETED"

        # Verify Case and Timeline reconciliation
        case = db.query(Case).filter(Case.id == case_id).first()
        assert case.status.value == "COMPLETED"

        timeline = CitizenService.get_citizen_timeline(db, primary.id, case_id)
        assert len(timeline) >= 2
        assert any(t["event_type"] == "CARE_COMPLETED" for t in timeline)
    finally:
        db.close()

def test_care_handoff_preview_validation_missing_concern(client):
    """Test preview generates structured editable draft packet even when initiated before chat symptoms are recorded."""
    from conftest import TestingSessionLocal
    db = TestingSessionLocal()
    try:
        primary = db.query(CitizenProfile).first()
        assert primary is not None

        # Call preview with no session and no need
        req = HandoffPreviewRequest(
            session_id=None,
            need_id=None,
            request_type="ASHA_ASSISTANCE"
        )
        packet = CitizenService.preview_handoff_packet(db, primary.id, req)
        assert packet is not None
        assert "chief_concern" in packet
        assert len(packet["symptoms"]) > 0
        assert packet["provenance"] if "provenance" in packet else True
    finally:
        db.close()

def test_care_handoff_preview_with_confirmed_need(client):
    """Test preview correctly formats packet when valid citizen need exists."""
    from conftest import TestingSessionLocal
    from app.models import CitizenNeed
    db = TestingSessionLocal()
    try:
        primary = db.query(CitizenProfile).first()
        assert primary is not None

        need = CitizenNeed(
            need_reference="NEED-TEST-001",
            citizen_id=primary.id,
            primary_intent="SYMPTOM_ASSESSMENT",
            confirmed_summary="Continuous dry cough and moderate fever",
            structured_facts={
                "symptoms": ["cough", "fever"],
                "negated_symptoms": ["chest_pain"],
                "duration": "3 days",
                "vitals": {"temperature_f": 100.4}
            }
        )
        db.add(need)
        db.commit()
        db.refresh(need)

        req = HandoffPreviewRequest(
            need_id=need.id,
            request_type="ASHA_ASSISTANCE"
        )
        packet = CitizenService.preview_handoff_packet(db, primary.id, req)
        assert packet is not None
        assert packet["chief_concern"] == "Continuous dry cough and moderate fever"
        assert len(packet["symptoms"]) == 2
        assert packet["duration"]["value"] == 3.0
        assert "Chest_Pain" in packet["negated_symptoms"] or "Chest Pain" in packet["negated_symptoms"]
        assert packet["safety"]["priority"] in ["ROUTINE", "URGENT", "EMERGENCY"]
    finally:
        db.close()

def test_service_request_ownership_check(client):
    """Test get_service_request_detail returns 403 for another citizen's request and 404 when non-existent."""
    from conftest import TestingSessionLocal
    db = TestingSessionLocal()
    try:
        primary = db.query(CitizenProfile).first()
        assert primary is not None

        # Create another citizen
        other_citizen = CitizenProfile(
            phone="+919999988888",
            display_name="Rajesh Kumar",
            village_name="Kalyanpur"
        )
        db.add(other_citizen)
        db.commit()
        db.refresh(other_citizen)

        # Create service request for other citizen
        dto = AshaRequestCreateDTO(
            assistance_type="HOME_VISIT",
            reason="Blood glucose monitoring",
            handoff_packet={"chief_concern": "Diabetes checkup"}
        )
        other_sr = CitizenService.create_asha_request(db, other_citizen.id, dto)

        # Now try to fetch it as primary citizen through router endpoint
        from app.routers.citizen import get_service_request_detail
        from fastapi import HTTPException

        # 404 test
        with pytest.raises(HTTPException) as exc_404:
            get_service_request_detail(
                request_id="non-existent-sr-id",
                db=db,
                current_user=primary.user
            )
        assert exc_404.value.status_code == 404

        # 403 test
        with pytest.raises(HTTPException) as exc_403:
            get_service_request_detail(
                request_id=other_sr["service_request_id"],
                db=db,
                current_user=primary.user
            )
        assert exc_403.value.status_code == 403
        assert "Forbidden" in exc_403.value.detail
    finally:
        db.close()
