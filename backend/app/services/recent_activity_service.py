"""
Authoritative Recent Care Activity Service for Doctor Portal
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models import (
    User, Case, Referral, Consultation, TestOrder, Prescription, FollowUp,
    FollowUpEscalation, AuditLog, CitizenProfile, WorkerProfile
)

def normalize_actor_name(name: Optional[str], role: str = "PHC_DOCTOR", default_name: Optional[str] = None) -> str:
    """
    Normalizes professional titles so names never duplicate into 'Dr. Dr. Name'.
    """
    fallback = default_name or ("Doctor" if role in ["PHC_DOCTOR", "DOCTOR"] else "ASHA Worker")
    if not name or str(name).strip().lower() in ["", "none", "null", "undefined"]:
        return fallback
    
    s = str(name).strip()
    if role in ["PHC_DOCTOR", "DOCTOR"]:
        # Strip all existing 'Dr.' or 'Dr ' prefixes
        while s.startswith("Dr. ") or s.startswith("Dr "):
            if s.startswith("Dr. "):
                s = s[4:].strip()
            elif s.startswith("Dr "):
                s = s[3:].strip()
        return f"Dr. {s}"
    elif role in ["ASHA_WORKER", "ASHA"]:
        # Ensure ASHA suffix or clean string
        if not s.endswith("(ASHA)") and not "ASHA" in s:
            return f"{s} (ASHA)"
        return s
    return s

def clean_diagnosis(diag: Optional[str]) -> Optional[str]:
    """
    Returns cleaned diagnosis string or None if diagnosis is null, blank, None, or undefined.
    """
    if not diag:
        return None
    d = str(diag).strip()
    if d.lower() in ["none", "null", "undefined", "", "n/a", "[]", "{}"]:
        return None
    return d

def format_iso_utc(dt: Optional[datetime]) -> str:
    if not dt:
        dt = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()

def get_doctor_facility_id(db: Session, doctor_user: User) -> Optional[str]:
    if doctor_user and doctor_user.worker_profile:
        return doctor_user.worker_profile.facility_id
    return None

def get_doctor_recent_activity_records(
    db: Session,
    doctor_user: User,
    limit: int = 8,
    offset: int = 0,
    event_type_filter: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    search_query: Optional[str] = None
) -> tuple[List[Dict[str, Any]], int]:
    """
    Compiles authoritative, deduplicated, PHC-scoped activity feed.
    """
    events: List[Dict[str, Any]] = []
    facility_id = get_doctor_facility_id(db, doctor_user)

    # 1. Referrals (REFERRAL_RECEIVED, REFERRAL_ACKNOWLEDGED, PATIENT_ARRIVED)
    ref_query = db.query(Referral)
    if facility_id:
        ref_query = ref_query.filter(Referral.to_facility_id == facility_id)
    referrals = ref_query.all()
    for ref in referrals:
        case = ref.case
        citizen = case.citizen if case else None
        p_name = citizen.display_name if citizen else "Citizen"
        c_ref = case.reference if case else "CASE"
        p_id = citizen.id if citizen else (case.citizen_id if case else "")
        asha_name = normalize_actor_name(case.assigned_asha_name if case else None, role="ASHA_WORKER", default_name="ASHA Worker")
        doc_name = normalize_actor_name(doctor_user.name if doctor_user else None, role="PHC_DOCTOR")

        # REFERRAL_RECEIVED
        if ref.created_at:
            urgency_str = ref.urgency.value if hasattr(ref.urgency, "value") else str(ref.urgency)
            events.append({
                "event_id": f"act-ref-rec-{ref.id}",
                "event_type": "REFERRAL_RECEIVED",
                "title": "New Referral Received",
                "description": f"New {urgency_str.lower()} referral received for {p_name} from {asha_name}.",
                "patient_id": p_id,
                "patient_name": p_name,
                "case_id": ref.case_id,
                "case_reference": c_ref,
                "source_entity_type": "REFERRAL",
                "source_entity_id": ref.id,
                "actor_id": ref.from_asha_id or "asha-001",
                "actor_name": asha_name,
                "actor_role": "ASHA_WORKER",
                "occurred_at": format_iso_utc(ref.created_at),
                "target_route": f"/doctor/referrals/{ref.id}"
            })

        # REFERRAL_ACKNOWLEDGED
        if ref.acknowledged_at:
            events.append({
                "event_id": f"act-ref-ack-{ref.id}",
                "event_type": "REFERRAL_ACKNOWLEDGED",
                "title": "Referral Acknowledged",
                "description": f"Doctor acknowledged referral for {p_name}.",
                "patient_id": p_id,
                "patient_name": p_name,
                "case_id": ref.case_id,
                "case_reference": c_ref,
                "source_entity_type": "REFERRAL",
                "source_entity_id": ref.id,
                "actor_id": doctor_user.id,
                "actor_name": doc_name,
                "actor_role": "PHC_DOCTOR",
                "occurred_at": format_iso_utc(ref.acknowledged_at),
                "target_route": f"/doctor/referrals/{ref.id}"
            })

        # PATIENT_ARRIVED
        if ref.status in ["PATIENT_ARRIVED", "ARRIVED"] or (case and case.status == "PATIENT_ARRIVED"):
            arr_time = getattr(ref, "updated_at", None) or ref.acknowledged_at or ref.created_at
            events.append({
                "event_id": f"act-pat-arr-{ref.id}",
                "event_type": "PATIENT_ARRIVED",
                "title": "Patient Arrived at PHC",
                "description": f"{p_name} arrived at {ref.to_facility_name or 'Kalyanpur PHC'}.",
                "patient_id": p_id,
                "patient_name": p_name,
                "case_id": ref.case_id,
                "case_reference": c_ref,
                "source_entity_type": "REFERRAL",
                "source_entity_id": ref.id,
                "actor_id": doctor_user.id,
                "actor_name": doc_name,
                "actor_role": "PHC_DOCTOR",
                "occurred_at": format_iso_utc(arr_time),
                "target_route": f"/doctor/referrals/{ref.id}"
            })

    # 2. Consultations (CONSULTATION_STARTED, CONSULTATION_COMPLETED, HIGHER_CENTER_REFERRAL_CREATED)
    consults_query = db.query(Consultation).join(Case, Consultation.case_id == Case.id)
    if facility_id:
        consults_query = consults_query.filter(Case.assigned_facility_id == facility_id)
    consults = consults_query.all()
    for c in consults:
        case = c.case
        citizen = case.citizen if case else None
        p_name = citizen.display_name if citizen else "Citizen"
        c_ref = case.reference if case else "CASE"
        p_id = citizen.id if citizen else (case.citizen_id if case else "")
        doc_name = normalize_actor_name(c.doctor_name or (doctor_user.name if doctor_user else None), role="PHC_DOCTOR")

        # CONSULTATION_STARTED
        if c.started_at:
            events.append({
                "event_id": f"act-cons-start-{c.id}",
                "event_type": "CONSULTATION_STARTED",
                "title": "Consultation Started",
                "description": f"Consultation started for {p_name}.",
                "patient_id": p_id,
                "patient_name": p_name,
                "case_id": c.case_id,
                "case_reference": c_ref,
                "source_entity_type": "CONSULTATION",
                "source_entity_id": c.id,
                "actor_id": c.doctor_id or doctor_user.id,
                "actor_name": doc_name,
                "actor_role": "PHC_DOCTOR",
                "occurred_at": format_iso_utc(c.started_at),
                "target_route": f"/doctor/consultations/{c.id}"
            })

        # CONSULTATION_COMPLETED
        if c.status == "COMPLETED" or c.completed_at:
            diag = clean_diagnosis(c.confirmed_diagnosis or c.provisional_diagnosis)
            if diag:
                desc = f"Consultation completed for {p_name} - Confirmed Diagnosis: {diag}."
            else:
                desc = f"Consultation completed for {p_name}."

            events.append({
                "event_id": f"act-cons-comp-{c.id}",
                "event_type": "CONSULTATION_COMPLETED",
                "title": "Consultation Completed",
                "description": desc,
                "patient_id": p_id,
                "patient_name": p_name,
                "case_id": c.case_id,
                "case_reference": c_ref,
                "source_entity_type": "CONSULTATION",
                "source_entity_id": c.id,
                "actor_id": c.doctor_id or doctor_user.id,
                "actor_name": doc_name,
                "actor_role": "PHC_DOCTOR",
                "occurred_at": format_iso_utc(c.completed_at or c.started_at or c.created_at),
                "target_route": f"/doctor/consultations/{c.id}"
            })

        # HIGHER_CENTER_REFERRAL_CREATED
        if c.consultation_type == "HIGHER_FACILITY_REFERRAL" or (case and case.status == "REFERRED_TO_HIGHER_FACILITY"):
            events.append({
                "event_id": f"act-hcr-{c.id}",
                "event_type": "HIGHER_CENTER_REFERRAL_CREATED",
                "title": "Higher-Center Referral Created",
                "description": f"Higher-center referral created for {p_name}.",
                "patient_id": p_id,
                "patient_name": p_name,
                "case_id": c.case_id,
                "case_reference": c_ref,
                "source_entity_type": "CONSULTATION",
                "source_entity_id": c.id,
                "actor_id": c.doctor_id or doctor_user.id,
                "actor_name": doc_name,
                "actor_role": "PHC_DOCTOR",
                "occurred_at": format_iso_utc(c.signed_at or c.completed_at or c.created_at),
                "target_route": f"/doctor/consultations/{c.id}"
            })

    # 3. TestOrders (INVESTIGATION_ORDERED, INVESTIGATION_RESULT_AVAILABLE)
    test_orders_query = db.query(TestOrder).join(Consultation, TestOrder.consultation_id == Consultation.id).join(Case, Consultation.case_id == Case.id)
    if facility_id:
        test_orders_query = test_orders_query.filter(Case.assigned_facility_id == facility_id)
    test_orders = test_orders_query.all()
    for t in test_orders:
        c = t.consultation
        case = c.case if c else None
        citizen = case.citizen if case else None
        p_name = citizen.display_name if citizen else "Citizen"
        c_ref = case.reference if case else "CASE"
        p_id = citizen.id if citizen else (case.citizen_id if case else "")
        doc_name = normalize_actor_name(doctor_user.name if doctor_user else None, role="PHC_DOCTOR")

        # INVESTIGATION_ORDERED
        if t.ordered_at:
            events.append({
                "event_id": f"act-inv-ord-{t.id}",
                "event_type": "INVESTIGATION_ORDERED",
                "title": "Investigation Ordered",
                "description": f"{t.test_name} ordered for {p_name}.",
                "patient_id": p_id,
                "patient_name": p_name,
                "case_id": c.case_id if c else "",
                "case_reference": c_ref,
                "source_entity_type": "INVESTIGATION",
                "source_entity_id": t.id,
                "actor_id": doctor_user.id,
                "actor_name": doc_name,
                "actor_role": "PHC_DOCTOR",
                "occurred_at": format_iso_utc(t.ordered_at),
                "target_route": f"/doctor/investigations/{t.id}"
            })

        # INVESTIGATION_RESULT_AVAILABLE
        if t.status in ["RESULT_AVAILABLE", "RESULT_READY", "COMPLETED"] or t.result:
            res_time = t.reviewed_at or t.ordered_at
            events.append({
                "event_id": f"act-inv-res-{t.id}",
                "event_type": "INVESTIGATION_RESULT_AVAILABLE",
                "title": "Test Result Ready",
                "description": f"{t.test_name} result is ready for review for {p_name}.",
                "patient_id": p_id,
                "patient_name": p_name,
                "case_id": c.case_id if c else "",
                "case_reference": c_ref,
                "source_entity_type": "INVESTIGATION",
                "source_entity_id": t.id,
                "actor_id": doctor_user.id,
                "actor_name": doc_name,
                "actor_role": "PHC_DOCTOR",
                "occurred_at": format_iso_utc(res_time),
                "target_route": f"/doctor/investigations/{t.id}"
            })

    # 4. Prescriptions (PRESCRIPTION_SIGNED)
    prescriptions_query = db.query(Prescription).join(Consultation, Prescription.consultation_id == Consultation.id).join(Case, Consultation.case_id == Case.id)
    if facility_id:
        prescriptions_query = prescriptions_query.filter(Case.assigned_facility_id == facility_id)
    prescriptions = prescriptions_query.all()
    for rx in prescriptions:
        c = rx.consultation
        case = c.case if c else None
        citizen = case.citizen if case else None
        p_name = citizen.display_name if citizen else "Citizen"
        c_ref = case.reference if case else "CASE"
        p_id = citizen.id if citizen else (case.citizen_id if case else "")
        doc_name = normalize_actor_name(c.doctor_name if c and c.doctor_name else (doctor_user.name if doctor_user else None), role="PHC_DOCTOR")

        rx_time = getattr(rx, "issued_at", rx.signed_at or rx.created_at)
        if rx_time:
            events.append({
                "event_id": f"act-rx-{rx.id}",
                "event_type": "PRESCRIPTION_SIGNED",
                "title": "Prescription Signed",
                "description": f"Prescription signed for {p_name}.",
                "patient_id": p_id,
                "patient_name": p_name,
                "case_id": c.case_id if c else "",
                "case_reference": c_ref,
                "source_entity_type": "PRESCRIPTION",
                "source_entity_id": rx.id,
                "actor_id": rx.doctor_id or doctor_user.id,
                "actor_name": doc_name,
                "actor_role": "PHC_DOCTOR",
                "occurred_at": format_iso_utc(rx_time),
                "target_route": f"/doctor/prescriptions/{rx.id}"
            })

    # 5. FollowUps (ASHA_FOLLOWUP_ASSIGNED, ASHA_FOLLOWUP_COMPLETED)
    followups_query = db.query(FollowUp).join(Case, FollowUp.case_id == Case.id)
    if facility_id:
        followups_query = followups_query.filter(Case.assigned_facility_id == facility_id)
    follow_ups = followups_query.all()
    for fu in follow_ups:
        case = fu.case
        citizen = fu.citizen or (case.citizen if case else None)
        p_name = citizen.display_name if citizen else "Citizen"
        c_ref = case.reference if case else "CASE"
        p_id = citizen.id if citizen else (case.citizen_id if case else "")
        asha_name = normalize_actor_name(case.assigned_asha_name if case else None, role="ASHA_WORKER", default_name="ASHA Worker")
        doc_name = normalize_actor_name(doctor_user.name if doctor_user else None, role="PHC_DOCTOR")

        # ASHA_FOLLOWUP_ASSIGNED
        if fu.created_at:
            events.append({
                "event_id": f"act-fup-ass-{fu.id}",
                "event_type": "ASHA_FOLLOWUP_ASSIGNED",
                "title": "ASHA Follow-up Assigned",
                "description": f"Follow-up ({fu.task_type or 'BP Monitoring'}) assigned to {asha_name} for {p_name}.",
                "patient_id": p_id,
                "patient_name": p_name,
                "case_id": fu.case_id or "",
                "case_reference": c_ref,
                "source_entity_type": "FOLLOWUP",
                "source_entity_id": fu.id,
                "actor_id": fu.created_by_id or doctor_user.id,
                "actor_name": doc_name,
                "actor_role": "PHC_DOCTOR",
                "occurred_at": format_iso_utc(fu.created_at),
                "target_route": f"/doctor/followups/{fu.id}"
            })

        # ASHA_FOLLOWUP_COMPLETED
        if fu.status in ["COMPLETED", "REVIEWED"] and fu.completed_at:
            events.append({
                "event_id": f"act-fup-comp-{fu.id}",
                "event_type": "ASHA_FOLLOWUP_COMPLETED",
                "title": "ASHA Follow-up Completed",
                "description": f"{asha_name} completed the assigned {fu.task_type or 'BP'} follow-up for {p_name}.",
                "patient_id": p_id,
                "patient_name": p_name,
                "case_id": fu.case_id or "",
                "case_reference": c_ref,
                "source_entity_type": "FOLLOWUP",
                "source_entity_id": fu.id,
                "actor_id": fu.assigned_user_id or "asha-001",
                "actor_name": asha_name,
                "actor_role": "ASHA_WORKER",
                "occurred_at": format_iso_utc(fu.completed_at),
                "target_route": f"/doctor/followups/{fu.id}"
            })

    # 6. FollowUpEscalations (ASHA_ESCALATION_CREATED, ASHA_ESCALATION_REVIEWED)
    escalations_query = db.query(FollowUpEscalation).join(Case, FollowUpEscalation.case_id == Case.id)
    if facility_id:
        escalations_query = escalations_query.filter(Case.assigned_facility_id == facility_id)
    escalations = escalations_query.all()
    for esc in escalations:
        case = esc.case
        citizen = esc.citizen or (case.citizen if case else None)
        p_name = citizen.display_name if citizen else "Citizen"
        c_ref = case.reference if case else "CASE"
        p_id = citizen.id if citizen else (case.citizen_id if case else "")
        asha_name = normalize_actor_name(case.assigned_asha_name if case else None, role="ASHA_WORKER", default_name="ASHA Worker")
        doc_name = normalize_actor_name(doctor_user.name if doctor_user else None, role="PHC_DOCTOR")

        # ASHA_ESCALATION_CREATED
        if esc.escalated_at or esc.created_at:
            events.append({
                "event_id": f"act-esc-cre-{esc.id}",
                "event_type": "ASHA_ESCALATION_CREATED",
                "title": "ASHA Escalation Submitted",
                "description": f"ASHA escalation submitted for {p_name} - {esc.reason}.",
                "patient_id": p_id,
                "patient_name": p_name,
                "case_id": esc.case_id,
                "case_reference": c_ref,
                "source_entity_type": "ESCALATION",
                "source_entity_id": esc.id,
                "actor_id": esc.assigned_asha_id or "asha-001",
                "actor_name": asha_name,
                "actor_role": "ASHA_WORKER",
                "occurred_at": format_iso_utc(esc.escalated_at or esc.created_at),
                "target_route": f"/doctor/followups/{esc.follow_up_id}"
            })

        # ASHA_ESCALATION_REVIEWED
        if esc.status in ["DOCTOR_ACKNOWLEDGED", "ACTION_ASSIGNED", "RESOLVED"] and (esc.acknowledged_at or esc.resolved_at):
            rev_time = esc.acknowledged_at or esc.resolved_at
            events.append({
                "event_id": f"act-esc-rev-{esc.id}",
                "event_type": "ASHA_ESCALATION_REVIEWED",
                "title": "ASHA Escalation Reviewed",
                "description": f"Doctor reviewed ASHA escalation for {p_name}.",
                "patient_id": p_id,
                "patient_name": p_name,
                "case_id": esc.case_id,
                "case_reference": c_ref,
                "source_entity_type": "ESCALATION",
                "source_entity_id": esc.id,
                "actor_id": doctor_user.id,
                "actor_name": doc_name,
                "actor_role": "PHC_DOCTOR",
                "occurred_at": format_iso_utc(rev_time),
                "target_route": f"/doctor/followups/{esc.follow_up_id}"
            })

    # 7. Deduplication by composite key (event_type, source_entity_type, source_entity_id)
    unique_events: List[Dict[str, Any]] = []
    seen_keys = set()
    for ev in events:
        composite_key = f"{ev['event_type']}:{ev['source_entity_type']}:{ev['source_entity_id']}"
        if composite_key not in seen_keys:
            seen_keys.add(composite_key)
            unique_events.append(ev)

    # 8. Sort by occurred_at DESC, event_id DESC
    def sort_key(x):
        dt_str = x["occurred_at"]
        try:
            dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        except Exception:
            dt = datetime.now(timezone.utc)
        return (dt, x["event_id"])

    unique_events.sort(key=sort_key, reverse=True)

    # 9. Apply filters (event_type, start_date, end_date, search_query)
    filtered_events = unique_events
    if event_type_filter and event_type_filter != "ALL":
        filtered_events = [e for e in filtered_events if e["event_type"] == event_type_filter]

    if start_date:
        filtered_events = [e for e in filtered_events if e["occurred_at"] >= start_date]

    if end_date:
        filtered_events = [e for e in filtered_events if e["occurred_at"] <= end_date]

    if search_query:
        sq = search_query.lower()
        filtered_events = [
            e for e in filtered_events
            if sq in e["patient_name"].lower()
            or sq in e["case_reference"].lower()
            or sq in e["title"].lower()
            or sq in e["description"].lower()
        ]

    total_count = len(filtered_events)
    paginated_items = filtered_events[offset: offset + limit]

    return paginated_items, total_count
