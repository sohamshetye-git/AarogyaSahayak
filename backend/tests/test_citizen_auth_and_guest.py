import pytest
from app.services.citizen_auth_service import (
    CitizenAuthService, normalize_indian_phone, mask_phone_number, hash_phone
)
from app.models import User, CitizenProfile, CitizenAuthIdentity, OtpChallenge, GuestSession, AuthSession
from app.config import settings

def test_indian_phone_normalization_and_masking():
    # Valid 10-digit
    assert normalize_indian_phone("9876543210") == "+919876543210"
    # With 91 prefix
    assert normalize_indian_phone("919876543210") == "+919876543210"
    # With +91 and spaces/dashes
    assert normalize_indian_phone("+91 98765-43210") == "+919876543210"
    # With 0 prefix
    assert normalize_indian_phone("09876543210") == "+919876543210"

    # Masking
    assert mask_phone_number("+919876543210") == "98******10"

    # Invalid cases
    with pytest.raises(ValueError):
        normalize_indian_phone("1234567890") # starts with 1
    with pytest.raises(ValueError):
        normalize_indian_phone("98765") # too short

def test_otp_request_and_verification_lifecycle(db_session):
    test_phone = "9876500001"
    
    # 1. Request OTP
    req_res = CitizenAuthService.request_otp(db_session, test_phone)
    assert req_res["phone_masked"] == "98******01"
    assert req_res["expires_in_seconds"] == 300
    assert "mock_code" in req_res

    # 2. Cooldown check (requesting immediately should raise ValueError)
    with pytest.raises(ValueError, match="Please wait"):
        CitizenAuthService.request_otp(db_session, test_phone)

    # 3. Invalid OTP verification attempt
    with pytest.raises(ValueError, match="Incorrect OTP"):
        CitizenAuthService.verify_otp(db_session, test_phone, "000000")

    # 4. Correct OTP verification
    verify_res = CitizenAuthService.verify_otp(db_session, test_phone, "123456")
    assert verify_res["phone_normalized"] == "+919876500001"
    assert verify_res["is_new_citizen"] is True # newly verified phone has no linked profile yet

    # 5. Verify challenge is now consumed (single-use)
    with pytest.raises(ValueError, match="No active OTP request found"):
        CitizenAuthService.verify_otp(db_session, test_phone, "123456")

def test_new_citizen_onboarding(db_session):
    test_phone = "9876500002"
    onboarding_data = {
        "full_name": "Ramesh Patil",
        "age": 35,
        "gender": "MALE",
        "village": "Kalyanpur",
        "district": "District 04",
        "pincode": "411001",
        "preferred_language": "mr-IN",
        "emergency_contact_name": "Suresh Patil",
        "emergency_contact_phone": "+919876500003",
        "consent_obtained": True
    }

    res = CitizenAuthService.register_onboarding(db_session, test_phone, onboarding_data)
    assert res["access_token"] is not None
    assert res["user"]["name"] == "Ramesh Patil"
    assert res["user"]["phone"] == "+919876500002"
    assert len(res["authorized_beneficiaries"]) == 1
    assert "Myself" in res["authorized_beneficiaries"][0]["displayName"]

    # Verify existing citizen OTP verify directly returns tokens
    # Invalidate cooldown by updating DB challenge timestamp
    p_hash = hash_phone("+919876500002")
    db_session.query(OtpChallenge).filter(OtpChallenge.phone_hash == p_hash).delete()
    db_session.commit()

    CitizenAuthService.request_otp(db_session, test_phone)
    verify_res = CitizenAuthService.verify_otp(db_session, test_phone, "123456")
    assert verify_res["is_new_citizen"] is False
    assert verify_res["user"]["name"] == "Ramesh Patil"
    assert verify_res["access_token"] is not None

def test_guest_session_and_atomic_migration(db_session):
    # 1. Create Guest Session
    guest_res = CitizenAuthService.create_guest_session(db_session, locale="hi-IN")
    session_id = guest_res["session_id"]
    assert session_id.startswith("gst_")
    assert guest_res["locale"] == "hi-IN"

    # 2. Update Guest context
    CitizenAuthService.update_guest_session_context(
        db_session,
        session_id=session_id,
        context_updates={"chief_concern": "Fever for 2 days", "symptoms": ["FEVER", "HEADACHE"]},
        intended_action={"type": "SPEAK_TO_DOCTOR", "channel": "CALLBACK"}
    )

    # 3. Create a user to migrate to
    test_phone = "9876500004"
    onb = CitizenAuthService.register_onboarding(db_session, test_phone, {
        "full_name": "Pooja Sharma",
        "age": 28,
        "gender": "FEMALE",
        "village": "Kalyanpur",
        "consent_obtained": True
    })
    user_id = onb["user"]["id"]

    # 4. Migrate Guest Session
    mig_res = CitizenAuthService.migrate_guest_to_citizen(
        db_session,
        guest_session_id=session_id,
        user_id=user_id,
        idempotency_key=f"mig_test_{session_id}"
    )
    assert mig_res["status"] == "COMPLETED"
    assert mig_res["intended_action"]["type"] == "SPEAK_TO_DOCTOR"

    # 5. Test Idempotency
    mig_res_repeat = CitizenAuthService.migrate_guest_to_citizen(
        db_session,
        guest_session_id=session_id,
        user_id=user_id,
        idempotency_key=f"mig_test_{session_id}"
    )
    assert mig_res_repeat["migration_id"] == mig_res["migration_id"]

def test_token_refresh_and_logout(db_session):
    test_phone = "9876500005"
    onb = CitizenAuthService.register_onboarding(db_session, test_phone, {
        "full_name": "Anita Deshmukh",
        "age": 40,
        "gender": "FEMALE",
        "village": "Kalyanpur",
        "consent_obtained": True
    })
    refresh_token = onb["refresh_token"]
    user_id = onb["user"]["id"]

    # Refresh
    ref_res = CitizenAuthService.refresh_token_session(db_session, refresh_token)
    assert ref_res["access_token"] is not None
    assert ref_res["refresh_token"] != refresh_token # Rotated
    assert ref_res["user"]["name"] == "Anita Deshmukh"

    # Old refresh token now invalid
    with pytest.raises(ValueError, match="Session revoked or not found"):
        CitizenAuthService.refresh_token_session(db_session, refresh_token)

    # Logout
    CitizenAuthService.logout_session(db_session, user_id=user_id)
    # New refresh token also revoked
    with pytest.raises(ValueError, match="Session revoked or not found"):
        CitizenAuthService.refresh_token_session(db_session, ref_res["refresh_token"])

def test_citizen_http_cookie_auth_flow(client):
    test_phone = "9876500099"

    # 1. Onboarding via HTTP
    onb_res = client.post("/api/citizen/onboarding", json={
        "phone": test_phone,
        "full_name": "Shiv Ramesh Kumar",
        "age": 32,
        "gender": "MALE",
        "village": "Kalyanpur",
        "consent_obtained": True
    })
    assert onb_res.status_code == 200
    assert "aarogya_citizen_refresh" in client.cookies
    data = onb_res.json()["data"]
    access_token = data["access_token"]
    assert data["user"]["name"] == "Shiv Ramesh Kumar"

    # 2. Get /auth/me with Bearer token
    me_res = client.get("/api/citizen/auth/me", headers={"Authorization": f"Bearer {access_token}"})
    assert me_res.status_code == 200
    me_data = me_res.json()["data"]
    assert me_data["user"]["name"] == "Shiv Ramesh Kumar"
    assert len(me_data["authorized_beneficiaries"]) >= 1

    # 3. Get /home-summary with Bearer token -> should match authenticated user name
    home_res = client.get("/api/citizen/home-summary", headers={"Authorization": f"Bearer {access_token}"})
    assert home_res.status_code == 200
    home_data = home_res.json()["data"]
    assert home_data["citizen_name"] == "Shiv Ramesh Kumar"

    # 4. Refresh token via Cookie (without sending body)
    ref_res = client.post("/api/citizen/auth/refresh", json={})
    assert ref_res.status_code == 200
    ref_data = ref_res.json()["data"]
    new_access_token = ref_data["access_token"]
    assert new_access_token is not None
    assert "aarogya_citizen_refresh" in client.cookies

    # 5. Access with new token
    me_res2 = client.get("/api/citizen/auth/me", headers={"Authorization": f"Bearer {new_access_token}"})
    assert me_res2.status_code == 200
    assert me_res2.json()["data"]["user"]["name"] == "Shiv Ramesh Kumar"

    # 6. Logout -> clears cookie & revokes session
    logout_res = client.post("/api/citizen/auth/logout", headers={"Authorization": f"Bearer {new_access_token}"})
    assert logout_res.status_code == 200

    # 7. Next refresh fails with 401
    fail_ref = client.post("/api/citizen/auth/refresh", json={})
    assert fail_ref.status_code == 401
