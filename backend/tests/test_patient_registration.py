import pytest
from app.models import CitizenProfile, Case, AshaVisit, Referral, AuditLog
from app.models import CasePriorityEnum, CaseStatusEnum

def get_asha_token(client):
    res = client.post("/api/auth/login", json={"identifier": "sita.asha", "password": "demo123"})
    assert res.status_code == 200
    return res.json()["data"]["access_token"]

def get_doctor_token(client):
    res = client.post("/api/auth/login", json={"identifier": "abhinav.doctor", "password": "demo123"})
    assert res.status_code == 200
    return res.json()["data"]["access_token"]

def test_get_patient_registration_options(client):
    token = get_asha_token(client)
    res = client.get("/api/asha/patient-registration/options", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()["data"]
    assert "villages" in data
    assert "facilities" in data
    assert "symptoms" in data
    assert len(data["villages"]) >= 1
    assert len(data["facilities"]) >= 1

def test_duplicate_check_finds_existing_patient(client):
    token = get_asha_token(client)
    # Sunita Devi is in the seeded test DB
    res = client.post(
        "/api/asha/patient-registration/duplicate-check",
        json={"full_name": "Sunita Devi", "village_name": "Kalyanpur"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["has_potential_duplicate"] is True
    assert len(data["potential_matches"]) >= 1
    # Ensure masked phone is returned without leaking full number
    match = data["potential_matches"][0]
    assert match["masked_phone"] is not None
    assert "XXXX" in match["masked_phone"] or "***" in match["masked_phone"]

def test_basic_patient_only_registration(client):
    token = get_asha_token(client)
    client_reg_id = "REG-TEST-001"
    payload = {
        "client_registration_id": client_reg_id,
        "full_name": "Geeta Ramesh Patil",
        "approximate_age": 32,
        "sex": "FEMALE",
        "phone": "9811223344",
        "preferred_contact_method": "PHONE",
        "village_name": "Shivaji Nagar",
        "state": "Maharashtra",
        "district": "District 04",
        "registration_consent_obtained": True,
        "consent_method": "VERBAL",
        "create_current_case": False,
        "accuracy_confirmed_by_asha": True
    }
    res = client.post(
        "/api/asha/patient-registration",
        json=payload,
        headers={"Authorization": f"Bearer {token}", "Idempotency-Key": client_reg_id}
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["citizen_id"] is not None
    assert data["citizen_name"] == "Geeta Ramesh Patil"
    assert data["case_id"] is None
    assert data["referral_id"] is None

def test_patient_registration_with_case_vitals_and_urgent_referral(client):
    token = get_asha_token(client)
    client_reg_id = "REG-TEST-URGENT-002"
    payload = {
        "client_registration_id": client_reg_id,
        "full_name": "Meena Suresh Rao",
        "date_of_birth": "1998-04-12",
        "exact_dob_unknown": False,
        "sex": "FEMALE",
        "phone": "9822334455",
        "preferred_contact_method": "PHONE",
        "abha_number": "12-9988-7766-5544",
        "village_name": "Kalyanpur",
        "state": "Maharashtra",
        "district": "District 04",
        "registration_consent_obtained": True,
        "voice_consent_obtained": True,
        "consent_method": "VERBAL",
        
        # Health Concern
        "create_current_case": True,
        "chief_complaint": "Severe headache and blurred vision at 30 weeks pregnancy",
        "symptoms": ["Severe Headache", "Blurred Vision", "Swelling in feet"],
        
        # Vitals
        "vitals": {
            "measured": True,
            "systolic_bp": 155,
            "diastolic_bp": 100,
            "temperature_c": 37.2,
            "spo2": 97,
            "pulse": 88
        },
        
        # Special condition: Pregnancy
        "special_conditions": {
            "condition_type": "PREGNANCY",
            "maternal": {
                "gestational_weeks": 30,
                "severe_headache": True,
                "blurred_vision": True,
                "severe_swelling": True,
                "anc_registered": True
            }
        },
        
        # Referral
        "referral_required": True,
        "referral_urgency": "URGENT",
        "referral_facility_id": "PHC-09",
        "referral_reason": "Severe gestational hypertension with visual symptoms",
        "accuracy_confirmed_by_asha": True
    }
    
    res = client.post(
        "/api/asha/patient-registration",
        json=payload,
        headers={"Authorization": f"Bearer {token}", "Idempotency-Key": client_reg_id}
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["citizen_id"] is not None
    assert data["case_id"] is not None
    assert data["visit_id"] is not None
    assert data["referral_id"] is not None
    assert data["safety_result"] is not None
    assert data["safety_result"]["safety_rule_triggered"] is True
    assert data["safety_result"]["priority"] == "URGENT"

def test_idempotent_patient_registration_replay(client):
    token = get_asha_token(client)
    client_reg_id = "REG-TEST-IDEMPOTENT-003"
    payload = {
        "client_registration_id": client_reg_id,
        "full_name": "Anita Vikas Shinde",
        "approximate_age": 29,
        "sex": "FEMALE",
        "village_name": "Rampur",
        "state": "Maharashtra",
        "district": "District 04",
        "registration_consent_obtained": True,
        "create_current_case": False,
        "accuracy_confirmed_by_asha": True
    }
    # First request
    res1 = client.post(
        "/api/asha/patient-registration",
        json=payload,
        headers={"Authorization": f"Bearer {token}", "Idempotency-Key": client_reg_id}
    )
    assert res1.status_code == 200
    cit_id_1 = res1.json()["data"]["citizen_id"]

    # Replay with same idempotency key
    res2 = client.post(
        "/api/asha/patient-registration",
        json=payload,
        headers={"Authorization": f"Bearer {token}", "Idempotency-Key": client_reg_id}
    )
    assert res2.status_code == 200
    cit_id_2 = res2.json()["data"]["citizen_id"]
    assert cit_id_1 == cit_id_2

def test_voice_structured_patient_intake(client):
    token = get_asha_token(client)
    res = client.post(
        "/api/asha/voice/structured-patient-intake",
        json={
            "raw_transcript": "रुग्णाचे नाव सुनिता कांबळे वय तीस वर्षे. डोकेदुखी आणि चक्कर. रक्तदाब १३०/८५.",
            "language": "mr-IN",
            "consent_obtained": True
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["requires_human_confirmation"] is True
    assert data["extracted_fields"] is not None
    assert data["extracted_fields"].get("full_name") == "Sunita Kamble"
    assert data["extracted_fields"].get("approximate_age") == 30
