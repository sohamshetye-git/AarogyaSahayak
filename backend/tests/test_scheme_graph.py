import pytest
from app.ai.graph.scheme_graph import scheme_graph_service

def test_jsy_scheme_matching_for_pregnant_citizen():
    # Sunita Devi scenario: Pregnant woman in rural Kalyanpur
    results = scheme_graph_service.evaluate_eligibility(
        is_pregnant=True,
        state="Maharashtra",
        area_type="RURAL",
        bpl_card_holder=None
    )
    assert len(results) >= 1
    
    jsy = next((s for s in results if s["scheme_code"] == "JSY"), None)
    assert jsy is not None
    assert jsy["status"] == "POTENTIALLY_ELIGIBLE"
    assert "₹1,400" in jsy["benefit_summary"]
    assert "Mother & Child Protection (MCP) Card" in jsy["required_documents"]
    assert "Kalyanpur Primary Health Center" in jsy["empanelled_facilities"]
    assert jsy["confidence_score"] >= 0.90

def test_pmjay_scheme_requires_bpl_info():
    # Without BPL information, status must be MORE_INFORMATION_REQUIRED
    results = scheme_graph_service.evaluate_eligibility(
        is_pregnant=False,
        state="Maharashtra",
        area_type="RURAL",
        bpl_card_holder=None
    )
    pmjay = next((s for s in results if s["scheme_code"] == "PMJAY"), None)
    assert pmjay is not None
    assert pmjay["status"] == "MORE_INFORMATION_REQUIRED"
    assert len(pmjay["missing_information"]) > 0

def test_pmjay_eligible_with_bpl_confirmation():
    results = scheme_graph_service.evaluate_eligibility(
        is_pregnant=False,
        state="Maharashtra",
        area_type="RURAL",
        bpl_card_holder=True
    )
    pmjay = next((s for s in results if s["scheme_code"] == "PMJAY"), None)
    assert pmjay is not None
    assert pmjay["status"] == "POTENTIALLY_ELIGIBLE"
    assert pmjay["confidence_score"] == 0.85
