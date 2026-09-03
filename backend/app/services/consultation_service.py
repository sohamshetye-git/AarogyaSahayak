import uuid
import random
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from app.models import (
    Case, Consultation, Prescription, PrescriptionItem, TestOrder, FollowUp,
    User, AuditLog, Notification, CaseStatusEnum, CasePriorityEnum, UserRoleEnum, Referral,
    InvestigationOrder, InvestigationSample, utc_now
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

        # Retrieve referral if any
        referral = None
        if req.referral_id:
            referral = db.query(Referral).filter(Referral.id == req.referral_id).first()
        elif hasattr(case, "referrals") and case.referrals:
            referral = case.referrals[-1]

        # Create Prescription if items provided
        if req.prescription_items:
            p_ref = f"RX-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{consultation.id[:6].upper()}"
            prescription = Prescription(
                reference=p_ref,
                citizen_id=case.citizen_id,
                case_id=case.id,
                referral_id=referral.id if referral else None,
                consultation_id=consultation.id,
                prescriber_doctor_id=doctor_user.id,
                doctor_id=doctor_user.id,
                facility_id=facility_id,
                status="SIGNED",
                signed_at=datetime.now(timezone.utc)
            )
            db.add(prescription)
            db.flush()

            for item in req.prescription_items:
                p_item = PrescriptionItem(
                    prescription_id=prescription.id,
                    generic_name_snapshot=item.medicine,
                    medicine=item.medicine,
                    strength=item.strength,
                    formulation=getattr(item, "form", "Tablet") or "Tablet",
                    dose=item.dose,
                    frequency=item.frequency,
                    timing=item.timing or "After food",
                    duration_value=int(item.duration) if str(item.duration).isdigit() else 5,
                    instructions=item.instructions
                )
                db.add(p_item)

        # Create Test Orders if any (detailed or simple)
        if req.investigation_orders_detailed:
            for d_test in req.investigation_orders_detailed:
                t_order = TestOrder(
                    consultation_id=consultation.id,
                    test_name=d_test.test_name,
                    priority=d_test.priority,
                    reason=d_test.clinical_reason or req.confirmed_diagnosis,
                    facility_id=facility_id,
                    status=d_test.status or "ORDERED"
                )
                db.add(t_order)

                # Persist canonical InvestigationOrder for Doctor Workspace & Citizen portal
                inv_ref = f"INV-{datetime.now(timezone.utc).year}-{uuid.uuid4().hex[:6].upper()}"
                now_utc = utc_now()
                inv_order = InvestigationOrder(
                    reference=inv_ref,
                    citizen_id=case.citizen_id,
                    case_id=case.id,
                    consultation_id=consultation.id,
                    ordered_by_doctor_id=doctor_user.id,
                    facility_id=facility_id,
                    test_name=d_test.test_name,
                    test_code=d_test.test_code,
                    category=d_test.category or "GENERAL",
                    priority=d_test.priority or "ROUTINE",
                    clinical_reason=d_test.clinical_reason or req.confirmed_diagnosis,
                    specimen_type=d_test.specimen_type or "Blood / Urine",
                    preparation_instructions=d_test.preparation_instructions or "Standard preparation",
                    collection_location=d_test.collection_location or "PHC Kalyanpur Sample Collection Counter",
                    ordered_at=now_utc,
                    due_at=now_utc + timedelta(days=1),
                    expected_result_at=now_utc + timedelta(days=2),
                    status="SAMPLE_PENDING"
                )
                db.add(inv_order)
                db.flush()
                db.add(InvestigationSample(
                    investigation_order_id=inv_order.id,
                    sample_reference=f"SMP-{inv_order.reference}",
                    collection_status="PENDING"
                ))
        elif req.investigation_orders:
            for test in req.investigation_orders:
                t_priority = "URGENT" if case.priority == CasePriorityEnum.URGENT else "ROUTINE"
                t_order = TestOrder(
                    consultation_id=consultation.id,
                    test_name=test,
                    priority=t_priority,
                    reason=req.confirmed_diagnosis,
                    facility_id=facility_id,
                    status="ORDERED"
                )
                db.add(t_order)

                # Persist canonical InvestigationOrder for Doctor Workspace & Citizen portal
                inv_ref = f"INV-{datetime.now(timezone.utc).year}-{uuid.uuid4().hex[:6].upper()}"
                now_utc = utc_now()
                inv_order = InvestigationOrder(
                    reference=inv_ref,
                    citizen_id=case.citizen_id,
                    case_id=case.id,
                    consultation_id=consultation.id,
                    ordered_by_doctor_id=doctor_user.id,
                    facility_id=facility_id,
                    test_name=test,
                    category="GENERAL",
                    priority=t_priority,
                    clinical_reason=req.confirmed_diagnosis or "Consultation order",
                    specimen_type="Blood / Urine",
                    preparation_instructions="Standard preparation",
                    collection_location="PHC Kalyanpur Sample Collection Counter",
                    ordered_at=now_utc,
                    due_at=now_utc + timedelta(days=1),
                    expected_result_at=now_utc + timedelta(days=2),
                    status="SAMPLE_PENDING"
                )
                db.add(inv_order)
                db.flush()
                db.add(InvestigationSample(
                    investigation_order_id=inv_order.id,
                    sample_reference=f"SMP-{inv_order.reference}",
                    collection_status="PENDING"
                ))

        # Create ASHA Follow-up Directive
        if req.asha_followup_directive or req.asha_followup_instructions or req.followup_due_days:
            directive = req.asha_followup_directive
            due_days = directive.due_days if directive else req.followup_due_days
            due_date = datetime.now(timezone.utc) + timedelta(days=due_days)
            
            instructions_text = directive.instructions if directive else (req.asha_followup_instructions or f"Check BP and adherence for {req.confirmed_diagnosis}")
            repeat_vitals = directive.measurements_to_repeat if directive else ["systolic_bp", "diastolic_bp", "pulse"]
            adherence_flag = directive.adherence_required if directive else True
            escalation_cond = directive.escalation_conditions if directive else "Report immediately if symptoms worsen or SBP >= 160."

            followup = FollowUp(
                case_id=case.id,
                citizen_id=case.citizen_id,
                created_by_id=doctor_user.id,
                created_by_role="PHC_DOCTOR",
                source="DOCTOR_ASSIGNED",
                task_type="POST_CONSULTATION_VITALS_CHECK",
                reason=f"Doctor directive for {req.confirmed_diagnosis}",
                assigned_role=UserRoleEnum.ASHA_WORKER,
                assigned_user_id=case.assigned_asha_id,
                instructions=instructions_text,
                measurements_to_repeat=repeat_vitals,
                adherence_required=adherence_flag,
                escalation_conditions=escalation_cond,
                priority=CasePriorityEnum.HIGH if directive and directive.priority == "URGENT" else CasePriorityEnum.HIGH,
                due_at=due_date,
                status="PENDING",
                sync_status="SYNCED"
            )
            db.add(followup)

            # Notify ASHA of new follow-up directive
            if case.assigned_asha_id:
                notif = Notification(
                    recipient_user_id=case.assigned_asha_id,
                    case_id=case.id,
                    notification_type="FOLLOW_UP_ASSIGNED",
                    title=f"Doctor Directive Assigned: {case.reference}",
                    message=f"Dr. {doctor_user.name} assigned follow-up for {case.citizen.display_name if case.citizen else 'Citizen'}. Due in {due_days} days.",
                    priority=CasePriorityEnum.HIGH
                )
                db.add(notif)

        # Update Case State based on disposition
        if req.disposition == "HIGHER_REFERRAL" or req.disposition == "EMERGENCY_TRANSFER":
            new_status = CaseStatusEnum.REFERRED_TO_PHC
        elif req.asha_followup_directive or req.asha_followup_instructions:
            new_status = CaseStatusEnum.FOLLOW_UP_REQUIRED
        else:
            new_status = CaseStatusEnum.COMPLETED

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
            metadata_json={"diagnosis": req.confirmed_diagnosis, "disposition": req.disposition, "followup_due_days": req.followup_due_days}
        )
        db.add(audit)
        db.commit()
        db.refresh(consultation)
        return consultation
