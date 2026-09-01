import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from app.database import get_db
from app.models import (
    SchemeModel, SchemeVersionModel, SchemeEvaluationModel,
    SchemeEvaluationResultModel, SchemeVerificationModel, SourceDocumentModel,
    CitizenProfile, User, EligibilityOutputEnum, SchemeEligibilityProfileModel
)
from app.dependencies import get_current_user, get_optional_user
from app.schemes.engine import DeterministicEligibilityEngine
from app.schemes.fact_mapper import map_citizen_to_facts
from app.schemes.explanation import generate_scheme_explanation

router = APIRouter(prefix='/schemes', tags=['Government Schemes'])

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

# -------------------------------------------------------------
# Request & Response Schemas
# -------------------------------------------------------------

class SchemeEvaluateRequest(BaseModel):
    citizen_id: Optional[str] = None
    case_id: Optional[str] = None
    additional_facts: Optional[Dict[str, Any]] = None
    locale: Optional[str] = 'mr-IN'
    persist: Optional[bool] = True

class SchemeVerificationRequest(BaseModel):
    citizen_id: str
    scheme_code: str
    verification_method: str
    verification_reference: str
    notes: Optional[str] = None

class ProfileSaveRequest(BaseModel):
    facts: Dict[str, Any]
    consent_obtained: Optional[bool] = True
    notes: Optional[str] = None

QUESTION_CATALOG: Dict[str, Dict[str, Any]] = {
    'age': {'label': 'Citizen Age (Years)', 'category': 'Demographics', 'type': 'number', 'min': 0, 'max': 120},
    'age_years': {'label': 'Citizen Age (Years)', 'category': 'Demographics', 'type': 'number', 'min': 0, 'max': 120},
    'gender': {'label': 'Gender', 'category': 'Demographics', 'type': 'select', 'options': ['FEMALE', 'MALE', 'OTHER']},
    'sex': {'label': 'Gender', 'category': 'Demographics', 'type': 'select', 'options': ['FEMALE', 'MALE', 'OTHER']},
    'state': {'label': 'State of Residence', 'category': 'Demographics', 'type': 'text'},
    'district': {'label': 'District', 'category': 'Demographics', 'type': 'text'},
    'village_name': {'label': 'Village / Locality', 'category': 'Demographics', 'type': 'text'},
    'area_type': {'label': 'Area Type', 'category': 'Demographics', 'type': 'select', 'options': ['RURAL', 'URBAN']},
    
    # Maternal & Child
    'is_pregnant': {'label': 'Is Citizen Currently Pregnant?', 'category': 'Maternal & Child', 'type': 'boolean'},
    'pregnancy': {'label': 'Is Citizen Currently Pregnant?', 'category': 'Maternal & Child', 'type': 'boolean'},
    'pregnancy_or_lactation': {'label': 'Is Citizen Pregnant or Lactating?', 'category': 'Maternal & Child', 'type': 'boolean'},
    'gestational_weeks': {'label': 'Gestational Age (Weeks)', 'category': 'Maternal & Child', 'type': 'number', 'min': 1, 'max': 42},
    'is_lactating': {'label': 'Currently Lactating / Nursing?', 'category': 'Maternal & Child', 'type': 'boolean'},
    'postpartum_days': {'label': 'Days Since Childbirth', 'category': 'Maternal & Child', 'type': 'number', 'min': 0, 'max': 365},
    'child_order': {'label': 'Current Child Order (1st, 2nd, etc.)', 'category': 'Maternal & Child', 'type': 'number', 'min': 1, 'max': 10},
    'living_children_count': {'label': 'Number of Living Children', 'category': 'Maternal & Child', 'type': 'number', 'min': 0, 'max': 10},
    'second_child_gender': {'label': 'Gender of Second Child', 'category': 'Maternal & Child', 'type': 'select', 'options': ['FEMALE', 'MALE']},
    'planned_delivery_facility_type': {'label': 'Planned Delivery Location', 'category': 'Maternal & Child', 'type': 'select', 'options': ['GOVERNMENT', 'JSY_ACCREDITED_PRIVATE', 'PRIVATE', 'HOME']},
    'institutional_delivery_planned': {'label': 'Institutional Delivery Planned (PHC/Govt Hospital)?', 'category': 'Maternal & Child', 'type': 'boolean'},
    'is_tribal_woman': {'label': 'Is Citizen a Scheduled Tribe (ST) Woman?', 'category': 'Maternal & Child', 'type': 'boolean'},

    # Economic & Social
    'social_category': {'label': 'Social / Caste Category', 'category': 'Economic & Social', 'type': 'select', 'options': ['SC', 'ST', 'OBC', 'GENERAL']},
    'social_category_or_bpl': {'label': 'Category or BPL Status', 'category': 'Economic & Social', 'type': 'select', 'options': ['BPL', 'SC', 'ST', 'OBC', 'GENERAL']},
    'household_category': {'label': 'Household Economic Category', 'category': 'Economic & Social', 'type': 'select', 'options': ['BPL', 'ANTYODAYA', 'AAY', 'PRIORITY', 'OTHER']},
    'ration_card_category': {'label': 'Ration Card Color/Type', 'category': 'Economic & Social', 'type': 'select', 'options': ['YELLOW', 'ORANGE', 'WHITE', 'BPL', 'AAY']},
    'has_bpl_ration_card': {'label': 'Holds Yellow / BPL Ration Card?', 'category': 'Economic & Social', 'type': 'boolean'},
    'has_nfsa_ration_card': {'label': 'Holds NFSA / Priority Household Card?', 'category': 'Economic & Social', 'type': 'boolean'},
    'bpl_card_holder': {'label': 'Is BPL Card Holder?', 'category': 'Economic & Social', 'type': 'boolean'},
    'annual_family_income': {'label': 'Annual Family Income (₹ INR)', 'category': 'Economic & Social', 'type': 'number', 'min': 0},
    'net_family_income_annual': {'label': 'Net Annual Family Income (₹ INR)', 'category': 'Economic & Social', 'type': 'number', 'min': 0},

    # Welfare & Identity Cards
    'has_disability': {'label': 'Has Recognized Disability?', 'category': 'Welfare & Cards', 'type': 'boolean'},
    'disability_percent': {'label': 'Disability Percentage (e.g. 40%+)', 'category': 'Welfare & Cards', 'type': 'number', 'min': 0, 'max': 100},
    'is_pmjay_beneficiary': {'label': 'Enrolled in Ayushman PM-JAY / Has Card?', 'category': 'Welfare & Cards', 'type': 'boolean'},
    'has_e_shram_card': {'label': 'Registered with e-Shram Card?', 'category': 'Welfare & Cards', 'type': 'boolean'},
    'has_mgnrega_job_card': {'label': 'Holds Active MGNREGA Job Card?', 'category': 'Welfare & Cards', 'type': 'boolean'},
    'is_pm_kisan_woman_beneficiary': {'label': 'Receives PM-KISAN Assistance?', 'category': 'Welfare & Cards', 'type': 'boolean'},
    'is_pregnant_lactating_aww_awh_asha': {'label': 'Is ASHA / Anganwadi Worker/Helper?', 'category': 'Welfare & Cards', 'type': 'boolean'},
    'has_aadhaar': {'label': 'Has Aadhaar Card Available?', 'category': 'Welfare & Cards', 'type': 'boolean'},
    'received_same_equipment_free_from_government_within_3_years': {'label': 'Received same assistive aid free within 3 years?', 'category': 'Welfare & Cards', 'type': 'boolean'},

    # Health & Disease Programs
    'suspected_tb': {'label': 'Suspected TB Symptoms (cough >2 weeks)?', 'category': 'Health Screening', 'type': 'boolean'},
    'diagnosed_tb': {'label': 'Diagnosed with Tuberculosis (TB)?', 'category': 'Health Screening', 'type': 'boolean'},
    'diagnosed_and_notified_tb': {'label': 'Registered on Nikshay Portal for TB?', 'category': 'Health Screening', 'type': 'boolean'},
    'suspected_or_diagnosed_leprosy': {'label': 'Suspected or Diagnosed Leprosy?', 'category': 'Health Screening', 'type': 'boolean'},
    'is_sick_infant': {'label': 'Sick infant under 1 year requiring inpatient care?', 'category': 'Health Screening', 'type': 'boolean'},
}

def calculate_profile_completeness(facts: Dict[str, Any]) -> int:
    core_fields = [
        'age', 'gender', 'state', 'district', 'village_name',
        'is_pregnant', 'social_category', 'household_category',
        'has_bpl_ration_card', 'annual_family_income', 'has_disability',
        'has_aadhaar', 'has_e_shram_card', 'has_mgnrega_job_card'
    ]
    filled = 0
    for f in core_fields:
        val = facts.get(f)
        if val is not None and val != "":
            filled += 1
    return min(100, int((filled / len(core_fields)) * 100))

# -------------------------------------------------------------
# Endpoints
# -------------------------------------------------------------

@router.get('')
def get_schemes(
    category: Optional[str] = None,
    state: Optional[str] = None,
    db: Session = Depends(get_db)
):
    schemes = db.query(SchemeModel).all()
    res = []
    for s in schemes:
        latest_v = s.versions[0] if s.versions else None
        v_payload = latest_v.version_payload if latest_v else {}
        res.append({
            'scheme_id': s.scheme_id,
            'scheme_code': s.scheme_code,
            'canonical_name': s.canonical_name,
            'short_name': s.short_name or s.scheme_code,
            'category_codes': s.category_codes or [],
            'description': latest_v.description if latest_v else '',
            'benefits': v_payload.get('benefits', []),
            'required_documents': v_payload.get('required_documents', []),
            'application_steps': v_payload.get('application_steps', []),
            'official_information_url': latest_v.official_information_url if latest_v else None,
            'official_application_url': latest_v.official_application_url if latest_v else None
        })
    return {'status': 'SUCCESS', 'count': len(res), 'schemes': res}

@router.get('/{scheme_id}')
def get_scheme_detail(scheme_id: str, db: Session = Depends(get_db)):
    scheme = db.query(SchemeModel).filter((SchemeModel.scheme_id == scheme_id) | (SchemeModel.scheme_code == scheme_id)).first()
    if not scheme:
        raise HTTPException(status_code=404, detail='Scheme not found')
    latest_v = scheme.versions[0] if scheme.versions else None
    v_payload = latest_v.version_payload if latest_v else {}
    return {
        'status': 'SUCCESS',
        'scheme': {
            'scheme_id': scheme.scheme_id,
            'scheme_code': scheme.scheme_code,
            'canonical_name': scheme.canonical_name,
            'short_name': scheme.short_name or scheme.scheme_code,
            'category_codes': scheme.category_codes or [],
            'description': latest_v.description if latest_v else '',
            'benefits': v_payload.get('benefits', []),
            'required_documents': v_payload.get('required_documents', []),
            'application_steps': v_payload.get('application_steps', []),
            'official_information_url': latest_v.official_information_url if latest_v else None,
            'official_application_url': latest_v.official_application_url if latest_v else None,
            'version_payload': v_payload
        }
    }

@router.post('/evaluate')
def evaluate_schemes(
    req: SchemeEvaluateRequest,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    citizen = None
    if req.citizen_id:
        try:
            citizen = db.query(CitizenProfile).filter_by(id=req.citizen_id).first()
        except Exception:
            citizen = None

    facts = map_citizen_to_facts(citizen, req.additional_facts)
    completeness = calculate_profile_completeness(facts)
    schemes = db.query(SchemeModel).all()

    eval_results = []
    eval_model = None
    if req.persist and current_user:
        eval_model = SchemeEvaluationModel(
            citizen_id=req.citizen_id,
            case_id=req.case_id,
            evaluator_user_id=current_user.id,
            evaluator_role=current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role),
            normalized_fact_hash=f"FACTS_{str(uuid.uuid4())[:8]}",
            input_facts_json=facts
        )
        db.add(eval_model)
        db.flush()

    counts = {
        'LIKELY_ELIGIBLE': 0,
        'SERVICE_AVAILABLE': 0,
        'OFFICIAL_VERIFICATION_REQUIRED': 0,
        'POTENTIALLY_ELIGIBLE': 0,
        'MORE_INFORMATION_REQUIRED': 0,
        'NOT_ELIGIBLE': 0
    }

    all_missing_fields_set = set()

    for sc in schemes:
        if not sc.versions:
            continue
        v = sc.versions[0]
        rule_set = v.rule_sets[0] if v.rule_sets else None
        expr = rule_set.expression_json if rule_set else {}
        v_payload = v.version_payload or {}

        eval_out = DeterministicEligibilityEngine.evaluate_scheme(
            scheme_id=sc.scheme_id,
            scheme_code=sc.scheme_code,
            scheme_version_id=v.scheme_version_id,
            result_ceiling=str(v.result_ceiling),
            expression=expr,
            facts=facts
        )

        st = eval_out['status']
        counts[st] = counts.get(st, 0) + 1

        for mf in eval_out.get('missing_fields', []):
            all_missing_fields_set.add(mf)

        expl = generate_scheme_explanation(eval_out, facts, req.locale)
        eval_out['explanation'] = expl['explanation']
        eval_out['canonical_name'] = sc.canonical_name
        eval_out['short_name'] = sc.short_name or sc.scheme_code
        eval_out['category_codes'] = sc.category_codes or []
        eval_out['description'] = v.description
        eval_out['benefits'] = v_payload.get('benefits', [])
        eval_out['required_documents'] = v_payload.get('required_documents', [])
        eval_out['application_steps'] = v_payload.get('application_steps', [])
        eval_out['help_centers'] = v_payload.get('help_centers', ['ASHA Worker / Arogya Mitra', 'Primary Health Centre (PHC)'])
        eval_out['official_information_url'] = v.official_information_url
        eval_out['official_application_url'] = v.official_application_url
        eval_out['last_verified'] = v_payload.get('freshness', {}).get('last_verified', '2026-08-25')

        if req.persist and eval_model:
            r_record = SchemeEvaluationResultModel(
                evaluation_id=eval_model.evaluation_id,
                scheme_id=sc.scheme_id,
                scheme_code=sc.scheme_code,
                scheme_version_id=v.scheme_version_id,
                status=eval_out['status'],
                explanation=expl['explanation'],
                matched_rules_json=eval_out['matched_rules'],
                failed_rules_json=eval_out['failed_rules'],
                unknown_rules_json=eval_out['unknown_rules'],
                missing_fields_json=eval_out['missing_fields'],
                official_urls_json={'info': v.official_information_url, 'app': v.official_application_url}
            )
            db.add(r_record)

        eval_results.append(eval_out)

    if req.persist and eval_model:
        db.commit()

    return {
        'status': 'SUCCESS',
        'evaluation_id': eval_model.evaluation_id if eval_model else None,
        'citizen_id': req.citizen_id,
        'profile_completeness': completeness,
        'evaluated_at': utc_now().isoformat(),
        'summary_counts': {
            'eligible_or_service': counts['LIKELY_ELIGIBLE'] + counts['SERVICE_AVAILABLE'] + counts['OFFICIAL_VERIFICATION_REQUIRED'] + counts['POTENTIALLY_ELIGIBLE'],
            'likely_eligible': counts['LIKELY_ELIGIBLE'],
            'service_available': counts['SERVICE_AVAILABLE'],
            'official_verification_required': counts['OFFICIAL_VERIFICATION_REQUIRED'],
            'potentially_eligible': counts['POTENTIALLY_ELIGIBLE'],
            'more_information_required': counts['MORE_INFORMATION_REQUIRED'],
            'not_eligible': counts['NOT_ELIGIBLE'],
            'total_evaluated': len(eval_results)
        },
        'missing_fields_aggregated': sorted(list(all_missing_fields_set)),
        'total_evaluated': len(eval_results),
        'results': eval_results
    }

@router.get('/profile/{citizen_id}')
def get_citizen_eligibility_profile(
    citizen_id: str,
    db: Session = Depends(get_db)
):
    citizen = db.query(CitizenProfile).filter_by(id=citizen_id).first()
    if not citizen:
        raise HTTPException(status_code=404, detail='Citizen profile not found')

    facts = map_citizen_to_facts(citizen)
    completeness = calculate_profile_completeness(facts)
    sep = db.query(SchemeEligibilityProfileModel).filter_by(citizen_id=citizen_id).first()

    return {
        'status': 'SUCCESS',
        'citizen_id': citizen_id,
        'citizen_name': citizen.display_name,
        'facts': facts,
        'completeness_percent': completeness,
        'field_provenance': sep.field_provenance_json if sep else {},
        'consent_obtained': sep.consent_obtained if sep else True,
        'last_updated_at': sep.updated_at.isoformat() if (sep and sep.updated_at) else citizen.updated_at.isoformat()
    }

@router.post('/profile/{citizen_id}')
def update_citizen_eligibility_profile(
    citizen_id: str,
    req: ProfileSaveRequest,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    citizen = db.query(CitizenProfile).filter_by(id=citizen_id).first()
    if not citizen:
        raise HTTPException(status_code=404, detail='Citizen profile not found')

    sep = db.query(SchemeEligibilityProfileModel).filter_by(citizen_id=citizen_id).first()
    now_iso = utc_now().isoformat()
    current_user_id = current_user.id if current_user else "ASHA_WORKER"

    if not sep:
        sep = SchemeEligibilityProfileModel(
            citizen_id=citizen_id,
            captured_by_user_id=current_user_id,
            consent_obtained=req.consent_obtained if req.consent_obtained is not None else True,
            field_provenance_json={},
            extra_facts_json={}
        )
        db.add(sep)
        db.flush()

    provenance = dict(sep.field_provenance_json or {})
    extra_facts = dict(sep.extra_facts_json or {})

    # Sync fields to sep and citizen
    for k, v in req.facts.items():
        if v is None:
            continue
        provenance[k] = {
            'source': 'ASHA_CAPTURED' if (current_user and 'ASHA' in str(getattr(current_user, 'role', ''))) else 'STAFF_VERIFIED',
            'captured_by': current_user_id,
            'updated_at': now_iso
        }

        # Map to columns on SchemeEligibilityProfileModel if available
        if hasattr(sep, k):
            setattr(sep, k, v)
        else:
            extra_facts[k] = v

        # Mirror core fields back to CitizenProfile
        if k in ('age', 'age_years', 'age_estimate'):
            try:
                citizen.age_estimate = int(v)
            except Exception:
                pass
        elif k == 'is_pregnant':
            citizen.is_pregnant = bool(v)
        elif k == 'gestational_weeks':
            try:
                citizen.gestational_weeks = int(v)
            except Exception:
                pass
        elif k in ('gender', 'sex'):
            citizen.sex = str(v).upper()
        elif k == 'household_category':
            citizen.household_category = str(v).upper()
        elif k == 'ration_card_category':
            citizen.ration_card_category = str(v).upper()

    sep.field_provenance_json = provenance
    sep.extra_facts_json = extra_facts
    sep.consent_obtained = req.consent_obtained if req.consent_obtained is not None else sep.consent_obtained
    sep.updated_at = utc_now()
    citizen.updated_at = utc_now()

    db.commit()

    # Re-evaluate all schemes immediately with updated facts
    eval_req = SchemeEvaluateRequest(
        citizen_id=citizen_id,
        locale='mr-IN',
        persist=True
    )
    return evaluate_schemes(eval_req, db, current_user)

@router.get('/questionnaire/{citizen_id}')
def get_missing_questionnaire(
    citizen_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    citizen = db.query(CitizenProfile).filter_by(id=citizen_id).first()
    if not citizen:
        raise HTTPException(status_code=404, detail='Citizen profile not found')

    eval_req = SchemeEvaluateRequest(citizen_id=citizen_id, persist=False)
    eval_res = evaluate_schemes(eval_req, db, current_user)
    missing_fields_map: Dict[str, List[str]] = {}

    for r in eval_res.get('results', []):
        sc_name = r.get('short_name') or r.get('canonical_name') or r.get('scheme_code')
        for mf in r.get('missing_fields', []):
            if mf not in missing_fields_map:
                missing_fields_map[mf] = []
            missing_fields_map[mf].append(sc_name)

    facts = map_citizen_to_facts(citizen)
    grouped_questions: Dict[str, List[Dict[str, Any]]] = {
        'Demographics': [],
        'Maternal & Child': [],
        'Economic & Social': [],
        'Welfare & Cards': [],
        'Health Screening': [],
        'Other': []
    }

    for field_name, required_by_schemes in missing_fields_map.items():
        q_meta = QUESTION_CATALOG.get(field_name, {
            'label': field_name.replace('_', ' ').title(),
            'category': 'Other',
            'type': 'text'
        })
        category = q_meta.get('category', 'Other')
        curr_val = facts.get(field_name)

        q_item = {
            'field': field_name,
            'label': q_meta.get('label'),
            'type': q_meta.get('type', 'text'),
            'options': q_meta.get('options'),
            'min': q_meta.get('min'),
            'max': q_meta.get('max'),
            'current_value': curr_val,
            'required_by_schemes': required_by_schemes,
            'explanation': f"Required for {', '.join(required_by_schemes[:3])}{' and others' if len(required_by_schemes) > 3 else ''}."
        }

        if category not in grouped_questions:
            grouped_questions[category] = []
        grouped_questions[category].append(q_item)

    # Filter out empty categories
    active_grouped = {k: v for k, v in grouped_questions.items() if len(v) > 0}

    return {
        'status': 'SUCCESS',
        'citizen_id': citizen_id,
        'citizen_name': citizen.display_name,
        'total_missing_fields': len(missing_fields_map),
        'grouped_questions': active_grouped
    }

@router.post('/verification')
def record_verification(
    req: SchemeVerificationRequest,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    v = SchemeVerificationModel(
        citizen_id=req.citizen_id,
        scheme_code=req.scheme_code,
        verification_status=EligibilityOutputEnum.VERIFIED_ELIGIBLE,
        verification_method=req.verification_method,
        verification_reference=req.verification_reference,
        verified_by_user_id=current_user.id if current_user else "STAFF_VERIFIED",
        notes=req.notes
    )
    db.add(v)
    db.commit()
    return {'status': 'SUCCESS', 'verification_id': v.verification_id, 'message': 'Official verification recorded successfully'}

@router.post('/admin/populate-catalog')
def populate_schemes_catalog(db: Session = Depends(get_db)):
    """
    Admin maintenance endpoint to populate / sync the government health schemes catalog knowledge base into PostgreSQL.
    """
    from app.schemes.import_kb import import_knowledge_base
    try:
        import_knowledge_base(db_session=db)
        count = db.query(SchemeModel).count()
        return {
            'status': 'SUCCESS',
            'message': f'Successfully populated government schemes knowledge base. Total schemes: {count}',
            'total_schemes': count
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f'Failed to populate schemes catalog: {e}')
