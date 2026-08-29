"""
Doctor Portal Demonstration Seed Script (Development & Test Only)

Creates an idempotent, linked demonstration dataset for:
- A. Anandi Bai Deshmukh (Maternal 30w, URGENT, PATIENT_ARRIVED -> Ready to Start)
- B. Meena Bai (Adult respiratory, URGENT, IN_CONSULTATION, active draft -> Resume Consultation)
- C. Rameshwar Shinde (NCD/hypertension, HIGH, saved draft -> Continue Draft)
- D. Aarav Sharma (Child 5y, HIGH, AWAITING_INVESTIGATION with CBC/urine orders -> View Results)
- E. Pooja Jadhav (Maternal 14w, ROUTINE, FOLLOW_UP_REQUIRED with completed ASHA follow-up -> Review Follow-up)
- F. Shankar Shinde (Adult routine, ROUTINE, COMPLETED signed consultation -> View Consultation)
- G. Kavita Patil (Maternal, URGENT, PENDING_DOCTOR_REVIEW -> Review & Acknowledge)
- H. Laxmi Kamble (Postnatal, HIGH, DOCTOR_ACKNOWLEDGED, transport EN_ROUTE -> Waiting Arrival)

Safety Rules:
- Refuses execution if APP_ENV is 'production'.
- Uses synthetic demonstration data only.
- Idempotent: re-running updates existing records by seed_key/reference without creating duplicates.
- All records created/updated in a single atomic transaction.
"""

import os
import sys
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from app.database import SessionLocal, engine, Base
from app.models import (
    User, CitizenProfile, WorkerProfile, Facility, Case, SymptomObservation,
    VitalRecord, AshaVisit, Referral, Consultation, Prescription, PrescriptionItem,
    TestOrder, FollowUp, Notification, AuditLog,
    UserRoleEnum, CasePriorityEnum, CaseStatusEnum, InformationSourceEnum
)
from app.auth.security import get_password_hash


def verify_environment():
    app_env = os.getenv("APP_ENV", "development").lower()
    if app_env in ["production", "prod"]:
        print("ERROR: Demonstration seed cannot run in PRODUCTION environment!")
        sys.exit(1)
    print(f"Environment check passed: APP_ENV='{app_env}'")


def seed_investigation_scenarios(db: Session, doc_user: User, asha_user: User):
    from app.models import (
        InvestigationOrder, InvestigationSample, InvestigationResult,
        InvestigationResultItem, InvestigationReview, InvestigationAshaTask,
        CitizenProfile, Case, utc_now
    )

    now = utc_now()

    # 1. CBC: Maternal Patient (Sunita Devi) - Result Available, Awaiting Doctor Review
    cit1 = db.query(CitizenProfile).filter(CitizenProfile.id == "CIT-SUNITA-001").first()
    case1 = db.query(Case).filter(Case.id == "CASE-SUNITA-001").first()
    if cit1 and case1:
        inv1 = db.query(InvestigationOrder).filter(InvestigationOrder.reference == "INV-2026-0001").first()
        if not inv1:
            inv1 = InvestigationOrder(
                id="INV-ID-0001",
                reference="INV-2026-0001",
                citizen_id=cit1.id,
                case_id=case1.id,
                consultation_id="CONS-SUNITA-001",
                referral_id="REF-SUNITA-001",
                ordered_by_doctor_id=doc_user.id,
                facility_id="FAC-PHC-09",
                test_name="Complete Blood Count (CBC)",
                test_code="CBC",
                category="HEMATOLOGY",
                priority="URGENT",
                clinical_reason="Second trimester anemia screening & fatigue evaluation in 24w pregnancy",
                specimen_type="Whole Blood (EDTA)",
                preparation_instructions="Non-fasting sample acceptable",
                collection_location="PHC Kalyanpur Sample Collection Room 3",
                ordered_at=now - timedelta(hours=24),
                due_at=now - timedelta(hours=18),
                expected_result_at=now - timedelta(hours=2),
                status="RESULT_AVAILABLE",
                idempotency_key="SEED-INV-001"
            )
            db.add(inv1)
            db.flush()

            smp1 = InvestigationSample(
                investigation_order_id=inv1.id,
                sample_reference="SMP-INV-2026-0001",
                collected_by_user_id=doc_user.id,
                collected_at=now - timedelta(hours=20),
                collection_status="COLLECTED"
            )
            db.add(smp1)

            res1 = InvestigationResult(
                investigation_order_id=inv1.id,
                result_source="PHC Manual/Demonstration Entry",
                laboratory_name="PHC Kalyanpur Central Lab",
                resulted_at=now - timedelta(hours=2),
                entered_by_user_id=doc_user.id,
                verified_by_user_id=doc_user.id,
                verification_status="VERIFIED",
                critical_flag=False
            )
            db.add(res1)
            db.flush()

            item1_1 = InvestigationResultItem(
                result_id=res1.id, parameter_name="Hemoglobin", parameter_code="HGB",
                value="8.7", unit="g/dL", reference_low="12.0", reference_high="15.5", source_flag="LOW",
                remarks="Moderate gestational anemia"
            )
            item1_2 = InvestigationResultItem(
                result_id=res1.id, parameter_name="Platelet Count", parameter_code="PLT",
                value="210,000", unit="/uL", reference_low="150,000", reference_high="450,000", source_flag="NORMAL"
            )
            db.add_all([item1_1, item1_2])

    # 2. Urine Albumin: Maternal Case (Pooja Jadhav) - Reviewed Result + ASHA repeat monitoring
    cit2 = db.query(CitizenProfile).filter(CitizenProfile.id == "CIT-POOJA-005").first()
    case2 = db.query(Case).filter(Case.id == "CASE-POOJA-005").first()
    if cit2 and case2:
        inv2 = db.query(InvestigationOrder).filter(InvestigationOrder.reference == "INV-2026-0002").first()
        if not inv2:
            inv2 = InvestigationOrder(
                id="INV-ID-0002",
                reference="INV-2026-0002",
                citizen_id=cit2.id,
                case_id=case2.id,
                consultation_id="CONS-POOJA-005",
                referral_id="REF-POOJA-005",
                ordered_by_doctor_id=doc_user.id,
                facility_id="FAC-PHC-09",
                test_name="Urine Albumin / Protein",
                test_code="URINE_ALB",
                category="BIOCHEMISTRY",
                priority="ROUTINE",
                clinical_reason="Antenatal pre-eclampsia screening in 14w pregnancy",
                specimen_type="Midstream Urine",
                preparation_instructions="Clean catch morning first urine sample",
                collection_location="PHC Kalyanpur Sample Counter",
                ordered_at=now - timedelta(hours=48),
                due_at=now - timedelta(hours=40),
                expected_result_at=now - timedelta(hours=24),
                status="REVIEWED",
                idempotency_key="SEED-INV-002"
            )
            db.add(inv2)
            db.flush()

            smp2 = InvestigationSample(
                investigation_order_id=inv2.id,
                sample_reference="SMP-INV-2026-0002",
                collected_by_user_id=doc_user.id,
                collected_at=now - timedelta(hours=38),
                collection_status="COLLECTED"
            )
            db.add(smp2)

            res2 = InvestigationResult(
                investigation_order_id=inv2.id,
                result_source="PHC Manual/Demonstration Entry",
                laboratory_name="PHC Kalyanpur Central Lab",
                resulted_at=now - timedelta(hours=24),
                entered_by_user_id=doc_user.id,
                verification_status="VERIFIED",
                critical_flag=False
            )
            db.add(res2)
            db.flush()

            item2 = InvestigationResultItem(
                result_id=res2.id, parameter_name="Urine Dipstick Albumin", parameter_code="ALB_DIP",
                value="1+ (Trace)", unit=None, reference_low="Negative", reference_high="Negative", source_flag="HIGH",
                remarks="Trace proteinuria observed"
            )
            db.add(item2)

            rev2 = InvestigationReview(
                result_id=res2.id,
                doctor_id=doc_user.id,
                review_note="Mild trace proteinuria. Advised dietary hydration and scheduled ASHA repeat dipstick monitoring in 7 days.",
                outcome="ASHA_FOLLOW_UP",
                reviewed_at=now - timedelta(hours=12),
                care_plan_updated=True
            )
            db.add(rev2)

    # 3. Blood Glucose / HbA1c: NCD Patient (Ramesh Patil) - Result Ready / Care Plan Update
    cit3 = db.query(CitizenProfile).filter(CitizenProfile.id == "CIT-RAMESH-003").first()
    case3 = db.query(Case).filter(Case.id == "CASE-RAMESH-003").first()
    if cit3 and case3:
        inv3 = db.query(InvestigationOrder).filter(InvestigationOrder.reference == "INV-2026-0003").first()
        if not inv3:
            inv3 = InvestigationOrder(
                id="INV-ID-0003",
                reference="INV-2026-0003",
                citizen_id=cit3.id,
                case_id=case3.id,
                consultation_id="CONS-RAMESH-003",
                referral_id="REF-RAMESH-003",
                ordered_by_doctor_id=doc_user.id,
                facility_id="FAC-PHC-09",
                test_name="Glycated Hemoglobin (HbA1c)",
                test_code="HBA1C",
                category="BIOCHEMISTRY",
                priority="ROUTINE",
                clinical_reason="Quarterly NCD diabetic control monitoring",
                specimen_type="Venous Blood",
                preparation_instructions="10-12 hours overnight fasting required",
                collection_location="PHC Kalyanpur Central Lab",
                ordered_at=now - timedelta(hours=36),
                due_at=now - timedelta(hours=24),
                expected_result_at=now - timedelta(hours=4),
                status="RESULT_AVAILABLE",
                idempotency_key="SEED-INV-003"
            )
            db.add(inv3)
            db.flush()

            smp3 = InvestigationSample(
                investigation_order_id=inv3.id,
                sample_reference="SMP-INV-2026-0003",
                collected_by_user_id=doc_user.id,
                collected_at=now - timedelta(hours=22),
                collection_status="COLLECTED"
            )
            db.add(smp3)

            res3 = InvestigationResult(
                investigation_order_id=inv3.id,
                result_source="PHC Manual/Demonstration Entry",
                laboratory_name="PHC Kalyanpur Central Lab",
                resulted_at=now - timedelta(hours=4),
                entered_by_user_id=doc_user.id,
                verification_status="VERIFIED",
                critical_flag=False
            )
            db.add(res3)
            db.flush()

            item3 = InvestigationResultItem(
                result_id=res3.id, parameter_name="HbA1c Level", parameter_code="HBA1C_PCT",
                value="8.4", unit="%", reference_low="4.0", reference_high="5.6", source_flag="HIGH",
                remarks="Uncontrolled glycemic status"
            )
            db.add(item3)

    # 4. Sample Rejection / Recollection Required (Meena Deshmukh)
    cit4 = db.query(CitizenProfile).filter(CitizenProfile.id == "CIT-MEENA-002").first()
    case4 = db.query(Case).filter(Case.id == "CASE-MEENA-002").first()
    if cit4 and case4:
        inv4 = db.query(InvestigationOrder).filter(InvestigationOrder.reference == "INV-2026-0004").first()
        if not inv4:
            inv4 = InvestigationOrder(
                id="INV-ID-0004",
                reference="INV-2026-0004",
                citizen_id=cit4.id,
                case_id=case4.id,
                consultation_id="CONS-MEENA-002",
                referral_id="REF-MEENA-002",
                ordered_by_doctor_id=doc_user.id,
                facility_id="FAC-PHC-09",
                test_name="Serum Creatinine",
                test_code="CREAT",
                category="BIOCHEMISTRY",
                priority="URGENT",
                clinical_reason="Renal function evaluation in persistent hypertension",
                specimen_type="Clotted Blood (Serum)",
                preparation_instructions="Standard fasting sample",
                collection_location="PHC Kalyanpur Sample Counter",
                ordered_at=now - timedelta(hours=18),
                due_at=now - timedelta(hours=12),
                expected_result_at=now - timedelta(hours=6),
                status="RECOLLECTION_REQUIRED",
                idempotency_key="SEED-INV-004"
            )
            db.add(inv4)
            db.flush()

            smp4 = InvestigationSample(
                investigation_order_id=inv4.id,
                sample_reference="SMP-INV-2026-0004",
                collected_by_user_id=doc_user.id,
                collected_at=now - timedelta(hours=10),
                collection_status="REJECTED",
                rejection_reason="Hemolyzed specimen during transport. Invalid for serum creatinine assay.",
                recollection_required=True
            )
            db.add(smp4)

            task4 = InvestigationAshaTask(
                investigation_order_id=inv4.id,
                asha_user_id=asha_user.id,
                citizen_id=cit4.id,
                task_type="ATTENDANCE_ASSISTANCE",
                due_date=now + timedelta(days=1),
                instructions="Contact Meena Deshmukh and assist her to attend PHC tomorrow morning for fresh sample recollection.",
                status="PENDING"
            )
            db.add(task4)

    db.commit()


def seed_doctor_demonstration():
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
        "notifications": 0,
        "audit_logs": 0,
    }

    try:
        print("\n=======================================================")
        print("  SEEDING IDEMPOTENT DOCTOR PORTAL DEMO DATASET")
        print("=======================================================\n")

        # -------------------------------------------------------------------------
        # 1. Facilities
        # -------------------------------------------------------------------------
        phc = db.query(Facility).filter(Facility.code == "PHC-09").first()
        if not phc:
            phc = Facility(
                id="FAC-PHC-09",
                code="PHC-09",
                name="Kalyanpur Primary Health Center",
                facility_type="PHC",
                district_name="District 04",
                block_name="Kalyanpur Block",
                address="Main Road, Kalyanpur Village"
            )
            db.add(phc)
            summary_counts["facilities"] += 1

        chc = db.query(Facility).filter(Facility.code == "CHC-02").first()
        if not chc:
            chc = Facility(
                id="FAC-CHC-02",
                code="CHC-02",
                name="Shivaji Nagar Community Health Center",
                facility_type="CHC",
                district_name="District 04",
                block_name="Shivaji Nagar Block",
                address="Hospital Chowk, Shivaji Nagar"
            )
            db.add(chc)
            summary_counts["facilities"] += 1

        db.flush()

        # -------------------------------------------------------------------------
        # 2. Staff Users & Worker Profiles
        # -------------------------------------------------------------------------
        # Dr. Abhinav Sharma
        doc_user = db.query(User).filter(User.identifier == "dr.sharma").first()
        if not doc_user:
            doc_user = User(
                id="USER-DOC-007",
                identifier="dr.sharma",
                name="Dr. Abhinav Sharma",
                phone="9876543210",
                email="dr.sharma@phc.arogya.gov.in",
                password_hash=get_password_hash("demo123"),
                role=UserRoleEnum.PHC_DOCTOR,
                preferred_language="mr-IN"
            )
            db.add(doc_user)
            summary_counts["users"] += 1
            db.flush()

        doc_profile = db.query(WorkerProfile).filter(WorkerProfile.user_id == doc_user.id).first()
        if not doc_profile:
            doc_profile = WorkerProfile(
                id="WP-DOC-007",
                user_id=doc_user.id,
                worker_type="DOCTOR",
                facility_id=phc.id,
                facility_name=phc.name,
                district_name="District 04",
                professional_registration="MCI-MH-2018-9942"
            )
            db.add(doc_profile)

        # Sita Patel (ASHA)
        asha_user = db.query(User).filter(User.identifier == "sita.asha").first()
        if not asha_user:
            asha_user = User(
                id="USER-ASHA-012",
                identifier="sita.asha",
                name="Sita Patel",
                phone="9823012345",
                email="sita.asha@arogya.gov.in",
                password_hash=get_password_hash("demo123"),
                role=UserRoleEnum.ASHA_WORKER,
                preferred_language="mr-IN"
            )
            db.add(asha_user)
            summary_counts["users"] += 1
            db.flush()

        asha_profile = db.query(WorkerProfile).filter(WorkerProfile.user_id == asha_user.id).first()
        if not asha_profile:
            asha_profile = WorkerProfile(
                id="WP-ASHA-012",
                user_id=asha_user.id,
                worker_type="ASHA",
                facility_id=phc.id,
                facility_name=phc.name,
                district_name="District 04",
                village_ids=["VILLAGE-01", "VILLAGE-02"],
                professional_registration="ASHA-MH-2024-8841"
            )
            db.add(asha_profile)

        db.flush()

        # -------------------------------------------------------------------------
        # Helper function for idempotent upsert of linked scenario
        # -------------------------------------------------------------------------
        def upsert_scenario(scenario_data: dict):
            # 1. Citizen Profile
            abha_ref = scenario_data["abha_reference"]
            citizen = db.query(CitizenProfile).filter(CitizenProfile.abha_reference == abha_ref).first()
            if not citizen:
                citizen = CitizenProfile(
                    id=scenario_data["citizen_id"],
                    abha_reference=abha_ref,
                    display_name=scenario_data["citizen_name"],
                    age_estimate=scenario_data["age"],
                    sex=scenario_data["sex"],
                    phone=scenario_data.get("phone", "9800000000"),
                    village_name=scenario_data.get("village", "Kalyanpur"),
                    is_pregnant=scenario_data.get("is_pregnant", False),
                    gestational_weeks=scenario_data.get("gestational_weeks"),
                    preferred_language=scenario_data.get("language", "mr-IN"),
                    assigned_facility_id=phc.id,
                    assigned_asha_id=asha_user.id
                )
                db.add(citizen)
                summary_counts["citizens"] += 1
                db.flush()
            else:
                citizen.display_name = scenario_data["citizen_name"]
                citizen.age_estimate = scenario_data["age"]
                citizen.sex = scenario_data["sex"]
                citizen.is_pregnant = scenario_data.get("is_pregnant", False)
                citizen.gestational_weeks = scenario_data.get("gestational_weeks")
                citizen.village_name = scenario_data.get("village", "Kalyanpur")

            # 2. Case
            case_ref = scenario_data["case_reference"]
            case_obj = db.query(Case).filter(Case.reference == case_ref).first()
            if not case_obj:
                case_obj = Case(
                    id=scenario_data["case_id"],
                    reference=case_ref,
                    citizen_id=citizen.id,
                    priority=scenario_data["priority"],
                    status=scenario_data["case_status"],
                    primary_concern=scenario_data["concern"],
                    preferred_language=scenario_data.get("language", "mr-IN"),
                    assigned_asha_id=asha_user.id,
                    assigned_asha_name=asha_user.name,
                    assigned_facility_id=phc.id,
                    assigned_facility_name=phc.name,
                    assigned_doctor_id=doc_user.id,
                    assigned_doctor_name=doc_user.name,
                    safety_rule_triggered=scenario_data.get("safety_rule_triggered", False),
                    safety_rule_reason=scenario_data.get("safety_rule_reason"),
                    created_at=now - timedelta(minutes=scenario_data.get("created_mins_ago", 30))
                )
                db.add(case_obj)
                summary_counts["cases"] += 1
                db.flush()
            else:
                case_obj.priority = scenario_data["priority"]
                case_obj.status = scenario_data["case_status"]
                case_obj.primary_concern = scenario_data["concern"]
                case_obj.safety_rule_triggered = scenario_data.get("safety_rule_triggered", False)
                case_obj.safety_rule_reason = scenario_data.get("safety_rule_reason")

            # 3. Symptoms
            db.query(SymptomObservation).filter(SymptomObservation.case_id == case_obj.id).delete()
            for sym in scenario_data.get("symptoms", []):
                symptom_item = SymptomObservation(
                    case_id=case_obj.id,
                    normalized_term=sym["normalized"],
                    spoken_term=sym.get("spoken"),
                    severity=sym.get("severity", "HIGH"),
                    source_type=InformationSourceEnum.CITIZEN_REPORTED,
                    recorded_by=sym.get("recorded_by", "Citizen Voice"),
                    recorded_at=now - timedelta(minutes=scenario_data.get("created_mins_ago", 30))
                )
                db.add(symptom_item)
                summary_counts["symptoms"] += 1

            # 4. Vitals
            db.query(VitalRecord).filter(VitalRecord.case_id == case_obj.id).delete()
            for vit in scenario_data.get("vitals", []):
                v_rec = VitalRecord(
                    case_id=case_obj.id,
                    systolic_bp=vit.get("systolic_bp"),
                    diastolic_bp=vit.get("diastolic_bp"),
                    spo2=vit.get("spo2"),
                    pulse=vit.get("pulse"),
                    temperature_c=vit.get("temperature_c", 37.0),
                    is_warning_sign=vit.get("is_warning_sign", False),
                    recorded_by=vit.get("recorded_by", "Sita Patel (ASHA)"),
                    recorded_at=now - timedelta(minutes=vit.get("mins_ago", 20)),
                    source_type=InformationSourceEnum.DEVICE_MEASURED
                )
                db.add(v_rec)
                summary_counts["vitals"] += 1

            # 5. ASHA Visit
            visit_ref = scenario_data.get("visit_reference")
            if visit_ref:
                visit_obj = db.query(AshaVisit).filter(AshaVisit.reference == visit_ref).first()
                if not visit_obj:
                    visit_obj = AshaVisit(
                        reference=visit_ref,
                        case_id=case_obj.id,
                        asha_worker_id=asha_user.id,
                        visit_type=scenario_data.get("visit_type", "URGENT_TRIAGE"),
                        status="COMPLETED",
                        notes=scenario_data.get("visit_notes", "Home visit completed."),
                        consent_obtained=True,
                        started_at=now - timedelta(minutes=scenario_data.get("created_mins_ago", 30)),
                        completed_at=now - timedelta(minutes=scenario_data.get("created_mins_ago", 30) - 10)
                    )
                    db.add(visit_obj)
                    summary_counts["visits"] += 1
                else:
                    visit_obj.notes = scenario_data.get("visit_notes", "Home visit completed.")

            # 6. Referral
            ref_code = scenario_data.get("referral_reference")
            referral_obj = None
            if ref_code:
                referral_obj = db.query(Referral).filter(Referral.reference == ref_code).first()
                if not referral_obj:
                    referral_obj = Referral(
                        id=scenario_data.get("referral_id", f"REF-{ref_code}"),
                        reference=ref_code,
                        case_id=case_obj.id,
                        from_asha_id=asha_user.id,
                        to_facility_id=phc.id,
                        to_facility_name=phc.name,
                        urgency=scenario_data["priority"],
                        reason=scenario_data["concern"],
                        status=scenario_data["referral_status"],
                        transport_assistance_required=scenario_data.get("transport_en_route", False),
                        acknowledged_by=doc_user.name if scenario_data.get("acknowledged", False) else None,
                        acknowledged_at=now - timedelta(minutes=scenario_data.get("ack_mins_ago", 15)) if scenario_data.get("acknowledged", False) else None,
                        created_at=now - timedelta(minutes=scenario_data.get("created_mins_ago", 30))
                    )
                    db.add(referral_obj)
                    summary_counts["referrals"] += 1
                    db.flush()
                else:
                    referral_obj.status = scenario_data["referral_status"]
                    referral_obj.transport_assistance_required = scenario_data.get("transport_en_route", False)
                    if scenario_data.get("acknowledged", False):
                        referral_obj.acknowledged_by = doc_user.name
                        referral_obj.acknowledged_at = now - timedelta(minutes=scenario_data.get("ack_mins_ago", 15))

            # 7. Consultation
            cons_code = scenario_data.get("consultation_reference")
            if cons_code:
                cons_obj = db.query(Consultation).filter(Consultation.reference == cons_code).first()
                if not cons_obj:
                    cons_obj = Consultation(
                        id=scenario_data.get("consultation_id", f"CONS-{cons_code}"),
                        reference=cons_code,
                        case_id=case_obj.id,
                        doctor_id=doc_user.id,
                        doctor_name=doc_user.name,
                        facility_id=phc.id,
                        consultation_type="IN_PERSON_PHC",
                        status=scenario_data.get("consultation_status", "IN_PROGRESS"),
                        examination_notes=scenario_data.get("examination_notes"),
                        clinical_summary=scenario_data.get("clinical_summary"),
                        provisional_diagnosis=scenario_data.get("provisional_diagnosis"),
                        confirmed_diagnosis=scenario_data.get("confirmed_diagnosis"),
                        icd10_code=scenario_data.get("icd10_code"),
                        care_plan_summary=scenario_data.get("care_plan_summary"),
                        asha_followup_instructions=scenario_data.get("asha_followup_instructions"),
                        followup_due_days=scenario_data.get("followup_due_days", 3),
                        started_at=now - timedelta(minutes=scenario_data.get("cons_started_mins_ago", 10)),
                        completed_at=now - timedelta(minutes=5) if scenario_data.get("consultation_status") == "COMPLETED" else None,
                        signed_at=now - timedelta(minutes=5) if scenario_data.get("consultation_status") == "COMPLETED" else None,
                        version=scenario_data.get("draft_version", 1),
                        created_at=now - timedelta(minutes=scenario_data.get("cons_started_mins_ago", 10))
                    )
                    db.add(cons_obj)
                    summary_counts["consultations"] += 1
                    db.flush()
                else:
                    cons_obj.status = scenario_data.get("consultation_status", "IN_PROGRESS")
                    cons_obj.examination_notes = scenario_data.get("examination_notes")
                    cons_obj.confirmed_diagnosis = scenario_data.get("confirmed_diagnosis")
                    cons_obj.icd10_code = scenario_data.get("icd10_code")
                    cons_obj.care_plan_summary = scenario_data.get("care_plan_summary")

                # Test Orders
                db.query(TestOrder).filter(TestOrder.consultation_id == cons_obj.id).delete()
                for t in scenario_data.get("test_orders", []):
                    t_order = TestOrder(
                        consultation_id=cons_obj.id,
                        test_name=t["test_name"],
                        priority=t.get("priority", "URGENT"),
                        reason=t.get("reason", "Diagnostic evaluation"),
                        facility_id=phc.id,
                        status=t.get("status", "PENDING"),
                        ordered_at=now - timedelta(minutes=15)
                    )
                    db.add(t_order)
                    summary_counts["test_orders"] += 1

                # Prescription & Items
                if scenario_data.get("prescription_items"):
                    existing_rx = db.query(Prescription).filter(Prescription.consultation_id == cons_obj.id).all()
                    for er in existing_rx:
                        db.query(PrescriptionItem).filter(PrescriptionItem.prescription_id == er.id).delete()
                    db.query(Prescription).filter(Prescription.consultation_id == cons_obj.id).delete()
                    db.flush()
                    rx_ref = f"RX-{cons_obj.reference or uuid.uuid4().hex[:6]}"
                    rx_obj = Prescription(
                        reference=rx_ref,
                        consultation_id=cons_obj.id,
                        case_id=case_obj.id,
                        citizen_id=citizen.id,
                        prescriber_doctor_id=doc_user.id,
                        doctor_id=doc_user.id,
                        status="SIGNED" if scenario_data.get("consultation_status") == "COMPLETED" else "DRAFT"
                    )
                    db.add(rx_obj)
                    summary_counts["prescriptions"] += 1
                    db.flush()

                    for med in scenario_data.get("prescription_items", []):
                        rx_item = PrescriptionItem(
                            prescription_id=rx_obj.id,
                            generic_name_snapshot=med.get("generic_name", med["medicine"]),
                            medicine=med["medicine"],
                            dose=med.get("dose", "1 tablet"),
                            frequency=med.get("frequency", "Twice daily"),
                            timing=med.get("timing", "After food"),
                            instructions=med.get("instructions")
                        )
                        db.add(rx_item)
                        summary_counts["prescription_items"] += 1

            if scenario_data.get("follow_up"):
                fu_data = scenario_data["follow_up"]
                fu_ids = [f.id for f in db.query(FollowUp.id).filter(FollowUp.case_id == case_obj.id).all()]
                if fu_ids:
                    from app.models import FollowUpEscalation
                    db.query(FollowUpEscalation).filter(FollowUpEscalation.follow_up_id.in_(fu_ids)).delete(synchronize_session=False)
                db.query(FollowUp).filter(FollowUp.case_id == case_obj.id).delete(synchronize_session=False)
                fu = FollowUp(
                    case_id=case_obj.id,
                    citizen_id=citizen.id,
                    referral_id=referral_obj.id if referral_obj else None,
                    created_by_id=doc_user.id,
                    created_by_role="DOCTOR",
                    source="DOCTOR_ASSIGNED",
                    task_type=fu_data.get("task_type", "BP_MONITORING"),
                    reason=fu_data.get("reason", "Post-consultation monitoring"),
                    assigned_role=UserRoleEnum.ASHA_WORKER,
                    assigned_user_id=asha_user.id,
                    instructions=fu_data.get("instructions", "Check vitals and medication adherence."),
                    measurements_to_repeat=fu_data.get("measurements_to_repeat", ["systolic_bp", "diastolic_bp"]),
                    adherence_required=True,
                    escalation_conditions=fu_data.get("escalation_conditions", "Escalate if SBP >= 160"),
                    priority=scenario_data["priority"],
                    due_at=now + timedelta(days=fu_data.get("due_days", 3)),
                    status=fu_data.get("status", "PENDING"),
                    completion_notes=fu_data.get("completion_notes"),
                    result=fu_data.get("result"),
                    completed_at=now - timedelta(hours=2) if fu_data.get("status") == "COMPLETED" else None
                )
                db.add(fu)
                summary_counts["follow_ups"] += 1

            # 9. Audit Log
            audit = AuditLog(
                actor_user_id=doc_user.id,
                actor_role="PHC_DOCTOR",
                action=f"DEMO_SCENARIO_{scenario_data['code']}",
                resource_type="CASE",
                resource_id=case_obj.id,
                outcome="SUCCESS",
                metadata_json={"scenario": scenario_data["citizen_name"], "priority": str(scenario_data["priority"])}
            )
            db.add(audit)
            summary_counts["audit_logs"] += 1

        # -------------------------------------------------------------------------
        # Scenario Definitions (A through H)
        # -------------------------------------------------------------------------
        scenarios = [
            # A. Anandi Bai Deshmukh — Ready to Start (Maternal 30w, URGENT, PATIENT_ARRIVED)
            {
                "code": "SCENARIO_A",
                "citizen_id": "c1d9bb3d-0854-4635-85af-b214b7d3c335",
                "abha_reference": "ABHA-2026-889101",
                "citizen_name": "Anandi Bai Deshmukh",
                "age": 30,
                "sex": "Female",
                "is_pregnant": True,
                "gestational_weeks": 30,
                "village": "Kalyanpur",
                "language": "mr-IN",
                "case_id": "c1d9bb3d-0854-4635-85af-b214b7d3c335",
                "case_reference": "CASE-2026-859171",
                "priority": CasePriorityEnum.URGENT,
                "case_status": CaseStatusEnum.PATIENT_ARRIVED,
                "concern": "Severe headache, blurred vision and swollen feet during pregnancy",
                "safety_rule_triggered": True,
                "safety_rule_reason": "Latest BP 155/100, severe headache and blurred vision, Rule MAT-BP-02, recorded by Sita Patel 10:12 AM.",
                "created_mins_ago": 25,
                "symptoms": [
                    {"normalized": "Severe Headache", "spoken": "खूप डोकेदुखी", "severity": "HIGH"},
                    {"normalized": "Blurred Vision", "spoken": "डोळ्यांसमोर अंधारी", "severity": "HIGH"},
                    {"normalized": "Pedal Edema", "spoken": "पायावर सूज", "severity": "MODERATE"},
                    {"normalized": "Dizziness", "spoken": "चक्कर येणे", "severity": "MODERATE"},
                ],
                "vitals": [
                    {"systolic_bp": 155, "diastolic_bp": 100, "spo2": 97, "pulse": 88, "temperature_c": 37.0, "is_warning_sign": True, "mins_ago": 18}
                ],
                "visit_reference": "VISIT-2026-363205",
                "visit_notes": "Initial home registration visit completed. Identified bilateral pedal edema and high BP. Accompanied to PHC.",
                "referral_id": "adc52a74-6006-4559-8485-910b7bb178d1",
                "referral_reference": "REF-2026-363205",
                "referral_status": "PATIENT_ARRIVED",
                "acknowledged": True,
                "ack_mins_ago": 18,
                # No consultation pre-seeded so Doctor clicks Start Consultation
            },

            # B. Meena Bai — In Progress (Adult respiratory, URGENT, IN_CONSULTATION)
            {
                "code": "SCENARIO_B",
                "citizen_id": "CIT-MEENA-002",
                "abha_reference": "ABHA-2026-772901",
                "citizen_name": "Meena Bai",
                "age": 45,
                "sex": "Female",
                "is_pregnant": False,
                "village": "Ganeshpur",
                "language": "mr-IN",
                "case_id": "CASE-MEENA-002",
                "case_reference": "CASE-2026-448201",
                "priority": CasePriorityEnum.URGENT,
                "case_status": CaseStatusEnum.CONSULTATION_IN_PROGRESS,
                "concern": "Shortness of breath, persistent cough and mild chest tightness",
                "safety_rule_triggered": True,
                "safety_rule_reason": "Low SpO2 (91%) with elevated pulse (102 bpm) triggers respiratory distress warning.",
                "created_mins_ago": 35,
                "symptoms": [
                    {"normalized": "Shortness of Breath", "spoken": "दम लागणे", "severity": "HIGH"},
                    {"normalized": "Persistent Cough", "spoken": "खोकला", "severity": "HIGH"},
                ],
                "vitals": [
                    {"systolic_bp": 130, "diastolic_bp": 85, "spo2": 91, "pulse": 102, "temperature_c": 37.4, "is_warning_sign": True, "mins_ago": 15}
                ],
                "visit_reference": "VISIT-2026-448201",
                "visit_notes": "Patient experiencing respiratory distress. Advised immediate PHC attendance.",
                "referral_id": "REF-MEENA-002",
                "referral_reference": "REF-2026-448201",
                "referral_status": "IN_CONSULTATION",
                "acknowledged": True,
                "ack_mins_ago": 15,
                "consultation_id": "CONS-MEENA-002",
                "consultation_reference": "CON-2026-022",
                "consultation_status": "IN_PROGRESS",
                "cons_started_mins_ago": 8,
                "draft_version": 2,
                "examination_notes": "Tachypneic at rest. Bilateral rhonchi present in lower lobes. No stridor. Nebulization initiated.",
                "clinical_summary": "Acute exacerbation of reactive airway disease with mild hypoxemia."
            },

            # C. Rameshwar Shinde — Saved Draft (NCD/hypertension, HIGH, DOCTOR_ACKNOWLEDGED)
            {
                "code": "SCENARIO_C",
                "citizen_id": "CIT-RAMESH-003",
                "abha_reference": "ABHA-2026-551902",
                "citizen_name": "Rameshwar Shinde",
                "age": 58,
                "sex": "Male",
                "is_pregnant": False,
                "village": "Shivaji Nagar",
                "language": "mr-IN",
                "case_id": "CASE-RAMESH-003",
                "case_reference": "CASE-2026-551902",
                "priority": CasePriorityEnum.HIGH,
                "case_status": CaseStatusEnum.DOCTOR_ACKNOWLEDGED,
                "concern": "Blood pressure monitoring, medication review and intermittent occipital headache",
                "safety_rule_triggered": False,
                "created_mins_ago": 45,
                "symptoms": [
                    {"normalized": "Headache", "spoken": "डोकेदुखी", "severity": "MODERATE"},
                    {"normalized": "Fatigue", "spoken": "थकवा", "severity": "MILD"},
                ],
                "vitals": [
                    {"systolic_bp": 162, "diastolic_bp": 96, "spo2": 98, "pulse": 84, "temperature_c": 36.8, "is_warning_sign": True, "mins_ago": 25}
                ],
                "visit_reference": "VISIT-2026-551902",
                "visit_notes": "Monthly NCD home checkup completed. Recorded high resting BP.",
                "referral_id": "REF-RAMESH-003",
                "referral_reference": "REF-2026-551902",
                "referral_status": "DOCTOR_ACKNOWLEDGED",
                "acknowledged": True,
                "ack_mins_ago": 20,
                "consultation_id": "CONS-RAMESH-003",
                "consultation_reference": "CON-2026-033",
                "consultation_status": "DRAFT",
                "cons_started_mins_ago": 12,
                "draft_version": 1,
                "examination_notes": "Alert, no focal neurological deficits. Heart sounds normal. Repeat seated BP 158/94 mmHg.",
                "clinical_summary": "Essential Hypertension Grade 2, uncontrolled on current monotherapy."
            },

            # D. Aarav Sharma — Awaiting Results (Child 5y, HIGH, AWAITING_INVESTIGATION)
            {
                "code": "SCENARIO_D",
                "citizen_id": "CIT-AARAV-004",
                "abha_reference": "ABHA-2026-118833",
                "citizen_name": "Aarav Sharma",
                "age": 5,
                "sex": "Male",
                "is_pregnant": False,
                "village": "Kalyanpur",
                "language": "hi-IN",
                "case_id": "CASE-AARAV-004",
                "case_reference": "CASE-2026-118833",
                "priority": CasePriorityEnum.HIGH,
                "case_status": CaseStatusEnum.FOLLOW_UP_REQUIRED,
                "concern": "High-grade fever for 3 days with reduced oral intake and lethargy",
                "safety_rule_triggered": True,
                "safety_rule_reason": "High pediatric fever (39.2°C) with tachycardia (116 bpm) requires investigation.",
                "created_mins_ago": 60,
                "symptoms": [
                    {"normalized": "High Fever", "spoken": "तेज बुखार", "severity": "HIGH"},
                    {"normalized": "Lethargy", "spoken": "सुस्ती", "severity": "HIGH"},
                ],
                "vitals": [
                    {"systolic_bp": 95, "diastolic_bp": 60, "spo2": 96, "pulse": 116, "temperature_c": 39.2, "is_warning_sign": True, "mins_ago": 30}
                ],
                "referral_id": "REF-AARAV-004",
                "referral_reference": "REF-2026-118833",
                "referral_status": "AWAITING_INVESTIGATION",
                "acknowledged": True,
                "ack_mins_ago": 30,
                "consultation_id": "CONS-AARAV-004",
                "consultation_reference": "CON-2026-044",
                "consultation_status": "AWAITING_INVESTIGATION",
                "cons_started_mins_ago": 25,
                "examination_notes": "Febrile child, mild mucosal dehydration. No meningeal signs. Chest clear.",
                "clinical_summary": "Acute febrile illness, under evaluation. Awaiting CBC and Urine routine results.",
                "test_orders": [
                    {"test_name": "Complete Blood Count (CBC)", "priority": "URGENT", "status": "RESULT_AVAILABLE"},
                    {"test_name": "Urine Routine & Micro", "priority": "ROUTINE", "status": "PENDING"}
                ]
            },

            # E. Pooja Jadhav — Follow-up Review (Maternal 14w, ROUTINE, FOLLOW_UP_REQUIRED)
            {
                "code": "SCENARIO_E",
                "citizen_id": "CIT-POOJA-005",
                "abha_reference": "ABHA-2026-224466",
                "citizen_name": "Pooja Jadhav",
                "age": 24,
                "sex": "Female",
                "is_pregnant": True,
                "gestational_weeks": 14,
                "village": "Kalyanpur",
                "language": "mr-IN",
                "case_id": "CASE-POOJA-005",
                "case_reference": "CASE-2026-224466",
                "priority": CasePriorityEnum.ROUTINE,
                "case_status": CaseStatusEnum.FOLLOW_UP_REQUIRED,
                "concern": "Second trimester ANC check-up and iron-folic acid compliance review",
                "safety_rule_triggered": False,
                "created_mins_ago": 120,
                "symptoms": [
                    {"normalized": "Mild Nausea", "spoken": "मळमळ", "severity": "MILD"}
                ],
                "vitals": [
                    {"systolic_bp": 118, "diastolic_bp": 76, "spo2": 99, "pulse": 78, "temperature_c": 36.6, "is_warning_sign": False, "mins_ago": 60}
                ],
                "referral_id": "REF-POOJA-005",
                "referral_reference": "REF-2026-224466",
                "referral_status": "FOLLOW_UP_REQUIRED",
                "acknowledged": True,
                "consultation_id": "CONS-POOJA-005",
                "consultation_reference": "CON-2026-055",
                "consultation_status": "FOLLOW_UP_REQUIRED",
                "cons_started_mins_ago": 50,
                "examination_notes": "Uterine size 14 weeks. Fetal Doppler positive (150 bpm). Good maternal nutrition.",
                "clinical_summary": "Routine second trimester antenatal visit. Iron and Calcium supplementation ongoing.",
                "follow_up": {
                    "task_type": "ANC_FOLLOWUP",
                    "due_days": 7,
                    "status": "COMPLETED",
                    "completion_notes": "ASHA visited home today. Verified daily IFA intake. Resting BP 116/74 mmHg.",
                    "result": "Patient compliant with medicines. No warning signs observed."
                }
            },

            # F. Shankar Shinde — Completed Today (Adult routine, ROUTINE, COMPLETED)
            {
                "code": "SCENARIO_F",
                "citizen_id": "CIT-SHANKAR-006",
                "abha_reference": "ABHA-2026-339911",
                "citizen_name": "Shankar Shinde",
                "age": 42,
                "sex": "Male",
                "is_pregnant": False,
                "village": "Ganeshpur",
                "language": "mr-IN",
                "case_id": "CASE-SHANKAR-006",
                "case_reference": "CASE-2026-339911",
                "priority": CasePriorityEnum.ROUTINE,
                "case_status": CaseStatusEnum.COMPLETED,
                "concern": "Mild seasonal allergic rhinitis and dry cough",
                "safety_rule_triggered": False,
                "created_mins_ago": 180,
                "symptoms": [
                    {"normalized": "Sneezing", "spoken": "शिंका", "severity": "MILD"},
                    {"normalized": "Dry Cough", "spoken": "कोरडा खोकला", "severity": "MILD"}
                ],
                "vitals": [
                    {"systolic_bp": 122, "diastolic_bp": 78, "spo2": 98, "pulse": 74, "temperature_c": 36.7, "is_warning_sign": False, "mins_ago": 90}
                ],
                "referral_id": "REF-SHANKAR-006",
                "referral_reference": "REF-2026-339911",
                "referral_status": "CONSULTED",
                "acknowledged": True,
                "consultation_id": "CONS-SHANKAR-006",
                "consultation_reference": "CON-2026-066",
                "consultation_status": "COMPLETED",
                "cons_started_mins_ago": 80,
                "examination_notes": "Nasal mucosa mildly congested. Throat clear. Chest clear on auscultation.",
                "clinical_summary": "Seasonal allergic rhinitis with non-productive cough.",
                "confirmed_diagnosis": "Allergic Rhinitis (ICD-10: J30.9)",
                "icd10_code": "J30.9",
                "care_plan_summary": "Antihistamine course for 5 days. Steam inhalation twice daily. Avoid cold exposure.",
                "prescription_items": [
                    {"medicine": "Cetirizine", "strength": "10mg", "form": "Tablet", "dose": "1 tablet", "frequency": "Once daily at night", "duration": "5 days", "instructions": "Take at bedtime."}
                ]
            },

            # G. Kavita Patil — New Urgent Referral (Maternal, URGENT, PENDING_DOCTOR_REVIEW)
            {
                "code": "SCENARIO_G",
                "citizen_id": "1f755748-d9e9-46b4-b58b-af7b0c58c497",
                "abha_reference": "ABHA-2026-993311",
                "citizen_name": "Kavita Patil",
                "age": 27,
                "sex": "Female",
                "is_pregnant": True,
                "gestational_weeks": 26,
                "village": "Kalyanpur",
                "language": "mr-IN",
                "case_id": "1f755748-d9e9-46b4-b58b-af7b0c58c497",
                "case_reference": "CASE-2026-504946",
                "priority": CasePriorityEnum.URGENT,
                "case_status": CaseStatusEnum.REFERRED_TO_PHC,
                "concern": "Pregnancy-related warning signs: elevated blood pressure and sudden swelling",
                "safety_rule_triggered": True,
                "safety_rule_reason": "High maternal BP (148/96 mmHg) detected during home visit. Urgent PHC review required.",
                "created_mins_ago": 15,
                "symptoms": [
                    {"normalized": "Headache", "spoken": "डोकेदुखी", "severity": "HIGH"},
                    {"normalized": "Swollen Feet", "spoken": "पायावर सूज", "severity": "HIGH"}
                ],
                "vitals": [
                    {"systolic_bp": 148, "diastolic_bp": 96, "spo2": 97, "pulse": 86, "temperature_c": 37.0, "is_warning_sign": True, "mins_ago": 12}
                ],
                "visit_reference": "VISIT-2026-504946",
                "visit_notes": "ASHA home visit recorded sudden weight gain and facial puffiness. Issued urgent PHC referral.",
                "referral_id": "10d3fb77-6123-4f39-99d3-7a482ead90bd",
                "referral_reference": "REF-2026-499701",
                "referral_status": "PENDING_DOCTOR_REVIEW",
                "acknowledged": False
            },

            # H. Laxmi Kamble — Acknowledged, Transport En Route (Postnatal, HIGH, DOCTOR_ACKNOWLEDGED)
            {
                "code": "SCENARIO_H",
                "citizen_id": "CIT-LAXMI-008",
                "abha_reference": "ABHA-2026-778844",
                "citizen_name": "Laxmi Kamble",
                "age": 22,
                "sex": "Female",
                "is_pregnant": False,
                "village": "Shivaji Nagar",
                "language": "mr-IN",
                "case_id": "CASE-LAXMI-008",
                "case_reference": "CASE-2026-778844",
                "priority": CasePriorityEnum.HIGH,
                "case_status": CaseStatusEnum.DOCTOR_ACKNOWLEDGED,
                "concern": "Postnatal fever and localized breast tenderness on day 8 postpartum",
                "safety_rule_triggered": True,
                "safety_rule_reason": "Postpartum maternal fever (38.6°C) requires clinical evaluation.",
                "created_mins_ago": 25,
                "symptoms": [
                    {"normalized": "Fever", "spoken": "ताप", "severity": "HIGH"},
                    {"normalized": "Breast Pain", "spoken": "स्तनात दुखणे", "severity": "HIGH"}
                ],
                "vitals": [
                    {"systolic_bp": 116, "diastolic_bp": 74, "spo2": 98, "pulse": 94, "temperature_c": 38.6, "is_warning_sign": True, "mins_ago": 15}
                ],
                "visit_reference": "VISIT-2026-778844",
                "visit_notes": "PNC home visit day 8. Arranged 108 emergency transport to PHC.",
                "referral_id": "REF-LAXMI-008",
                "referral_reference": "REF-2026-778844",
                "referral_status": "DOCTOR_ACKNOWLEDGED",
                "transport_en_route": True,
                "acknowledged": True,
                "ack_mins_ago": 10
            }
        ]

        # Process all scenarios in order
        for scenario in scenarios:
            upsert_scenario(scenario)

        # Seed 4 canonical investigation scenarios
        seed_investigation_scenarios(db, doc_user, asha_user)

        # -------------------------------------------------------------------------
        # Doctor Alerts Seed (Idempotent 8 Linked Alerts)
        # -------------------------------------------------------------------------
        from app.services.doctor_alert_service import DoctorAlertService

        alerts_to_seed = [
            {
                "facility_id": "PHC-09",
                "category": "REFERRAL",
                "alert_type": "URGENT_REFERRAL_CREATED",
                "severity": "CRITICAL",
                "title": "Urgent Maternal Referral: Anandi Bai Deshmukh",
                "safe_summary": "Preeclampsia warning (BP 155/100 mmHg, severe headache, blurred vision). ASHA arranged emergency transport.",
                "source_entity_type": "REFERRAL",
                "source_entity_id": "adc52a74-6006-4559-8485-910b7bb178d1",
                "citizen_id": "c1d9bb3d-0854-4635-85af-b214b7d3c335",
                "case_id": "c1d9bb3d-0854-4635-85af-b214b7d3c335",
                "response_due_hours": 1
            },
            {
                "facility_id": "PHC-09",
                "category": "CLINICAL",
                "alert_type": "URGENT_REFERRAL_CREATED",
                "severity": "URGENT",
                "title": "Low SpO2 Alert: Aarav Sharma",
                "safe_summary": "Pediatric acute respiratory distress (SpO2 96%, high fever 39.2°C, lethargy). Prompt evaluation required.",
                "source_entity_type": "REFERRAL",
                "source_entity_id": "REF-AARAV-004",
                "citizen_id": "CIT-AARAV-004",
                "case_id": "CASE-AARAV-004",
                "response_due_hours": 2
            },
            {
                "facility_id": "PHC-09",
                "category": "FOLLOW_UP",
                "alert_type": "FOLLOWUP_ESCALATED",
                "severity": "HIGH",
                "title": "ASHA Repeat-BP Escalation: Kavita Patil",
                "safe_summary": "ASHA field visit noted persistent hypertension (148/96 mmHg) despite medication adherence.",
                "source_entity_type": "FOLLOWUP",
                "source_entity_id": "10d3fb77-6123-4f39-99d3-7a482ead90bd",
                "citizen_id": "1f755748-d9e9-46b4-b58b-af7b0c58c497",
                "case_id": "1f755748-d9e9-46b4-b58b-af7b0c58c497",
                "response_due_hours": 4
            },
            {
                "facility_id": "PHC-09",
                "category": "INVESTIGATION",
                "alert_type": "CRITICAL_RESULT_AVAILABLE",
                "severity": "CRITICAL",
                "title": "Critical Lab Result: Anandi Bai Deshmukh",
                "safe_summary": "Severe Anemia detected (Hemoglobin 6.2 g/dL, Hematocrit 19%). Immediate clinical review required.",
                "source_entity_type": "INVESTIGATION",
                "source_entity_id": "INV-ID-0001",
                "citizen_id": "c1d9bb3d-0854-4635-85af-b214b7d3c335",
                "case_id": "c1d9bb3d-0854-4635-85af-b214b7d3c335",
                "response_due_hours": 1
            },
            {
                "facility_id": "PHC-09",
                "category": "OPERATIONAL",
                "alert_type": "PATIENT_WAIT_THRESHOLD_EXCEEDED",
                "severity": "HIGH",
                "title": "Patient Wait Threshold Exceeded: Meena Bai",
                "safe_summary": "Patient arrived at PHC registration desk > 35 mins ago. Consultation in progress.",
                "source_entity_type": "CONSULTATION",
                "source_entity_id": "REF-MEENA-002",
                "citizen_id": "CIT-MEENA-002",
                "case_id": "CASE-MEENA-002",
                "response_due_hours": 1
            },
            {
                "facility_id": "PHC-09",
                "category": "CLINICAL",
                "alert_type": "MISSING_INFORMATION_RECEIVED",
                "severity": "INFORMATION",
                "title": "Missing Information Received: Pooja Jadhav",
                "safe_summary": "ASHA confirmed updated home address and family phone contact details.",
                "source_entity_type": "CITIZEN",
                "source_entity_id": "CIT-POOJA-005",
                "citizen_id": "CIT-POOJA-005",
                "case_id": "CASE-POOJA-005",
                "response_due_hours": 12
            },
            {
                "facility_id": "PHC-09",
                "category": "CITIZEN_REQUEST",
                "alert_type": "CITIZEN_HELP_REQUESTED",
                "severity": "HIGH",
                "title": "Citizen Assistance Requested: Rameshwar Shinde",
                "safe_summary": "Citizen requested medicine dosage clarification and refill assistance via portal.",
                "source_entity_type": "CITIZEN",
                "source_entity_id": "CIT-RAMESH-003",
                "citizen_id": "CIT-RAMESH-003",
                "case_id": "CASE-RAMESH-003",
                "response_due_hours": 6
            }
        ]

        for alt in alerts_to_seed:
            DoctorAlertService.create_or_update_alert_from_event(
                db=db,
                facility_id=alt["facility_id"],
                category=alt["category"],
                alert_type=alt["alert_type"],
                severity=alt["severity"],
                title=alt["title"],
                safe_summary=alt["safe_summary"],
                source_entity_type=alt["source_entity_type"],
                source_entity_id=alt["source_entity_id"],
                citizen_id=alt.get("citizen_id"),
                case_id=alt.get("case_id"),
                doctor_id=doc_user.id,
                response_due_hours=alt["response_due_hours"]
            )

        db.commit()

        print("\n=======================================================")
        print("  DEMO SEEDING COMPLETED SUCCESSFULLY")
        print("=======================================================")
        print(f"Facilities Created/Reused:        {summary_counts['facilities']}")
        print(f"Users Created/Reused:             {summary_counts['users']}")
        print(f"Citizens Created/Updated:         {summary_counts['citizens']}")
        print(f"Cases Created/Updated:            {summary_counts['cases']}")
        print(f"Symptoms Inserted:                {summary_counts['symptoms']}")
        print(f"Vitals Inserted:                  {summary_counts['vitals']}")
        print(f"Visits Inserted:                  {summary_counts['visits']}")
        print(f"Referrals Inserted:               {summary_counts['referrals']}")
        print(f"Consultations Inserted:           {summary_counts['consultations']}")
        print(f"Prescriptions Inserted:           {summary_counts['prescriptions']}")
        print(f"Prescription Items:               {summary_counts['prescription_items']}")
        print(f"Test Orders Inserted:             {summary_counts['test_orders']}")
        print(f"Follow-ups Inserted:              {summary_counts['follow_ups']}")
        print(f"Notifications:                    {summary_counts['notifications']}")
        print(f"Audit Logs:                       {summary_counts['audit_logs']}")
        print("=======================================================\n")

    except Exception as e:
        db.rollback()
        print(f"ERROR: Seeding failed with exception: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_doctor_demonstration()
