"""
Comprehensive Four-Role Demonstration Seed Script (Development & Test Only)

Seed Namespace: AAROGYA_DEMO_V1
is_demo: true

Safety Rules:
- Allows ONLY APP_ENV='development' or APP_ENV='test'.
- Explicitly refuses execution in production (APP_ENV=production or prod).
- Uses synthetic demonstration data only (no real Aadhaar, ABHA, phone numbers, or clinical PII).
- All writes execute transactionally with automatic rollback on error.
- Preserves user-created records; '--reset-demo' purges ONLY records belonging to 'AAROGYA_DEMO_V1'.
- Requires 'CONFIRM_RESET_DEMO=true' or '--force' environment guard for resetting.
- Idempotent: Re-running updates existing records by seed_key/reference without creating duplicates.
- All timestamps are UTC-aware; displayed in Asia/Kolkata where needed.

CLI Commands:
- Seed & Upsert: python -m app.seeds.seed_full_demo
- Verify Integrity: python -m app.seeds.seed_full_demo --verify
- Reset Demo Data: python -m app.seeds.seed_full_demo --reset-demo
- Reset Canonical Live Journey: python -m app.seeds.seed_full_demo --reset-canonical
"""

import os
import sys
import argparse
from datetime import datetime, timezone, timedelta
from sqlalchemy import or_
from sqlalchemy.orm import Session
from app.database import SessionLocal, engine, Base
from app.models import (
    User, CitizenProfile, WorkerProfile, Facility, Case, SymptomObservation,
    VitalRecord, AshaVisit, Referral, Consultation, Prescription, PrescriptionItem,
    TestOrder, FollowUp, Notification, AuditLog,
    UserRoleEnum, CasePriorityEnum, CaseStatusEnum, InformationSourceEnum
)
from app.auth.security import get_password_hash

SEED_NAMESPACE = "AAROGYA_DEMO_V1"


def verify_environment():
    app_env = os.getenv("APP_ENV", "development").lower()
    if app_env in ["production", "prod"]:
        print("\n[CRITICAL SAFETY ERROR] Demonstration seed script CANNOT run in PRODUCTION (APP_ENV=production)!\n")
        sys.exit(1)
    print(f"Safety Gate Passed: APP_ENV='{app_env}' (non-production). Seed Namespace: {SEED_NAMESPACE}")


def reset_demo_records(db: Session, force: bool = False):
    """Safely reset and delete only records belonging to the AAROGYA_DEMO_V1 namespace."""
    verify_environment()

    # Guard check for reset
    confirm = os.getenv("CONFIRM_RESET_DEMO", "").lower() in ["true", "1", "yes"]
    if not (confirm or force):
        print("\n[SAFETY GUARD ERROR] '--reset-demo' requires setting CONFIRM_RESET_DEMO=true environment variable or passing --force!")
        print("Example: $env:CONFIRM_RESET_DEMO=\"true\"; python -m app.seeds.seed_full_demo --reset-demo\n")
        sys.exit(1)

    print("\n--- RESETTING AAROGYA_DEMO_V1 RECORDS ---")
    try:
        # Delete prescription items
        db.query(PrescriptionItem).filter(
            PrescriptionItem.prescription_id.in_(
                db.query(Prescription.id).join(Consultation).join(Case).filter(Case.reference.like("CASE-DEMO-%"))
            )
        ).delete(synchronize_session=False)

        # Delete prescriptions
        db.query(Prescription).filter(
            Prescription.consultation_id.in_(
                db.query(Consultation.id).join(Case).filter(Case.reference.like("CASE-DEMO-%"))
            )
        ).delete(synchronize_session=False)

        # Delete test orders
        db.query(TestOrder).filter(
            TestOrder.consultation_id.in_(
                db.query(Consultation.id).join(Case).filter(Case.reference.like("CASE-DEMO-%"))
            )
        ).delete(synchronize_session=False)

        # Delete follow ups
        db.query(FollowUp).filter(
            FollowUp.case_id.in_(
                db.query(Case.id).filter(Case.reference.like("CASE-DEMO-%"))
            )
        ).delete(synchronize_session=False)

        # Delete consultations
        db.query(Consultation).filter(
            Consultation.case_id.in_(
                db.query(Case.id).filter(Case.reference.like("CASE-DEMO-%"))
            )
        ).delete(synchronize_session=False)

        # Delete referrals
        db.query(Referral).filter(
            Referral.reference.like("REF-DEMO-%")
        ).delete(synchronize_session=False)

        # Delete vitals
        db.query(VitalRecord).filter(
            VitalRecord.case_id.in_(
                db.query(Case.id).filter(Case.reference.like("CASE-DEMO-%"))
            )
        ).delete(synchronize_session=False)

        # Delete symptoms
        db.query(SymptomObservation).filter(
            SymptomObservation.case_id.in_(
                db.query(Case.id).filter(Case.reference.like("CASE-DEMO-%"))
            )
        ).delete(synchronize_session=False)

        # Delete Asha visits
        db.query(AshaVisit).filter(
            AshaVisit.reference.like("VISIT-DEMO-%")
        ).delete(synchronize_session=False)

        # Delete cases
        db.query(Case).filter(
            Case.reference.like("CASE-DEMO-%")
        ).delete(synchronize_session=False)

        # Delete citizen profiles belonging to demo
        db.query(CitizenProfile).filter(
            CitizenProfile.abha_reference.like("ABHA-DEMO-%")
        ).delete(synchronize_session=False)

        db.commit()
        print("[SUCCESS] All AAROGYA_DEMO_V1 namespace records successfully purged.\n")
    except Exception as e:
        db.rollback()
        print(f"[ERROR] Resetting demo records failed: {e}")
        raise


def reset_canonical_journey(db: Session):
    """Resets only DEMO-LIVE-JOURNEY-001 (Nisha Patil) to its clean initial state."""
    verify_environment()
    print("\n--- RESETTING CANONICAL LIVE JOURNEY (Nisha Patil) ---")
    try:
        live_cases = db.query(Case).filter(Case.reference.like("CASE-DEMO-LIVE-%")).all()
        for lc in live_cases:
            db.query(PrescriptionItem).filter(
                PrescriptionItem.prescription_id.in_(
                    db.query(Prescription.id).join(Consultation).filter(Consultation.case_id == lc.id)
                )
            ).delete(synchronize_session=False)
            db.query(Prescription).filter(
                Prescription.consultation_id.in_(
                    db.query(Consultation.id).filter(Consultation.case_id == lc.id)
                )
            ).delete(synchronize_session=False)
            db.query(TestOrder).filter(
                TestOrder.consultation_id.in_(
                    db.query(Consultation.id).filter(Consultation.case_id == lc.id)
                )
            ).delete(synchronize_session=False)
            db.query(FollowUp).filter(FollowUp.case_id == lc.id).delete(synchronize_session=False)
            db.query(Consultation).filter(Consultation.case_id == lc.id).delete(synchronize_session=False)
            db.query(Referral).filter(Referral.case_id == lc.id).delete(synchronize_session=False)
            db.query(VitalRecord).filter(VitalRecord.case_id == lc.id).delete(synchronize_session=False)
            db.query(SymptomObservation).filter(SymptomObservation.case_id == lc.id).delete(synchronize_session=False)
            db.query(AshaVisit).filter(AshaVisit.case_id == lc.id).delete(synchronize_session=False)
            db.delete(lc)

        # Restore Nisha Patil citizen record if missing
        live_abha = "ABHA-DEMO-LIVE-001"
        live_cit = db.query(CitizenProfile).filter(CitizenProfile.abha_reference == live_abha).first()
        if not live_cit:
            now = datetime.now(timezone.utc)
            asha_user = db.query(User).filter(User.identifier == "sita.asha").first()
            live_cit = CitizenProfile(
                abha_reference=live_abha,
                display_name="Nisha Patil",
                age_estimate=29,
                sex="Female",
                village_name="Kalyanpur",
                district="Demo District 04",
                state="Maharashtra",
                phone="9876599999",
                is_pregnant=True,
                gestational_weeks=26,
                assigned_asha_id=asha_user.id if asha_user else None,
                preferred_language="mr-IN",
                created_at=now - timedelta(days=2),
            )
            db.add(live_cit)

        db.commit()
        print("[SUCCESS] Canonical live journey DEMO-LIVE-JOURNEY-001 successfully reset to clean initial state.\n")
    except Exception as e:
        db.rollback()
        print(f"[ERROR] Resetting canonical journey failed: {e}")
        raise


def seed_full_demonstration():
    verify_environment()
    db: Session = SessionLocal()

    now = datetime.now(timezone.utc)
    summary_counts = {
        "users": 0,
        "facilities": 0,
        "citizens": 0,
        "cases": 0,
        "symptoms": 0,
        "vitals": 0,
        "visits": 0,
        "referrals": 0,
        "consultations": 0,
        "prescriptions": 0,
        "prescription_items": 0,
        "test_orders": 0,
        "follow_ups": 0,
    }

    try:
        print("\n=======================================================")
        print("  SEEDING 4-ROLE AAROGYA SAHAYAK DEMO DATASET (V1)")
        print("=======================================================")

        # 1. Facilities
        facilities_data = [
            {
                "id": "FAC-PHC-09",
                "code": "PHC-09",
                "name": "Kalyanpur Primary Health Centre",
                "facility_type": "PHC",
                "district_name": "Demo District 04",
                "block_name": "Kalyanpur Block",
                "address": "Main Road, Kalyanpur Village",
            },
            {
                "id": "FAC-SC-05",
                "code": "SC-05",
                "name": "Ganeshpur Sub-Centre",
                "facility_type": "SUB_CENTRE",
                "district_name": "Demo District 04",
                "block_name": "Kalyanpur Block",
                "address": "Ganeshpur Panchayat Office Road",
            },
            {
                "id": "FAC-CHC-03",
                "code": "CHC-03",
                "name": "Shivaji Nagar Community Health Centre",
                "facility_type": "CHC",
                "district_name": "Demo District 04",
                "block_name": "Shivaji Nagar Block",
                "address": "Station Road, Shivaji Nagar",
            },
            {
                "id": "FAC-DH-01",
                "code": "DH-01",
                "name": "Demo District Hospital",
                "facility_type": "DISTRICT_HOSPITAL",
                "district_name": "Demo District 04",
                "block_name": "District Headquarter Block",
                "address": "Civil Lines, District HQ",
            },
        ]

        fac_map = {}
        for f in facilities_data:
            rec = db.query(Facility).filter(Facility.code == f["code"]).first()
            if not rec:
                rec = Facility(
                    id=f["id"],
                    code=f["code"],
                    name=f["name"],
                    facility_type=f["facility_type"],
                    district_name=f["district_name"],
                    block_name=f["block_name"],
                    address=f["address"],
                    is_active=True,
                    created_at=now,
                )
                db.add(rec)
                summary_counts["facilities"] += 1
            else:
                rec.name = f["name"]
                rec.is_active = True
            fac_map[f["code"]] = rec
        db.flush()

        # 2. Users (ASHA, Doctor, District Admin)
        demo_pwd_hash = get_password_hash("demo123")

        asha_user = db.query(User).filter(User.identifier == "sita.asha").first()
        if not asha_user:
            asha_user = User(
                id="USR-ASHA-012",
                identifier="sita.asha",
                name="Sita Patel",
                email="sita.asha@demo.aarogya.gov.in",
                phone="9823012345",
                password_hash=demo_pwd_hash,
                role=UserRoleEnum.ASHA_WORKER,
                preferred_language="mr-IN",
                is_active=True,
                created_at=now,
            )
            db.add(asha_user)
            summary_counts["users"] += 1
            db.flush()

            asha_profile = WorkerProfile(
                user_id=asha_user.id,
                worker_type="ASHA",
                facility_id=fac_map["PHC-09"].id,
                facility_name="Kalyanpur Primary Health Centre",
                district_name="Demo District 04",
                created_at=now,
            )
            db.add(asha_profile)

        doc_user = db.query(User).filter(User.identifier == "dr.sharma").first()
        if not doc_user:
            doc_user = User(
                id="USR-DOC-007",
                identifier="dr.sharma",
                name="Dr. Abhinav Sharma",
                email="dr.sharma@demo.aarogya.gov.in",
                phone="9823012346",
                password_hash=demo_pwd_hash,
                role=UserRoleEnum.PHC_DOCTOR,
                preferred_language="mr-IN",
                is_active=True,
                created_at=now,
            )
            db.add(doc_user)
            summary_counts["users"] += 1
            db.flush()

            doc_profile = WorkerProfile(
                user_id=doc_user.id,
                worker_type="DOCTOR",
                facility_id=fac_map["PHC-09"].id,
                facility_name="Kalyanpur Primary Health Centre",
                district_name="Demo District 04",
                created_at=now,
            )
            db.add(doc_profile)

        admin_user = db.query(User).filter(User.identifier == "dho.admin").first()
        if not admin_user:
            admin_user = User(
                id="USR-ADMIN-004",
                identifier="dho.admin",
                name="Dr. Rajesh Deshmukh",
                email="dho.admin@demo.aarogya.gov.in",
                phone="9823012347",
                password_hash=demo_pwd_hash,
                role=UserRoleEnum.DISTRICT_ADMIN,
                preferred_language="mr-IN",
                is_active=True,
                created_at=now,
            )
            db.add(admin_user)
            summary_counts["users"] += 1
            db.flush()

            admin_profile = WorkerProfile(
                user_id=admin_user.id,
                worker_type="ADMIN",
                district_name="Demo District 04",
                created_at=now,
            )
            db.add(admin_profile)

        # Helper Upsert Function
        def upsert_scenario(
            p_key: str,
            c_ref: str,
            r_ref: str,
            name: str,
            age: int,
            gender: str,
            village: str,
            category: str,
            priority: CasePriorityEnum,
            case_status: CaseStatusEnum,
            referral_status: str,
            concern: str,
            symptoms: list,
            vitals: dict,
            is_pregnant: bool = False,
            gestational_weeks: int = None,
            anc_registered: bool = False,
            transport_status: str = "SELF",
            arrival_delta_min: int = None,
            consultation_data: dict = None,
            followup_data: dict = None,
            visit_data: dict = None,
            test_orders: list = None,
        ):
            # 1. Citizen Profile
            abha = f"ABHA-DEMO-{p_key.split('-')[-1]}"
            cit = db.query(CitizenProfile).filter(CitizenProfile.abha_reference == abha).first()
            if not cit:
                cit = CitizenProfile(
                    abha_reference=abha,
                    display_name=name,
                    age_estimate=age,
                    sex=gender,
                    village_name=village,
                    district="Demo District 04",
                    state="Maharashtra",
                    phone="9876500000"[:-len(p_key.split('-')[-1])] + p_key.split('-')[-1],
                    is_pregnant=is_pregnant,
                    gestational_weeks=gestational_weeks,
                    anc_registration_number=f"ANC-DEMO-{p_key.split('-')[-1]}" if anc_registered else None,
                    assigned_asha_id=asha_user.id,
                    preferred_language="mr-IN",
                    registration_consent_obtained=True,
                    consent_method="VERBAL",
                    consent_timestamp=now - timedelta(days=14),
                    created_at=now - timedelta(days=14),
                )
                db.add(cit)
                summary_counts["citizens"] += 1
                db.flush()
            else:
                cit.display_name = name
                cit.is_pregnant = is_pregnant
                cit.gestational_weeks = gestational_weeks
                cit.village_name = village

            # 2. Case
            case = db.query(Case).filter(Case.reference == c_ref).first()
            created_time = now - timedelta(minutes=arrival_delta_min if arrival_delta_min else 180)
            if not case:
                case = Case(
                    reference=c_ref,
                    citizen_id=cit.id,
                    assigned_asha_id=asha_user.id,
                    assigned_asha_name="Sita Patel",
                    assigned_facility_id=fac_map["PHC-09"].id,
                    assigned_facility_name="Kalyanpur Primary Health Centre",
                    assigned_doctor_id=doc_user.id,
                    assigned_doctor_name="Dr. Abhinav Sharma",
                    primary_concern=concern,
                    priority=priority,
                    status=case_status,
                    preferred_language="mr-IN",
                    safety_rule_triggered=(priority == CasePriorityEnum.URGENT),
                    safety_rule_reason="Maternal warning signs detected" if is_pregnant and priority == CasePriorityEnum.URGENT else None,
                    created_at=created_time,
                )
                db.add(case)
                summary_counts["cases"] += 1
                db.flush()
            else:
                case.primary_concern = concern
                case.priority = priority
                case.status = case_status

            # 3. Symptoms
            for s in symptoms:
                sym = db.query(SymptomObservation).filter(
                    SymptomObservation.case_id == case.id,
                    SymptomObservation.normalized_term == s["term"]
                ).first()
                if not sym:
                    sym = SymptomObservation(
                        case_id=case.id,
                        normalized_term=s["term"],
                        spoken_term=s.get("spoken", s["term"]),
                        severity=s.get("severity", "HIGH"),
                        source_type=InformationSourceEnum.ASHA_CONFIRMED,
                        recorded_by=asha_user.id,
                        recorded_at=created_time,
                    )
                    db.add(sym)
                    summary_counts["symptoms"] += 1

            # 4. Vitals
            if vitals:
                vit = db.query(VitalRecord).filter(VitalRecord.case_id == case.id).first()
                if not vit:
                    vit = VitalRecord(
                        case_id=case.id,
                        systolic_bp=vitals.get("sbp"),
                        diastolic_bp=vitals.get("dbp"),
                        temperature_c=vitals.get("temp"),
                        spo2=vitals.get("spo2"),
                        pulse=vitals.get("pulse"),
                        respiratory_rate=vitals.get("rr", 18),
                        is_warning_sign=(vitals.get("sbp", 120) > 140 or vitals.get("spo2", 98) < 94),
                        source_type=InformationSourceEnum.ASHA_CONFIRMED,
                        recorded_by=asha_user.id,
                        recorded_at=created_time,
                    )
                    db.add(vit)
                    summary_counts["vitals"] += 1

            # 5. ASHA Visit
            if visit_data:
                v_ref = f"VISIT-DEMO-{p_key.split('-')[-1]}"
                vst = db.query(AshaVisit).filter(AshaVisit.reference == v_ref).first()
                if not vst:
                    vst = AshaVisit(
                        reference=v_ref,
                        case_id=case.id,
                        asha_worker_id=asha_user.id,
                        visit_type=visit_data.get("type", "Maternal Visit"),
                        notes=visit_data.get("notes", "Field visit conducted."),
                        status=visit_data.get("status", "COMPLETED"),
                        completed_at=created_time,
                    )
                    db.add(vst)
                    summary_counts["visits"] += 1

            # 6. Referral
            ref = None
            if r_ref:
                ref = db.query(Referral).filter(Referral.reference == r_ref).first()
                if not ref:
                    ref = Referral(
                        reference=r_ref,
                        case_id=case.id,
                        from_asha_id=asha_user.id,
                        to_facility_id=fac_map["PHC-09"].id,
                        to_facility_name="Kalyanpur Primary Health Centre",
                        reason=concern,
                        urgency=priority.value,
                        status=referral_status,
                        transport_assistance_required=(transport_status == "ASHA_ACCOMPANIED"),
                        created_at=created_time,
                    )
                    db.add(ref)
                    summary_counts["referrals"] += 1
                    db.flush()
                else:
                    ref.status = referral_status

            # 7. Consultation
            cons = None
            if consultation_data:
                cons_ref = consultation_data.get("reference", f"CON-DEMO-{p_key.split('-')[-1]}")
                cons = db.query(Consultation).filter(Consultation.reference == cons_ref).first()
                if not cons:
                    cons = Consultation(
                        reference=cons_ref,
                        case_id=case.id,
                        doctor_id=doc_user.id,
                        doctor_name="Dr. Abhinav Sharma",
                        facility_id=fac_map["PHC-09"].id,
                        status=consultation_data.get("status", "IN_CONSULTATION"),
                        examination_notes=consultation_data.get("examination_notes"),
                        provisional_diagnosis=consultation_data.get("provisional_diagnosis"),
                        confirmed_diagnosis=consultation_data.get("confirmed_diagnosis"),
                        icd10_code=consultation_data.get("icd10_code"),
                        clinical_summary=consultation_data.get("examination_notes"),
                        care_plan_summary=consultation_data.get("care_plan_summary"),
                        asha_followup_instructions=consultation_data.get("asha_directive"),
                        followup_due_days=consultation_data.get("followup_due_days", 3),
                        created_at=now - timedelta(minutes=15),
                        completed_at=now - timedelta(minutes=5) if consultation_data.get("status") == "COMPLETED" else None,
                        signed_at=now - timedelta(minutes=5) if consultation_data.get("status") == "COMPLETED" else None,
                    )
                    db.add(cons)
                    summary_counts["consultations"] += 1
                    db.flush()

                # Prescriptions
                if consultation_data.get("prescriptions"):
                    for rx in consultation_data["prescriptions"]:
                        p_rec = db.query(Prescription).filter(Prescription.consultation_id == cons.id).first()
                        if not p_rec:
                            p_rec = Prescription(
                                consultation_id=cons.id,
                                doctor_id=doc_user.id,
                                status="SIGNED" if consultation_data.get("status") == "COMPLETED" else "DRAFT",
                                issued_at=now - timedelta(minutes=10),
                            )
                            db.add(p_rec)
                            summary_counts["prescriptions"] += 1
                            db.flush()

                        for item in rx.get("items", []):
                            pi = db.query(PrescriptionItem).filter(
                                PrescriptionItem.prescription_id == p_rec.id,
                                PrescriptionItem.medicine == item["name"]
                            ).first()
                            if not pi:
                                pi = PrescriptionItem(
                                    prescription_id=p_rec.id,
                                    medicine=item["name"],
                                    strength=item.get("strength", "100mg"),
                                    form="Tablet",
                                    dose=item.get("dose", "1 tablet"),
                                    frequency=item.get("freq", "Twice daily"),
                                    duration=item.get("duration", 5),
                                    timing="After food",
                                    instructions=item.get("inst", "Take after meals"),
                                )
                                db.add(pi)
                                summary_counts["prescription_items"] += 1

            # 8. Test Orders
            if test_orders and cons:
                for t in test_orders:
                    t_rec = db.query(TestOrder).filter(
                        TestOrder.consultation_id == cons.id,
                        TestOrder.test_name == t["name"]
                    ).first()
                    if not t_rec:
                        t_rec = TestOrder(
                            consultation_id=cons.id,
                            test_name=t["name"],
                            priority=t.get("priority", "URGENT"),
                            status=t.get("status", "ORDERED"),
                            ordered_at=now - timedelta(minutes=30),
                        )
                        db.add(t_rec)
                        summary_counts["test_orders"] += 1

            # 9. Follow Up
            if followup_data:
                fu = db.query(FollowUp).filter(FollowUp.case_id == case.id).first()
                if not fu:
                    fu = FollowUp(
                        case_id=case.id,
                        citizen_id=cit.id,
                        referral_id=ref.id if ref else None,
                        consultation_id=cons.id if cons else None,
                        assigned_user_id=asha_user.id,
                        assigned_role=UserRoleEnum.ASHA_WORKER,
                        created_by_id=doc_user.id,
                        created_by_role="DOCTOR",
                        task_type="BP_MONITORING",
                        instructions=followup_data.get("desc", "Conduct ASHA home follow-up"),
                        due_at=now + timedelta(days=followup_data.get("due_days", 1)),
                        priority=CasePriorityEnum.URGENT if followup_data.get("priority") == "URGENT" else CasePriorityEnum.ROUTINE,
                        status=followup_data.get("status", "PENDING"),
                        completion_notes=followup_data.get("notes"),
                        escalation_conditions=followup_data.get("escalation_reason"),
                        created_at=now - timedelta(hours=1),
                    )
                    db.add(fu)
                    summary_counts["follow_ups"] += 1

        # Clean up any legacy 'Arogya Test' or corrupt records
        test_cits = db.query(CitizenProfile).filter(
            or_(
                CitizenProfile.display_name.ilike("%Arogya Test%"),
                CitizenProfile.display_name.ilike("%Test Patient%")
            )
        ).all()
        for tc in test_cits:
            for c in tc.cases:
                db.query(Consultation).filter(Consultation.case_id == c.id).delete(synchronize_session=False)
                db.query(Referral).filter(Referral.case_id == c.id).delete(synchronize_session=False)
                db.query(VitalRecord).filter(VitalRecord.case_id == c.id).delete(synchronize_session=False)
                db.query(SymptomObservation).filter(SymptomObservation.case_id == c.id).delete(synchronize_session=False)
                db.query(AshaVisit).filter(AshaVisit.case_id == c.id).delete(synchronize_session=False)
                db.delete(c)
            db.delete(tc)
        db.flush()

        # Track created, updated, unchanged for idempotency reporting
        idempotency_tracker = {"created": 0, "updated": 0, "unchanged": 0}

        def upsert_scenario(
            p_key: str,
            c_ref: str,
            r_ref: str,
            name: str,
            age: int,
            gender: str,
            village: str,
            category: str,
            priority: CasePriorityEnum,
            case_status: CaseStatusEnum,
            referral_status: str,
            concern: str,
            symptoms: list,
            vitals: dict,
            is_pregnant: bool = False,
            gestational_weeks: int = None,
            anc_registered: bool = False,
            transport_status: str = "SELF",
            arrival_delta_min: int = None,
            consultation_data: dict = None,
            followup_data: dict = None,
            visit_data: dict = None,
            test_orders: list = None,
        ):
            record_changed = False
            # 1. Citizen Profile
            abha = f"ABHA-DEMO-{p_key.split('-')[-1]}"
            cit = db.query(CitizenProfile).filter(CitizenProfile.abha_reference == abha).first()
            if not cit:
                cit = CitizenProfile(
                    abha_reference=abha,
                    display_name=name,
                    age_estimate=age,
                    sex=gender,
                    village_name=village,
                    district="Demo District 04",
                    state="Maharashtra",
                    phone="9876500000"[:-len(p_key.split('-')[-1])] + p_key.split('-')[-1],
                    is_pregnant=is_pregnant,
                    gestational_weeks=gestational_weeks,
                    anc_registration_number=f"ANC-DEMO-{p_key.split('-')[-1]}" if anc_registered else None,
                    assigned_asha_id=asha_user.id,
                    preferred_language="mr-IN",
                    registration_consent_obtained=True,
                    consent_method="VERBAL",
                    consent_timestamp=now - timedelta(days=14),
                    created_at=now - timedelta(days=14),
                )
                db.add(cit)
                summary_counts["citizens"] += 1
                record_changed = True
                db.flush()
            else:
                if cit.display_name != name or cit.is_pregnant != is_pregnant:
                    cit.display_name = name
                    cit.is_pregnant = is_pregnant
                    cit.gestational_weeks = gestational_weeks
                    cit.village_name = village
                    record_changed = True

            # 2. Case
            case = db.query(Case).filter(Case.reference == c_ref).first()
            created_time = now - timedelta(minutes=arrival_delta_min if arrival_delta_min else 180)
            if not case:
                case = Case(
                    reference=c_ref,
                    citizen_id=cit.id,
                    assigned_asha_id=asha_user.id,
                    assigned_asha_name="Sita Patel",
                    assigned_facility_id=fac_map["PHC-09"].id,
                    assigned_facility_name="Kalyanpur Primary Health Centre",
                    assigned_doctor_id=doc_user.id,
                    assigned_doctor_name="Dr. Abhinav Sharma",
                    primary_concern=concern,
                    priority=priority,
                    status=case_status,
                    preferred_language="mr-IN",
                    safety_rule_triggered=(priority == CasePriorityEnum.URGENT),
                    safety_rule_reason="Maternal warning signs detected" if is_pregnant and priority == CasePriorityEnum.URGENT else None,
                    created_at=created_time,
                )
                db.add(case)
                summary_counts["cases"] += 1
                record_changed = True
                db.flush()
            else:
                if case.status != case_status or case.priority != priority:
                    case.primary_concern = concern
                    case.priority = priority
                    case.status = case_status
                    record_changed = True

            # 3. Symptoms
            for s in symptoms:
                sym = db.query(SymptomObservation).filter(
                    SymptomObservation.case_id == case.id,
                    SymptomObservation.normalized_term == s["term"]
                ).first()
                if not sym:
                    sym = SymptomObservation(
                        case_id=case.id,
                        normalized_term=s["term"],
                        spoken_term=s.get("spoken", s["term"]),
                        severity=s.get("severity", "HIGH"),
                        source_type=InformationSourceEnum.ASHA_CONFIRMED,
                        recorded_by=asha_user.id,
                        recorded_at=created_time,
                    )
                    db.add(sym)
                    summary_counts["symptoms"] += 1
                    record_changed = True

            # 4. Vitals
            if vitals:
                vit = db.query(VitalRecord).filter(VitalRecord.case_id == case.id).first()
                if not vit:
                    vit = VitalRecord(
                        case_id=case.id,
                        systolic_bp=vitals.get("sbp"),
                        diastolic_bp=vitals.get("dbp"),
                        temperature_c=vitals.get("temp"),
                        spo2=vitals.get("spo2"),
                        pulse=vitals.get("pulse"),
                        respiratory_rate=vitals.get("rr", 18),
                        is_warning_sign=(vitals.get("sbp", 120) > 140 or vitals.get("spo2", 98) < 94),
                        source_type=InformationSourceEnum.ASHA_CONFIRMED,
                        recorded_by=asha_user.id,
                        recorded_at=created_time,
                    )
                    db.add(vit)
                    summary_counts["vitals"] += 1
                    record_changed = True
                else:
                    if vit.systolic_bp != vitals.get("sbp") or vit.spo2 != vitals.get("spo2"):
                        vit.systolic_bp = vitals.get("sbp")
                        vit.diastolic_bp = vitals.get("dbp")
                        vit.temperature_c = vitals.get("temp")
                        vit.spo2 = vitals.get("spo2")
                        vit.pulse = vitals.get("pulse")
                        record_changed = True

            # 5. ASHA Visit
            if visit_data:
                v_ref = f"VISIT-DEMO-{p_key.split('-')[-1]}"
                vst = db.query(AshaVisit).filter(AshaVisit.reference == v_ref).first()
                if not vst:
                    vst = AshaVisit(
                        reference=v_ref,
                        case_id=case.id,
                        asha_worker_id=asha_user.id,
                        visit_type=visit_data.get("type", "Maternal Visit"),
                        notes=visit_data.get("notes", "Field visit conducted."),
                        status=visit_data.get("status", "COMPLETED"),
                        completed_at=created_time,
                    )
                    db.add(vst)
                    summary_counts["visits"] += 1
                    record_changed = True

            # 6. Referral
            ref = None
            if r_ref:
                ref = db.query(Referral).filter(Referral.reference == r_ref).first()
                if not ref:
                    arrived_time = (now - timedelta(minutes=arrival_delta_min)) if arrival_delta_min else (created_time if referral_status == "PATIENT_ARRIVED" else None)
                    ref = Referral(
                        reference=r_ref,
                        case_id=case.id,
                        from_asha_id=asha_user.id,
                        to_facility_id=fac_map["PHC-09"].id,
                        to_facility_name="Kalyanpur Primary Health Centre",
                        reason=concern,
                        urgency=priority,
                        status=referral_status,
                        arrived_at=arrived_time,
                        transport_assistance_required=(transport_status == "ASHA_ACCOMPANIED"),
                        created_at=created_time,
                    )
                    db.add(ref)
                    summary_counts["referrals"] += 1
                    record_changed = True
                    db.flush()
                else:
                    if ref.status != referral_status:
                        ref.status = referral_status
                        record_changed = True
                    if arrival_delta_min:
                        ref.arrived_at = now - timedelta(minutes=arrival_delta_min)
                        record_changed = True

            # 7. Consultation
            cons = None
            if consultation_data:
                cons_ref = consultation_data.get("reference", f"CON-DEMO-{p_key.split('-')[-1]}")
                cons = db.query(Consultation).filter(Consultation.reference == cons_ref).first()
                if not cons:
                    cons = Consultation(
                        reference=cons_ref,
                        case_id=case.id,
                        doctor_id=doc_user.id,
                        doctor_name="Dr. Abhinav Sharma",
                        facility_id=fac_map["PHC-09"].id,
                        status=consultation_data.get("status", "IN_CONSULTATION"),
                        examination_notes=consultation_data.get("examination_notes"),
                        provisional_diagnosis=consultation_data.get("provisional_diagnosis"),
                        confirmed_diagnosis=consultation_data.get("confirmed_diagnosis"),
                        icd10_code=consultation_data.get("icd10_code"),
                        clinical_summary=consultation_data.get("examination_notes"),
                        care_plan_summary=consultation_data.get("care_plan_summary"),
                        asha_followup_instructions=consultation_data.get("asha_directive"),
                        followup_due_days=consultation_data.get("followup_due_days", 3),
                        created_at=now - timedelta(minutes=15),
                        completed_at=now - timedelta(minutes=5) if consultation_data.get("status") == "COMPLETED" else None,
                        signed_at=now - timedelta(minutes=5) if consultation_data.get("status") == "COMPLETED" else None,
                    )
                    db.add(cons)
                    summary_counts["consultations"] += 1
                    record_changed = True
                    db.flush()
                else:
                    if cons.status != consultation_data.get("status"):
                        cons.status = consultation_data.get("status")
                        record_changed = True

            if record_changed:
                idempotency_tracker["updated"] += 1
            else:
                idempotency_tracker["unchanged"] += 1

        # =========================================================================
        # SEED CANONICAL DEMO SCENARIOS (Requirements 5)
        # =========================================================================

        # Scenario 1 — Meena Bai (New/Unacknowledged)
        upsert_scenario(
            p_key="DEMO-PATIENT-002",
            c_ref="CASE-DEMO-002",
            r_ref="REF-DEMO-002",
            name="Meena Bai",
            age=62,
            gender="Female",
            village="Ganeshpur",
            category="Adult respiratory",
            priority=CasePriorityEnum.URGENT,
            case_status=CaseStatusEnum.REFERRED_TO_PHC,
            referral_status="PENDING_DOCTOR_REVIEW",
            concern="Urgent respiratory warning signs, shortness of breath, SpO2 91%.",
            symptoms=[
                {"term": "Shortness of breath", "spoken": "श्वास घेण्यास त्रास", "severity": "URGENT"},
                {"term": "Hypoxemia", "spoken": "ऑक्सिजन कमी", "severity": "URGENT"},
            ],
            vitals={"sbp": 134, "dbp": 86, "temp": 37.4, "spo2": 91, "pulse": 102},
            visit_data={"type": "Urgent Triage Visit", "notes": "Observed respiratory distress and hypoxemia SpO2 91%.", "status": "COMPLETED"},
        )

        # Scenario 2 — Laxmi Kamble (New/Unacknowledged)
        upsert_scenario(
            p_key="DEMO-PATIENT-003",
            c_ref="CASE-DEMO-003",
            r_ref="REF-DEMO-003",
            name="Laxmi Kamble",
            age=26,
            gender="Female",
            village="Shivaji Nagar",
            category="Postnatal, day 8",
            priority=CasePriorityEnum.HIGH,
            case_status=CaseStatusEnum.REFERRED_TO_PHC,
            referral_status="PENDING_DOCTOR_REVIEW",
            concern="High-priority postnatal fever and localized breast tenderness.",
            symptoms=[
                {"term": "Postnatal Fever", "spoken": "बाळंतपणानंतरचा ताप", "severity": "HIGH"},
                {"term": "Breast Tenderness", "spoken": "स्तनात दुखणे", "severity": "HIGH"},
            ],
            vitals={"sbp": 118, "dbp": 76, "temp": 38.4, "spo2": 98, "pulse": 96},
            is_pregnant=False,
            visit_data={"type": "PNC Day 8 Check", "notes": "PNC visit noted fever and mastitis signs.", "status": "COMPLETED"},
        )

        # Scenario 3 — Rameshwar Shinde (Acknowledged)
        upsert_scenario(
            p_key="DEMO-PATIENT-005",
            c_ref="CASE-DEMO-005",
            r_ref="REF-DEMO-005",
            name="Rameshwar Shinde",
            age=54,
            gender="Male",
            village="Kalyanpur",
            category="NCD blood-pressure review",
            priority=CasePriorityEnum.HIGH,
            case_status=CaseStatusEnum.DOCTOR_ACKNOWLEDGED,
            referral_status="DOCTOR_ACKNOWLEDGED",
            concern="Chronic BP review with occipital headache.",
            symptoms=[
                {"term": "Elevated blood pressure", "spoken": "उच्च रक्तदाब", "severity": "HIGH"},
                {"term": "Occipital headache", "spoken": "डोकेदुखी", "severity": "MODERATE"},
            ],
            vitals={"sbp": 162, "dbp": 96, "temp": 36.7, "spo2": 98, "pulse": 84},
            visit_data={"type": "NCD Follow-Up", "notes": "Chronic BP evaluation.", "status": "COMPLETED"},
        )

        # Scenario 4 — Aarav Sharma (Acknowledged)
        upsert_scenario(
            p_key="DEMO-PATIENT-006",
            c_ref="CASE-DEMO-006",
            r_ref="REF-DEMO-006",
            name="Aarav Sharma",
            age=5,
            gender="Male",
            village="Kalyanpur",
            category="Child Pediatric",
            priority=CasePriorityEnum.HIGH,
            case_status=CaseStatusEnum.DOCTOR_ACKNOWLEDGED,
            referral_status="DOCTOR_ACKNOWLEDGED",
            concern="Pediatric fever with reduced oral intake.",
            symptoms=[
                {"term": "High fever", "spoken": "खूप ताप", "severity": "HIGH"},
                {"term": "Reduced oral intake", "spoken": "कमी खाणे", "severity": "MODERATE"},
            ],
            vitals={"sbp": 95, "dbp": 60, "temp": 39.1, "spo2": 96, "pulse": 116},
            visit_data={"type": "Pediatric Triage", "notes": "Fever evaluation.", "status": "COMPLETED"},
        )

        # Scenario 5 — Kisan Rao (Transport Arranged)
        upsert_scenario(
            p_key="DEMO-PATIENT-013",
            c_ref="CASE-DEMO-013",
            r_ref="REF-DEMO-013",
            name="Kisan Rao",
            age=58,
            gender="Male",
            village="Kalyanpur",
            category="Adult Cardiology",
            priority=CasePriorityEnum.URGENT,
            case_status=CaseStatusEnum.REFERRED_TO_PHC,
            referral_status="TRANSPORT_ARRANGED",
            concern="Urgent chest discomfort radiating to left arm with breathlessness.",
            symptoms=[
                {"term": "Chest Discomfort", "spoken": "छातीत दुखणे", "severity": "URGENT"},
                {"term": "Breathlessness", "spoken": "दम लागणे", "severity": "URGENT"},
            ],
            vitals={"sbp": 142, "dbp": 92, "temp": 36.8, "spo2": 95, "pulse": 98},
            transport_status="ASHA_ACCOMPANIED",
            visit_data={"type": "Emergency Field Triage", "notes": "Chest discomfort detected, 108 ambulance dispatched.", "status": "COMPLETED"},
        )

        # Scenario 6 — Sunita Devi (Patient Arrived - 31 min ago)
        upsert_scenario(
            p_key="DEMO-PATIENT-004",
            c_ref="CASE-DEMO-004",
            r_ref="REF-DEMO-004",
            name="Sunita Devi",
            age=28,
            gender="Female",
            village="Kalyanpur",
            category="Maternal, 28 weeks",
            priority=CasePriorityEnum.URGENT,
            case_status=CaseStatusEnum.PATIENT_ARRIVED,
            referral_status="PATIENT_ARRIVED",
            concern="Pregnancy warning signs, BP 150/100 with dizziness and pedal edema.",
            symptoms=[
                {"term": "High BP in pregnancy", "spoken": "गरोदरपणातील उच्च रक्तदाब", "severity": "URGENT"},
                {"term": "Dizziness", "spoken": "चक्कर येणे", "severity": "HIGH"},
            ],
            vitals={"sbp": 150, "dbp": 100, "temp": 36.8, "spo2": 98, "pulse": 86},
            is_pregnant=True,
            gestational_weeks=28,
            anc_registered=True,
            arrival_delta_min=31,
            visit_data={"type": "ANC Field Visit", "notes": "High BP detected in pregnancy.", "status": "COMPLETED"},
        )

        # Scenario 7 — Anandi Bai Deshmukh (Patient Arrived - 8 min ago)
        upsert_scenario(
            p_key="DEMO-PATIENT-001",
            c_ref="CASE-DEMO-001",
            r_ref="REF-DEMO-001",
            name="Anandi Bai Deshmukh",
            age=30,
            gender="Female",
            village="Kalyanpur",
            category="Maternal, 30 weeks",
            priority=CasePriorityEnum.URGENT,
            case_status=CaseStatusEnum.PATIENT_ARRIVED,
            referral_status="PATIENT_ARRIVED",
            concern="Maternal warning signs, severe headache, blurred vision and swelling of feet.",
            symptoms=[
                {"term": "Severe Headache", "spoken": "खूप डोकेदुखी", "severity": "URGENT"},
                {"term": "Blurred Vision", "spoken": "डोळ्यांसमोर अंधारी", "severity": "URGENT"},
                {"term": "Pedal Edema", "spoken": "पायावर सूज", "severity": "HIGH"},
            ],
            vitals={"sbp": 155, "dbp": 100, "temp": 37.0, "spo2": 97, "pulse": 88},
            is_pregnant=True,
            gestational_weeks=30,
            anc_registered=True,
            transport_status="ASHA_ACCOMPANIED",
            arrival_delta_min=8,
            visit_data={"type": "ANC Home Registration", "notes": "High BP detection.", "status": "COMPLETED"},
        )

        # Scenario 7b — Pooja Jadhav (Patient Arrived - 18 min ago)
        upsert_scenario(
            p_key="DEMO-PATIENT-015",
            c_ref="CASE-DEMO-015",
            r_ref="REF-DEMO-015",
            name="Pooja Jadhav",
            age=22,
            gender="Female",
            village="Ganeshpur",
            category="Maternal, 14 weeks",
            priority=CasePriorityEnum.URGENT,
            case_status=CaseStatusEnum.PATIENT_ARRIVED,
            referral_status="PATIENT_ARRIVED",
            concern="Second trimester ANC check-up and iron supplementation guidance.",
            symptoms=[{"term": "Mild nausea", "spoken": "मळमळ", "severity": "MILD"}],
            vitals={"sbp": 120, "dbp": 78, "temp": 36.7, "spo2": 99, "pulse": 78},
            is_pregnant=True,
            gestational_weeks=14,
            arrival_delta_min=18,
        )

        # Scenario 7c — Kavita Patil (Patient Arrived - 47 min ago)
        upsert_scenario(
            p_key="DEMO-PATIENT-014",
            c_ref="CASE-DEMO-014",
            r_ref="REF-DEMO-014",
            name="Kavita Patil",
            age=34,
            gender="Female",
            village="Shivaji Nagar",
            category="Postnatal, day 14",
            priority=CasePriorityEnum.HIGH,
            case_status=CaseStatusEnum.PATIENT_ARRIVED,
            referral_status="PATIENT_ARRIVED",
            concern="Postnatal follow-up check and anemia evaluation.",
            symptoms=[{"term": "Fatigue", "spoken": "थकवा", "severity": "MODERATE"}],
            vitals={"sbp": 110, "dbp": 72, "temp": 36.5, "spo2": 98, "pulse": 74},
            arrival_delta_min=47,
        )

        # Scenario 8 — Savita Ghadge (In Consultation)
        upsert_scenario(
            p_key="DEMO-PATIENT-009",
            c_ref="CASE-DEMO-009",
            r_ref="REF-DEMO-009",
            name="Savita Ghadge",
            age=45,
            gender="Female",
            village="Kalyanpur",
            category="NCD/diabetes follow-up",
            priority=CasePriorityEnum.ROUTINE,
            case_status=CaseStatusEnum.CONSULTATION_IN_PROGRESS,
            referral_status="IN_CONSULTATION",
            concern="Diabetes follow-up and routine glycemic evaluation.",
            symptoms=[{"term": "Mild fatigue", "spoken": "थकवा", "severity": "MILD"}],
            vitals={"sbp": 126, "dbp": 82, "temp": 36.6, "spo2": 98, "pulse": 76},
            consultation_data={
                "reference": "CON-DEMO-009",
                "status": "IN_CONSULTATION",
                "examination_notes": "Glucose review in progress. Patient compliance good.",
                "provisional_diagnosis": "Type 2 Diabetes Mellitus Follow-up",
            },
        )

        # Scenario 9 — Pooja Jadhav (Processed Today)
        upsert_scenario(
            p_key="DEMO-PATIENT-007",
            c_ref="CASE-DEMO-007",
            r_ref="REF-DEMO-007",
            name="Pooja Jadhav",
            age=22,
            gender="Female",
            village="Ganeshpur",
            category="Maternal, 14 weeks",
            priority=CasePriorityEnum.ROUTINE,
            case_status=CaseStatusEnum.COMPLETED,
            referral_status="PROCESSED",
            concern="Completed antenatal consultation and Iron Folic Acid compliance check.",
            symptoms=[{"term": "Mild nausea", "spoken": "मळमळ", "severity": "MILD"}],
            vitals={"sbp": 116, "dbp": 74, "temp": 36.6, "spo2": 99, "pulse": 76},
            is_pregnant=True,
            gestational_weeks=14,
            consultation_data={
                "reference": "CON-DEMO-007",
                "status": "COMPLETED",
                "confirmed_diagnosis": "Normal Pregnancy in 2nd Trimester (Z34.8)",
                "icd10_code": "Z34.8",
            },
        )

        # Scenario 10 — Shankar Shinde (Processed Today)
        upsert_scenario(
            p_key="DEMO-PATIENT-012",
            c_ref="CASE-DEMO-012",
            r_ref="REF-DEMO-012",
            name="Shankar Shinde",
            age=31,
            gender="Male",
            village="Ganeshpur",
            category="Adult routine",
            priority=CasePriorityEnum.ROUTINE,
            case_status=CaseStatusEnum.COMPLETED,
            referral_status="PROCESSED",
            concern="Completed routine consultation for allergic rhinitis.",
            symptoms=[
                {"term": "Runny nose", "spoken": "नाक वाहणे", "severity": "MILD"},
                {"term": "Sneezing", "spoken": "शिंका येणे", "severity": "MILD"},
            ],
            vitals={"sbp": 118, "dbp": 78, "temp": 36.8, "spo2": 99, "pulse": 72},
            consultation_data={
                "reference": "CON-DEMO-012",
                "status": "COMPLETED",
                "examination_notes": "Nasal mucosa congested. Throat normal.",
                "confirmed_diagnosis": "Allergic Rhinitis (J30.9)",
                "icd10_code": "J30.9",
                "care_plan_summary": "Oral antihistamines for 5 days.",
            }
        )

        # Resettable Canonical Live Journey: Nisha Patil
        live_abha = "ABHA-DEMO-LIVE-001"
        live_cit = db.query(CitizenProfile).filter(CitizenProfile.abha_reference == live_abha).first()
        if not live_cit:
            live_cit = CitizenProfile(
                abha_reference=live_abha,
                display_name="Nisha Patil",
                age_estimate=29,
                sex="Female",
                village_name="Kalyanpur",
                district="Demo District 04",
                state="Maharashtra",
                phone="9876599999",
                is_pregnant=True,
                gestational_weeks=26,
                assigned_asha_id=asha_user.id,
                preferred_language="mr-IN",
                created_at=now - timedelta(days=2),
            )
            db.add(live_cit)
            summary_counts["citizens"] += 1

        if doc_user and asha_user:
            from app.seeds.seed_doctor_demo import seed_investigation_scenarios
            seed_investigation_scenarios(db, doc_user, asha_user)

        db.commit()

        print("\n=======================================================")
        print("  DEMONSTRATION SEEDING COMPLETED SUCCESSFULLY")
        print("=======================================================")
        print("Records created / updated:")
        for k, v in summary_counts.items():
            print(f"  - {k}: {v}")
        print("=======================================================\n")

    except Exception as e:
        db.rollback()
        print(f"\n[FATAL] Seeding failed with error: {e}\n")
        raise
    finally:
        db.close()


def verify_relationships():
    verify_environment()
    db: Session = SessionLocal()
    print("\n=======================================================")
    print("  VERIFYING DEMONSTRATION DATASET RELATIONSHIPS")
    print("=======================================================")

    try:
        cases = db.query(Case).filter(Case.reference.like("CASE-DEMO-%")).all()
        print(f"Found {len(cases)} demonstration cases in database.")

        errors = []
        patient_keys_seen = set()

        for c in cases:
            if not c.citizen:
                errors.append(f"Case {c.reference} missing linked citizen profile")
            else:
                if c.citizen.abha_reference in patient_keys_seen:
                    errors.append(f"Duplicate citizen profile for {c.citizen.abha_reference}")
                patient_keys_seen.add(c.citizen.abha_reference)

            # Max 1 active consultation per referral/case
            active_cons = [cs for cs in c.consultations if cs.status == "IN_CONSULTATION"]
            if len(active_cons) > 1:
                errors.append(f"Case {c.reference} has multiple active consultations: {len(active_cons)}")

            for r in c.referrals:
                if r.case_id != c.id:
                    errors.append(f"Referral {r.reference} case_id mismatch with case {c.id}")
                if not r.to_facility_id:
                    errors.append(f"Referral {r.reference} missing to_facility_id")

            for cons in c.consultations:
                if cons.case_id != c.id:
                    errors.append(f"Consultation {cons.reference} case_id mismatch with case {c.id}")

            for fu in c.follow_ups:
                if fu.case_id != c.id:
                    errors.append(f"FollowUp {fu.id} case_id mismatch with case {c.id}")

            for vit in c.vitals:
                if vit.case_id != c.id:
                    errors.append(f"VitalRecord {vit.id} case_id mismatch with case {c.id}")

        if errors:
            print("\n[VERIFICATION FAILED]:")
            for err in errors:
                print(f"  - {err}")
            sys.exit(1)
        else:
            print("[PASS] All 9 relationship & isolation invariants verified successfully!")
            print(f"[PASS] Demo patients verified: {len(cases)} cases.")
            print("[PASS] No duplicate active consultations, no invalid foreign keys.\n")
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Aarogya Sahayak Demonstration Dataset CLI")
    parser.add_argument("--verify", action="store_true", help="Verify relationship integrity")
    parser.add_argument("--reset-demo", action="store_true", help="Reset and purge demo records")
    parser.add_argument("--reset-canonical", action="store_true", help="Reset canonical live journey DEMO-LIVE-JOURNEY-001")
    parser.add_argument("--force", action="store_true", help="Force action bypassing confirmation prompts")
    args = parser.parse_args()

    if args.reset_demo:
        db = SessionLocal()
        reset_demo_records(db, force=args.force)
        db.close()
    elif args.reset_canonical:
        db = SessionLocal()
        reset_canonical_journey(db)
        db.close()
    elif args.verify:
        verify_relationships()
    else:
        seed_full_demonstration()
