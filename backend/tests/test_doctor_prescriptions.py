import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.database import get_db, SessionLocal
from app.models import (
    User, UserRoleEnum, CitizenProfile, Case, Consultation, Prescription,
    PrescriptionItem, MedicineCatalog, PrescriptionSafetyCheck, PrescriptionAmendment,
    PrescriptionAcknowledgement, FollowUp, AuditLog
)
from app.auth.security import create_access_token

client = TestClient(app)


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def doctor_headers(db_session: Session):
    doc = db_session.query(User).filter(User.role == UserRoleEnum.PHC_DOCTOR).first()
    if not doc:
        doc = User(
            id="DOC-TEST-999",
            identifier="test.doctor",
            name="Dr. Test Doctor",
            role=UserRoleEnum.PHC_DOCTOR,
            preferred_language="en-IN"
        )
        db_session.add(doc)
        db_session.commit()
    
    token = create_access_token({"sub": doc.id, "type": "access"})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def citizen_headers(db_session: Session):
    cit = db_session.query(User).filter(User.role == UserRoleEnum.CITIZEN).first()
    if not cit:
        cit = User(
            id="CIT-TEST-999",
            identifier="test.citizen",
            name="Test Citizen",
            role=UserRoleEnum.CITIZEN,
            preferred_language="en-IN"
        )
        db_session.add(cit)
        db_session.commit()
    
    token = create_access_token({"sub": cit.id, "type": "access"})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def asha_headers(db_session: Session):
    asha = db_session.query(User).filter(User.role == UserRoleEnum.ASHA_WORKER).first()
    if not asha:
        asha = User(
            id="ASHA-TEST-999",
            identifier="test.asha",
            name="Test ASHA",
            role=UserRoleEnum.ASHA_WORKER,
            preferred_language="en-IN"
        )
        db_session.add(asha)
        db_session.commit()

    token = create_access_token({"sub": asha.id, "type": "access"})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_headers(db_session: Session):
    adm = db_session.query(User).filter(User.role == UserRoleEnum.DISTRICT_ADMIN).first()
    if not adm:
        adm = User(
            id="ADM-TEST-999",
            identifier="test.admin",
            name="Test Admin",
            role=UserRoleEnum.DISTRICT_ADMIN,
            preferred_language="en-IN"
        )
        db_session.add(adm)
        db_session.commit()

    token = create_access_token({"sub": adm.id, "type": "access"})
    return {"Authorization": f"Bearer {token}"}


def test_doctor_prescription_summary(doctor_headers):
    response = client.get("/api/doctor/prescriptions/summary", headers=doctor_headers)
    assert response.status_code == 200
    data = response.json()["data"]
    assert "drafts_count" in data
    assert "active_count" in data
    assert "signed_today_count" in data
    assert data["phc_name"] == "Kalyanpur Primary Health Centre"


def test_doctor_create_and_update_draft(doctor_headers, db_session):
    citizen = db_session.query(CitizenProfile).first()
    case = db_session.query(Case).first()
    cons = db_session.query(Consultation).first()

    payload = {
        "citizen_id": citizen.id,
        "case_id": case.id,
        "consultation_id": cons.id,
        "patient_language": "mr-IN",
        "clinical_context": "Test draft creation for acute fever.",
        "items": [
            {
                "generic_name_snapshot": "Paracetamol",
                "brand_name_snapshot": "Calpol",
                "formulation": "Tablet",
                "strength": "500 mg",
                "dose": "1",
                "dose_unit": "tablet",
                "route": "Oral",
                "frequency": "Twice daily",
                "duration_value": 5,
                "duration_unit": "days",
                "quantity": 10,
                "instructions": "After meals"
            }
        ]
    }
    create_res = client.post("/api/doctor/prescriptions/draft", json=payload, headers=doctor_headers)
    assert create_res.status_code == 200
    draft_data = create_res.json()["data"]
    rx_id = draft_data["id"]
    assert draft_data["status"] == "DRAFT"

    # Update draft
    update_payload = {
        "clinical_context": "Updated clinical context for draft.",
        "items": [
            {
                "generic_name_snapshot": "Amoxicillin",
                "brand_name_snapshot": "Mox 500",
                "formulation": "Tablet",
                "strength": "500 mg",
                "dose": "1",
                "dose_unit": "tablet",
                "route": "Oral",
                "frequency": "Three times daily",
                "duration_value": 7,
                "duration_unit": "days",
                "quantity": 21,
                "instructions": "Take with water"
            }
        ]
    }
    update_res = client.put(f"/api/doctor/prescriptions/{rx_id}/draft", json=update_payload, headers=doctor_headers)
    assert update_res.status_code == 200
    updated_data = update_res.json()["data"]
    assert updated_data["clinical_context"] == "Updated clinical context for draft."
    assert len(updated_data["items"]) == 1
    assert updated_data["items"][0]["generic_name_snapshot"] == "Amoxicillin"


def test_deterministic_safety_checks_and_signing(doctor_headers, db_session):
    rx = db_session.query(Prescription).filter(Prescription.status == "READY_FOR_REVIEW").first()
    if not rx:
        rx = db_session.query(Prescription).filter(Prescription.status == "DRAFT").first()

    validate_res = client.post(f"/api/doctor/prescriptions/{rx.id}/validate", headers=doctor_headers)
    assert validate_res.status_code == 200
    checks = validate_res.json()["data"]["checks"]
    assert isinstance(checks, list)

    sign_res = client.post(
        f"/api/doctor/prescriptions/{rx.id}/sign",
        json={"confirmed_warnings": [], "instructions_reviewed": True},
        headers={**doctor_headers, "Idempotency-Key": "IDEMPOTENT-KEY-TEST-001"}
    )
    assert sign_res.status_code == 200
    signed_data = sign_res.json()["data"]
    assert signed_data["status"] == "SIGNED"
    assert signed_data["signed_at"] is not None

    # Repeated signing returns existing signed record
    repeat_res = client.post(
        f"/api/doctor/prescriptions/{rx.id}/sign",
        json={"confirmed_warnings": [], "instructions_reviewed": True},
        headers={**doctor_headers, "Idempotency-Key": "IDEMPOTENT-KEY-TEST-001"}
    )
    assert repeat_res.status_code == 200
    assert repeat_res.json()["data"]["status"] in ["SIGNED", "ACTIVE"]


def test_immutable_signed_prescription_modification_conflict(doctor_headers, db_session):
    signed_rx = db_session.query(Prescription).filter(Prescription.status == "SIGNED").first()
    if signed_rx:
        update_res = client.put(
            f"/api/doctor/prescriptions/{signed_rx.id}/draft",
            json={"clinical_context": "Attempted edit on signed prescription"},
            headers=doctor_headers
        )
        assert update_res.status_code == 409


def test_prescription_amendment_workflow(doctor_headers, db_session):
    signed_rx = db_session.query(Prescription).filter(Prescription.status.in_(["SIGNED", "ACTIVE"])).first()
    amend_payload = {
        "reason_code": "DOSE_ADJUSTED",
        "reason_note": "Increasing dose due to persistent symptoms",
        "items": [
            {
                "generic_name_snapshot": "Amoxicillin",
                "formulation": "Tablet",
                "strength": "500 mg",
                "dose": "2",
                "dose_unit": "tablet",
                "route": "Oral",
                "frequency": "Twice daily",
                "duration_value": 7,
                "duration_unit": "days",
                "quantity": 28,
                "instructions": "Take twice daily"
            }
        ]
    }
    res = client.post(f"/api/doctor/prescriptions/{signed_rx.id}/amend", json=amend_payload, headers=doctor_headers)
    assert res.status_code == 200
    new_rx_data = res.json()["data"]
    assert new_rx_data["version_number"] == signed_rx.version_number + 1
    assert new_rx_data["supersedes_prescription_id"] == signed_rx.id

    # Verify original is marked AMENDED
    db_session.refresh(signed_rx)
    assert signed_rx.status == "AMENDED"


def test_stop_medicine_workflow(doctor_headers, db_session):
    rx = db_session.query(Prescription).filter(Prescription.status.in_(["SIGNED", "ACTIVE"])).first()
    if rx and rx.items:
        item = rx.items[0]
        stop_payload = {
            "stop_reason": "ALLERGY_CONCERN",
            "doctor_note": "Patient reported skin rash",
            "patient_guidance": "Discontinue medicine immediately",
            "asha_notification_required": True
        }
        res = client.post(f"/api/doctor/prescriptions/{rx.id}/items/{item.id}/stop", json=stop_payload, headers=doctor_headers)
        assert res.status_code == 200
        updated_data = res.json()["data"]
        assert updated_data["status"] in ["STOPPED", "PARTIALLY_STOPPED"]


def test_citizen_signed_only_visibility_and_acknowledgement(citizen_headers, db_session):
    res = client.get("/api/citizen/prescriptions", headers=citizen_headers)
    assert res.status_code == 200
    rxs = res.json()["data"]
    assert isinstance(rxs, list)
    for r in rxs:
        assert r["status"] in ["SIGNED", "ACTIVE", "COMPLETED", "AMENDED", "PARTIALLY_STOPPED", "STOPPED"]

    if rxs:
        rx_id = rxs[0]["id"]
        ack_res = client.post(
            f"/api/citizen/prescriptions/{rx_id}/acknowledge",
            json={"instructions_understood": True, "language": "mr-IN"},
            headers=citizen_headers
        )
        assert ack_res.status_code == 200
        assert ack_res.json()["data"]["acknowledged"] is True


def test_asha_adherence_followup_workflow(asha_headers, db_session):
    res = client.get("/api/asha/adherence-followups", headers=asha_headers)
    assert res.status_code == 200
    fus = res.json()["data"]
    assert isinstance(fus, list)

    if fus:
        fu_id = fus[0]["id"]
        outcome_payload = {
            "patient_contacted": True,
            "medicine_obtained": True,
            "adherence_status": "YES",
            "missed_doses": 0,
            "guidance_delivered": "Confirmed daily dosage schedule with patient",
            "notes": "Patient taking medicines regularly after breakfast and dinner."
        }
        outcome_res = client.post(f"/api/asha/adherence-followups/{fu_id}/outcome", json=outcome_payload, headers=asha_headers)
        assert outcome_res.status_code == 200
        assert outcome_res.json()["data"]["status"] == "COMPLETED"


def test_admin_prescriptions_analytics_privacy(admin_headers):
    res = client.get("/api/admin/analytics/prescriptions", headers=admin_headers)
    assert res.status_code == 200
    data = res.json()["data"]

    # Verify anonymized aggregates
    assert "prescriptions_signed_total" in data
    assert "active_prescriptions_count" in data
    assert "amendment_rate_percentage" in data
    assert "adherence_followup_completion_rate" in data

    # Verify zero PII returned
    serialized = str(data).lower()
    assert "sunita" not in serialized
    assert "ramesh" not in serialized
    assert "phone" not in serialized
    assert "abha" not in serialized
