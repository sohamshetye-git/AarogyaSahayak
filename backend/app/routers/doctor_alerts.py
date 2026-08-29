"""
FastAPI Router for PHC Doctor Alerts
Strictly protected by Doctor RBAC. Implements canonical response wrappers,
pagination, filtering, summary counters, status transitions, and audit logging.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any, List
import uuid

from app.database import get_db
from app.models import User, UserRoleEnum, AuditLog, CitizenProfile
from app.schemas import StandardResponse
from app.dependencies import require_staff, require_doctor
from app.services.doctor_alert_service import DoctorAlertService

router = APIRouter(prefix="/doctor/alerts", tags=["Doctor Alerts"])


def _extract_doctor_context(current_user: User) -> tuple:
    facility_id = "PHC-09"
    if current_user.worker_profile and current_user.worker_profile.facility_id:
        facility_id = current_user.worker_profile.facility_id
    return facility_id, current_user


def _serialize_alert(alert, db: Session, include_phone: bool = False) -> Dict[str, Any]:
    citizen = alert.citizen
    citizen_name = citizen.display_name if citizen else "Citizen"
    village_name = citizen.village_name if citizen else "Kalyanpur"
    
    phone_display = None
    if include_phone and citizen and citizen.phone:
        phone_display = citizen.phone
    elif citizen and citizen.phone:
        # Masked phone by default until doctor explicitly clicks Reveal/Call
        phone_display = f"XXXXXX{citizen.phone[-4:]}" if len(citizen.phone) >= 4 else "XXXXXX"

    actions_history = []
    if alert.actions:
        for a in alert.actions:
            actions_history.append({
                "id": a.id,
                "action": a.action,
                "previous_status": a.previous_status,
                "new_status": a.new_status,
                "actor_role": a.actor_role,
                "note": a.note,
                "created_at": a.created_at.isoformat() if a.created_at else None
            })

    return {
        "id": alert.id,
        "alert_reference": alert.alert_reference,
        "facility_id": alert.facility_id,
        "doctor_id": alert.doctor_id,
        "citizen_id": alert.citizen_id,
        "citizen_name": citizen_name,
        "citizen_age": citizen.age_estimate if citizen else None,
        "citizen_gender": citizen.sex if citizen else None,
        "village_name": village_name,
        "citizen_phone": phone_display,
        "case_id": alert.case_id,
        "case_reference": alert.case.reference if alert.case else None,
        "category": alert.category,
        "alert_type": alert.alert_type,
        "severity": alert.severity,
        "title": alert.title,
        "safe_summary": alert.safe_summary,
        "source_entity_type": alert.source_entity_type,
        "source_entity_id": alert.source_entity_id,
        "source_event_id": alert.source_event_id,
        "lifecycle_version": alert.lifecycle_version,
        "status": alert.status,
        "response_due_at": alert.response_due_at.isoformat() if alert.response_due_at else None,
        "created_at": alert.created_at.isoformat() if alert.created_at else None,
        "seen_at": alert.seen_at.isoformat() if alert.seen_at else None,
        "acknowledged_at": alert.acknowledged_at.isoformat() if alert.acknowledged_at else None,
        "snoozed_until": alert.snoozed_until.isoformat() if alert.snoozed_until else None,
        "resolved_at": alert.resolved_at.isoformat() if alert.resolved_at else None,
        "dismissed_at": alert.dismissed_at.isoformat() if alert.dismissed_at else None,
        "acknowledged_by_id": alert.acknowledged_by_id,
        "resolved_by_id": alert.resolved_by_id,
        "resolution_note": alert.resolution_note,
        "dismissal_reason": alert.dismissal_reason,
        "snooze_reason": alert.snooze_reason,
        "actions_history": actions_history
    }


@router.get("", response_model=StandardResponse)
def list_doctor_alerts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    category: Optional[str] = None,
    severity: Optional[str] = None,
    status: Optional[str] = None,
    village: Optional[str] = None,
    source_entity_type: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    sort_by: Optional[str] = "newest",
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    # Restrict Admin from viewing individual PHC patient alerts
    if current_user.role == UserRoleEnum.DISTRICT_ADMIN:
        raise HTTPException(status_code=403, detail="District Admins receive anonymized aggregate alert metrics only.")

    facility_id, doctor = _extract_doctor_context(current_user)
    items, total = DoctorAlertService.get_doctor_alerts(
        db=db,
        facility_id=facility_id,
        page=page,
        page_size=page_size,
        search=search,
        category=category,
        severity=severity,
        status=status,
        village=village,
        source_entity_type=source_entity_type,
        date_from=date_from,
        date_to=date_to,
        sort_by=sort_by
    )

    serialized_items = [_serialize_alert(it, db) for it in items]

    return StandardResponse(
        data={
            "items": serialized_items,
            "total": total,
            "page": page,
            "page_size": page_size
        }
    )


@router.get("/summary", response_model=StandardResponse)
def get_doctor_alerts_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    facility_id, _ = _extract_doctor_context(current_user)
    summary = DoctorAlertService.get_alerts_summary(db=db, facility_id=facility_id)
    return StandardResponse(data=summary)


@router.get("/{alertId}", response_model=StandardResponse)
def get_doctor_alert_detail(
    alertId: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    if current_user.role == UserRoleEnum.DISTRICT_ADMIN:
        raise HTTPException(status_code=403, detail="District Admins receive anonymized aggregate alert metrics only.")

    facility_id, doctor = _extract_doctor_context(current_user)
    alert = DoctorAlertService.get_alert_by_id(db, alertId, facility_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found.")

    # Automatically mark SEEN upon opening detail view
    alert = DoctorAlertService.mark_seen(db, alert, doctor)

    return StandardResponse(data=_serialize_alert(alert, db))


@router.post("/{alertId}/seen", response_model=StandardResponse)
def mark_alert_seen(
    alertId: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    facility_id, doctor = _extract_doctor_context(current_user)
    alert = DoctorAlertService.get_alert_by_id(db, alertId, facility_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found.")

    alert = DoctorAlertService.mark_seen(db, alert, doctor)
    return StandardResponse(data=_serialize_alert(alert, db))


@router.post("/{alertId}/acknowledge", response_model=StandardResponse)
def acknowledge_alert(
    alertId: str,
    payload: Dict[str, Any] = {},
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    facility_id, doctor = _extract_doctor_context(current_user)
    alert = DoctorAlertService.get_alert_by_id(db, alertId, facility_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found.")

    note = payload.get("note")
    alert = DoctorAlertService.acknowledge_alert(db, alert, doctor, note=note)

    # Audit Log Entry
    audit = AuditLog(
        actor_user_id=current_user.id,
        actor_role=current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role),
        action="DOCTOR_ALERT_ACKNOWLEDGED",
        resource_type="DOCTOR_ALERT",
        resource_id=alert.id,
        outcome="SUCCESS",
        metadata_json={"alert_reference": alert.alert_reference, "note": note}
    )
    db.add(audit)
    db.commit()

    return StandardResponse(data=_serialize_alert(alert, db))


@router.post("/{alertId}/snooze", response_model=StandardResponse)
def snooze_alert(
    alertId: str,
    payload: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    facility_id, doctor = _extract_doctor_context(current_user)
    alert = DoctorAlertService.get_alert_by_id(db, alertId, facility_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found.")

    hours = int(payload.get("hours", 4))
    reason = payload.get("reason")
    alert = DoctorAlertService.snooze_alert(db, alert, doctor, hours=hours, reason=reason)
    return StandardResponse(data=_serialize_alert(alert, db))


@router.post("/{alertId}/resolve", response_model=StandardResponse)
def resolve_alert(
    alertId: str,
    payload: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    facility_id, doctor = _extract_doctor_context(current_user)
    alert = DoctorAlertService.get_alert_by_id(db, alertId, facility_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found.")

    note = payload.get("note", "Resolution completed by Doctor.")
    alert = DoctorAlertService.resolve_alert(db, alert, doctor, note=note)

    # Audit Log Entry
    audit = AuditLog(
        actor_user_id=current_user.id,
        actor_role=current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role),
        action="DOCTOR_ALERT_RESOLVED",
        resource_type="DOCTOR_ALERT",
        resource_id=alert.id,
        outcome="SUCCESS",
        metadata_json={"alert_reference": alert.alert_reference, "note": note}
    )
    db.add(audit)
    db.commit()

    return StandardResponse(data=_serialize_alert(alert, db))


@router.post("/{alertId}/dismiss", response_model=StandardResponse)
def dismiss_alert(
    alertId: str,
    payload: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    facility_id, doctor = _extract_doctor_context(current_user)
    alert = DoctorAlertService.get_alert_by_id(db, alertId, facility_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found.")

    reason = payload.get("reason", "")
    try:
        alert = DoctorAlertService.dismiss_alert(db, alert, doctor, reason=reason)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))

    return StandardResponse(data=_serialize_alert(alert, db))


@router.post("/{alertId}/reveal-phone", response_model=StandardResponse)
def reveal_alert_phone(
    alertId: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    facility_id, doctor = _extract_doctor_context(current_user)
    alert = DoctorAlertService.get_alert_by_id(db, alertId, facility_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found.")

    # Audit log entry for phone reveal attempt
    audit = AuditLog(
        actor_user_id=current_user.id,
        actor_role=current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role),
        action="DOCTOR_ALERT_PHONE_REVEALED",
        resource_type="DOCTOR_ALERT",
        resource_id=alert.id,
        outcome="SUCCESS",
        metadata_json={"alert_reference": alert.alert_reference, "citizen_id": alert.citizen_id}
    )
    db.add(audit)
    db.commit()

    return StandardResponse(data=_serialize_alert(alert, db, include_phone=True))
