import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app.models import CitizenProfile, SchemeModel, SchemeEligibilityProfileModel
from app.schemes.fact_mapper import map_citizen_to_facts
from app.schemes.engine import DeterministicEligibilityEngine, EvalResult, OutputStatus

client = TestClient(app)

def test_elderly_maharashtra_citizen_no_spurious_unknowns():
    """
    Scenario 1: A 62-year-old Maharashtra citizen does not produce UNKNOWN for known age/location fields.
    """
    db = SessionLocal()
    try:
        # Meena Bai (CP-005) is 62yo female in Kalyanpur, Maharashtra
        citizen = db.query(CitizenProfile).filter_by(id='CP-005').first()
        assert citizen is not None

        facts = map_citizen_to_facts(citizen)
        assert facts.get('age') == 62 or facts.get('age_years') == 62
        assert facts.get('state') == 'Maharashtra'
        assert facts.get('village_name') == 'Kalyanpur'

        # Check RBSK (0-18y) -> FALSE, CM-VAYOSHREE (>=65y) -> FALSE, Maternal -> FALSE
        schemes = db.query(SchemeModel).all()
        results = {}
        for sc in schemes:
            v = sc.versions[0]
            rs = v.rule_sets[0] if v.rule_sets else None
            out = DeterministicEligibilityEngine.evaluate_scheme(
                sc.scheme_id, sc.scheme_code, v.scheme_version_id, str(v.result_ceiling),
                rs.expression_json if rs else {}, facts
            )
            results[sc.scheme_code] = out

        # RBSK (requires 0-18) must evaluate to NOT_ELIGIBLE (known age 62), NOT MORE_INFO_REQUIRED!
        assert results['IN-NHM-RBSK-2']['status'] == OutputStatus.NOT_ELIGIBLE.value
        assert 'age_years' not in results['IN-NHM-RBSK-2']['missing_fields']

        # Maternal schemes must evaluate to NOT_ELIGIBLE (she is not pregnant)
        assert results['IN-MWCD-PMMVY-2']['status'] == OutputStatus.NOT_ELIGIBLE.value
        assert results['IN-NHM-JSY-MH']['status'] == OutputStatus.NOT_ELIGIBLE.value

        # Universal services must evaluate to SERVICE_AVAILABLE
        assert results['IN-DGHS-TELEMANAS']['status'] == OutputStatus.SERVICE_AVAILABLE.value
        assert results['IN-MOHFW-ESANJEEVANI']['status'] == OutputStatus.SERVICE_AVAILABLE.value
        assert results['IN-MOHFW-AAM']['status'] == OutputStatus.SERVICE_AVAILABLE.value

        # CM-Vayoshree requires age >= 65 on 2023-12-31, for 62yo age rule is FALSE -> NOT_ELIGIBLE
        assert results['MH-SJSA-CM-VAYOSHREE']['status'] == OutputStatus.NOT_ELIGIBLE.value
    finally:
        db.close()

def test_pregnant_citizen_evaluates_maternal_schemes():
    """
    Scenario 2: A pregnant citizen evaluates maternal schemes using existing maternal data.
    """
    db = SessionLocal()
    try:
        # Sunita Devi (CP-001) is 28yo pregnant
        citizen = db.query(CitizenProfile).filter_by(id='CP-001').first()
        assert citizen is not None

        facts = map_citizen_to_facts(citizen)
        assert facts.get('is_pregnant') is True
        assert facts.get('pregnancy') is True
        assert facts.get('pregnancy_or_lactation') is True

        # JSSK is a universal entitlement for pregnant women in Govt hospitals -> SERVICE_AVAILABLE
        sc_jssk = db.query(SchemeModel).filter_by(scheme_code='IN-NHM-JSSK-MH').first()
        v_jssk = sc_jssk.versions[0]
        out_jssk = DeterministicEligibilityEngine.evaluate_scheme(
            sc_jssk.scheme_id, sc_jssk.scheme_code, v_jssk.scheme_version_id, str(v_jssk.result_ceiling),
            v_jssk.rule_sets[0].expression_json, facts
        )
        assert out_jssk['status'] == OutputStatus.SERVICE_AVAILABLE.value

        # PMSMA antenatal checkup service -> SERVICE_AVAILABLE
        sc_pmsma = db.query(SchemeModel).filter_by(scheme_code='IN-NHM-PMSMA').first()
        v_pmsma = sc_pmsma.versions[0]
        out_pmsma = DeterministicEligibilityEngine.evaluate_scheme(
            sc_pmsma.scheme_id, sc_pmsma.scheme_code, v_pmsma.scheme_version_id, str(v_pmsma.result_ceiling),
            v_pmsma.rule_sets[0].expression_json, facts
        )
        assert out_pmsma['status'] == OutputStatus.SERVICE_AVAILABLE.value

        # With BPL facts added, PMMVY & JSY must become LIKELY_ELIGIBLE
        facts_with_bpl = map_citizen_to_facts(citizen, {
            'has_bpl_ration_card': True,
            'social_category': 'SC',
            'social_category_or_bpl': 'BPL',
            'institutional_delivery_planned': True,
            'child_order': 1,
            'living_children_count': 0
        })

        sc_jsy = db.query(SchemeModel).filter_by(scheme_code='IN-NHM-JSY-MH').first()
        out_jsy = DeterministicEligibilityEngine.evaluate_scheme(
            sc_jsy.scheme_id, sc_jsy.scheme_code, sc_jsy.versions[0].scheme_version_id,
            str(sc_jsy.versions[0].result_ceiling), sc_jsy.versions[0].rule_sets[0].expression_json,
            facts_with_bpl
        )
        assert out_jsy['status'] == OutputStatus.LIKELY_ELIGIBLE.value

        sc_pmmvy = db.query(SchemeModel).filter_by(scheme_code='IN-MWCD-PMMVY-2').first()
        out_pmmvy = DeterministicEligibilityEngine.evaluate_scheme(
            sc_pmmvy.scheme_id, sc_pmmvy.scheme_code, sc_pmmvy.versions[0].scheme_version_id,
            str(sc_pmmvy.versions[0].result_ceiling), sc_pmmvy.versions[0].rule_sets[0].expression_json,
            facts_with_bpl
        )
        assert out_pmmvy['status'] == OutputStatus.LIKELY_ELIGIBLE.value
    finally:
        db.close()

def test_missing_income_produces_only_relevant_missing_fields():
    """
    Scenario 3: Missing income produces only the relevant missing-field result.
    """
    db = SessionLocal()
    try:
        # 68yo senior citizen with location & age, but missing income
        facts = {
            'state': 'Maharashtra',
            'age': 68,
            'age_years': 68,
            'age_on_2023_12_31': 68,
            'gender': 'FEMALE'
        }
        sc = db.query(SchemeModel).filter_by(scheme_code='MH-SJSA-CM-VAYOSHREE').first()
        out = DeterministicEligibilityEngine.evaluate_scheme(
            sc.scheme_id, sc.scheme_code, sc.versions[0].scheme_version_id,
            str(sc.versions[0].result_ceiling), sc.versions[0].rule_sets[0].expression_json,
            facts
        )
        assert out['status'] == OutputStatus.MORE_INFORMATION_REQUIRED.value
        assert 'annual_family_income' in out['missing_fields']
        # Age and state are known and should NOT be in missing_fields!
        assert 'age' not in out['missing_fields']
        assert 'state' not in out['missing_fields']
    finally:
        db.close()

def test_failed_mandatory_rule_returns_not_eligible():
    """
    Scenario 4: A failed mandatory rule returns NOT_ELIGIBLE.
    """
    db = SessionLocal()
    try:
        # Male citizen (Rameshwar Shinde CP-002, 54y Male)
        citizen = db.query(CitizenProfile).filter_by(id='CP-002').first()
        assert citizen is not None

        facts = map_citizen_to_facts(citizen)
        assert facts.get('gender') == 'MALE'

        # PMSMA requires pregnancy -> must be NOT_ELIGIBLE
        sc = db.query(SchemeModel).filter_by(scheme_code='IN-NHM-PMSMA').first()
        out = DeterministicEligibilityEngine.evaluate_scheme(
            sc.scheme_id, sc.scheme_code, sc.versions[0].scheme_version_id,
            str(sc.versions[0].result_ceiling), sc.versions[0].rule_sets[0].expression_json,
            facts
        )
        assert out['status'] == OutputStatus.NOT_ELIGIBLE.value
        assert len(out['failed_rules']) >= 1
    finally:
        db.close()

def test_universal_public_services_return_service_available():
    """
    Scenario 5: Universal services return SERVICE_AVAILABLE when applicable.
    """
    db = SessionLocal()
    try:
        facts = {'state': 'Maharashtra', 'district': 'District 04', 'village_name': 'Kalyanpur', 'age': 30, 'gender': 'FEMALE'}
        universal_codes = [
            'IN-DGHS-TELEMANAS', 'IN-MOHFW-ESANJEEVANI', 'IN-MOHFW-AAM',
            'IN-NHM-SUMAN', 'IN-DOP-PMBJP', 'IN-MOHFW-NACP', 'IN-NHM-NP-NCD'
        ]
        for code in universal_codes:
            sc = db.query(SchemeModel).filter_by(scheme_code=code).first()
            assert sc is not None, f"Scheme {code} not found in DB"
            out = DeterministicEligibilityEngine.evaluate_scheme(
                sc.scheme_id, sc.scheme_code, sc.versions[0].scheme_version_id,
                str(sc.versions[0].result_ceiling), sc.versions[0].rule_sets[0].expression_json,
                facts
            )
            assert out['status'] == OutputStatus.SERVICE_AVAILABLE.value, f"Scheme {code} was {out['status']}"
    finally:
        db.close()

def test_profile_update_and_immediate_reevaluation():
    """
    Scenario 6: Saving missing information changes results immediately.
    """
    citizen_id = "CP-003"
    db = SessionLocal()
    try:
        # Clean existing sep if any to start fresh
        existing_sep = db.query(SchemeEligibilityProfileModel).filter_by(citizen_id=citizen_id).first()
        if existing_sep:
            db.delete(existing_sep)
        cit = db.query(CitizenProfile).filter_by(id=citizen_id).first()
        cit.is_pregnant = True
        cit.household_category = "OTHER"
        cit.ration_card_category = "WHITE"
        db.commit()
    finally:
        db.close()

    # 1. Evaluate initially (pregnant citizen with no BPL / income -> PMMVY requires more info)
    res1 = client.post('/api/schemes/evaluate', json={'citizen_id': citizen_id, 'persist': False})
    assert res1.status_code == 200
    data1 = res1.json()
    pmmvy1 = next(r for r in data1['results'] if r['scheme_code'] == 'IN-MWCD-PMMVY-2')
    assert pmmvy1['status'] == 'MORE_INFORMATION_REQUIRED'

    # 2. Save profile facts via endpoint
    save_payload = {
        'facts': {
            'has_bpl_ration_card': True,
            'household_category': 'BPL',
            'ration_card_category': 'YELLOW',
            'social_category': 'SC',
            'social_category_or_bpl': 'BPL',
            'child_order': 1,
            'living_children_count': 0,
            'planned_delivery_facility_type': 'GOVERNMENT',
            'institutional_delivery_planned': True
        },
        'consent_obtained': True
    }
    res_save = client.post(f'/api/schemes/profile/{citizen_id}', json=save_payload)
    assert res_save.status_code == 200
    save_data = res_save.json()

    # PMMVY and JSY must immediately change to LIKELY_ELIGIBLE
    pmmvy_after = next(r for r in save_data['results'] if r['scheme_code'] == 'IN-MWCD-PMMVY-2')
    jsy_after = next(r for r in save_data['results'] if r['scheme_code'] == 'IN-NHM-JSY-MH')
    assert pmmvy_after['status'] == 'LIKELY_ELIGIBLE'
    assert jsy_after['status'] == 'LIKELY_ELIGIBLE'

def test_cross_portal_evaluation_consistency():
    """
    Scenario 7: Citizen and ASHA endpoints show consistent evaluation.
    """
    citizen_id = "CP-001"
    # ASHA evaluation
    asha_res = client.post('/api/schemes/evaluate', json={'citizen_id': citizen_id, 'persist': False})
    assert asha_res.status_code == 200
    asha_data = asha_res.json()

    # Citizen screening
    citizen_res = client.post('/api/citizen/schemes/screen', json={'is_pregnant': True})
    assert citizen_res.status_code == 200
    citizen_data = citizen_res.json()['data']

    # Both evaluate all 29 schemes
    assert asha_data['total_evaluated'] >= 29
    assert citizen_data['total_schemes_evaluated'] >= 29

    # Both return matching status for universal and maternal services
    asha_telemanas = next(r for r in asha_data['results'] if r['scheme_code'] == 'IN-DGHS-TELEMANAS')
    cit_telemanas = next(r for r in citizen_data['results'] if r['scheme_code'] == 'IN-DGHS-TELEMANAS')
    assert asha_telemanas['status'] == cit_telemanas['status'] == 'SERVICE_AVAILABLE'

    asha_jssk = next(r for r in asha_data['results'] if r['scheme_code'] == 'IN-NHM-JSSK-MH')
    cit_jssk = next(r for r in citizen_data['results'] if r['scheme_code'] == 'IN-NHM-JSSK-MH')
    assert asha_jssk['status'] == cit_jssk['status'] == 'SERVICE_AVAILABLE'
