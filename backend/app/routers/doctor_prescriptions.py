from datetime import datetime, timezone, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Header, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, desc, func

from app.database import get_db
from app.dependencies import get_current_user, RoleChecker
from app.models import (
    User, UserRoleEnum, Prescription, PrescriptionItem, MedicineCatalog,
    PrescriptionSafetyCheck, PrescriptionAmendment, PrescriptionAcknowledgement,
    CitizenProfile, Case, Consultation, Referral, FollowUp, utc_now
)
from app.schemas import StandardResponse
from app.schemas.prescription import (
    PrescriptionCreateDraft, PrescriptionUpdateDraft, PrescriptionSignRequest,
    PrescriptionAmendRequest, StopMedicineRequest, PrescriptionCancelRequest,
    PrescriptionFollowUpAssignRequest, PrescriptionDetailResponse,
    PrescriptionItemResponse, PrescriptionSafetyCheckResponse,
    PrescriptionSummaryResponse, MedicineCatalogResponse
)
from app.services.prescription_service import (
    generate_prescription_reference, validate_status_transition,
    run_deterministic_safety_checks, log_prescription_audit_event
)

router = APIRouter(prefix="/doctor", tags=["Doctor Prescriptions"])
doctor_only = RoleChecker([UserRoleEnum.PHC_DOCTOR])


def build_prescription_detail_dict(db: Session, p: Prescription) -> dict:
    citizen = db.query(CitizenProfile).filter(CitizenProfile.id == p.citizen_id).first()
    case = db.query(Case).filter(Case.id == p.case_id).first()
    cons = db.query(Consultation).filter(Consultation.id == p.consultation_id).first()
    doc = db.query(User).filter(User.id == p.prescriber_doctor_id).first()

    patient_category = "General"
    if citizen:
        if citizen.is_pregnant:
            patient_category = "Maternal"
        elif citizen.age_estimate and citizen.age_estimate <= 12:
            patient_category = "Pediatric"
        elif citizen.age_estimate and citizen.age_estimate >= 60:
            patient_category = "Elderly"
        elif citizen.chronic_conditions and len(citizen.chronic_conditions) > 0:
            patient_category = "NCD Chronic"

    for it in p.items:
        if not it.generic_name_snapshot and getattr(it, "medicine", None):
            it.generic_name_snapshot = getattr(it, "medicine")
        if not it.generic_name_snapshot:
            it.generic_name_snapshot = "Unspecified Medicine"

    items_dto = [PrescriptionItemResponse.from_orm(it) for it in p.items]
    checks_dto = [PrescriptionSafetyCheckResponse.from_orm(sc) for sc in p.safety_checks]

    return {
        "id": p.id,
        "reference": p.reference,
        "citizen_id": p.citizen_id,
        "case_id": p.case_id,
        "referral_id": p.referral_id,
        "consultation_id": p.consultation_id,
        "prescriber_doctor_id": p.prescriber_doctor_id,
        "facility_id": p.facility_id,
        "status": p.status,
        "version_number": p.version_number,
        "supersedes_prescription_id": p.supersedes_prescription_id,
        "clinical_context": p.clinical_context,
        "patient_language": p.patient_language,
        "signed_at": p.signed_at,
        "completed_at": p.completed_at,
        "cancelled_at": p.cancelled_at,
        "cancellation_reason": p.cancellation_reason,
        "idempotency_key": p.idempotency_key,
        "created_at": p.created_at,
        "updated_at": p.updated_at,

        "patient_name": citizen.display_name if citizen else "Unknown Patient",
        "patient_age": citizen.age_estimate if citizen else None,
        "patient_gender": citizen.sex if citizen else None,
        "patient_village": citizen.village_name if citizen else "Kalyanpur",
        "patient_category": patient_category,
        "case_reference": case.reference if case else None,
        "consultation_reference": cons.reference if cons else None,
        "prescriber_doctor_name": doc.name if doc else "Dr. Abhinav Sharma",

        "items": [it.dict() for it in items_dto],
        "safety_checks": [sc.dict() for sc in checks_dto],
    }


@router.get("/prescriptions/summary", response_model=StandardResponse)
def get_doctor_prescription_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(doctor_only)
):
    now = utc_now()
    today_start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
    soon_threshold = now + timedelta(days=2)

    drafts_count = db.query(Prescription).filter(Prescription.status == "DRAFT").count()
    awaiting_sig_count = db.query(Prescription).filter(Prescription.status == "READY_FOR_REVIEW").count()
    signed_today_count = db.query(Prescription).filter(
        Prescription.status.in_(["SIGNED", "ACTIVE"]),
        Prescription.signed_at >= today_start
    ).count()
    active_count = db.query(Prescription).filter(Prescription.status.in_(["SIGNED", "ACTIVE"])).count()
    
    # Ending soon query
    ending_soon_count = db.query(PrescriptionItem).filter(
        PrescriptionItem.status == "ACTIVE",
        PrescriptionItem.end_date != None,
        PrescriptionItem.end_date <= soon_threshold,
        PrescriptionItem.end_date >= now
    ).count()

    adherence_req_count = db.query(FollowUp).filter(
        FollowUp.prescription_id != None,
        FollowUp.status.in_(["PENDING", "IN_PROGRESS"])
    ).count()

    amended_count = db.query(Prescription).filter(Prescription.status == "AMENDED").count()
    stopped_cancelled_count = db.query(Prescription).filter(Prescription.status.in_(["STOPPED", "CANCELLED", "VOIDED", "PARTIALLY_STOPPED"])).count()

    summary_data = {
        "drafts_count": drafts_count,
        "awaiting_signature_count": awaiting_sig_count,
        "signed_today_count": signed_today_count,
        "active_count": active_count,
        "ending_soon_count": ending_soon_count,
        "adherence_followup_required_count": adherence_req_count,
        "amended_count": amended_count,
        "stopped_cancelled_count": stopped_cancelled_count,
        "phc_name": "Kalyanpur Primary Health Centre",
        "last_synchronized_at": now.isoformat()
    }
    return StandardResponse(data=summary_data)


@router.get("/prescriptions", response_model=StandardResponse)
def get_doctor_prescriptions(
    status: Optional[str] = None,
    search: Optional[str] = None,
    sort_by: Optional[str] = "newest",
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(doctor_only)
):
    query = db.query(Prescription).join(CitizenProfile, Prescription.citizen_id == CitizenProfile.id)

    if status and status.upper() != "ALL":
        st = status.upper()
        if st == "ENDING_SOON":
            now = utc_now()
            soon_thresh = now + timedelta(days=2)
            query = query.join(PrescriptionItem).filter(
                PrescriptionItem.status == "ACTIVE",
                PrescriptionItem.end_date <= soon_thresh,
                PrescriptionItem.end_date >= now
            )
        elif st in ["DRAFT", "READY_FOR_REVIEW", "SIGNED", "ACTIVE", "COMPLETED", "AMENDED", "PARTIALLY_STOPPED", "STOPPED", "CANCELLED", "VOIDED"]:
            query = query.filter(Prescription.status == st)

    if search and search.strip():
        term = f"%{search.strip()}%"
        query = query.outerjoin(Case, Prescription.case_id == Case.id)\
                     .outerjoin(Consultation, Prescription.consultation_id == Consultation.id)\
                     .outerjoin(PrescriptionItem, Prescription.id == PrescriptionItem.prescription_id)\
                     .filter(
                         or_(
                             CitizenProfile.display_name.ilike(term),
                             Prescription.reference.ilike(term),
                             Case.reference.ilike(term),
                             Consultation.reference.ilike(term),
                             PrescriptionItem.generic_name_snapshot.ilike(term),
                             PrescriptionItem.brand_name_snapshot.ilike(term),
                             CitizenProfile.village_name.ilike(term)
                         )
                     ).distinct()

    if sort_by == "oldest":
        query = query.order_by(Prescription.created_at.asc())
    elif sort_by == "patient":
        query = query.order_by(CitizenProfile.display_name.asc())
    else:  # newest
        query = query.order_by(Prescription.created_at.desc())

    total = query.count()
    prescriptions = query.offset(offset).limit(limit).all()

    results = [build_prescription_detail_dict(db, p) for p in prescriptions]
    return StandardResponse(data=results, meta={"total": total, "limit": limit, "offset": offset})


@router.get("/medicine-catalog", response_model=StandardResponse)
def get_medicine_catalog(
    search: Optional[str] = None,
    category: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(MedicineCatalog).filter(MedicineCatalog.active == True)
    if search:
        term = f"%{search.strip()}%"
        query = query.filter(
            or_(
                MedicineCatalog.generic_name.ilike(term),
                MedicineCatalog.brand_name.ilike(term)
            )
        )
    if category:
        query = query.filter(MedicineCatalog.medicine_category == category)

    medicines = query.order_by(MedicineCatalog.generic_name.asc()).all()
    results = [MedicineCatalogResponse.from_orm(m).dict() for m in medicines]
    return StandardResponse(data=results)


@router.get("/prescriptions/{prescription_id}", response_model=StandardResponse)
def get_doctor_prescription_detail(
    prescription_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(doctor_only)
):
    p = db.query(Prescription).filter(Prescription.id == prescription_id).first()
    if not p:
        raise HTTPException(status_code=404, detail={"code": "PRESCRIPTION_NOT_FOUND", "message": "Prescription record not found."})
    
    log_prescription_audit_event(db, p.id, "VIEW", current_user.id, current_user.role.value)
    return StandardResponse(data=build_prescription_detail_dict(db, p))


@router.get("/consultations/{consultation_id}/prescriptions", response_model=StandardResponse)
def get_doctor_consultation_prescriptions(
    consultation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(doctor_only)
):
    rxs = db.query(Prescription).filter(Prescription.consultation_id == consultation_id).order_by(Prescription.created_at.desc()).all()
    results = [build_prescription_detail_dict(db, p) for p in rxs]
    return StandardResponse(data=results)


@router.post("/prescriptions/draft", response_model=StandardResponse)
def create_prescription_draft(
    payload: PrescriptionCreateDraft,
    db: Session = Depends(get_db),
    current_user: User = Depends(doctor_only)
):
    # Verify clinical encounter
    cons = db.query(Consultation).filter(Consultation.id == payload.consultation_id).first()
    if not cons:
        raise HTTPException(status_code=404, detail={"code": "CONSULTATION_NOT_FOUND", "message": "Active clinical consultation required."})
    
    ref = generate_prescription_reference()
    now = utc_now()

    p = Prescription(
        reference=ref,
        citizen_id=payload.citizen_id,
        case_id=payload.case_id,
        referral_id=payload.referral_id,
        consultation_id=payload.consultation_id,
        prescriber_doctor_id=current_user.id,
        doctor_id=current_user.id,
        facility_id=payload.facility_id or "PHC-KALYANPUR",
        status="DRAFT",
        version_number=1,
        clinical_context=payload.clinical_context,
        patient_language=payload.patient_language,
        created_at=now,
        updated_at=now
    )
    db.add(p)
    db.flush()

    for item in payload.items:
        it = PrescriptionItem(
            prescription_id=p.id,
            medicine_catalog_id=item.medicine_catalog_id,
            generic_name_snapshot=item.generic_name_snapshot,
            medicine=item.generic_name_snapshot,
            brand_name_snapshot=item.brand_name_snapshot,
            formulation=item.formulation,
            strength=item.strength,
            dose=item.dose,
            dose_unit=item.dose_unit,
            route=item.route,
            frequency=item.frequency,
            timing=item.timing,
            duration_value=item.duration_value,
            duration_unit=item.duration_unit,
            quantity=item.quantity,
            instructions=item.instructions,
            indication=item.indication,
            as_needed=item.as_needed,
            max_frequency=item.max_frequency,
            adherence_monitoring_required=item.adherence_monitoring_required,
            status="ACTIVE",
            created_at=now,
            updated_at=now
        )
        db.add(it)

    db.commit()
    db.refresh(p)

    run_deterministic_safety_checks(db, p)
    log_prescription_audit_event(db, p.id, "DRAFT_CREATED", current_user.id, current_user.role.value)

    return StandardResponse(data=build_prescription_detail_dict(db, p))


@router.put("/prescriptions/{prescription_id}/draft", response_model=StandardResponse)
def update_prescription_draft(
    prescription_id: str,
    payload: PrescriptionUpdateDraft,
    db: Session = Depends(get_db),
    current_user: User = Depends(doctor_only)
):
    p = db.query(Prescription).filter(Prescription.id == prescription_id).first()
    if not p:
        raise HTTPException(status_code=404, detail={"code": "PRESCRIPTION_NOT_FOUND", "message": "Prescription not found."})

    if p.status not in ["DRAFT", "READY_FOR_REVIEW"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "IMMUTABLE_RECORD", "message": f"Prescription is in '{p.status}' state and cannot be modified as a draft."}
        )

    now = utc_now()
    if payload.clinical_context is not None:
        p.clinical_context = payload.clinical_context
    if payload.patient_language is not None:
        p.patient_language = payload.patient_language

    p.updated_at = now

    # Replace items
    db.query(PrescriptionItem).filter(PrescriptionItem.prescription_id == p.id).delete()
    for item in payload.items:
        it = PrescriptionItem(
            prescription_id=p.id,
            medicine_catalog_id=item.medicine_catalog_id,
            generic_name_snapshot=item.generic_name_snapshot,
            medicine=item.generic_name_snapshot,
            brand_name_snapshot=item.brand_name_snapshot,
            formulation=item.formulation,
            strength=item.strength,
            dose=item.dose,
            dose_unit=item.dose_unit,
            route=item.route,
            frequency=item.frequency,
            timing=item.timing,
            duration_value=item.duration_value,
            duration_unit=item.duration_unit,
            quantity=item.quantity,
            instructions=item.instructions,
            indication=item.indication,
            as_needed=item.as_needed,
            max_frequency=item.max_frequency,
            adherence_monitoring_required=item.adherence_monitoring_required,
            status="ACTIVE",
            created_at=now,
            updated_at=now
        )
        db.add(it)

    db.commit()
    db.refresh(p)

    run_deterministic_safety_checks(db, p)
    log_prescription_audit_event(db, p.id, "DRAFT_UPDATED", current_user.id, current_user.role.value)

    return StandardResponse(data=build_prescription_detail_dict(db, p))


@router.post("/prescriptions/{prescription_id}/validate", response_model=StandardResponse)
def validate_prescription_safety(
    prescription_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(doctor_only)
):
    p = db.query(Prescription).filter(Prescription.id == prescription_id).first()
    if not p:
        raise HTTPException(status_code=404, detail={"code": "PRESCRIPTION_NOT_FOUND", "message": "Prescription not found."})

    checks = run_deterministic_safety_checks(db, p)
    log_prescription_audit_event(db, p.id, "SAFETY_VALIDATED", current_user.id, current_user.role.value)

    return StandardResponse(data={"checks": checks, "prescription_id": p.id})


@router.post("/prescriptions/{prescription_id}/sign", response_model=StandardResponse)
def sign_prescription(
    prescription_id: str,
    payload: PrescriptionSignRequest,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
    current_user: User = Depends(doctor_only)
):
    p = db.query(Prescription).filter(Prescription.id == prescription_id).first()
    if not p:
        raise HTTPException(status_code=404, detail={"code": "PRESCRIPTION_NOT_FOUND", "message": "Prescription not found."})

    # Idempotency check: if already signed with same idempotency key or already SIGNED/ACTIVE
    if p.status in ["SIGNED", "ACTIVE"]:
        return StandardResponse(data=build_prescription_detail_dict(db, p))

    if idempotency_key:
        existing = db.query(Prescription).filter(Prescription.idempotency_key == idempotency_key).first()
        if existing and existing.status in ["SIGNED", "ACTIVE"]:
            return StandardResponse(data=build_prescription_detail_dict(db, existing))

    validate_status_transition(p.status, "SIGNED")

    checks = run_deterministic_safety_checks(db, p)
    blocking = [c for c in checks if c["severity"] == "BLOCKING_ERROR"]
    if blocking:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "BLOCKING_SAFETY_ERROR", "message": "Blocking safety errors must be resolved before signing.", "blocking": blocking}
        )

    now = utc_now()
    p.status = "SIGNED"
    p.signed_at = now
    p.updated_at = now
    if idempotency_key:
        p.idempotency_key = idempotency_key

    # Update item start and end dates
    for item in p.items:
        item.start_date = now
        item.end_date = now + timedelta(days=item.duration_value or 5)
        item.updated_at = now

    # Mark safety checks confirmed
    for sc in p.safety_checks:
        if sc.requires_confirmation:
            sc.confirmed_by_doctor = True
            sc.confirmed_at = now

    # Check if adherence monitoring required for any item -> create ASHA follow-up task
    adherence_items = [it for it in p.items if it.adherence_monitoring_required]
    if adherence_items:
        citizen = db.query(CitizenProfile).filter(CitizenProfile.id == p.citizen_id).first()
        asha_id = citizen.assigned_asha_id if citizen else None

        fu = FollowUp(
            case_id=p.case_id,
            citizen_id=p.citizen_id,
            consultation_id=p.consultation_id,
            prescription_id=p.id,
            created_by_id=current_user.id,
            created_by_role="DOCTOR",
            source="DOCTOR_ASSIGNED",
            task_type="PRESCRIPTION_ADHERENCE_MONITORING",
            reason=f"Medication adherence check for {len(adherence_items)} items: {', '.join([it.generic_name_snapshot for it in adherence_items])}",
            assigned_user_id=asha_id,
            instructions=f"Verify patient has obtained medicines ({', '.join([it.generic_name_snapshot for it in adherence_items])}) and is following dosage schedule.",
            due_at=now + timedelta(days=2),
            status="PENDING",
            adherence_required=True,
            created_at=now
        )
        db.add(fu)

    db.commit()
    db.refresh(p)

    log_prescription_audit_event(db, p.id, "SIGNED", current_user.id, current_user.role.value, {"reference": p.reference})

    return StandardResponse(data=build_prescription_detail_dict(db, p))


@router.post("/prescriptions/{prescription_id}/amend", response_model=StandardResponse)
def amend_prescription(
    prescription_id: str,
    payload: PrescriptionAmendRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(doctor_only)
):
    orig = db.query(Prescription).filter(Prescription.id == prescription_id).first()
    if not orig:
        raise HTTPException(status_code=404, detail={"code": "PRESCRIPTION_NOT_FOUND", "message": "Original prescription not found."})

    if orig.status not in ["SIGNED", "ACTIVE"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "INVALID_AMENDMENT_TARGET", "message": "Only signed/active prescriptions can be amended."}
        )

    now = utc_now()
    new_ref = generate_prescription_reference()

    new_rx = Prescription(
        reference=new_ref,
        citizen_id=orig.citizen_id,
        case_id=orig.case_id,
        referral_id=orig.referral_id,
        consultation_id=orig.consultation_id,
        prescriber_doctor_id=current_user.id,
        doctor_id=current_user.id,
        facility_id=orig.facility_id,
        status="DRAFT",
        version_number=orig.version_number + 1,
        supersedes_prescription_id=orig.id,
        clinical_context=f"Amended: {payload.reason_note or payload.reason_code}. Original Ref: {orig.reference}",
        patient_language=orig.patient_language,
        created_at=now,
        updated_at=now
    )
    db.add(new_rx)
    db.flush()

    # Add amended items
    for item in payload.items:
        it = PrescriptionItem(
            prescription_id=new_rx.id,
            medicine_catalog_id=item.medicine_catalog_id,
            generic_name_snapshot=item.generic_name_snapshot,
            medicine=item.generic_name_snapshot,
            brand_name_snapshot=item.brand_name_snapshot,
            formulation=item.formulation,
            strength=item.strength,
            dose=item.dose,
            dose_unit=item.dose_unit,
            route=item.route,
            frequency=item.frequency,
            timing=item.timing,
            duration_value=item.duration_value,
            duration_unit=item.duration_unit,
            quantity=item.quantity,
            instructions=item.instructions,
            indication=item.indication,
            as_needed=item.as_needed,
            max_frequency=item.max_frequency,
            adherence_monitoring_required=item.adherence_monitoring_required,
            status="ACTIVE",
            created_at=now,
            updated_at=now
        )
        db.add(it)

    # Mark original prescription as AMENDED
    orig.status = "AMENDED"
    orig.updated_at = now

    # Record amendment history record
    amendment_rec = PrescriptionAmendment(
        original_prescription_id=orig.id,
        new_prescription_id=new_rx.id,
        reason_code=payload.reason_code,
        reason_note=payload.reason_note,
        created_by_doctor_id=current_user.id,
        created_at=now
    )
    db.add(amendment_rec)

    db.commit()
    db.refresh(new_rx)

    run_deterministic_safety_checks(db, new_rx)
    log_prescription_audit_event(db, orig.id, "AMENDED", current_user.id, current_user.role.value, {"new_prescription_id": new_rx.id})

    return StandardResponse(data=build_prescription_detail_dict(db, new_rx))


@router.post("/prescriptions/{prescription_id}/items/{item_id}/stop", response_model=StandardResponse)
def stop_prescription_item(
    prescription_id: str,
    item_id: str,
    payload: StopMedicineRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(doctor_only)
):
    p = db.query(Prescription).filter(Prescription.id == prescription_id).first()
    if not p:
        raise HTTPException(status_code=404, detail={"code": "PRESCRIPTION_NOT_FOUND", "message": "Prescription not found."})

    item = db.query(PrescriptionItem).filter(
        PrescriptionItem.id == item_id,
        PrescriptionItem.prescription_id == prescription_id
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail={"code": "ITEM_NOT_FOUND", "message": "Prescription item not found."})

    now = utc_now()
    item.status = "STOPPED"
    item.stopped_at = payload.stop_date or now
    item.stopped_by_doctor_id = current_user.id
    item.stop_reason = f"{payload.stop_reason}: {payload.doctor_note or ''}"
    item.updated_at = now

    # Evaluate overall prescription status
    active_items = [it for it in p.items if it.status == "ACTIVE" and it.id != item_id]
    if not active_items:
        p.status = "STOPPED"
    else:
        p.status = "PARTIALLY_STOPPED"
    p.updated_at = now

    if payload.asha_notification_required:
        fu = FollowUp(
            case_id=p.case_id,
            citizen_id=p.citizen_id,
            consultation_id=p.consultation_id,
            prescription_id=p.id,
            created_by_id=current_user.id,
            created_by_role="DOCTOR",
            source="DOCTOR_ASSIGNED",
            task_type="MEDICINE_STOPPED_CONFIRMATION",
            reason=f"Doctor stopped medication '{item.generic_name_snapshot}'. Reason: {payload.stop_reason}",
            instructions=f"Inform patient to immediately discontinue taking '{item.generic_name_snapshot}'. Guidance: {payload.patient_guidance or 'Discontinue as directed by doctor.'}",
            due_at=now + timedelta(days=1),
            status="PENDING",
            created_at=now
        )
        db.add(fu)

    db.commit()
    db.refresh(p)

    log_prescription_audit_event(db, p.id, "MEDICINE_STOPPED", current_user.id, current_user.role.value, {"item_id": item_id, "medicine": item.generic_name_snapshot})

    return StandardResponse(data=build_prescription_detail_dict(db, p))


@router.post("/prescriptions/{prescription_id}/cancel", response_model=StandardResponse)
def cancel_prescription(
    prescription_id: str,
    payload: PrescriptionCancelRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(doctor_only)
):
    p = db.query(Prescription).filter(Prescription.id == prescription_id).first()
    if not p:
        raise HTTPException(status_code=404, detail={"code": "PRESCRIPTION_NOT_FOUND", "message": "Prescription not found."})

    now = utc_now()
    if p.status in ["SIGNED", "ACTIVE"]:
        p.status = "VOIDED"
    else:
        p.status = "CANCELLED"

    p.cancelled_at = now
    p.cancellation_reason = payload.cancellation_reason
    p.updated_at = now

    db.commit()
    db.refresh(p)

    log_prescription_audit_event(db, p.id, "CANCELLED", current_user.id, current_user.role.value, {"reason": payload.cancellation_reason})

    return StandardResponse(data=build_prescription_detail_dict(db, p))


@router.post("/prescriptions/{prescription_id}/assign-followup", response_model=StandardResponse)
def assign_prescription_adherence_followup(
    prescription_id: str,
    payload: PrescriptionFollowUpAssignRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(doctor_only)
):
    p = db.query(Prescription).filter(Prescription.id == prescription_id).first()
    if not p:
        raise HTTPException(status_code=404, detail={"code": "PRESCRIPTION_NOT_FOUND", "message": "Prescription not found."})

    now = utc_now()
    citizen = db.query(CitizenProfile).filter(CitizenProfile.id == p.citizen_id).first()
    target_asha_id = payload.asha_id or (citizen.assigned_asha_id if citizen else None)

    fu = FollowUp(
        case_id=p.case_id,
        citizen_id=p.citizen_id,
        consultation_id=p.consultation_id,
        prescription_id=p.id,
        created_by_id=current_user.id,
        created_by_role="DOCTOR",
        source="DOCTOR_ASSIGNED",
        task_type="PRESCRIPTION_ADHERENCE_MONITORING",
        reason=f"Doctor assigned adherence follow-up for Prescription {p.reference}",
        assigned_user_id=target_asha_id,
        instructions=payload.instructions,
        measurements_to_repeat=payload.measurements_to_repeat,
        due_at=now + timedelta(days=payload.due_in_days),
        status="PENDING",
        adherence_required=True,
        created_at=now
    )
    db.add(fu)
    db.commit()
    db.refresh(fu)

    log_prescription_audit_event(db, p.id, "FOLLOWUP_ASSIGNED", current_user.id, current_user.role.value, {"followup_id": fu.id})

    return StandardResponse(data={"message": "Adherence follow-up task assigned successfully.", "followup_id": fu.id})
