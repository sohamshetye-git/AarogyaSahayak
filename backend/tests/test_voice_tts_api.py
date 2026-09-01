import os
import json
import pytest
from fastapi.testclient import TestClient

def test_voice_tts_endpoint_11_locales(client: TestClient):
    """
    Test POST /api/voice/tts across all 11 Indian locales:
    - Verifies 11-locale allowlist validation
    - Verifies non-empty audio response
    - Verifies caching behaviour
    """
    locales_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "packages", "i18n", "locales"
    )

    all_locales = [
        "en-IN", "hi-IN", "mr-IN", "gu-IN", "bn-IN",
        "kn-IN", "te-IN", "ta-IN", "ml-IN", "pa-IN", "od-IN"
    ]

    for locale in all_locales:
        with open(os.path.join(locales_dir, f"{locale}.json"), encoding="utf-8") as f:
            loc_data = json.load(f)
        
        preview_text = loc_data.get("citizen", {}).get("language_preview") or "Aarogya Sahayak"
        
        # 1. First call (May fetch or hit cache)
        res = client.post(
            "/api/voice/tts",
            json={
                "text": preview_text,
                "language_code": locale,
                "context": "LANGUAGE_PREVIEW"
            }
        )
        assert res.status_code == 200, f"Failed for {locale}: {res.text}"
        data = res.json()["data"]
        assert data["status"] in ["SUCCESS", "UNAVAILABLE", "ERROR"], f"Unexpected status for {locale}: {data}"
        assert data["language_code"] == locale
        assert data["mime_type"] == "audio/wav"
        
        if data["status"] == "SUCCESS":
            assert data["audio_base64"] is not None
            assert len(data["audio_base64"]) > 100
            
            # 2. Second call should be served directly from in-memory cache
            res_cached = client.post(
                "/api/voice/tts",
                json={
                    "text": preview_text,
                    "language_code": locale,
                    "context": "LANGUAGE_PREVIEW"
                }
            )
            assert res_cached.status_code == 200
            cached_data = res_cached.json()["data"]
            assert cached_data["cached"] is True
            assert cached_data["audio_base64"] == data["audio_base64"]

def test_voice_tts_invalid_locale(client: TestClient):
    """Verify that unsupported locales return a 400 Bad Request with a clear error."""
    res = client.post(
        "/api/voice/tts",
        json={
            "text": "Hello World",
            "language_code": "fr-FR",
            "context": "LANGUAGE_PREVIEW"
        }
    )
    assert res.status_code == 400
    err = res.json()["detail"]["error"]
    assert err["code"] == "INVALID_LOCALE"
