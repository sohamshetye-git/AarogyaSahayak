import pytest
from app.models import CitizenProfile, HouseholdMember, ServiceRequest, CareHandoff, DoctorChatThread, TeleconsultationRequest, User
from app.services.citizen_service import CitizenService
from app.services.recent_activity_service import normalize_actor_name
from app.schemas.citizen import DoctorRequestCreateDTO

def test_get_beneficiaries_deduplication(db_session):
    # Setup test citizen profile
    profile = CitizenProfile(
        id="citizen-dedup-test-1",
        display_name="Krishna Omkar Mohite",
        phone="919876543210",
        sex="MALE",
        age_estimate=32
    )
    db_session.add(profile)
    
    # Add SELF household member representing the same profile
    self_member = HouseholdMember(
        id="hh-self-member-1",
        citizen_id=profile.id,
        full_name="Krishna Omkar Mohite",
        relationship_type="SELF",
        sex="MALE",
        age=32,
        is_active=True
    )
    # Add genuine household member
    child_member = HouseholdMember(
        id="hh-child-member-2",
        citizen_id=profile.id,
        full_name="Aarav Mohite",
        relationship_type="CHILD",
        sex="MALE",
        age=5,
        is_active=True
    )
    db_session.add(self_member)
    db_session.add(child_member)
    db_session.commit()

    # Call get_beneficiaries
    beneficiaries = CitizenService.get_beneficiaries(db_session, profile.id)

    # Verify SELF appears EXACTLY ONCE
    self_entries = [b for b in beneficiaries if b["relationship"] == "SELF"]
    assert len(self_entries) == 1, f"Expected 1 SELF entry, got {len(self_entries)}"
    assert self_entries[0]["beneficiary_id"] == profile.id
    assert self_entries[0]["display_name"] == "Krishna Omkar Mohite"

    # Verify genuine household member is present
    child_entries = [b for b in beneficiaries if b["relationship"] == "CHILD"]
    assert len(child_entries) == 1
    assert child_entries[0]["beneficiary_id"] == "hh-child-member-2"
    assert child_entries[0]["display_name"] == "Aarav Mohite"

def test_doctor_title_normalization():
    assert normalize_actor_name("Dr. Abhinav Sharma", role="PHC_DOCTOR") == "Dr. Abhinav Sharma"
    assert normalize_actor_name("Dr. Dr. Abhinav Sharma", role="PHC_DOCTOR") == "Dr. Abhinav Sharma"
    assert normalize_actor_name("Abhinav Sharma", role="PHC_DOCTOR") == "Dr. Abhinav Sharma"
    assert normalize_actor_name("Dr. Sunil Patil", role="PHC_DOCTOR") == "Dr. Sunil Patil"

def test_update_symptoms_and_care_handoff_versioning(db_session):
    # Setup test citizen and doctor request
    profile = CitizenProfile(
        id="citizen-triage-test-1",
        display_name="Sunita Shinde",
        phone="919876543211",
        sex="FEMALE",
        age_estimate=26,
        is_pregnant=True,
        gestational_weeks=28
    )
    db_session.add(profile)
    db_session.commit()

    # Create doctor request
    create_dto = DoctorRequestCreateDTO(
        beneficiary_id=profile.id,
        chief_complaint="Mild fever and body ache",
        symptoms=["Fever", "Body ache"],
        channel="CHAT"
    )
    created = CitizenService.create_doctor_request(db_session, profile.id, create_dto)
    request_id = created["id"]

    # Verify initial handoff version
    initial_handoff = db_session.query(CareHandoff).filter(
        CareHandoff.service_request_id == created["service_request_id"]
    ).order_by(CareHandoff.version.desc()).first()
    assert initial_handoff is not None
    assert initial_handoff.version == 1

    # Update symptoms with emergency symptom (e.g. chest pain / severe breathlessness)
    update_res = CitizenService.update_doctor_request_symptoms(
        db=db_session,
        citizen_id=profile.id,
        request_id=request_id,
        new_symptoms=["Severe headache", "Chest pain", "Shortness of breath"],
        notes="Symptoms started 2 hours ago"
    )

    # Verify response
    assert update_res["priority"] in ["EMERGENCY", "URGENT", "HIGH"]
    assert update_res["handoff_version"] == 2
    assert any("chest pain" in s.lower() for s in update_res["symptoms"])

    # Verify new CareHandoff record created in DB
    handoffs = db_session.query(CareHandoff).filter(
        CareHandoff.service_request_id == created["service_request_id"]
    ).order_by(CareHandoff.version.asc()).all()
    assert len(handoffs) >= 2
    latest = handoffs[-1]
    assert latest.version == 2
    assert latest.service_request_id == created["service_request_id"]
    assert latest.source == "CITIZEN_UPDATE"
