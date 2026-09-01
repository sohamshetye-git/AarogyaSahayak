import os
import json
import base64
import wave
import io
import tempfile
import pytest
from fastapi.testclient import TestClient

def test_voice_diagnostics_endpoint(client: TestClient):
    """
    Test GET /api/voice/diagnostics:
    - Verifies secret-safe structure (no API keys exposed)
    - Verifies configured status and models
    """
    res = client.get("/api/voice/diagnostics")
    assert res.status_code == 200
    data = res.json()["data"]
    assert "sarvam_key_configured" in data
    assert "tts_enabled" in data
    assert "model" in data
    assert "speaker" in data
    assert "api_connectivity" in data
    # Ensure no secret strings leaked
    raw_text = res.text
    assert "sk_" not in raw_text

def test_voice_tts_canonical_contract_11_locales(client: TestClient):
    """
    Test POST /api/voice/tts canonical contract across all 11 Indian locales:
    - Gujarati, Bengali, Kannada, Telugu, Tamil, Malayalam, Punjabi, Odia, Marathi, Hindi, English
    - Verifies exact canonical response structure:
      {
        "data": {
          "audio_base64": "<non-empty>",
          "mime_type": "audio/wav",
          "language_code": "<locale>",
          "provider": "SARVAM",
          "model": "bulbul:v3"
        }
      }
    - Validates audio is non-empty, valid base64 and decodable WAV
    """
    all_locales = [
        ("mr-IN", "आरोग्य सहाय्यक वापरण्यासाठी मराठी निवडा"),
        ("hi-IN", "आरोग्य सहायक का उपयोग करने के लिए हिंदी चुनें"),
        ("en-IN", "Choose English to use Aarogya Sahayak"),
        ("gu-IN", "આરોગ્ય સહાયક વાપરવા માટે ગુજરાતી પસંદ કરો"),
        ("bn-IN", "আরোগ্য সহায়ক ব্যবহার করার জন্য বাংলা বেছে নিন"),
        ("kn-IN", "ಆರೋಗ್ಯ ಸಹಾಯಕ ಬಳಸಲು ಕನ್ನಡ ಆಯ್ಕೆಮಾಡಿ"),
        ("te-IN", "ఆరోగ్య సహాయక్ ఉపయోగించడానికి తెలుగు ఎంచుకోండి"),
        ("ta-IN", "ஆரோக்ய சஹாயக்கைப் பயன்படுத்த தமிழைத் தேர்வு செய்யவும்"),
        ("ml-IN", "ആരോഗ്യ സഹായക് ഉപയോഗിക്കാൻ മലയാളം തിരഞ്ഞെടുക്കുക"),
        ("pa-IN", "ਅਰੋਗਿਆ ਸਹਾਇਕ ਦੀ ਵਰਤੋਂ ਕਰਨ ਲਈ ਪੰਜਾਬੀ ਚੁਣੋ"),
        ("od-IN", "ଆରୋଗ୍ୟ ସହାୟକ ବ୍ୟବହାର କରିବା ପାଇଁ ଓଡ଼ିଆ ବାଛନ୍ତୁ")
    ]

    for locale, phrase in all_locales:
        res = client.post(
            "/api/voice/tts",
            json={
                "text": phrase,
                "language_code": locale,
                "context": "LANGUAGE_PREVIEW"
            }
        )
        assert res.status_code == 200, f"Failed for {locale}: {res.text}"
        body = res.json()
        assert "data" in body, f"Missing 'data' wrapper for {locale}"
        data = body["data"]

        # Canonical contract fields assertion
        assert data["language_code"] == locale
        assert data["mime_type"] == "audio/wav"
        assert data["provider"] == "SARVAM"
        assert data["model"] == "bulbul:v3"
        assert isinstance(data["audio_base64"], str)
        assert len(data["audio_base64"]) > 100

        # Decode base64 and verify valid audio structure
        audio_bytes = base64.b64decode(data["audio_base64"])
        assert len(audio_bytes) > 0

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_wav:
            temp_path = temp_wav.name
            temp_wav.write(audio_bytes)

        try:
            with wave.open(temp_path, "rb") as wav_file:
                assert wav_file.getnchannels() in (1, 2)
                assert wav_file.getsampwidth() in (1, 2, 4)
                assert wav_file.getframerate() > 0
                assert wav_file.getnframes() > 0
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

def test_voice_tts_invalid_locale_rejection(client: TestClient):
    """Verify that unsupported locales are rejected with 400."""
    res = client.post(
        "/api/voice/tts",
        json={
            "text": "Hello World",
            "language_code": "de-DE",
            "context": "LANGUAGE_PREVIEW"
        }
    )
    assert res.status_code == 400
    assert res.json()["detail"]["error"]["code"] == "INVALID_LOCALE"
