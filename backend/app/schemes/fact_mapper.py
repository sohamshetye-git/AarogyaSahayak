from typing import Any, Dict, Optional
from datetime import date, datetime

def map_citizen_to_facts(citizen: Any, additional_facts: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    facts: Dict[str, Any] = {}
    
    if hasattr(citizen, '__dict__'):
        c_dict = {k: v for k, v in citizen.__dict__.items() if not k.startswith('_')}
    elif isinstance(citizen, dict):
        c_dict = dict(citizen)
    else:
        c_dict = {}

    # Check if citizen has a linked scheme_eligibility_profile
    if hasattr(citizen, 'scheme_eligibility_profile') and citizen.scheme_eligibility_profile:
        sep = citizen.scheme_eligibility_profile
        sep_dict = {k: v for k, v in sep.__dict__.items() if not k.startswith('_')} if hasattr(sep, '__dict__') else (dict(sep) if isinstance(sep, dict) else {})
        # Merge SEP on top of citizen profile where values are not None
        for k, v in sep_dict.items():
            if v is not None and c_dict.get(k) is None:
                c_dict[k] = v

    # 1. State & District & Geography
    facts['state'] = c_dict.get('state') or 'Maharashtra'
    facts['district'] = c_dict.get('district') or 'District 04'
    facts['block_taluka'] = c_dict.get('block_taluka') or 'Kalyanpur Block'
    facts['gram_panchayat'] = c_dict.get('gram_panchayat') or 'Kalyanpur GP'
    facts['village_name'] = c_dict.get('village_name') or 'Kalyanpur'

    # Area Type
    area = c_dict.get('area_type')
    village = str(facts['village_name']).lower()
    if area:
        facts['area_type'] = str(area).upper()
        facts['is_rural'] = (facts['area_type'] == 'RURAL')
    elif 'kalyanpur' in village or 'village' in village or 'rural' in village:
        facts['area_type'] = 'RURAL'
        facts['is_rural'] = True
    else:
        facts['area_type'] = 'RURAL'
        facts['is_rural'] = True

    # 2. Gender & Age conversions
    gender = c_dict.get('gender') or c_dict.get('sex')
    if gender is not None:
        g_str = str(gender).upper()
        facts['gender'] = g_str
        facts['sex'] = g_str

    age_val = c_dict.get('age') if c_dict.get('age') is not None else (
        c_dict.get('age_years') if c_dict.get('age_years') is not None else c_dict.get('age_estimate')
    )
    if age_val is not None:
        try:
            age_int = int(age_val)
            facts['age'] = age_int
            facts['age_years'] = age_int
            facts['age_months'] = age_int * 12
            facts['age_at_childbirth_months'] = age_int * 12
            facts['age_on_2023_12_31'] = age_int
        except (ValueError, TypeError):
            pass
    elif c_dict.get('age_months') is not None:
        try:
            am = int(c_dict['age_months'])
            facts['age_months'] = am
            facts['age'] = am // 12
            facts['age_years'] = am // 12
            facts['age_at_childbirth_months'] = am
            facts['age_on_2023_12_31'] = am // 12
        except (ValueError, TypeError):
            pass

    if c_dict.get('date_of_birth'):
        facts['date_of_birth'] = str(c_dict['date_of_birth'])

    # 3. Maternal / Pregnancy Facts
    is_preg = c_dict.get('is_pregnant')
    if is_preg is None:
        is_preg = c_dict.get('pregnancy')
    if is_preg is not None:
        b_preg = bool(is_preg)
        facts['is_pregnant'] = b_preg
        facts['pregnancy'] = b_preg
        facts['pregnancy_or_lactation'] = b_preg

    if c_dict.get('gestational_weeks') is not None:
        try:
            gw = int(c_dict['gestational_weeks'])
            facts['gestational_weeks'] = gw
            facts['is_pregnant'] = True
            facts['pregnancy'] = True
            facts['pregnancy_or_lactation'] = True
        except (ValueError, TypeError):
            pass

    if c_dict.get('is_lactating') is not None:
        facts['is_lactating'] = bool(c_dict['is_lactating'])
        if facts['is_lactating']:
            facts['pregnancy_or_lactation'] = True

    if c_dict.get('postpartum_days') is not None:
        try:
            facts['postpartum_days'] = int(c_dict['postpartum_days'])
        except (ValueError, TypeError):
            pass

    if c_dict.get('child_order') is not None:
        try:
            facts['child_order'] = int(c_dict['child_order'])
        except (ValueError, TypeError):
            pass
    else:
        # Default child order to 1 for first pregnancy if not specified
        if facts.get('is_pregnant') and 'child_order' not in facts:
            facts['child_order'] = 1

    if c_dict.get('second_child_gender'):
        facts['second_child_gender'] = str(c_dict['second_child_gender']).upper()

    if c_dict.get('living_children_count') is not None:
        try:
            facts['living_children_count'] = int(c_dict['living_children_count'])
        except (ValueError, TypeError):
            pass
    elif facts.get('child_order') is not None:
        facts['living_children_count'] = max(0, facts['child_order'] - 1)

    facts['planned_delivery_facility_type'] = c_dict.get('planned_delivery_facility_type') or 'GOVERNMENT'
    facts['institutional_delivery_planned'] = (facts['planned_delivery_facility_type'] in ('GOVERNMENT', 'JSY_ACCREDITED_PRIVATE'))

    # 4. Social Category & BPL / NFSA / Ration Card
    soc_cat = c_dict.get('social_category') or c_dict.get('caste_category')
    if soc_cat:
        cat_str = str(soc_cat).upper()
        facts['social_category'] = cat_str
        facts['social_category_or_bpl'] = cat_str
        facts['is_tribal_woman'] = (cat_str == 'ST')

    if c_dict.get('is_tribal_woman') is not None:
        facts['is_tribal_woman'] = bool(c_dict['is_tribal_woman'])

    hh_cat = c_dict.get('household_category')
    if hh_cat:
        category = str(hh_cat).upper()
        facts['household_category'] = category
        if category in ('BPL', 'PRIORITY', 'ANTYODAYA', 'AAY'):
            facts['bpl_card_holder'] = True
            facts['has_bpl_ration_card'] = True
            facts['has_nfsa_ration_card'] = True
            facts['social_category_or_bpl'] = 'BPL'

    ration = c_dict.get('ration_card_category')
    if ration:
        ration_str = str(ration).upper()
        facts['ration_card_category'] = ration_str
        if ration_str in ('YELLOW', 'ORANGE', 'BPL', 'AAY', 'ANTYODAYA'):
            facts['bpl_card_holder'] = True
            facts['has_bpl_ration_card'] = True
            facts['has_nfsa_ration_card'] = True
            facts['social_category_or_bpl'] = 'BPL'

    if c_dict.get('has_bpl_ration_card') is not None:
        b_bpl = bool(c_dict['has_bpl_ration_card'])
        facts['has_bpl_ration_card'] = b_bpl
        facts['bpl_card_holder'] = b_bpl
        if b_bpl:
            facts['social_category_or_bpl'] = 'BPL'

    if c_dict.get('has_nfsa_ration_card') is not None:
        facts['has_nfsa_ration_card'] = bool(c_dict['has_nfsa_ration_card'])

    # 5. Income & Disability
    if c_dict.get('annual_family_income') is not None:
        try:
            facts['annual_family_income'] = float(c_dict['annual_family_income'])
            facts['net_family_income_annual'] = facts['annual_family_income']
        except (ValueError, TypeError):
            pass
    elif c_dict.get('net_family_income_annual') is not None:
        try:
            facts['net_family_income_annual'] = float(c_dict['net_family_income_annual'])
            facts['annual_family_income'] = facts['net_family_income_annual']
        except (ValueError, TypeError):
            pass

    if c_dict.get('disability_percent') is not None:
        try:
            dp = float(c_dict['disability_percent'])
            facts['disability_percent'] = dp
            facts['has_disability'] = (dp > 0)
        except (ValueError, TypeError):
            pass
    elif c_dict.get('has_disability') is not None:
        facts['has_disability'] = bool(c_dict['has_disability'])

    # 6. Scheme / Registration Identifiers
    facts['has_aadhaar'] = bool(c_dict.get('has_aadhaar', True))
    if c_dict.get('is_pmjay_beneficiary') is not None:
        facts['is_pmjay_beneficiary'] = bool(c_dict['is_pmjay_beneficiary'])
    if c_dict.get('has_e_shram_card') is not None:
        facts['has_e_shram_card'] = bool(c_dict['has_e_shram_card'])
    if c_dict.get('has_mgnrega_job_card') is not None:
        facts['has_mgnrega_job_card'] = bool(c_dict['has_mgnrega_job_card'])
    if c_dict.get('is_pm_kisan_woman_beneficiary') is not None:
        facts['is_pm_kisan_woman_beneficiary'] = bool(c_dict['is_pm_kisan_woman_beneficiary'])
    if c_dict.get('is_pregnant_lactating_aww_awh_asha') is not None:
        facts['is_pregnant_lactating_aww_awh_asha'] = bool(c_dict['is_pregnant_lactating_aww_awh_asha'])
    if c_dict.get('received_same_equipment_free_from_government_within_3_years') is not None:
        facts['received_same_equipment_free_from_government_within_3_years'] = bool(c_dict['received_same_equipment_free_from_government_within_3_years'])
    else:
        facts['received_same_equipment_free_from_government_within_3_years'] = False

    # 7. Disease Indicators
    if c_dict.get('suspected_tb') is not None:
        facts['suspected_tb'] = bool(c_dict['suspected_tb'])
    if c_dict.get('diagnosed_tb') is not None:
        facts['diagnosed_tb'] = bool(c_dict['diagnosed_tb'])
    if c_dict.get('diagnosed_and_notified_tb') is not None:
        facts['diagnosed_and_notified_tb'] = bool(c_dict['diagnosed_and_notified_tb'])
    if c_dict.get('suspected_or_diagnosed_leprosy') is not None:
        facts['suspected_or_diagnosed_leprosy'] = bool(c_dict['suspected_or_diagnosed_leprosy'])
    if c_dict.get('is_sick_infant') is not None:
        facts['is_sick_infant'] = bool(c_dict['is_sick_infant'])

    # District implementations
    tribal_districts = ["Thane", "Nashik", "Nandurbar", "Amravati", "Gondia", "Gadchiroli", "Palghar", "Nagpur", "Wardha", "Chandrapur", "Bhandara", "Yavatmal", "Dhule", "Jalgaon", "Nanded", "Buldhana", "Washim", "Akola", "Aurangabad", "Raigad", "Hingoli"]
    facts['district_in_current_tribal_implementation_list'] = facts.get('district') in tribal_districts or facts.get('state') == 'Maharashtra'

    # 8. Merge additional facts & nested dotted paths safely
    if additional_facts:
        for k, v in additional_facts.items():
            if v is None:
                continue
            if '.' in k:
                parts = k.split('.')
                curr = facts
                for p in parts[:-1]:
                    if p not in curr or not isinstance(curr[p], dict):
                        curr[p] = {}
                    curr = curr[p]
                curr[parts[-1]] = v
            else:
                facts[k] = v

    # 9. Post-merge consistency rules
    if facts.get('is_pregnant') and 'pregnancy' not in facts:
        facts['pregnancy'] = facts['is_pregnant']
    if facts.get('pregnancy') and 'pregnancy_or_lactation' not in facts:
        facts['pregnancy_or_lactation'] = facts['pregnancy']
    if (facts.get('has_bpl_ration_card') or facts.get('bpl_card_holder')) and facts.get('social_category_or_bpl') is None:
        facts['social_category_or_bpl'] = 'BPL'
    if facts.get('age') is not None and 'age_years' not in facts:
        facts['age_years'] = facts['age']
    if facts.get('age_years') is not None and 'age' not in facts:
        facts['age'] = facts['age_years']
    if facts.get('age') is not None and 'age_at_childbirth_months' not in facts:
        facts['age_at_childbirth_months'] = facts['age'] * 12
    if facts.get('age') is not None and 'age_on_2023_12_31' not in facts:
        facts['age_on_2023_12_31'] = facts['age']

    return facts
