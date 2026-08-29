import re
from typing import Tuple, Dict

class PIIMaskingService:
    """
    Detects and masks Personally Identifiable Information (PII) 
    before sending text to any external LLM or third-party service.
    """

    # Aadhaar (12 digits, optional dashes/spaces)
    AADHAAR_PATTERN = r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}\b"
    
    # ABHA ID (14 digits or xx-xxxx-xxxx-xxxx format)
    ABHA_PATTERN = r"\b\d{2}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b"
    
    # Indian Phone numbers (10 digits, optional +91 or 0 prefix)
    PHONE_PATTERN = r"(?:\+91[-\s]?|0)?[6-9]\d{9}\b"

    @classmethod
    def mask_text(cls, text: str, citizen_name: str = None) -> Tuple[str, Dict[str, str]]:
        """
        Masks names, phone numbers, Aadhaar, and ABHA numbers.
        Returns:
            (masked_text, replacement_map)
        """
        masked = text
        mapping: Dict[str, str] = {}
        counter = 1

        # Mask ABHA / Aadhaar
        for match in re.finditer(cls.ABHA_PATTERN, masked):
            placeholder = f"[ABHA_MASKED_{counter}]"
            mapping[placeholder] = match.group(0)
            masked = masked.replace(match.group(0), placeholder)
            counter += 1

        for match in re.finditer(cls.AADHAAR_PATTERN, masked):
            placeholder = f"[AADHAAR_MASKED_{counter}]"
            mapping[placeholder] = match.group(0)
            masked = masked.replace(match.group(0), placeholder)
            counter += 1

        # Mask Phone numbers
        for match in re.finditer(cls.PHONE_PATTERN, masked):
            placeholder = f"[PHONE_MASKED_{counter}]"
            mapping[placeholder] = match.group(0)
            masked = masked.replace(match.group(0), placeholder)
            counter += 1

        # Mask citizen name if provided
        if citizen_name and len(citizen_name.strip()) > 2:
            name_pattern = re.compile(re.escape(citizen_name.strip()), re.IGNORECASE)
            placeholder = "[CITIZEN_NAME]"
            mapping[placeholder] = citizen_name
            masked = name_pattern.sub(placeholder, masked)

        return masked, mapping

    @staticmethod
    def mask_phone(phone: str) -> str:
        if not phone or len(phone.strip()) < 10:
            return phone or ""
        clean = phone.strip()
        return clean[:2] + "XXXXXX" + clean[-2:]

    @staticmethod
    def mask_abha(abha: str) -> str:
        if not abha or len(abha.strip()) < 8:
            return abha or ""
        clean = abha.strip()
        return clean[:2] + "-XXXX-XXXX-" + clean[-4:]

