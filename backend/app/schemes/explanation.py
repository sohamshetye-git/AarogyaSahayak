from typing import Dict, Any
from app.ai.providers.gemini_service import gemini_service

def generate_scheme_explanation(
    evaluation_result: Dict[str, Any],
    citizen_facts: Dict[str, Any],
    locale: str = 'mr-IN'
) -> Dict[str, Any]:
    status = evaluation_result.get('status', 'MORE_INFORMATION_REQUIRED')
    matched = evaluation_result.get('matched_rules', [])
    missing = evaluation_result.get('missing_fields', [])
    scheme_code = evaluation_result.get('scheme_code', 'SCHEME')

    prompt = f'Scheme: {scheme_code}, Status: {status}, Matched: {matched}, Missing: {missing}'

    try:
        if gemini_service.is_live:
            res_text = gemini_service.generate_content(prompt)
            explanation = res_text.strip()
        else:
            missing_str = ', '.join(missing) if missing else 'None'
            explanation = f'Deterministic Result: {status}. Matched {len(matched)} criteria. Missing: {missing_str}. Official verification required.'
    except Exception:
        explanation = f'Deterministic Result: {status}. Matched {len(matched)} criteria. Official verification required.'

    return {
        'scheme_code': scheme_code,
        'status': status,
        'explanation': explanation,
        'locale': locale,
        'provider_mode': gemini_service.get_mode()
    }
