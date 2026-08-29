from fastapi.testclient import TestClient

def get_asha_token(client: TestClient):
    res = client.post("/api/auth/login", json={"identifier": "sita.asha", "password": "demo123"})
    assert res.status_code == 200
    return res.json()["data"]["access_token"]

def test_patient_only_registration_flow(client: TestClient):
    """Verify Register Patient Only creates citizen, but NO case, clinical complaint, or referral."""
    token = get_asha_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    
    import random
    unique_num = random.randint(100000, 999999)
    phone = f"9876{unique_num}"
    
    payload = {
        "client_registration_id": f"REG-ONLY-{unique_num}",
        "full_name": f"Test Citizen Only {unique_num}",
        "exact_dob_unknown": False,
        "date_of_birth": "1995-05-12",
        "approximate_age": 31,
        "sex": "Female",
        "phone": phone,
        "preferred_contact_method": "PHONE",
        "village_name": "Kalyanpur",
        "state": "Maharashtra",
        "district": "District 04",
        "block_taluka": "Kalyanpur Block",
        "gram_panchayat": "Kalyanpur GP",
        "assigned_facility_id": "PHC-09",
        "registration_consent_obtained": True,
        "consent_method": "VERBAL",
        "preferred_language": "mr-IN",
        "create_current_case": False,
        "vitals": {
            "measured": False,
            "unmeasured_reason": "Patient registration only"
        },
        "referral": {
            "required": False
        },
        "follow_up": {
            "required": False
        },
        "accuracy_confirmed_by_asha": True
    }

    resp = client.post("/api/asha/patient-registration", json=payload, headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    citizen_id = data["citizen_id"]
    assert citizen_id is not None
    assert data["case_id"] is None
    assert data["case_reference"] is None
    assert data["referral_id"] is None

    # Verify citizen appears in People directory
    people_resp = client.get("/api/asha/people", headers=headers)
    assert people_resp.status_code == 200
    people = people_resp.json()["data"]
    matched = [p for p in people if p["id"] == citizen_id]
    assert len(matched) == 1
    assert matched[0]["name"] == f"Test Citizen Only {unique_num}"
    assert matched[0]["latest_case_id"] is None

    # Verify /api/asha/cases/citizen-{citizen_id} returns structured profile with NO_ACTIVE_CASE
    case_resp = client.get(f"/api/asha/cases/citizen-{citizen_id}", headers=headers)
    assert case_resp.status_code == 200
    case_data = case_resp.json()["data"]
    assert case_data["status"] == "NO_ACTIVE_CASE"
    assert case_data["primary_concern"] == "No active health concern"
    assert case_data["citizen_id"] == citizen_id

def test_register_patient_and_record_health_concern_flow(client: TestClient):
    """Verify Register Patient and Record Health Concern creates citizen, Case, SymptomObservation, Referral, and Follow-up."""
    token = get_asha_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    import random
    unique_num = random.randint(100000, 999999)
    phone = f"9877{unique_num}"

    payload = {
        "client_registration_id": f"REG-CASE-{unique_num}",
        "full_name": f"Test Citizen Case {unique_num}",
        "exact_dob_unknown": False,
        "date_of_birth": "1998-08-20",
        "approximate_age": 28,
        "sex": "Female",
        "phone": phone,
        "preferred_contact_method": "PHONE",
        "village_name": "Kalyanpur",
        "state": "Maharashtra",
        "district": "District 04",
        "block_taluka": "Kalyanpur Block",
        "gram_panchayat": "Kalyanpur GP",
        "assigned_facility_id": "PHC-09",
        "registration_consent_obtained": True,
        "consent_method": "VERBAL",
        "preferred_language": "mr-IN",
        "create_current_case": True,
        "chief_complaint": "Severe headache and blurred vision for 3 days",
        "duration": "3 days",
        "severity": "SEVERE",
        "symptoms": ["Severe Headache", "Blurred Vision"],
        "vitals": {
            "measured": True,
            "systolic_bp": 155,
            "diastolic_bp": 98,
            "temperature_c": 37.1,
            "spo2": 97,
            "pulse": 88
        },
        "special_conditions": {
            "condition_type": "PREGNANCY",
            "maternal": {
                "gestational_weeks": 26,
                "anc_registered": True,
                "severe_headache": True,
                "blurred_vision": True
            }
        },
        "referral": {
            "required": True,
            "facility_id": "PHC-09",
            "urgency": "URGENT",
            "reason": "Maternal hypertension (BP 155/98) and blurred vision in pregnancy",
            "citizen_response": "ACCEPTED"
        },
        "follow_up": {
            "required": True,
            "due_date": "2026-08-28",
            "purpose": "Verify PHC attendance and repeat BP check",
            "notes": "Home visit after PHC consultation"
        },
        "accuracy_confirmed_by_asha": True
    }

    # Test via alias route /api/asha/patients/register
    resp = client.post("/api/asha/patients/register", json=payload, headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    
    assert data["citizen_id"] is not None
    assert data["case_id"] is not None
    assert data["case_reference"] is not None
    assert data["referral_id"] is not None
    assert data["follow_up_id"] is not None

    citizen_id = data["citizen_id"]
    case_id = data["case_id"]

    # Verify case review API endpoint returns complete data
    case_resp = client.get(f"/api/asha/cases/{case_id}", headers=headers)
    assert case_resp.status_code == 200
    case_data = case_resp.json()["data"]
    assert case_data["citizen_name"] == f"Test Citizen Case {unique_num}"
    assert case_data["safety_rule_triggered"] == True
    assert len(case_data["symptoms"]) >= 2
    assert len(case_data["referrals"]) >= 1
    assert len(case_data["followups"]) >= 1

def test_patient_plus_followup_only_flow(client: TestClient):
    """Verify Patient registration with Follow-up only (no referral)."""
    token = get_asha_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    import random
    unique_num = random.randint(100000, 999999)
    phone = f"9878{unique_num}"

    payload = {
        "client_registration_id": f"REG-FUP-{unique_num}",
        "full_name": f"Test Patient Followup {unique_num}",
        "sex": "Female",
        "phone": phone,
        "village_name": "Kalyanpur",
        "create_current_case": False,
        "registration_consent_obtained": True,
        "follow_up": {
            "required": True,
            "due_date": "2026-08-30",
            "purpose": "Routine monthly health checkup",
            "notes": "Verify nutritional intake"
        },
        "referral": {
            "required": False
        },
        "accuracy_confirmed_by_asha": True
    }

    resp = client.post("/api/asha/patient-registration", json=payload, headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["citizen_id"] is not None
    assert data["follow_up_id"] is not None
    assert data["referral_id"] is None

def test_patient_plus_referral_only_flow(client: TestClient):
    """Verify Patient registration with PHC Referral only (no follow-up)."""
    token = get_asha_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    import random
    unique_num = random.randint(100000, 999999)
    phone = f"9879{unique_num}"

    payload = {
        "client_registration_id": f"REG-REF-{unique_num}",
        "full_name": f"Test Patient Referral {unique_num}",
        "sex": "Male",
        "phone": phone,
        "village_name": "Kalyanpur",
        "create_current_case": True,
        "chief_complaint": "Persistent cough and mild fever",
        "registration_consent_obtained": True,
        "referral": {
            "required": True,
            "facility_id": "PHC-09",
            "urgency": "ROUTINE",
            "reason": "Chest examination required by Medical Officer",
            "citizen_response": "ACCEPTED"
        },
        "follow_up": {
            "required": False
        },
        "accuracy_confirmed_by_asha": True
    }

    resp = client.post("/api/asha/patient-registration", json=payload, headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["citizen_id"] is not None
    assert data["referral_id"] is not None
    assert data["follow_up_id"] is None

def test_double_submit_idempotency_and_offline_replay(client: TestClient):
    """Verify double-submit with same client_registration_id returns exact cached record."""
    token = get_asha_token(client)
    headers = {"Authorization": f"Bearer {token}"}

    import random
    unique_num = random.randint(100000, 999999)
    client_reg_id = f"REG-IDEMP-{unique_num}"
    phone = f"9880{unique_num}"

    payload = {
        "client_registration_id": client_reg_id,
        "full_name": f"Test Idempotent Citizen {unique_num}",
        "sex": "Female",
        "phone": phone,
        "village_name": "Kalyanpur",
        "create_current_case": True,
        "chief_complaint": "Headache",
        "registration_consent_obtained": True,
        "accuracy_confirmed_by_asha": True
    }

    # First submit
    resp1 = client.post(
        "/api/asha/patient-registration",
        json=payload,
        headers={"Authorization": f"Bearer {token}", "X-Idempotency-Key": client_reg_id}
    )
    assert resp1.status_code == 200, resp1.text
    data1 = resp1.json()["data"]

    # Replay submit (exact-once synchronization)
    resp2 = client.post(
        "/api/asha/patient-registration",
        json=payload,
        headers={"Authorization": f"Bearer {token}", "X-Idempotency-Key": client_reg_id}
    )
    assert resp2.status_code == 200, resp2.text
    data2 = resp2.json()["data"]

    # Must return exact same citizen_id and case_id without creating duplicate records
    assert data1["citizen_id"] == data2["citizen_id"]
    assert data1["case_id"] == data2["case_id"]
