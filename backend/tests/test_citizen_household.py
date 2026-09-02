import pytest
from app.models import User, CitizenProfile, HouseholdMember
from app.services.citizen_service import CitizenService
from app.schemas.citizen import HouseholdMemberCreateRequest, HouseholdMemberUpdateRequest

def test_add_household_member_success(db_session):
    # 1. Create a dummy citizen user & profile
    user = User(
        identifier="citizen_9876543201",
        name="Ramesh Patil",
        phone="9876543201",
        password_hash="mockhash123",
        role="CITIZEN",
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    profile = CitizenProfile(
        user_id=user.id,
        phone=user.phone,
        display_name="Ramesh Patil",
        age_estimate=35,
        sex="Male"
    )
    db_session.add(profile)
    db_session.commit()
    db_session.refresh(profile)

    # 2. Add a household member
    req = HouseholdMemberCreateRequest(
        full_name="Pooja Patil",
        relationship_type="SPOUSE",
        age=32,
        sex="Female",
        phone="9876543202",
        blood_group="B+",
        health_notes="No major ailments",
        consent_obtained=True
    )
    new_member = CitizenService.add_household_member(db_session, profile.id, req)

    assert new_member is not None
    assert new_member["full_name"] == "Pooja Patil"
    assert new_member["relationship"] == "SPOUSE"
    assert new_member["relationship_type"] == "SPOUSE"
    assert new_member["age"] == 32
    assert new_member["sex"] == "Female"
    assert new_member["phone"] == "9876543202"
    assert new_member["blood_group"] == "B+"
    assert new_member["is_active"] is True

    # 3. Retrieve list and verify seeding of SELF + new member
    members = CitizenService.get_household_members(db_session, profile.id)
    assert len(members) == 2
    names = [m["full_name"] for m in members]
    assert "Ramesh Patil" in names
    assert "Pooja Patil" in names

def test_add_duplicate_household_member_fails(db_session):
    user = User(
        identifier="citizen_9876543203",
        name="Anil Kumar",
        phone="9876543203",
        password_hash="mockhash123",
        role="CITIZEN",
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    profile = CitizenProfile(
        user_id=user.id,
        phone=user.phone,
        display_name="Anil Kumar",
        age_estimate=40,
        sex="Male"
    )
    db_session.add(profile)
    db_session.commit()
    db_session.refresh(profile)

    req = HouseholdMemberCreateRequest(
        full_name="Aarav Kumar",
        relationship_type="CHILD",
        age=10,
        sex="Male"
    )
    CitizenService.add_household_member(db_session, profile.id, req)

    # Attempt to add duplicate
    with pytest.raises(ValueError) as excinfo:
        CitizenService.add_household_member(db_session, profile.id, req)
    assert "already exists in your household" in str(excinfo.value)

def test_add_household_member_invalid_age(db_session):
    user = User(
        identifier="citizen_9876543204",
        name="Sunita Deshmukh",
        phone="9876543204",
        password_hash="mockhash123",
        role="CITIZEN",
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    profile = CitizenProfile(
        user_id=user.id,
        phone=user.phone,
        display_name="Sunita Deshmukh"
    )
    db_session.add(profile)
    db_session.commit()
    db_session.refresh(profile)

    req = HouseholdMemberCreateRequest(
        full_name="Grandpa",
        relationship_type="ELDER",
        age=150
    )
    with pytest.raises(ValueError) as excinfo:
        CitizenService.add_household_member(db_session, profile.id, req)
    assert "Age must be between 0 and 125" in str(excinfo.value)
