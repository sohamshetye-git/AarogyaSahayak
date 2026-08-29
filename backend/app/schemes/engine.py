from typing import Any, Dict, List, Tuple, Set, Optional
from enum import Enum
from datetime import date, datetime

class EvalResult(str, Enum):
    TRUE = 'TRUE'
    FALSE = 'FALSE'
    UNKNOWN = 'UNKNOWN'

class OutputStatus(str, Enum):
    SERVICE_AVAILABLE = 'SERVICE_AVAILABLE'
    LIKELY_ELIGIBLE = 'LIKELY_ELIGIBLE'
    POTENTIALLY_ELIGIBLE = 'POTENTIALLY_ELIGIBLE'
    MORE_INFORMATION_REQUIRED = 'MORE_INFORMATION_REQUIRED'
    OFFICIAL_VERIFICATION_REQUIRED = 'OFFICIAL_VERIFICATION_REQUIRED'
    VERIFIED_ELIGIBLE = 'VERIFIED_ELIGIBLE'
    NOT_ELIGIBLE = 'NOT_ELIGIBLE'

def eval_and(results: List[EvalResult]) -> EvalResult:
    if any(r == EvalResult.FALSE for r in results):
        return EvalResult.FALSE
    if all(r == EvalResult.TRUE for r in results):
        return EvalResult.TRUE
    return EvalResult.UNKNOWN

def eval_or(results: List[EvalResult]) -> EvalResult:
    if any(r == EvalResult.TRUE for r in results):
        return EvalResult.TRUE
    if all(r == EvalResult.FALSE for r in results):
        return EvalResult.FALSE
    return EvalResult.UNKNOWN

def eval_not(result: EvalResult) -> EvalResult:
    if result == EvalResult.TRUE:
        return EvalResult.FALSE
    if result == EvalResult.FALSE:
        return EvalResult.TRUE
    return EvalResult.UNKNOWN

def get_nested(facts: Dict[str, Any], path: Optional[str]) -> Tuple[bool, Any]:
    if not path:
        return False, None
    parts = path.split('.')
    curr = facts
    for p in parts:
        if not isinstance(curr, dict) or p not in curr:
            return False, None
        curr = curr[p]
    if curr is None:
        return False, None
    return True, curr

def parse_comparable_date(val: Any) -> Optional[datetime]:
    if isinstance(val, (datetime, date)):
        if isinstance(val, date) and not isinstance(val, datetime):
            return datetime(val.year, val.month, val.day)
        return val
    if isinstance(val, str):
        for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f", "%d/%m/%Y"):
            try:
                return datetime.strptime(val[:10] if "T" not in fmt else val, fmt)
            except Exception:
                pass
    return None

def eval_atom(rule: Dict[str, Any], facts: Dict[str, Any]) -> EvalResult:
    field = rule.get('field')
    op = rule.get('operator')
    expected = rule.get('value')
    found, actual = get_nested(facts, field)
    if not found:
        return EvalResult.UNKNOWN

    try:
        if op == 'equals':
            if isinstance(expected, bool) or isinstance(actual, bool):
                return EvalResult.TRUE if bool(actual) == bool(expected) else EvalResult.FALSE
            if isinstance(expected, (int, float)) and isinstance(actual, (int, float, str)):
                try:
                    return EvalResult.TRUE if float(actual) == float(expected) else EvalResult.FALSE
                except (ValueError, TypeError):
                    pass
            if isinstance(expected, str) and isinstance(actual, str):
                return EvalResult.TRUE if actual.strip().lower() == expected.strip().lower() else EvalResult.FALSE
            return EvalResult.TRUE if actual == expected else EvalResult.FALSE

        elif op == 'not_equals':
            if isinstance(expected, bool) or isinstance(actual, bool):
                return EvalResult.FALSE if bool(actual) == bool(expected) else EvalResult.TRUE
            if isinstance(expected, (int, float)) and isinstance(actual, (int, float, str)):
                try:
                    return EvalResult.FALSE if float(actual) == float(expected) else EvalResult.TRUE
                except (ValueError, TypeError):
                    pass
            if isinstance(expected, str) and isinstance(actual, str):
                return EvalResult.FALSE if actual.strip().lower() == expected.strip().lower() else EvalResult.TRUE
            return EvalResult.FALSE if actual == expected else EvalResult.TRUE

        elif op == 'in':
            if isinstance(expected, list):
                if isinstance(actual, str):
                    act = actual.strip().lower()
                    exps = [str(x).strip().lower() for x in expected]
                    return EvalResult.TRUE if act in exps else EvalResult.FALSE
                return EvalResult.TRUE if actual in expected else EvalResult.FALSE
            return EvalResult.FALSE

        elif op == 'not_in':
            if isinstance(expected, list):
                if isinstance(actual, str):
                    act = actual.strip().lower()
                    exps = [str(x).strip().lower() for x in expected]
                    return EvalResult.FALSE if act in exps else EvalResult.TRUE
                return EvalResult.FALSE if actual in expected else EvalResult.TRUE
            return EvalResult.FALSE

        elif op in ('gt', 'greater_than'):
            return EvalResult.TRUE if float(actual) > float(expected) else EvalResult.FALSE

        elif op in ('gte', 'greater_than_or_equal'):
            return EvalResult.TRUE if float(actual) >= float(expected) else EvalResult.FALSE

        elif op in ('lt', 'less_than'):
            return EvalResult.TRUE if float(actual) < float(expected) else EvalResult.FALSE

        elif op in ('lte', 'less_than_or_equal'):
            return EvalResult.TRUE if float(actual) <= float(expected) else EvalResult.FALSE

        elif op == 'between':
            if isinstance(expected, list) and len(expected) == 2:
                return EvalResult.TRUE if (float(expected[0]) <= float(actual) <= float(expected[1])) else EvalResult.FALSE
            return EvalResult.FALSE

        elif op == 'contains':
            if isinstance(actual, list):
                return EvalResult.TRUE if expected in actual or any(str(x).lower() == str(expected).lower() for x in actual) else EvalResult.FALSE
            if isinstance(actual, str) and isinstance(expected, str):
                return EvalResult.TRUE if expected.lower() in actual.lower() else EvalResult.FALSE
            return EvalResult.FALSE

        elif op == 'exists':
            return EvalResult.TRUE if actual is not None else EvalResult.FALSE

        elif op == 'date_before':
            act_d = parse_comparable_date(actual)
            exp_d = parse_comparable_date(expected)
            if act_d and exp_d:
                return EvalResult.TRUE if act_d < exp_d else EvalResult.FALSE
            return EvalResult.UNKNOWN

        elif op == 'date_after':
            act_d = parse_comparable_date(actual)
            exp_d = parse_comparable_date(expected)
            if act_d and exp_d:
                return EvalResult.TRUE if act_d > exp_d else EvalResult.FALSE
            return EvalResult.UNKNOWN

    except Exception:
        return EvalResult.FALSE

    return EvalResult.UNKNOWN

def eval_node(node: Dict[str, Any], facts: Dict[str, Any], matched: List[str], failed: List[str], unknown: List[str], missing: Set[str]) -> EvalResult:
    if not isinstance(node, dict) or not node:
        return EvalResult.TRUE

    # Unwrap top-level envelope if present
    if 'rule' in node and ('enabled' in node or 'result_ceiling' in node):
        return eval_node(node['rule'], facts, matched, failed, unknown, missing)

    rule_id = node.get('rule_id') or node.get('source_assertion_id', 'RULE')
    label = node.get('label') or node.get('field', 'Rule')

    if 'all' in node:
        res = eval_and([eval_node(c, facts, matched, failed, unknown, missing) for c in node['all']])
    elif 'any' in node:
        res = eval_or([eval_node(c, facts, matched, failed, unknown, missing) for c in node['any']])
    elif 'not' in node:
        res = eval_not(eval_node(node['not'], facts, matched, failed, unknown, missing))
    elif 'if' in node and 'then' in node:
        if_res = eval_node(node['if'], facts, matched, failed, unknown, missing)
        if if_res == EvalResult.TRUE:
            res = eval_node(node['then'], facts, matched, failed, unknown, missing)
        elif if_res == EvalResult.FALSE:
            if 'else' in node:
                res = eval_node(node['else'], facts, matched, failed, unknown, missing)
            else:
                res = EvalResult.TRUE
        else:
            # If condition is UNKNOWN, missing fields have been recorded by if branch
            # Also evaluate branches to gather potential missing fields
            eval_node(node['then'], facts, [], [], [], missing)
            if 'else' in node:
                eval_node(node['else'], facts, [], [], [], missing)
            res = EvalResult.UNKNOWN
    else:
        # Atomic rule
        if 'field' in node:
            res = eval_atom(node, facts)
            if res == EvalResult.UNKNOWN:
                missing.add(node['field'])
        else:
            # Empty / non-rule node
            return EvalResult.TRUE

    desc = f"{rule_id}: {label}" if label else str(rule_id)
    if res == EvalResult.TRUE and 'field' in node:
        matched.append(desc)
    elif res == EvalResult.FALSE and 'field' in node:
        failed.append(desc)
    elif res == EvalResult.UNKNOWN and 'field' in node:
        unknown.append(desc)

    return res

class DeterministicEligibilityEngine:
    @staticmethod
    def evaluate_scheme(
        scheme_id: str,
        scheme_code: str,
        scheme_version_id: str,
        result_ceiling: str,
        expression: Dict[str, Any],
        facts: Dict[str, Any],
        official_verification_required: bool = False
    ) -> Dict[str, Any]:
        matched: List[str] = []
        failed: List[str] = []
        unknown: List[str] = []
        missing: Set[str] = set()

        expr = expression or {}
        ceiling = result_ceiling or expr.get('result_ceiling', 'LIKELY_ELIGIBLE')
        if ceiling.startswith('EligibilityOutputEnum.'):
            ceiling = ceiling.split('.')[-1]

        # Check if screening is explicitly disabled (Universal public service or Registry gate)
        if expr.get('enabled') is False:
            if ceiling == 'SERVICE_AVAILABLE':
                status = OutputStatus.SERVICE_AVAILABLE
                matched.append("Universal Public-Health Service: Available to all citizens in implementation areas")
            elif ceiling == 'OFFICIAL_VERIFICATION_REQUIRED':
                status = OutputStatus.OFFICIAL_VERIFICATION_REQUIRED
                matched.append("Official Registry Gate: Entitlement verified via BIS / official beneficiary portal")
            elif ceiling == 'POTENTIALLY_ELIGIBLE':
                status = OutputStatus.POTENTIALLY_ELIGIBLE
                matched.append("Discretionary Grant: Case-by-case medical and hospital sanction required")
            else:
                status = OutputStatus.LIKELY_ELIGIBLE

            return {
                'scheme_id': scheme_id,
                'scheme_code': scheme_code,
                'scheme_version_id': scheme_version_id,
                'status': status.value,
                'matched_rules': matched,
                'failed_rules': failed,
                'unknown_rules': unknown,
                'missing_fields': sorted(list(missing)),
                'disclaimer': 'Preliminary deterministic evaluation. Official verification is required.'
            }

        # Otherwise, evaluate deterministic rule tree
        rule_tree = expr.get('rule', expr)
        final_res = eval_node(rule_tree, facts, matched, failed, unknown, missing)

        if final_res == EvalResult.FALSE:
            status = OutputStatus.NOT_ELIGIBLE
        elif final_res == EvalResult.UNKNOWN:
            status = OutputStatus.MORE_INFORMATION_REQUIRED
        else:
            # All mandatory conditions evaluated to TRUE
            if ceiling == 'SERVICE_AVAILABLE':
                status = OutputStatus.SERVICE_AVAILABLE
            elif ceiling == 'OFFICIAL_VERIFICATION_REQUIRED' or official_verification_required:
                status = OutputStatus.OFFICIAL_VERIFICATION_REQUIRED
            elif ceiling == 'POTENTIALLY_ELIGIBLE':
                status = OutputStatus.POTENTIALLY_ELIGIBLE
            else:
                status = OutputStatus.LIKELY_ELIGIBLE

        return {
            'scheme_id': scheme_id,
            'scheme_code': scheme_code,
            'scheme_version_id': scheme_version_id,
            'status': status.value,
            'matched_rules': matched,
            'failed_rules': failed,
            'unknown_rules': unknown,
            'missing_fields': sorted(list(missing)),
            'disclaimer': 'Preliminary deterministic evaluation. Official verification is required.'
        }
