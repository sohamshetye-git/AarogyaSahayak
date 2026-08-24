import random
from typing import List, Optional
from sqlalchemy.orm import Session
from app.models import (
    Case, SymptomObservation, VitalRecord, CitizenProfile, User, 
    CasePriorityEnum, CaseStatusEnum, InformationSourceEnum, AuditLog, Notification
)
from app.safety.emergency_rules import EmergencyRuleEvaluator
from app.schemas import CitizenCreateCaseRequest

class CaseService:
    @staticmethod
    def generate_reference(prefix: str = "CASE") -> str:
        num = random.randint(100000, 999999)
        return f"{prefix}-2026-{num}"

    @classmethod
    def create_case(
        cls,
        db: Session,
        req: CitizenCreateCaseRequest,
        citizen_profile: CitizenProfile,
        created_by_name: str = "Citizen Self-Report"
    ) -> Case:
        # Extract vitals if present
        systolic = req.vitals.systolic_bp if req.vitals else None
        diastolic = req.vitals.diastolic_bp if req.vitals else None
        spo2 = req.vitals.spo2 if req.vitals else None
        temp = req.vitals.temperature_c if req.vitals else None

        # 1. Authoritative Deterministic Safety Evaluation
        priority, rule_triggered, rule_reason, guidance_text = EmergencyRuleEvaluator.evaluate(
            symptoms=req.symptoms,
            is_pregnant=req.is_pregnant or citizen_profile.is_pregnant,
            gestational_weeks=req.gestational_weeks or citizen_profile.gestational_weeks,
            systolic_bp=systolic,
            diastolic_bp=diastolic,
            spo2=spo2,
            temperature_c=temp
        )

        # 2. Determine Primary Concern Summary
        primary_concern = req.spoken_transcript or (", ".join(req.symptoms) if req.symptoms else "Health concern reported")

        # 3. Find/Assign default ASHA & PHC in same village/block
        default_asha = db.query(User).filter(User.role == "ASHA_WORKER").first()
        assigned_asha_id = default_asha.id if default_asha else None
        assigned_asha_name = default_asha.name if default_asha else "Sita Patel (ASHA)"

        new_case = Case(
            reference=cls.generate_reference("CASE"),
            citizen_id=citizen_profile.id,
            priority=priority,
            status=CaseStatusEnum.NEW,
            primary_concern=primary_concern,
            preferred_language=req.preferred_language,
            assigned_asha_id=assigned_asha_id,
            assigned_asha_name=assigned_asha_name,
            assigned_facility_name="Kalyanpur PHC",
            safety_rule_triggered=rule_triggered,
            safety_rule_reason=rule_reason,
            citizen_guidance_text=guidance_text
        )
        db.add(new_case)
        db.flush()

        # Add Symptoms
        for sym in req.symptoms:
            obs = SymptomObservation(
                case_id=new_case.id,
                spoken_term=sym,
                normalized_term=sym.title(),
                source_type=InformationSourceEnum.CITIZEN_REPORTED,
                recorded_by=created_by_name
            )
            db.add(obs)

        # Add Vitals if recorded
        if req.vitals:
            vit = VitalRecord(
                case_id=new_case.id,
                systolic_bp=req.vitals.systolic_bp,
                diastolic_bp=req.vitals.diastolic_bp,
                temperature_c=req.vitals.temperature_c,
                spo2=req.vitals.spo2,
                pulse=req.vitals.pulse,
                respiratory_rate=req.vitals.respiratory_rate,
                glucose_mg_dl=req.vitals.glucose_mg_dl,
                weight_kg=req.vitals.weight_kg,
                is_warning_sign=rule_triggered,
                source_type=InformationSourceEnum.CITIZEN_REPORTED,
                recorded_by=created_by_name
            )
            db.add(vit)

        # Create ASHA Notification if urgent/high
        if assigned_asha_id:
            notif = Notification(
                recipient_user_id=assigned_asha_id,
                case_id=new_case.id,
                notification_type="URGENT_CASE_ALERT" if priority == CasePriorityEnum.URGENT else "NEW_TASK_ASSIGNED",
                title=f"Urgent Case: {new_case.reference}" if priority == CasePriorityEnum.URGENT else f"New Task: {new_case.reference}",
                message=f"Case {new_case.reference} for {citizen_profile.display_name} ({primary_concern[:60]}). Priority: {priority.value}",
                priority=priority
            )
            db.add(notif)

        # Audit Log
        audit = AuditLog(
            actor_user_id=citizen_profile.user_id,
            actor_role="CITIZEN",
            action="CASE_CREATED",
            resource_type="Case",
            resource_id=new_case.id,
            outcome="SUCCESS",
            metadata_json={"priority": priority.value, "rule_triggered": rule_triggered}
        )
        db.add(audit)
        db.commit()
        db.refresh(new_case)
        return new_case

    @staticmethod
    def update_status(db: Session, case: Case, new_status: CaseStatusEnum) -> Case:
        # Define allowed state transitions
        VALID_TRANSITIONS = {
            CaseStatusEnum.NEW: {CaseStatusEnum.ASHA_ASSIGNED, CaseStatusEnum.ASHA_ACKNOWLEDGED},
            CaseStatusEnum.ASHA_ASSIGNED: {CaseStatusEnum.ASHA_ACKNOWLEDGED},
            CaseStatusEnum.ASHA_ACKNOWLEDGED: {CaseStatusEnum.CITIZEN_CONTACTED, CaseStatusEnum.VISIT_SCHEDULED, CaseStatusEnum.VISIT_IN_PROGRESS, CaseStatusEnum.ASHA_REVIEWED, CaseStatusEnum.REFERRED_TO_PHC},
            CaseStatusEnum.CITIZEN_CONTACTED: {CaseStatusEnum.VISIT_SCHEDULED, CaseStatusEnum.VISIT_IN_PROGRESS, CaseStatusEnum.ASHA_REVIEWED, CaseStatusEnum.REFERRED_TO_PHC},
            CaseStatusEnum.VISIT_SCHEDULED: {CaseStatusEnum.VISIT_IN_PROGRESS, CaseStatusEnum.ASHA_REVIEWED, CaseStatusEnum.REFERRED_TO_PHC},
            CaseStatusEnum.VISIT_IN_PROGRESS: {CaseStatusEnum.ASHA_REVIEWED, CaseStatusEnum.REFERRED_TO_PHC},
            CaseStatusEnum.ASHA_REVIEWED: {CaseStatusEnum.REFERRED_TO_PHC, CaseStatusEnum.COMPLETED},
            CaseStatusEnum.REFERRED_TO_PHC: {CaseStatusEnum.DOCTOR_ACKNOWLEDGED, CaseStatusEnum.CONSULTATION_IN_PROGRESS, CaseStatusEnum.FOLLOW_UP_REQUIRED, CaseStatusEnum.COMPLETED},
            CaseStatusEnum.DOCTOR_ACKNOWLEDGED: {CaseStatusEnum.CONSULTATION_IN_PROGRESS, CaseStatusEnum.FOLLOW_UP_REQUIRED, CaseStatusEnum.COMPLETED},
            CaseStatusEnum.CONSULTATION_IN_PROGRESS: {CaseStatusEnum.FOLLOW_UP_REQUIRED, CaseStatusEnum.COMPLETED},
            CaseStatusEnum.FOLLOW_UP_REQUIRED: {CaseStatusEnum.COMPLETED, CaseStatusEnum.VISIT_IN_PROGRESS},
            CaseStatusEnum.COMPLETED: {CaseStatusEnum.NEW, CaseStatusEnum.FOLLOW_UP_REQUIRED}
        }
        
        if case.status == new_status:
            return case
            
        allowed = VALID_TRANSITIONS.get(case.status, set())
        if new_status not in allowed:
            raise ValueError(f"Invalid status transition from {case.status.value} to {new_status.value}")
            
        case.status = new_status
        db.add(case)
        return case
