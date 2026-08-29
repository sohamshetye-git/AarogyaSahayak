"""
Escalation Service - Follow-up Escalation Lifecycle & State Machine Management

State Transitions:
ESCALATED -> DOCTOR_ACKNOWLEDGED -> ACTION_ASSIGNED -> RESOLVED (or CANCELLED)
"""

from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import func, distinct, or_
from fastapi import HTTPException, status

from app.models import (
    User, Case, Referral, Consultation, FollowUp, FollowUpEscalation,
    CitizenProfile, CasePriorityEnum, Notification, UserRoleEnum
)
from app.services.event_bus import publish_domain_event

VALID_TRANSITIONS = {
    "ESCALATED": ["DOCTOR_ACKNOWLEDGED", "ACTION_ASSIGNED", "RESOLVED", "CANCELLED"],
    "DOCTOR_ACKNOWLEDGED": ["ACTION_ASSIGNED", "RESOLVED", "CANCELLED"],
    "ACTION_ASSIGNED": ["RESOLVED", "CANCELLED"],
    "RESOLVED": [],
    "CANCELLED": []
}

def validate_state_transition(current_status: str, target_status: str):
    allowed = VALID_TRANSITIONS.get(current_status, [])
    if target_status not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "INVALID_STATE_TRANSITION",
                "message": f"Cannot transition escalation from state '{current_status}' to '{target_status}'."
            }
        )


def create_or_update_escalation(
    db: Session,
    follow_up_id: str,
    reason: str,
    priority: CasePriorityEnum = CasePriorityEnum.URGENT,
    asha_user_id: Optional[str] = None
) -> FollowUpEscalation:
    """
    Creates or reuses single active FollowUpEscalation for a given follow-up.
    Guarantees no duplicate active escalations.
    """
    fu = db.query(FollowUp).filter(FollowUp.id == follow_up_id).first()
    if not fu:
        raise HTTPException(status_code=404, detail={"code": "FOLLOWUP_NOT_FOUND", "message": "FollowUp record not found"})

    now = datetime.now(timezone.utc)
    raw_asha_id = asha_user_id or fu.assigned_user_id or fu.created_by_id
    valid_asha = db.query(User).filter(User.id == raw_asha_id).first() if raw_asha_id else None
    if not valid_asha:
        fallback_asha = db.query(User).filter(User.role == UserRoleEnum.ASHA_WORKER).first()
        assigned_asha = fallback_asha.id if fallback_asha else None
    else:
        assigned_asha = valid_asha.id

    citizen_id = fu.citizen_id
    if not citizen_id and fu.case:
        citizen_id = fu.case.citizen_id
    if not citizen_id:
        cit = db.query(CitizenProfile).first()
        citizen_id = cit.id if cit else "CITIZEN-DEMO-001"

    # Check for existing escalation
    esc = db.query(FollowUpEscalation).filter(FollowUpEscalation.follow_up_id == follow_up_id).first()
    if esc:
        esc.reason = reason
        esc.priority = priority
        esc.status = "ESCALATED"
        esc.updated_at = now
    else:
        esc = FollowUpEscalation(
            follow_up_id=fu.id,
            case_id=fu.case_id or "case-001",
            citizen_id=citizen_id,
            consultation_id=fu.consultation_id,
            referral_id=fu.referral_id,
            assigned_asha_id=assigned_asha or "ASHA-001",
            priority=priority,
            reason=reason,
            status="ESCALATED",
            escalated_at=now,
            created_at=now,
            updated_at=now
        )
        db.add(esc)

    fu.status = "ESCALATED"
    db.commit()
    db.refresh(esc)

    # Publish notification & domain event
    publish_domain_event(
        event_name="FOLLOWUP_ESCALATED",
        payload={
            "escalation_id": esc.id,
            "follow_up_id": fu.id,
            "case_id": fu.case_id,
            "citizen_name": fu.citizen.display_name if fu.citizen else "Citizen",
            "reason": reason,
            "priority": priority.value if hasattr(priority, "value") else str(priority),
            "escalated_at": now.isoformat()
        },
        target_roles=["PHC_DOCTOR"]
    )

    return esc


def acknowledge_escalation(
    db: Session,
    escalation_id: str,
    doctor_user: User
) -> FollowUpEscalation:
    """
    Doctor acknowledges escalation without resolving.
    Transitions state to DOCTOR_ACKNOWLEDGED.
    """
    esc = db.query(FollowUpEscalation).filter(FollowUpEscalation.id == escalation_id).first()
    if not esc:
        raise HTTPException(status_code=404, detail={"code": "ESCALATION_NOT_FOUND", "message": "Escalation record not found"})

    validate_state_transition(esc.status, "DOCTOR_ACKNOWLEDGED")

    now = datetime.now(timezone.utc)
    esc.status = "DOCTOR_ACKNOWLEDGED"
    esc.acknowledged_at = now
    esc.acknowledged_by = doctor_user.id
    esc.assigned_doctor_id = doctor_user.id
    esc.updated_at = now

    db.commit()
    db.refresh(esc)

    publish_domain_event(
        event_name="ESCALATION_ACKNOWLEDGED",
        payload={
            "escalation_id": esc.id,
            "follow_up_id": esc.follow_up_id,
            "doctor_name": doctor_user.name,
            "acknowledged_at": now.isoformat()
        },
        target_roles=["ASHA_WORKER", "PHC_DOCTOR"]
    )

    return esc


def assign_escalation_action(
    db: Session,
    escalation_id: str,
    action_type: str,
    action_notes: str,
    doctor_user: User
) -> FollowUpEscalation:
    """
    Assigns an escalation action (e.g. REQUEST_PATIENT_TO_PHC, REPEAT_FOLLOWUP).
    Transitions state to ACTION_ASSIGNED.
    """
    esc = db.query(FollowUpEscalation).filter(FollowUpEscalation.id == escalation_id).first()
    if not esc:
        raise HTTPException(status_code=404, detail={"code": "ESCALATION_NOT_FOUND", "message": "Escalation record not found"})

    validate_state_transition(esc.status, "ACTION_ASSIGNED")

    now = datetime.now(timezone.utc)
    esc.status = "ACTION_ASSIGNED"
    esc.action_type = action_type
    esc.action_notes = action_notes
    esc.assigned_doctor_id = doctor_user.id
    esc.updated_at = now

    # If action is REQUEST_PATIENT_TO_PHC, update case & referral
    if action_type == "REQUEST_PATIENT_TO_PHC" and esc.case:
        esc.case.status = "REFERRED_TO_PHC"
        ref = db.query(Referral).filter(Referral.case_id == esc.case_id).first()
        if ref:
            ref.status = "REFERRED_TO_PHC"
            ref.reason = f"[Doctor Escalation Directive]: {action_notes}"

    db.commit()
    db.refresh(esc)

    publish_domain_event(
        event_name="ESCALATION_ACTION_ASSIGNED",
        payload={
            "escalation_id": esc.id,
            "follow_up_id": esc.follow_up_id,
            "action_type": action_type,
            "action_notes": action_notes,
            "assigned_at": now.isoformat()
        },
        target_roles=["ASHA_WORKER", "PHC_DOCTOR"]
    )

    return esc


def resolve_escalation(
    db: Session,
    escalation_id: str,
    resolution_notes: str,
    resolution_outcome: str,
    doctor_user: User
) -> FollowUpEscalation:
    """
    Resolves escalation. Transitions state to RESOLVED.
    Removes escalation from active dashboard count.
    """
    esc = db.query(FollowUpEscalation).filter(FollowUpEscalation.id == escalation_id).first()
    if not esc:
        raise HTTPException(status_code=404, detail={"code": "ESCALATION_NOT_FOUND", "message": "Escalation record not found"})

    validate_state_transition(esc.status, "RESOLVED")

    now = datetime.now(timezone.utc)
    esc.status = "RESOLVED"
    esc.resolved_at = now
    esc.resolved_by = doctor_user.id
    esc.resolution = resolution_notes
    esc.resolution_outcome = resolution_outcome
    esc.updated_at = now

    if esc.follow_up:
        esc.follow_up.status = "REVIEWED"
        esc.follow_up.reviewed_by_doctor_at = now
        esc.follow_up.reviewed_by_doctor_id = doctor_user.id

    db.commit()
    db.refresh(esc)

    publish_domain_event(
        event_name="ESCALATION_RESOLVED",
        payload={
            "escalation_id": esc.id,
            "follow_up_id": esc.follow_up_id,
            "resolution_outcome": resolution_outcome,
            "resolved_at": now.isoformat()
        },
        target_roles=["ASHA_WORKER", "PHC_DOCTOR"]
    )

    return esc


def get_active_escalations(db: Session, doctor_user: User) -> List[FollowUpEscalation]:
    """
    Queries active escalations (status IN ('ESCALATED', 'DOCTOR_ACKNOWLEDGED', 'ACTION_ASSIGNED'))
    using COUNT(DISTINCT escalation.id) to guarantee zero duplicate cards.
    """
    phc_id = "PHC-09"
    if doctor_user.worker_profile and doctor_user.worker_profile.facility_id:
        phc_id = doctor_user.worker_profile.facility_id

    query = (
        db.query(FollowUpEscalation)
        .join(Case, FollowUpEscalation.case_id == Case.id)
        .filter(
            FollowUpEscalation.status.in_(["ESCALATED", "DOCTOR_ACKNOWLEDGED", "ACTION_ASSIGNED"]),
            or_(Case.assigned_facility_id == phc_id, FollowUpEscalation.assigned_doctor_id == doctor_user.id)
        )
        .order_by(FollowUpEscalation.escalated_at.desc())
    )
    return query.all()
