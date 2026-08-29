import pytest
import concurrent.futures
from datetime import datetime, timezone, timedelta
from app.services.citizen_auth_service import (
    CitizenAuthService, normalize_indian_phone, mask_phone_number, hash_phone
)
from app.services.diagnostic_service import IdentityDiagnosticService
from app.models import (
    User, CitizenProfile, CitizenAuthIdentity, OtpChallenge,
    AuthSession, Case, ServiceRequest, Prescription, FollowUp, HouseholdMember,
    generate_uuid, utc_now
)
from app.database import SessionLocal

def test_1_first_verified_login_creates_one_identity_account_profile(db_session):
    phone = "9820000001"
    norm_phone = normalize_indian_phone(phone)
    p_hash = hash_phone(norm_phone)

    # Initial state: 0 records
    assert db_session.query(CitizenAuthIdentity).filter(CitizenAuthIdentity.phone_hash == p_hash).count() == 0
    assert db_session.query(User).filter(User.phone == norm_phone).count() == 0

    # Request OTP & Verify
    CitizenAuthService.request_otp(db_session, phone)
    verify_res = CitizenAuthService.verify_otp(db_session, phone, "123456")
    assert verify_res["onboarding_required"] is True
    assert verify_res["is_new_citizen"] is True

    # Complete Onboarding
    onb_res = CitizenAuthService.register_onboarding(db_session, phone, {
        "full_name": "Kavita Shinde",
        "age": 30,
        "gender": "FEMALE",
        "village": "Kalyanpur",
        "preferred_language": "mr-IN",
        "consent_obtained": True
    })

    assert onb_res["authenticated"] is True
    assert onb_res["onboarding_required"] is False
    assert onb_res["user"]["name"] == "Kavita Shinde"

    # Exactly 1 User, 1 CitizenProfile, 1 CitizenAuthIdentity
    assert db_session.query(User).filter(User.phone == norm_phone).count() == 1
    assert db_session.query(CitizenProfile).filter(CitizenProfile.phone == norm_phone).count() == 1
    assert db_session.query(CitizenAuthIdentity).filter(CitizenAuthIdentity.phone_hash == p_hash).count() == 1

def test_2_second_otp_login_creates_zero_new_users_or_profiles(db_session):
    phone = "9820000002"
    norm_phone = normalize_indian_phone(phone)
    p_hash = hash_phone(norm_phone)

    # First login & onboarding
    CitizenAuthService.request_otp(db_session, phone)
    CitizenAuthService.verify_otp(db_session, phone, "123456")
    onb_res = CitizenAuthService.register_onboarding(db_session, phone, {
        "full_name": "Sanjay Gaikwad",
        "age": 42,
        "gender": "MALE",
        "village": "Kalyanpur",
        "consent_obtained": True
    })
    initial_profile_id = onb_res["citizen_profile"]["id"]
    initial_user_id = onb_res["user"]["id"]

    users_before = db_session.query(User).count()
    profiles_before = db_session.query(CitizenProfile).count()
    sessions_before = db_session.query(AuthSession).filter(AuthSession.user_id == initial_user_id).count()

    # Clear OTP challenge cooldown for second login
    db_session.query(OtpChallenge).filter(OtpChallenge.phone_hash == p_hash).delete()
    db_session.commit()

    # Second Login with same phone and new OTP
    CitizenAuthService.request_otp(db_session, phone)
    login2_res = CitizenAuthService.verify_otp(db_session, phone, "123456")

    users_after = db_session.query(User).count()
    profiles_after = db_session.query(CitizenProfile).count()
    sessions_after = db_session.query(AuthSession).filter(AuthSession.user_id == initial_user_id).count()

    # Exact Assertion Requirements
    assert users_after - users_before == 0, "Users created on second login must be 0"
    assert profiles_after - profiles_before == 0, "Citizen profiles created on second login must be 0"
    assert sessions_after - sessions_before == 1, "Auth sessions created on second login must be 1"
    assert login2_res["onboarding_required"] is False
    assert login2_res["authenticated"] is True
    assert login2_res["user"]["id"] == initial_user_id
    assert login2_res["citizen_profile"]["id"] == initial_profile_id

def test_3_and_4_explicit_logout_and_restore_profile(db_session):
    phone = "9820000003"
    p_hash = hash_phone(normalize_indian_phone(phone))

    CitizenAuthService.request_otp(db_session, phone)
    CitizenAuthService.verify_otp(db_session, phone, "123456")
    onb = CitizenAuthService.register_onboarding(db_session, phone, {
        "full_name": "Meena Waghmare",
        "age": 27,
        "gender": "FEMALE",
        "consent_obtained": True
    })
    user_id = onb["user"]["id"]
    profile_id = onb["citizen_profile"]["id"]
    refresh_token = onb["refresh_token"]

    # Explicit logout revokes session
    CitizenAuthService.logout_session(db_session, user_id=user_id, refresh_token=refresh_token)

    # Refreshing with revoked token fails
    with pytest.raises(ValueError, match="Session revoked or not found"):
        CitizenAuthService.refresh_token_session(db_session, refresh_token)

    # User and Profile remain completely intact
    user_in_db = db_session.query(User).filter(User.id == user_id).first()
    assert user_in_db is not None
    assert user_in_db.citizen_profile.id == profile_id

    # Second login restores the exact same profile ID
    db_session.query(OtpChallenge).filter(OtpChallenge.phone_hash == p_hash).delete()
    db_session.commit()

    CitizenAuthService.request_otp(db_session, phone)
    res2 = CitizenAuthService.verify_otp(db_session, phone, "123456")
    assert res2["user"]["id"] == user_id
    assert res2["citizen_profile"]["id"] == profile_id

def test_5_existing_care_records_and_cases_remain_visible(db_session):
    phone = "9820000004"
    p_hash = hash_phone(normalize_indian_phone(phone))

    CitizenAuthService.request_otp(db_session, phone)
    CitizenAuthService.verify_otp(db_session, phone, "123456")
    onb = CitizenAuthService.register_onboarding(db_session, phone, {
        "full_name": "Vikas Shinde",
        "age": 48,
        "gender": "MALE",
        "consent_obtained": True
    })
    user_id = onb["user"]["id"]
    profile_id = onb["citizen_profile"]["id"]

    # Seed clinical records for this citizen
    case = Case(
        id="case-test-restore-001",
        reference="CAS-TEST-001",
        citizen_id=profile_id,
        primary_concern="Hypertension checkup"
    )
    req = ServiceRequest(
        id="req-test-restore-001",
        request_reference="REQ-TEST-001",
        citizen_id=profile_id,
        request_type="DOCTOR_CONSULTATION",
        priority="ROUTINE",
        status="SUBMITTED"
    )
    fu = FollowUp(
        id="fu-test-restore-001",
        citizen_id=profile_id,
        instructions="Check BP in 3 days",
        task_type="BP_MONITORING",
        reason="Follow up on blood pressure reading",
        due_at=datetime.now(timezone.utc) + timedelta(days=3)
    )
    db_session.add_all([case, req, fu])
    db_session.commit()

    # Logout
    CitizenAuthService.logout_session(db_session, user_id=user_id)

    # Login later with same number and new OTP
    db_session.query(OtpChallenge).filter(OtpChallenge.phone_hash == p_hash).delete()
    db_session.commit()

    CitizenAuthService.request_otp(db_session, phone)
    login_res = CitizenAuthService.verify_otp(db_session, phone, "123456")
    restored_profile_id = login_res["citizen_profile"]["id"]

    # Query clinical data through foreign keys
    cases = db_session.query(Case).filter(Case.citizen_id == restored_profile_id).all()
    requests = db_session.query(ServiceRequest).filter(ServiceRequest.citizen_id == restored_profile_id).all()
    followups = db_session.query(FollowUp).filter(FollowUp.citizen_id == restored_profile_id).all()

    assert len(cases) == 1
    assert cases[0].primary_concern == "Hypertension checkup"
    assert len(requests) == 1
    assert len(followups) == 1

def test_6_refresh_with_valid_session_does_not_request_otp(db_session):
    phone = "9820000005"
    CitizenAuthService.request_otp(db_session, phone)
    CitizenAuthService.verify_otp(db_session, phone, "123456")
    onb = CitizenAuthService.register_onboarding(db_session, phone, {
        "full_name": "Priyanka Joshi",
        "consent_obtained": True
    })
    refresh_tok = onb["refresh_token"]

    ref_res = CitizenAuthService.refresh_token_session(db_session, refresh_tok)
    assert ref_res["access_token"] is not None
    assert ref_res["user"]["name"] == "Priyanka Joshi"

def test_7_concurrent_otp_verification_does_not_create_duplicates(db_session):
    phone = "9820000006"
    norm_phone = normalize_indian_phone(phone)
    p_hash = hash_phone(norm_phone)

    CitizenAuthService.request_otp(db_session, phone)
    CitizenAuthService.verify_otp(db_session, phone, "123456")
    CitizenAuthService.register_onboarding(db_session, phone, {
        "full_name": "Anil Kulkarni",
        "consent_obtained": True
    })

    # Prepare for concurrent OTP verify
    db_session.query(OtpChallenge).filter(OtpChallenge.phone_hash == p_hash).delete()
    db_session.commit()
    CitizenAuthService.request_otp(db_session, phone)

    res1 = CitizenAuthService.verify_otp(db_session, phone, "123456")
    assert res1["authenticated"] is True
    assert res1["onboarding_required"] is False

    # Second OTP verify attempt after challenge consumed raises single-use check
    with pytest.raises(ValueError, match="No active OTP request found"):
        CitizenAuthService.verify_otp(db_session, phone, "123456")

    assert db_session.query(User).filter(User.phone == norm_phone).count() == 1
    assert db_session.query(CitizenProfile).filter(CitizenProfile.phone == norm_phone).count() == 1

def test_8_guest_migration_is_idempotent(db_session):
    guest = CitizenAuthService.create_guest_session(db_session, locale="mr-IN")
    session_id = guest["session_id"]

    phone = "9820000008"
    CitizenAuthService.request_otp(db_session, phone)
    CitizenAuthService.verify_otp(db_session, phone, "123456")
    onb = CitizenAuthService.register_onboarding(db_session, phone, {
        "full_name": "Sunil More",
        "consent_obtained": True
    })
    user_id = onb["user"]["id"]

    # Migrate 1
    mig1 = CitizenAuthService.migrate_guest_to_citizen(
        db_session,
        guest_session_id=session_id,
        user_id=user_id,
        idempotency_key=f"idem_key_{session_id}"
    )
    # Migrate 2
    mig2 = CitizenAuthService.migrate_guest_to_citizen(
        db_session,
        guest_session_id=session_id,
        user_id=user_id,
        idempotency_key=f"idem_key_{session_id}"
    )
    assert mig1["migration_id"] == mig2["migration_id"]
    assert mig1["status"] == "COMPLETED"

def test_9_different_phone_number_starts_onboarding(db_session):
    phone_a = "9820000009"
    phone_b = "9820000010"

    CitizenAuthService.request_otp(db_session, phone_a)
    CitizenAuthService.verify_otp(db_session, phone_a, "123456")
    CitizenAuthService.register_onboarding(db_session, phone_a, {
        "full_name": "Citizen A",
        "consent_obtained": True
    })

    # Phone B
    CitizenAuthService.request_otp(db_session, phone_b)
    res_b = CitizenAuthService.verify_otp(db_session, phone_b, "123456")
    assert res_b["onboarding_required"] is True
    assert res_b["is_new_citizen"] is True
    assert res_b["user"] is None

def test_10_household_and_citizen_rbac_isolation(db_session):
    phone_1 = "9820000011"
    phone_2 = "9820000012"

    CitizenAuthService.request_otp(db_session, phone_1)
    CitizenAuthService.verify_otp(db_session, phone_1, "123456")
    onb1 = CitizenAuthService.register_onboarding(db_session, phone_1, {
        "full_name": "Household Head 1",
        "consent_obtained": True
    })
    user1_id = onb1["user"]["id"]
    prof1_id = onb1["citizen_profile"]["id"]

    # Add household member to citizen 1
    m1 = HouseholdMember(
        id="hm-test-001",
        citizen_id=prof1_id,
        full_name="Grandmother 1",
        relationship_type="GRANDMOTHER",
        age=70,
        sex="FEMALE"
    )
    db_session.add(m1)
    db_session.commit()

    CitizenAuthService.request_otp(db_session, phone_2)
    CitizenAuthService.verify_otp(db_session, phone_2, "123456")
    onb2 = CitizenAuthService.register_onboarding(db_session, phone_2, {
        "full_name": "Household Head 2",
        "consent_obtained": True
    })
    user2_id = onb2["user"]["id"]

    bens1 = CitizenAuthService.get_authorized_beneficiaries(db_session, user1_id)
    bens2 = CitizenAuthService.get_authorized_beneficiaries(db_session, user2_id)

    # Citizen 1 has Myself + Grandmother 1
    assert len(bens1) == 2
    assert any("Grandmother 1" in b["displayName"] for b in bens1)
    grandma_ben = [b for b in bens1 if "Grandmother 1" in b["displayName"]][0]
    assert grandma_ben["relationship"] == "GRANDMOTHER"

    # Citizen 2 has only Myself, isolated from Citizen 1's household
    assert len(bens2) == 1
    assert not any("Grandmother 1" in b["displayName"] for b in bens2)

def test_11_missing_relationship_returns_unknown_without_blocking_login(db_session):
    phone = "9820000013"
    norm_phone = normalize_indian_phone(phone)
    p_hash = hash_phone(norm_phone)

    CitizenAuthService.request_otp(db_session, phone)
    CitizenAuthService.verify_otp(db_session, phone, "123456")
    onb = CitizenAuthService.register_onboarding(db_session, phone, {
        "full_name": "Suresh Raina",
        "consent_obtained": True
    })
    user_id = onb["user"]["id"]
    prof_id = onb["citizen_profile"]["id"]

    # Insert incomplete household member row with empty relationship
    m_incomplete = HouseholdMember(
        id="hm-test-incomplete-001",
        citizen_id=prof_id,
        full_name="Uncle Without Relation",
        relationship_type="",
        age=55,
        sex="MALE"
    )
    db_session.add(m_incomplete)
    db_session.commit()

    # Clear OTP challenge cooldown
    db_session.query(OtpChallenge).filter(OtpChallenge.phone_hash == p_hash).delete()
    db_session.commit()

    # Returning login must succeed without 500 error
    CitizenAuthService.request_otp(db_session, phone)
    login_res = CitizenAuthService.verify_otp(db_session, phone, "123456")
    assert login_res["authenticated"] is True

    # Incomplete member serialized with canonical relationship: UNKNOWN
    bens = login_res["authorized_beneficiaries"]
    uncle_ben = [b for b in bens if b["displayName"] == "Uncle Without Relation"][0]
    assert uncle_ben["relationship"] == "UNKNOWN"

def test_12_otp_double_submission_is_idempotent(db_session):
    phone = "9820000014"
    norm_phone = normalize_indian_phone(phone)
    p_hash = hash_phone(norm_phone)

    CitizenAuthService.request_otp(db_session, phone)
    CitizenAuthService.verify_otp(db_session, phone, "123456")
    CitizenAuthService.register_onboarding(db_session, phone, {
        "full_name": "Ravi Shastri",
        "consent_obtained": True
    })

    # Prepare for returning login with idempotency key
    db_session.query(OtpChallenge).filter(OtpChallenge.phone_hash == p_hash).delete()
    db_session.commit()

    CitizenAuthService.request_otp(db_session, phone)
    idem_key = "test_idem_verify_12345"

    res1 = CitizenAuthService.verify_otp(db_session, phone, "123456", idempotency_key=idem_key)
    res2 = CitizenAuthService.verify_otp(db_session, phone, "123456", idempotency_key=idem_key)

    assert res1["access_token"] == res2["access_token"]
    assert res1["user"]["id"] == res2["user"]["id"]

def test_13_returning_citizen_login_after_explicit_logout_full_journey(client, db_session):
    phone = "9820000099"
    norm_phone = normalize_indian_phone(phone)
    p_hash = hash_phone(norm_phone)

    # 1. Onboard new citizen via API
    onb_res = client.post("/api/citizen/onboarding", json={
        "phone": phone,
        "full_name": "Manav Raju Singh",
        "age": 29,
        "gender": "MALE",
        "village": "Kalyanpur",
        "consent_obtained": True
    })
    assert onb_res.status_code == 200
    onb_data = onb_res.json()["data"]
    user_id = onb_data["user"]["id"]
    profile_id = onb_data["citizen_profile"]["id"]
    token_1 = onb_data["access_token"]
    assert "aarogya_citizen_refresh" in client.cookies

    # 2. Add a household member to test household serialization on returning login
    m = HouseholdMember(
        id=generate_uuid(),
        citizen_id=profile_id,
        full_name="Sunita Singh",
        relationship_type="SPOUSE",
        age=27,
        sex="FEMALE"
    )
    db_session.add(m)
    db_session.commit()

    # 3. Explicit Logout
    logout_res = client.post("/api/citizen/auth/logout", headers={"Authorization": f"Bearer {token_1}"})
    assert logout_res.status_code == 200

    # Old sessions for this user should all be revoked
    revoked_sessions = db_session.query(AuthSession).filter(
        AuthSession.user_id == user_id,
        AuthSession.revoked_at.isnot(None)
    ).all()
    assert len(revoked_sessions) >= 1

    # Refreshing after logout must return 401
    fail_refresh = client.post("/api/citizen/auth/refresh", json={})
    assert fail_refresh.status_code == 401

    # 4. User and CitizenProfile remain active and untouched
    user = db_session.query(User).filter(User.id == user_id).first()
    assert user is not None and user.is_active is True
    assert user.citizen_profile.id == profile_id

    # 5. Clear challenge cooldown & Request new OTP for the SAME number
    db_session.query(OtpChallenge).filter(OtpChallenge.phone_hash == p_hash).delete()
    db_session.commit()

    otp_req = client.post("/api/citizen/auth/otp/request", json={"phone": phone})
    assert otp_req.status_code == 200

    # 6. Verify OTP for returning citizen
    otp_verify = client.post("/api/citizen/auth/otp/verify", json={
        "phone": phone,
        "otp": "123456"
    })
    assert otp_verify.status_code == 200
    verify_data = otp_verify.json()["data"]

    # Assertions
    assert verify_data["authenticated"] is True
    assert verify_data["onboarding_required"] is False
    assert verify_data["is_new_citizen"] is False
    assert verify_data["user"]["id"] == user_id
    assert verify_data["user"]["name"] == "Manav Raju Singh"
    assert verify_data["citizen_profile"]["id"] == profile_id
    assert len(verify_data["authorized_beneficiaries"]) == 2
    assert "aarogya_citizen_refresh" in client.cookies

    new_token = verify_data["access_token"]
    assert new_token is not None

    # 7. Check database counts: 0 new users, 0 new profiles, exactly 1 new active AuthSession
    new_active_sessions = db_session.query(AuthSession).filter(
        AuthSession.user_id == user_id,
        AuthSession.revoked_at.is_(None)
    ).all()
    assert len(new_active_sessions) == 1

    # 8. Immediately verify /auth/refresh -> 200
    ref_res = client.post("/api/citizen/auth/refresh", json={})
    assert ref_res.status_code == 200
    assert ref_res.json()["data"]["access_token"] is not None

    # 9. Verify /auth/me -> 200 with the exact same identity
    me_res = client.get("/api/citizen/auth/me", headers={"Authorization": f"Bearer {new_token}"})
    assert me_res.status_code == 200
    me_data = me_res.json()["data"]
    assert me_data["user"]["id"] == user_id
    assert me_data["user"]["name"] == "Manav Raju Singh"
    assert len(me_data["authorized_beneficiaries"]) == 2

def test_14_returning_login_with_multiple_old_revoked_sessions(db_session):
    phone = "9820000088"
    norm_phone = normalize_indian_phone(phone)
    p_hash = hash_phone(norm_phone)

    CitizenAuthService.request_otp(db_session, phone)
    CitizenAuthService.verify_otp(db_session, phone, "123456")
    onb = CitizenAuthService.register_onboarding(db_session, phone, {
        "full_name": "Kavita Rao",
        "consent_obtained": True
    })
    user_id = onb["user"]["id"]

    # Create 3 historical revoked sessions for this user
    now = utc_now()
    for i in range(3):
        sess = AuthSession(
            id=generate_uuid(),
            user_id=user_id,
            refresh_token_hash=f"revoked_hash_{i}_{generate_uuid()}",
            expires_at=now + timedelta(days=7),
            revoked_at=now - timedelta(days=i+1),
            created_at=now - timedelta(days=i+2)
        )
        db_session.add(sess)
    db_session.commit()

    # Clear OTP cooldown
    db_session.query(OtpChallenge).filter(OtpChallenge.phone_hash == p_hash).delete()
    db_session.commit()

    # Returning login must succeed smoothly without conflicting with revoked sessions
    CitizenAuthService.request_otp(db_session, phone)
    login_res = CitizenAuthService.verify_otp(db_session, phone, "123456")
    assert login_res["authenticated"] is True
    assert login_res["user"]["id"] == user_id

def test_15_deactivated_user_cannot_login(db_session):
    phone = "9820000077"
    norm_phone = normalize_indian_phone(phone)
    p_hash = hash_phone(norm_phone)

    CitizenAuthService.request_otp(db_session, phone)
    CitizenAuthService.verify_otp(db_session, phone, "123456")
    onb = CitizenAuthService.register_onboarding(db_session, phone, {
        "full_name": "Deactivated User",
        "consent_obtained": True
    })
    user_id = onb["user"]["id"]

    # Deactivate user
    user = db_session.query(User).filter(User.id == user_id).first()
    user.is_active = False
    db_session.commit()

    # Clear OTP cooldown
    db_session.query(OtpChallenge).filter(OtpChallenge.phone_hash == p_hash).delete()
    db_session.commit()

    CitizenAuthService.request_otp(db_session, phone)
    with pytest.raises(ValueError, match="Account is deactivated"):
        CitizenAuthService.verify_otp(db_session, phone, "123456")

def test_identity_diagnostic_integrity_report(db_session):
    report = IdentityDiagnosticService.run_full_diagnostic(db_session)
    assert "summary" in report
    assert "status" in report["summary"]
    assert report["summary"]["duplicate_identities_count"] == 0
    assert report["summary"]["multiple_profiles_count"] == 0
    assert report["summary"]["orphaned_profiles_count"] == 0


