import pytest
from app.ai.pii.masker import PIIMasker
from app.ai.orchestrator.orchestrator import orchestrator_service
from app.ai.providers.gemini_service import gemini_service

def test_pii_masking_strips_sensitive_data():
    raw_prompt = "Sunita Devi from Kalyanpur, phone 9876543210 and ABHA 12-3456-7890-1234 has severe headache."
    masked, tokens = PIIMasker.mask_text(
        text=raw_prompt,
        citizen_name="Sunita Devi",
        phone="9876543210",
        abha="12-3456-7890-1234"
    )
    
    assert "Sunita Devi" not in masked
    assert "9876543210" not in masked
    assert "12-3456-7890-1234" not in masked
    assert "[CITIZEN_1]" in masked
    assert "[PHONE_REDACTED]" in masked
    assert "[ABHA_REDACTED]" in masked

def test_multi_agent_orchestrator_execution_order_and_critique():
    # Sunita Devi canonical clinical case
    result = orchestrator_service.orchestrate(
        raw_text="माझे डोके खूप दुखत आहे आणि डोळ्यांसमोर अंधारी येत आहे (Severe headache and blurred vision)",
        citizen_name="Sunita Devi",
        phone="9876543210",
        abha="12-3456-7890-1234",
        preferred_language="mr-IN",
        systolic_bp=150,
        diastolic_bp=100,
        is_pregnant=True,
        gestational_weeks=28
    )

    # 1. Verify structured intake
    assert result.intake is not None
    assert result.intake.is_pregnant is True
    assert len(result.intake.symptoms) >= 1

    # 2. Verify clinical evidence citations
    assert result.evidence_summary is not None
    assert len(result.evidence_summary.guideline_citations) >= 1
    assert any("pre-eclampsia" in n.lower() or "warning" in n.lower() or "pregnant" in n.lower() for n in result.evidence_summary.safety_notes)

    # 3. Verify scheme recommendations
    assert len(result.schemes) >= 1
    jsy = next((s for s in result.schemes if s.scheme_code == "JSY"), None)
    assert jsy is not None

    # 4. Verify Safety Critic validation
    assert result.critique.is_safe is True
    assert result.critique.human_confirmation_mandated is True
    assert result.critique.contains_unauthorized_diagnosis is False
    assert result.critique.contains_unauthorized_prescription is False
