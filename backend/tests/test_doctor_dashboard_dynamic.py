import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from app.models import Case, Referral, Consultation, FollowUp, User, Facility, CasePriorityEnum, CaseStatusEnum
from conftest import TestingSessionLocal

def test_doctor_dashboard_full_aggregation(client: TestClient):
    # 1. Login as PHC Doctor
    login_res = client.post("/api/auth/login", json={"identifier": "dr.sharma", "password": "demo123"})
    assert login_res.status_code == 200
    token = login_res.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Query Dashboard
    res = client.get("/api/doctor/dashboard", headers=headers)
    assert res.status_code == 200
    data = res.json()["data"]

    # Verify structure
    assert "metrics" in data
    assert "incoming_referrals" in data
    assert "today_clinical_work" in data
    assert "asha_followups" in data
    assert "recent_activity" in data

    metrics = data["metrics"]
    assert metrics["new_referrals_count"] >= 0
    assert metrics["urgent_cases_count"] >= 0
    assert metrics["awaiting_consultation_count"] >= 0
    assert metrics["asha_followups_count"] >= 0
    assert metrics["escalations_count"] >= 0
    assert metrics["completed_today_count"] >= 0

    # Verify Doctor Info
    assert "Dr." in data["doctor_name"]
    assert "Primary Health Center" in data["facility_name"] or "PHC" in data["facility_name"]

def test_doctor_referral_state_transitions(client: TestClient):
    login_res = client.post("/api/auth/login", json={"identifier": "dr.sharma", "password": "demo123"})
    token = login_res.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    db = TestingSessionLocal()
    # Check or create active case and referral
    case = db.query(Case).filter(Case.id == "case-canonical-001").first()
    if not case:
        case = Case(
            id="case-canonical-001",
            reference="CASE-2026-001",
            citizen_id="CP-001",
            priority=CasePriorityEnum.URGENT,
            status=CaseStatusEnum.REFERRED_TO_PHC,
            primary_concern="Elevated blood pressure in pregnancy"
        )
        db.add(case)
        db.commit()
    else:
        case.status = CaseStatusEnum.REFERRED_TO_PHC
        db.commit()

    ref = db.query(Referral).filter(Referral.case_id == "case-canonical-001").first()
    if not ref:
        ref = Referral(
            case_id="case-canonical-001",
            to_facility_id="PHC-09",
            to_facility_name="Kalyanpur Primary Health Center",
            urgency=CasePriorityEnum.URGENT,
            reason="High BP monitoring required",
            status="PENDING_DOCTOR_REVIEW"
        )
        db.add(ref)
        db.commit()
    else:
        ref.status = "PENDING_DOCTOR_REVIEW"
        db.commit()
    db.close()

    # Step 1: Acknowledge referral
    ack_res = client.post("/api/doctor/referrals/case-canonical-001/acknowledge", headers=headers)
    assert ack_res.status_code == 200
    assert ack_res.json()["data"]["status"] == "DOCTOR_ACKNOWLEDGED"

    # Step 2: Mark patient arrived
    arr_res = client.post("/api/doctor/referrals/case-canonical-001/mark-arrived", headers=headers)
    assert arr_res.status_code == 200
    assert arr_res.json()["data"]["status"] == "PATIENT_ARRIVED"

def test_doctor_escalation_acknowledgement(client: TestClient):
    login_res = client.post("/api/auth/login", json={"identifier": "dr.sharma", "password": "demo123"})
    token = login_res.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    db = TestingSessionLocal()
    fup = db.query(FollowUp).filter(FollowUp.case_id == "case-canonical-001").first()
    if fup:
        fup.status = "ESCALATED"
        db.commit()
        followup_id = fup.id
    else:
        fup = FollowUp(
            id="fup-esc-test-001",
            case_id="case-canonical-001",
            citizen_id="CP-001",
            status="ESCALATED",
            instructions="Check urgent BP symptoms"
        )
        db.add(fup)
        db.commit()
        followup_id = fup.id
    db.close()

    res = client.post(f"/api/doctor/escalations/{followup_id}/acknowledge", headers=headers)
    assert res.status_code == 200
    assert res.json()["data"]["acknowledged"] is True
