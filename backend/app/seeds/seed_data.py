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
    db: Session = SessionLocal()

    try:
        if db.query(User).filter(User.identifier == "sita.asha").first():
            print("Database already seeded. Skipping.")
            return

        print("Seeding comprehensive synthetic healthcare fixtures for Aarogya Sahayak...")

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
            CitizenProfile(id="CP-002", display_name="Rameshwar Shinde", age_estimate=54, sex="Male", phone="9876543211", village_name="Kalyanpur", is_pregnant=False),
            CitizenProfile(id="CP-003", display_name="Pooja Jadhav", age_estimate=22, sex="Female", phone="9876543212", village_name="Ganeshpur", is_pregnant=True, gestational_weeks=14),
            CitizenProfile(id="CP-004", display_name="Aarav Sharma", age_estimate=5, sex="Male", phone="9876543213", village_name="Kalyanpur", is_pregnant=False),
            CitizenProfile(id="CP-005", display_name="Meena Bai", age_estimate=62, sex="Female", phone="9876543214", village_name="Kalyanpur", is_pregnant=False),
            CitizenProfile(id="CP-006", display_name="Kisan Rao", age_estimate=48, sex="Male", phone="9876543215", village_name="Ganeshpur", is_pregnant=False),
            CitizenProfile(id="CP-007", display_name="Savita Ghadge", age_estimate=45, sex="Female", phone="9876543216", village_name="Kalyanpur", is_pregnant=False),
            CitizenProfile(id="CP-008", display_name="Vikram Patil", age_estimate=35, sex="Male", phone="9876543217", village_name="Kalyanpur", is_pregnant=False),
            CitizenProfile(id="CP-009", display_name="Laxmi Kamble", age_estimate=26, sex="Female", phone="9876543218", village_name="Kalyanpur", is_pregnant=False),
            CitizenProfile(id="CP-010", display_name="Shankar Shinde", age_estimate=31, sex="Male", phone="9876543219", village_name="Kalyanpur", is_pregnant=False),
            CitizenProfile(id="CP-011", display_name="Anita Deshmukh", age_estimate=24, sex="Female", phone="9876543220", village_name="Ganeshpur", is_pregnant=True, gestational_weeks=20)
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
                safety_rule_reason="Pregnancy-related warning signs with elevated blood pressure (Possible Pre-eclampsia)",
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

        # 6. Follow-ups
        followups = [
            FollowUp(id="FUP-001", case_id="case-followup-003", task_type="BP_MONITORING", assigned_role=UserRoleEnum.ASHA_WORKER, assigned_user_id=asha_user.id, instructions="Record weekly BP and verify medication adherence (Amlodipine 5mg).", priority=CasePriorityEnum.HIGH, due_at=now + timedelta(days=2), status="PENDING"),
            FollowUp(id="FUP-002", case_id="case-diabetes-007", task_type="GLUCOSE_CHECK", assigned_role=UserRoleEnum.ASHA_WORKER, assigned_user_id=asha_user.id, instructions="Check fasting capillary blood glucose and verify Metformin 500mg intake.", priority=CasePriorityEnum.ROUTINE, due_at=now + timedelta(days=3), status="PENDING"),
            FollowUp(id="FUP-003", case_id="case-pnc-009", task_type="POSTNATAL_CHECK", assigned_role=UserRoleEnum.ASHA_WORKER, assigned_user_id=asha_user.id, instructions="Evaluate neonatal umbilical cord and maternal lochia. Check for fever.", priority=CasePriorityEnum.HIGH, due_at=now - timedelta(days=1), status="PENDING")
        ]
        db.add_all(followups)

        # 7. Cluster Alerts
        db.add_all([
            ClusterAlert(alert_title="Elevated Acute Febrile Illness / Joint Pain Cluster", district_name="District 04", block_name="Kalyanpur Block", village_name="Kalyanpur Village", symptom_group="FEVER_JOINT_PAIN", case_count=18, time_window_hours=48, risk_level=CasePriorityEnum.HIGH, status="UNDER_INVESTIGATION"),
            ClusterAlert(alert_title="Maternal Hypertension Early Signal", district_name="District 04", block_name="Kalyanpur Block", village_name="Ganeshpur Village", symptom_group="MATERNAL_HYPERTENSION", case_count=4, time_window_hours=72, risk_level=CasePriorityEnum.HIGH, status="UNDER_INVESTIGATION")
        ])

        db.commit()
        print("Database successfully seeded with 11 diverse clinical demo cases!")
    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
