import os
import pytest
from fastapi.testclient import TestClient

os.environ["APP_ENV"] = "test"

from app.main import app
from app.seeds.seed_full_demo import seed_full_demonstration
from app.database import SessionLocal
from app.models import Case, CitizenProfile, User

client = TestClient(app)

@pytest.fixture(scope="module", autouse=True)
def setup_demo_data():
    seed_full_demonstration()
    yield

def get_auth_token(username="dr.sharma", password="demo123"):
    resp = client.post("/api/auth/login", json={"identifier": username, "password": password})
    assert resp.status_code == 200, f"Login failed for {username}"
    return resp.json()["data"]["access_token"]

def test_doctor_timeline_by_valid_case_id():
    token = get_auth_token("dr.sharma", "demo123")
    db = SessionLocal()
    laxmi_case = db.query(Case).join(CitizenProfile).filter(CitizenProfile.display_name == "Laxmi Kamble").first()
    assert laxmi_case is not None, "Laxmi Kamble case missing from DB"
    db.close()

    resp = client.get(
        f"/api/doctor/cases/{laxmi_case.id}/timeline",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200, f"Timeline fetch failed: {resp.text}"
    data = resp.json()["data"]

    assert data["case_id"] == laxmi_case.id
    assert data["case_reference"] == laxmi_case.reference
    assert data["citizen_name"] == "Laxmi Kamble"
    assert "events" in data
    assert len(data["events"]) > 0

    # Assert event structure
    for ev in data["events"]:
        assert "event_id" in ev
        assert "event_type" in ev
        assert "title" in ev
        assert "safe_description" in ev
        assert "actor_name" in ev
        assert "actor_role" in ev
        assert "occurred_at" in ev
        assert "category" in ev

def test_doctor_timeline_chronological_order_and_no_duplicates():
    token = get_auth_token("dr.sharma", "demo123")
    db = SessionLocal()
    anandi_case = db.query(Case).join(CitizenProfile).filter(CitizenProfile.display_name == "Anandi Bai Deshmukh").first()
    assert anandi_case is not None
    db.close()

    resp = client.get(
        f"/api/doctor/cases/{anandi_case.id}/timeline",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    events = resp.json()["data"]["events"]

    # Check chronological ordering
    timestamps = [ev["occurred_at"] for ev in events]
    assert timestamps == sorted(timestamps), "Events are not sorted chronologically"

    # Check no duplicate event IDs
    event_ids = [ev["event_id"] for ev in events]
    assert len(event_ids) == len(set(event_ids)), "Duplicate events found in timeline"

def test_doctor_timeline_unknown_case_404():
    token = get_auth_token("dr.sharma", "demo123")
    resp = client.get(
        "/api/doctor/cases/invalid-non-existent-uuid-999/timeline",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 404
    data = resp.json()
    code = data.get("error", {}).get("code") or data.get("detail", {}).get("code")
    assert code == "CASE_NOT_FOUND"

def test_doctor_timeline_unauthorized_facility_403():
    db = SessionLocal()
    dr_sharma = db.query(User).filter(User.identifier == "dr.sharma").first()
    laxmi_case = db.query(Case).join(CitizenProfile).filter(CitizenProfile.display_name == "Laxmi Kamble").first()
    
    orig_facility_id = dr_sharma.worker_profile.facility_id
    dr_sharma.worker_profile.facility_id = "DH-01"
    db.commit()

    token = get_auth_token("dr.sharma", "demo123")
    resp = client.get(
        f"/api/doctor/cases/{laxmi_case.id}/timeline",
        headers={"Authorization": f"Bearer {token}"}
    )

    dr_sharma.worker_profile.facility_id = orig_facility_id
    db.commit()
    db.close()

    assert resp.status_code == 403
    data = resp.json()
    code = data.get("error", {}).get("code") or data.get("detail", {}).get("code")
    assert code == "FORBIDDEN_FACILITY_ACCESS"

def test_doctor_timeline_no_pii_leakage():
    token = get_auth_token("dr.sharma", "demo123")
    db = SessionLocal()
    meena_case = db.query(Case).join(CitizenProfile).filter(CitizenProfile.display_name == "Meena Bai").first()
    db.close()

    resp = client.get(
        f"/api/doctor/cases/{meena_case.id}/timeline",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    res_str = str(resp.json())

    assert "123456789012" not in res_str, "Raw Aadhaar leaked in timeline API response"
    assert "ABHA-REAL" not in res_str, "Real ABHA leaked in timeline API response"
