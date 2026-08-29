import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models import Case, AuditLog, CaseStatusEnum, Referral, FollowUp, CasePriorityEnum

def test_case_acknowledgement_idempotency(client: TestClient):
    # Log in as ASHA worker
    login_res = client.post("/api/auth/login", json={"identifier": "sita.asha", "password": "demo123"})
    token = login_res.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Acknowledge case first time
    res1 = client.post("/api/asha/cases/case-canonical-001/acknowledge", headers=headers)
    assert res1.status_code in [200, 400] # It might be already acknowledged in seed data, but if it is or not:
    
    # 2. Force status back to ASHA_ASSIGNED in DB to test transition
    from conftest import TestingSessionLocal
    db = TestingSessionLocal()
    case = db.query(Case).filter(Case.id == "case-canonical-001").first()
    case.status = CaseStatusEnum.ASHA_ASSIGNED
    db.commit()

    # Clear audit logs for CASE_ACKNOWLEDGED to get clean count
    db.query(AuditLog).filter(AuditLog.resource_id == "case-canonical-001", AuditLog.action == "CASE_ACKNOWLEDGED").delete()
    db.commit()
    db.close()

    # Try acknowledging again
    res2 = client.post("/api/asha/cases/case-canonical-001/acknowledge", headers=headers)
    assert res2.status_code == 200

    # Acknowledge case second time
    res3 = client.post("/api/asha/cases/case-canonical-001/acknowledge", headers=headers)
    assert res3.status_code == 200 # Should be idempotent and return success

    # Verify only one CASE_ACKNOWLEDGED audit log exists
    db = TestingSessionLocal()
    logs = db.query(AuditLog).filter(
        AuditLog.resource_id == "case-canonical-001", 
        AuditLog.action == "CASE_ACKNOWLEDGED"
    ).all()
    assert len(logs) == 1
    db.close()

def test_referral_acknowledgement_idempotency(client: TestClient):
    # Log in as doctor
    login_res = client.post("/api/auth/login", json={"identifier": "dr.sharma", "password": "demo123"})
    token = login_res.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Dynamically create referral in test DB
    from conftest import TestingSessionLocal
    db = TestingSessionLocal()
    
    # Check if case exists
    case = db.query(Case).filter(Case.id == "case-canonical-001").first()
    assert case is not None
    case.status = CaseStatusEnum.REFERRED_TO_PHC
    db.commit()

    # Delete existing referral for this case if any
    db.query(Referral).filter(Referral.case_id == "case-canonical-001").delete()
    db.commit()

    # Create new referral
    ref = Referral(
        case_id="case-canonical-001",
        to_facility_id="FAC-001",
        to_facility_name="Kalyanpur PHC",
        reason="Pregnancy risk monitoring required",
        status="PENDING_DOCTOR_REVIEW",
        urgency=CasePriorityEnum.HIGH
    )
    db.add(ref)
    db.commit()

    # Clear audit logs for REFERRAL_ACKNOWLEDGED to get clean count
    db.query(AuditLog).filter(AuditLog.resource_id == "case-canonical-001", AuditLog.action == "REFERRAL_ACKNOWLEDGED").delete()
    db.commit()
    db.close()

    # 1. Acknowledge referral first time (by case_id)
    res1 = client.post("/api/doctor/referrals/case-canonical-001/acknowledge", headers=headers)
    assert res1.status_code == 200

    # 2. Acknowledge referral second time (by case_id)
    res2 = client.post("/api/doctor/referrals/case-canonical-001/acknowledge", headers=headers)
    assert res2.status_code == 200

    # Verify only one REFERRAL_ACKNOWLEDGED audit log exists
    db = TestingSessionLocal()
    logs = db.query(AuditLog).filter(
        AuditLog.resource_id == "case-canonical-001", 
        AuditLog.action == "REFERRAL_ACKNOWLEDGED"
    ).all()
    assert len(logs) == 1
    db.close()

def test_followup_crud_lifecycle(client: TestClient):
    # Log in as ASHA worker
    login_res = client.post("/api/auth/login", json={"identifier": "sita.asha", "password": "demo123"})
    token = login_res.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create Follow-Up
    create_res = client.post(
        "/api/asha/followups",
        headers=headers,
        json={
            "citizen_id": "citizen-canonical-001",
            "case_id": "case-canonical-001",
            "task_type": "BLOOD_PRESSURE_CHECK",
            "instructions": "Verify repeat vitals daily",
            "priority": "HIGH",
            "due_at": "2026-08-30T10:00:00Z"
        }
    )
    assert create_res.status_code == 200
    followup_id = create_res.json()["data"]["followup_id"]

    # 2. Get Follow-Up details
    get_res = client.get(f"/api/asha/followups/{followup_id}", headers=headers)
    assert get_res.status_code == 200
    assert get_res.json()["data"]["status"] == "PENDING"
    assert get_res.json()["data"]["instructions"] == "Verify repeat vitals daily"

    # 3. Start Follow-Up
    start_res = client.post(f"/api/asha/followups/{followup_id}/start", headers=headers)
    assert start_res.status_code == 200
    assert start_res.json()["data"]["status"] == "IN_PROGRESS"

    # 4. Reschedule Follow-Up
    resched_res = client.post(
        f"/api/asha/followups/{followup_id}/reschedule",
        headers=headers,
        json={
            "new_due_date": "2026-09-02T12:00:00Z",
            "reason": "Citizen not at home"
        }
    )
    assert resched_res.status_code == 200
    assert resched_res.json()["data"]["status"] == "PENDING"

    # 5. Start again
    client.post(f"/api/asha/followups/{followup_id}/start", headers=headers)

    # 6. Escalate Follow-Up
    esc_res = client.post(
        f"/api/asha/followups/{followup_id}/escalate",
        headers=headers,
        json={
            "reason": "Patient has developed severe symptoms",
            "urgency": "HIGH",
            "notes": "Red flag signs visible"
        }
    )
    assert esc_res.status_code == 200
    assert esc_res.json()["data"]["status"] == "ESCALATED"
