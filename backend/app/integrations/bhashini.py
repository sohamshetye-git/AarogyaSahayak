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
        if self.is_mock:
            # Deterministic mock transcripts based on language
            sample_transcripts = {
                "mr": "मला खूप डोकेदुखी होत आहे, डोळ्यांसमोर अंधारी येत आहे आणि पायावर सूज आहे.", # Marathi canonical
                "hi": "मुझे बहुत तेज सिरदर्द हो रहा है, आंखों के आगे धुंधलापन है और पैरों में सूजन है.", # Hindi canonical
                "en": "I have severe headache, blurred vision, and swollen feet."
            }
            return {
                "status": "MOCKED",
                "transcript": sample_transcripts.get(source_language, sample_transcripts["mr"]),
                "detected_language": source_language,
                "confidence": 0.96,
                "confirmation_required": True
            }
        
        # Real BHASHINI API invocation logic here when live keys are provided
        return {
            "status": "MOCKED",
            "transcript": "मला खूप डोकेदुखी होत आहे आणि डोळ्यांसमोर अंधारी येत आहे.",
            "detected_language": source_language,
            "confidence": 0.94
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
