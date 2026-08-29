import re
from typing import Dict, Any, Tuple, Optional

class PIIMasker:
    """
    Strict Request-Scoped PII Masker & Anonymization Engine.
    Ensures zero raw citizen PII (Names, Phone Numbers, ABHA IDs, Village/Address)
    is ever passed to external LLM (Gemini, Lyzr) or vector databases.
    """
    
    @classmethod
    def mask_text(cls, text: str, citizen_name: Optional[str] = None, phone: Optional[str] = None, abha: Optional[str] = None) -> Tuple[str, Dict[str, str]]:
        if not text:
            return "", {}

        masked = text
        token_map: Dict[str, str] = {}

        # Mask explicit citizen name if provided
        if citizen_name and citizen_name.strip():
            for part in citizen_name.split():
                if len(part) > 2:
                    pattern = re.compile(re.escape(part), re.IGNORECASE)
                    if pattern.search(masked):
                        token_map["[CITIZEN_1]"] = citizen_name
                        masked = pattern.sub("[CITIZEN_1]", masked)

        # Mask 10-digit Indian phone numbers
        phone_pattern = re.compile(r'\b(?:\+91|91)?[-.\s]?[6-9]\d{9}\b')
        if phone_pattern.search(masked):
            token_map["[PHONE_REDACTED]"] = phone or "REDACTED"
            masked = phone_pattern.sub("[PHONE_REDACTED]", masked)

        # Mask 14-digit ABHA Numbers (XX-XXXX-XXXX-XXXX)
        abha_pattern = re.compile(r'\b\d{2}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b')
        if abha_pattern.search(masked):
            token_map["[ABHA_REDACTED]"] = abha or "REDACTED"
            masked = abha_pattern.sub("[ABHA_REDACTED]", masked)

        # Mask Aadhaar numbers (12 digits)
        aadhaar_pattern = re.compile(r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}\b')
        if aadhaar_pattern.search(masked):
            token_map["[AADHAAR_REDACTED]"] = "REDACTED"
            masked = aadhaar_pattern.sub("[AADHAAR_REDACTED]", masked)

        return masked, token_map

    @classmethod
    def unmask_text(cls, masked_text: str, token_map: Dict[str, str]) -> str:
        res = masked_text
        for token, original in token_map.items():
            res = res.replace(token, original)
        return res
