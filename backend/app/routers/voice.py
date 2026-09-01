import hashlib
import time
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Request, Response
from pydantic import BaseModel, Field
from app.config import settings
from app.integrations.sarvam import sarvam_adapter
from app.schemas import StandardResponse

router = APIRouter(prefix="/voice", tags=["Voice & TTS Services"])

# Allowlist of 11 supported Indian locales
SUPPORTED_LOCALES = {
    "en-IN", "hi-IN", "mr-IN", "gu-IN", "bn-IN",
    "kn-IN", "te-IN", "ta-IN", "ml-IN", "pa-IN", "od-IN"
}

# In-memory LRU / TTS Cache: hash(locale + text + model) -> {audio_base64, mime_type, timestamp}
_TTS_CACHE: Dict[str, Dict[str, Any]] = {}
MAX_CACHE_ENTRIES = 500

# Simple sliding window rate limiting: ip -> list of timestamps
_RATE_LIMITS: Dict[str, list] = {}
RATE_LIMIT_MAX_CALLS = 60 # 60 calls per minute
RATE_LIMIT_WINDOW = 60 # 60 seconds

class TTSRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000, description="Text to synthesize")
    language_code: str = Field(..., description="11-locale language code, e.g. gu-IN")
    context: Optional[str] = Field(default="LANGUAGE_PREVIEW", description="Context tag e.g. LANGUAGE_PREVIEW, ONBOARDING, CLINICAL_SUMMARY")
    speaker: Optional[str] = Field(default=None, description="Optional speaker override")

class TTSResponseData(BaseModel):
    audio_base64: str
    mime_type: str = "audio/wav"
    language_code: str
    provider: str = "SARVAM"
    model: str = "bulbul:v3"

class VoiceDiagnosticsData(BaseModel):
    sarvam_key_configured: bool
    tts_enabled: bool
    model: str
    speaker: str
    api_connectivity: str
    last_status_code: Optional[int] = None

# Track last API status code safely in memory
_LAST_API_STATUS_CODE: Optional[int] = None

def _get_cache_key(text: str, locale: str, model: str, speaker: str) -> str:
    h = hashlib.sha256(f"{locale}:{model}:{speaker}:{text.strip()}".encode("utf-8")).hexdigest()
    return h

def _check_rate_limit(client_ip: str):
    now = time.time()
    if client_ip not in _RATE_LIMITS:
        _RATE_LIMITS[client_ip] = []
    
    # Filter timestamps within window
    _RATE_LIMITS[client_ip] = [t for t in _RATE_LIMITS[client_ip] if now - t < RATE_LIMIT_WINDOW]
    
    if len(_RATE_LIMITS[client_ip]) >= RATE_LIMIT_MAX_CALLS:
        raise HTTPException(
            status_code=429,
            detail={
                "error": {
                    "code": "RATE_LIMIT_EXCEEDED",
                    "message": "Too many voice synthesis requests. Please wait a moment and retry."
                }
            }
        )
    _RATE_LIMITS[client_ip].append(now)

@router.get("/diagnostics", response_model=StandardResponse)
async def get_voice_diagnostics():
    """
    Secret-safe diagnostic endpoint for voice & Sarvam TTS configuration.
    Never prints or reveals API keys.
    """
    is_key_configured = bool(settings.SARVAM_API_KEY and len(settings.SARVAM_API_KEY.strip()) > 0)
    tts_enabled = bool(settings.SARVAM_TTS_ENABLED)
    model = getattr(settings, "SARVAM_TTS_MODEL", "bulbul:v3")
    speaker = getattr(settings, "SARVAM_TTS_SPEAKER", "ritu")

    connectivity = "UNAVAILABLE"
    if is_key_configured and tts_enabled and not sarvam_adapter.is_mock:
        connectivity = "CONFIGURED_LIVE"
    elif sarvam_adapter.is_mock:
        connectivity = "MOCK_MODE"

    return StandardResponse(
        data=VoiceDiagnosticsData(
            sarvam_key_configured=is_key_configured,
            tts_enabled=tts_enabled,
            model=model,
            speaker=speaker,
            api_connectivity=connectivity,
            last_status_code=_LAST_API_STATUS_CODE
        ).model_dump()
    )

@router.post("/tts", response_model=StandardResponse)
async def synthesize_speech(req: TTSRequest, request: Request):
    """
    Synthesize natural Indian speech audio using Sarvam AI bulbul:v3 via backend gateway.
    Never exposes API keys to client. Returns canonical base64 audio and MIME type.
    """
    global _LAST_API_STATUS_CODE

    # 1. Locale validation against 11-language allowlist
    norm_locale = req.language_code.strip()
    if norm_locale in {"en", "hi", "mr", "gu", "bn", "kn", "te", "ta", "ml", "pa", "od", "or"}:
        norm_locale = f"{norm_locale}-IN" if norm_locale != "or" else "od-IN"
    
    if norm_locale not in SUPPORTED_LOCALES:
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "INVALID_LOCALE",
                    "message": f"Unsupported language locale '{req.language_code}'. Supported locales are: {', '.join(sorted(SUPPORTED_LOCALES))}"
                }
            }
        )

    # 2. Rate limiting check
    client_ip = request.client.host if request.client else "127.0.0.1"
    _check_rate_limit(client_ip)

    # 3. Model and Speaker Resolution
    model = getattr(settings, "SARVAM_TTS_MODEL", "bulbul:v3")
    speaker = req.speaker or getattr(settings, "SARVAM_TTS_SPEAKER", "ritu")

    # 4. Check cache for fixed onboarding & language preview queries
    cache_key = _get_cache_key(req.text, norm_locale, model, speaker)
    if cache_key in _TTS_CACHE:
        cached_item = _TTS_CACHE[cache_key]
        return StandardResponse(
            data=TTSResponseData(
                audio_base64=cached_item["audio_base64"],
                mime_type="audio/wav",
                language_code=norm_locale,
                provider="SARVAM",
                model=model
            ).model_dump()
        )

    # 5. Check if Sarvam is enabled and API key is present
    if not settings.SARVAM_TTS_ENABLED or sarvam_adapter.is_mock or not settings.SARVAM_API_KEY:
        raise HTTPException(
            status_code=503,
            detail={
                "error": {
                    "code": "TTS_PROVIDER_UNAVAILABLE",
                    "message": "Sarvam TTS provider is not configured or currently disabled"
                }
            }
        )

    # 6. Perform live TTS request via Sarvam Adapter
    tts_result = sarvam_adapter.text_to_speech(
        text=req.text,
        target_language_code=norm_locale,
        speaker=speaker,
        model=model
    )

    if tts_result.get("status") == "SUCCESS" and tts_result.get("audio_base64"):
        audio_b64 = tts_result["audio_base64"]
        _LAST_API_STATUS_CODE = 200
        
        # Store in cache
        if len(_TTS_CACHE) >= MAX_CACHE_ENTRIES:
            oldest_k = next(iter(_TTS_CACHE))
            _TTS_CACHE.pop(oldest_k, None)
        
        _TTS_CACHE[cache_key] = {
            "audio_base64": audio_b64,
            "timestamp": time.time()
        }

        return StandardResponse(
            data=TTSResponseData(
                audio_base64=audio_b64,
                mime_type="audio/wav",
                language_code=norm_locale,
                provider="SARVAM",
                model=model
            ).model_dump()
        )
    else:
        err_code = tts_result.get("error_code")
        if err_code and err_code.startswith("HTTP_"):
            try:
                _LAST_API_STATUS_CODE = int(err_code.replace("HTTP_", ""))
            except ValueError:
                _LAST_API_STATUS_CODE = 502
        else:
            _LAST_API_STATUS_CODE = 500

        raise HTTPException(
            status_code=502,
            detail={
                "error": {
                    "code": "TTS_SYNTHESIS_FAILED",
                    "message": f"TTS synthesis failed for locale {norm_locale}",
                    "detail": tts_result.get("detail", "Unknown upstream error")
                }
            }
        )
