from typing import Dict, Any, Optional
from app.integrations.base import BaseIntegrationAdapter
from app.config import settings

class BhashiniAdapter(BaseIntegrationAdapter):
    """
    BHASHINI Government Indic Speech, Translation & TTS Adapter.
    """
    def __init__(self):
        super().__init__(mode=settings.BHASHINI_MODE)

    def speech_to_text(self, audio_bytes: bytes, source_language: str = "mr") -> Dict[str, Any]:
        if not audio_bytes or len(audio_bytes) == 0:
            return {
                "status": "NO_AUDIO",
                "transcript": "",
                "detected_language": source_language,
                "confidence": 0.0,
                "provider": "BHASHINI"
            }

        if self.is_mock:
            return {
                "status": "PROVIDER_UNAVAILABLE",
                "transcript": "",
                "detected_language": source_language,
                "confidence": 0.0,
                "detail": "BHASHINI live credentials not configured"
            }
        
        return {
            "status": "PROVIDER_UNAVAILABLE",
            "transcript": "",
            "detected_language": source_language,
            "confidence": 0.0
        }

    def text_to_speech(self, text: str, target_language: str = "mr") -> Dict[str, Any]:
        if self.is_mock:
            return {
                "status": "MOCKED",
                "audio_url": "/api/voice/mock-audio-response.mp3",
                "target_language": target_language,
                "duration_seconds": 4.5
            }
        return {
            "status": "MOCKED",
            "audio_url": "/api/voice/mock-audio-response.mp3",
            "target_language": target_language
        }

bhashini_adapter = BhashiniAdapter()
