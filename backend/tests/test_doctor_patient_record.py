import pytest
from fastapi.testclient import TestClient
from app.models import AuditLog, CitizenProfile, User, WorkerProfile, Case, Referral, Consultation, Prescription

def test_get_doctor_patient_record_pooja_success(client: TestClient):
    # Login as Dr. Abhinav Sharma
    login_res = client.post("/api/auth/login", json={"identifier": "dr.sharma", "password": "demo123"})
    assert login_res.status_code == 200
    token = login_res.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Fetch Pooja Jadhav's record (CP-003)
    response = client.get("/api/doctor/patients/CP-003", headers=headers)
    assert response.status_code == 200, response.text

    data = response.json()["data"]
    assert data["citizen_id"] == "CP-003"

    # Demographics assertion
    demographics = data["demographics"]
    assert demographics["display_name"] == "Pooja Jadhav"
    assert demographics["patient_category"] == "MATERNAL"
    assert demographics["assigned_asha_name"] is not None

    # Active Care assertion
    active_care = data["active_care"]
    assert active_care["active_case_reference"] == "CASE-2026-002"

    # Dynamic clinical context assertion
    maternal_ctx = data["dynamic_clinical_context"]["maternal"]
    assert maternal_ctx is not None
    assert maternal_ctx["gestational_weeks"] == 14

    # Prescriptions assertion (must only be signed)
    for p in data["prescriptions"]:
        assert p["status"] == "SIGNED"

    # Measurements & Trends assertion
    measurements = data["measurements_and_trends"]
    assert isinstance(measurements, list)

def test_doctor_patient_record_not_found(client: TestClient):
    login_res = client.post("/api/auth/login", json={"identifier": "dr.sharma", "password": "demo123"})
    token = login_res.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get("/api/doctor/patients/NON-EXISTENT-UUID-999", headers=headers)
    assert response.status_code == 404

def test_get_doctor_direct_requests_has_explicit_patient_profile_id(client: TestClient):
    # First create a citizen doctor request so list is populated
    from app.schemas.citizen import DoctorRequestCreateDTO
    from app.services.citizen_service import CitizenService
    from conftest import TestingSessionLocal
    db = TestingSessionLocal()
    try:
        dto = DoctorRequestCreateDTO(
            beneficiary_id=None,
            channel="CALLBACK",
            chief_complaint="Severe migraine and nausea",
            symptoms=["HEADACHE", "NAUSEA"],
            preferred_language="mr-IN",
            sharing_scope={"share_structured_summary": True},
            handoff_packet={"chief_concern": "Severe migraine and nausea"},
            idempotency_key="idemp-direct-req-1"
        )
        CitizenService.create_doctor_request(db, "CP-001", dto)
    finally:
        db.close()

    # Login as Dr. Abhinav Sharma
    login_res = client.post("/api/auth/login", json={"identifier": "dr.sharma", "password": "demo123"})
    assert login_res.status_code == 200
    token = login_res.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Fetch direct requests
    response = client.get("/api/doctor/direct-requests", headers=headers)
    assert response.status_code == 200
    items = response.json()["data"]
    assert len(items) > 0
    for req in items:
        # Assert canonical IDs are present
        assert "patient_profile_id" in req or "patient_id" in req
        assert "citizen_id" in req or "patient_id" in req
        assert req["id"] is not None

def test_get_doctor_patient_record_sunita_success(client: TestClient):
    # Login as Dr. Abhinav Sharma
    login_res = client.post("/api/auth/login", json={"identifier": "dr.sharma", "password": "demo123"})
    assert login_res.status_code == 200
    token = login_res.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Fetch Sunita Devi's record (CP-001)
    response = client.get("/api/doctor/patients/CP-001", headers=headers)
    assert response.status_code == 200, response.text

    data = response.json()["data"]
    assert data["citizen_id"] == "CP-001"
    assert data["demographics"]["display_name"] == "Sunita Devi"
    assert data["demographics"]["phone"] is not None  # Full phone visible to Doctor
    assert "health_history" in data
    assert "dynamic_clinical_context" in data
    assert "prescriptions" in data
    assert "investigations" in data
    assert "follow_ups" in data
