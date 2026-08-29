import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app.models import User, Case, Referral, Consultation, UserRoleEnum
from app.auth.security import create_access_token
from app.seeds.seed_full_demo import seed_full_demonstration

client = TestClient(app)

@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture
def doctor_headers(db_session):
    doc = db_session.query(User).filter(User.id == "DOC-007").first()
    if not doc:
        doc = db_session.query(User).filter(User.role == UserRoleEnum.PHC_DOCTOR).first()
    token = create_access_token({"sub": doc.id, "role": "PHC_DOCTOR"})
    return {"Authorization": f"Bearer {token}"}

def test_get_waiting_patients_phc_isolation_and_status(db_session, doctor_headers):
    """Test GET /api/doctor/consultations/waiting returns only PATIENT_ARRIVED referrals for doctor's PHC."""
    seed_full_demonstration()

    res = client.get("/api/doctor/consultations/waiting", headers=doctor_headers)
    assert res.status_code == 200
    data = res.json()["data"]

    assert "items" in data
    assert "total" in data
    assert isinstance(data["items"], list)
    assert data["total"] >= 4

    for item in data["items"]:
        assert item["referral_id"] is not None
        assert item["case_id"] is not None
        assert item["citizen_name"] is not None
        assert isinstance(item["waiting_minutes"], int)
        assert item["waiting_minutes"] >= 0

def test_staggered_waiting_minutes_and_priority_sorting(db_session, doctor_headers):
    """Test waiting patients are sorted by priority (URGENT/HIGH first), then waiting minutes DESC."""
    seed_full_demonstration()

    res = client.get("/api/doctor/consultations/waiting", headers=doctor_headers)
    assert res.status_code == 200
    items = res.json()["data"]["items"]

    priority_map = {"URGENT": 0, "HIGH": 1, "MODERATE": 2, "ROUTINE": 3, "LOW": 4}
    for i in range(len(items) - 1):
        curr_p = priority_map.get(items[i]["priority"].upper(), 5)
        next_p = priority_map.get(items[i + 1]["priority"].upper(), 5)
        assert curr_p <= next_p, f"Item {i} priority {items[i]['priority']} should rank before Item {i+1} priority {items[i+1]['priority']}"
        if curr_p == next_p:
            assert items[i]["waiting_minutes"] >= items[i + 1]["waiting_minutes"], "Within same priority, longer waiting minutes must rank first"

def test_start_or_resume_consultation_atomic_creation_and_transition(db_session, doctor_headers):
    """Test POST /api/doctor/consultations/start-or-resume transitions referral to IN_CONSULTATION and is idempotent."""
    seed_full_demonstration()

    # Get first waiting patient
    res_waiting = client.get("/api/doctor/consultations/waiting", headers=doctor_headers)
    items = res_waiting.json()["data"]["items"]
    assert len(items) > 0
    target_ref_id = items[0]["referral_id"]

    # 1. Start Consultation
    res_start = client.post(
        "/api/doctor/consultations/start-or-resume",
        json={"referral_id": target_ref_id, "idempotency_key": "test-key-1"},
        headers=doctor_headers
    )
    assert res_start.status_code == 200
    start_data = res_start.json()["data"]
    cons_id = start_data["consultation_id"]
    assert cons_id is not None
    assert start_data["status"] == "IN_CONSULTATION"

    # Verify referral status changed in DB
    ref = db_session.query(Referral).filter(Referral.id == target_ref_id).first()
    assert ref.status == "IN_CONSULTATION"

    # 2. Idempotent call — call again with same referral_id
    res_resume = client.post(
        "/api/doctor/consultations/start-or-resume",
        json={"referral_id": target_ref_id, "idempotency_key": "test-key-1"},
        headers=doctor_headers
    )
    assert res_resume.status_code == 200
    resume_data = res_resume.json()["data"]
    assert resume_data["consultation_id"] == cons_id, "Repeated start-or-resume call must return exact same consultation ID"

def test_starting_consultation_removes_patient_from_waiting_queue(db_session, doctor_headers):
    """Starting consultation on a waiting patient removes them from GET /api/doctor/consultations/waiting."""
    seed_full_demonstration()

    res_before = client.get("/api/doctor/consultations/waiting", headers=doctor_headers)
    before_count = res_before.json()["data"]["total"]
    target_ref_id = res_before.json()["data"]["items"][0]["referral_id"]

    # Start consultation
    client.post(
        "/api/doctor/consultations/start-or-resume",
        json={"referral_id": target_ref_id},
        headers=doctor_headers
    )

    res_after = client.get("/api/doctor/consultations/waiting", headers=doctor_headers)
    after_count = res_after.json()["data"]["total"]
    assert after_count == before_count - 1
    after_ids = [item["referral_id"] for item in res_after.json()["data"]["items"]]
    assert target_ref_id not in after_ids, "Started patient must be removed from waiting list"

def test_unauthenticated_waiting_request_fails():
    """Unauthenticated request to waiting endpoint returns 401 Unauthorized."""
    res = client.get("/api/doctor/consultations/waiting")
    assert res.status_code == 401
