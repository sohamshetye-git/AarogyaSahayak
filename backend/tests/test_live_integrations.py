import pytest
from app.ai.providers.gemini_service import gemini_service
from app.ai.providers.tavily_service import tavily_service
from app.ai.providers.sarvam_service import sarvam_voice_provider

@pytest.mark.live
def test_gemini_live_structured_smoke():
    if not gemini_service.is_live:
        pytest.skip("Gemini API Key is not live or configured. Skipping live test.")

    intake = gemini_service.process_intake("Citizen states headache and blurred vision during pregnancy")
    assert intake.is_pregnant is True
    assert any("headache" in s.lower() for s in intake.symptoms)

@pytest.mark.live
def test_tavily_live_verification_smoke():
    if not tavily_service.is_live:
        pytest.skip("Tavily API Key is not live or configured. Skipping live test.")

    res = tavily_service.verify_official_update(query="National Health Mission maternal guide")
    assert "verified" in res
    assert "status" in res

@pytest.mark.live
def test_sarvam_voice_live_smoke():
    if not sarvam_voice_provider.enabled:
        pytest.skip("Sarvam live speech is disabled. Skipping live test.")

    res = sarvam_voice_provider.transcribe_audio("nonexistent.webm")
    assert res["status"] in ("BLOCKED_BY_CREDENTIALS", "PROVIDER_UNAVAILABLE")
