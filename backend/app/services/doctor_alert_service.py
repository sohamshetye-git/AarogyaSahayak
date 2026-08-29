"""
Doctor Alert Service
Encapsulates PHC Doctor Alert query logic, lifecycle status transitions, audit logging,
and idempotent creation from real domain workflow events.
"""

from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timezone, timedelta
import uuid
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func, desc

from app.models import DoctorAlert, AlertAction, User, CitizenProfile, Case, Referral, Consultation, InvestigationOrder, FollowUp, AuditLog, UserRoleEnum

IST = timezone(timedelta(hours=5, minutes=30))

class DoctorAlertService:

    @staticmethod
    def _generate_alert_ref() -> str:
        s = uuid.uuid4().hex[:6].upper()
        return f"ALT-{s}"

    @staticmethod
    def get_doctor_alerts(
        db: Session,
        facility_id: str,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        category: Optional[str] = None,
        severity: Optional[str] = None,
        status: Optional[str] = None,
        village: Optional[str] = None,
        source_entity_type: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        sort_by: Optional[str] = "newest"
    ) -> Tuple[List[DoctorAlert], int]:
        q = db.query(DoctorAlert).filter(DoctorAlert.facility_id == facility_id)

        if village:
            q = q.join(CitizenProfile, DoctorAlert.citizen_id == CitizenProfile.id).filter(CitizenProfile.village_name == village)

        if category:
            q = q.filter(DoctorAlert.category == category.upper())
        if severity:
            q = q.filter(DoctorAlert.severity == severity.upper())
        if status:
            if status.upper() == "UNREAD":
                q = q.filter(DoctorAlert.status.in_(["NEW", "SEEN"]))
            elif status.upper() == "ACTIVE":
                q = q.filter(DoctorAlert.status.in_(["NEW", "SEEN", "ACKNOWLEDGED", "IN_ACTION", "SNOOZED"]))
            else:
                q = q.filter(DoctorAlert.status == status.upper())
        if source_entity_type:
            q = q.filter(DoctorAlert.source_entity_type == source_entity_type.upper())

        if date_from:
            try:
                dt_from = datetime.fromisoformat(date_from).replace(tzinfo=timezone.utc)
                q = q.filter(DoctorAlert.created_at >= dt_from)
            except Exception:
                pass
        if date_to:
            try:
                dt_to = datetime.fromisoformat(date_to).replace(tzinfo=timezone.utc) + timedelta(days=1)
                q = q.filter(DoctorAlert.created_at <= dt_to)
            except Exception:
                pass

        if search:
            s_term = f"%{search}%"
            q = q.outerjoin(CitizenProfile, DoctorAlert.citizen_id == CitizenProfile.id)\
                 .outerjoin(Case, DoctorAlert.case_id == Case.id)\
                 .filter(
                     or_(
                         DoctorAlert.title.ilike(s_term),
                         DoctorAlert.alert_reference.ilike(s_term),
                         DoctorAlert.safe_summary.ilike(s_term),
                         CitizenProfile.display_name.ilike(s_term),
                         Case.reference.ilike(s_term)
                     )
                 )

        total = q.count()

        if sort_by == "oldest":
            q = q.order_by(DoctorAlert.created_at.asc())
        elif sort_by == "severity":
            # Order CRITICAL -> URGENT -> HIGH -> INFORMATION
            q = q.order_by(
                func.case(
                    (DoctorAlert.severity == "CRITICAL", 1),
                    (DoctorAlert.severity == "URGENT", 2),
                    (DoctorAlert.severity == "HIGH", 3),
                    else_=4
                ),
                DoctorAlert.created_at.desc()
            )
        elif sort_by == "due_date":
            q = q.order_by(DoctorAlert.response_due_at.asc().nullslast())
        else:
            q = q.order_by(DoctorAlert.created_at.desc())

        offset = (page - 1) * page_size
        items = q.offset(offset).limit(page_size).all()
        return items, total

    @staticmethod
    def get_alerts_summary(db: Session, facility_id: str) -> Dict[str, int]:
        base_q = db.query(DoctorAlert).filter(DoctorAlert.facility_id == facility_id)
        
        critical = base_q.filter(DoctorAlert.severity == "CRITICAL", DoctorAlert.status.notin_(["RESOLVED", "DISMISSED"])).count()
        urgent = base_q.filter(DoctorAlert.severity == "URGENT", DoctorAlert.status.notin_(["RESOLVED", "DISMISSED"])).count()
        unread = base_q.filter(DoctorAlert.status.in_(["NEW", "SEEN"])).count()
        acknowledged = base_q.filter(DoctorAlert.status == "ACKNOWLEDGED").count()
        snoozed = base_q.filter(DoctorAlert.status == "SNOOZED").count()
        system = base_q.filter(DoctorAlert.category == "SYSTEM", DoctorAlert.status.notin_(["RESOLVED", "DISMISSED"])).count()
        
        today_utc = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        resolved_today = base_q.filter(DoctorAlert.status == "RESOLVED", DoctorAlert.resolved_at >= today_utc).count()

        return {
            "critical": critical,
            "urgent": urgent,
            "unread": unread,
            "acknowledged": acknowledged,
            "snoozed": snoozed,
            "system": system,
            "resolved_today": resolved_today,
            "total_active": base_q.filter(DoctorAlert.status.notin_(["RESOLVED", "DISMISSED"])).count()
        }

    @staticmethod
    def get_alert_by_id(db: Session, alert_id: str, facility_id: str) -> Optional[DoctorAlert]:
        return db.query(DoctorAlert).filter(
            or_(DoctorAlert.id == alert_id, DoctorAlert.alert_reference == alert_id),
            DoctorAlert.facility_id == facility_id
        ).first()

    @staticmethod
    def mark_seen(db: Session, alert: DoctorAlert, user: User) -> DoctorAlert:
        if alert.status == "NEW":
            prev = alert.status
            alert.status = "SEEN"
            alert.seen_at = datetime.now(timezone.utc)
            
            action = AlertAction(
                alert_id=alert.id,
                action="SEEN",
                previous_status=prev,
                new_status="SEEN",
                actor_id=user.id,
                actor_role=user.role.value if hasattr(user.role, "value") else str(user.role)
            )
            db.add(action)
            db.commit()
            db.refresh(alert)
        return alert

    @staticmethod
    def acknowledge_alert(db: Session, alert: DoctorAlert, user: User, note: Optional[str] = None) -> DoctorAlert:
        if alert.status in ["RESOLVED", "DISMISSED"]:
            return alert

        prev = alert.status
        alert.status = "ACKNOWLEDGED"
        alert.acknowledged_at = datetime.now(timezone.utc)
        alert.acknowledged_by_id = user.id

        action = AlertAction(
            alert_id=alert.id,
            action="ACKNOWLEDGED",
            previous_status=prev,
            new_status="ACKNOWLEDGED",
            actor_id=user.id,
            actor_role=user.role.value if hasattr(user.role, "value") else str(user.role),
            note=note
        )
        db.add(action)
        db.commit()
        db.refresh(alert)
        return alert

    @staticmethod
    def snooze_alert(db: Session, alert: DoctorAlert, user: User, hours: int = 4, reason: Optional[str] = None) -> DoctorAlert:
        prev = alert.status
        alert.status = "SNOOZED"
        alert.snoozed_until = datetime.now(timezone.utc) + timedelta(hours=hours)
        alert.snooze_reason = reason

        action = AlertAction(
            alert_id=alert.id,
            action="SNOOZED",
            previous_status=prev,
            new_status="SNOOZED",
            actor_id=user.id,
            actor_role=user.role.value if hasattr(user.role, "value") else str(user.role),
            note=f"Snoozed for {hours}h. Reason: {reason or 'None'}"
        )
        db.add(action)
        db.commit()
        db.refresh(alert)
        return alert

    @staticmethod
    def resolve_alert(db: Session, alert: DoctorAlert, user: User, note: str) -> DoctorAlert:
        prev = alert.status
        alert.status = "RESOLVED"
        alert.resolved_at = datetime.now(timezone.utc)
        alert.resolved_by_id = user.id
        alert.resolution_note = note

        action = AlertAction(
            alert_id=alert.id,
            action="RESOLVED",
            previous_status=prev,
            new_status="RESOLVED",
            actor_id=user.id,
            actor_role=user.role.value if hasattr(user.role, "value") else str(user.role),
            note=note
        )
        db.add(action)
        db.commit()
        db.refresh(alert)
        return alert

    @staticmethod
    def dismiss_alert(db: Session, alert: DoctorAlert, user: User, reason: str) -> DoctorAlert:
        if alert.severity == "CRITICAL" and not reason:
            raise ValueError("Critical alerts cannot be dismissed without an authorized reason.")

        prev = alert.status
        alert.status = "DISMISSED"
        alert.dismissed_at = datetime.now(timezone.utc)
        alert.dismissed_by_id = user.id
        alert.dismissal_reason = reason

        action = AlertAction(
            alert_id=alert.id,
            action="DISMISSED",
            previous_status=prev,
            new_status="DISMISSED",
            actor_id=user.id,
            actor_role=user.role.value if hasattr(user.role, "value") else str(user.role),
            note=reason
        )
        db.add(action)
        db.commit()
        db.refresh(alert)
        return alert

    @staticmethod
    def create_or_update_alert_from_event(
        db: Session,
        facility_id: str,
        category: str,
        alert_type: str,
        severity: str,
        title: str,
        safe_summary: str,
        source_entity_type: str,
        source_entity_id: str,
        citizen_id: Optional[str] = None,
        case_id: Optional[str] = None,
        doctor_id: Optional[str] = None,
        source_event_id: Optional[str] = None,
        response_due_hours: int = 4
    ) -> DoctorAlert:
        """Idempotent creation of DoctorAlert using deduplication key (type+entity_type+entity_id)."""
        existing = db.query(DoctorAlert).filter(
            DoctorAlert.facility_id == facility_id,
            DoctorAlert.alert_type == alert_type,
            DoctorAlert.source_entity_type == source_entity_type,
            DoctorAlert.source_entity_id == source_entity_id,
            DoctorAlert.status.notin_(["RESOLVED", "DISMISSED"])
        ).first()

        if existing:
            existing.title = title
            existing.safe_summary = safe_summary
            existing.severity = severity
            db.commit()
            db.refresh(existing)
            return existing

        alert = DoctorAlert(
            alert_reference=DoctorAlertService._generate_alert_ref(),
            facility_id=facility_id,
            doctor_id=doctor_id,
            citizen_id=citizen_id,
            case_id=case_id,
            category=category.upper(),
            alert_type=alert_type,
            severity=severity.upper(),
            title=title,
            safe_summary=safe_summary,
            source_entity_type=source_entity_type.upper(),
            source_entity_id=source_entity_id,
            source_event_id=source_event_id,
            status="NEW",
            response_due_at=datetime.now(timezone.utc) + timedelta(hours=response_due_hours)
        )
        db.add(alert)
        db.commit()
        db.refresh(alert)

        action = AlertAction(
            alert_id=alert.id,
            action="CREATED",
            previous_status=None,
            new_status="NEW",
            actor_id=doctor_id,
            actor_role="SYSTEM"
        )
        db.add(action)
        db.commit()
        return alert
