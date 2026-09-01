import pytest
import uuid
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from app.main import app
from app.models import User, UserRoleEnum, ServiceRequest, TeleconsultationRequest, TeleconsultationMessage, CitizenProfile
from app.services.teleconsultation_service import TeleconsultationService

@pytest.fixture
def client():
    return TestClient(app)

def test_live_chat_canonical_flow(db_session, doctor_auth_headers, citizen_auth_headers):
    client = TestClient(app)
    
    # 1. Create a Citizen Doctor Request (CHAT mode)
    fresh_need_id = f"NEED-TEST-{uuid.uuid4().hex[:6]}"
    req_payload = {
        "need_id": fresh_need_id,
        "beneficiary_id": None,
        "language_code": "en",
        "chief_concern": "Persistent throat ache and mild fever",
        "requested_channel": "CHAT",
        "priority": "ROUTINE",
        "intake_responses": {"duration": "2 days", "severity": "MODERATE"}
    }
    
    create_res = client.post("/api/citizen/doctor/requests", json=req_payload, headers=citizen_auth_headers)
    assert create_res.status_code == 200
    res_data = create_res.json()["data"]
    request_ref = res_data.get("request_reference") or res_data.get("id")
    assert request_ref is not None

    # 2. Citizen sends first chat message before doctor accepts
    client_msg_id = f"cmsg-test-{uuid.uuid4().hex[:6]}"
    send_res = client.post(
        f"/api/citizen/doctor/requests/{request_ref}/messages",
        json={"body": "Hello Doctor, I have had a throat ache for 2 days.", "client_message_id": client_msg_id},
        headers=citizen_auth_headers
    )
    assert send_res.status_code == 200
    msg_data = send_res.json()["data"]
    assert msg_data["body"] == "Hello Doctor, I have had a throat ache for 2 days."
    assert msg_data["sender_role"] == "CITIZEN"
    assert msg_data["client_message_id"] == client_msg_id

    # 3. Idempotency test: duplicate post with same client_message_id should not duplicate
    dup_res = client.post(
        f"/api/citizen/doctor/requests/{request_ref}/messages",
        json={"body": "Hello Doctor, I have had a throat ache for 2 days.", "client_message_id": client_msg_id},
        headers=citizen_auth_headers
    )
    assert dup_res.status_code == 200
    assert dup_res.json()["data"]["id"] == msg_data["id"]

    # 4. Doctor accepts the direct request
    accept_res = client.post(f"/api/doctor/direct-requests/{request_ref}/accept", headers=doctor_auth_headers)
    assert accept_res.status_code == 200
    accept_data = accept_res.json()["data"]
    assert accept_data["status"] == "DOCTOR_ACCEPTED"

    # 5. Doctor views request detail and sees citizen's prior message
    detail_res = client.get(f"/api/doctor/direct-requests/{request_ref}", headers=doctor_auth_headers)
    assert detail_res.status_code == 200
    detail_data = detail_res.json()["data"]
    messages = detail_data.get("messages", [])
    assert len(messages) >= 1
    assert any(m["body"] == "Hello Doctor, I have had a throat ache for 2 days." for m in messages)

    # 6. Doctor sends clinical guidance reply
    doc_msg_res = client.post(
        f"/api/doctor/direct-requests/{request_ref}/messages",
        json={"body": "Please gargle with warm salt water and rest. I will write a prescription for you."},
        headers=doctor_auth_headers
    )
    assert doc_msg_res.status_code == 200
    doc_msg_data = doc_msg_res.json()["data"]
    assert doc_msg_data["sender_role"] == "PHC_DOCTOR"

    # 7. Citizen retrieves messages and receives Doctor reply
    cit_msg_res = client.get(f"/api/citizen/doctor/requests/{request_ref}/messages", headers=citizen_auth_headers)
    assert cit_msg_res.status_code == 200
    all_msgs = cit_msg_res.json()["data"]
    assert len(all_msgs) == 2
    assert all_msgs[0]["sender_role"] == "CITIZEN"
    assert all_msgs[1]["sender_role"] == "PHC_DOCTOR"

    # 8. Citizen marks message as read
    read_res = client.patch(f"/api/citizen/messages/{doc_msg_data['id']}/read", headers=citizen_auth_headers)
    assert read_res.status_code == 200
    assert read_res.json()["data"]["status"] == "READ"

    # 9. Doctor completes consultation
    complete_res = client.post(
        f"/api/doctor/direct-requests/{request_ref}/complete",
        json={
            "provisional_diagnosis": "Acute Pharyngitis",
            "clinical_summary": "Patient presented with mild pharyngitis. Advised gargles and hydration.",
            "patient_guidance": "Rest and gargle with warm saline.",
            "disposition": "COMPLETED",
            "prescriptions": [
                {"medicine_name": "Paracetamol 500mg", "formulation": "Tablet", "dosage": "1", "frequency": "1-0-1", "duration_days": 3, "instructions": "After food"}
            ]
        },
        headers=doctor_auth_headers
    )
    assert complete_res.status_code == 200
    comp_data = complete_res.json()["data"]
    assert comp_data["status"] == "COMPLETED"
