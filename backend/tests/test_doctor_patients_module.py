import pytest
from fastapi.testclient import TestClient

def test_doctor_patients_summary(client: TestClient):
    login_res = client.post("/api/auth/login", json={"identifier": "dr.sharma", "password": "demo123"})
    assert login_res.status_code == 200
    token = login_res.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get("/api/doctor/patients/summary", headers=headers)
    assert res.status_code == 200, res.text
    data = res.json()["data"]
    assert "total_phc_patients" in data
    assert "active_cases" in data
    assert "high_risk_active_care" in data
    assert "patients_waiting_at_phc" in data
    assert "followups_required" in data
    assert "results_ready" in data
    assert "consultations_today" in data

def test_doctor_patients_list_search_filter_pagination(client: TestClient):
    login_res = client.post("/api/auth/login", json={"identifier": "dr.sharma", "password": "demo123"})
    token = login_res.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Search Pooja
    res = client.get("/api/doctor/patients?search=Pooja", headers=headers)
    assert res.status_code == 200
    items = res.json()["data"]["items"]
    assert len(items) >= 1
    pooja = next(p for p in items if p["display_name"] == "Pooja Jadhav")
    assert pooja["patient_category"] == "MATERNAL"
    assert pooja["phone"] is not None  # Authorized doctor gets full phone

    # 2. Filter Maternal
    res_mat = client.get("/api/doctor/patients?filter=MATERNAL", headers=headers)
    assert res_mat.status_code == 200
    mat_items = res_mat.json()["data"]["items"]
    for m in mat_items:
        assert m["is_pregnant"] is True or m["patient_category"] == "MATERNAL"

    # 3. Pagination
    res_page = client.get("/api/doctor/patients?page=1&page_size=5", headers=headers)
    assert res_page.status_code == 200
    p_data = res_page.json()["data"]
    assert p_data["page"] == 1
    assert p_data["page_size"] == 5
    assert len(p_data["items"]) <= 5

def test_admin_phone_pii_omission(client: TestClient):
    login_res = client.post("/api/auth/login", json={"identifier": "dho.admin", "password": "demo123"})
    assert login_res.status_code == 200
    token = login_res.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Admin accessing patient record
    res = client.get("/api/doctor/patients/CP-003", headers=headers)
    assert res.status_code == 200
    demographics = res.json()["data"]["demographics"]
    # Admin must NOT receive raw phone
    assert demographics.get("phone") is None
    assert demographics.get("phone_masked") is not None

def test_doctor_patient_sub_resources(client: TestClient):
    login_res = client.post("/api/auth/login", json={"identifier": "dr.sharma", "password": "demo123"})
    token = login_res.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    citizen_id = "CP-003"  # Pooja Jadhav

    # Cases
    res_cases = client.get(f"/api/doctor/patients/{citizen_id}/cases", headers=headers)
    assert res_cases.status_code == 200
    assert isinstance(res_cases.json()["data"], list)

    # Measurements
    res_meas = client.get(f"/api/doctor/patients/{citizen_id}/measurements", headers=headers)
    assert res_meas.status_code == 200
    assert isinstance(res_meas.json()["data"], list)

    # Record new PHC measurement
    res_post_meas = client.post(f"/api/doctor/patients/{citizen_id}/measurements", headers=headers, json={
        "systolic_bp": 120,
        "diastolic_bp": 80,
        "spo2": 99,
        "pulse": 72
    })
    assert res_post_meas.status_code == 200
    assert res_post_meas.json()["data"]["status"] == "RECORDED"

    # Contact attempt audit
    res_contact = client.post(f"/api/doctor/patients/{citizen_id}/contact-attempt", headers=headers, json={
        "target": "CITIZEN",
        "outcome": "ANSWERED",
        "notes": "Followed up regarding ANC checkup"
    })
    assert res_contact.status_code == 200
    assert res_contact.json()["data"]["status"] == "AUDITED"

    # Request demographic update
    res_demo = client.post(f"/api/doctor/patients/{citizen_id}/request-demographic-update", headers=headers, json={
        "corrections": {"preferred_language": "mr-IN"},
        "verification_note": "Doctor verified patient language preference during PHC visit"
    })
    assert res_demo.status_code == 200
    assert res_demo.json()["data"]["status"] == "SUBMITTED"
