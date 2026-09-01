import pytest
import uuid
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app.models import (
    User, WorkerProfile, Facility, ServiceRequest, CareHandoff,
    SharingConsent, Case, TeleconsultationRequest, DoctorChatThread,
    UserRoleEnum, CaseStatusEnum
)
from app.auth.security import create_access_token
from app.db.repair_doctor_requests import repair_doctor_citizen_requests

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def test_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_auth_headers(user_id: str, role: str = "PHC_DOCTOR"):
    token = create_access_token({"sub": user_id, "role": role})
    return {"Authorization": f"Bearer {token}"}

def test_facility_scoped_waiting_request_visibility(client: TestClient, test_db):
    """
    Test that a doctor at PHC-09 can view WAITING_FOR_DOCTOR requests for PHC-09,
    and the response matches the typed envelope contract.
    """
    # 1. Ensure PHC-09 Facility and Doctor exist
    fac = test_db.query(Facility).filter(Facility.id == "FAC-TEST-PHC-01").first()
    if not fac:
        fac = Facility(id="FAC-TEST-PHC-01", name="Test PHC Center", code="TEST-PHC-01", is_active=True)
        test_db.add(fac)
        test_db.flush()

    doc_user = test_db.query(User).filter(User.identifier == "test.doc.phc01").first()
    if not doc_user:
        doc_user = User(
            id=str(uuid.uuid4()),
            identifier="test.doc.phc01",
            name="Dr. Test Specialist",
            role=UserRoleEnum.PHC_DOCTOR,
            password_hash="fakehash",
            is_active=True
        )
        test_db.add(doc_user)
        test_db.flush()
        wp = WorkerProfile(
            id=str(uuid.uuid4()),
            user_id=doc_user.id,
            worker_type="DOCTOR",
            facility_id=fac.id,
            facility_name=fac.name
        )
        test_db.add(wp)
        test_db.flush()

    # Create a WAITING_FOR_DOCTOR request for this facility
    req_ref = f"DOCREQ-TEST-{uuid.uuid4().hex[:6].upper()}"
    sr = ServiceRequest(
        id=str(uuid.uuid4()),
        request_reference=req_ref,
        citizen_id="CP-001",
        request_type="DOCTOR_CONSULTATION",
        requested_channel="CHAT",
        status="WAITING_FOR_DOCTOR",
        priority="ROUTINE",
        assigned_facility_id=fac.id,
        details={"chief_complaint": "Persistent cough and sore throat"}
    )
    test_db.add(sr)
    test_db.commit()

    headers = get_auth_headers(doc_user.id, "PHC_DOCTOR")

    # 2. Call GET /api/doctor/direct-requests
    res = client.get("/api/doctor/direct-requests", headers=headers)
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    body = res.json()
    assert "data" in body
    data = body["data"]

    # Verify typed contract
    assert "items" in data, "Response data must contain 'items' array"
    assert "total" in data, "Response data must contain 'total' count"
    assert "counts" in data, "Response data must contain 'counts' dictionary"
    assert "waiting" in data["counts"]
    assert "urgent" in data["counts"]
    assert "accepted" in data["counts"]
    assert "in_consultation" in data["counts"]
    assert "completed" in data["counts"]

    found = [it for it in data["items"] if it["request_reference"] == req_ref]
    assert len(found) == 1
    assert found[0]["id"] == sr.id
    assert found[0]["status"] == "WAITING_FOR_DOCTOR"
    assert found[0]["chief_complaint"] == "Persistent cough and sore throat"

def test_authenticated_doctor_identity(client: TestClient, test_db):
    """
    Test that /api/auth/me returns authoritative doctor principal with matching facility.
    """
    doc_user = test_db.query(User).filter(User.identifier == "dr.sharma").first()
    assert doc_user is not None, "Dr. Sharma user should exist in DB"

    headers = get_auth_headers(doc_user.id, "PHC_DOCTOR")
    res = client.get("/api/auth/me", headers=headers)
    assert res.status_code == 200
    user_data = res.json()["data"]

    assert user_data["id"] == doc_user.id
    assert user_data["name"] == doc_user.name
    assert user_data["role"] == "PHC_DOCTOR"
    assert user_data["facility_id"] == "PHC-09"

def test_unauthorized_facility_isolation(client: TestClient, test_db):
    """
    Test that a doctor from FAC-ISOLATED-02 CANNOT view or accept requests from FAC-TEST-PHC-01.
    """
    # Doctor at Facility B
    doc_b = test_db.query(User).filter(User.identifier == "test.doc.fac_b").first()
    if not doc_b:
        doc_b = User(
            id=str(uuid.uuid4()),
            identifier="test.doc.fac_b",
            name="Dr. Facility B Doctor",
            role=UserRoleEnum.PHC_DOCTOR,
            password_hash="fakehash",
            is_active=True
        )
        test_db.add(doc_b)
        test_db.flush()
        wp_b = WorkerProfile(
            id=str(uuid.uuid4()),
            user_id=doc_b.id,
            worker_type="DOCTOR",
            facility_id="FAC-ISOLATED-02",
            facility_name="Isolated Facility B"
        )
        test_db.add(wp_b)
        test_db.flush()

    # Request at Facility A
    req_ref_a = f"DOCREQ-FACA-{uuid.uuid4().hex[:6].upper()}"
    sr_a = ServiceRequest(
        id=str(uuid.uuid4()),
        request_reference=req_ref_a,
        citizen_id="CP-001",
        request_type="DOCTOR_CONSULTATION",
        requested_channel="CHAT",
        status="WAITING_FOR_DOCTOR",
        priority="ROUTINE",
        assigned_facility_id="FAC-TEST-PHC-01",
        details={"chief_complaint": "Facility A patient request"}
    )
    test_db.add(sr_a)
    test_db.commit()

    headers_b = get_auth_headers(doc_b.id, "PHC_DOCTOR")

    # Doctor B lists direct requests -> should NOT see SR A
    res_list = client.get("/api/doctor/direct-requests", headers=headers_b)
    assert res_list.status_code == 200
    items = res_list.json()["data"]["items"]
    assert all(it["id"] != sr_a.id for it in items), "Doctor B must not see Facility A requests"

    # Doctor B attempts to view SR A detail -> 403 Forbidden
    res_detail = client.get(f"/api/doctor/direct-requests/{sr_a.id}", headers=headers_b)
    assert res_detail.status_code == 403, f"Expected 403 Forbidden, got {res_detail.status_code}"

    # Doctor B attempts to accept SR A -> 403 Forbidden
    res_accept = client.post(f"/api/doctor/direct-requests/{sr_a.id}/accept", headers=headers_b)
    assert res_accept.status_code == 403, f"Expected 403 Forbidden, got {res_accept.status_code}"

def test_acceptance_idempotency_and_companion_sync(client: TestClient, test_db):
    """
    Test that doctor accepting a request updates ServiceRequest, TeleconsultationRequest,
    DoctorChatThread, and Case atomically, and is idempotent on repeat calls.
    """
    doc_user = test_db.query(User).filter(User.identifier == "dr.sharma").first()
    headers = get_auth_headers(doc_user.id, "PHC_DOCTOR")

    # Create Case, SR, TeleReq, Thread
    c = Case(
        id=str(uuid.uuid4()),
        reference=f"AC-TEST-{uuid.uuid4().hex[:6].upper()}",
        citizen_id="CP-001",
        primary_concern="Fever and chills",
        status=CaseStatusEnum.NEW,
        assigned_facility_id="PHC-09"
    )
    test_db.add(c)
    test_db.flush()

    sr = ServiceRequest(
        id=str(uuid.uuid4()),
        request_reference=f"DOCREQ-SYNC-{uuid.uuid4().hex[:6].upper()}",
        citizen_id="CP-001",
        case_id=c.id,
        request_type="DOCTOR_CONSULTATION",
        requested_channel="CHAT",
        status="WAITING_FOR_DOCTOR",
        priority="HIGH",
        assigned_facility_id="PHC-09",
        details={"chief_complaint": "Fever and chills"}
    )
    test_db.add(sr)
    test_db.flush()

    tele = TeleconsultationRequest(
        id=str(uuid.uuid4()),
        public_reference=sr.request_reference,
        citizen_id="CP-001",
        service_request_id=sr.id,
        case_id=c.id,
        facility_id="PHC-09",
        status="WAITING_FOR_DOCTOR",
        priority="HIGH",
        chief_complaint="Fever and chills"
    )
    test_db.add(tele)
    test_db.flush()

    thread = DoctorChatThread(
        id=tele.id,
        service_request_id=sr.id,
        citizen_id="CP-001",
        facility_id="PHC-09",
        channel="DOCTOR_CHAT",
        status="WAITING_FOR_DOCTOR"
    )
    test_db.add(thread)
    test_db.commit()

    # 1. First Acceptance
    res1 = client.post(f"/api/doctor/direct-requests/{sr.id}/accept", headers=headers)
    assert res1.status_code == 200
    assert res1.json()["data"]["status"] == "DOCTOR_ACCEPTED"

    # Verify DB state
    test_db.refresh(sr)
    test_db.refresh(tele)
    test_db.refresh(thread)
    test_db.refresh(c)
    assert sr.status == "DOCTOR_ACCEPTED"
    assert sr.assigned_user_id == doc_user.id
    assert tele.status == "DOCTOR_ACCEPTED"
    assert tele.assigned_doctor_id == doc_user.id
    assert thread.status == "DOCTOR_ACCEPTED"
    assert thread.doctor_id == doc_user.id
    assert c.status == CaseStatusEnum.DOCTOR_ACKNOWLEDGED

    # 2. Second Acceptance (Idempotent)
    res2 = client.post(f"/api/doctor/direct-requests/{sr.id}/accept", headers=headers)
    assert res2.status_code == 200
    assert res2.json()["data"]["status"] == "DOCTOR_ACCEPTED"

def test_canonical_status_counts(client: TestClient, test_db):
    """
    Test summary endpoint counts match database status aggregation.
    """
    doc_user = test_db.query(User).filter(User.identifier == "dr.sharma").first()
    headers = get_auth_headers(doc_user.id, "PHC_DOCTOR")

    res = client.get("/api/doctor/direct-requests/summary", headers=headers)
    assert res.status_code == 200
    sum_data = res.json()["data"]

    assert "total" in sum_data
    assert "waiting" in sum_data
    assert "urgent" in sum_data
    assert "accepted" in sum_data
    assert "in_consultation" in sum_data
    assert "completed" in sum_data

    # Verify list response counts match summary counts
    list_res = client.get("/api/doctor/direct-requests?status=ALL", headers=headers)
    assert list_res.status_code == 200
    list_counts = list_res.json()["data"]["counts"]

    assert list_counts["waiting"] == sum_data["waiting"]
    assert list_counts["urgent"] == sum_data["urgent"]
    assert list_counts["accepted"] == sum_data["accepted"]
    assert list_counts["in_consultation"] == sum_data["in_consultation"]
    assert list_counts["completed"] == sum_data["completed"]

def test_existing_request_restoration_migration(test_db):
    """
    Test that the repair migration script successfully audits and reconciles requests.
    """
    repairs = repair_doctor_citizen_requests(test_db)
    assert isinstance(repairs, int)
    # Subsequent run must be 0
    repairs_idemp = repair_doctor_citizen_requests(test_db)
    assert repairs_idemp == 0
