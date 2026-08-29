import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from app.models import Case, FollowUp, CitizenProfile, User, CaseStatusEnum, CasePriorityEnum, AuditLog
from conftest import TestingSessionLocal

def test_followup_comprehensive_suite(client: TestClient):
    # 1. Login as ASHA
    login_res = client.post("/api/auth/login", json={"identifier": "sita.asha", "password": "demo123"})
    assert login_res.status_code == 200
    token = login_res.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    db = TestingSessionLocal()
    asha_user = db.query(User).filter(User.identifier == "sita.asha").first()
    assert asha_user is not None

    # Clean up test follow-ups
    db.query(FollowUp).filter(FollowUp.id.like("test-fup-%")).delete()
    db.commit()

    # Create distinct follow-ups:
    # A. ASHA Scheduled - Overdue
    past_date = datetime.now(timezone.utc) - timedelta(days=3)
    fup_overdue = FollowUp(
        id="test-fup-overdue-001",
        case_id="case-canonical-001",
        citizen_id="citizen-canonical-001",
        assigned_user_id=asha_user.id,
        source="ASHA_SCHEDULED",
        task_type="BP_MONITORING",
        instructions="Recheck hypertension BP",
        priority=CasePriorityEnum.HIGH,
        status="PENDING",
        due_at=past_date,
        created_by_role="ASHA"
    )

    # B. Doctor Directive - Due Today
    now_date = datetime.now(timezone.utc)
    fup_today = FollowUp(
        id="test-fup-today-002",
        case_id="case-canonical-001",
        citizen_id="citizen-canonical-001",
        assigned_user_id=asha_user.id,
        source="DOCTOR_DIRECTIVE",
        task_type="MEDICATION_REVIEW",
        instructions="Verify antibiotic adherence for 5 days",
        priority=CasePriorityEnum.URGENT,
        status="PENDING",
        due_at=now_date,
        created_by_role="DOCTOR"
    )

    # C. Doctor Directive - Upcoming
    future_date = datetime.now(timezone.utc) + timedelta(days=5)
    fup_upcoming = FollowUp(
        id="test-fup-upcoming-003",
        case_id="case-canonical-001",
        citizen_id="citizen-canonical-001",
        assigned_user_id=asha_user.id,
        source="DOCTOR_DIRECTIVE",
        task_type="BLOOD_GLUCOSE_CHECK",
        instructions="Postprandial sugar check",
        priority=CasePriorityEnum.ROUTINE,
        status="PENDING",
        due_at=future_date,
        created_by_role="DOCTOR"
    )

    db.add_all([fup_overdue, fup_today, fup_upcoming])
    db.commit()
    db.close()

    # 2. Test GET /api/asha/followups without filters
    res = client.get("/api/asha/followups", headers=headers)
    assert res.status_code == 200
    all_fups = res.json()["data"]
    ids = [f["id"] for f in all_fups]
    assert "test-fup-overdue-001" in ids
    assert "test-fup-today-002" in ids
    assert "test-fup-upcoming-003" in ids

    # 3. Test filter=OVERDUE
    res_od = client.get("/api/asha/followups?status_filter=OVERDUE", headers=headers)
    assert res_od.status_code == 200
    od_ids = [f["id"] for f in res_od.json()["data"]]
    assert "test-fup-overdue-001" in od_ids
    assert "test-fup-upcoming-003" not in od_ids

    # 4. Test filter=DOCTOR
    res_doc = client.get("/api/asha/followups?source_filter=DOCTOR", headers=headers)
    assert res_doc.status_code == 200
    doc_ids = [f["id"] for f in res_doc.json()["data"]]
    assert "test-fup-today-002" in doc_ids
    assert "test-fup-overdue-001" not in doc_ids

    # 5. Start follow-up
    res_start = client.post("/api/asha/followups/test-fup-today-002/start", headers=headers)
    assert res_start.status_code == 200
    assert res_start.json()["data"]["status"] == "IN_PROGRESS"

    # 6. Reschedule follow-up
    new_due = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
    res_resched = client.post(
        "/api/asha/followups/test-fup-overdue-001/reschedule",
        headers=headers,
        json={"new_due_date": new_due, "reason": "Patient out of village"}
    )
    assert res_resched.status_code == 200
    assert res_resched.json()["data"]["status"] == "PENDING"

    # 7. Escalate follow-up
    res_esc = client.post(
        "/api/asha/followups/test-fup-upcoming-003/escalate",
        headers=headers,
        json={"reason": "Sudden breathlessness and chest pain", "urgency": "EMERGENCY", "notes": "Immediate medical attention needed"}
    )
    assert res_esc.status_code == 200
    assert res_esc.json()["data"]["status"] == "ESCALATED"

    # 8. Complete follow-up with full vitals and adherence check
    res_comp = client.post(
        "/api/asha/followups/test-fup-today-002/complete",
        headers=headers,
        json={
            "vitals": {"systolic_bp": 124, "diastolic_bp": 82, "spo2": 99, "pulse": 72},
            "medication_adherent": True,
            "symptoms_improved": True,
            "notes": "Patient completed course of antibiotics. BP normal.",
            "escalate_to_doctor": False
        }
    )
    assert res_comp.status_code == 200
    assert res_comp.json()["data"]["status"] == "COMPLETED"

    # 9. Verify completed item in completed filter
    res_comp_list = client.get("/api/asha/followups?status_filter=COMPLETED", headers=headers)
    assert res_comp_list.status_code == 200
    comp_ids = [f["id"] for f in res_comp_list.json()["data"]]
    assert "test-fup-today-002" in comp_ids
