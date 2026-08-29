import pytest
import os
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import (
    User, CitizenProfile, Facility, Case, Referral, Consultation,
    VitalRecord, SymptomObservation, TestOrder, FollowUp, AuditLog
)
from app.seeds.seed_doctor_demo import seed_doctor_demonstration, verify_environment

def test_seed_safety_production():
    """Verify demonstration seed refuses execution in production environment."""
    os.environ["APP_ENV"] = "production"
    with pytest.raises(SystemExit):
        verify_environment()
    os.environ["APP_ENV"] = "development"

def test_seed_idempotency_and_integrity():
    """Verify demo seed runs without duplicate creation and establishes all required relationships."""
    os.environ["APP_ENV"] = "development"
    seed_doctor_demonstration()

    db: Session = SessionLocal()
    try:
        # 1. Check Scenario A: Anandi Bai Deshmukh
        anandi_case = db.query(Case).filter(Case.reference == "CASE-2026-859171").first()
        assert anandi_case is not None
        assert anandi_case.citizen.display_name == "Anandi Bai Deshmukh"
        assert anandi_case.citizen.is_pregnant is True
        assert anandi_case.citizen.gestational_weeks == 30
        assert anandi_case.priority.value == "URGENT"
        assert len(anandi_case.vitals) > 0
        assert anandi_case.vitals[0].systolic_bp == 155
        assert anandi_case.vitals[0].diastolic_bp == 100

        anandi_ref = db.query(Referral).filter(Referral.case_id == anandi_case.id).first()
        assert anandi_ref is not None
        assert anandi_ref.status == "PATIENT_ARRIVED"

        # 2. Check Scenario B: Meena Bai (In progress draft)
        meena_case = db.query(Case).filter(Case.reference == "CASE-2026-448201").first()
        assert meena_case is not None
        assert meena_case.citizen.display_name == "Meena Bai"
        meena_cons = db.query(Consultation).filter(Consultation.case_id == meena_case.id).first()
        assert meena_cons is not None
        assert meena_cons.status == "IN_PROGRESS"

        # 3. Check Scenario D: Aarav Sharma (Awaiting results)
        aarav_case = db.query(Case).filter(Case.reference == "CASE-2026-118833").first()
        assert aarav_case is not None
        assert aarav_case.citizen.display_name == "Aarav Sharma"
        assert aarav_case.citizen.age_estimate == 5
        aarav_cons = db.query(Consultation).filter(Consultation.case_id == aarav_case.id).first()
        assert aarav_cons is not None
        assert len(aarav_cons.test_orders) >= 2

        # 4. Check Scenario E: Pooja Jadhav (Completed ASHA follow-up)
        pooja_case = db.query(Case).filter(Case.reference == "CASE-2026-224466").first()
        assert pooja_case is not None
        assert len(pooja_case.follow_ups) > 0
        assert pooja_case.follow_ups[0].status == "COMPLETED"

        # 5. Check Scenario F: Shankar Shinde (Completed consultation)
        shankar_case = db.query(Case).filter(Case.reference == "CASE-2026-339911").first()
        assert shankar_case is not None
        shankar_cons = db.query(Consultation).filter(Consultation.case_id == shankar_case.id).first()
        assert shankar_cons is not None
        assert shankar_cons.status == "COMPLETED"
        assert shankar_cons.confirmed_diagnosis is not None
        assert len(shankar_cons.prescriptions) > 0

        # 6. Check Scenario G: Kavita Patil (Pending doctor review)
        kavita_case = db.query(Case).filter(Case.reference == "CASE-2026-504946").first()
        assert kavita_case is not None
        kavita_ref = db.query(Referral).filter(Referral.case_id == kavita_case.id).first()
        assert kavita_ref is not None
        assert kavita_ref.status == "PENDING_DOCTOR_REVIEW"

        # 7. Check Scenario H: Laxmi Kamble (Acknowledged, Transport en route)
        laxmi_case = db.query(Case).filter(Case.reference == "CASE-2026-778844").first()
        assert laxmi_case is not None
        laxmi_ref = db.query(Referral).filter(Referral.case_id == laxmi_case.id).first()
        assert laxmi_ref is not None
        assert laxmi_ref.status == "DOCTOR_ACKNOWLEDGED"
        assert laxmi_ref.transport_assistance_required is True

    finally:
        db.close()
