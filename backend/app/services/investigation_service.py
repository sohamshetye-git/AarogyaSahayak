from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, and_, desc, asc
from fastapi import HTTPException, status

import json
from app.models import (
    InvestigationOrder, InvestigationSample, InvestigationResult,
    InvestigationResultItem, InvestigationReview, InvestigationAshaTask,
    User, CitizenProfile, Case, Referral, Consultation, FollowUp, AuditLog, utc_now
)
from app.schemas import (
    InvestigationOrderCreateInput, SampleCollectInput, ResultEntryInput,
    CriticalAcknowledgeInput, DoctorReviewInput, InvestigationSummaryDTO,
    DoctorInvestigationItemDTO, InvestigationSampleDTO, InvestigationResultDTO,
    ResultItemDTO, InvestigationReviewDTO, CitizenInvestigationInstructionDTO,
    AshaInvestigationTaskDTO, InvestigationDetailDTO, RecollectionRequestInput,
    TestDetailDTO, PatientDetailDTO, CaseDetailDTO, ConsultationDetailDTO, OrderDetailMetaDTO
)
from app.services.event_bus import publish_domain_event

def log_activity(db: Session, user_id: str = None, user_role: str = None, action: str = None, description: str = None, metadata: Any = None, **kwargs):
    try:
        actor = user_id or kwargs.get("actor_id") or "SYSTEM"
        act = action or "ACTION"
        role = user_role or "PHC_DOCTOR"
        res_type = "INVESTIGATION"
        res_id = (metadata.get("order_id") if isinstance(metadata, dict) else None) or "N/A"
        meta_dict = metadata if isinstance(metadata, dict) else {"description": str(metadata or description or "")}
        log = AuditLog(
            actor_user_id=actor,
            actor_role=role,
            action=act,
            resource_type=res_type,
            resource_id=res_id,
            outcome="SUCCESS",
            metadata_json=meta_dict
        )
        db.add(log)
    except Exception as e:
        print(f"Warning: Failed to create AuditLog: {e}")

VALID_TRANSITIONS = {
    "DRAFT": ["ORDERED", "CANCELLED"],
    "ORDERED": ["SAMPLE_PENDING", "SAMPLE_COLLECTED", "SAMPLE_REJECTED", "CANCELLED"],
    "SAMPLE_PENDING": ["SAMPLE_COLLECTED", "SAMPLE_REJECTED", "RECOLLECTION_REQUIRED", "CANCELLED"],
    "SAMPLE_COLLECTED": ["IN_PROCESS", "RESULT_AVAILABLE", "CRITICAL_RESULT", "SAMPLE_REJECTED", "RECOLLECTION_REQUIRED", "CANCELLED"],
    "SAMPLE_REJECTED": ["RECOLLECTION_REQUIRED", "SAMPLE_PENDING", "SAMPLE_COLLECTED", "CANCELLED"],
    "RECOLLECTION_REQUIRED": ["SAMPLE_PENDING", "SAMPLE_COLLECTED", "SAMPLE_REJECTED", "CANCELLED"],
    "IN_PROCESS": ["RESULT_AVAILABLE", "CRITICAL_RESULT", "CANCELLED"],
    "RESULT_AVAILABLE": ["CRITICAL_RESULT", "DOCTOR_ACKNOWLEDGED", "REVIEW_REQUIRED", "REVIEWED", "CLOSED", "CANCELLED"],
    "CRITICAL_RESULT": ["DOCTOR_ACKNOWLEDGED", "REVIEWED", "CLOSED", "CANCELLED"],
    "DOCTOR_ACKNOWLEDGED": ["REVIEW_REQUIRED", "REVIEWED", "CLOSED", "CANCELLED"],
    "REVIEW_REQUIRED": ["REVIEWED", "CLOSED", "CANCELLED"],
    "REVIEWED": ["CLOSED", "CANCELLED"],
    "CLOSED": [],
    "CANCELLED": []
}

def validate_transition(current_status: str, target_status: str):
    allowed = VALID_TRANSITIONS.get(current_status, [])
    if target_status not in allowed and target_status != current_status:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "INVALID_LIFECYCLE_TRANSITION",
                "message": f"Cannot transition investigation lifecycle from '{current_status}' to '{target_status}'."
            }
        )

def generate_order_reference(db: Session) -> str:
    count = db.query(func.count(InvestigationOrder.id)).scalar() or 0
    year = datetime.now(timezone.utc).year
    return f"INV-{year}-{(count + 1):04d}"

def to_doctor_investigation_dto(order: InvestigationOrder) -> DoctorInvestigationItemDTO:
    cit = order.citizen
    case = order.case
    cons = order.consultation
    doc = order.ordered_by_doctor

    sample_dto = None
    if order.sample:
        s = order.sample
        collector_name = s.collected_by.name if s.collected_by else None
        sample_dto = InvestigationSampleDTO(
            id=s.id,
            sample_reference=s.sample_reference,
            collected_by_name=collector_name,
            collected_at=s.collected_at.isoformat() if s.collected_at else None,
            collection_status=s.collection_status,
            rejection_reason=s.rejection_reason,
            recollection_required=s.recollection_required or False
        )

    res_dto = None
    is_abnormal = False
    result_preview = None
    if order.result:
        r = order.result
        items_dto = [
            ResultItemDTO(
                id=item.id,
                parameter_name=item.parameter_name,
                parameter_code=item.parameter_code,
                value=item.value,
                unit=item.unit,
                reference_low=item.reference_low,
                reference_high=item.reference_high,
                source_flag=item.source_flag,
                remarks=item.remarks
            )
            for item in r.items
        ]
        
        entered_by = r.entered_by.name if r.entered_by else None
        res_dto = InvestigationResultDTO(
            id=r.id,
            result_source=r.result_source,
            laboratory_name=r.laboratory_name,
            resulted_at=r.resulted_at.isoformat() if r.resulted_at else utc_now().isoformat(),
            entered_by_name=entered_by,
            verification_status=r.verification_status,
            critical_flag=r.critical_flag,
            report_attachment_id=r.report_attachment_id,
            items=items_dto
        )

        flags = [i.source_flag for i in r.items]
        if "CRITICAL" in flags or r.critical_flag:
            is_abnormal = True
        elif "HIGH" in flags or "LOW" in flags:
            is_abnormal = True

        if items_dto:
            preview_parts = [f"{i.parameter_name}: {i.value} {i.unit or ''}".strip() for i in items_dto[:2]]
            result_preview = f"{', '.join(preview_parts)} ({r.result_source})"
        else:
            result_preview = f"Result Available ({r.result_source})"

    rev_dto = None
    if order.result and order.result.review:
        rv = order.result.review
        doctor_name = rv.doctor.name if rv.doctor else None
        rev_dto = InvestigationReviewDTO(
            id=rv.id,
            doctor_id=rv.doctor_id,
            doctor_name=doctor_name,
            review_note=rv.review_note,
            outcome=rv.outcome,
            reviewed_at=rv.reviewed_at.isoformat() if rv.reviewed_at else utc_now().isoformat(),
            critical_acknowledged_at=rv.critical_acknowledged_at.isoformat() if rv.critical_acknowledged_at else None,
            care_plan_updated=rv.care_plan_updated or False,
            related_follow_up_id=rv.related_follow_up_id,
            related_higher_referral_id=rv.related_higher_referral_id
        )

    assigned_asha_name = None
    if cit:
        asha_obj = getattr(cit, "assigned_asha", None)
        if asha_obj and hasattr(asha_obj, "name"):
            assigned_asha_name = asha_obj.name
        elif getattr(cit, "assigned_asha_id", None):
            assigned_asha_name = "Sita ASHA"

    clinical_ctx = "General"
    if cit:
        if cit.is_pregnant:
            clinical_ctx = "Maternal Health"
        elif cit.age_estimate and cit.age_estimate <= 5:
            clinical_ctx = "Child Health (Under 5)"
        elif cit.chronic_conditions:
            clinical_ctx = "NCD Health"

    age_val = 30
    gender_val = "Female"
    village_val = "Kalyanpur"
    if cit:
        if cit.age_estimate is not None:
            age_val = cit.age_estimate
        if cit.sex:
            gender_val = cit.sex
        if cit.village_name:
            village_val = cit.village_name

    cit_id = cit.id if cit else (order.citizen_id or "")
    case_id_val = case.id if case else (order.case_id or (cons.case_id if cons else ""))
    case_ref_val = case.reference if case else (cons.case.reference if cons and getattr(cons, "case", None) else "")
    cons_id_val = cons.id if cons else (order.consultation_id or None)
    cons_ref_val = cons.reference if cons else None

    return DoctorInvestigationItemDTO(
        id=order.id,
        reference=order.reference,
        investigation_id=order.id,
        investigation_order_id=order.id,
        investigation_reference=order.reference,
        citizen_id=cit_id,
        patient_id=cit_id,
        citizen_name=cit.display_name if cit else "Citizen",
        citizen_age=age_val,
        citizen_gender=gender_val,
        village_name=village_val,
        clinical_context=clinical_ctx,
        case_id=case_id_val,
        case_reference=case_ref_val,
        consultation_id=cons_id_val,
        consultation_reference=cons_ref_val,
        referral_id=order.referral_id,
        ordering_doctor_name=doc.name if doc else "Dr. Abhinav Sharma",
        test_name=order.test_name,
        test_code=order.test_code,
        category=order.category or "Other",
        priority=order.priority or "ROUTINE",
        status=order.status,
        clinical_reason=order.clinical_reason or "Not recorded",
        specimen_type=order.specimen_type or "Not recorded",
        preparation_instructions=order.preparation_instructions or "Not recorded",
        collection_location=order.collection_location or "PHC Kalyanpur",
        ordered_at=order.ordered_at.isoformat() if order.ordered_at else utc_now().isoformat(),
        due_at=order.due_at.isoformat() if order.due_at else None,
        expected_result_at=order.expected_result_at.isoformat() if order.expected_result_at else None,
        assigned_asha_name=assigned_asha_name,
        sample_id=order.sample.id if order.sample else None,
        result_id=order.result.id if order.result else None,
        sample=sample_dto,
        result=res_dto,
        review=rev_dto,
        is_abnormal=is_abnormal,
        result_preview=result_preview
    )

def to_investigation_detail_dto(order: InvestigationOrder) -> InvestigationDetailDTO:
    from app.schemas import (
        InvestigationDetailDTO, TestDetailDTO, PatientDetailDTO, CaseDetailDTO,
        ConsultationDetailDTO, OrderDetailMetaDTO
    )
    dto_item = to_doctor_investigation_dto(order)
    return InvestigationDetailDTO(
        investigation_id=order.id,
        investigation_reference=order.reference,
        id=order.id,
        reference=order.reference,
        status=order.status,
        priority=order.priority or "ROUTINE",
        test=TestDetailDTO(
            name=order.test_name,
            code=order.test_code,
            category=order.category or "Other"
        ),
        patient=PatientDetailDTO(
            citizen_id=dto_item.citizen_id,
            name=dto_item.citizen_name,
            age=dto_item.citizen_age,
            gender=dto_item.citizen_gender,
            village=dto_item.village_name
        ),
        case=CaseDetailDTO(
            case_id=dto_item.case_id,
            reference=dto_item.case_reference or "N/A"
        ),
        consultation=ConsultationDetailDTO(
            consultation_id=dto_item.consultation_id,
            reference=dto_item.consultation_reference
        ) if dto_item.consultation_id else None,
        order=OrderDetailMetaDTO(
            clinical_reason=order.clinical_reason or "Not recorded",
            specimen_type=order.specimen_type or "Not recorded",
            preparation_instructions=order.preparation_instructions or "Not recorded",
            collection_location=order.collection_location or "PHC Kalyanpur",
            ordered_by=dto_item.ordering_doctor_name or "Dr. Abhinav Sharma",
            ordered_at=dto_item.ordered_at,
            due_at=dto_item.due_at,
            expected_result_at=dto_item.expected_result_at
        ),
        sample=dto_item.sample,
        result=dto_item.result,
        review=dto_item.review,
        citizen_id=dto_item.citizen_id,
        case_id=dto_item.case_id,
        consultation_id=dto_item.consultation_id
    )

def create_investigation_order(
    db: Session,
    doctor_user: User,
    req: InvestigationOrderCreateInput
) -> InvestigationOrder:
    if req.idempotency_key:
        existing = db.query(InvestigationOrder).filter(InvestigationOrder.idempotency_key == req.idempotency_key).first()
        if existing:
            return existing

    # Duplicate check for identical active order on same patient & test name
    active_statuses = ["ORDERED", "SAMPLE_PENDING", "SAMPLE_COLLECTED", "IN_PROCESS", "RESULT_AVAILABLE", "CRITICAL_RESULT", "REVIEW_REQUIRED"]
    dup = db.query(InvestigationOrder).filter(
        InvestigationOrder.citizen_id == req.citizen_id,
        InvestigationOrder.test_name == req.test_name,
        InvestigationOrder.status.in_(active_statuses)
    ).first()

    if dup and not req.clinical_reason:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "DUPLICATE_ACTIVE_ORDER",
                "message": f"An active order for '{req.test_name}' already exists ({dup.reference}). Enter a distinct clinical reason to override."
            }
        )

    ref = generate_order_reference(db)
    now = utc_now()
    due_at = req.due_at or (now + timedelta(days=1))
    expected_result_at = req.expected_result_at or (now + timedelta(days=2))

    from app.models import WorkerProfile
    wp = db.query(WorkerProfile).filter(WorkerProfile.user_id == doctor_user.id).first()
    facility_id = wp.facility_id if wp and wp.facility_id else "FAC-PHC-09"

    order = InvestigationOrder(
        reference=ref,
        citizen_id=req.citizen_id,
        case_id=req.case_id,
        consultation_id=req.consultation_id,
        referral_id=req.referral_id,
        ordered_by_doctor_id=doctor_user.id,
        facility_id=facility_id,
        test_name=req.test_name,
        test_code=req.test_code,
        category=req.category or "GENERAL",
        priority=req.priority or "ROUTINE",
        clinical_reason=req.clinical_reason,
        specimen_type=req.specimen_type or "Blood / Urine",
        preparation_instructions=req.preparation_instructions or "Fasting or standard preparation as advised",
        collection_location=req.collection_location or "PHC Kalyanpur Sample Collection Counter",
        ordered_at=now,
        due_at=due_at,
        expected_result_at=expected_result_at,
        status="SAMPLE_PENDING",
        idempotency_key=req.idempotency_key
    )
    db.add(order)
    db.flush()

    # Initial sample tracking row
    sample = InvestigationSample(
        investigation_order_id=order.id,
        sample_reference=f"SMP-{order.reference}",
        collection_status="PENDING"
    )
    db.add(sample)

    # Optional ASHA assistance task
    if req.assign_asha_assistance:
        cit = db.query(CitizenProfile).filter(CitizenProfile.id == req.citizen_id).first()
        asha_id = cit.assigned_asha_id if cit else None
        if asha_id:
            asha_task = InvestigationAshaTask(
                investigation_order_id=order.id,
                asha_user_id=asha_id,
                citizen_id=req.citizen_id,
                task_type="ATTENDANCE_ASSISTANCE",
                due_date=due_at,
                instructions=req.asha_instructions or f"Assist patient {cit.display_name if cit else ''} to attend PHC for {req.test_name} sample collection.",
                status="PENDING"
            )
            db.add(asha_task)

    db.commit()
    db.refresh(order)

    log_activity(
        db,
        user_id=doctor_user.id,
        user_role="PHC_DOCTOR",
        action="INVESTIGATION_ORDERED",
        description=f"Ordered {order.test_name} ({order.reference}) for patient.",
        metadata={"order_id": order.id, "citizen_id": req.citizen_id, "case_id": req.case_id}
    )

    publish_domain_event(
        event_name="INVESTIGATION_ORDERED",
        payload={
            "investigation_id": order.id,
            "reference": order.reference,
            "citizen_id": req.citizen_id,
            "case_id": req.case_id,
            "test_name": order.test_name,
            "priority": order.priority
        },
        target_roles=["PHC_DOCTOR", "ASHA_WORKER", "CITIZEN"]
    )

    return order

def record_sample_collection(
    db: Session,
    user: User,
    order_id: str,
    input_data: SampleCollectInput
) -> InvestigationOrder:
    order = db.query(InvestigationOrder).filter(InvestigationOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail={"code": "INVESTIGATION_NOT_FOUND", "message": "Investigation not found"})

    now = utc_now()
    if input_data.rejection_reason:
        validate_transition(order.status, "SAMPLE_REJECTED")
        order.status = "SAMPLE_REJECTED"
        if not order.sample:
            order.sample = InvestigationSample(investigation_order_id=order.id)
        order.sample.collection_status = "REJECTED"
        order.sample.rejection_reason = input_data.rejection_reason
        order.sample.recollection_required = input_data.recollection_required
        if input_data.recollection_required:
            order.status = "RECOLLECTION_REQUIRED"
    else:
        validate_transition(order.status, "SAMPLE_COLLECTED")
        order.status = "SAMPLE_COLLECTED"
        if not order.sample:
            order.sample = InvestigationSample(investigation_order_id=order.id)
        order.sample.collection_status = "COLLECTED"
        order.sample.collected_at = input_data.collected_at or now
        order.sample.collected_by_user_id = user.id
        if input_data.sample_reference:
            order.sample.sample_reference = input_data.sample_reference
        if input_data.specimen_type:
            order.specimen_type = input_data.specimen_type

    db.commit()
    db.refresh(order)

    log_activity(
        db,
        user_id=user.id,
        user_role=user.role,
        action="SAMPLE_STATUS_UPDATED",
        description=f"Sample status updated for {order.reference}: {order.status}.",
        metadata={"order_id": order.id, "status": order.status}
    )

    publish_domain_event(
        event_name="SAMPLE_COLLECTED" if order.status == "SAMPLE_COLLECTED" else "SAMPLE_REJECTED",
        payload={"investigation_id": order.id, "status": order.status},
        target_roles=["PHC_DOCTOR", "ASHA_WORKER"]
    )

    return order

def enter_investigation_result(
    db: Session,
    user: User,
    order_id: str,
    input_data: ResultEntryInput
) -> InvestigationOrder:
    order = db.query(InvestigationOrder).filter(InvestigationOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail={"code": "INVESTIGATION_NOT_FOUND", "message": "Investigation not found"})

    now = utc_now()
    if not order.result:
        res = InvestigationResult(
            investigation_order_id=order.id,
            result_source=input_data.result_source or "PHC Manual/Demonstration Entry",
            laboratory_name=input_data.laboratory_name or "PHC Kalyanpur Central Lab",
            resulted_at=input_data.resulted_at or now,
            entered_by_user_id=user.id,
            verified_by_user_id=user.id,
            verification_status="VERIFIED",
            report_attachment_id=input_data.report_attachment_id,
            critical_flag=input_data.critical_flag
        )
        db.add(res)
        db.flush()
    else:
        res = order.result
        res.result_source = input_data.result_source
        res.laboratory_name = input_data.laboratory_name
        res.resulted_at = input_data.resulted_at or now
        res.critical_flag = input_data.critical_flag

    # Add items
    db.query(InvestigationResultItem).filter(InvestigationResultItem.result_id == res.id).delete()
    has_critical = input_data.critical_flag
    for item_in in input_data.items:
        if item_in.source_flag == "CRITICAL":
            has_critical = True
        ritem = InvestigationResultItem(
            result_id=res.id,
            parameter_name=item_in.parameter_name,
            parameter_code=item_in.parameter_code,
            value=item_in.value,
            unit=item_in.unit,
            reference_low=item_in.reference_low,
            reference_high=item_in.reference_high,
            source_flag=item_in.source_flag,
            remarks=item_in.remarks
        )
        db.add(ritem)

    res.critical_flag = has_critical

    if has_critical:
        validate_transition(order.status, "CRITICAL_RESULT")
        order.status = "CRITICAL_RESULT"
    else:
        validate_transition(order.status, "RESULT_AVAILABLE")
        order.status = "RESULT_AVAILABLE"

    db.commit()
    db.refresh(order)

    log_activity(
        db,
        user_id=user.id,
        user_role=user.role,
        action="INVESTIGATION_RESULT_ENTERED",
        description=f"Lab result entered for {order.reference} (Critical: {has_critical}).",
        metadata={"order_id": order.id, "critical": has_critical}
    )

    publish_domain_event(
        event_name="CRITICAL_RESULT" if has_critical else "RESULT_AVAILABLE",
        payload={"investigation_id": order.id, "critical": has_critical, "status": order.status},
        target_roles=["PHC_DOCTOR"]
    )

    return order

def acknowledge_critical_result(
    db: Session,
    doctor_user: User,
    order_id: str,
    input_data: CriticalAcknowledgeInput
) -> InvestigationOrder:
    order = db.query(InvestigationOrder).filter(InvestigationOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail={"code": "INVESTIGATION_NOT_FOUND", "message": "Investigation not found"})

    now = utc_now()
    validate_transition(order.status, "DOCTOR_ACKNOWLEDGED")
    order.status = "DOCTOR_ACKNOWLEDGED"

    if order.result:
        if not order.result.review:
            rev = InvestigationReview(
                result_id=order.result.id,
                doctor_id=doctor_user.id,
                review_note=f"[CRITICAL ACKNOWLEDGEMENT]: {input_data.notes or 'Acknowledged critical result.'}",
                outcome="DOCTOR_ACKNOWLEDGED",
                critical_acknowledged_at=now
            )
            db.add(rev)
        else:
            order.result.review.critical_acknowledged_at = now
            order.result.review.review_note += f"\n[CRITICAL ACKNOWLEDGEMENT]: {input_data.notes or 'Acknowledged critical result.'}"

    db.commit()
    db.refresh(order)

    log_activity(
        db,
        user_id=doctor_user.id,
        user_role="PHC_DOCTOR",
        action="CRITICAL_RESULT_ACKNOWLEDGED",
        description=f"Doctor acknowledged critical result for {order.reference}.",
        metadata={"order_id": order.id}
    )

    publish_domain_event(
        event_name="CRITICAL_RESULT_ACKNOWLEDGED",
        payload={"investigation_id": order.id, "doctor_id": doctor_user.id},
        target_roles=["PHC_DOCTOR"]
    )

    return order

def review_investigation_result_full(
    db: Session,
    doctor_user: User,
    order_id: str,
    input_data: DoctorReviewInput
) -> InvestigationOrder:
    order = db.query(InvestigationOrder).filter(InvestigationOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail={"code": "INVESTIGATION_NOT_FOUND", "message": "Investigation not found"})

    now = utc_now()
    validate_transition(order.status, "REVIEWED")

    if not order.result:
        # Create minimal result shell if none exists
        res = InvestigationResult(
            investigation_order_id=order.id,
            result_source="PHC Clinical Review",
            laboratory_name="PHC Kalyanpur Central Lab",
            resulted_at=now,
            entered_by_user_id=doctor_user.id
        )
        db.add(res)
        db.flush()
        order.result = res

    rel_follow_up_id = None
    if input_data.create_followup:
        fu = FollowUp(
            case_id=order.case_id,
            citizen_id=order.citizen_id,
            consultation_id=order.consultation_id,
            created_by_id=doctor_user.id,
            created_by_role="DOCTOR",
            source="DOCTOR_ASSIGNED",
            task_type="INVESTIGATION_REPEATED_MONITORING",
            reason=f"Follow-up for lab review outcome: {input_data.outcome}",
            instructions=input_data.followup_instructions or f"Perform follow-up vitals and monitor patient regarding {order.test_name} results.",
            priority="HIGH" if "EMERGENCY" in input_data.outcome else "FOLLOW_UP",
            due_at=now + timedelta(days=input_data.followup_due_days),
            status="PENDING"
        )
        db.add(fu)
        db.flush()
        rel_follow_up_id = fu.id

    rel_referral_id = None
    if input_data.create_referral:
        ref = Referral(
            case_id=order.case_id,
            citizen_id=order.citizen_id,
            referred_by_id=doctor_user.id,
            target_facility_id=input_data.referral_facility or "FAC-CHC-02",
            target_facility_name="District Specialist Hospital",
            urgency="URGENT" if "EMERGENCY" in input_data.outcome else "ROUTINE",
            reason=input_data.referral_reason or f"Higher-center referral based on {order.test_name} lab review outcome.",
            status="REFERRED"
        )
        db.add(ref)
        db.flush()
        rel_referral_id = ref.id

    if not order.result.review:
        rev = InvestigationReview(
            result_id=order.result.id,
            doctor_id=doctor_user.id,
            review_note=input_data.review_note,
            outcome=input_data.outcome,
            reviewed_at=now,
            care_plan_updated=input_data.update_care_plan,
            related_follow_up_id=rel_follow_up_id,
            related_higher_referral_id=rel_referral_id
        )
        db.add(rev)
    else:
        order.result.review.doctor_id = doctor_user.id
        order.result.review.review_note = input_data.review_note
        order.result.review.outcome = input_data.outcome
        order.result.review.reviewed_at = now
        order.result.review.care_plan_updated = input_data.update_care_plan
        if rel_follow_up_id:
            order.result.review.related_follow_up_id = rel_follow_up_id
        if rel_referral_id:
            order.result.review.related_higher_referral_id = rel_referral_id

    order.status = "REVIEWED"

    db.commit()
    db.refresh(order)

    log_activity(
        db,
        user_id=doctor_user.id,
        user_role="PHC_DOCTOR",
        action="RESULT_REVIEWED",
        description=f"Reviewed result for {order.reference} with outcome '{input_data.outcome}'.",
        metadata={"order_id": order.id, "outcome": input_data.outcome}
    )

    publish_domain_event(
        event_name="RESULT_REVIEWED",
        payload={
            "investigation_id": order.id,
            "outcome": input_data.outcome,
            "doctor_id": doctor_user.id
        },
        target_roles=["PHC_DOCTOR", "ASHA_WORKER", "CITIZEN"]
    )

    return order

def request_investigation_recollection(
    db: Session,
    user: User,
    order_id: str,
    input_data: RecollectionRequestInput
) -> InvestigationOrder:
    order = db.query(InvestigationOrder).filter(
        or_(InvestigationOrder.id == order_id, InvestigationOrder.reference == order_id)
    ).first()
    if not order:
        raise HTTPException(status_code=404, detail={"code": "INVESTIGATION_NOT_FOUND", "message": f"Investigation order '{order_id}' not found"})

    if order.status in ["CLOSED", "CANCELLED"]:
        raise HTTPException(status_code=409, detail={"code": "INVALID_LIFECYCLE_TRANSITION", "message": f"Cannot request recollection for investigation in state '{order.status}'"})

    if order.result and order.result.review and not order.result.critical_flag and order.status in ["REVIEWED", "CLOSED"]:
        flags = [i.source_flag for i in order.result.items]
        if "CRITICAL" not in flags and "HIGH" not in flags and "LOW" not in flags:
            raise HTTPException(status_code=409, detail={"code": "NORMAL_RESULT_RECOLLECTION_PROHIBITED", "message": "Normal verified result cannot be sent for sample recollection. Create a Repeat Test order instead if clinically indicated."})

    validate_transition(order.status, "RECOLLECTION_REQUIRED")
    order.status = "RECOLLECTION_REQUIRED"

    if not order.sample:
        order.sample = InvestigationSample(investigation_order_id=order.id)

    order.sample.collection_status = "REJECTED"
    order.sample.rejection_reason = f"[{input_data.reason_code}] {input_data.reason_note}"
    order.sample.recollection_required = True

    now = utc_now()
    due_at = utc_now() + timedelta(days=1)
    if input_data.due_at:
        try:
            due_at = datetime.fromisoformat(input_data.due_at.replace("Z", "+00:00"))
        except Exception:
            pass

    if input_data.assign_asha_assistance:
        cit = db.query(CitizenProfile).filter(CitizenProfile.id == order.citizen_id).first()
        asha_id = (cit.assigned_asha_id if cit else None) or "USR-ASHA-001"
        task = db.query(InvestigationAshaTask).filter(
            InvestigationAshaTask.investigation_order_id == order.id,
            InvestigationAshaTask.status == "PENDING"
        ).first()
        if not task:
            task = InvestigationAshaTask(
                investigation_order_id=order.id,
                asha_user_id=asha_id,
                citizen_id=order.citizen_id,
                task_type="ATTENDANCE_ASSISTANCE",
                due_date=due_at,
                instructions=f"Sample recollection required ({input_data.reason_code}): {input_data.reason_note}. Please guide patient to {input_data.collection_location or 'PHC Kalyanpur'}.",
                status="PENDING"
            )
            db.add(task)

    db.commit()
    db.refresh(order)

    log_activity(
        db,
        user_id=user.id,
        user_role=user.role,
        action="RECOLLECTION_REQUESTED",
        description=f"Recollection requested for {order.reference}: {input_data.reason_note}.",
        metadata={"order_id": order.id, "reason_code": input_data.reason_code}
    )

    publish_domain_event(
        event_name="RECOLLECTION_REQUESTED",
        payload={"investigation_id": order.id, "status": order.status},
        target_roles=["PHC_DOCTOR", "ASHA_WORKER", "CITIZEN"]
    )

    return order

def cancel_investigation_order(db: Session, user: User, order_id: str, reason: str) -> InvestigationOrder:
    order = db.query(InvestigationOrder).filter(InvestigationOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail={"code": "INVESTIGATION_NOT_FOUND", "message": "Investigation not found"})

    validate_transition(order.status, "CANCELLED")
    order.status = "CANCELLED"
    order.clinical_reason = (order.clinical_reason or "") + f" [Cancelled: {reason}]"

    db.commit()
    db.refresh(order)

    log_activity(
        db, user_id=user.id, user_role=user.role, action="INVESTIGATION_CANCELLED",
        description=f"Cancelled investigation order {order.reference}.", metadata={"order_id": order.id}
    )

    return order

def get_investigations_summary(db: Session, doctor_user: User) -> InvestigationSummaryDTO:
    orders = db.query(InvestigationOrder).all()
    today_str = utc_now().date().isoformat()

    summary = InvestigationSummaryDTO()
    for o in orders:
        if o.ordered_at and o.ordered_at.date().isoformat() == today_str:
            summary.total_ordered_today += 1

        st = o.status
        if st in ["ORDERED", "SAMPLE_PENDING"]:
            summary.sample_pending += 1
        elif st in ["SAMPLE_COLLECTED", "IN_PROCESS"]:
            summary.sample_collected += 1
        elif st in ["RESULT_AVAILABLE", "CRITICAL_RESULT", "REVIEW_REQUIRED"]:
            summary.results_ready += 1
            summary.awaiting_doctor_review += 1
            if st == "CRITICAL_RESULT" or (o.result and o.result.critical_flag):
                summary.urgent_critical_results += 1
        elif st == "RECOLLECTION_REQUIRED" or st == "SAMPLE_REJECTED":
            summary.recollection_required += 1
        elif st == "REVIEWED" or st == "CLOSED":
            if o.result and o.result.review and o.result.review.reviewed_at and o.result.review.reviewed_at.date().isoformat() == today_str:
                summary.reviewed_today += 1

    return summary
