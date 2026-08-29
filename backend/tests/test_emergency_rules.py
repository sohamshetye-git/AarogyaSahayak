from app.safety.emergency_rules import EmergencyRuleEvaluator
from app.models import CasePriorityEnum

def test_maternal_preeclampsia_rule():
    priority, rule_trig, reason, guidance = EmergencyRuleEvaluator.evaluate(
        symptoms=["blurred vision", "severe headache", "swollen feet"],
        is_pregnant=True,
        gestational_weeks=28,
        systolic_bp=150,
        diastolic_bp=100
    )
    assert priority == CasePriorityEnum.URGENT
    assert rule_trig is True
    assert "Pregnancy-related warning signs" in reason
    assert "Warning signs were detected" in guidance

def test_critical_chest_pain_rule():
    priority, rule_trig, reason, guidance = EmergencyRuleEvaluator.evaluate(
        symptoms=["chest pain", "sweating"],
        is_pregnant=False
    )
    assert priority == CasePriorityEnum.URGENT
    assert rule_trig is True
    assert "Chest Pain" in reason

def test_low_spo2_rule():
    priority, rule_trig, reason, guidance = EmergencyRuleEvaluator.evaluate(
        symptoms=["cough"],
        spo2=87
    )
    assert priority == CasePriorityEnum.URGENT
    assert rule_trig is True
    assert "oxygen" in reason.lower()

def test_routine_mild_cold():
    priority, rule_trig, reason, guidance = EmergencyRuleEvaluator.evaluate(
        symptoms=["mild cold", "running nose"],
        is_pregnant=False,
        systolic_bp=118,
        diastolic_bp=78
    )
    assert priority == CasePriorityEnum.ROUTINE
    assert rule_trig is False
