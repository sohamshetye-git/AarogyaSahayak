import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import User, CitizenProfile, HouseholdMember, CitizenAuthIdentity
from app.services.citizen_auth_service import CitizenAuthService, hash_phone


# PostgreSQL test URL (uses running local postgres container)
PG_TEST_DB_URL = os.getenv("PG_TEST_DATABASE_URL", "postgresql+psycopg2://aarogya:aarogya_secure_pass@localhost:5432/test_schema_check")

@pytest.fixture(scope="module")
def pg_session():
    engine = create_engine(PG_TEST_DB_URL)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = Session()
    try:
        yield db
    finally:
        db.close()

def test_postgresql_citizen_registration_workflow(pg_session, monkeypatch):
    """
    Integration test verifying:
    Citizen OTP authentication -> new citizen registration -> citizen profile creation -> self household-member lookup -> idempotency on retry.
    Executed directly against migrated PostgreSQL schema.
    """
    monkeypatch.setattr(settings, "ENVIRONMENT", "staging")
    monkeypatch.setattr(settings, "OTP_MODE", "MOCK")
    monkeypatch.setattr(settings, "DEMO_OTP_CODE", "123456")

    test_phone = "9820088771"

    # Clean previous run artifact if any
    old_users = pg_session.query(User).filter(User.phone == f"+91{test_phone}").all()
    for u in old_users:
        if u.citizen_profile:
            pg_session.query(HouseholdMember).filter(HouseholdMember.citizen_id == u.citizen_profile.id).delete()
            pg_session.delete(u.citizen_profile)
        pg_session.query(CitizenAuthIdentity).filter(CitizenAuthIdentity.user_id == u.id).delete()
        pg_session.delete(u)
    
    p_hash = hash_phone(f"+91{test_phone}")
    from app.models import OtpChallenge
    pg_session.query(OtpChallenge).filter(OtpChallenge.phone_hash == p_hash).delete()
    pg_session.commit()


    # 1. Request OTP
    otp_req = CitizenAuthService.request_otp(pg_session, test_phone)
    assert otp_req["provider"] == "MOCK"
    assert "challenge_id" in otp_req


    # 2. Verify OTP with 123456
    otp_verify = CitizenAuthService.verify_otp(pg_session, test_phone, "123456")
    assert otp_verify["onboarding_required"] is True
    assert otp_verify["is_new_citizen"] is True

    # 3. Submit Onboarding / Registration
    reg_data = {
        "full_name": "Rukmini Shinde",
        "village": "Kalyanpur",
        "district": "District 04",
        "age": 29,
        "gender": "Female",
        "preferred_language": "mr-IN",
        "consent_obtained": True
    }
    onboarding_res = CitizenAuthService.register_onboarding(
        db=pg_session,
        phone_raw=test_phone,
        registration_data=reg_data,
        idempotency_key="pg-test-idem-001"
    )
    assert onboarding_res["authenticated"] is True
    assert onboarding_res["access_token"] is not None
    assert onboarding_res["user"]["name"] == "Rukmini Shinde"
    assert len(onboarding_res["authorized_beneficiaries"]) >= 1

    # 4. Verify Citizen Profile in PostgreSQL
    profile = pg_session.query(CitizenProfile).filter(CitizenProfile.phone == f"+91{test_phone}").first()
    assert profile is not None
    assert profile.display_name == "Rukmini Shinde"

    # 5. Query Household Members & Beneficiaries with is_active filter (no SQL error)
    beneficiaries = CitizenAuthService.get_authorized_beneficiaries(pg_session, profile.user_id)
    assert len(beneficiaries) >= 1
    assert beneficiaries[0]["relationship"] == "SELF"
    assert beneficiaries[0]["is_active"] is True

    # 6. Idempotency verification: Retrying onboarding does not duplicate users or throw errors
    retry_res = CitizenAuthService.register_onboarding(
        db=pg_session,
        phone_raw=test_phone,
        registration_data=reg_data,
        idempotency_key="pg-test-idem-001"
    )
    assert retry_res["authenticated"] is True
    assert retry_res["user"]["id"] == profile.user_id

    # Confirm count of users is exactly 1 for this phone
    count = pg_session.query(User).filter(User.phone == f"+91{test_phone}").count()
    assert count == 1
