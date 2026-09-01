from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from app.database import SessionLocal, engine, Base
from app.models import (
    User, CitizenProfile, WorkerProfile, Facility, Case, SymptomObservation,
    VitalRecord, AshaVisit, Referral, Consultation, FollowUp, ClusterAlert,
    UserRoleEnum, CasePriorityEnum, CaseStatusEnum, InformationSourceEnum
)
from app.auth.security import get_password_hash

def seed_database():
    from app.config import settings

    db: Session = SessionLocal()

    try:
        # 1. Always ensure government schemes knowledge base catalog is populated idempotently
        ensure_schemes_knowledge_base(db)

        # 2. Skip demo users/cases in production if configured
        if settings.ENVIRONMENT.lower() == "production":
            print("Demo database fixtures seeding is disabled in production environments.")
            return

        ensure_facilities_and_staff(db)
    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
        raise
    finally:
        db.close()

def ensure_schemes_knowledge_base(db: Session):
    # Seed Government Health Schemes Knowledge Base idempotently
    try:
        from app.models import SchemeModel
        if db.query(SchemeModel).count() == 0:
            import os
            from app.schemes.import_kb import import_knowledge_base
            import_knowledge_base(db_session=db)
            print("Government Schemes knowledge base seeded successfully.")
    except Exception as e:
        print(f"Warning: Could not auto-seed schemes KB: {e}")

def ensure_facilities_and_staff(db: Session):
    if db.query(User).filter(User.identifier == "sita.asha").first():
        print("Staff users and cases already exist. Skipping case seeding.")
        return

    print("Seeding comprehensive synthetic healthcare fixtures for Aarogya Sahayak...")

    try:
        # 1. Facilities
        phc = Facility(
            id="PHC-09",
            code="PHC-09",
            name="Kalyanpur Primary Health Center",
            facility_type="PHC",
            district_name="District 04",
            block_name="Kalyanpur Block",
            address="Main Road, Kalyanpur Village"
        )
        chc = Facility(
            id="CHC-02",
            code="CHC-02",
            name="Shivaji Nagar Community Health Center",
            facility_type="CHC",
            district_name="District 04",
            block_name="Shivaji Nagar Block",
            address="Hospital Chowk, Shivaji Nagar"
        )
        sub_center = Facility(
            id="SUB-01",
            code="SUB-01",
            name="Ganeshpur Sub-Center",
            facility_type="SUB_CENTER",
            district_name="District 04",
            block_name="Kalyanpur Block",
            address="Near Gram Panchayat, Ganeshpur"
        )
        db.add_all([phc, chc, sub_center])
        db.flush()

        # 2. Staff Users & Profiles
        asha_user = User(
            id="ASHA-012",
            identifier="sita.asha",
            name="Sita Patel",
            phone="9823012345",
            email="sita.asha@arogya.gov.in",
            password_hash=get_password_hash("demo123"),
            role=UserRoleEnum.ASHA_WORKER,
            preferred_language="mr-IN"
        )
        asha_alias = User(
            id="ASHA-001",
            identifier="asha01",
            name="Sita Patel",
            phone="9823012346",
            email="asha01@arogya.gov.in",
            password_hash=get_password_hash("demo123"),
            role=UserRoleEnum.ASHA_WORKER,
            preferred_language="mr-IN"
        )
        asha_profile = WorkerProfile(
            user_id="ASHA-012",
            worker_type="ASHA",
            facility_id=phc.id,
            facility_name=phc.name,
            district_name="District 04",
            village_ids=["VILLAGE-01"],
            professional_registration="ASHA-MH-2024-8841"
        )

        doctor_user = User(
            id="DOC-007",
            identifier="dr.sharma",
            name="Dr. Abhinav Sharma",
            phone="9823098765",
            email="dr.sharma@phc.arogya.gov.in",
            password_hash=get_password_hash("demo123"),
            role=UserRoleEnum.PHC_DOCTOR,
            preferred_language="mr-IN"
        )
        doctor_alias = User(
            id="DOC-001",
            identifier="doctor01",
            name="Dr. Abhinav Sharma",
            phone="9823098766",
            email="doctor01@phc.arogya.gov.in",
            password_hash=get_password_hash("demo123"),
            role=UserRoleEnum.PHC_DOCTOR,
            preferred_language="mr-IN"
        )
        doctor_profile = WorkerProfile(
            user_id="DOC-007",
            worker_type="DOCTOR",
            facility_id=phc.id,
            facility_name=phc.name,
            district_name="District 04",
            professional_registration="MMC-2018-09142"
        )

        admin_user = User(
            id="ADMIN-003",
            identifier="dho.admin",
            name="Dr. Rajesh Deshmukh (DHO)",
            phone="9823000001",
            email="dho.district04@arogya.gov.in",
            password_hash=get_password_hash("demo123"),
            role=UserRoleEnum.DISTRICT_ADMIN,
            preferred_language="en-IN"
        )
        admin_alias = User(
            id="ADMIN-001",
            identifier="admin01",
            name="District Health Officer",
            phone="9823000002",
            email="admin01@arogya.gov.in",
            password_hash=get_password_hash("demo123"),
            role=UserRoleEnum.DISTRICT_ADMIN,
            preferred_language="en-IN"
        )
        admin_profile = WorkerProfile(
            user_id="ADMIN-003",
            worker_type="ADMIN",
            district_name="District 04"
        )

        # Citizen user: Sunita Devi
        citizen_user = User(
            id="CIT-001",
            identifier="sunita.devi",
            name="Sunita Devi",
            phone="9876543210",
            email="sunita@demo.in",
            password_hash=get_password_hash("demo123"),
            role=UserRoleEnum.CITIZEN,
            preferred_language="mr-IN"
        )

        db.add_all([
            asha_user, asha_alias, asha_profile,
            doctor_user, doctor_alias, doctor_profile,
            admin_user, admin_alias, admin_profile,
            citizen_user
        ])
        db.flush()

        # 3. Citizen Profiles (11 diverse cases)
        citizens = [
            CitizenProfile(id="CP-001", display_name="Sunita Devi", age_estimate=28, sex="Female", phone="9876543210", village_name="Kalyanpur", is_pregnant=True, gestational_weeks=28, abha_reference="12-3456-7890-1234"),
            CitizenProfile(id="CP-002", display_name="Rameshwar Shinde", age_estimate=54, sex="Male", phone="9876543211", village_name="Kalyanpur", is_pregnant=False, abha_reference="12-3456-7890-5678"),
            CitizenProfile(id="CP-003", display_name="Pooja Jadhav", age_estimate=22, sex="Female", phone="9876543212", village_name="Ganeshpur", is_pregnant=True, gestational_weeks=14, abha_reference="12-3456-7890-9012"),
            CitizenProfile(id="CP-004", display_name="Aarav Sharma", age_estimate=5, sex="Male", phone="9876543213", village_name="Kalyanpur", is_pregnant=False, abha_reference="12-3456-7890-3456"),
            CitizenProfile(id="CP-005", display_name="Meena Bai", age_estimate=62, sex="Female", phone="9876543214", village_name="Kalyanpur", is_pregnant=False, abha_reference="12-3456-7890-7890"),
            CitizenProfile(id="CP-006", display_name="Kisan Rao", age_estimate=48, sex="Male", phone="9876543215", village_name="Ganeshpur", is_pregnant=False, abha_reference="12-3456-7890-2345"),
            CitizenProfile(id="CP-007", display_name="Savita Ghadge", age_estimate=45, sex="Female", phone="9876543216", village_name="Kalyanpur", is_pregnant=False, abha_reference="12-3456-7890-6789"),
            CitizenProfile(id="CP-008", display_name="Vikram Patil", age_estimate=35, sex="Male", phone="9876543217", village_name="Kalyanpur", is_pregnant=False, abha_reference="12-3456-7890-1122"),
            CitizenProfile(id="CP-009", display_name="Laxmi Kamble", age_estimate=26, sex="Female", phone="9876543218", village_name="Kalyanpur", is_pregnant=False, abha_reference="12-3456-7890-3344"),
            CitizenProfile(id="CP-010", display_name="Shankar Shinde", age_estimate=31, sex="Male", phone="9876543219", village_name="Kalyanpur", is_pregnant=False, abha_reference="12-3456-7890-5566"),
            CitizenProfile(id="CP-011", display_name="Anita Deshmukh", age_estimate=24, sex="Female", phone="9876543220", village_name="Ganeshpur", is_pregnant=True, gestational_weeks=20, abha_reference="12-3456-7890-7788")
        ]
        db.add_all(citizens)
        db.flush()

        now = datetime.now(timezone.utc)

        # 4. Cases (11 Synthetic Scenarios)
        cases = [
            # Case 1: Canonical Scenario - Sunita Devi
            Case(
                id="case-canonical-001",
                reference="CASE-2026-001",
                citizen_id="CP-001",
                priority=CasePriorityEnum.URGENT,
                status=CaseStatusEnum.NEW,
                primary_concern="Blurred vision, severe headache, and swollen feet during pregnancy (7 months)",
                preferred_language="mr-IN",
                assigned_asha_id=asha_user.id,
                assigned_asha_name=asha_user.name,
                assigned_facility_id=phc.id,
                assigned_facility_name=phc.name,
                safety_rule_triggered=True,
                safety_rule_reason="Pregnancy-related warning signs were recorded, including elevated blood pressure. Urgent PHC evaluation is recommended.",
                citizen_guidance_text="Warning signs detected for pregnancy. Please rest while ASHA coordinates PHC assistance.",
                created_at=now - timedelta(minutes=25)
            ),
            # Case 2: Routine 2nd Trimester ANC - Pooja Jadhav
            Case(
                id="case-routine-002",
                reference="CASE-2026-002",
                citizen_id="CP-003",
                priority=CasePriorityEnum.ROUTINE,
                status=CaseStatusEnum.ASHA_REVIEWED,
                primary_concern="Second trimester routine ANC checkup and iron supplementation guidance",
                preferred_language="mr-IN",
                assigned_asha_id=asha_user.id,
                assigned_asha_name=asha_user.name,
                assigned_facility_id=phc.id,
                assigned_facility_name=phc.name,
                safety_rule_triggered=False,
                created_at=now - timedelta(hours=4)
            ),
            # Case 3: Chronic Hypertension Follow-up - Rameshwar Shinde
            Case(
                id="case-followup-003",
                reference="CASE-2026-003",
                citizen_id="CP-002",
                priority=CasePriorityEnum.HIGH,
                status=CaseStatusEnum.FOLLOW_UP_REQUIRED,
                primary_concern="Blood pressure monitoring following medication adjustment",
                preferred_language="mr-IN",
                assigned_asha_id=asha_user.id,
                assigned_asha_name=asha_user.name,
                assigned_facility_id=phc.id,
                assigned_facility_name=phc.name,
                safety_rule_triggered=False,
                created_at=now - timedelta(days=1)
            ),
            # Case 4: Child High Fever - Aarav Sharma
            Case(
                id="case-child-004",
                reference="CASE-2026-004",
                citizen_id="CP-004",
                priority=CasePriorityEnum.HIGH,
                status=CaseStatusEnum.NEW,
                primary_concern="High grade fever for 2 days with reduced oral intake in 5-year child",
                preferred_language="mr-IN",
                assigned_asha_id=asha_user.id,
                assigned_asha_name=asha_user.name,
                assigned_facility_id=phc.id,
                assigned_facility_name=phc.name,
                safety_rule_triggered=True,
                safety_rule_reason="High fever in pediatric age group requiring dehydration assessment",
                created_at=now - timedelta(minutes=40)
            ),
            # Case 5: Low SpO2 / Breathlessness - Meena Bai
            Case(
                id="case-respiratory-005",
                reference="CASE-2026-005",
                citizen_id="CP-005",
                priority=CasePriorityEnum.URGENT,
                status=CaseStatusEnum.NEW,
                primary_concern="Shortness of breath on mild exertion and coughing at night",
                preferred_language="mr-IN",
                assigned_asha_id=asha_user.id,
                assigned_asha_name=asha_user.name,
                assigned_facility_id=phc.id,
                assigned_facility_name=phc.name,
                safety_rule_triggered=True,
                safety_rule_reason="Hypoxemia warning: SpO2 measured at 91%",
                created_at=now - timedelta(minutes=55)
            ),
            # Case 6: Acute Chest Discomfort - Kisan Rao
            Case(
                id="case-cardiac-006",
                reference="CASE-2026-006",
                citizen_id="CP-006",
                priority=CasePriorityEnum.URGENT,
                status=CaseStatusEnum.REFERRED_TO_PHC,
                primary_concern="Retrosternal chest tightness and sweating for 1 hour",
                preferred_language="mr-IN",
                assigned_asha_id=asha_user.id,
                assigned_asha_name=asha_user.name,
                assigned_facility_id=phc.id,
                assigned_facility_name=phc.name,
                safety_rule_triggered=True,
                safety_rule_reason="Red flag cardiac symptoms: immediate medical evaluation required",
                created_at=now - timedelta(hours=2)
            ),
            # Case 7: Diabetes Follow-up - Savita Ghadge
            Case(
                id="case-diabetes-007",
                reference="CASE-2026-007",
                citizen_id="CP-007",
                priority=CasePriorityEnum.ROUTINE,
                status=CaseStatusEnum.FOLLOW_UP_REQUIRED,
                primary_concern="Fasting blood glucose log review and diet adherence",
                preferred_language="mr-IN",
                assigned_asha_id=asha_user.id,
                assigned_asha_name=asha_user.name,
                assigned_facility_id=phc.id,
                assigned_facility_name=phc.name,
                safety_rule_triggered=False,
                created_at=now - timedelta(days=2)
            ),
            # Case 8: Unreachable / Reschedule - Vikram Patil
            Case(
                id="case-unreachable-008",
                reference="CASE-2026-008",
                citizen_id="CP-008",
                priority=CasePriorityEnum.ROUTINE,
                status=CaseStatusEnum.UNREACHABLE,
                primary_concern="Seasonal skin rash consultation follow-up",
                preferred_language="mr-IN",
                assigned_asha_id=asha_user.id,
                assigned_asha_name=asha_user.name,
                assigned_facility_id=phc.id,
                assigned_facility_name=phc.name,
                safety_rule_triggered=False,
                created_at=now - timedelta(days=3)
            ),
            # Case 9: Postnatal Overdue - Laxmi Kamble
            Case(
                id="case-pnc-009",
                reference="CASE-2026-009",
                citizen_id="CP-009",
                priority=CasePriorityEnum.HIGH,
                status=CaseStatusEnum.FOLLOW_UP_REQUIRED,
                primary_concern="Postnatal Day 14 home visit and newborn thermal care",
                preferred_language="mr-IN",
                assigned_asha_id=asha_user.id,
                assigned_asha_name=asha_user.name,
                assigned_facility_id=phc.id,
                assigned_facility_name=phc.name,
                safety_rule_triggered=False,
                created_at=now - timedelta(days=5)
            ),
            # Case 10: Mild Cold / Seasonal - Shankar Shinde
            Case(
                id="case-cold-010",
                reference="CASE-2026-010",
                citizen_id="CP-010",
                priority=CasePriorityEnum.ROUTINE,
                status=CaseStatusEnum.COMPLETED,
                primary_concern="Mild cough and runny nose for 1 day without fever",
                preferred_language="mr-IN",
                assigned_asha_id=asha_user.id,
                assigned_asha_name=asha_user.name,
                assigned_facility_id=phc.id,
                assigned_facility_name=phc.name,
                safety_rule_triggered=False,
                created_at=now - timedelta(days=6)
            ),
            # Case 11: Maternal Nutrition / Anemia - Anita Deshmukh
            Case(
                id="case-anemia-011",
                reference="CASE-2026-011",
                citizen_id="CP-011",
                priority=CasePriorityEnum.HIGH,
                status=CaseStatusEnum.ASHA_ACKNOWLEDGED,
                primary_concern="Severe lethargy and pale conjunctiva at 20 weeks gestational age",
                preferred_language="mr-IN",
                assigned_asha_id=asha_user.id,
                assigned_asha_name=asha_user.name,
                assigned_facility_id=phc.id,
                assigned_facility_name=phc.name,
                safety_rule_triggered=True,
                safety_rule_reason="Suspected moderate-to-severe maternal anemia",
                created_at=now - timedelta(hours=6)
            )
        ]
        db.add_all(cases)
        db.flush()

        # 5. Symptoms and Vitals for Canonical Case 1
        db.add_all([
            SymptomObservation(case_id="case-canonical-001", spoken_term="डोळ्यांसमोर अंधारी (Blurred vision)", normalized_term="Blurred Vision", severity="HIGH", duration_text="2 days", source_type=InformationSourceEnum.CITIZEN_REPORTED, recorded_by="Citizen Voice (Marathi)"),
            SymptomObservation(case_id="case-canonical-001", spoken_term="खूप डोकेदुखी (Severe headache)", normalized_term="Severe Headache", severity="HIGH", duration_text="3 days", source_type=InformationSourceEnum.CITIZEN_REPORTED, recorded_by="Citizen Voice (Marathi)"),
            SymptomObservation(case_id="case-canonical-001", spoken_term="पायावर सूज (Swollen feet)", normalized_term="Pedal Edema", severity="MODERATE", duration_text="1 week", source_type=InformationSourceEnum.CITIZEN_REPORTED, recorded_by="Citizen Voice (Marathi)"),
            VitalRecord(case_id="case-canonical-001", systolic_bp=150, diastolic_bp=100, temperature_c=37.0, spo2=97, pulse=88, respiratory_rate=18, is_warning_sign=True, source_type=InformationSourceEnum.CITIZEN_REPORTED, recorded_by="Citizen / Digital Sphygmomanometer")
        ])

        # 6. Follow-ups (Diverse: ASHA Scheduled, Doctor Directives, Overdue, Due Today, Upcoming)
        followups = [
            FollowUp(
                id="FUP-001",
                case_id="case-followup-003",
                citizen_id="CP-002",
                source="DOCTOR_ASSIGNED",
                created_by_id=doctor_user.id,
                created_by_role="PHC_DOCTOR",
                task_type="BP_MONITORING",
                reason="Titration of antihypertensive therapy and weekly pressure monitoring",
                assigned_role=UserRoleEnum.ASHA_WORKER,
                assigned_user_id=asha_user.id,
                instructions="Record weekly BP and verify medication adherence (Amlodipine 5mg). Check for dizziness.",
                measurements_to_repeat=["systolic_bp", "diastolic_bp", "pulse"],
                adherence_required=True,
                escalation_conditions="Escalate if SBP >= 160 mmHg or citizen reports severe headache/chest tightness.",
                priority=CasePriorityEnum.HIGH,
                due_at=now + timedelta(hours=4), # Due Today
                status="PENDING",
                sync_status="SYNCED"
            ),
            FollowUp(
                id="FUP-002",
                case_id="case-diabetes-007",
                citizen_id="CP-007",
                source="DOCTOR_ASSIGNED",
                created_by_id=doctor_user.id,
                created_by_role="PHC_DOCTOR",
                task_type="GLUCOSE_CHECK",
                reason="Post-diagnosis fasting blood sugar verification",
                assigned_role=UserRoleEnum.ASHA_WORKER,
                assigned_user_id=asha_user.id,
                instructions="Check fasting capillary blood glucose and verify Metformin 500mg daily compliance.",
                measurements_to_repeat=["glucose_mg_dl", "weight_kg"],
                adherence_required=True,
                escalation_conditions="Escalate if fasting glucose > 200 mg/dL or presence of diabetic foot sore.",
                priority=CasePriorityEnum.ROUTINE,
                due_at=now + timedelta(days=3), # Upcoming
                status="PENDING",
                sync_status="SYNCED"
            ),
            FollowUp(
                id="FUP-003",
                case_id="case-pnc-009",
                citizen_id="CP-009",
                source="ASHA_SCHEDULED",
                created_by_id=asha_user.id,
                created_by_role="ASHA_WORKER",
                task_type="POSTNATAL_CHECK",
                reason="Day 14 Postnatal home assessment and neonatal jaundice check",
                assigned_role=UserRoleEnum.ASHA_WORKER,
                assigned_user_id=asha_user.id,
                instructions="Evaluate neonatal umbilical cord and maternal lochia. Check for fever and breastfeeding latch.",
                measurements_to_repeat=["temperature_c", "pulse"],
                adherence_required=False,
                escalation_conditions="Escalate immediately if maternal temperature > 38°C or newborn lethargy/poor feeding.",
                priority=CasePriorityEnum.HIGH,
                due_at=now - timedelta(days=1), # Overdue
                status="PENDING",
                sync_status="SYNCED"
            ),
            FollowUp(
                id="FUP-004",
                case_id="case-canonical-001",
                citizen_id="CP-001",
                source="DOCTOR_ASSIGNED",
                created_by_id=doctor_user.id,
                created_by_role="PHC_DOCTOR",
                task_type="MATERNAL_ANC_MONITORING",
                reason="Post-PHC emergency evaluation for high blood pressure in 3rd trimester",
                assigned_role=UserRoleEnum.ASHA_WORKER,
                assigned_user_id=asha_user.id,
                instructions="Repeat BP check, inspect for worsening pedal edema or visual disturbances daily.",
                measurements_to_repeat=["systolic_bp", "diastolic_bp", "spo2", "pulse"],
                adherence_required=True,
                escalation_conditions="Emergency PHC transfer if SBP >= 140/90 with headache or blurred vision.",
                priority=CasePriorityEnum.URGENT,
                due_at=now + timedelta(days=1),
                status="IN_PROGRESS",
                started_at=now - timedelta(hours=2),
                sync_status="SYNCED"
            ),
            FollowUp(
                id="FUP-005",
                case_id="case-routine-002",
                citizen_id="CP-003",
                source="DOCTOR_ASSIGNED",
                created_by_id=doctor_user.id,
                created_by_role="PHC_DOCTOR",
                task_type="POST_CONSULTATION_BP_CHECK",
                reason="Post-consultation BP verification for gestational hypertension",
                assigned_role=UserRoleEnum.ASHA_WORKER,
                assigned_user_id=asha_user.id,
                instructions="Visit patient at home. Re-check BP twice, check Labetalol 100mg adherence.",
                measurements_to_repeat=["systolic_bp", "diastolic_bp", "spo2"],
                adherence_required=True,
                escalation_conditions="Escalate if SBP >= 150 mmHg or severe headache.",
                priority=CasePriorityEnum.HIGH,
                due_at=now - timedelta(hours=1),
                status="COMPLETED_BY_ASHA",
                started_at=now - timedelta(hours=5),
                completed_at=now - timedelta(hours=1),
                symptoms_outcome="IMPROVED",
                completion_notes="Patient visited. BP measured 132/84 mmHg. Patient reports headache resolved. Medication taken regularly.",
                result="BP 132/84 mmHg, SpO2 98%. Adherent to Labetalol.",
                sync_status="SYNCED"
            ),
            FollowUp(
                id="FUP-006",
                case_id="case-canonical-001",
                citizen_id="CP-004",
                source="DOCTOR_ASSIGNED",
                created_by_id=doctor_user.id,
                created_by_role="PHC_DOCTOR",
                task_type="URGENT_BP_MONITORING",
                reason="Severe hypertension follow-up",
                assigned_role=UserRoleEnum.ASHA_WORKER,
                assigned_user_id=asha_user.id,
                instructions="Urgent home visit. Measure BP and evaluate for chest discomfort.",
                measurements_to_repeat=["systolic_bp", "diastolic_bp", "pulse"],
                adherence_required=True,
                escalation_conditions="Escalate if SBP > 160 mmHg.",
                priority=CasePriorityEnum.URGENT,
                due_at=now - timedelta(hours=2),
                status="ESCALATED",
                completed_at=now - timedelta(hours=2),
                symptoms_outcome="WORSENED",
                completion_notes="BP severely elevated 168/104 mmHg. Patient experiencing dizziness and blurred vision.",
                result="BP 168/104 mmHg. Escalated for immediate doctor review.",
                sync_status="SYNCED"
            ),
            FollowUp(
                id="FUP-007",
                case_id="case-diabetes-007",
                citizen_id="CP-005",
                source="DOCTOR_ASSIGNED",
                created_by_id=doctor_user.id,
                created_by_role="PHC_DOCTOR",
                task_type="GLUCOSE_MONITORING",
                reason="Routine post-treatment glucose check",
                assigned_role=UserRoleEnum.ASHA_WORKER,
                assigned_user_id=asha_user.id,
                instructions="Check fasting sugar level.",
                measurements_to_repeat=["glucose_mg_dl"],
                adherence_required=True,
                priority=CasePriorityEnum.ROUTINE,
                due_at=now - timedelta(days=2),
                status="REVIEWED",
                completed_at=now - timedelta(days=2),
                reviewed_by_doctor_at=now - timedelta(days=1),
                reviewed_by_doctor_id=doctor_user.id,
                symptoms_outcome="IMPROVED",
                completion_notes="Fasting blood sugar 110 mg/dL.",
                sync_status="SYNCED"
            ),
            FollowUp(
                id="FUP-008",
                case_id="case-followup-003",
                citizen_id="CP-006",
                source="DOCTOR_ASSIGNED",
                created_by_id=doctor_user.id,
                created_by_role="PHC_DOCTOR",
                task_type="BP_MONITORING",
                reason="Completed treatment follow-up",
                assigned_role=UserRoleEnum.ASHA_WORKER,
                assigned_user_id=asha_user.id,
                instructions="Final BP verification.",
                measurements_to_repeat=["systolic_bp", "diastolic_bp"],
                adherence_required=True,
                priority=CasePriorityEnum.ROUTINE,
                due_at=now - timedelta(days=4),
                status="RESOLVED",
                completed_at=now - timedelta(days=4),
                reviewed_by_doctor_at=now - timedelta(days=3),
                reviewed_by_doctor_id=doctor_user.id,
                symptoms_outcome="IMPROVED",
                completion_notes="BP normalized 120/80 mmHg.",
                sync_status="SYNCED"
            )
        ]
        db.add_all(followups)

        # 8. Seed Controlled Formulary (MedicineCatalog) & Prescription Scenarios
        seed_prescriptions_data(db, doctor_user, asha_user)

        db.commit()
        print("Database successfully seeded with clinical demo cases and prescriptions!")
    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
        raise
    finally:
        db.close()


def seed_prescriptions_data(db: Session, doctor_user: User, asha_user: User):
    from app.models import (
        MedicineCatalog, Prescription, PrescriptionItem, PrescriptionSafetyCheck,
        PrescriptionAmendment, PrescriptionAcknowledgement, FollowUp, CitizenProfile, Case, Consultation
    )

    # 1. Seed MedicineCatalog idempotently
    formulary = [
        {"id": "MED-001", "generic_name": "Amoxicillin", "brand_name": "Mox 500", "formulation": "Tablet", "strength_options": ["250 mg", "500 mg"], "route_options": ["Oral"], "medicine_category": "Antibiotic", "phc_availability_status": "AVAILABLE"},
        {"id": "MED-002", "generic_name": "Paracetamol", "brand_name": "Calpol", "formulation": "Tablet", "strength_options": ["500 mg", "650 mg"], "route_options": ["Oral"], "medicine_category": "Essential", "phc_availability_status": "AVAILABLE"},
        {"id": "MED-003", "generic_name": "Labetalol", "brand_name": "Labebet", "formulation": "Tablet", "strength_options": ["100 mg", "200 mg"], "route_options": ["Oral"], "medicine_category": "Maternal", "phc_availability_status": "AVAILABLE"},
        {"id": "MED-004", "generic_name": "Folic Acid", "brand_name": "Folvite", "formulation": "Tablet", "strength_options": ["5 mg"], "route_options": ["Oral"], "medicine_category": "Maternal", "phc_availability_status": "AVAILABLE"},
        {"id": "MED-005", "generic_name": "Metformin", "brand_name": "Glycomet", "formulation": "Tablet", "strength_options": ["500 mg", "850 mg", "1000 mg"], "route_options": ["Oral"], "medicine_category": "NCD", "phc_availability_status": "AVAILABLE"},
        {"id": "MED-006", "generic_name": "Amlodipine", "brand_name": "Amlopress", "formulation": "Tablet", "strength_options": ["2.5 mg", "5 mg", "10 mg"], "route_options": ["Oral"], "medicine_category": "NCD", "phc_availability_status": "AVAILABLE"},
        {"id": "MED-007", "generic_name": "ORS Sachet", "brand_name": "Electral", "formulation": "Powder", "strength_options": ["21.8 g"], "route_options": ["Oral"], "medicine_category": "Child", "phc_availability_status": "AVAILABLE"},
        {"id": "MED-008", "generic_name": "Iron + Folic Acid", "brand_name": "IFA Red Tablet", "formulation": "Tablet", "strength_options": ["100 mg Elemental Iron + 500 mcg FA"], "route_options": ["Oral"], "medicine_category": "Maternal", "phc_availability_status": "AVAILABLE"}
    ]

    for m in formulary:
        if not db.query(MedicineCatalog).filter(MedicineCatalog.id == m["id"]).first():
            mc = MedicineCatalog(
                id=m["id"],
                generic_name=m["generic_name"],
                brand_name=m["brand_name"],
                formulation=m["formulation"],
                strength_options=m["strength_options"],
                route_options=m["route_options"],
                medicine_category=m["medicine_category"],
                phc_availability_status=m["phc_availability_status"],
                active=True
            )
            db.add(mc)
    db.flush()

    now = datetime.now(timezone.utc)

    # Fetch reference demo entities
    citizen1 = db.query(CitizenProfile).filter(CitizenProfile.id == "CP-001").first() or db.query(CitizenProfile).first()
    case1 = db.query(Case).first()
    cons1 = db.query(Consultation).first()

    if not citizen1 or not case1 or not cons1:
        return

    # Scenario 1: Draft Prescription (RX-DRAFT-001)
    if not db.query(Prescription).filter(Prescription.id == "RX-DRAFT-001").first():
        rx1 = Prescription(
            id="RX-DRAFT-001",
            reference="RX-20260826-DRAFT1",
            citizen_id=citizen1.id,
            case_id=case1.id,
            consultation_id=cons1.id,
            prescriber_doctor_id=doctor_user.id,
            facility_id="PHC-09",
            status="DRAFT",
            version_number=1,
            clinical_context="Draft prescription for fever and headache in-progress consultation.",
            patient_language="mr-IN",
            created_at=now - timedelta(hours=2),
            updated_at=now - timedelta(hours=1)
        )
        db.add(rx1)
        db.add(PrescriptionItem(
            id="RXI-001",
            prescription_id="RX-DRAFT-001",
            medicine_catalog_id="MED-002",
            generic_name_snapshot="Paracetamol",
            brand_name_snapshot="Calpol",
            formulation="Tablet",
            strength="500 mg",
            dose="1",
            dose_unit="tablet",
            route="Oral",
            frequency="Three times daily",
            timing="After food",
            duration_value=5,
            duration_unit="days",
            quantity=15,
            instructions="Take with warm water after meals.",
            status="ACTIVE"
        ))

    # Scenario 2: Ready for Signature (RX-REVIEW-002)
    if not db.query(Prescription).filter(Prescription.id == "RX-REVIEW-002").first():
        rx2 = Prescription(
            id="RX-REVIEW-002",
            reference="RX-20260826-REV02",
            citizen_id=citizen1.id,
            case_id=case1.id,
            consultation_id=cons1.id,
            prescriber_doctor_id=doctor_user.id,
            facility_id="PHC-09",
            status="READY_FOR_REVIEW",
            version_number=1,
            clinical_context="Maternal hypertension routine regimen review.",
            patient_language="mr-IN",
            created_at=now - timedelta(hours=1),
            updated_at=now - timedelta(minutes=30)
        )
        db.add(rx2)
        db.add_all([
            PrescriptionItem(
                id="RXI-002",
                prescription_id="RX-REVIEW-002",
                medicine_catalog_id="MED-003",
                generic_name_snapshot="Labetalol",
                brand_name_snapshot="Labebet",
                formulation="Tablet",
                strength="100 mg",
                dose="1",
                dose_unit="tablet",
                route="Oral",
                frequency="Twice daily",
                timing="After food",
                duration_value=14,
                duration_unit="days",
                quantity=28,
                instructions="Monitor blood pressure daily.",
                adherence_monitoring_required=True,
                status="ACTIVE"
            ),
            PrescriptionItem(
                id="RXI-003",
                prescription_id="RX-REVIEW-002",
                medicine_catalog_id="MED-004",
                generic_name_snapshot="Folic Acid",
                brand_name_snapshot="Folvite",
                formulation="Tablet",
                strength="5 mg",
                dose="1",
                dose_unit="tablet",
                route="Oral",
                frequency="Once daily",
                timing="After food",
                duration_value=30,
                duration_unit="days",
                quantity=30,
                instructions="Daily antenatal supplement.",
                status="ACTIVE"
            ),
            PrescriptionSafetyCheck(
                id="RXSC-001",
                prescription_id="RX-REVIEW-002",
                check_type="MISSING_HISTORY",
                severity="DOCTOR_CONFIRMATION_REQUIRED",
                message="Allergy history is not recorded. Doctor confirmation is required before signing.",
                source_rule="RULE_ALLERGY_HISTORY_MISSING",
                requires_confirmation=True,
                confirmed_by_doctor=False
            )
        ])

    # Scenario 3: Signed Active Prescription (RX-ACTIVE-003)
    if not db.query(Prescription).filter(Prescription.id == "RX-ACTIVE-003").first():
        rx3 = Prescription(
            id="RX-ACTIVE-003",
            reference="RX-20260826-ACT03",
            citizen_id=citizen1.id,
            case_id=case1.id,
            consultation_id=cons1.id,
            prescriber_doctor_id=doctor_user.id,
            facility_id="PHC-09",
            status="ACTIVE",
            version_number=1,
            clinical_context="Confirmed maternal pre-eclampsia management plan.",
            patient_language="mr-IN",
            signed_at=now - timedelta(days=1),
            created_at=now - timedelta(days=1),
            updated_at=now - timedelta(days=1)
        )
        db.add(rx3)
        db.add_all([
            PrescriptionItem(
                id="RXI-004",
                prescription_id="RX-ACTIVE-003",
                medicine_catalog_id="MED-003",
                generic_name_snapshot="Labetalol",
                brand_name_snapshot="Labebet",
                formulation="Tablet",
                strength="100 mg",
                dose="1",
                dose_unit="tablet",
                route="Oral",
                frequency="Twice daily",
                timing="After food",
                duration_value=14,
                duration_unit="days",
                quantity=28,
                start_date=now - timedelta(days=1),
                end_date=now + timedelta(days=13),
                instructions="Take regularly with water.",
                adherence_monitoring_required=True,
                status="ACTIVE"
            ),
            PrescriptionAcknowledgement(
                id="RXACK-001",
                prescription_id="RX-ACTIVE-003",
                citizen_id=citizen1.id,
                instructions_understood=True,
                language="mr-IN",
                acknowledged_at=now - timedelta(hours=12)
            )
        ])

    # Scenario 4: Amended & Stopped Medicine (RX-AMENDED-004 -> RX-AMENDED-005)
    if not db.query(Prescription).filter(Prescription.id == "RX-AMENDED-004").first():
        rx4_orig = Prescription(
            id="RX-AMENDED-004",
            reference="RX-20260826-OLD04",
            citizen_id=citizen1.id,
            case_id=case1.id,
            consultation_id=cons1.id,
            prescriber_doctor_id=doctor_user.id,
            facility_id="PHC-09",
            status="AMENDED",
            version_number=1,
            clinical_context="Original regimen prior to dose adjustment.",
            patient_language="mr-IN",
            signed_at=now - timedelta(days=5),
            created_at=now - timedelta(days=5),
            updated_at=now - timedelta(days=2)
        )
        rx4_new = Prescription(
            id="RX-AMENDED-005",
            reference="RX-20260826-NEW05",
            citizen_id=citizen1.id,
            case_id=case1.id,
            consultation_id=cons1.id,
            prescriber_doctor_id=doctor_user.id,
            facility_id="PHC-09",
            status="ACTIVE",
            version_number=2,
            supersedes_prescription_id="RX-AMENDED-004",
            clinical_context="Amended: Dose adjusted based on blood pressure tracking.",
            patient_language="mr-IN",
            signed_at=now - timedelta(days=2),
            created_at=now - timedelta(days=2),
            updated_at=now - timedelta(days=2)
        )
        db.add_all([rx4_orig, rx4_new])
        db.add_all([
            PrescriptionItem(
                id="RXI-005",
                prescription_id="RX-AMENDED-004",
                medicine_catalog_id="MED-003",
                generic_name_snapshot="Labetalol",
                formulation="Tablet",
                strength="100 mg",
                dose="1",
                dose_unit="tablet",
                route="Oral",
                frequency="Once daily",
                duration_value=7,
                duration_unit="days",
                quantity=7,
                status="STOPPED",
                stopped_at=now - timedelta(days=2),
                stopped_by_doctor_id=doctor_user.id,
                stop_reason="Dose increased to twice daily"
            ),
            PrescriptionItem(
                id="RXI-006",
                prescription_id="RX-AMENDED-005",
                medicine_catalog_id="MED-003",
                generic_name_snapshot="Labetalol",
                formulation="Tablet",
                strength="100 mg",
                dose="1",
                dose_unit="tablet",
                route="Oral",
                frequency="Twice daily",
                duration_value=14,
                duration_unit="days",
                quantity=28,
                start_date=now - timedelta(days=2),
                end_date=now + timedelta(days=12),
                status="ACTIVE"
            ),
            PrescriptionAmendment(
                id="RXAMD-001",
                original_prescription_id="RX-AMENDED-004",
                new_prescription_id="RX-AMENDED-005",
                reason_code="DOSE_ADJUSTED",
                reason_note="Elevated BP requiring BD dosage escalation.",
                created_by_doctor_id=doctor_user.id,
                created_at=now - timedelta(days=2)
            )
        ])

    db.flush()


