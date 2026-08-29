import os
import requests
from typing import Dict, Any, Optional

class SarvamVoiceProvider:
    """
    Sarvam Live Voice AI Integration provider.
    Fallback speech-to-text / text-to-speech for local deployment.
    """
    def __init__(self):
        self.api_key = os.getenv("SARVAM_API_KEY", "")
        self.enabled = (
            os.getenv("SARVAM_STT_ENABLED", "false").lower() == "true" or
            os.getenv("SARVAM_ENABLED", "false").lower() == "true"
        )
        self.stt_model = os.getenv("SARVAM_STT_MODEL", "saaras:v3")
        self.compute_url = "https://api.sarvam.ai/speech-to-text"

    def transcribe_audio(self, file_path: str, language: str = "mr-IN") -> Dict[str, Any]:
        """
        Transcribes the supplied audio file path using Sarvam's ASR pipeline.
        """
        if not self.enabled or not self.api_key:
            return {
                "transcript": "",
                "status": "BLOCKED_BY_CREDENTIALS",
                "mode": "FALLBACK"
            }

        try:
            # Official Sarvam API expects form data with 'file' and 'model' attributes.
            headers = {"api-subscription-key": self.api_key}
            with open(file_path, "rb") as f:
                files = {"file": f}
                data = {
                    "model": self.stt_model,
                    "language_code": language
                }
                res = requests.post(self.compute_url, headers=headers, files=files, data=data, timeout=30)
                if res.status_code == 200:
                    res_data = res.json()
                    return {
                        "transcript": res_data.get("transcript", ""),
                        "status": "LIVE_VERIFIED",
                        "mode": "Sarvam Live"
                    }
                else:
                    return {
                        "transcript": "",
                        "status": f"ERROR_{res.status_code}",
                        "mode": "FALLBACK"
                    }
        except Exception as e:
            print(f"Sarvam Voice client error: {e}")
            return {
                "transcript": "",
                "status": "PROVIDER_UNAVAILABLE",
                "mode": "FALLBACK"
            }

sarvam_voice_provider = SarvamVoiceProvider()
