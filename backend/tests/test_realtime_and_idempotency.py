import pytest
from fastapi.testclient import TestClient
from app.database import SessionLocal
from app.models import IdempotencyRecord, User

def test_idempotency_same_key_same_payload_returns_cached(client: TestClient):
    asha_login = client.post("/api/auth/login", json={"identifier": "sita.asha", "password": "demo123"})
    token = asha_login.json()["data"]["access_token"]
    headers = {
        "Authorization": f"Bearer {token}",
        "Idempotency-Key": "test-idem-key-001"
    }

    # 1. Create a case
    create_res = client.post(
        "/api/citizen/cases",
        json={"preferred_language": "mr-IN", "spoken_transcript": "Fever", "symptoms": ["fever"], "is_pregnant": False}
    )
    case_id = create_res.json()["data"]["case_id"]

    # 2. First call with Idempotency-Key
    res1 = client.post(f"/api/asha/cases/{case_id}/acknowledge", headers=headers)
    assert res1.status_code == 200
    data1 = res1.json()["data"]

    # 3. Second call with SAME Idempotency-Key and SAME payload
    res2 = client.post(f"/api/asha/cases/{case_id}/acknowledge", headers=headers)
    assert res2.status_code == 200
    data2 = res2.json()["data"]
    assert data1["status"] == data2["status"]

def test_idempotency_same_key_different_payload_fails_with_409(client: TestClient):
    asha_login = client.post("/api/auth/login", json={"identifier": "sita.asha", "password": "demo123"})
    token = asha_login.json()["data"]["access_token"]
    headers = {
        "Authorization": f"Bearer {token}",
        "Idempotency-Key": "test-idem-key-002"
    }

    create_res = client.post(
        "/api/citizen/cases",
        json={"preferred_language": "mr-IN", "spoken_transcript": "Headache", "symptoms": ["headache"], "is_pregnant": False}
    )
    case_id = create_res.json()["data"]["case_id"]
    client.post(f"/api/asha/cases/{case_id}/acknowledge", headers={"Authorization": f"Bearer {token}"})

    # Submit contact result with key
    res1 = client.post(
        f"/api/asha/cases/{case_id}/contact-result",
        headers=headers,
        json={"outcome": "SPOKE_TO_CITIZEN", "next_action": "PLAN_VISIT", "notes": "Initial contact"}
    )
    assert res1.status_code == 200

    # Submit DIFFERENT payload with same key -> MUST return 409 Conflict
    res2 = client.post(
        f"/api/asha/cases/{case_id}/contact-result",
        headers=headers,
        json={"outcome": "CITIZEN_UNREACHABLE", "next_action": "RESCHEDULE", "notes": "Different outcome"}
    )
    assert res2.status_code == 409
    assert "IDEMPOTENCY" in res2.json()["detail"]["code"]

def test_realtime_ticket_issuance_and_redemption(client: TestClient):
    asha_login = client.post("/api/auth/login", json={"identifier": "sita.asha", "password": "demo123"})
    token = asha_login.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Request ticket
    ticket_res = client.post("/api/realtime/ticket", headers=headers)
    assert ticket_res.status_code == 200
    ticket = ticket_res.json()["data"]["ticket"]
    assert ticket is not None
    assert len(ticket) > 20

    # 2. Test websocket connection using ticket
    with client.websocket_connect(f"/api/ws?ticket={ticket}") as websocket:
        data = websocket.receive_json()
        assert data["event"] == "CONNECTED"
        assert data["data"]["role"] == "ASHA_WORKER"
