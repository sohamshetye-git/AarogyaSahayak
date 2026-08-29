import pytest
from fastapi.testclient import TestClient
from app.models import User, Case, Facility, WorkerProfile, UserRoleEnum
from app.auth.security import create_access_token
from conftest import TestingSessionLocal

@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture
def doctor_headers(db_session):
    doc = db_session.query(User).filter(User.role == UserRoleEnum.PHC_DOCTOR).first()
    token = create_access_token({"sub": doc.id, "role": "PHC_DOCTOR"})
    return {"Authorization": f"Bearer {token}"}

def test_pooja_jadhav_timeline_integrity_and_chronology(client: TestClient, db_session, doctor_headers):
    """Test case timeline data integrity, response structure, and event chronology."""
    case = db_session.query(Case).first()
    assert case is not None, "Case record must exist in DB."
    
    # 1. Access by canonical case UUID
    res = client.get(f"/api/doctor/cases/{case.id}/timeline", headers=doctor_headers)
    assert res.status_code == 200
    data = res.json()["data"]
    
    assert data["case_id"] == case.id
    assert data["case_reference"] == case.reference
    assert "events" in data
    assert isinstance(data["events"], list)
    assert len(data["events"]) > 0
    
    # 2. Verify chronological sorting (occurred_at ASC)
    timestamps = [ev["occurred_at"] for ev in data["events"]]
    sorted_timestamps = sorted(timestamps)
    assert timestamps == sorted_timestamps, "Timeline events must be sorted chronologically by occurred_at ASC."
    
    # 3. Verify deduplication by event_id
    event_ids = [ev["event_id"] for ev in data["events"]]
    assert len(event_ids) == len(set(event_ids)), "Timeline events must not contain duplicate event IDs."
    
    # 4. Access by case reference alias
    res_ref = client.get(f"/api/doctor/cases/{case.reference}/timeline", headers=doctor_headers)
    assert res_ref.status_code == 200
    assert res_ref.json()["data"]["case_id"] == case.id

def test_doctor_cannot_access_other_phc_case(client: TestClient, db_session, doctor_headers):
    """Doctor from PHC-09 should receive 403 when requesting a case assigned to another facility."""
    # Create test case assigned to PHC-99
    other_case = Case(
        reference="CASE-OTHER-PHC-999",
        citizen_id=db_session.query(Case).first().citizen_id,
        assigned_facility_id="PHC-99",
        primary_concern="Other facility patient",
        priority="ROUTINE",
        status="REFERRED_TO_PHC"
    )
    db_session.add(other_case)
    db_session.commit()
    
    res = client.get(f"/api/doctor/cases/{other_case.id}/timeline", headers=doctor_headers)
    assert res.status_code == 403
    assert res.json()["detail"]["code"] == "FORBIDDEN_FACILITY_ACCESS"
    
    # Cleanup test case
    db_session.delete(other_case)
    db_session.commit()

def test_missing_case_returns_404(client: TestClient, doctor_headers):
    """Requesting invalid/non-existent case ID must return 404 CASE_NOT_FOUND."""
    res = client.get("/api/doctor/cases/NON_EXISTENT_CASE_ID/timeline", headers=doctor_headers)
    assert res.status_code == 404
    assert res.json()["detail"]["code"] == "CASE_NOT_FOUND"

def test_unauthenticated_timeline_request_fails(client: TestClient):
    """Unauthenticated request must return 401 Unauthorized."""
    res = client.get("/api/doctor/cases/CASE-DEMO-007/timeline")
    assert res.status_code == 401
