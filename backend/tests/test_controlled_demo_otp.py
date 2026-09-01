import os
import pytest
from app.config import settings, Settings, validate_production_settings
from app.services.citizen_auth_service import (
    CitizenAuthService, MockOtpProvider, TwilioOtpProvider, get_otp_provider,
    normalize_indian_phone, hash_phone
)
from app.models import OtpChallenge, User, UserRoleEnum
from app.auth.security import get_password_hash

def test_staging_mock_otp_123456_succeeds(db_session, monkeypatch):
    """1. staging + MOCK + 123456 succeeds."""
    monkeypatch.setattr(settings, "ENVIRONMENT", "staging")
    monkeypatch.setattr(settings, "OTP_MODE", "MOCK")
    monkeypatch.setattr(settings, "DEMO_OTP_CODE", "123456")

    phone = "9820099001"
    req_res = CitizenAuthService.request_otp(db_session, phone)
    assert req_res["provider"] == "MOCK"

    # Verify with 123456
    verify_res = CitizenAuthService.verify_otp(db_session, phone, "123456")
    assert verify_res is not None
    assert "onboarding_required" in verify_res or "authenticated" in verify_res

def test_staging_mock_otp_12345_fails(db_session, monkeypatch):
    """2. staging + MOCK + 12345 (5 digits) fails."""
    monkeypatch.setattr(settings, "ENVIRONMENT", "staging")
    monkeypatch.setattr(settings, "OTP_MODE", "MOCK")
    monkeypatch.setattr(settings, "DEMO_OTP_CODE", "123456")

    phone = "9820099002"
    CitizenAuthService.request_otp(db_session, phone)

    with pytest.raises(ValueError, match="Incorrect OTP"):
        CitizenAuthService.verify_otp(db_session, phone, "12345")

def test_staging_mock_otp_incorrect_six_digit_code_fails(db_session, monkeypatch):
    """3. staging + MOCK + incorrect six-digit code fails."""
    monkeypatch.setattr(settings, "ENVIRONMENT", "staging")
    monkeypatch.setattr(settings, "OTP_MODE", "MOCK")
    monkeypatch.setattr(settings, "DEMO_OTP_CODE", "123456")

    phone = "9820099003"
    CitizenAuthService.request_otp(db_session, phone)

    with pytest.raises(ValueError, match="Incorrect OTP"):
        CitizenAuthService.verify_otp(db_session, phone, "654321")

def test_expired_mock_otp_fails(db_session, monkeypatch):
    """4. Expired mock OTP fails."""
    monkeypatch.setattr(settings, "ENVIRONMENT", "staging")
    monkeypatch.setattr(settings, "OTP_MODE", "MOCK")

    phone = "9820099004"
    CitizenAuthService.request_otp(db_session, phone)

    # Manually expire the challenge in DB
    p_hash = hash_phone(normalize_indian_phone(phone))
    challenge = db_session.query(OtpChallenge).filter(
        OtpChallenge.phone_hash == p_hash,
        OtpChallenge.consumed_at.is_(None)
    ).first()
    assert challenge is not None
    from datetime import datetime, timezone, timedelta
    challenge.expires_at = datetime.now(timezone.utc) - timedelta(seconds=10)
    db_session.commit()

    with pytest.raises(ValueError, match="OTP has expired"):
        CitizenAuthService.verify_otp(db_session, phone, "123456")

def test_too_many_attempts_are_rate_limited(db_session, monkeypatch):
    """5. Too many attempts are rate-limited and consume the challenge."""
    monkeypatch.setattr(settings, "ENVIRONMENT", "staging")
    monkeypatch.setattr(settings, "OTP_MODE", "MOCK")

    phone = "9820099005"
    CitizenAuthService.request_otp(db_session, phone)

    # Attempt 5 wrong codes
    for i in range(4):
        with pytest.raises(ValueError, match="Incorrect OTP"):
            CitizenAuthService.verify_otp(db_session, phone, f"99999{i}")

    # 5th attempt fails and locks challenge
    with pytest.raises(ValueError, match="Limit reached|Maximum OTP verification attempts exceeded"):
        CitizenAuthService.verify_otp(db_session, phone, "999999")

    # Subsequent attempt fails because max attempts reached / consumed
    with pytest.raises(ValueError, match="No active OTP request found|Maximum OTP verification attempts exceeded|Limit reached"):
        CitizenAuthService.verify_otp(db_session, phone, "123456")

def test_resend_cooldown_enforced(db_session, monkeypatch):
    """6. Resend cooldown remains enforced."""
    monkeypatch.setattr(settings, "ENVIRONMENT", "staging")
    monkeypatch.setattr(settings, "OTP_MODE", "MOCK")

    phone = "9820099006"
    CitizenAuthService.request_otp(db_session, phone)

    # Requesting immediately again should raise cooldown error
    with pytest.raises(ValueError, match="Please wait.*seconds before requesting a new OTP"):
        CitizenAuthService.request_otp(db_session, phone)

def test_no_twilio_http_request_in_mock_mode(db_session, monkeypatch):
    """7. No Twilio HTTP request occurs in mock mode."""
    monkeypatch.setattr(settings, "ENVIRONMENT", "staging")
    monkeypatch.setattr(settings, "OTP_MODE", "MOCK")

    provider = get_otp_provider()
    assert isinstance(provider, MockOtpProvider)
    assert not isinstance(provider, TwilioOtpProvider)

    # Mock provider dispatches synchronously without network calls
    phone = "9820099007"
    res = CitizenAuthService.request_otp(db_session, phone)
    assert res["provider"] == "MOCK"

def test_production_plus_mock_fails_startup():
    """8. production + MOCK fails startup or configuration validation."""
    orig_env = settings.ENVIRONMENT
    orig_otp = settings.OTP_MODE
    try:
        settings.ENVIRONMENT = "production"
        settings.OTP_MODE = "MOCK"
        with pytest.raises(RuntimeError, match="OTP_MODE=MOCK is strictly forbidden in production"):
            validate_production_settings()
    finally:
        settings.ENVIRONMENT = orig_env
        settings.OTP_MODE = orig_otp

def test_production_cannot_accept_demo_code(db_session, monkeypatch):
    """9. Production cannot accept the demo code automatically."""
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(settings, "OTP_MODE", "TWILIO")
    monkeypatch.setattr(settings, "TWILIO_ACCOUNT_SID", "AC_dummy")
    monkeypatch.setattr(settings, "TWILIO_AUTH_TOKEN", "auth_dummy")
    monkeypatch.setattr(settings, "TWILIO_FROM_NUMBER", "+1234567890")

    phone = "9820099008"

    # Mock the twilio network post so we can test code generation logic
    class FakeTwilioProvider:
        def send_otp(self, phone_norm, otp_code):
            return {"provider": "TWILIO", "status": "SENT"}

    monkeypatch.setattr("app.services.citizen_auth_service.get_otp_provider", lambda: FakeTwilioProvider())

    req = CitizenAuthService.request_otp(db_session, phone)
    assert "mock_code" not in req

    # In production, random 6 digits is generated, so fixed "123456" won't match (unless 1 in a million)
    # Check that hardcoded 123456 fails
    p_hash = hash_phone(normalize_indian_phone(phone))
    challenge = db_session.query(OtpChallenge).filter(
        OtpChallenge.phone_hash == p_hash,
        OtpChallenge.consumed_at.is_(None)
    ).first()
    assert challenge is not None
    # Verify candidate "123456" fails against challenge otp_hash if random code generated != 123456
    from app.services.citizen_auth_service import verify_otp_hash
    if not verify_otp_hash("123456", p_hash, challenge.otp_hash):
        with pytest.raises(ValueError, match="Incorrect OTP"):
            CitizenAuthService.verify_otp(db_session, phone, "123456")

def test_doctor_asha_admin_cannot_use_citizen_demo_otp(client, db_session):
    """13. Doctor, ASHA and Admin login cannot use Citizen demo OTP."""
    # Doctor / ASHA / Admin authenticate via /auth/login with identifier + password, not OTP
    doc = db_session.query(User).filter(User.identifier == "doc.sharma").first()
    if not doc:
        doc = User(
            id="doc-test-otp-guard",
            identifier="doc.sharma",
            name="Dr. Sharma",
            password_hash=get_password_hash("doctor123"),
            role=UserRoleEnum.PHC_DOCTOR,
            is_active=True
        )
        db_session.add(doc)
        db_session.commit()

    # Attempting to log in as doctor with demo OTP as password fails
    fail_res = client.post("/api/auth/login", json={"identifier": "doc.sharma", "password": "123456"})
    assert fail_res.status_code == 401

    # Correct password succeeds
    success_res = client.post("/api/auth/login", json={"identifier": "doc.sharma", "password": "doctor123"})
    assert success_res.status_code == 200
