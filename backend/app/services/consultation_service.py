import random
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from app.models import (
    Case, Consultation, Prescription, PrescriptionItem, TestOrder, FollowUp,
    User, AuditLog, Notification, CaseStatusEnum, CasePriorityEnum, UserRoleEnum
)
from app.schemas import DoctorConsultationSubmitRequest
from app.services.case_service import CaseService

class ConsultationService:
    @staticmethod
    def generate_reference(prefix: str = "CONS") -> str:
        num = random.randint(100, 999)
        return f"{prefix}-2026-{num}"

    @classmethod
    def complete_consultation(
        cls,
        db: Session,
        doctor_user: User,
        req: DoctorConsultationSubmitRequest
    ) -> Consultation:
        case = db.query(Case).filter(Case.id == req.case_id).first()
        if not case:
            raise ValueError("Case not found")

        facility_id = case.assigned_facility_id or "PHC-09"

        # Create Consultation Record
        consultation = Consultation(
            reference=cls.generate_reference("CONS"),
            case_id=case.id,
            doctor_id=doctor_user.id,
            doctor_name=doctor_user.name,
            facility_id=facility_id,
            consultation_type="IN_PERSON_PHC",
            status="COMPLETED",
            examination_notes=req.examination_notes,
            clinical_summary=req.clinical_summary,
            provisional_diagnosis=req.provisional_diagnosis,
            confirmed_diagnosis=req.confirmed_diagnosis,
            icd10_code=req.icd10_code or "O14.9", # Pre-eclampsia / maternal default if pregnancy
            care_plan_summary=req.care_plan_summary,
            asha_followup_instructions=req.asha_followup_instructions,
            followup_due_days=req.followup_due_days,
            completed_at=datetime.now(timezone.utc),
            signed_at=datetime.now(timezone.utc)
        )
        db.add(consultation)
        db.flush()

        # Create Prescription if items provided
        if req.prescription_items:
            prescription = Prescription(
                consultation_id=consultation.id,
                doctor_id=doctor_user.id,
                status="SIGNED",
                signature_ref=f"SIG-DR-{doctor_user.name.upper()[:6]}-{int(datetime.now(timezone.utc).timestamp())}"
            )
            db.add(prescription)
            db.flush()

            for item in req.prescription_items:
                p_item = PrescriptionItem(
                    prescription_id=prescription.id,
                    medicine=item.medicine,
                    strength=item.strength,
                    form=item.form,
                    dose=item.dose,
                    frequency=item.frequency,
                    duration=item.duration,
                    timing=item.timing,
                    instructions=item.instructions
                )
                db.add(p_item)

        # Create Test Orders if any
        for test in req.investigation_orders:
            t_order = TestOrder(
                consultation_id=consultation.id,
                test_name=test,
                priority="URGENT" if case.priority == CasePriorityEnum.URGENT else "ROUTINE",
                reason=req.confirmed_diagnosis,
                facility_id=facility_id,
                status="ORDERED"
            )
            db.add(t_order)

        # Create ASHA Follow-up
        if req.asha_followup_instructions or req.followup_due_days:
            due_date = datetime.now(timezone.utc) + timedelta(days=req.followup_due_days)
            followup = FollowUp(
                case_id=case.id,
                task_type="POST_CONSULTATION_VITALS_CHECK",
                assigned_role=UserRoleEnum.ASHA_WORKER,
                assigned_user_id=case.assigned_asha_id,
                instructions=req.asha_followup_instructions or f"Check BP and adherence for {req.confirmed_diagnosis}",
                priority=CasePriorityEnum.HIGH,
                due_at=due_date,
                status="PENDING"
            )
            db.add(followup)

            # Notify ASHA of new follow-up
            if case.assigned_asha_id:
                notif = Notification(
                    recipient_user_id=case.assigned_asha_id,
                    case_id=case.id,
                    notification_type="FOLLOW_UP_ASSIGNED",
                    title=f"New Follow-up Task: {case.reference}",
                    message=f"Dr. {doctor_user.name} assigned follow-up for {case.citizen.display_name}. Due in {req.followup_due_days} days.",
                    priority=CasePriorityEnum.HIGH
                )
                db.add(notif)

        # Update Case State to FOLLOW_UP_REQUIRED or COMPLETED
        new_status = CaseStatusEnum.FOLLOW_UP_REQUIRED if req.asha_followup_instructions else CaseStatusEnum.COMPLETED
        CaseService.update_status(db, case, new_status)
        case.completed_at = datetime.now(timezone.utc)

        # Notify Citizen that consultation is complete and care plan is ready
        if case.citizen and case.citizen.user_id:
            c_notif = Notification(
                recipient_user_id=case.citizen.user_id,
                case_id=case.id,
                notification_type="CARE_PLAN_READY",
                title="Doctor Consultation Complete",
                message=f"Dr. {doctor_user.name} has signed your care plan and prescription. Your ASHA worker will assist with follow-up.",
                priority=CasePriorityEnum.ROUTINE
            )
            db.add(c_notif)

        # Audit
        audit = AuditLog(
            actor_user_id=doctor_user.id,
            actor_role="PHC_DOCTOR",
            action="CONSULTATION_COMPLETED",
            resource_type="Consultation",
            resource_id=consultation.id,
            outcome="SUCCESS",
            metadata_json={"diagnosis": req.confirmed_diagnosis, "followup_due_days": req.followup_due_days}
        )
        db.add(audit)
        db.commit()
        db.refresh(consultation)
        return consultation
