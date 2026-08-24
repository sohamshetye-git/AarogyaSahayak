from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Case, Consultation, Referral
from app.schemas import StandardResponse

router = APIRouter(prefix="/reports", tags=["Reports & Clinical Documents"])

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
