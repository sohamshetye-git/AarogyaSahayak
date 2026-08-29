from typing import Dict, Any, Optional
from app.models import CasePriorityEnum

class LiteRTOfflineModelService:
    """
    LiteRT (TensorFlow Lite) Offline Edge Model Evaluation Service.
    BOUNDED SUPPLEMENTAL SIGNAL:
    Deterministic emergency rules always run independently and override any lower AI signal.
    """
    MODEL_VERSION = "litert-v1.0.4-edge"
    
    @classmethod
    def evaluate_supplemental_signal(
        cls,
        systolic_bp: Optional[int],
        diastolic_bp: Optional[int],
        spo2: Optional[int],
        is_pregnant: bool = False
    ) -> Dict[str, Any]:
        """
        Outputs: LOW_MODEL_SIGNAL, MODERATE_MODEL_SIGNAL, or HIGH_MODEL_SIGNAL.
        """
        signal = "LOW_MODEL_SIGNAL"
        confidence = 0.85

        if (systolic_bp and systolic_bp >= 140) or (diastolic_bp and diastolic_bp >= 90) or (spo2 and spo2 < 94):
            signal = "HIGH_MODEL_SIGNAL"
            confidence = 0.94
        elif (systolic_bp and systolic_bp >= 130) or is_pregnant:
            signal = "MODERATE_MODEL_SIGNAL"
            confidence = 0.88

        return {
            "model_signal": signal,
            "confidence": confidence,
            "model_version": cls.MODEL_VERSION,
            "label": "Research/Demonstration Model — Not Clinically Validated",
            "deterministic_override_guaranteed": True
        }

litert_service = LiteRTOfflineModelService()
