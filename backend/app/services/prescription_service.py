"""Prescription Service: Lifecycle State Machine, Deterministic Safety Validation, Signing, Amendments, Medicine Stopping, and Audit Event Logging.
"""

from datetime import datetime, timezone
import uuid
from typing import List, Dict, Any, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, desc

from app.models import (
    Prescription, PrescriptionItem, MedicineCatalog, PrescriptionSafetyCheck,
    PrescriptionAmendment, PrescriptionAcknowledgement, CitizenProfile, Case,
    Consultation, Referral, FollowUp, User, AuditLog, utc_now
)

VALID_STATUS_TRANSITIONS = {
    "DRAFT": ["READY_FOR_REVIEW", "SIGNED", "CANCELLED"],
    "READY_FOR_REVIEW": ["DRAFT", "SIGNED", "CANCELLED"],
    "SIGNED": ["ACTIVE", "AMENDED", "VOIDED"],
    "ACTIVE": ["COMPLETED", "AMENDED", "PARTIALLY_STOPPED", "STOPPED", "VOIDED"],
    "PARTIALLY_STOPPED": ["COMPLETED", "AMENDED", "STOPPED"],
    "AMENDED": [],
    "COMPLETED": [],
    "STOPPED": [],
    "CANCELLED": [],
    "VOIDED": [],
}


def generate_prescription_reference() -> str:
    today_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    short_uuid = str(uuid.uuid4())[:6].upper()
    return f"RX-{today_str}-{short_uuid}"


def validate_status_transition(current_status: str, target_status: str):
    allowed = VALID_STATUS_TRANSITIONS.get(current_status, [])
    if target_status not in allowed and current_status != target_status:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Invalid prescription status transition from '{current_status}' to '{target_status}'. Allowed: {allowed}"
        )


def run_deterministic_safety_checks(db: Session, prescription: Prescription) -> List[Dict[str, Any]]:
    """Runs deterministic safety validation rules without AI interpretation.
    Returns list of dicts with check details.
    """
    citizen = db.query(CitizenProfile).filter(CitizenProfile.id == prescription.citizen_id).first()
    items = prescription.items or []

    checks = []

    # 1. Required fields check
    if not items:
        checks.append({
            "check_type": "REQUIRED_FIELDS",
            "severity": "BLOCKING_ERROR",
            "message": "Prescription must contain at least one medication item.",
            "source_rule": "RULE_MIN_MEDICINE_COUNT",
            "requires_confirmation": False
        })

    for item in items:
        if not item.generic_name_snapshot or not item.dose or not item.frequency or not item.duration_value:
            checks.append({
                "check_type": "REQUIRED_FIELDS",
                "severity": "BLOCKING_ERROR",
                "message": f"Medicine '{item.generic_name_snapshot or 'Unnamed'}' is missing required dosage/frequency/duration fields.",
                "source_rule": "RULE_REQUIRED_ITEM_FIELDS",
                "requires_confirmation": False
            })

    if citizen:
        # 2. Missing Allergy History check
        if citizen.allergies is None or (isinstance(citizen.allergies, list) and len(citizen.allergies) == 0):
            checks.append({
                "check_type": "MISSING_HISTORY",
                "severity": "DOCTOR_CONFIRMATION_REQUIRED",
                "message": "Allergy history is not recorded for this patient. Doctor confirmation is required before signing.",
                "source_rule": "RULE_ALLERGY_HISTORY_MISSING",
                "requires_confirmation": True
            })

        # 3. Missing Current Medications History check
        if citizen.current_medications is None or (isinstance(citizen.current_medications, list) and len(citizen.current_medications) == 0):
            checks.append({
                "check_type": "MISSING_HISTORY",
                "severity": "DOCTOR_CONFIRMATION_REQUIRED",
                "message": "Current medication history is not recorded for this patient. Doctor confirmation is required before signing.",
                "source_rule": "RULE_CURRENT_MEDS_MISSING",
                "requires_confirmation": True
            })

        # 4. Allergy Match check
        patient_allergies = [a.lower() for a in (citizen.allergies or []) if isinstance(a, str)]
        for item in items:
            med_name = (item.generic_name_snapshot or "").lower()
            for allergy in patient_allergies:
                if allergy in med_name or (allergy == "penicillin" and "amoxicillin" in med_name):
                    checks.append({
                        "check_type": "ALLERGY_CHECK",
                        "severity": "BLOCKING_ERROR",
                        "message": f"Known patient allergy '{allergy.upper()}' matches prescribed medicine '{item.generic_name_snapshot}'.",
                        "source_rule": "RULE_ALLERGY_MATCH",
                        "requires_confirmation": False
                    })

        # 5. Duplicate Active Medicine Check
        existing_active_rxs = db.query(Prescription).filter(
            Prescription.citizen_id == citizen.id,
            Prescription.status.in_(["SIGNED", "ACTIVE"]),
            Prescription.id != prescription.id
        ).all()
        active_med_names = set()
        for rx in existing_active_rxs:
            for it in rx.items:
                if it.status == "ACTIVE":
                    active_med_names.add(it.generic_name_snapshot.lower())

        for item in items:
            if item.generic_name_snapshot.lower() in active_med_names:
                checks.append({
                    "check_type": "DUPLICATE_THERAPY",
                    "severity": "DOCTOR_CONFIRMATION_REQUIRED",
                    "message": f"Patient is already taking active medication '{item.generic_name_snapshot}'. Doctor confirmation required for duplicate therapy.",
                    "source_rule": "RULE_DUPLICATE_THERAPY",
                    "requires_confirmation": True
                })

        # 6. Pregnancy demographic caution check
        if citizen.is_pregnant:
            for item in items:
                name_l = (item.generic_name_snapshot or "").lower()
                if any(bad in name_l for bad in ["enalapril", "losartan", "ibuprofen", "doxycycline", "warfarin"]):
                    checks.append({
                        "check_type": "DEMOGRAPHIC_ALERT",
                        "severity": "BLOCKING_ERROR",
                        "message": f"Medication '{item.generic_name_snapshot}' is contraindicated in pregnancy.",
                        "source_rule": "RULE_PREGNANCY_CONTRAINDICATION",
                        "requires_confirmation": False
                    })
                elif any(caut in name_l for caut in ["metformin", "labetalol", "methyldopa", "nifedipine", "iron", "folic"]):
                    checks.append({
                        "check_type": "DEMOGRAPHIC_ALERT",
                        "severity": "DOCTOR_CONFIRMATION_REQUIRED",
                        "message": f"Patient is pregnant ({citizen.gestational_weeks or '?'} weeks). Confirm maternal dosage safety for '{item.generic_name_snapshot}'.",
                        "source_rule": "RULE_PREGNANCY_CONFIRMATION",
                        "requires_confirmation": True
                    })

        # 7. Previously Stopped Medicine Check
        stopped_items = db.query(PrescriptionItem).join(Prescription).filter(
            Prescription.citizen_id == citizen.id,
            PrescriptionItem.status == "STOPPED"
        ).all()
        stopped_names = {it.generic_name_snapshot.lower() for it in stopped_items}
        for item in items:
            if item.generic_name_snapshot.lower() in stopped_names:
                checks.append({
                    "check_type": "PREVIOUSLY_STOPPED",
                    "severity": "DOCTOR_CONFIRMATION_REQUIRED",
                    "message": f"Medication '{item.generic_name_snapshot}' was previously stopped for this patient. Confirm reassessment before prescribing.",
                    "source_rule": "RULE_PREVIOUSLY_STOPPED_REASSESSMENT",
                    "requires_confirmation": True
                })

    # Save safety checks to database
    db.query(PrescriptionSafetyCheck).filter(PrescriptionSafetyCheck.prescription_id == prescription.id).delete()
    for c in checks:
        sc = PrescriptionSafetyCheck(
            prescription_id=prescription.id,
            check_type=c["check_type"],
            severity=c["severity"],
            message=c["message"],
            source_rule=c["source_rule"],
            requires_confirmation=c["requires_confirmation"],
            confirmed_by_doctor=False
        )
        db.add(sc)
    db.commit()

    return checks


def log_prescription_audit_event(
    db: Session,
    prescription_id: str,
    action: str,
    actor_id: str,
    actor_role: str,
    details: Optional[Dict[str, Any]] = None
):
    log = AuditLog(
        actor_user_id=actor_id,
        actor_role=actor_role,
        action=f"PRESCRIPTION_{action}",
        resource_type="PRESCRIPTION",
        resource_id=prescription_id,
        outcome="SUCCESS",
        metadata_json=details or {},
        created_at=utc_now()
    )
    db.add(log)
    db.commit()
