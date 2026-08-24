from fastapi.testclient import TestClient
from app.models import CaseStatusEnum, CasePriorityEnum, UserRoleEnum

def test_role_protection_citizen_cannot_access_staff_endpoints(client: TestClient):
    # Login as Citizen (sunita.devi)
    login_res = client.post("/api/auth/login", json={"identifier": "sunita.devi", "password": "demo123"})
    assert login_res.status_code == 200
    token = login_res.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Try to access ASHA dashboard (should be 403 Forbidden)
    res = client.get("/api/asha/dashboard", headers=headers)
    assert res.status_code == 403
    assert res.json()["detail"]["code"] == "PERMISSION_DENIED"

    # Try to access Doctor dashboard (should be 403 Forbidden)
    res = client.get("/api/doctor/dashboard", headers=headers)
    assert res.status_code == 403

    # Try to access Admin dashboard (should be 403 Forbidden)
    res = client.get("/api/admin/dashboard", headers=headers)
    assert res.status_code == 403

def test_invalid_case_transition_fails(client: TestClient):
    # Step 1: Create a citizen case (defaults to status = NEW)
    create_res = client.post(
        "/api/citizen/cases",
        json={
            "preferred_language": "mr-IN",
            "spoken_transcript": "Severe pregnancy symptoms",
            "symptoms": ["blurred vision", "severe headache"],
            "is_pregnant": True,
            "gestational_weeks": 28,
            "vitals": {"systolic_bp": 150, "diastolic_bp": 100}
        }
    )
    assert create_res.status_code == 200
    case_id = create_res.json()["data"]["case_id"]

    # Step 2: Login as Doctor
    doc_login = client.post("/api/auth/login", json={"identifier": "dr.sharma", "password": "demo123"})
    doc_token = doc_login.json()["data"]["access_token"]
    doc_headers = {"Authorization": f"Bearer {doc_token}"}

    # Step 3: Try to submit consultation directly on NEW case (invalid transition: NEW -> FOLLOW_UP_REQUIRED)
    consult_res = client.post(
        "/api/doctor/consultations",
        headers=doc_headers,
        json={
            "case_id": case_id,
            "examination_notes": "Attempting invalid direct consultation.",
            "clinical_summary": "Should fail",
            "confirmed_diagnosis": "Gestational Hypertension",
            "icd10_code": "O14.9",
            "prescription_items": [],
            "investigation_orders": [],
            "care_plan_summary": "Rest",
            "asha_followup_instructions": "Check BP daily",
            "followup_due_days": 3
        }
    )
    assert consult_res.status_code == 400
    assert consult_res.json()["detail"]["code"] == "INVALID_STATE_TRANSITION"

def test_asha_acknowledgement_idempotency(client: TestClient):
    # Login as ASHA
    asha_login = client.post("/api/auth/login", json={"identifier": "sita.asha", "password": "demo123"})
    asha_token = asha_login.json()["data"]["access_token"]
    asha_headers = {"Authorization": f"Bearer {asha_token}"}

    # Create a new case
    create_res = client.post(
        "/api/citizen/cases",
        json={
            "preferred_language": "mr-IN",
            "spoken_transcript": "Mild fever concern",
            "symptoms": ["fever"],
            "is_pregnant": False
        }
    )
    case_id = create_res.json()["data"]["case_id"]

    # Acknowledge 1st time (should succeed)
    ack1 = client.post(f"/api/asha/cases/{case_id}/acknowledge", headers=asha_headers)
    assert ack1.status_code == 200
    assert ack1.json()["data"]["status"] == "ASHA_ACKNOWLEDGED"

    # Acknowledge 2nd time (should succeed and remain ASHA_ACKNOWLEDGED - idempotent)
    ack2 = client.post(f"/api/asha/cases/{case_id}/acknowledge", headers=asha_headers)
    assert ack2.status_code == 200
    assert ack2.json()["data"]["status"] == "ASHA_ACKNOWLEDGED"

def test_contact_result_updates_status(client: TestClient):
    asha_login = client.post("/api/auth/login", json={"identifier": "sita.asha", "password": "demo123"})
    asha_headers = {"Authorization": f"Bearer {asha_login.json()['data']['access_token']}"}

    create_res = client.post(
        "/api/citizen/cases",
        json={
            "preferred_language": "mr-IN",
            "spoken_transcript": "Headache",
            "symptoms": ["headache"],
            "is_pregnant": False
        }
    )
    case_id = create_res.json()["data"]["case_id"]

    # First acknowledge (NEW -> ASHA_ACKNOWLEDGED)
    client.post(f"/api/asha/cases/{case_id}/acknowledge", headers=asha_headers)

    # Submit contact result (ASHA_ACKNOWLEDGED -> CITIZEN_CONTACTED)
    res = client.post(
        f"/api/asha/cases/{case_id}/contact-result",
        headers=asha_headers,
        json={"outcome": "SPOKE_TO_CITIZEN", "next_action": "PLAN_VISIT", "notes": "Spoke to citizen and scheduled home visit"}
    )
    assert res.status_code == 200
    assert res.json()["data"]["status"] == "CITIZEN_CONTACTED"

def test_consent_and_vitals_stored_in_visit(client: TestClient):
    asha_login = client.post("/api/auth/login", json={"identifier": "sita.asha", "password": "demo123"})
    asha_headers = {"Authorization": f"Bearer {asha_login.json()['data']['access_token']}"}

    create_res = client.post(
        "/api/citizen/cases",
        json={
            "preferred_language": "mr-IN",
            "spoken_transcript": "Pregnancy follow up",
            "symptoms": ["severe headache"],
            "is_pregnant": True,
            "gestational_weeks": 28
        }
    )
    case_id = create_res.json()["data"]["case_id"]

    # Acknowledge
    client.post(f"/api/asha/cases/{case_id}/acknowledge", headers=asha_headers)

    # Submit visit with consent and vitals (ASHA_ACKNOWLEDGED -> ASHA_REVIEWED -> REFERRED_TO_PHC)
    visit_res = client.post(
        "/api/asha/visits",
        headers=asha_headers,
        json={
            "case_id": case_id,
            "consent_obtained": True,
            "symptoms": ["severe headache"],
            "vitals": {"systolic_bp": 150, "diastolic_bp": 100, "spo2": 98, "pulse": 80},
            "notes": "ASHA visited and measured vitals.",
            "next_action": "REFER_TO_PHC",
            "refer_to_facility_id": "PHC-09"
        }
    )
    assert visit_res.status_code == 200
    visit_data = visit_res.json()["data"]
    assert visit_data["case_status"] == "REFERRED_TO_PHC"
    assert visit_data["referral_id"] is not None

def test_prescription_restricted_from_citizen(client: TestClient):
    # Log in as doctor and complete a consultation
    doc_login = client.post("/api/auth/login", json={"identifier": "dr.sharma", "password": "demo123"})
    doc_headers = {"Authorization": f"Bearer {doc_login.json()['data']['access_token']}"}

    asha_login = client.post("/api/auth/login", json={"identifier": "sita.asha", "password": "demo123"})
    asha_headers = {"Authorization": f"Bearer {asha_login.json()['data']['access_token']}"}

    create_res = client.post(
        "/api/citizen/cases",
        json={
            "preferred_language": "mr-IN",
            "spoken_transcript": "Cardiac concern",
            "symptoms": ["severe chest pain"],
            "is_pregnant": False
        }
    )
    case_id = create_res.json()["data"]["case_id"]

    # Acknowledge -> Visit -> Refer
    client.post(f"/api/asha/cases/{case_id}/acknowledge", headers=asha_headers)
    client.post(
        "/api/asha/visits",
        headers=asha_headers,
        json={
            "case_id": case_id,
            "consent_obtained": True,
            "symptoms": ["severe chest pain"],
            "vitals": {"systolic_bp": 140, "diastolic_bp": 90},
            "next_action": "REFER_TO_PHC"
        }
    )

    # Doctor Acknowledge & Consult
    client.post(f"/api/doctor/referrals/{case_id}/acknowledge", headers=doc_headers)
    client.post(
        "/api/doctor/consultations",
        headers=doc_headers,
        json={
            "case_id": case_id,
            "examination_notes": "Chest pain evaluated.",
            "clinical_summary": "Angina suspected.",
            "confirmed_diagnosis": "Angina Pectoris",
            "icd10_code": "I20.9",
            "prescription_items": [{"medicine": "Aspirin", "strength": "75mg", "dose": "1 tab", "frequency": "Once daily", "duration": "30 days"}],
            "investigation_orders": [],
            "care_plan_summary": "Avoid stress."
        }
    )

    # Fetch status as Citizen (should NOT contain raw prescription items)
    cit_res = client.get(f"/api/citizen/cases/{case_id}")
    assert cit_res.status_code == 200
    assert "prescription" not in cit_res.text
    assert "Aspirin" not in cit_res.text
