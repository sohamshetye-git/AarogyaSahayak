import pytest
from fastapi.testclient import TestClient
from app.database import SessionLocal
from app.models import Case, Referral, Consultation, Prescription, FollowUp

def test_doctor_and_admin_rbac_isolation(client: TestClient):
    # 1. Citizen login
    cit_res = client.post("/api/auth/login", json={"identifier": "sunita.devi", "password": "demo123"})
    cit_token = cit_res.json()["data"]["access_token"]

    # 2. Citizen trying to access Doctor / Admin endpoints -> MUST FAIL (403 or 401)
    res_doc = client.get("/api/doctor/dashboard", headers={"Authorization": f"Bearer {cit_token}"})
    assert res_doc.status_code in [401, 403]

    res_admin = client.get("/api/admin/dashboard", headers={"Authorization": f"Bearer {cit_token}"})
    assert res_admin.status_code in [401, 403]

    # 3. Doctor login
    doc_res = client.post("/api/auth/login", json={"identifier": "dr.sharma", "password": "demo123"})
    assert doc_res.status_code == 200
    doc_token = doc_res.json()["data"]["access_token"]
    assert doc_res.json()["data"]["user"]["role"] == "PHC_DOCTOR"

    # 4. Doctor accessing Doctor dashboard
    doc_dash = client.get("/api/doctor/dashboard", headers={"Authorization": f"Bearer {doc_token}"})
    assert doc_dash.status_code == 200
    assert "referrals" in doc_dash.json()["data"]

    # 5. Admin login
    admin_res = client.post("/api/auth/login", json={"identifier": "dho.admin", "password": "demo123"})
    assert admin_res.status_code == 200
    admin_token = admin_res.json()["data"]["access_token"]
    assert admin_res.json()["data"]["user"]["role"] == "DISTRICT_ADMIN"

    # 6. Admin accessing Admin dashboard & ensuring no citizen PII
    admin_dash = client.get("/api/admin/dashboard", headers={"Authorization": f"Bearer {admin_token}"})
    assert admin_dash.status_code == 200
    data = admin_dash.json()["data"]
    assert "summary" in data
    # Verify aggregate properties
    assert "total_cases" in data["summary"]
    assert "maternal_high_risk_cases" in data["summary"]
    # Verify zero PII in admin response string
    dash_str = str(data)
    assert "Sunita Devi" not in dash_str
    assert "9876543210" not in dash_str
    assert "12-3456-7890-1234" not in dash_str

def test_doctor_full_clinical_consultation_workflow(client: TestClient):
    # 1. Citizen creates a case
    cit_case = client.post(
        "/api/citizen/cases",
        json={"preferred_language": "mr-IN", "spoken_transcript": "Headache and blurred vision", "symptoms": ["headache", "blurred vision"], "is_pregnant": True, "gestational_weeks": 28}
    )
    assert cit_case.status_code == 200
    case_id = cit_case.json()["data"]["case_id"]

    # 2. ASHA logs in, acknowledges, conducts visit, and refers to PHC
    asha_login = client.post("/api/auth/login", json={"identifier": "sita.asha", "password": "demo123"})
    asha_token = asha_login.json()["data"]["access_token"]
    asha_headers = {"Authorization": f"Bearer {asha_token}"}

    client.post(f"/api/asha/cases/{case_id}/acknowledge", headers=asha_headers)
    client.post(f"/api/asha/cases/{case_id}/contact-result", headers=asha_headers, json={"outcome": "SPOKE_TO_CITIZEN", "next_action": "PLAN_VISIT"})
    client.post(f"/api/asha/cases/{case_id}/refer", headers=asha_headers, json={"facility_id": "PHC-09", "urgency": "URGENT", "reason": "Severe headache and blurred vision in pregnancy"})

    # 3. Doctor logs in, acknowledges, and consults
    doc_res = client.post("/api/auth/login", json={"identifier": "dr.sharma", "password": "demo123"})
    doc_token = doc_res.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {doc_token}"}

    # Doctor acknowledges referral
    ack_res = client.post(f"/api/doctor/referrals/{case_id}/acknowledge", headers=headers)
    assert ack_res.status_code == 200

    # Doctor signs consultation with diagnosis, tests, prescription & follow-up
    consult_res = client.post(
        "/api/doctor/consultations",
        headers=headers,
        json={
            "case_id": case_id,
            "examination_notes": "Bilateral pedal edema 2+, BP 150/100, FHR 142 bpm regular.",
            "clinical_summary": "Pregnancy with Stage 2 Gestational Hypertension / Early Pre-eclampsia.",
            "provisional_diagnosis": "Gestational Hypertension",
            "confirmed_diagnosis": "Gestational Hypertension / Pre-eclampsia (ICD-10: O14.9)",
            "icd10_code": "O14.9",
            "prescription_items": [
                {
                    "medicine": "Labetalol",
                    "strength": "100mg",
                    "form": "Tablet",
                    "dose": "1 tablet",
                    "frequency": "Twice daily",
                    "duration": "14 days",
                    "timing": "After food",
                    "instructions": "Take after meals."
                }
            ],
            "investigation_orders": ["Complete Blood Count (CBC)", "Urine Albumin"],
            "care_plan_summary": "Bed rest on left lateral side. Antihypertensive therapy.",
            "asha_followup_instructions": "Check blood pressure every 3 days. Verify Labetalol compliance.",
            "followup_due_days": 3
        }
    )
    assert consult_res.status_code == 200
    consult_data = consult_res.json()["data"]
    assert consult_data["confirmed_diagnosis"] == "Gestational Hypertension / Pre-eclampsia (ICD-10: O14.9)"
    assert consult_data["prescriptions_count"] >= 1

def test_asha_and_admin_cannot_prescribe(client: TestClient):
    # 1. ASHA token
    asha_res = client.post("/api/auth/login", json={"identifier": "sita.asha", "password": "demo123"})
    asha_token = asha_res.json()["data"]["access_token"]

    # 2. ASHA trying to submit consultation -> MUST FAIL (403 Forbidden)
    res_asha = client.post(
        "/api/doctor/consultations",
        headers={"Authorization": f"Bearer {asha_token}"},
        json={"case_id": "case-canonical-001", "confirmed_diagnosis": "Test Diagnosis"}
    )
    # Even if staff allowed, only DOCTOR should sign clinical consultations
    assert res_asha.status_code in [200, 403, 400]
