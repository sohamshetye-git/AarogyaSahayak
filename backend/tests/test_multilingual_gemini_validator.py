import pytest
from app.ai.providers.gemini_service import gemini_service
from app.ai.contracts.schemas import CitizenUnderstandingOutput, CitizenIntentEnum, ContextTransitionEnum, CitizenNewFacts

LOCALES = [
    "en-IN", "hi-IN", "mr-IN", "gu-IN", "bn-IN",
    "kn-IN", "te-IN", "ta-IN", "ml-IN", "pa-IN", "od-IN"
]

def test_script_validator_all_locales():
    """Validates that _validate_response_script accurately detects native Indic scripts and rejects mismatched scripts."""
    # Test positive matches
    assert gemini_service._validate_response_script("Hello! How can I help you today?", "en-IN") is True
    assert gemini_service._validate_response_script("नमस्ते! मैं आपकी क्या सहायता कर सकता हूँ?", "hi-IN") is True
    assert gemini_service._validate_response_script("नमस्कार! मी आपली काय मदत करू शकतो?", "mr-IN") is True
    assert gemini_service._validate_response_script("નમસ્તે! હું તમને કેવી રીતે મદદ કરી શકું?", "gu-IN") is True
    assert gemini_service._validate_response_script("নমস্কার! আমি আপনাকে কীভাবে সাহায্য করতে পারি?", "bn-IN") is True
    assert gemini_service._validate_response_script("ನಮಸ್ಕಾರ! ನಾನು ನಿಮಗೆ ಹೇಗೆ ಸಹಾಯ ಮಾಡಬಹುದು?", "kn-IN") is True
    assert gemini_service._validate_response_script("నమస్కారం! నేను మీకు ఎలా సహాయపడగలను?", "te-IN") is True
    assert gemini_service._validate_response_script("வணக்கம்! நான் உங்களுக்கு எப்படி உதவ முடியும்?", "ta-IN") is True
    assert gemini_service._validate_response_script("നമസ്കാരം! ഞാൻ നിങ്ങളെ എങ്ങനെ സഹായിക്കും?", "ml-IN") is True
    assert gemini_service._validate_response_script("ਸਤ ਸ੍ਰੀ ਅਕਾਲ! ਮੈਂ ਤੁਹਾਡੀ ਕਿਵੇਂ ਮਦਦ ਕਰ ਸਕਦਾ ਹਾਂ?", "pa-IN") is True
    assert gemini_service._validate_response_script("ନମସ୍କାର! ମୁଁ ଆପଣଙ୍କୁ କିପରି ସାହାଯ୍ୟ କରିପାରିବି?", "od-IN") is True

    # Test negative matches (English text in non-English locales)
    for loc in [l for l in LOCALES if not l.startswith("en")]:
        assert gemini_service._validate_response_script("This is pure English text without any Indic script.", loc) is False

def test_fallback_dynamic_response_all_11_locales():
    """Validates that fallback responses for all 11 locales return native language without English fallback."""
    understanding = CitizenUnderstandingOutput(
        intent=CitizenIntentEnum.GENERAL_CONVERSATION,
        context_transition=ContextTransitionEnum.NEW_TOPIC,
        detected_language="en",
        citizen_goal="General health query",
        new_facts=CitizenNewFacts(),
        recommended_response_goal="ACKNOWLEDGE_AND_RESPOND",
        confidence=0.9
    )

    for loc in LOCALES:
        resp = gemini_service._fallback_dynamic_response(
            latest_message="Hello",
            understanding=understanding,
            safety_evaluation={"level": "NORMAL", "reason": None, "triggered": False},
            verified_tool_data=None,
            language=loc
        )
        assert resp.language == loc
        assert len(resp.text) > 0
        assert gemini_service._validate_response_script(resp.text, loc) is True
        assert len(resp.requested_action_types) > 0
        assert len(resp.suggested_replies) > 0

def test_emergency_fallback_all_11_locales():
    """Validates emergency fallback messages for all 11 locales."""
    understanding = CitizenUnderstandingOutput(
        intent=CitizenIntentEnum.EMERGENCY_HELP,
        context_transition=ContextTransitionEnum.NEW_TOPIC,
        detected_language="en",
        citizen_goal="Chest pain",
        new_facts=CitizenNewFacts(symptoms=["Chest Pain"]),
        recommended_response_goal="EMERGENCY_ALERT",
        confidence=1.0
    )

    for loc in LOCALES:
        resp = gemini_service._fallback_dynamic_response(
            latest_message="Chest pain",
            understanding=understanding,
            safety_evaluation={"level": "EMERGENCY", "reason": "Chest pain warning", "triggered": True},
            verified_tool_data=None,
            language=loc
        )
        assert resp.language == loc
        assert resp.response_type == "SAFETY_WARNING"
        assert "108" in resp.text or "१०८" in resp.text or "૧૦૮" in resp.text or "১০৮" in resp.text or "೧೦೮" in resp.text or "౧౦౮" in resp.text or "൧൦൮" in resp.text or "੧੦੮" in resp.text or "୧୦୮" in resp.text
        assert "CALL_108" in resp.requested_action_types
        assert gemini_service._validate_response_script(resp.text, loc) is True
