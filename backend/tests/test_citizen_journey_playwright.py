import os
import time
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app.models import (
    CitizenProfile, CitizenChatSession, CitizenChatMessage, CitizenNeed,
    ServiceRequest, Case, CaseStatusEnum, Referral, Prescription, FollowUp
)
try:
    from conftest import TestingSessionLocal
except ImportError:
    from tests.conftest import TestingSessionLocal

def test_complete_citizen_e2e_journey(client):
    db = TestingSessionLocal()
    try:
        # 1. First-use language selection & home summary
        home_res = client.get("/api/citizen/home-summary")
        assert home_res.status_code == 200
        home_data = home_res.json().get("data")
        assert home_data["citizen_name"] is not None

        # 2. Chat Session & Intent Orchestrator
        session_res = client.post("/api/citizen/chat/session", json={
            "preferred_language": "mr-IN",
            "channel": "VOICE"
        })
        assert session_res.status_code == 200
        session_id = session_res.json()["data"]["session_id"]

        # Add message
        msg_res = client.post(f"/api/citizen/chat/session/{session_id}/message", json={
            "input_type": "VOICE",
            "original_text": "माझ्या आईला २ दिवसांपासून छातीत दुखत आहे आणि मूत्राशय त्रास होतोय.",
            "language": "mr-IN"
        })
        assert msg_res.status_code == 200

        # Confirm transcript
        conf_res = client.post(f"/api/citizen/chat/session/{session_id}/confirm-transcript", json={
            "confirmed_text": "माझ्या आईला २ दिवसांपासून छातीत दुखत आहे आणि मूत्राशय त्रास होतोय.",
            "action": "CONFIRM"
        })
        assert conf_res.status_code == 200
        und = conf_res.json()["data"]
        assert und["safety"]["level"] == "EMERGENCY"

        # Verify chat session state and messages via history endpoint
        hist_res = client.get(f"/api/citizen/chat/session/{session_id}/history")
        assert hist_res.status_code == 200
        hist_data = hist_res.json()["data"]
        assert hist_data["current_state"] == "AWAITING_ACTION_SELECTION"
        assert len(hist_data["messages"]) >= 2

        # 3. Create confirmed CitizenNeed
        need_res = client.post("/api/citizen/need", json={
            "session_id": session_id,
            "primary_intent": "DOCTOR_CONSULTATION",
            "secondary_intents": ["HEALTH_CONCERN", "FACILITY_SEARCH"],
            "confirmed_summary": "Chest pain 2 days, urgent Doctor request",
            "urgency": "EMERGENCY"
        })
        assert need_res.status_code == 200
        need_id = need_res.json()["data"]["need_id"]

        # 4. Citizen -> Doctor Request
        doc_req_res = client.post("/api/citizen/doctor/requests", json={
            "need_id": need_id,
            "chief_complaint": "Severe chest pain since 2 days",
            "symptoms": ["chest pain", "shortness of breath"],
            "request_type": "TELECONSULTATION",
            "idempotency_key": f"IDEM-E2E-{int(time.time())}"
        })
        assert doc_req_res.status_code == 200
        doc_req_data = doc_req_res.json()["data"]
        case_id = doc_req_data["case_id"]

        # 5. Citizen case status check
        case_res = client.get(f"/api/citizen/cases/{case_id}")
        assert case_res.status_code == 200
        case_data = case_res.json()["data"]
        assert case_data["id"] == case_id

        # Citizen timeline check
        tl_res = client.get(f"/api/citizen/cases/{case_id}/timeline")
        assert tl_res.status_code == 200
        tl_events = tl_res.json()["data"]
        assert len(tl_events) >= 1

        # 6. Citizen -> ASHA Request
        asha_req_res = client.post("/api/citizen/asha/requests", json={
            "case_id": case_id,
            "reason": "Request home visit follow-up for BP check",
            "urgency": "ROUTINE",
            "idempotency_key": f"IDEM-ASHA-E2E-{int(time.time())}"
        })
        assert asha_req_res.status_code == 200
        assert "Sita Patel" in asha_req_res.json()["data"]["assigned_asha"]

        # 7. Schemes & Facilities
        scheme_res = client.post("/api/citizen/schemes/screen", json={"is_pregnant": True})
        assert scheme_res.status_code == 200
        assert len(scheme_res.json()["data"]) >= 3

        fac_res = client.get("/api/citizen/facilities")
        assert fac_res.status_code == 200
        assert len(fac_res.json()["data"]) >= 3

        # 8. Household Member
        hh_res = client.post("/api/citizen/household", json={
            "full_name": "Ramesh Devi",
            "relationship_type": "FATHER",
            "age": 62
        })
        assert hh_res.status_code == 200
        assert hh_res.json()["data"]["full_name"] == "Ramesh Devi"

    finally:
        db.close()
