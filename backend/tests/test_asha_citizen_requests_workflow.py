import pytest
from app.models import (
    CitizenProfile, HouseholdMember, Case, ServiceRequest, CareHandoff,
    SharingConsent, ServiceRequestStatusHistory, User, Referral, FollowUp
)
from app.services.citizen_service import CitizenService
from app.schemas.citizen import AshaRequestCreateDTO
from fastapi import HTTPException
from datetime import datetime, timezone

def test_list_contains_valid_service_request_id_and_canonical_contract(client):
    """Test ASHA citizen requests list endpoint returns canonical contract and valid ServiceRequest ID."""
    from conftest import TestingSessionLocal
    db = TestingSessionLocal()
    try:
        primary = db.query(CitizenProfile).first()
        assert primary is not None

        # Create an ASHA assistance request
        dto = AshaRequestCreateDTO(
            assistance_type="HOME_VISIT",
            preferred_time_window="MORNING",
            landmark="Near Kalyanpur Temple",
            reason="Blood pressure measurement and maternal follow-up",
            urgency="ROUTINE",
            sharing_scope={"share_structured_summary": True, "share_profile": True},
            handoff_packet={
                "chief_concern": "Blood pressure check",
                "symptoms": ["Mild headache"],
                "location": {"landmark": "Near Kalyanpur Temple"}
            },
            idempotency_key="idemp-list-contract-001"
        )
        res = CitizenService.create_asha_request(db, primary.id, dto)
        req_id = res["service_request_id"]
        assert req_id is not None

        # Fetch ASHA citizen requests list
        from app.routers.asha import get_asha_citizen_requests
        asha_user = db.query(User).filter(User.role == "ASHA_WORKER").first() or User(id="asha-1", name="Sita Patel", role="ASHA_WORKER")
        
        list_res = get_asha_citizen_requests(db=db, current_user=asha_user)
        assert list_res is not None
        items = list_res.data
        assert len(items) > 0

        match = next((item for item in items if item["id"] == req_id), None)
        assert match is not None
        # Canonical List Contract Assertions
        assert match["id"] == req_id
        assert match["request_reference"].startswith("ASHAREQ-")
        assert match["request_type"] == "ASHA_ASSISTANCE"
        assert match["source"] == "CITIZEN_CHAT"
        assert match["status"] in ["ASHA_ASSIGNED", "ASSIGNMENT_PENDING", "NEW", "SUBMITTED"]
        assert match["priority"] in ["ROUTINE", "URGENT"]
        assert match["citizen_id"] == primary.id
        assert match["citizen_name"] == primary.display_name
        assert match["village"] == (primary.village_name or "Kalyanpur")
        assert "created_at" in match
    finally:
        db.close()

def test_detail_endpoint_and_authorization_checks(client):
    """Test detail endpoint returns matching request, 404 on missing, and 403 on unauthorized ASHA."""
    from conftest import TestingSessionLocal
    from app.routers.asha import get_asha_citizen_request_detail
    db = TestingSessionLocal()
    try:
        primary = db.query(CitizenProfile).first()
        assert primary is not None

        dto = AshaRequestCreateDTO(
            assistance_type="HOME_VISIT",
            reason="Routine antenatal check",
            handoff_packet={"chief_concern": "Routine antenatal check"},
            idempotency_key="idemp-detail-auth-001"
        )
        res = CitizenService.create_asha_request(db, primary.id, dto)
        req_id = res["service_request_id"]

        asha_user = db.query(User).filter(User.role == "ASHA_WORKER").first() or User(id="asha-1", name="Sita Patel", role="ASHA_WORKER")

        # 1. Successful fetch
        detail_res = get_asha_citizen_request_detail(request_id=req_id, db=db, current_user=asha_user)
        assert detail_res.data["id"] == req_id
        assert detail_res.data["request_reference"] == res["request_reference"]
        assert detail_res.data["citizen_name"] == primary.display_name
        assert "consent" in detail_res.data
        assert "patient_context" in detail_res.data
        assert "status_history" in detail_res.data

        # 2. 404 test on non-existent request ID
        with pytest.raises(HTTPException) as exc_404:
            get_asha_citizen_request_detail(request_id="00000000-0000-0000-0000-000000000000", db=db, current_user=asha_user)
        assert exc_404.value.status_code == 404

        # 3. 403 test on another ASHA worker if explicitly assigned
        other_asha = User(
            id="other-asha-999",
            identifier="geetabai",
            name="Geeta Bai",
            role="ASHA_WORKER",
            password_hash="mockhash"
        )
        db.add(other_asha)
        db.flush()

        sr = db.query(ServiceRequest).filter(ServiceRequest.id == req_id).first()
        sr.assigned_user_id = asha_user.id
        db.commit()

        with pytest.raises(HTTPException) as exc_403:
            get_asha_citizen_request_detail(request_id=req_id, db=db, current_user=other_asha)
        assert exc_403.value.status_code == 403
    finally:
        db.close()

def test_duplicate_submission_protection_and_reuse(client):
    """Test duplicate submission returns existing request with reused_existing_request: true."""
    from conftest import TestingSessionLocal
    db = TestingSessionLocal()
    try:
        primary = db.query(CitizenProfile).first()
        assert primary is not None

        dto1 = AshaRequestCreateDTO(
            assistance_type="HOME_VISIT",
            reason="Blood pressure monitoring and headache assessment",
            handoff_packet={"chief_concern": "Blood pressure monitoring and headache assessment"},
            idempotency_key="idemp-dup-test-unique-key-1"
        )
        res1 = CitizenService.create_asha_request(db, primary.id, dto1)
        req1_id = res1["service_request_id"]

        # Submit again with same idempotency key
        res_idemp = CitizenService.create_asha_request(db, primary.id, dto1)
        assert res_idemp["service_request_id"] == req1_id
        assert res_idemp.get("reused_existing_request") is True

        # Submit another request with same reason while active open request exists
        dto2 = AshaRequestCreateDTO(
            assistance_type="HOME_VISIT",
            reason="Blood pressure monitoring and headache assessment",
            handoff_packet={"chief_concern": "Blood pressure monitoring and headache assessment"},
            idempotency_key="idemp-dup-test-unique-key-2"
        )
        res2 = CitizenService.create_asha_request(db, primary.id, dto2)
        assert res2["service_request_id"] == req1_id
        assert res2.get("reused_existing_request") is True
    finally:
        db.close()

def test_state_actions_and_history_reconciliation(client):
    """Test ASHA state actions (Acknowledge, Call, Schedule, Escalate, Complete) and history creation."""
    from conftest import TestingSessionLocal
    from app.routers.asha import patch_asha_citizen_request_status
    db = TestingSessionLocal()
    try:
        primary = db.query(CitizenProfile).first()
        assert primary is not None

        dto = AshaRequestCreateDTO(
            assistance_type="HOME_VISIT",
            reason="High fever and chills in maternal patient",
            urgency="URGENT",
            handoff_packet={"chief_concern": "High fever and chills", "safety": {"priority": "URGENT"}},
            idempotency_key="idemp-state-actions-001"
        )
        res = CitizenService.create_asha_request(db, primary.id, dto)
        req_id = res["service_request_id"]
        case_id = res["case_id"]

        asha_user = db.query(User).filter(User.role == "ASHA_WORKER").first() or User(id="asha-1", name="Sita Patel", role="ASHA_WORKER")

        # 1. Acknowledge
        ack_res = patch_asha_citizen_request_status(
            request_id=req_id,
            payload={"action": "ACKNOWLEDGE"},
            db=db,
            current_user=asha_user
        )
        assert ack_res.data["status"] == "ASHA_ACKNOWLEDGED"

        # 2. Mark Contacted
        contact_res = patch_asha_citizen_request_status(
            request_id=req_id,
            payload={"action": "MARK_CONTACTED", "notes": "Citizen confirmed home address and morning availability"},
            db=db,
            current_user=asha_user
        )
        assert contact_res.data["status"] == "CITIZEN_CONTACTED"

        # 3. Schedule Visit
        sched_res = patch_asha_citizen_request_status(
            request_id=req_id,
            payload={"action": "SCHEDULE_VISIT", "scheduled_date": "2026-08-29", "scheduled_time_slot": "MORNING"},
            db=db,
            current_user=asha_user
        )
        assert sched_res.data["status"] == "VISIT_SCHEDULED"

        # Verify FollowUp created for ASHA schedule
        fu = db.query(FollowUp).filter(FollowUp.case_id == case_id).first()
        assert fu is not None
        assert fu.task_type == "ASHA_HOME_VISIT"

        # 4. Escalate to PHC Doctor
        esc_res = patch_asha_citizen_request_status(
            request_id=req_id,
            payload={"action": "ESCALATE_PHC", "notes": "Fever persisting over 102F. Needs medical officer prescription."},
            db=db,
            current_user=asha_user
        )
        assert esc_res.data["status"] == "REFERRED_TO_PHC"

        # Verify Referral atomically created for Doctor Queue
        referral = db.query(Referral).filter(Referral.case_id == case_id).first()
        assert referral is not None
        assert referral.to_facility_id == "PHC-09"
        assert referral.status == "PENDING_DOCTOR_REVIEW"

        # 5. Verify Status History entries exist
        history = db.query(ServiceRequestStatusHistory).filter(ServiceRequestStatusHistory.service_request_id == req_id).all()
        assert len(history) >= 4
    finally:
        db.close()
