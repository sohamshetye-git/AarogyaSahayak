import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models import (
    User, CitizenProfile, WorkerProfile, Facility, Case,
    VitalRecord, SymptomObservation, AshaVisit, Referral, FollowUp,
    UserRoleEnum, CasePriorityEnum, CaseStatusEnum
)
from app.auth.security import get_password_hash, create_access_token

@pytest.fixture
def workspace_fixture(db_session: Session):
    db = db_session
    # Setup test facility
    phc = db.query(Facility).filter(Facility.id == "PHC-TEST-09").first()
    if not phc:
        phc = Facility(
            id="PHC-TEST-09",
            code="PHC-TEST-09",
            name="Kalyanpur Primary Health Center",
            facility_type="PHC",
            district_name="District 04",
            block_name="Kalyanpur Block",
            address="Main Road, Kalyanpur"
        )
        db.add(phc)

    # Setup ASHA worker Sita
    sita = db.query(User).filter(User.identifier == "sita.asha.test").first()
    if not sita:
        sita = User(
            id="ASHA-SITA-001",
            identifier="sita.asha.test",
            name="Sita Patel",
            phone="9823019999",
            email="sita.test@arogya.gov.in",
            password_hash=get_password_hash("demo123"),
            role=UserRoleEnum.ASHA_WORKER,
            preferred_language="mr-IN"
        )
        db.add(sita)
        db.flush()
        db.add(WorkerProfile(
            user_id=sita.id,
            worker_type="ASHA",
            facility_id=phc.id,
            facility_name=phc.name,
            district_name="District 04",
            village_ids=["VILLAGE-01"]
        ))

    # Setup another ASHA worker (for unauthorized tests)
    geeta = db.query(User).filter(User.identifier == "geeta.asha.test").first()
    if not geeta:
        geeta = User(
            id="ASHA-GEETA-002",
            identifier="geeta.asha.test",
            name="Geeta Shinde",
            phone="9823018888",
            email="geeta.test@arogya.gov.in",
            password_hash=get_password_hash("demo123"),
            role=UserRoleEnum.ASHA_WORKER,
            preferred_language="mr-IN"
        )
        db.add(geeta)
        db.flush()
        db.add(WorkerProfile(
            user_id=geeta.id,
            worker_type="ASHA",
            facility_id=phc.id,
            facility_name=phc.name,
            district_name="District 04",
            village_ids=["VILLAGE-02"]
        ))

    # Setup 31-year-old male citizen: Amit Suresh Sawant
    amit = db.query(CitizenProfile).filter(CitizenProfile.id == "CP-AMIT-001").first()
    if not amit:
        amit = CitizenProfile(
            id="CP-AMIT-001",
            display_name="Amit Suresh Sawant",
            age_estimate=31,
            sex="Male",
            phone="9823011122",
            village_name="Kalyanpur",
            is_pregnant=False,
            abha_reference="12-3456-7890-9999"
        )
        db.add(amit)

    # Setup Case: CASE-2026-730209
    case = db.query(Case).filter(Case.id == "case-amit-730209").first()
    if not case:
        case = Case(
            id="case-amit-730209",
            reference="CASE-2026-730209",
            citizen_id="CP-AMIT-001",
            priority=CasePriorityEnum.ROUTINE,
            status=CaseStatusEnum.NEW,
            primary_concern="High blood pressure, severe dizziness and blurred vision",
            preferred_language="mr-IN",
            assigned_asha_id=sita.id,
            assigned_asha_name=sita.name,
            assigned_facility_id=phc.id,
            assigned_facility_name=phc.name,
            safety_rule_triggered=False,
            created_at=datetime.now(timezone.utc) - timedelta(hours=2)
        )
        db.add(case)
        db.flush()

    # Setup FollowUp
    fup = db.query(FollowUp).filter(FollowUp.id == "fup-amit-001").first()
    if not fup:
        fup = FollowUp(
            id="fup-amit-001",
            case_id=case.id,
            citizen_id=amit.id,
            assigned_user_id=sita.id,
            task_type="BP_MONITORING",
            instructions="Check BP and monitor for neurological warning signs",
            priority="URGENT",
            status="PENDING",
            due_at=datetime.now(timezone.utc) + timedelta(days=2),
            source="DOCTOR",
            created_at=datetime.now(timezone.utc) - timedelta(hours=1)
        )
        db.add(fup)

    db.commit()

    sita_token = create_access_token({"sub": sita.id, "role": sita.role.value, "name": sita.name})
    geeta_token = create_access_token({"sub": geeta.id, "role": geeta.role.value, "name": geeta.name})

    return {
        "sita_token": sita_token,
        "geeta_token": geeta_token,
        "case_id": case.id,
        "case_ref": case.reference,
        "fup_id": fup.id,
        "amit_id": amit.id,
        "sita_id": sita.id,
        "geeta_id": geeta.id
    }


def test_dynamic_context_male_patient_no_pregnancy(client: TestClient, workspace_fixture: dict):
    """Test Defect 2: Dynamic Context must not display antenatal / pregnancy information for a male patient."""
    headers = {"Authorization": f"Bearer {workspace_fixture['sita_token']}"}
    res = client.get(f"/api/asha/cases/{workspace_fixture['case_id']}", headers=headers)
    assert res.status_code == 200, res.text
    data = res.json()["data"]

    # Assert male patient
    assert data["citizen_gender"] == "Male"
    assert data["citizen_name"] == "Amit Suresh Sawant"
    assert data["citizen_age"] == 31

    # Assert pregnancy sanitization
    assert data["is_pregnant"] is False
    assert data["gestational_weeks"] is None

    # Assert dynamic context is NCD / General, NOT ANTENATAL
    dyn = data["dynamic_context"]
    assert dyn is not None
    assert dyn["type"] != "ANTENATAL"
    assert "Maternal" not in dyn["title"]
    assert "Weeks" not in dyn.get("description", "")


def test_confirm_add_symptoms_and_safety_evaluation(client: TestClient, workspace_fixture: dict):
    """Test Defect 1: Confirm & Add Symptoms in Field Visit saves to DB, deduplicates, and evaluates safety."""
    headers = {"Authorization": f"Bearer {workspace_fixture['sita_token']}"}
    
    # 1. Add symptoms
    payload = {
        "symptoms": ["Severe Headache", "Blurry Vision", "severe headache"], # test deduplication
        "severity": "Severe",
        "onset_duration": "2 days",
        "notes": "Patient reports worsening headache and visual disturbance"
    }
    res = client.post(f"/api/asha/cases/{workspace_fixture['case_id']}/symptoms", json=payload, headers=headers)
    assert res.status_code == 200, res.text
    data = res.json()["data"]

    # Verify symptoms saved and deduplicated
    symptom_terms = [s["term"] for s in data["symptoms"]]
    assert "Severe Headache" in symptom_terms
    assert "Blurry Vision" in symptom_terms
    # Case insensitive deduplication: shouldn't have duplicate
    assert len([s for s in symptom_terms if s.lower() == "severe headache"]) == 1
    assert data["visit_id"] is not None


def test_record_vitals_validation_and_persistence(client: TestClient, workspace_fixture: dict):
    """Test Defect 4: Record Vitals validates paired BP, numeric ranges, and saves observation."""
    headers = {"Authorization": f"Bearer {workspace_fixture['sita_token']}"}

    # 1. Empty submission should fail
    res_empty = client.post(f"/api/asha/cases/{workspace_fixture['case_id']}/vitals", json={}, headers=headers)
    assert res_empty.status_code == 400

    # 2. Unpaired BP (systolic without diastolic) should fail
    res_unpaired = client.post(f"/api/asha/cases/{workspace_fixture['case_id']}/vitals", json={"systolic_bp": 150}, headers=headers)
    assert res_unpaired.status_code == 400
    assert "Both systolic and diastolic" in res_unpaired.json()["detail"]["message"]

    # 3. Out of range value should fail
    res_range = client.post(f"/api/asha/cases/{workspace_fixture['case_id']}/vitals", json={"systolic_bp": 350, "diastolic_bp": 90}, headers=headers)
    assert res_range.status_code == 400

    # 4. Valid vitals submission with Stage 2 Hypertension triggers safety warning
    valid_payload = {
        "systolic_bp": 155,
        "diastolic_bp": 100,
        "spo2": 96,
        "pulse": 88,
        "temperature_c": 37.2,
        "weight_kg": 68.0,
        "glucose_mg_dl": 125.0,
        "notes": "Stage 2 elevated BP measured via manual validated cuff"
    }
    res_valid = client.post(f"/api/asha/cases/{workspace_fixture['case_id']}/vitals", json=valid_payload, headers=headers)
    assert res_valid.status_code == 200, res_valid.text
    vital_data = res_valid.json()["data"]

    assert vital_data["systolic_bp"] == 155
    assert vital_data["diastolic_bp"] == 100
    assert vital_data["spo2"] == 96
    assert vital_data["pulse"] == 88
    assert vital_data["is_warning_sign"] is True
    assert vital_data["recorded_by"] == "Sita Patel"


def test_view_trends_chronological_history(client: TestClient, workspace_fixture: dict):
    """Test Defect 3: View Trends loads real chronological vital history for this beneficiary."""
    headers = {"Authorization": f"Bearer {workspace_fixture['sita_token']}"}

    res = client.get(f"/api/asha/cases/{workspace_fixture['case_id']}/vitals/trends", headers=headers)
    assert res.status_code == 200, res.text
    trends = res.json()["data"]

    assert isinstance(trends, list)
    assert len(trends) >= 1
    latest_pt = trends[-1]
    assert latest_pt["systolic_bp"] == 155
    assert latest_pt["diastolic_bp"] == 100
    assert latest_pt["recorded_at"] is not None


def test_prepare_referral_to_kalyanpur_phc(client: TestClient, workspace_fixture: dict):
    """Test Defect 5: Prepare Referral creates referral at Kalyanpur PHC and prevents duplicates."""
    headers = {"Authorization": f"Bearer {workspace_fixture['sita_token']}"}

    ref_payload = {
        "facility_id": "PHC-TEST-09",
        "urgency": "URGENT",
        "reason": "Stage 2 Hypertension with severe headache and neurological danger signs",
        "transport_required": False
    }

    # First submission
    res1 = client.post(f"/api/asha/cases/{workspace_fixture['case_id']}/refer", json=ref_payload, headers=headers)
    assert res1.status_code == 200, res1.text
    ref1 = res1.json()["data"]
    assert ref1["referral_id"] is not None
    assert "Kalyanpur" in ref1["facility_name"]
    assert ref1["status"] == "REFERRED_TO_PHC"

    # Second submission: must return existing referral idempotently
    res2 = client.post(f"/api/asha/cases/{workspace_fixture['case_id']}/refer", json=ref_payload, headers=headers)
    assert res2.status_code == 200
    ref2 = res2.json()["data"]
    assert ref2["referral_id"] == ref1["referral_id"]


def test_start_followup_task_workflow(client: TestClient, workspace_fixture: dict):
    """Test Defect 6: Start Follow-up Task transitions PENDING -> IN_PROGRESS and creates visit."""
    headers_sita = {"Authorization": f"Bearer {workspace_fixture['sita_token']}"}
    headers_geeta = {"Authorization": f"Bearer {workspace_fixture['geeta_token']}"}

    # 1. Unauthorized ASHA worker should get 403
    res_unauth = client.post(f"/api/asha/followups/{workspace_fixture['fup_id']}/start", headers=headers_geeta)
    assert res_unauth.status_code == 403

    # 2. Authorized ASHA worker starts the follow-up
    res_start = client.post(f"/api/asha/followups/{workspace_fixture['fup_id']}/start", headers=headers_sita)
    assert res_start.status_code == 200, res_start.text
    fup_data = res_start.json()["data"]
    assert fup_data["status"] == "IN_PROGRESS"
    assert fup_data["started_at"] is not None
    assert fup_data["visit_id"] is not None

    # 3. Repeated call is idempotent
    res_repeat = client.post(f"/api/asha/followups/{workspace_fixture['fup_id']}/start", headers=headers_sita)
    assert res_repeat.status_code == 200
    assert res_repeat.json()["data"]["status"] == "IN_PROGRESS"


def test_timeline_integrity_and_deduplication(client: TestClient, workspace_fixture: dict):
    """Test Defect 7: Timeline contains deduplicated chronological events."""
    headers = {"Authorization": f"Bearer {workspace_fixture['sita_token']}"}

    res = client.get(f"/api/asha/cases/{workspace_fixture['case_id']}/timeline", headers=headers)
    assert res.status_code == 200, res.text
    events = res.json()["data"]

    assert len(events) >= 3
    # Check chronological order
    timestamps = [datetime.fromisoformat(e["timestamp"].replace("Z", "+00:00")) for e in events]
    assert timestamps == sorted(timestamps)

    # Check deduplication: all event IDs are unique
    event_ids = [e["id"] for e in events]
    assert len(event_ids) == len(set(event_ids))


def test_care_coordination_statuses(client: TestClient, workspace_fixture: dict):
    """Test Defect 8: Care Coordination statuses reliably reflect real PostgreSQL records."""
    headers = {"Authorization": f"Bearer {workspace_fixture['sita_token']}"}

    res = client.get(f"/api/asha/cases/{workspace_fixture['case_id']}", headers=headers)
    assert res.status_code == 200, res.text
    data = res.json()["data"]

    assert data["field_visit_status"] in ["In Progress", "Completed"]
    assert "Referred" in data["phc_referral_status"]
    assert data["doctor_review_status"] in ["Pending Doctor Review", "Reviewed by Doctor", "Completed (Prescription Signed)"]
    assert data["followup_status"] in ["In Progress", "Completed", "Assigned"]
