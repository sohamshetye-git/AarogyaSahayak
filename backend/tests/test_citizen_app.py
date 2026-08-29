import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import get_db
from app.models import (
    User, CitizenProfile, HouseholdMember, CitizenChatSession,
    CitizenNeed, ServiceRequest, Case, CaseStatusEnum, Prescription, FollowUp
)

def test_citizen_home_summary(client):
    response = client.get("/api/citizen/home-summary")
    assert response.status_code == 200
    data = response.json().get("data")
    assert data is not None
    assert "citizen_name" in data
    assert "quick_actions" in data
    assert len(data["quick_actions"]) >= 4

def test_citizen_chat_session_orchestrator(client):
    # 1. Start chat session
    start_resp = client.post("/api/citizen/chat/session", json={
        "preferred_language": "mr-IN",
        "channel": "VOICE"
    })
    assert start_resp.status_code == 200
    session_data = start_resp.json().get("data")
    session_id = session_data["session_id"]
    assert session_id is not None

    # 2. Add spoken message
    msg_resp = client.post(f"/api/citizen/chat/session/{session_id}/message", json={
        "input_type": "VOICE",
        "original_text": "माझ्या आईला २ दिवसांपासून छातीत दुखत आहे.",
        "language": "mr-IN"
    })
    assert msg_resp.status_code == 200

    # 3. Confirm transcript
    confirm_resp = client.post(f"/api/citizen/chat/session/{session_id}/confirm-transcript", json={
        "confirmed_text": "माझ्या आईला २ दिवसांपासून छातीत दुखत आहे.",
        "action": "CONFIRM"
    })
    assert confirm_resp.status_code == 200
    understanding_data = confirm_resp.json().get("data")
    assert understanding_data["state"] == "AWAITING_ACTION_SELECTION"
    assert understanding_data["safety"]["level"] == "EMERGENCY"
    assert len(understanding_data["actions"]) >= 2

def test_citizen_doctor_request_idempotency(client):
    idem_key = "IDEM-DOC-TEST-999"
    payload = {
        "chief_complaint": "Severe chest pain and dizziness",
        "symptoms": ["chest pain", "dizziness"],
        "request_type": "TELECONSULTATION",
        "idempotency_key": idem_key
    }

    # First request
    res1 = client.post("/api/citizen/doctor/requests", json=payload)
    assert res1.status_code == 200
    d1 = res1.json().get("data")
    assert d1["status"] in ["PENDING", "WAITING_FOR_DOCTOR"]
    req_id = d1["request_id"]

    # Second request with same idempotency key must return same record with zero duplicate creation
    res2 = client.post("/api/citizen/doctor/requests", json=payload)
    assert res2.status_code == 200
    d2 = res2.json().get("data")
    assert d2["request_id"] == req_id

def test_citizen_asha_request(client):
    payload = {
        "reason": "Home visit required for pregnancy ANC checkup",
        "urgency": "ROUTINE",
        "idempotency_key": "IDEM-ASHA-111"
    }
    res = client.post("/api/citizen/asha/requests", json=payload)
    assert res.status_code == 200
    data = res.json().get("data")
    assert data["status"] in ["PENDING", "ASHA_ASSIGNED", "ASSIGNMENT_PENDING"]
    assert "assigned_asha" in data

def test_citizen_safe_timeline(client):
    # Fetch cases
    cases_resp = client.get("/api/citizen/cases")
    assert cases_resp.status_code == 200
    cases_list = cases_resp.json().get("data")
    if cases_list:
        case_id = cases_list[0]["id"]
        tl_resp = client.get(f"/api/citizen/cases/{case_id}/timeline")
        assert tl_resp.status_code == 200
        events = tl_resp.json().get("data")
        assert isinstance(events, list)
        for e in events:
            assert e.get("is_citizen_safe") is True
            # Verify internal doctor note keywords are stripped
            assert "internal_note" not in e
            assert "staff_alert" not in e

def test_citizen_household_members(client):
    # 1. Get household members
    get_res = client.get("/api/citizen/household")
    assert get_res.status_code == 200
    members_data = get_res.json().get("data")
    members = members_data.get("items") if isinstance(members_data, dict) else members_data
    assert isinstance(members, list)

    # 2. Add household member
    add_res = client.post("/api/citizen/household", json={
        "full_name": "Kavita Devi",
        "relationship_type": "CHILD",
        "age": 5,
        "sex": "Female"
    })
    assert add_res.status_code == 200
    added = add_res.json().get("data")
    assert added["full_name"] == "Kavita Devi"

def test_citizen_scheme_screening(client):
    screen_res = client.post("/api/citizen/schemes/screen", json={
        "is_pregnant": True,
        "gestational_weeks": 28,
        "household_category": "PRIORITY"
    })
    assert screen_res.status_code == 200
    results = screen_res.json().get("data")
    assert len(results) > 0

def test_citizen_facilities_search(client):
    fac_res = client.get("/api/citizen/facilities?facility_type=PHC")
    assert fac_res.status_code == 200
    facilities = fac_res.json().get("data")
    assert len(facilities) > 0
