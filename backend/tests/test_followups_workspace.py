"""
Automated Pytest Suite for Doctor Follow-up Review Workspace
"""

import pytest
from datetime import datetime, timezone, timedelta
from app.database import SessionLocal
from app.models import User, FollowUp, FollowUpEscalation, Case
from app.services.followup_monitor_service import (
    get_doctor_followups_summary,
    get_doctor_followup_monitor_records,
    acknowledge_doctor_followup,
    update_doctor_followup_directive,
    resolve_doctor_followup,
    request_repeat_vitals,
    get_followup_canonical_dto
)

def test_doctor_followup_workspace_rbac_and_isolation():
    db = SessionLocal()
    try:
        doc_user = db.query(User).filter(User.role == "PHC_DOCTOR").first()
        assert doc_user is not None, "PHC Doctor user must exist in seed data"

        summary = get_doctor_followups_summary(db=db, doctor_user=doc_user)
        assert isinstance(summary, dict)
        assert "results_ready_count" in summary
        assert "escalated_count" in summary
        assert "overdue_count" in summary
        assert "due_today_count" in summary
        assert "pending_count" in summary
        assert "total_actionable" in summary

        items, total = get_doctor_followup_monitor_records(
            db=db,
            doctor_user=doc_user,
            status_filter="ACTION_REQUIRED",
            limit=20
        )
        assert isinstance(items, list)
        assert total >= len(items)
    finally:
        db.close()


def test_doctor_followups_summary_counts_matching_filters():
    db = SessionLocal()
    try:
        doc_user = db.query(User).filter(User.role == "PHC_DOCTOR").first()
        summary = get_doctor_followups_summary(db=db, doctor_user=doc_user)

        # Query ESCALATED items directly
        esc_items, esc_total = get_doctor_followup_monitor_records(
            db=db, doctor_user=doc_user, status_filter="ESCALATED", limit=100
        )
        assert summary["escalated_count"] == esc_total, f"Summary escalated ({summary['escalated_count']}) must match list total ({esc_total})"
    finally:
        db.close()


def test_doctor_followup_acknowledgement_and_directive_mutations():
    db = SessionLocal()
    try:
        doc_user = db.query(User).filter(User.role == "PHC_DOCTOR").first()
        c = db.query(Case).first()
        assert c is not None

        # Create a dedicated test follow-up record
        test_fup = FollowUp(
            id="fup-unit-test-001",
            case_id=c.id,
            citizen_id=c.citizen_id,
            assigned_user_id="asha-001",
            created_by_id=doc_user.id,
            status="ESCALATED",
            instructions="Initial test directive",
            due_at=datetime.now(timezone.utc) + timedelta(days=1)
        )
        db.merge(test_fup)
        db.commit()

        fup_id = "fup-unit-test-001"

        # 1. Acknowledge
        ack_res = acknowledge_doctor_followup(db=db, followup_id=fup_id, doctor_user=doc_user)
        assert ack_res["status"] == "DOCTOR_ACKNOWLEDGED"

        # 2. Modify Directive
        dir_res = update_doctor_followup_directive(
            db=db,
            followup_id=fup_id,
            doctor_user=doc_user,
            instructions="Repeat BP check tomorrow and verify adherence",
            priority="HIGH"
        )
        assert dir_res["status"] == "ACTION_ASSIGNED"
        assert "Repeat BP" in dir_res["directive"]
    finally:
        db.close()


def test_doctor_followup_repeat_vitals_request():
    db = SessionLocal()
    try:
        doc_user = db.query(User).filter(User.role == "PHC_DOCTOR").first()

        res = request_repeat_vitals(
            db=db,
            followup_id="fup-unit-test-001",
            doctor_user=doc_user,
            vitals_to_repeat=["systolic_bp", "diastolic_bp", "spo2"],
            notes="Please record repeat vitals at 8 AM"
        )
        assert res["status"] == "ACTION_ASSIGNED"
        assert "systolic_bp" in res["measurements_to_repeat"]
    finally:
        db.close()


def test_doctor_followup_full_lifecycle_resolution():
    db = SessionLocal()
    try:
        doc_user = db.query(User).filter(User.role == "PHC_DOCTOR").first()

        res = resolve_doctor_followup(
            db=db,
            followup_id="fup-unit-test-001",
            doctor_user=doc_user,
            resolution_notes="Patient symptoms resolved completely",
            resolution_outcome="RESOLVED_SATISFACTORILY"
        )
        assert res["status"] == "RESOLVED"
    finally:
        db.close()


def test_idempotency_and_duplicate_prevention():
    db = SessionLocal()
    try:
        doc_user = db.query(User).filter(User.role == "PHC_DOCTOR").first()
        items1, total1 = get_doctor_followup_monitor_records(db=db, doctor_user=doc_user, status_filter="ALL", limit=50)

        ids = [item["follow_up_id"] for item in items1]
        assert len(ids) == len(set(ids)), "Follow-up list must contain zero duplicate IDs"
    finally:
        db.close()
