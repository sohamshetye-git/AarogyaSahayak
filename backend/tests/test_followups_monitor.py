"""
Automated Pytest Suite for Doctor Portal ASHA Follow-up Monitor
"""

import pytest
from datetime import datetime, timezone, timedelta
from app.database import SessionLocal
from app.models import User, FollowUp, Case, CasePriorityEnum, CitizenProfile
from app.services.followup_monitor_service import (
    get_doctor_followup_monitor_records,
    get_followup_canonical_dto,
    review_doctor_followup,
    reschedule_doctor_followup,
    cancel_doctor_followup
)

def test_doctor_followup_monitor_query_deduplication_and_sorting():
    db = SessionLocal()
    try:
        doc_user = db.query(User).filter(User.role == "PHC_DOCTOR").first()
        assert doc_user is not None, "Doctor user must exist in demo database"

        items, total = get_doctor_followup_monitor_records(
            db=db,
            doctor_user=doc_user,
            status_filter="ACTION_REQUIRED",
            limit=50
        )

        assert isinstance(items, list)
        assert total >= len(items)

        # Check deduplication: all follow_up_ids in returned items must be unique
        ids = [item["follow_up_id"] for item in items]
        assert len(ids) == len(set(ids)), "Follow-up items must be distinct without duplicate IDs"

        # Check canonical DTO fields
        if items:
            item = items[0]
            assert "follow_up_id" in item
            assert "case_id" in item
            assert "patient_name" in item
            assert "case_reference" in item
            assert "status" in item
            assert "directive" in item
            assert "assigned_asha_name" in item
    finally:
        db.close()


def test_doctor_followup_review_mutation_and_count_decrement():
    db = SessionLocal()
    try:
        doc_user = db.query(User).filter(User.role == "PHC_DOCTOR").first()
        fu = db.query(FollowUp).filter(FollowUp.status == "COMPLETED").first()
        if not fu:
            fu = db.query(FollowUp).first()
            fu.status = "COMPLETED"
            db.commit()

        initial_items, initial_total = get_doctor_followup_monitor_records(
            db=db,
            doctor_user=doc_user,
            status_filter="ACTION_REQUIRED"
        )

        # Doctor reviews completed follow-up
        reviewed_dto = review_doctor_followup(
            db=db,
            followup_id=fu.id,
            doctor_user=doc_user,
            review_notes="Vitals within normal limits. No immediate escalation needed.",
            next_action="NO_FURTHER_ACTION"
        )

        assert reviewed_dto["status"] == "REVIEWED"
        assert reviewed_dto["reviewed_by_doctor_at"] is not None

        # Verify reviewed record leaves active monitor list
        after_items, after_total = get_doctor_followup_monitor_records(
            db=db,
            doctor_user=doc_user,
            status_filter="ACTION_REQUIRED"
        )

        after_ids = [item["follow_up_id"] for item in after_items]
        assert fu.id not in after_ids, "Reviewed follow-up must leave the active monitor list"
    finally:
        db.close()


def test_followup_reschedule_and_cancel_mutations():
    db = SessionLocal()
    try:
        doc_user = db.query(User).filter(User.role == "PHC_DOCTOR").first()
        fu = db.query(FollowUp).first()
        assert fu is not None

        # 1. Reschedule
        new_due = datetime.now(timezone.utc) + timedelta(days=2)
        rescheduled = reschedule_doctor_followup(
            db=db,
            followup_id=fu.id,
            doctor_user=doc_user,
            new_due_at=new_due,
            reason="Rescheduled for post-medication evaluation"
        )
        assert rescheduled["status"] == "RESCHEDULED"

        # 2. Cancel
        cancelled = cancel_doctor_followup(
            db=db,
            followup_id=fu.id,
            doctor_user=doc_user,
            reason="Patient admitted to hospital ward"
        )
        assert cancelled["status"] == "CANCELLED"
    finally:
        db.close()
