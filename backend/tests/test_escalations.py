"""
Automated Pytest Suite for ASHA Follow-up Escalations & State Machine Engine
"""

import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from app.main import app
from app.database import get_db, SessionLocal
from app.models import User, FollowUp, FollowUpEscalation, Case, CasePriorityEnum
from app.services.escalation_service import (
    create_or_update_escalation, acknowledge_escalation,
    assign_escalation_action, resolve_escalation, get_active_escalations
)

client = TestClient(app)

def get_auth_header(username: str = "dr.sharma"):
    db = SessionLocal()
    user = db.query(User).filter(User.username == username).first()
    db.close()
    if not user:
        token = "mock-doctor-token"
    else:
        token = f"mock-token-{user.id}"
    return {"Authorization": f"Bearer {token}", "X-User-Role": "PHC_DOCTOR"}


def test_asha_escalation_creation_and_state_machine():
    db = SessionLocal()
    try:
        # Find or create a follow-up
        fu = db.query(FollowUp).first()
        assert fu is not None, "FollowUp record must exist in demo DB"

        # 1. Create Escalation
        esc = create_or_update_escalation(
            db=db,
            follow_up_id=fu.id,
            reason="Repeat BP 165/105 mmHg and severe frontal headache",
            priority=CasePriorityEnum.URGENT,
            asha_user_id=fu.assigned_user_id
        )

        assert esc.id is not None
        assert esc.follow_up_id == fu.id
        assert esc.status == "ESCALATED"
        assert esc.reason == "Repeat BP 165/105 mmHg and severe frontal headache"

        # 2. Query active escalations
        doc_user = db.query(User).filter(User.role == "PHC_DOCTOR").first()
        active_list = get_active_escalations(db, doc_user)
        assert len(active_list) >= 1
        active_ids = [e.id for e in active_list]
        assert esc.id in active_ids

        # 3. Doctor Acknowledgement
        esc_ack = acknowledge_escalation(db, esc.id, doc_user)
        assert esc_ack.status == "DOCTOR_ACKNOWLEDGED"
        assert esc_ack.acknowledged_at is not None
        assert esc_ack.acknowledged_by == doc_user.id

        # 4. Doctor Action Assignment
        esc_act = assign_escalation_action(
            db=db,
            escalation_id=esc.id,
            action_type="REQUEST_PATIENT_TO_PHC",
            action_notes="Urgent PHC referral issued for hypertensive crisis evaluation",
            doctor_user=doc_user
        )
        assert esc_act.status == "ACTION_ASSIGNED"
        assert esc_act.action_type == "REQUEST_PATIENT_TO_PHC"

        # 5. Doctor Resolution (Decrements active count)
        esc_res = resolve_escalation(
            db=db,
            escalation_id=esc.id,
            resolution_notes="Patient evaluated at PHC. Alpha Methyldopa increased. Vitals stabilized.",
            resolution_outcome="RESOLVED_SATISFACTORILY",
            doctor_user=doc_user
        )
        assert esc_res.status == "RESOLVED"
        assert esc_res.resolved_at is not None

        # Verify active escalations list no longer includes resolved escalation
        active_after = get_active_escalations(db, doc_user)
        active_after_ids = [e.id for e in active_after]
        assert esc.id not in active_after_ids

    finally:
        db.close()


def test_invalid_state_transition():
    db = SessionLocal()
    try:
        fu = db.query(FollowUp).first()
        esc = create_or_update_escalation(
            db=db,
            follow_up_id=fu.id,
            reason="Test invalid state transition",
            priority=CasePriorityEnum.HIGH,
            asha_user_id=fu.assigned_user_id
        )

        doc_user = db.query(User).filter(User.role == "PHC_DOCTOR").first()
        
        # Transition to RESOLVED first
        resolve_escalation(
            db=db,
            escalation_id=esc.id,
            resolution_notes="Resolved early",
            resolution_outcome="RESOLVED_SATISFACTORILY",
            doctor_user=doc_user
        )

        # Attempt invalid transition from RESOLVED to DOCTOR_ACKNOWLEDGED -> Should raise HTTPException 400
        with pytest.raises(Exception) as exc_info:
            acknowledge_escalation(db, esc.id, doc_user)
        
        assert "400" in str(exc_info.value) or "INVALID_STATE_TRANSITION" in str(exc_info.value)

    finally:
        db.close()
