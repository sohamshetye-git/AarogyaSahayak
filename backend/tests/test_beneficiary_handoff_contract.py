import pytest
from app.models import (
    CitizenProfile, HouseholdMember, ServiceRequest, Case, User, UserRoleEnum
)
from app.services.citizen_service import CitizenService
from app.schemas.citizen import HandoffPreviewRequest, DoctorRequestCreateDTO

def test_beneficiaries_endpoint_returns_self_and_household_members(client):
    res = client.get("/api/citizen/beneficiaries")
    assert res.status_code == 200
    data = res.json().get("data", {})
    items = data.get("items", [])
    assert len(items) >= 1
    
    # First item must be SELF
    self_item = items[0]
    assert self_item["relationship"] == "SELF"
    assert self_item["beneficiary_id"] is not None
    assert self_item["citizen_id"] == self_item["beneficiary_id"]
    assert self_item["profile_id"] == self_item["beneficiary_id"]
    assert self_item["display_name"] == "Sunita Devi"
    assert self_item["is_registered_patient"] is True

def test_care_handoff_preview_with_beneficiary_id(client):
    # Retrieve beneficiaries list
    b_res = client.get("/api/citizen/beneficiaries")
    items = b_res.json()["data"]["items"]
    self_b = items[0]

    # Preview handoff with canonical beneficiary_id without chat session
    preview_res = client.post("/api/citizen/care-handoffs/preview", json={
        "beneficiary_id": self_b["beneficiary_id"],
        "request_type": "DOCTOR_CONSULTATION",
        "requested_channel": "CALLBACK"
    })
    assert preview_res.status_code == 200
    pdata = preview_res.json()["data"]
    assert pdata["beneficiary_id"] == self_b["beneficiary_id"]
    assert pdata["beneficiary_name"] == "Sunita Devi"
    assert "handoff_id" in pdata
    assert "chief_concern" in pdata
    assert "safety" in pdata

def test_doctor_request_creation_from_home_and_duplicate_reuse(client):
    b_res = client.get("/api/citizen/beneficiaries")
    self_b = b_res.json()["data"]["items"][0]

    idem_key = "IDEM-HOME-DOC-TEST-4422"
    payload = {
        "beneficiary_id": self_b["beneficiary_id"],
        "chief_complaint": "Severe persistent headache and dizziness",
        "symptoms": ["headache", "dizziness"],
        "channel": "CALLBACK",
        "request_type": "DOCTOR_CONSULTATION",
        "sharing_scope": {
            "share_structured_summary": True,
            "share_profile": True,
            "share_location": True
        },
        "idempotency_key": idem_key
    }

    # 1. Create request from Home
    res1 = client.post("/api/citizen/doctor/requests", json=payload)
    assert res1.status_code == 200
    d1 = res1.json()["data"]
    assert d1["status"] == "WAITING_FOR_DOCTOR"
    req_ref = d1["reference"]
    req_id = d1["request_id"]

    # 2. Resubmit identical request -> Should return reused_existing_request
    res2 = client.post("/api/citizen/doctor/requests", json=payload)
    assert res2.status_code == 200
    d2 = res2.json()["data"]
    assert d2.get("reused_existing_request") is True
    assert d2["request_id"] == req_id
    assert d2["reference"] == req_ref
