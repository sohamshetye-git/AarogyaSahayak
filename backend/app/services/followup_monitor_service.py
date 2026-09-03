"""
Follow-up Monitor Service - Authoritative Doctor Follow-up Queries & Management
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, distinct, or_, and_, case
from fastapi import HTTPException, status

from app.models import (
    User, Case, Referral, Consultation, FollowUp, FollowUpEscalation,
    CitizenProfile, CasePriorityEnum, AuditLog
)
from app.services.event_bus import publish_domain_event

def get_followup_canonical_dto(f: FollowUp, db: Session, current_user: User) -> Dict[str, Any]:
    case = f.case
    citizen = f.citizen or (case.citizen if case else None)
    
    # Calculate category
    category = "MATERNAL" if (citizen and citizen.is_pregnant) else ("CHILD_HEALTH" if (citizen and citizen.age_estimate and citizen.age_estimate <= 12) else "NCD_CHRONIC")

    # Determine assigned ASHA name
    asha_name = "Unassigned"
    assigned_asha_id = f.assigned_user_id
    if f.assigned_user_id:
        asha_user = db.query(User).filter(User.id == f.assigned_user_id).first()
        if asha_user:
            asha_name = asha_user.name
    elif f.created_by_role == "ASHA_WORKER" and f.created_by_id:
        asha_user = db.query(User).filter(User.id == f.created_by_id).first()
        if asha_user:
            asha_name = asha_user.name
            assigned_asha_id = asha_user.id
    elif case and getattr(case, "assigned_asha_name", None):
        asha_name = case.assigned_asha_name
        assigned_asha_id = getattr(case, "assigned_asha_id", None)

    # Determine doctor name
    doc_name = "Unassigned"
    assigned_doc_id = None
    if f.created_by_id and f.created_by_role in ["PHC_DOCTOR", "DOCTOR", "STAFF"]:
        doc_user = db.query(User).filter(User.id == f.created_by_id).first()
        if doc_user:
            doc_name = doc_user.name
            assigned_doc_id = doc_user.id
    elif case and getattr(case, "assigned_doctor_name", None):
        doc_name = case.assigned_doctor_name
        assigned_doc_id = getattr(case, "assigned_doctor_id", None)

    # Escalation ID if present
    esc_id = None
    if getattr(f, "escalation", None):
        esc_val = f.escalation
        if isinstance(esc_val, list) and len(esc_val) > 0:
            esc_id = esc_val[0].id
        elif hasattr(esc_val, "id"):
            esc_id = esc_val.id

    if not esc_id:
        esc_rec = db.query(FollowUpEscalation).filter(FollowUpEscalation.follow_up_id == f.id).first()
        if esc_rec:
            esc_id = esc_rec.id

    now = datetime.now(timezone.utc)
    due_at_val = f.due_at
    if due_at_val and due_at_val.tzinfo is None:
        due_at_val = due_at_val.replace(tzinfo=timezone.utc)

    # Derive effective status label
    effective_status = f.status
    if f.status in ["PENDING", "SCHEDULED", "IN_PROGRESS"] and due_at_val and due_at_val < now:
        effective_status = "OVERDUE"
    elif f.status in ["COMPLETED", "COMPLETED_BY_ASHA"] and not f.reviewed_by_doctor_at:
        effective_status = "COMPLETED" # Result Ready

    # Vitals dict (only if conducted/recorded)
    latest_v = None
    is_conducted = f.status in ["COMPLETED", "COMPLETED_BY_ASHA", "REVIEW_REQUIRED", "ESCALATED", "DOCTOR_ACKNOWLEDGED", "REVIEWED", "RESOLVED"]
    if is_conducted and case and case.vitals and len(case.vitals) > 1:
        lv = case.vitals[-1]
        latest_v = {
            "systolic_bp": lv.systolic_bp,
            "diastolic_bp": lv.diastolic_bp,
            "spo2": lv.spo2,
            "pulse": lv.pulse,
            "temperature_c": lv.temperature_c,
            "glucose_mg_dl": lv.glucose_mg_dl,
            "recorded_at": lv.recorded_at.isoformat() if lv.recorded_at else None
        }

    return {
        "follow_up_id": f.id,
        "case_id": f.case_id or "",
        "citizen_id": citizen.id if citizen else "",
        "consultation_id": f.consultation_id,
        "directive_id": f.id,
        "escalation_id": esc_id,
        "patient_name": citizen.display_name if citizen else (f.result or "Citizen"),
        "case_reference": case.reference if case else "CASE-001",
        "patient_category": category,
        "patient_age": citizen.age_estimate if citizen else None,
        "patient_gender": citizen.sex if citizen else "Female",
        "village_name": citizen.village_name if citizen else "Kalyanpur",
        "is_pregnant": citizen.is_pregnant if citizen else False,
        "gestational_weeks": citizen.gestational_weeks if citizen else None,
        "priority": f.priority.value if hasattr(f.priority, "value") else str(f.priority),
        "status": effective_status,
        "assigned_asha_id": assigned_asha_id,
        "assigned_asha_name": asha_name,
        "created_by_doctor_id": assigned_doc_id,
        "created_by_doctor_name": doc_name,
        "assigned_doctor_name": doc_name,
        "directive": f.instructions or f.reason or "Follow-up monitoring",
        "measurements_to_repeat": f.measurements_to_repeat or [],
        "adherence_required": f.adherence_required if f.adherence_required is not None else False,
        "due_at": f.due_at.isoformat() if f.due_at else None,
        "completed_at": f.completed_at.isoformat() if (f.completed_at and is_conducted) else None,
        "escalated_at": f.completed_at.isoformat() if f.status == "ESCALATED" and f.completed_at else None,
        "reviewed_by_doctor_at": f.reviewed_by_doctor_at.isoformat() if f.reviewed_by_doctor_at else None,
        "completion_notes": f.completion_notes if is_conducted else None,
        "symptoms_outcome": f.symptoms_outcome if is_conducted else None,
        "latest_vitals": latest_v
    }


def get_doctor_followup_monitor_records(
    db: Session,
    doctor_user: User,
    status_filter: Optional[str] = "ACTION_REQUIRED",
    query_str: Optional[str] = None,
    priority_filter: Optional[str] = None,
    village_filter: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
) -> Tuple[List[Dict[str, Any]], int]:
    """
    Queries follow-ups using COUNT(DISTINCT follow_ups.id) to guarantee zero duplicate cards.
    Applies authoritative active monitor sorting: 1. Escalated -> 2. Overdue -> 3. Result Ready -> 4. Due Today -> 5. Pending.
    """
    phc_id = "PHC-09"
    if doctor_user.worker_profile and doctor_user.worker_profile.facility_id:
        phc_id = doctor_user.worker_profile.facility_id

    query = (
        db.query(FollowUp)
        .outerjoin(Case, FollowUp.case_id == Case.id)
        .outerjoin(CitizenProfile, FollowUp.citizen_id == CitizenProfile.id)
    )

    now = datetime.now(timezone.utc)

    # Filter logic
    if status_filter in ["ACTIONABLE", "ACTION_REQUIRED"]:
        query = query.filter(
            FollowUp.status.in_(["ESCALATED", "COMPLETED", "PENDING", "IN_PROGRESS", "SCHEDULED", "ACTION_ASSIGNED", "DOCTOR_ACKNOWLEDGED"]),
            FollowUp.reviewed_by_doctor_at.is_(None)
        )
    elif status_filter == "ESCALATED":
        query = query.filter(FollowUp.status == "ESCALATED")
    elif status_filter in ["COMPLETED", "RESULT_READY"]:
        query = query.filter(FollowUp.status == "COMPLETED", FollowUp.reviewed_by_doctor_at.is_(None))
    elif status_filter == "OVERDUE":
        query = query.filter(FollowUp.status.in_(["PENDING", "IN_PROGRESS", "SCHEDULED"]), FollowUp.due_at < now)
    elif status_filter == "PENDING":
        query = query.filter(FollowUp.status.in_(["PENDING", "IN_PROGRESS", "SCHEDULED"]))
    elif status_filter == "REVIEWED":
        query = query.filter(FollowUp.reviewed_by_doctor_at.isnot(None))
    elif status_filter == "RESOLVED":
        query = query.filter(FollowUp.status == "REVIEWED")
    elif status_filter == "CANCELLED":
        query = query.filter(FollowUp.status == "CANCELLED")

    if priority_filter:
        query = query.filter(FollowUp.priority == priority_filter)

    if village_filter:
        query = query.filter(CitizenProfile.village_name.ilike(f"%{village_filter}%"))

    if query_str:
        q = f"%{query_str}%"
        query = query.filter(
            or_(
                CitizenProfile.display_name.ilike(q),
                Case.reference.ilike(q),
                FollowUp.id.ilike(q),
                FollowUp.instructions.ilike(q)
            )
        )

    # Calculate total distinct count
    total_count = query.with_entities(func.count(distinct(FollowUp.id))).scalar() or 0

    # Custom ordering based on state priority
    status_order = case(
        (FollowUp.status == "ESCALATED", 1),
        (and_(FollowUp.status.in_(["PENDING", "IN_PROGRESS"]), FollowUp.due_at < now), 2),
        (FollowUp.status == "COMPLETED", 3),
        else_=4
    )

    followups = (
        query.order_by(status_order, FollowUp.due_at.asc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    # Deduplicate canonical items safely
    seen_ids = set()
    items = []
    for f in followups:
        if f.id not in seen_ids:
            seen_ids.add(f.id)
            items.append(get_followup_canonical_dto(f, db, doctor_user))

    return items, total_count


def review_doctor_followup(
    db: Session,
    followup_id: str,
    doctor_user: User,
    review_notes: str,
    next_action: Optional[str] = "NO_FURTHER_ACTION"
) -> Dict[str, Any]:
    """
    Doctor reviews completed follow-up. Sets status to REVIEWED,
    records reviewed_by_doctor_at, and decrements active monitor count.
    """
    f = db.query(FollowUp).filter(FollowUp.id == followup_id).first()
    if not f:
        raise HTTPException(status_code=404, detail={"code": "FOLLOWUP_NOT_FOUND", "message": "Follow-up record not found"})

    now = datetime.now(timezone.utc)
    f.status = "REVIEWED"
    f.reviewed_by_doctor_at = now
    f.reviewed_by_doctor_id = doctor_user.id
    if review_notes:
        f.completion_notes = (f.completion_notes or "") + f"\n[Doctor Review Note]: {review_notes}"

    db.commit()
    db.refresh(f)

    publish_domain_event(
        event_name="FOLLOWUP_REVIEWED",
        payload={
            "follow_up_id": f.id,
            "case_id": f.case_id,
            "reviewed_by_doctor_name": doctor_user.name,
            "reviewed_at": now.isoformat(),
            "next_action": next_action
        },
        target_roles=["ASHA_WORKER", "PHC_DOCTOR"]
    )

    return get_followup_canonical_dto(f, db, doctor_user)


def reschedule_doctor_followup(
    db: Session,
    followup_id: str,
    doctor_user: User,
    new_due_at: datetime,
    reason: str
) -> Dict[str, Any]:
    f = db.query(FollowUp).filter(FollowUp.id == followup_id).first()
    if not f:
        raise HTTPException(status_code=404, detail={"code": "FOLLOWUP_NOT_FOUND", "message": "Follow-up record not found"})

    f.due_at = new_due_at
    f.status = "RESCHEDULED"
    if reason:
        f.instructions = (f.instructions or "") + f"\n[Rescheduled by Doctor]: {reason}"

    db.commit()
    db.refresh(f)

    publish_domain_event(
        event_name="FOLLOWUP_RESCHEDULED",
        payload={
            "follow_up_id": f.id,
            "case_id": f.case_id,
            "new_due_at": new_due_at.isoformat(),
            "reason": reason
        },
        target_roles=["ASHA_WORKER", "PHC_DOCTOR"]
    )

    return get_followup_canonical_dto(f, db, doctor_user)


def cancel_doctor_followup(
    db: Session,
    followup_id: str,
    doctor_user: User,
    reason: str
) -> Dict[str, Any]:
    f = db.query(FollowUp).filter(FollowUp.id == followup_id).first()
    if not f:
        raise HTTPException(status_code=404, detail={"code": "FOLLOWUP_NOT_FOUND", "message": "Follow-up record not found"})

    f.status = "CANCELLED"
    f.completion_notes = f"[Cancelled by Doctor]: {reason}"

    db.commit()
    db.refresh(f)

    publish_domain_event(
        event_name="FOLLOWUP_CANCELLED",
        payload={
            "follow_up_id": f.id,
            "case_id": f.case_id,
            "reason": reason
        },
        target_roles=["ASHA_WORKER", "PHC_DOCTOR"]
    )

    return get_followup_canonical_dto(f, db, doctor_user)


def get_doctor_followups_summary(db: Session, doctor_user: User) -> Dict[str, int]:
    """
    Returns summary metric counts for PHC Doctor Follow-up Workspace.
    """
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    tomorrow_start = today_start + timedelta(days=1)

    # Base query
    base = db.query(FollowUp)

    results_ready = base.filter(FollowUp.status == "COMPLETED", FollowUp.reviewed_by_doctor_at.is_(None)).count()
    escalated = base.filter(FollowUp.status == "ESCALATED").count()
    overdue = base.filter(FollowUp.status.in_(["PENDING", "IN_PROGRESS", "SCHEDULED"]), FollowUp.due_at < now).count()
    due_today = base.filter(
        FollowUp.status.in_(["PENDING", "IN_PROGRESS", "SCHEDULED"]),
        FollowUp.due_at >= today_start,
        FollowUp.due_at < tomorrow_start
    ).count()
    pending = base.filter(FollowUp.status.in_(["PENDING", "IN_PROGRESS", "SCHEDULED"])).count()
    reviewed_today = base.filter(FollowUp.reviewed_by_doctor_at >= today_start).count()
    resolved_today = base.filter(FollowUp.status.in_(["RESOLVED", "REVIEWED"]), FollowUp.updated_at >= today_start).count()

    total_actionable = results_ready + escalated + overdue

    return {
        "results_ready_count": results_ready,
        "escalated_count": escalated,
        "overdue_count": overdue,
        "due_today_count": due_today,
        "pending_count": pending,
        "reviewed_today_count": reviewed_today,
        "resolved_today_count": resolved_today,
        "total_actionable": total_actionable
    }


def acknowledge_doctor_followup(db: Session, followup_id: str, doctor_user: User) -> Dict[str, Any]:
    f = db.query(FollowUp).filter(FollowUp.id == followup_id).first()
    if not f:
        raise HTTPException(status_code=404, detail={"code": "FOLLOWUP_NOT_FOUND", "message": "Follow-up record not found"})

    now = datetime.now(timezone.utc)
    f.status = "DOCTOR_ACKNOWLEDGED"

    esc = db.query(FollowUpEscalation).filter(FollowUpEscalation.follow_up_id == f.id).first()
    if esc:
        esc.status = "DOCTOR_ACKNOWLEDGED"
        esc.acknowledged_at = now
        esc.acknowledged_by = doctor_user.id

    db.commit()
    db.refresh(f)

    publish_domain_event(
        event_name="FOLLOWUP_DOCTOR_ACKNOWLEDGED",
        payload={
            "follow_up_id": f.id,
            "case_id": f.case_id,
            "doctor_name": doctor_user.name,
            "acknowledged_at": now.isoformat()
        },
        target_roles=["ASHA_WORKER", "PHC_DOCTOR"]
    )

    return get_followup_canonical_dto(f, db, doctor_user)


def update_doctor_followup_directive(
    db: Session,
    followup_id: str,
    doctor_user: User,
    instructions: str,
    due_at: Optional[datetime] = None,
    priority: Optional[str] = None
) -> Dict[str, Any]:
    f = db.query(FollowUp).filter(FollowUp.id == followup_id).first()
    if not f:
        raise HTTPException(status_code=404, detail={"code": "FOLLOWUP_NOT_FOUND", "message": "Follow-up record not found"})

    f.status = "ACTION_ASSIGNED"
    if instructions:
        f.instructions = instructions
    if due_at:
        f.due_at = due_at
    if priority and hasattr(CasePriorityEnum, priority):
        f.priority = getattr(CasePriorityEnum, priority)

    esc = db.query(FollowUpEscalation).filter(FollowUpEscalation.follow_up_id == f.id).first()
    if esc:
        esc.status = "ACTION_ASSIGNED"
        esc.action_type = "MODIFY_DIRECTIVE"
        esc.action_notes = instructions

    db.commit()
    db.refresh(f)

    publish_domain_event(
        event_name="FOLLOWUP_DIRECTIVE_UPDATED",
        payload={
            "follow_up_id": f.id,
            "case_id": f.case_id,
            "instructions": instructions,
            "due_at": f.due_at.isoformat() if f.due_at else None,
            "updated_by": doctor_user.name
        },
        target_roles=["ASHA_WORKER", "PHC_DOCTOR"]
    )

    return get_followup_canonical_dto(f, db, doctor_user)


def resolve_doctor_followup(
    db: Session,
    followup_id: str,
    doctor_user: User,
    resolution_notes: str,
    resolution_outcome: Optional[str] = "RESOLVED_SATISFACTORILY"
) -> Dict[str, Any]:
    f = db.query(FollowUp).filter(FollowUp.id == followup_id).first()
    if not f:
        raise HTTPException(status_code=404, detail={"code": "FOLLOWUP_NOT_FOUND", "message": "Follow-up record not found"})

    now = datetime.now(timezone.utc)
    f.status = "RESOLVED"
    f.reviewed_by_doctor_at = now
    f.reviewed_by_doctor_id = doctor_user.id
    if resolution_notes:
        f.completion_notes = (f.completion_notes or "") + f"\n[Resolution Note]: {resolution_notes}"

    esc = db.query(FollowUpEscalation).filter(FollowUpEscalation.follow_up_id == f.id).first()
    if esc:
        esc.status = "RESOLVED"
        esc.resolved_at = now
        esc.resolved_by = doctor_user.id
        esc.resolution = resolution_notes
        esc.resolution_outcome = resolution_outcome

    db.commit()
    db.refresh(f)

    publish_domain_event(
        event_name="FOLLOWUP_RESOLVED",
        payload={
            "follow_up_id": f.id,
            "case_id": f.case_id,
            "resolved_by": doctor_user.name,
            "resolved_at": now.isoformat(),
            "outcome": resolution_outcome
        },
        target_roles=["ASHA_WORKER", "PHC_DOCTOR"]
    )

    return get_followup_canonical_dto(f, db, doctor_user)


def request_repeat_vitals(
    db: Session,
    followup_id: str,
    doctor_user: User,
    vitals_to_repeat: List[str],
    notes: Optional[str] = None
) -> Dict[str, Any]:
    f = db.query(FollowUp).filter(FollowUp.id == followup_id).first()
    if not f:
        raise HTTPException(status_code=404, detail={"code": "FOLLOWUP_NOT_FOUND", "message": "Follow-up record not found"})

    f.status = "ACTION_ASSIGNED"
    f.measurements_to_repeat = vitals_to_repeat
    if notes:
        f.instructions = (f.instructions or "") + f"\n[Repeat Vitals Requested]: {notes}"

    db.commit()
    db.refresh(f)

    publish_domain_event(
        event_name="FOLLOWUP_DIRECTIVE_UPDATED",
        payload={
            "follow_up_id": f.id,
            "case_id": f.case_id,
            "vitals_to_repeat": vitals_to_repeat,
            "notes": notes,
            "updated_by": doctor_user.name
        },
        target_roles=["ASHA_WORKER", "PHC_DOCTOR"]
    )

    return get_followup_canonical_dto(f, db, doctor_user)
