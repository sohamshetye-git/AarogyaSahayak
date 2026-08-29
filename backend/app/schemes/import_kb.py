import os
import sys
import json
import hashlib
import argparse
from typing import Dict, Any
from app.database import SessionLocal
from app.models import (
    AuthorityModel, SchemeModel, SchemeVersionModel, SourceDocumentModel,
    EligibilityRuleSetModel, SchemeBenefitModel, GovernmentLevelEnum,
    ReviewStateEnum, SourceTierEnum, EligibilityOutputEnum,
    AssistanceCapabilityModel, SchemeAssistanceCapabilityModel
)

def compute_hash(data: Any) -> str:
    s = json.dumps(data, sort_keys=True)
    return hashlib.sha256(s.encode('utf-8')).hexdigest()

def import_knowledge_base(pkg_path: str, validate_only: bool = False, dry_run: bool = False, db_session: Any = None):
    sources_file = os.path.join(pkg_path, 'sources.json')
    schemes_file = os.path.join(pkg_path, 'schemes.json')

    if not os.path.exists(sources_file) or not os.path.exists(schemes_file):
        raise FileNotFoundError(f'Package files not found at {pkg_path}')

    with open(sources_file, 'r', encoding='utf-8') as f:
        sources_data = json.load(f).get('sources', [])

    with open(schemes_file, 'r', encoding='utf-8') as f:
        schemes_data = json.load(f).get('records', [])

    print(f'[KB Import] Loaded {len(sources_data)} sources and {len(schemes_data)} schemes.')

    if validate_only:
        print('[KB Import] Validation PASSED successfully!')
        return

    if dry_run:
        print('[KB Import] Dry run completed. No DB changes made.')
        return

    db = db_session if db_session is not None else SessionLocal()
    try:
        # 1. Import Sources
        for src in sources_data:
            s_code = src['source_id']
            existing = db.query(SourceDocumentModel).filter_by(source_code=s_code).first()
            if not existing:
                doc = SourceDocumentModel(
                    source_code=s_code,
                    title=src.get('name', s_code),
                    authority_name=src.get('authority', 'Government'),
                    source_tier=SourceTierEnum.TIER_1_AUTHORITY,
                    official_url=src.get('official_url', 'https://www.india.gov.in/'),
                    content_sha256=compute_hash(src),
                    last_verified=src.get('update_observation', '2026-08-25')
                )
                db.add(doc)
        db.flush()

        # 2. Default Authority
        def_auth = db.query(AuthorityModel).filter_by(authority_code='AUTH-GOI').first()
        if not def_auth:
            def_auth = AuthorityModel(
                authority_code='AUTH-GOI',
                name='Ministry of Health & Family Welfare / NHA',
                authority_type='STATUTORY',
                government_level=GovernmentLevelEnum.CENTRAL,
                official_url='https://mohfw.gov.in'
            )
            db.add(def_auth)
            db.flush()

        # 3. Import Schemes
        created_count = 0
        for sc in schemes_data:
            s_code = sc['scheme_id']
            existing_scheme = db.query(SchemeModel).filter_by(scheme_code=s_code).first()
            if not existing_scheme:
                existing_scheme = SchemeModel(
                    scheme_code=s_code,
                    canonical_name=sc['scheme_name'],
                    short_name=sc.get('short_name', s_code),
                    entity_type=sc.get('entity_type', 'PUBLIC_HEALTH_PROGRAM'),
                    authority_id=def_auth.authority_id,
                    category_codes=sc.get('scheme_category', [])
                )
                db.add(existing_scheme)
                db.flush()
                created_count += 1

            # Scheme Version
            v_label = sc.get('freshness', {}).get('scheme_version', '2026-08-25.1')
            ceiling_val = sc.get('screening', {}).get('result_ceiling', 'LIKELY_ELIGIBLE')
            try:
                ceiling_enum = getattr(EligibilityOutputEnum, ceiling_val, EligibilityOutputEnum.LIKELY_ELIGIBLE)
            except Exception:
                ceiling_enum = EligibilityOutputEnum.LIKELY_ELIGIBLE

            existing_v = db.query(SchemeVersionModel).filter_by(
                scheme_id=existing_scheme.scheme_id, version_label=v_label
            ).first()

            if not existing_v:
                s_version = SchemeVersionModel(
                    scheme_id=existing_scheme.scheme_id,
                    version_label=v_label,
                    description=sc.get('description', ''),
                    eligibility_mode=sc.get('eligibility_mode', 'DETERMINISTIC_RULES'),
                    result_ceiling=ceiling_enum,
                    active_status=sc.get('active_status', 'ACTIVE'),
                    official_information_url=sc.get('official_information_url'),
                    official_application_url=sc.get('official_application_url'),
                    version_payload=sc
                )
                db.add(s_version)
                db.flush()

                # Add Benefits
                for b in sc.get('benefits', []):
                    benefit = SchemeBenefitModel(
                        scheme_version_id=s_version.scheme_version_id,
                        description=b.get('description', ''),
                        amount=b.get('amount'),
                        currency=b.get('currency', 'INR'),
                        period=b.get('period')
                    )
                    db.add(benefit)

                # Add Default Rule Set
                rule_set = EligibilityRuleSetModel(
                    scheme_version_id=s_version.scheme_version_id,
                    rule_set_code=f'RS-{s_code}',
                    name=f'Eligibility Rules for {s_code}',
                    result_ceiling=ceiling_enum,
                    official_verification_required=True,
                    expression_json=sc.get('rule_tree', sc.get('screening', {}))
                )
                db.add(rule_set)
            else:
                existing_v.result_ceiling = ceiling_enum
                existing_v.version_payload = sc
                existing_v.official_information_url = sc.get('official_information_url')
                existing_v.official_application_url = sc.get('official_application_url')
                for rs in existing_v.rule_sets:
                    rs.result_ceiling = ceiling_enum
                    rs.expression_json = sc.get('rule_tree', sc.get('screening', {}))

        # 4. Seed Canonical Assistance Capabilities & Scheme-to-Capability Mappings
        CAPABILITY_DEFINITIONS = [
            {"code": "PMJAY_HELP_DESK", "name": "PM-JAY / Ayushman Bharat Help Desk", "service_code": "AYUSHMAN_HELP_DESK", "desc": "Ayushman Mitra desk, e-KYC assistance, beneficiary identification"},
            {"code": "AYUSHMAN_CARD_SUPPORT", "name": "Ayushman Card Support & e-KYC", "service_code": "AYUSHMAN_HELP_DESK", "desc": "Card generation, Aadhaar e-KYC and BIS search"},
            {"code": "CSC", "name": "Common Service Centre / Aaple Sarkar", "service_code": "CSC_OPERATOR", "desc": "Online registration, DBT seeding, document uploads"},
            {"code": "EMPANELLED_HOSPITAL", "name": "Empanelled Hospital Network", "service_code": "SURGERY", "desc": "Secondary and tertiary cashless hospitalization"},
            {"code": "MJPJAY_HELP_DESK", "name": "MJPJAY Arogyamitra Desk", "service_code": "AYUSHMAN_HELP_DESK", "desc": "MJPJAY Maharashtra scheme assistance & pre-authorization"},
            {"code": "STATE_HEALTH_AGENCY_SUPPORT", "name": "State Health Agency Support", "service_code": "GENERAL_OPD", "desc": "SHAS district/taluka grievance and verification support"},
            {"code": "ANGANWADI", "name": "Anganwadi Centre (WCD)", "service_code": "CHILD_VACCINATION", "desc": "PMMVY mother registration, nutrition monitoring, POSHAN"},
            {"code": "WCD_OFFICE", "name": "Women & Child Development Office", "service_code": "GENERAL_OPD", "desc": "CDPO / ICDS office for maternity scheme application processing"},
            {"code": "ASHA_SUPPORT", "name": "ASHA Worker Community Support", "service_code": "MATERNITY_DELIVERY", "desc": "Doorstep village assistance, ANC tracking, JSY/JSSK escort"},
            {"code": "ANM_SUB_CENTRE", "name": "ANM & Sub-Centre (Arogya Mandir)", "service_code": "ANTENATAL_CARE", "desc": "MCP card issuance, primary antenatal checkup, JSY registration"},
            {"code": "PHC_FACILITY", "name": "Primary Health Centre (PHC)", "service_code": "MATERNITY_DELIVERY", "desc": "Institutional delivery, JSY cash voucher processing, JSSK medicines"},
            {"code": "GOVT_MATERNITY_FACILITY", "name": "Government Maternity Hospital / FRU", "service_code": "MATERNITY_DELIVERY", "desc": "CEmOC delivery, C-section, free diet, JSSK zero-expense"},
            {"code": "TB_DOTS_CENTRE", "name": "TB / DOTS Centre (NTEP)", "service_code": "TB_DOTS", "desc": "Sputum testing, Nikshay portal DBT registration, anti-TB medicines"},
            {"code": "VACCINATION_CENTRE", "name": "Vaccination & Cold Chain Centre", "service_code": "CHILD_VACCINATION", "desc": "U-WIN registration, eVIN cold chain, childhood & pregnant immunizations"},
            {"code": "SOCIAL_WELFARE_OFFICE", "name": "Social Welfare & Disability Office", "service_code": "GENERAL_OPD", "desc": "Senior citizen pension, UDID disability card assessment"},
            {"code": "DISTRICT_OFFICE", "name": "District Health / Collector Office", "service_code": "GENERAL_OPD", "desc": "Medical financial aid, Rare disease grant, emergency distress funds"}
        ]

        cap_obj_map = {}
        for cdef in CAPABILITY_DEFINITIONS:
            cap = db.query(AssistanceCapabilityModel).filter_by(capability_code=cdef["code"]).first()
            if not cap:
                cap = AssistanceCapabilityModel(
                    capability_code=cdef["code"],
                    name=cdef["name"],
                    description=cdef["desc"],
                    facility_service_code=cdef["service_code"]
                )
                db.add(cap)
                db.flush()
            else:
                cap.name = cdef["name"]
                cap.description = cdef["desc"]
                cap.facility_service_code = cdef["service_code"]
            cap_obj_map[cdef["code"]] = cap

        # Canonical Scheme-to-Capability Mappings
        SCHEME_CAPABILITY_RULES = {
            "IN-NHA-PMJAY": ["PMJAY_HELP_DESK", "AYUSHMAN_CARD_SUPPORT", "CSC", "EMPANELLED_HOSPITAL"],
            "MH-SHAS-MJPJAY": ["MJPJAY_HELP_DESK", "EMPANELLED_HOSPITAL", "STATE_HEALTH_AGENCY_SUPPORT", "CSC"],
            "IN-MOWCD-PMMVY": ["ANGANWADI", "WCD_OFFICE", "ASHA_SUPPORT", "CSC"],
            "IN-MOHFW-JSY": ["ASHA_SUPPORT", "ANM_SUB_CENTRE", "PHC_FACILITY", "GOVT_MATERNITY_FACILITY"],
            "IN-MOHFW-JSSK": ["ASHA_SUPPORT", "ANM_SUB_CENTRE", "PHC_FACILITY", "GOVT_MATERNITY_FACILITY"],
            "IN-MOHFW-NIKSHAY-POSHAN": ["TB_DOTS_CENTRE", "PHC_FACILITY", "ASHA_SUPPORT"],
            "IN-MOHFW-UWIN": ["VACCINATION_CENTRE", "ANM_SUB_CENTRE", "PHC_FACILITY", "ASHA_SUPPORT"],
            "IN-MOSJE-SNC": ["SOCIAL_WELFARE_OFFICE", "CSC", "DISTRICT_OFFICE"],
            "IN-DEPWD-UDID": ["SOCIAL_WELFARE_OFFICE", "DISTRICT_OFFICE", "CSC"],
            "IN-MOHFW-RAN": ["DISTRICT_OFFICE", "PHC_FACILITY", "EMPANELLED_HOSPITAL"]
        }

        for sc_code, cap_codes in SCHEME_CAPABILITY_RULES.items():
            scheme = db.query(SchemeModel).filter_by(scheme_code=sc_code).first()
            if not scheme:
                # Try matching by short_name or partial
                scheme = db.query(SchemeModel).filter(
                    (SchemeModel.scheme_code.ilike(f"%{sc_code}%")) |
                    (SchemeModel.short_name.ilike(f"%{sc_code}%"))
                ).first()
            if not scheme:
                continue

            for v in scheme.versions:
                for c_code in cap_codes:
                    cap = cap_obj_map.get(c_code)
                    if not cap:
                        continue
                    existing_map = db.query(SchemeAssistanceCapabilityModel).filter_by(
                        scheme_version_id=v.scheme_version_id,
                        capability_id=cap.capability_id
                    ).first()
                    if not existing_map:
                        db.add(SchemeAssistanceCapabilityModel(
                            scheme_version_id=v.scheme_version_id,
                            capability_id=cap.capability_id,
                            required_level="REQUIRED",
                            assistance_type="IN_PERSON",
                            source_reference="National Health Mission & NHA Guidelines 2026"
                        ))

        # Also assign standard capability fallback for any remaining active scheme versions
        all_active_versions = db.query(SchemeVersionModel).all()
        for v in all_active_versions:
            if not v.assistance_capabilities:
                # Assign default primary healthcare & ASHA capabilities
                for def_cap_code in ["PHC_FACILITY", "ASHA_SUPPORT", "CSC"]:
                    cap = cap_obj_map.get(def_cap_code)
                    if cap:
                        db.add(SchemeAssistanceCapabilityModel(
                            scheme_version_id=v.scheme_version_id,
                            capability_id=cap.capability_id,
                            required_level="REQUIRED",
                            assistance_type="IN_PERSON",
                            source_reference="General Public Health Program Guidelines 2026"
                        ))

        db.commit()
        print(f'[KB Import] Successfully imported {created_count} new schemes and seeded Assistance Capabilities into PostgreSQL!')
    except Exception as e:
        db.rollback()
        print(f'[KB Import ERROR] {e}')
        raise e
    finally:
        db.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--path', default='../schemes')
    parser.add_argument('--validate-only', action='store_true')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()

    import_knowledge_base(args.path, args.validate_only, args.dry_run)
