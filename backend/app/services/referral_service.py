import random
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models import (
    Case, Referral, Facility, User, Notification, AuditLog, 
    CaseStatusEnum, CasePriorityEnum
)
from app.schemas import AshaReferralRequest
from app.services.case_service import CaseService

class ReferralService:
    @staticmethod
    def generate_reference(prefix: str = "REF") -> str:
        num = random.randint(100000, 999999)
        return f"{prefix}-2026-{num}"

    @classmethod
    def create_referral(
        cls,
        db: Session,
        case: Case,
        asha_user: User,
        req: AshaReferralRequest
    ) -> Referral:
        # Find facility
        facility = db.query(Facility).filter(Facility.id == req.facility_id).first()
        facility_name = facility.name if facility else "Kalyanpur PHC"

        referral = Referral(
            reference=cls.generate_reference("REF"),
            case_id=case.id,
            from_asha_id=asha_user.id,
            to_facility_id=req.facility_id,
            to_facility_name=facility_name,
            urgency=CasePriorityEnum(req.urgency) if req.urgency in CasePriorityEnum.__members__ else CasePriorityEnum.URGENT,
            reason=req.reason,
            status="PENDING_DOCTOR_REVIEW"
        )
        db.add(referral)
        db.flush()

        # Update case state
        CaseService.update_status(db, case, CaseStatusEnum.REFERRED_TO_PHC)
        case.assigned_facility_id = req.facility_id
        case.assigned_facility_name = facility_name

        # Notify PHC Doctor
        doctor = db.query(User).filter(User.role == "PHC_DOCTOR").first()
        if doctor:
            notif = Notification(
                recipient_user_id=doctor.id,
                case_id=case.id,
                notification_type="PHC_REFERRAL_ALERT",
                title=f"New Referral: {referral.reference}",
                message=f"Patient {case.citizen.display_name} referred by ASHA {asha_user.name} for: {req.reason}",
                priority=referral.urgency
            )
            db.add(notif)

        # Audit
        audit = AuditLog(
            actor_user_id=asha_user.id,
            actor_role="ASHA_WORKER",
            action="REFERRAL_CREATED",
            resource_type="Referral",
            resource_id=referral.id,
            outcome="SUCCESS",
            metadata_json={"to_facility": facility_name, "urgency": referral.urgency.value}
        )
        db.add(audit)
        db.commit()
        db.refresh(referral)
        return referral

    @classmethod
    def acknowledge_referral(
        cls,
        db: Session,
        case_id: str,
        doctor_user: User
    ) -> Referral:
        referral = db.query(Referral).filter(Referral.case_id == case_id).first()
        if referral:
            referral.status = "ACKNOWLEDGED"
            referral.acknowledged_by = doctor_user.name
            referral.acknowledged_at = datetime.now(timezone.utc)
        
        case = db.query(Case).filter(Case.id == case_id).first()
        if case:
            CaseService.update_status(db, case, CaseStatusEnum.DOCTOR_ACKNOWLEDGED)
            case.assigned_doctor_id = doctor_user.id
            case.assigned_doctor_name = doctor_user.name

            # Notify ASHA that doctor acknowledged
            if case.assigned_asha_id:
                notif = Notification(
                    recipient_user_id=case.assigned_asha_id,
                    case_id=case.id,
                    notification_type="DOCTOR_ACKNOWLEDGED",
                    title="Doctor Acknowledged Referral",
                    message=f"Dr. {doctor_user.name} has acknowledged referral for {case.citizen.display_name} ({case.reference}).",
                    priority=case.priority
                )
                db.add(notif)

        # Audit
        audit = AuditLog(
            actor_user_id=doctor_user.id,
            actor_role="PHC_DOCTOR",
            action="REFERRAL_ACKNOWLEDGED",
            resource_type="Case",
            resource_id=case_id,
            outcome="SUCCESS"
        )
        db.add(audit)
        db.commit()
        return referral
