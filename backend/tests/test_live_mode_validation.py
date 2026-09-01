import os
import pytest
from app.config import Settings, validate_production_settings
from app.services.citizen_auth_service import (
    CitizenAuthService, get_otp_provider, MockOtpProvider, TwilioOtpProvider, Msg91OtpProvider
)
from app.ai.providers.gemini_service import GeminiService
from app.ai.providers.tavily_service import TavilyVerificationService
from app.integrations.sarvam import SarvamAdapter
from app.integrations.google_maps import GoogleMapsAdapter

def test_live_modes_reject_missing_credentials(monkeypatch):
    """Live modes must raise safe configuration errors on startup if required API keys are missing."""
    
    # 1. Gemini live without key
    monkeypatch.setenv("GEMINI_MODE", "live")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="GEMINI_MODE=live requires GEMINI_API_KEY"):
        test_settings = Settings(GEMINI_MODE="live", GEMINI_API_KEY=None)
        # Verify validation function detects this
        from app.config import settings
        orig_gemini = settings.GEMINI_MODE
        orig_key = settings.GEMINI_API_KEY
        try:
            settings.GEMINI_MODE = "live"
            settings.GEMINI_API_KEY = None
            validate_production_settings()
        finally:
            settings.GEMINI_MODE = orig_gemini
            settings.GEMINI_API_KEY = orig_key

    # 2. Sarvam live without key
    with pytest.raises(RuntimeError, match="SARVAM_MODE=live requires SARVAM_API_KEY"):
        from app.config import settings
        orig_sarvam = settings.SARVAM_MODE
        orig_key = settings.SARVAM_API_KEY
        try:
            settings.SARVAM_MODE = "live"
            settings.SARVAM_API_KEY = None
            validate_production_settings()
        finally:
            settings.SARVAM_MODE = orig_sarvam
            settings.SARVAM_API_KEY = orig_key

    # 3. Tavily live without key
    with pytest.raises(RuntimeError, match="TAVILY_MODE=live requires TAVILY_API_KEY"):
        from app.config import settings
        orig_tavily = settings.TAVILY_MODE
        orig_key = settings.TAVILY_API_KEY
        try:
            settings.TAVILY_MODE = "live"
            settings.TAVILY_API_KEY = None
            validate_production_settings()
        finally:
            settings.TAVILY_MODE = orig_tavily
            settings.TAVILY_API_KEY = orig_key

def test_production_rejects_mock_otp():
    """Production environment must strictly block OTP_MODE=MOCK."""
    from app.config import settings
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

def test_staging_supports_live_and_mock_otp():
    """Staging supports MOCK, TWILIO, or MSG91 depending on credentials."""
    from app.config import settings
    orig_env = settings.ENVIRONMENT
    orig_otp = settings.OTP_MODE
    try:
        settings.ENVIRONMENT = "staging"
        settings.OTP_MODE = "MOCK"
        # Should not raise
        validate_production_settings()

        # Twilio without credentials in staging fails safely
        settings.OTP_MODE = "TWILIO"
        settings.TWILIO_ACCOUNT_SID = None
        with pytest.raises(RuntimeError, match="OTP_MODE=TWILIO requires TWILIO_ACCOUNT_SID"):
            validate_production_settings()

        # Twilio with credentials passes
        settings.TWILIO_ACCOUNT_SID = "AC_test123"
        settings.TWILIO_AUTH_TOKEN = "token_test123"
        settings.TWILIO_FROM_NUMBER = "+1234567890"
        validate_production_settings()
    finally:
        settings.ENVIRONMENT = orig_env
        settings.OTP_MODE = orig_otp
        settings.TWILIO_ACCOUNT_SID = None
        settings.TWILIO_AUTH_TOKEN = None
        settings.TWILIO_FROM_NUMBER = None

def test_otp_provider_resolution():
    """get_otp_provider returns the exact configured provider class."""
    from app.config import settings
    orig_otp = settings.OTP_MODE
    try:
        settings.OTP_MODE = "MOCK"
        assert isinstance(get_otp_provider(), MockOtpProvider)

        settings.OTP_MODE = "TWILIO"
        assert isinstance(get_otp_provider(), TwilioOtpProvider)

        settings.OTP_MODE = "MSG91"
        assert isinstance(get_otp_provider(), Msg91OtpProvider)
    finally:
        settings.OTP_MODE = orig_otp

def test_admin_integrations_diagnostic_never_exposes_secrets(client, db_session):
    """Admin diagnostic reports only 'configured' or 'unconfigured' without secrets."""
    # Log in as admin
    from app.models import User, UserRoleEnum
    from app.auth.security import get_password_hash

    admin = db_session.query(User).filter(User.identifier == "dho.admin").first()
    if not admin:
        admin = User(
            id="admin-test-01",
            identifier="dho.admin",
            name="District Admin",
            password_hash=get_password_hash("demo123"),
            role=UserRoleEnum.DISTRICT_ADMIN,
            is_active=True
        )
        db_session.add(admin)
        db_session.commit()

    login_res = client.post("/api/auth/login", json={"identifier": "dho.admin", "password": "demo123"})
    assert login_res.status_code == 200
    token = login_res.json()["data"]["access_token"]

    diag_res = client.get("/api/admin/integrations-status", headers={"Authorization": f"Bearer {token}"})
    assert diag_res.status_code == 200
    data = diag_res.json()["data"]
    
    assert "Gemini" in data
    assert "Sarvam" in data
    assert "Tavily" in data
    assert "OTP provider" in data
    assert "Google Maps" in data

    # Verify no secret keywords or partial tokens are leaked
    raw_str = str(data)
    assert "sk-" not in raw_str
    assert "AIza" not in raw_str
    assert "secret" not in raw_str.lower()
