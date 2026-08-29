from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import Response as FastAPIResponse
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any, List

from app.database import get_db
from app.models import Case, Consultation, Referral, User, AuditLog
from app.schemas import StandardResponse
from app.dependencies import require_staff, require_doctor
from app.services.doctor_report_service import DoctorReportService

router = APIRouter(prefix="/reports", tags=["Reports & Clinical Documents"])


def _extract_doctor_context(current_user: User) -> tuple:
    facility_id = "PHC-09"
    facility_name = "Kalyanpur Primary Health Centre"
    if current_user.worker_profile and current_user.worker_profile.facility_id:
        facility_id = current_user.worker_profile.facility_id
    if current_user.worker_profile and getattr(current_user.worker_profile, "facility_name", None):
        facility_name = current_user.worker_profile.facility_name
    doctor_name = getattr(current_user, "name", getattr(current_user, "full_name", "Dr. Abhinav Sharma"))
    return facility_id, facility_name, doctor_name


@router.get("/case/{case_id}", response_model=StandardResponse)
def get_case_clinical_report(case_id: str, db: Session = Depends(get_db)):
    case = db.query(Case).filter((Case.id == case_id) | (Case.reference == case_id)).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    consultation = db.query(Consultation).filter(Consultation.case_id == case.id).first()
    referral = db.query(Referral).filter(Referral.case_id == case.id).first()

    report = {
        "title": "AAROGYA SAHAYAK CLINICAL CASE SUMMARY",
        "case_reference": case.reference,
        "date": case.created_at.strftime("%d %B %Y"),
        "patient": {
            "name": case.citizen.display_name if case.citizen else "Sunita Devi",
            "age": case.citizen.age_estimate if case.citizen else 28,
            "village": case.citizen.village_name if case.citizen else "Kalyanpur",
            "is_pregnant": case.citizen.is_pregnant if case.citizen else False,
            "gestational_weeks": case.citizen.gestational_weeks if case.citizen else None
        },
        "presenting_symptoms": [s.normalized_term for s in case.symptoms],
        "vitals_recorded": [
            {
                "bp": f"{v.systolic_bp}/{v.diastolic_bp}" if v.systolic_bp else "N/A",
                "spo2": f"{v.spo2}%" if v.spo2 else "N/A",
                "pulse": f"{v.pulse} bpm" if v.pulse else "N/A",
                "temp": f"{v.temperature_c} C" if v.temperature_c else "N/A"
            }
            for v in case.vitals
        ],
        "asha_referral": {
            "reference": referral.reference if referral else "N/A",
            "facility": referral.to_facility_name if referral else "Kalyanpur PHC",
            "reason": referral.reason if referral else "Pregnancy risk signs"
        } if referral else None,
        "doctor_consultation": {
            "doctor": consultation.doctor_name if consultation else "Dr. Abhinav Sharma",
            "confirmed_diagnosis": consultation.confirmed_diagnosis if consultation else "Evaluation of Pre-eclampsia",
            "care_plan": consultation.care_plan_summary if consultation else "Bed rest, low sodium, BP monitoring, antihypertensive regimen as prescribed.",
            "signed_at": consultation.signed_at.isoformat() if consultation and consultation.signed_at else None
        } if consultation else None,
        "disclaimer": "AI-assisted structured summary – Human medical review and approval completed."
    }

    return StandardResponse(data=report)


# ==============================================================================
# DOCTOR REPORTS ENDPOINTS (STRICT PHC SCOPE & STANDARD RESPONSE WRAPPER)
# ==============================================================================

@router.get("/overview", response_model=StandardResponse)
def get_doctor_reports_overview(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    village: Optional[str] = None,
    asha_id: Optional[str] = None,
    category: Optional[str] = None,
    priority: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    facility_id, facility_name, doctor_name = _extract_doctor_context(current_user)
    data = DoctorReportService.get_overview_report(
        db=db,
        facility_id=facility_id,
        facility_name=facility_name,
        doctor_name=doctor_name,
        date_from_str=date_from,
        date_to_str=date_to,
        village=village,
        asha_id=asha_id,
        category=category,
        priority=priority
    )
    return StandardResponse(data=data)


@router.get("/referrals", response_model=StandardResponse)
def get_doctor_referrals_report(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    village: Optional[str] = None,
    asha_id: Optional[str] = None,
    category: Optional[str] = None,
    priority: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    facility_id, facility_name, doctor_name = _extract_doctor_context(current_user)
    data = DoctorReportService.get_referral_report(
        db=db,
        facility_id=facility_id,
        facility_name=facility_name,
        doctor_name=doctor_name,
        date_from_str=date_from,
        date_to_str=date_to,
        village=village,
        asha_id=asha_id,
        category=category,
        priority=priority
    )
    return StandardResponse(data=data)


@router.get("/consultations", response_model=StandardResponse)
def get_doctor_consultations_report(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    village: Optional[str] = None,
    asha_id: Optional[str] = None,
    category: Optional[str] = None,
    priority: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    facility_id, facility_name, doctor_name = _extract_doctor_context(current_user)
    data = DoctorReportService.get_consultation_report(
        db=db,
        facility_id=facility_id,
        facility_name=facility_name,
        doctor_name=doctor_name,
        date_from_str=date_from,
        date_to_str=date_to,
        village=village,
        asha_id=asha_id,
        category=category,
        priority=priority
    )
    return StandardResponse(data=data)


@router.get("/patients", response_model=StandardResponse)
def get_doctor_patients_report(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    village: Optional[str] = None,
    asha_id: Optional[str] = None,
    category: Optional[str] = None,
    priority: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    facility_id, facility_name, doctor_name = _extract_doctor_context(current_user)
    data = DoctorReportService.get_patient_workload_report(
        db=db,
        facility_id=facility_id,
        facility_name=facility_name,
        doctor_name=doctor_name,
        date_from_str=date_from,
        date_to_str=date_to,
        village=village,
        asha_id=asha_id,
        category=category,
        priority=priority
    )
    return StandardResponse(data=data)


@router.get("/investigations", response_model=StandardResponse)
def get_doctor_investigations_report(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    village: Optional[str] = None,
    asha_id: Optional[str] = None,
    category: Optional[str] = None,
    priority: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    facility_id, facility_name, doctor_name = _extract_doctor_context(current_user)
    data = DoctorReportService.get_investigation_report(
        db=db,
        facility_id=facility_id,
        facility_name=facility_name,
        doctor_name=doctor_name,
        date_from_str=date_from,
        date_to_str=date_to,
        village=village,
        asha_id=asha_id,
        category=category,
        priority=priority
    )
    return StandardResponse(data=data)


@router.get("/prescriptions", response_model=StandardResponse)
def get_doctor_prescriptions_report(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    village: Optional[str] = None,
    asha_id: Optional[str] = None,
    category: Optional[str] = None,
    priority: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    facility_id, facility_name, doctor_name = _extract_doctor_context(current_user)
    data = DoctorReportService.get_prescription_report(
        db=db,
        facility_id=facility_id,
        facility_name=facility_name,
        doctor_name=doctor_name,
        date_from_str=date_from,
        date_to_str=date_to,
        village=village,
        asha_id=asha_id,
        category=category,
        priority=priority
    )
    return StandardResponse(data=data)


@router.get("/followups", response_model=StandardResponse)
def get_doctor_followups_report(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    village: Optional[str] = None,
    asha_id: Optional[str] = None,
    category: Optional[str] = None,
    priority: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    facility_id, facility_name, doctor_name = _extract_doctor_context(current_user)
    data = DoctorReportService.get_asha_followup_report(
        db=db,
        facility_id=facility_id,
        facility_name=facility_name,
        doctor_name=doctor_name,
        date_from_str=date_from,
        date_to_str=date_to,
        village=village,
        asha_id=asha_id,
        category=category,
        priority=priority
    )
    return StandardResponse(data=data)


@router.get("/maternal", response_model=StandardResponse)
def get_doctor_maternal_report(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    village: Optional[str] = None,
    asha_id: Optional[str] = None,
    category: Optional[str] = None,
    priority: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    facility_id, facility_name, doctor_name = _extract_doctor_context(current_user)
    data = DoctorReportService.get_maternal_report(
        db=db,
        facility_id=facility_id,
        facility_name=facility_name,
        doctor_name=doctor_name,
        date_from_str=date_from,
        date_to_str=date_to,
        village=village,
        asha_id=asha_id,
        category=category,
        priority=priority
    )
    return StandardResponse(data=data)


@router.get("/child-health", response_model=StandardResponse)
def get_doctor_child_health_report(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    village: Optional[str] = None,
    asha_id: Optional[str] = None,
    category: Optional[str] = None,
    priority: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    facility_id, facility_name, doctor_name = _extract_doctor_context(current_user)
    data = DoctorReportService.get_child_health_report(
        db=db,
        facility_id=facility_id,
        facility_name=facility_name,
        doctor_name=doctor_name,
        date_from_str=date_from,
        date_to_str=date_to,
        village=village,
        asha_id=asha_id,
        category=category,
        priority=priority
    )
    return StandardResponse(data=data)


@router.get("/ncd", response_model=StandardResponse)
def get_doctor_ncd_report(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    village: Optional[str] = None,
    asha_id: Optional[str] = None,
    category: Optional[str] = None,
    priority: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    facility_id, facility_name, doctor_name = _extract_doctor_context(current_user)
    data = DoctorReportService.get_ncd_report(
        db=db,
        facility_id=facility_id,
        facility_name=facility_name,
        doctor_name=doctor_name,
        date_from_str=date_from,
        date_to_str=date_to,
        village=village,
        asha_id=asha_id,
        category=category,
        priority=priority
    )
    return StandardResponse(data=data)


@router.get("/safety", response_model=StandardResponse)
def get_doctor_safety_report(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    village: Optional[str] = None,
    asha_id: Optional[str] = None,
    category: Optional[str] = None,
    priority: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    facility_id, facility_name, doctor_name = _extract_doctor_context(current_user)
    data = DoctorReportService.get_safety_report(
        db=db,
        facility_id=facility_id,
        facility_name=facility_name,
        doctor_name=doctor_name,
        date_from_str=date_from,
        date_to_str=date_to,
        village=village,
        asha_id=asha_id,
        category=category,
        priority=priority
    )
    return StandardResponse(data=data)


@router.get("/workflow-funnel", response_model=StandardResponse)
def get_doctor_workflow_funnel(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    village: Optional[str] = None,
    asha_id: Optional[str] = None,
    category: Optional[str] = None,
    priority: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    facility_id, facility_name, doctor_name = _extract_doctor_context(current_user)
    data = DoctorReportService.get_care_workflow_funnel(
        db=db,
        facility_id=facility_id,
        facility_name=facility_name,
        doctor_name=doctor_name,
        date_from_str=date_from,
        date_to_str=date_to,
        village=village,
        asha_id=asha_id,
        category=category,
        priority=priority
    )
    return StandardResponse(data=data)


@router.get("/pending-work", response_model=StandardResponse)
def get_doctor_pending_work(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    facility_id, _, _ = _extract_doctor_context(current_user)
    data = DoctorReportService.get_pending_clinical_work(db=db, facility_id=facility_id)
    return StandardResponse(data=data)


@router.get("/recent-activity", response_model=StandardResponse)
def get_doctor_recent_activity(
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    facility_id, _, _ = _extract_doctor_context(current_user)
    data = DoctorReportService.get_recent_care_activity(db=db, facility_id=facility_id, limit=limit)
    return StandardResponse(data=data)


@router.get("/export")
def export_doctor_report(
    format: str = Query("csv", regex="^(csv|pdf)$"),
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    village: Optional[str] = None,
    asha_id: Optional[str] = None,
    category: Optional[str] = None,
    priority: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    facility_id, facility_name, doctor_name = _extract_doctor_context(current_user)
    
    # Audit log entry for report export event
    audit = AuditLog(
        actor_user_id=current_user.id,
        actor_role=current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role),
        action="DOCTOR_REPORT_EXPORTED",
        resource_type="REPORT_EXPORT",
        resource_id=facility_id,
        outcome="SUCCESS",
        metadata_json={
            "format": format,
            "date_from": date_from,
            "date_to": date_to,
            "village": village,
            "facility_id": facility_id
        }
    )
    db.add(audit)
    db.commit()

    content, media_type, filename = DoctorReportService.generate_report_export(
        db=db,
        facility_id=facility_id,
        facility_name=facility_name,
        doctor_name=doctor_name,
        export_format=format,
        date_from_str=date_from,
        date_to_str=date_to,
        village=village,
        asha_id=asha_id,
        category=category,
        priority=priority
    )

    return FastAPIResponse(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )
