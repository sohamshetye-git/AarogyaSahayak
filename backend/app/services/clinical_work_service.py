"""
Clinical Work Service - Authoritative Queries for Doctor Dashboard & Destination Lists

Implements shared PostgreSQL query logic ensuring:
Dashboard Summary Count === Destination List Result Total
"""

from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import func, distinct, or_, and_

from app.models import (
    User, WorkerProfile, Case, Referral, Consultation, TestOrder, FollowUp,
    CitizenProfile, AshaVisit, SymptomObservation, VitalRecord
)

def get_doctor_jurisdiction(db: Session, current_user: User) -> Tuple[str, Optional[str]]:
    """
    Returns (doctor_id, phc_id) for the authenticated doctor.
    """
    doctor_id = current_user.id
    phc_id = None
    if current_user.worker_profile and current_user.worker_profile.facility_id:
        phc_id = current_user.worker_profile.facility_id
    return doctor_id, phc_id


def query_ready_to_start_consultations(db: Session, doctor_user: User):
    """
    Queries referrals where:
    - Referral.status = PATIENT_ARRIVED
    - Referral.to_facility_id = doctor.phc_id
    - No active DoctorConsultation exists for that referral
    """
    doctor_id, phc_id = get_doctor_jurisdiction(db, doctor_user)

    # Find referrals with status PATIENT_ARRIVED for this facility
    query = (
        db.query(Referral)
        .join(Case, Referral.case_id == Case.id)
        .filter(
            Referral.status == "PATIENT_ARRIVED",
            or_(Referral.to_facility_id == phc_id, Case.assigned_facility_id == phc_id)
        )
    )
    return query


def query_consultations_in_progress(db: Session, doctor_user: User):
    """
    Queries consultations where:
    - Consultation.status = IN_PROGRESS
    - Consultation.doctor_id = doctor.id (or doctor staff ID)
    - signed_at IS NULL
    """
    doctor_id, phc_id = get_doctor_jurisdiction(db, doctor_user)

    query = (
        db.query(Consultation)
        .join(Case, Consultation.case_id == Case.id)
        .filter(
            Consultation.status == "IN_PROGRESS",
            Consultation.signed_at.is_(None),
            or_(Consultation.doctor_id == doctor_id, Consultation.facility_id == phc_id)
        )
    )
    return query


def query_results_ready_for_review(db: Session, doctor_user: User):
    """
    Queries test orders where:
    - TestOrder.status = RESULT_AVAILABLE
    - TestOrder.reviewed_at IS NULL
    - Consultation belongs to doctor's facility / jurisdiction
    """
    doctor_id, phc_id = get_doctor_jurisdiction(db, doctor_user)

    query = (
        db.query(TestOrder)
        .join(Consultation, TestOrder.consultation_id == Consultation.id)
        .filter(
            TestOrder.status == "RESULT_AVAILABLE",
            TestOrder.reviewed_at.is_(None),
            or_(Consultation.facility_id == phc_id, Consultation.doctor_id == doctor_id)
        )
    )
    return query


def query_asha_followups_to_review(db: Session, doctor_user: User):
    """
    Queries follow-ups where:
    - FollowUp.status IN (COMPLETED, ESCALATED)
    - FollowUp.reviewed_by_doctor_at IS NULL
    - Created by or assigned to doctor's facility / jurisdiction
    """
    doctor_id, phc_id = get_doctor_jurisdiction(db, doctor_user)

    query = (
        db.query(FollowUp)
        .join(Case, FollowUp.case_id == Case.id)
        .filter(
            FollowUp.status.in_(["COMPLETED", "ESCALATED"]),
            FollowUp.reviewed_by_doctor_at.is_(None),
            or_(
                FollowUp.created_by_id == doctor_id,
                Case.assigned_facility_id == phc_id,
                FollowUp.created_by_role == "DOCTOR"
            )
        )
    )
    return query


def get_clinical_work_summary(db: Session, doctor_user: User) -> Dict[str, Any]:
    """
    Generates single summary DTO with PostgreSQL COUNT(DISTINCT entity.id)
    """
    doctor_id, phc_id = get_doctor_jurisdiction(db, doctor_user)

    ready_to_start_count = query_ready_to_start_consultations(db, doctor_user).with_entities(func.count(distinct(Referral.id))).scalar() or 0
    in_progress_count = query_consultations_in_progress(db, doctor_user).with_entities(func.count(distinct(Consultation.id))).scalar() or 0
    results_ready_count = query_results_ready_for_review(db, doctor_user).with_entities(func.count(distinct(TestOrder.id))).scalar() or 0
    followups_review_count = query_asha_followups_to_review(db, doctor_user).with_entities(func.count(distinct(FollowUp.id))).scalar() or 0

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "doctor_id": doctor_id,
        "phc_id": phc_id,
        "ready_to_start": ready_to_start_count,
        "consultations_in_progress": in_progress_count,
        "results_ready_for_review": results_ready_count,
        "asha_followups_to_review": followups_review_count,
    }
