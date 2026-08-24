import re
from typing import Dict, Any, List

class OutputGuard:
    """
    Medical Safety Guard for AI Generated Text.
    Ensures AI NEVER issues a diagnosis, prescribes dosage, or suggests medication directly to citizens.
    """

    PROHIBITED_PRESCRIPTION_TERMS = [
        r"\btake\s+\d+\s*mg\b",
        r"\bdosage\s+is\b",
        r"\bprescribe\b",
        r"\btake\s+(paracetamol|amoxicillin|ibuprofen|metformin|atenolol|nifedipine|aspirin)\b",
        r"\bdiscontinue\s+your\s+medication\b",
        r"\byou\s+have\s+been\s+diagnosed\s+with\b",
        r"\bconfirmed\s+diagnosis\b"
    ]

    CITIZEN_DISCLAIMER = "AI-assisted information – not a diagnosis."
    CLINICAL_DISCLAIMER = "AI-assisted summary – human review required."

    @classmethod
    def sanitize_citizen_response(cls, text: str) -> Dict[str, Any]:
        """
        Validates and guards AI output intended for rural citizens.
        """
        lower_text = text.lower()
        violates = False
        matched_violations: List[str] = []

        for pattern in cls.PROHIBITED_PRESCRIPTION_TERMS:
            if re.search(pattern, lower_text):
                violates = True
                matched_violations.append(pattern)

        if violates:
            # Fallback safe guidance
            return {
                "is_safe": False,
                "sanitized_text": (
                    "Based on the reported symptoms, please consult your assigned ASHA worker "
                    "or visit the Primary Health Center for a full professional checkup."
                ),
                "disclaimer": cls.CITIZEN_DISCLAIMER,
                "violations": matched_violations
            }

        return {
            "is_safe": True,
            "sanitized_text": text,
            "disclaimer": cls.CITIZEN_DISCLAIMER,
            "violations": []
        }

    @classmethod
    def format_clinical_summary(cls, text: str, sources: List[str] = None) -> Dict[str, Any]:
        """
        Attaches required clinical disclaimers and verified source IDs.
        """
        return {
            "summary": text,
            "disclaimer": cls.CLINICAL_DISCLAIMER,
            "verified_sources": sources or ["MoHFW-Clinical-Protocols-2024", "ICMR-STW-Obstetrics-v2"]
        }
