from fastapi.testclient import TestClient

def test_full_canonical_scenario_vertical_slice(client: TestClient):
    # Step 1: Login as ASHA
    asha_login = client.post("/api/auth/login", json={"identifier": "sita.asha", "password": "demo123"})
    assert asha_login.status_code == 200
    asha_token = asha_login.json()["data"]["access_token"]
    asha_headers = {"Authorization": f"Bearer {asha_token}"}

    # Step 2: Login as Doctor
    doc_login = client.post("/api/auth/login", json={"identifier": "dr.sharma", "password": "demo123"})
    assert doc_login.status_code == 200
    doc_token = doc_login.json()["data"]["access_token"]
    doc_headers = {"Authorization": f"Bearer {doc_token}"}

    # Step 3: Citizen creates case (Sunita Devi pregnancy warning signs)
    create_res = client.post(
        "/api/citizen/cases",
        json={
            "preferred_language": "mr-IN",
            "spoken_transcript": "मला खूप डोकेदुखी होत आहे आणि डोळ्यांसमोर अंधारी येत आहे.",
            "symptoms": ["blurred vision", "severe headache", "swollen feet"],
            "is_pregnant": True,
            "gestational_weeks": 28,
            "vitals": {"systolic_bp": 150, "diastolic_bp": 100, "spo2": 97}
        }
    )
    assert create_res.status_code == 200
    case_data = create_res.json()["data"]
    case_id = case_data["case_id"]
    assert case_data["priority"] == "URGENT"
    assert case_data["safety_rule_triggered"] is True

    # Step 4: ASHA dashboard sees case & acknowledges it
    tasks_res = client.get("/api/asha/tasks", headers=asha_headers)
    assert tasks_res.status_code == 200

    ack_res = client.post(f"/api/asha/cases/{case_id}/acknowledge", headers=asha_headers)
    assert ack_res.status_code == 200
    assert ack_res.json()["data"]["status"] == "ASHA_ACKNOWLEDGED"

    # Step 5: ASHA conducts visit & submits field report + refers to PHC
    visit_res = client.post(
        "/api/asha/visits",
        headers=asha_headers,
        json={
            "case_id": case_id,
            "consent_obtained": True,
            "symptoms": ["blurred vision", "severe headache", "swollen feet"],
            "vitals": {"systolic_bp": 150, "diastolic_bp": 100, "spo2": 97, "pulse": 88},
            "notes": "Field visit confirmed BP 150/100. Referred immediately to Kalyanpur PHC.",
            "next_action": "REFER_TO_PHC",
            "refer_to_facility_id": "PHC-09"
        }
    )
    assert visit_res.status_code == 200

    # Step 6: Doctor views referrals and acknowledges
    doc_refs = client.get("/api/doctor/referrals", headers=doc_headers)
    assert doc_refs.status_code == 200

    doc_ack = client.post(f"/api/doctor/referrals/{case_id}/acknowledge", headers=doc_headers)
    assert doc_ack.status_code == 200

    # Step 7: Doctor completes consultation with diagnosis, prescription, care plan & follow-up
    consult_res = client.post(
        "/api/doctor/consultations",
        headers=doc_headers,
        json={
            "case_id": case_id,
            "examination_notes": "Patient conscious, pedal edema 2+, BP 150/100 confirmed.",
            "clinical_summary": "Pre-eclampsia screening positive. Initiating antihypertensive and strict monitoring.",
            "confirmed_diagnosis": "Gestational Hypertension / Pre-eclampsia (ICD-10: O14.9)",
            "icd10_code": "O14.9",
            "prescription_items": [
                {
                    "medicine": "Labetalol",
                    "strength": "100mg",
                    "dose": "1 tablet",
                    "frequency": "Twice daily",
                    "duration": "14 days",
                    "instructions": "Take after meals. Do not skip doses."
                },
                {
                    "medicine": "Calcium + Vitamin D3",
                    "strength": "500mg",
                    "dose": "1 tablet",
                    "frequency": "Once daily",
                    "duration": "30 days"
                }
            ],
            "investigation_orders": ["Complete Blood Count (CBC)", "Urine Albumin (Dipstick)", "Serum Creatinine"],
            "care_plan_summary": "Rest on left lateral side. Low sodium diet. Immediate referral to District Hospital if headache worsens.",
            "asha_followup_instructions": "Visit patient at home every 3 days to record BP and verify medication adherence.",
            "followup_due_days": 3
        }
    )
    assert consult_res.status_code == 200
    consult_data = consult_res.json()["data"]
    assert consult_data["status"] == "FOLLOW_UP_REQUIRED"
    assert consult_data["confirmed_diagnosis"] == "Gestational Hypertension / Pre-eclampsia (ICD-10: O14.9)"

    # Step 8: Citizen checks status and sees updated completed state
    status_res = client.get(f"/api/citizen/cases/{case_id}")
    assert status_res.status_code == 200
    assert "Doctor has prescribed a care plan" in status_res.json()["data"]["status_explanation"]
