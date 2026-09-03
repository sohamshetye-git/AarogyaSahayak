import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app.models import (
    User, UserRoleEnum, WorkerProfile, CitizenProfile, Case,
    CasePriorityEnum, CaseStatusEnum, Consultation, Referral,
    InvestigationOrder, FollowUp
)
from app.auth.security import create_access_token

@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

def test_doctor_investigation_list_and_timeline_journey(db):
    client = TestClient(app)

    # 1. Setup Doctor in Facility 1
    doc_user = User(
        id="doc-timeline-test-01",
        identifier="919811122201",
        phone="919811122201",
        name="Dr. Abhinav Sharma",
        password_hash="mock_hash",
        role=UserRoleEnum.PHC_DOCTOR,
        is_active=True
    )
    doc_wp = WorkerProfile(
        id="wp-timeline-test-01",
        user_id=doc_user.id,
        facility_id="FAC-PHC-01",
        worker_type="DOCTOR"
    )

    # 2. Setup Doctor in Facility 2 (Unauthorized for Facility 1 cases)
    other_doc = User(
        id="doc-timeline-other-02",
        identifier="919811122202",
        phone="919811122202",
        name="Dr. Other Facility",
        password_hash="mock_hash",
        role=UserRoleEnum.PHC_DOCTOR,
        is_active=True
    )
    other_wp = WorkerProfile(
        id="wp-timeline-other-02",
        user_id=other_doc.id,
        facility_id="FAC-PHC-02",
        worker_type="DOCTOR"
    )

    # 3. Setup Citizen: Krishna Omkar Mohite
    citizen = CitizenProfile(
        id="cit-krishna-mohite-01",
        user_id=None,
        display_name="Krishna Omkar Mohite",
        phone="919876543201",
        sex="Male",
        age_estimate=32,
        village_name="Kalyanpur"
    )

    # 4. Setup Canonical Case in Facility 1
    case = Case(
        id="case-krishna-mohite-01",
        reference="CASE-2026-8928",
        citizen_id=citizen.id,
        assigned_facility_id="FAC-PHC-01",
        assigned_facility_name="Kalyanpur PHC",
        assigned_asha_name="Sita ASHA",
        primary_concern="Fever and burning micturition",
        priority=CasePriorityEnum.ROUTINE,
        status=CaseStatusEnum.CONSULTATION_IN_PROGRESS
    )

    # 5. Setup Consultation
    cons = Consultation(
        id="cons-krishna-01",
        reference="CON-2026-8928",
        case_id=case.id,
        doctor_id=doc_user.id,
        doctor_name="Dr. Abhinav Sharma",
        facility_id="FAC-PHC-01",
        status="COMPLETED"
    )

    # 6. Setup Investigation Order: Urine Routine (LAB-20260903030225-8928)
    order = InvestigationOrder(
        id="inv-order-urine-8928",
        reference="LAB-20260903030225-8928",
        citizen_id=citizen.id,
        case_id=case.id,
        consultation_id=cons.id,
        ordered_by_doctor_id=doc_user.id,
        facility_id="FAC-PHC-01",
        test_name="Urine Routine",
        category="BIOCHEMISTRY",
        priority="ROUTINE",
        status="ORDERED"
    )

    # Add all to db
    db.merge(doc_user)
    db.merge(doc_wp)
    db.merge(other_doc)
    db.merge(other_wp)
    db.merge(citizen)
    db.merge(case)
    db.merge(cons)
    db.merge(order)
    db.commit()

    token_doc1 = create_access_token({"sub": doc_user.id, "role": doc_user.role.value, "phone": doc_user.phone})
    token_doc2 = create_access_token({"sub": other_doc.id, "role": other_doc.role.value, "phone": other_doc.phone})

    # Test 1: GET /api/doctor/investigations returns all required DTO fields
    res = client.get("/api/doctor/investigations", headers={"Authorization": f"Bearer {token_doc1}"})
    assert res.status_code == 200, f"Failed: {res.text}"
    inv_data = res.json()["data"]
    target_inv = next((i for i in inv_data if i["reference"] == "LAB-20260903030225-8928"), None)
    assert target_inv is not None, "LAB-20260903030225-8928 not found in investigations list"

    # Confirm required fields
    assert target_inv["investigation_order_id"] == "inv-order-urine-8928"
    assert target_inv["case_id"] == "case-krishna-mohite-01"
    assert target_inv["case_reference"] == "CASE-2026-8928"
    assert target_inv["citizen_id"] == "cit-krishna-mohite-01"
    assert target_inv["patient_id"] == "cit-krishna-mohite-01"
    assert target_inv["consultation_id"] == "cons-krishna-01"
    assert target_inv["test_name"] == "Urine Routine"
    assert target_inv["citizen_name"] == "Krishna Omkar Mohite"

    # Test 2: GET /api/doctor/cases/{case_id}/timeline returns 200 and loads patient and timeline events
    tl_res = client.get(f"/api/doctor/cases/{target_inv['case_id']}/timeline", headers={"Authorization": f"Bearer {token_doc1}"})
    assert tl_res.status_code == 200, f"Timeline fetch failed: {tl_res.text}"
    tl_data = tl_res.json()["data"]

    assert tl_data["case_id"] == "case-krishna-mohite-01"
    assert tl_data["citizen_name"] == "Krishna Omkar Mohite"
    
    events = tl_data["events"]
    # Check that Urine Routine investigation order is in the timeline events
    inv_events = [e for e in events if "Urine Routine" in e["title"] or "LAB-20260903030225-8928" in e["safe_description"]]
    assert len(inv_events) > 0, "Urine Routine investigation order must appear in timeline events"
    assert inv_events[0]["category"] == "INVESTIGATION"
    assert inv_events[0]["source_entity_id"] == "inv-order-urine-8928"

    # Test 3: Unauthorized doctor (Facility 2) gets 403 FORBIDDEN
    unauth_res = client.get(f"/api/doctor/cases/{target_inv['case_id']}/timeline", headers={"Authorization": f"Bearer {token_doc2}"})
    assert unauth_res.status_code == 403, f"Expected 403 for unauthorized facility, got {unauth_res.status_code}"
    assert unauth_res.json()["detail"]["code"] == "FORBIDDEN_FACILITY_ACCESS"

    # Test 4: Non-existent case returns 404
    not_found_res = client.get("/api/doctor/cases/non-existent-case-uuid/timeline", headers={"Authorization": f"Bearer {token_doc1}"})
    assert not_found_res.status_code == 404, f"Expected 404 for invalid case, got {not_found_res.status_code}"
