from typing import List, Optional, Tuple
from app.models import CasePriorityEnum

class EmergencyRuleEvaluator:
    """
    Deterministic Safety Rule Engine.
    Executes authoritatively in code before and independently of any LLM.
    Zero hallucination risk.
    """

    CRITICAL_SYMPTOMS = {
        "chest pain", "severe breathlessness", "unconscious", "unconsciousness",
        "convulsions", "seizure", "heavy bleeding", "severe bleeding",
        "coughing blood", "self harm", "suicide", "breathing difficulty",
        "difficulty breathing", "shortness of breath", "breathlessness"
    }

    MATERNAL_RED_FLAGS = {
        "blurred vision", "blurring of vision", "severe headache", 
        "swelling in feet", "swelling of face", "epigastric pain",
        "reduced fetal movement", "water breaking", "vaginal bleeding"
    }

    @classmethod
    def evaluate(
        cls,
        symptoms: List[str],
        is_pregnant: bool = False,
        gestational_weeks: Optional[int] = None,
        systolic_bp: Optional[int] = None,
        diastolic_bp: Optional[int] = None,
        spo2: Optional[int] = None,
        temperature_c: Optional[float] = None
    ) -> Tuple[CasePriorityEnum, bool, Optional[str], str]:
        """
        Returns:
            (priority, rule_triggered, reason, citizen_guidance)
        """
        normalized_symptoms = [s.strip().lower() for s in symptoms]
        symptom_text = " ".join(normalized_symptoms)

        # Rule 1: Maternal Pre-eclampsia / Severe Pregnancy Warning Sign
        # Gestational age >= 20 weeks (or known pregnant) + High BP (>=140/90) + Neurological/Visual signs
        has_maternal_symptoms = any(rf in symptom_text for rf in cls.MATERNAL_RED_FLAGS)
        has_severe_bp = (systolic_bp is not None and systolic_bp >= 140) or (diastolic_bp is not None and diastolic_bp >= 90)
        
        if is_pregnant and (has_severe_bp or (systolic_bp is not None and systolic_bp >= 150)) and has_maternal_symptoms:
            return (
                CasePriorityEnum.URGENT,
                True,
                "Pregnancy-related warning signs were recorded, including elevated blood pressure. Urgent PHC evaluation is recommended.",
                "Warning signs were detected for pregnancy health. We have alerted your assigned ASHA worker immediately. Please rest in a calm position while assistance is coordinated."
            )

        if is_pregnant and (systolic_bp is not None and systolic_bp >= 160 or (diastolic_bp is not None and diastolic_bp >= 110)):
            return (
                CasePriorityEnum.URGENT,
                True,
                "Severe maternal hypertension detected",
                "Your blood pressure reading requires immediate professional medical evaluation. Your ASHA worker has been notified."
            )

        # Rule 2: Critical General Red Flags
        for crit in cls.CRITICAL_SYMPTOMS:
            if crit in symptom_text:
                return (
                    CasePriorityEnum.URGENT,
                    True,
                    f"Critical symptom detected: {crit.title()}",
                    "Urgent professional evaluation is recommended. An immediate alert has been sent to your local health worker."
                )

        # Rule 3: SpO2 critical threshold
        if spo2 is not None and spo2 < 90:
            return (
                CasePriorityEnum.URGENT,
                True,
                f"Critically low oxygen saturation (SpO2: {spo2}%)",
                "Your oxygen level is significantly low. Urgent medical evaluation at the nearest health center is required."
            )

        # Rule 4: Moderate High Risk (High BP without pregnancy or Fever + moderate warning)
        if (systolic_bp is not None and systolic_bp >= 140) or (diastolic_bp is not None and diastolic_bp >= 90):
            return (
                CasePriorityEnum.HIGH,
                True,
                f"Stage 2 Hypertension detected (BP: {systolic_bp}/{diastolic_bp})",
                "Your blood pressure is elevated. A visit with your ASHA worker or PHC doctor is advised."
            )

        if temperature_c is not None and temperature_c >= 39.5: # 103.1 F
            return (
                CasePriorityEnum.HIGH,
                True,
                f"High fever detected ({temperature_c}°C)",
                "High body temperature recorded. Keep hydrated and seek medical consultation."
            )

        # Default Routine / Informational
        return (
            CasePriorityEnum.ROUTINE,
            False,
            None,
            "Your symptoms have been recorded. Your local ASHA worker will review your case during routine rounds."
        )
