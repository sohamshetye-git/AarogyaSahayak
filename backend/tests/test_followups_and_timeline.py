import pytest
from fastapi.testclient import TestClient
from app.database import SessionLocal
from app.models import Case, FollowUp, VitalRecord

def test_get_asha_followups(client: TestClient):
    asha_login = client.post("/api/auth/login", json={"identifier": "sita.asha", "password": "demo123"})
    token = asha_login.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get("/api/asha/followups", headers=headers)
    assert res.status_code == 200
    data = res.json()["data"]
    assert len(data) >= 3
    assert any(f["task_type"] == "BP_MONITORING" for f in data)

def test_complete_asha_followup_success(client: TestClient):
    asha_login = client.post("/api/auth/login", json={"identifier": "sita.asha", "password": "demo123"})
    token = asha_login.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}", "Idempotency-Key": "test-fup-idem-001"}

    # 1. Fetch pending followups
    res = client.get("/api/asha/followups", headers={"Authorization": f"Bearer {token}"})
    followup_id = res.json()["data"][0]["id"]

    # 2. Complete follow-up with repeat vitals
    complete_res = client.post(
        f"/api/asha/followups/{followup_id}/complete",
        headers=headers,
        json={
            "vitals": {"systolic_bp": 128, "diastolic_bp": 82, "spo2": 98, "pulse": 76},
            "medication_adherent": True,
            "symptoms_improved": True,
            "notes": "Patient reports blood pressure is well controlled. Medication taken on schedule.",
            "escalate_to_doctor": False
        }
    )
    assert complete_res.status_code == 200
    assert complete_res.json()["data"]["status"] == "COMPLETED"

def test_case_timeline_chronological_events(client: TestClient):
    asha_login = client.post("/api/auth/login", json={"identifier": "sita.asha", "password": "demo123"})
    token = asha_login.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    timeline_res = client.get("/api/asha/cases/case-canonical-001/timeline", headers=headers)
    assert timeline_res.status_code == 200
    events = timeline_res.json()["data"]
    assert len(events) >= 1
    assert any(e["event_type"] == "CASE_CREATED" for e in events)
    case_created_event = next(e for e in events if e["event_type"] == "CASE_CREATED")
    assert "Sunita Devi" in case_created_event["actor_name"] or "Citizen" in case_created_event["actor_name"]

def test_voice_transcribe_endpoint(client: TestClient):
    asha_login = client.post("/api/auth/login", json={"identifier": "sita.asha", "password": "demo123"})
    token = asha_login.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    res = client.post("/api/asha/voice/transcribe", headers=headers, json={"preferred_language": "mr-IN"})
    assert res.status_code == 200
    data = res.json()["data"]
    assert "रक्तदाब" in data["transcript"]
    assert data["detected_language"] == "mr-IN"
