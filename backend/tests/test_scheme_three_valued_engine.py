import pytest
from app.schemes.engine import DeterministicEligibilityEngine, EvalResult, OutputStatus, eval_node

def test_missing_facts_become_unknown():
    # Rule requires age and state
    rule = {
        'all': [
            {'field': 'age', 'operator': 'gte', 'value': 18, 'rule_id': 'R1', 'label': 'Age 18+'},
            {'field': 'state', 'operator': 'equals', 'value': 'Maharashtra', 'rule_id': 'R2', 'label': 'MH Resident'}
        ]
    }
    matched, failed, unknown, missing = [], [], [], set()
    facts = {} # Empty facts - missing age and state
    res = eval_node(rule, facts, matched, failed, unknown, missing)

    assert res == EvalResult.UNKNOWN
    assert 'age' in missing
    assert 'state' in missing

def test_unknown_does_not_become_false():
    rule = {'field': 'is_pregnant', 'operator': 'equals', 'value': True, 'rule_id': 'R1'}
    matched, failed, unknown, missing = [], [], [], set()
    facts = {} # Not specified
    res = eval_node(rule, facts, matched, failed, unknown, missing)

    assert res == EvalResult.UNKNOWN
    assert res != EvalResult.FALSE

def test_all_any_not_logic():
    rule_all = {
        'all': [
            {'field': 'is_pregnant', 'operator': 'equals', 'value': True},
            {'field': 'age', 'operator': 'gte', 'value': 18}
        ]
    }
    # One true, one missing -> UNKNOWN for ALL
    m, f, u, miss = [], [], [], set()
    assert eval_node(rule_all, {'is_pregnant': True}, m, f, u, miss) == EvalResult.UNKNOWN

    # One true, one false -> FALSE for ALL
    m, f, u, miss = [], [], [], set()
    assert eval_node(rule_all, {'is_pregnant': True, 'age': 15}, m, f, u, miss) == EvalResult.FALSE

    # One true -> TRUE for ANY
    rule_any = {
        'any': [
            {'field': 'is_pregnant', 'operator': 'equals', 'value': True},
            {'field': 'age', 'operator': 'gte', 'value': 60}
        ]
    }
    m, f, u, miss = [], [], [], set()
    assert eval_node(rule_any, {'is_pregnant': True}, m, f, u, miss) == EvalResult.TRUE

def test_operators():
    facts = {'num': 10, 'text': 'hello', 'arr': ['A', 'B']}
    m, f, u, miss = [], [], [], set()

    assert eval_node({'field': 'num', 'operator': 'equals', 'value': 10}, facts, m, f, u, miss) == EvalResult.TRUE
    assert eval_node({'field': 'num', 'operator': 'gt', 'value': 5}, facts, m, f, u, miss) == EvalResult.TRUE
    assert eval_node({'field': 'num', 'operator': 'between', 'value': [5, 15]}, facts, m, f, u, miss) == EvalResult.TRUE
    assert eval_node({'field': 'text', 'operator': 'contains', 'value': 'ell'}, facts, m, f, u, miss) == EvalResult.TRUE
    assert eval_node({'field': 'arr', 'operator': 'in', 'value': ['A']}, facts, m, f, u, miss) == EvalResult.FALSE
    assert eval_node({'field': 'arr', 'operator': 'contains', 'value': 'A'}, facts, m, f, u, miss) == EvalResult.TRUE

def test_gemini_cannot_alter_deterministic_output():
    out = DeterministicEligibilityEngine.evaluate_scheme(
        scheme_id='S1', scheme_code='JSY', scheme_version_id='V1',
        result_ceiling='LIKELY_ELIGIBLE',
        expression={'field': 'is_pregnant', 'operator': 'equals', 'value': True},
        facts={'is_pregnant': True}
    )
    assert out['status'] == OutputStatus.LIKELY_ELIGIBLE.value
    assert out['status'] != OutputStatus.VERIFIED_ELIGIBLE.value
    assert 'Official verification is required' in out['disclaimer']

    # For PM-JAY registry gate
    out_pmjay = DeterministicEligibilityEngine.evaluate_scheme(
        scheme_id='S2', scheme_code='IN-NHA-PMJAY', scheme_version_id='V1',
        result_ceiling='OFFICIAL_VERIFICATION_REQUIRED',
        expression={'enabled': False, 'result_ceiling': 'OFFICIAL_VERIFICATION_REQUIRED'},
        facts={'has_aadhaar': True}
    )
    assert out_pmjay['status'] == OutputStatus.OFFICIAL_VERIFICATION_REQUIRED.value
