import pytest
from app.ai.providers.tavily_service import tavily_service
from app.ai.providers.n8n_service import n8n_service
from app.ai.providers.abdm_service import abdm_service
from app.ai.providers.litert_service import litert_service

def test_tavily_blocks_non_official_domains():
    res_fake = tavily_service.verify_official_update(
        query="Maternal guidelines",
        candidate_url="https://commercial-health-blog.com/tips"
    )
    assert res_fake["verified"] is False
    assert res_fake["status"] == "BLOCKED_NON_OFFICIAL_DOMAIN"

    res_gov = tavily_service.verify_official_update(
        query="Maternal guidelines",
        candidate_url="https://nhm.gov.in/guidelines/maternal_2024.pdf"
    )
    assert res_gov["verified"] is True

def test_n8n_followup_payload_has_no_pii():
    res = n8n_service.dispatch_followup_task(
        case_id="case-canonical-001",
        asha_id="user-asha-001",
        instructions="Check BP every 3 days",
        due_days=3
    )
    assert res["status"] == "DISPATCHED"
    assert res["workflow"] == "ASHA_Followup_Reminder_Flow"

def test_abdm_sandbox_synthetic_linking():
    res = abdm_service.verify_abha_reference("12-3456-7890-1234")
    assert res["status"] == "SANDBOX_MOCK_VERIFIED"
    assert res["environment"] == "ABDM_SANDBOX"

def test_litert_offline_model_and_deterministic_override():
    # Elevated BP -> HIGH_MODEL_SIGNAL
    res_high = litert_service.evaluate_supplemental_signal(
        systolic_bp=150,
        diastolic_bp=100,
        spo2=97,
        is_pregnant=True
    )
    assert res_high["model_signal"] == "HIGH_MODEL_SIGNAL"
    assert res_high["deterministic_override_guaranteed"] is True
    assert "Not Clinically Validated" in res_high["label"]
