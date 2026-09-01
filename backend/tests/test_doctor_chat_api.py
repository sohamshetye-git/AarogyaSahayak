import pytest
import uuid
from datetime import datetime, timezone

from app.models import (
    User, UserRoleEnum, CitizenProfile, HouseholdMember, ServiceRequest,
    TeleconsultationRequest, DoctorChatThread, DoctorChatMessage
)
from app.auth.security import get_password_hash, create_access_token


@pytest.fixture
def test_data(db_session):
    # Create Citizen User & Profile
    cit_user = User(
        id=str(uuid.uuid4()),
        identifier=f"citizen_{uuid.uuid4().hex[:6]}",
        name="Sunita Patil",
        phone="9876543210",
        password_hash=get_password_hash("testpass123"),
        role=UserRoleEnum.CITIZEN
    )
    db_session.add(cit_user)
    db_session.flush()

    cit_profile = CitizenProfile(
        id=str(uuid.uuid4()),
        user_id=cit_user.id,
        display_name="Sunita Patil",
        phone="9876543210",
        village_name="Kalyanpur"
    )
    db_session.add(cit_profile)

    # Create Doctor User
    doc_user = User(
        id=str(uuid.uuid4()),
        identifier=f"doctor_{uuid.uuid4().hex[:6]}",
        name="Dr. Ramesh Kulkarni",
        phone="9823000001",
        password_hash=get_password_hash("testpass123"),
        role=UserRoleEnum.PHC_DOCTOR
    )
    db_session.add(doc_user)

    # Create Other Doctor User (for authorization testing)
    other_doc = User(
        id=str(uuid.uuid4()),
        identifier=f"other_doc_{uuid.uuid4().hex[:6]}",
        name="Dr. Priya Deshmukh",
        phone="9823000002",
        password_hash=get_password_hash("testpass123"),
        role=UserRoleEnum.PHC_DOCTOR
    )
    db_session.add(other_doc)

    # Create Doctor Service Request
    srv_req = ServiceRequest(
        id=str(uuid.uuid4()),
        request_reference=f"REQ-DOC-CHAT-{uuid.uuid4().hex[:6]}",
        citizen_id=cit_profile.id,
        request_type="DOCTOR_CONSULTATION",
        requested_channel="CHAT",
        status="WAITING_FOR_DOCTOR",
        priority="ROUTINE",
        details={"chief_complaint": "Persistent sore throat and mild fever for 2 days"}
    )
    db_session.add(srv_req)
    db_session.flush()

    db_session.commit()

    cit_token = create_access_token(data={"sub": cit_user.id, "role": "CITIZEN", "user_id": cit_user.id})
    doc_token = create_access_token(data={"sub": doc_user.id, "role": "PHC_DOCTOR", "user_id": doc_user.id})
    other_doc_token = create_access_token(data={"sub": other_doc.id, "role": "PHC_DOCTOR", "user_id": other_doc.id})

    return {
        "cit_user": cit_user,
        "cit_profile": cit_profile,
        "doc_user": doc_user,
        "other_doc": other_doc,
        "srv_req": srv_req,
        "cit_token": cit_token,
        "doc_token": doc_token,
        "other_doc_token": other_doc_token
    }


def test_doctor_chat_workflow_end_to_end(client, test_data):
    cit_headers = {"Authorization": f"Bearer {test_data['cit_token']}"}
    doc_headers = {"Authorization": f"Bearer {test_data['doc_token']}"}
    req_id = test_data["srv_req"].id

    # 1. Citizen resolves canonical thread
    thread_res = client.get(f"/api/doctor-chat/requests/{req_id}/thread", headers=cit_headers)
    assert thread_res.status_code == 200
    thread_data = thread_res.json()["data"]["thread"]
    conv_id = thread_data["id"]
    assert conv_id is not None
    assert thread_data["status"] == "WAITING_FOR_DOCTOR"
    assert thread_data["service_request_id"] == req_id
    assert len(thread_data["messages"]) == 0

    # 2. Citizen sends message before doctor acceptance
    cit_client_msg_id = f"cmsg-{uuid.uuid4().hex[:8]}"
    send_res1 = client.post(
        f"/api/doctor-chat/conversations/{conv_id}/messages",
        headers=cit_headers,
        json={
            "body": "Hello Doctor, I have had a throat infection since yesterday.",
            "client_message_id": cit_client_msg_id
        }
    )
    assert send_res1.status_code == 200
    msg1 = send_res1.json()["data"]
    assert msg1["sender_role"] == "CITIZEN"
    assert msg1["client_message_id"] == cit_client_msg_id
    assert msg1["body"] == "Hello Doctor, I have had a throat infection since yesterday."
    assert msg1["status"] == "DELIVERED"

    # 3. Idempotency test: posting the same client_message_id returns the exact same message
    send_dup = client.post(
        f"/api/doctor-chat/conversations/{conv_id}/messages",
        headers=cit_headers,
        json={
            "body": "Hello Doctor, I have had a throat infection since yesterday.",
            "client_message_id": cit_client_msg_id
        }
    )
    assert send_dup.status_code == 200
    assert send_dup.json()["data"]["id"] == msg1["id"]

    # 4. Doctor accepts and opens thread -> sees citizen's message
    doc_thread_res = client.get(f"/api/doctor-chat/requests/{req_id}/thread", headers=doc_headers)
    assert doc_thread_res.status_code == 200
    doc_msgs = doc_thread_res.json()["data"]["messages"]
    assert len(doc_msgs) == 1
    assert doc_msgs[0]["id"] == msg1["id"]
    assert doc_msgs[0]["body"] == "Hello Doctor, I have had a throat infection since yesterday."

    # 5. Doctor sends reply message
    doc_client_msg_id = f"dmsg-{uuid.uuid4().hex[:8]}"
    send_res2 = client.post(
        f"/api/doctor-chat/conversations/{conv_id}/messages",
        headers=doc_headers,
        json={
            "body": "Please take warm saline gargles twice daily and rest.",
            "client_message_id": doc_client_msg_id
        }
    )
    assert send_res2.status_code == 200
    msg2 = send_res2.json()["data"]
    assert msg2["sender_role"] == "PHC_DOCTOR"
    assert msg2["sender_id"] == test_data["doc_user"].id
    assert msg2["body"] == "Please take warm saline gargles twice daily and rest."

    # 6. Both sides retrieve complete message history (preserves order and all fields)
    history_res = client.get(f"/api/doctor-chat/conversations/{conv_id}/messages", headers=cit_headers)
    assert history_res.status_code == 200
    all_msgs = history_res.json()["data"]
    assert len(all_msgs) == 2
    assert all_msgs[0]["client_message_id"] == cit_client_msg_id
    assert all_msgs[1]["client_message_id"] == doc_client_msg_id

    # 7. Citizen marks doctor's message as READ
    read_res = client.post(
        f"/api/doctor-chat/conversations/{conv_id}/read",
        headers=cit_headers,
        json={"up_to_message_id": msg2["id"]}
    )
    assert read_res.status_code == 200
    assert read_res.json()["data"]["read_count"] >= 1

    # Verify status changed to READ
    history_res2 = client.get(f"/api/doctor-chat/conversations/{conv_id}/messages", headers=doc_headers)
    all_msgs2 = history_res2.json()["data"]
    assert all_msgs2[1]["status"] == "READ"


def test_doctor_chat_security_and_validation(client, test_data, db_session):
    cit_headers = {"Authorization": f"Bearer {test_data['cit_token']}"}
    doc_headers = {"Authorization": f"Bearer {test_data['doc_token']}"}
    req_id = test_data["srv_req"].id

    # Resolve thread
    t_res = client.get(f"/api/doctor-chat/requests/{req_id}/thread", headers=cit_headers)
    conv_id = t_res.json()["data"]["thread"]["id"]

    # 1. Validation: Empty or whitespace message rejected
    bad_res1 = client.post(
        f"/api/doctor-chat/conversations/{conv_id}/messages",
        headers=cit_headers,
        json={"body": "   ", "client_message_id": "test-empty"}
    )
    assert bad_res1.status_code == 422 or bad_res1.status_code == 400

    # 2. Validation: Script tags sanitized safely
    xss_res = client.post(
        f"/api/doctor-chat/conversations/{conv_id}/messages",
        headers=cit_headers,
        json={"body": "Hello <script>alert('xss')</script>world", "client_message_id": f"xss-{uuid.uuid4().hex[:6]}"}
    )
    assert xss_res.status_code == 200
    assert "<script>" not in xss_res.json()["data"]["body"]
    assert "alert" not in xss_res.json()["data"]["body"]
    assert "Hello world" in xss_res.json()["data"]["body"]

    # 3. Terminal state protection: Completed consultations are read-only
    srv = db_session.query(ServiceRequest).filter(ServiceRequest.id == req_id).first()
    if srv:
        srv.status = "COMPLETED"
    th = db_session.query(DoctorChatThread).filter(DoctorChatThread.id == conv_id).first()
    if th:
        th.status = "COMPLETED"
    tele = db_session.query(TeleconsultationRequest).filter(
        (TeleconsultationRequest.service_request_id == req_id) | (TeleconsultationRequest.id == conv_id)
    ).first()
    if tele:
        tele.status = "COMPLETED"
    db_session.commit()

    post_comp = client.post(
        f"/api/doctor-chat/conversations/{conv_id}/messages",
        headers=cit_headers,
        json={"body": "Message after complete", "client_message_id": f"comp-{uuid.uuid4().hex[:6]}"}
    )
    assert post_comp.status_code == 400
    assert "terminal state" in str(post_comp.json()).lower() or "completed" in str(post_comp.json()).lower()


def test_canonical_routes_and_isolation(client, test_data, db_session):
    cit_headers = {"Authorization": f"Bearer {test_data['cit_token']}"}
    doc_headers = {"Authorization": f"Bearer {test_data['doc_token']}"}
    req_id = test_data["srv_req"].id

    # 1. Test canonical endpoint: GET /api/citizen/doctor/requests/{requestId}
    res1 = client.get(f"/api/citizen/doctor/requests/{req_id}", headers=cit_headers)
    assert res1.status_code == 200
    data1 = res1.json()["data"]
    conv_id = data1["thread"]["id"]
    assert conv_id is not None
    assert data1["thread"]["service_request_id"] == req_id
    assert data1["thread"]["beneficiary_name"] == "Sunita Patil"  # Real citizen name, NOT "Self"

    # 2. Test canonical endpoint: GET /api/care-conversations/{conversationId}/messages
    res2 = client.get(f"/api/care-conversations/{conv_id}/messages", headers=cit_headers)
    assert res2.status_code == 200
    assert isinstance(res2.json()["data"], list)

    # 3. Test canonical endpoint: POST /api/care-conversations/{conversationId}/messages
    cmsg_id = f"cmsg-care-{uuid.uuid4().hex[:6]}"
    post_res = client.post(
        f"/api/care-conversations/{conv_id}/messages",
        headers=cit_headers,
        json={"body": "hello doctor", "client_message_id": cmsg_id}
    )
    assert post_res.status_code == 200
    post_data = post_res.json()["data"]
    assert post_data["client_message_id"] == cmsg_id
    assert post_data["body"] == "hello doctor"
    assert post_data["delivery_status"] == "DELIVERED"
    assert post_data["status"] == "DELIVERED"

    # Verify DB persistence of exact row
    db_msg = db_session.query(DoctorChatMessage).filter(DoctorChatMessage.client_message_id == cmsg_id).first()
    assert db_msg is not None
    assert db_msg.body == "hello doctor"
    assert db_msg.conversation_id == conv_id
    assert db_msg.service_request_id == req_id
    assert db_msg.sender_role == "CITIZEN"
    assert db_msg.delivery_status == "DELIVERED"

    # 4. Doctor receives message via GET /api/care-conversations/{conversationId}/messages
    get_res = client.get(f"/api/care-conversations/{conv_id}/messages", headers=doc_headers)
    assert get_res.status_code == 200
    msgs = get_res.json()["data"]
    assert any(m["client_message_id"] == cmsg_id and m["body"] == "hello doctor" for m in msgs)

    # 5. Doctor replies "How can I help you?"
    doc_cmsg_id = f"dmsg-care-{uuid.uuid4().hex[:6]}"
    doc_post_res = client.post(
        f"/api/care-conversations/{conv_id}/messages",
        headers=doc_headers,
        json={"body": "How can I help you?", "client_message_id": doc_cmsg_id}
    )
    assert doc_post_res.status_code == 200
    assert doc_post_res.json()["data"]["body"] == "How can I help you?"

    # 6. Citizen receives doctor reply via GET /api/care-conversations/{conversationId}/messages
    cit_get_res = client.get(f"/api/care-conversations/{conv_id}/messages", headers=cit_headers)
    assert cit_get_res.status_code == 200
    cit_msgs = cit_get_res.json()["data"]
    assert any(m["client_message_id"] == doc_cmsg_id and m["body"] == "How can I help you?" for m in cit_msgs)

    # 7. Test Cross-Citizen Isolation: A different citizen user CANNOT access this conversation
    other_cit_user = User(
        id=str(uuid.uuid4()),
        identifier=f"other_cit_{uuid.uuid4().hex[:6]}",
        name="Asha Shinde",
        phone="9876543299",
        password_hash=get_password_hash("testpass123"),
        role=UserRoleEnum.CITIZEN
    )
    db_session.add(other_cit_user)
    db_session.flush()

    other_cit_profile = CitizenProfile(
        id=str(uuid.uuid4()),
        user_id=other_cit_user.id,
        display_name="Asha Shinde",
        phone="9876543299",
        village_name="Kalyanpur"
    )
    db_session.add(other_cit_profile)
    db_session.commit()

    other_cit_token = create_access_token(data={"sub": other_cit_user.id, "role": "CITIZEN", "user_id": other_cit_user.id})
    other_cit_headers = {"Authorization": f"Bearer {other_cit_token}"}

    # Attempt access by unauthorized citizen -> MUST return 403
    unauth_res = client.get(f"/api/citizen/doctor/requests/{req_id}", headers=other_cit_headers)
    assert unauth_res.status_code == 403

    unauth_res2 = client.get(f"/api/care-conversations/{conv_id}/messages", headers=other_cit_headers)
    assert unauth_res2.status_code == 403

    unauth_res3 = client.post(
        f"/api/care-conversations/{conv_id}/messages",
        headers=other_cit_headers,
        json={"body": "Hacked message", "client_message_id": "hack-1"}
    )
    assert unauth_res3.status_code == 403


def test_doctor_request_creation_and_canonical_identifiers(client, test_data, db_session):
    cit_headers = {"Authorization": f"Bearer {test_data['cit_token']}"}

    # 1. Citizen creates Doctor Chat Request via POST /api/citizen/doctor/requests
    idemp_key = f"idemp-test-{uuid.uuid4().hex[:8]}"
    create_payload = {
        "beneficiary_id": test_data["cit_profile"].id,
        "channel": "CHAT",
        "chief_complaint": "Acute throat pain and fever",
        "symptoms": ["Throat pain", "Fever"],
        "preferred_language": "en-IN",
        "idempotency_key": idemp_key
    }

    create_res = client.post("/api/citizen/doctor/requests", headers=cit_headers, json=create_payload)
    assert create_res.status_code == 200
    data = create_res.json()["data"]

    # Verify all 7 canonical identifiers
    assert "service_request_id" in data and data["service_request_id"] is not None
    assert "request_reference" in data and data["request_reference"].startswith("DOCREQ-")
    assert "conversation_id" in data and data["conversation_id"] is not None
    assert "case_id" in data and data["case_id"] is not None
    assert "citizen_id" in data and data["citizen_id"] == test_data["cit_profile"].id
    assert "channel" in data and data["channel"] == "CHAT"
    assert data["status"] == "WAITING_FOR_DOCTOR"

    srv_id = data["service_request_id"]
    conv_id = data["conversation_id"]

    # 2. Idempotent repeated submission returns same identifiers
    create_res_dup = client.post("/api/citizen/doctor/requests", headers=cit_headers, json=create_payload)
    assert create_res_dup.status_code == 200
    dup_data = create_res_dup.json()["data"]
    assert dup_data["service_request_id"] == srv_id
    assert dup_data["conversation_id"] == conv_id

    # 3. Fetch canonical waiting room detail
    wr_res = client.get(f"/api/citizen/doctor/requests/{srv_id}", headers=cit_headers)
    assert wr_res.status_code == 200
    wr_data = wr_res.json()["data"]
    assert wr_data["thread"]["id"] == conv_id
    assert wr_data["thread"]["service_request_id"] == srv_id
    assert wr_data["request_details"]["id"] == srv_id

