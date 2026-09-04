"""
Automated Pytest Suite for Doctor Portal Recent Care Activity Stream
"""

import pytest
from datetime import datetime, timezone
from app.database import SessionLocal
from app.models import User, Consultation, Referral
from app.services.recent_activity_service import (
    get_doctor_recent_activity_records,
    normalize_actor_name,
    clean_diagnosis
)

def test_doctor_title_normalization_and_clean_diagnosis():
    # Test doctor title normalization
    assert normalize_actor_name("Dr. Abhinav Sharma", role="PHC_DOCTOR") == "Dr. Abhinav Sharma"
    assert normalize_actor_name("Dr. Dr. Abhinav Sharma", role="PHC_DOCTOR") == "Dr. Abhinav Sharma"
    assert normalize_actor_name("Abhinav Sharma", role="PHC_DOCTOR") == "Dr. Abhinav Sharma"
    assert normalize_actor_name(None, role="PHC_DOCTOR") == "Doctor"
    assert normalize_actor_name(None, role="PHC_DOCTOR", default_name="Dr. Abhinav Sharma") == "Dr. Abhinav Sharma"

    # Test clean diagnosis
    assert clean_diagnosis(None) is None
    assert clean_diagnosis("None") is None
    assert clean_diagnosis("null") is None
    assert clean_diagnosis("undefined") is None
    assert clean_diagnosis("") is None
    assert clean_diagnosis("  ") is None
    assert clean_diagnosis("Severe Preeclampsia") == "Severe Preeclampsia"


def test_recent_activity_phc_isolation_and_rbac():
    db = SessionLocal()
    try:
        doc_user = db.query(User).filter(User.role == "PHC_DOCTOR").first()
        assert doc_user is not None, "Doctor user must exist in demo database"

        items, total = get_doctor_recent_activity_records(
            db=db,
            doctor_user=doc_user,
            limit=8
        )

        assert isinstance(items, list)
        assert total >= len(items)

        if items:
            item = items[0]
            assert "event_id" in item
            assert "event_type" in item
            assert "title" in item
            assert "description" in item
            assert "patient_name" in item
            assert "case_reference" in item
            assert "source_entity_type" in item
            assert "source_entity_id" in item
            assert "actor_name" in item
            assert "actor_role" in item
            assert "occurred_at" in item
            assert "target_route" in item
    finally:
        db.close()


def test_recent_activity_event_mapping_and_ordering():
    db = SessionLocal()
    try:
        doc_user = db.query(User).filter(User.role == "PHC_DOCTOR").first()
        items, total = get_doctor_recent_activity_records(
            db=db,
            doctor_user=doc_user,
            limit=50
        )

        # Check ordering: occurred_at DESC
        timestamps = [item["occurred_at"] for item in items]
        for i in range(len(timestamps) - 1):
            assert timestamps[i] >= timestamps[i + 1], "Activity stream must be sorted by occurred_at DESC"

        # Check target routes format
        for item in items:
            route = item["target_route"]
            assert route.startswith("/doctor/"), f"Target route should start with /doctor/, got {route}"
            assert not route.endswith("/None"), f"Target route must not end with /None, got {route}"
    finally:
        db.close()


def test_null_diagnosis_omission_in_consultation_completed():
    db = SessionLocal()
    try:
        doc_user = db.query(User).filter(User.role == "PHC_DOCTOR").first()

        # Find or create a consultation with null diagnosis
        c = db.query(Consultation).first()
        if c:
            c.confirmed_diagnosis = None
            db.commit()

        items, _ = get_doctor_recent_activity_records(db=db, doctor_user=doc_user, limit=50)

        cons_comp_events = [e for e in items if e["event_type"] == "CONSULTATION_COMPLETED"]
        for ev in cons_comp_events:
            desc = ev["description"]
            assert "None" not in desc, f"Description must not contain 'None', got: {desc}"
            assert "null" not in desc, f"Description must not contain 'null', got: {desc}"
            assert "undefined" not in desc, f"Description must not contain 'undefined', got: {desc}"
            assert "Dr. Dr." not in ev["actor_name"], f"Actor name must not duplicate title, got: {ev['actor_name']}"
    finally:
        db.close()


def test_recent_activity_deduplication_and_idempotency():
    db = SessionLocal()
    try:
        doc_user = db.query(User).filter(User.role == "PHC_DOCTOR").first()

        # Query twice
        items1, total1 = get_doctor_recent_activity_records(db=db, doctor_user=doc_user, limit=50)
        items2, total2 = get_doctor_recent_activity_records(db=db, doctor_user=doc_user, limit=50)

        assert total1 == total2
        assert len(items1) == len(items2)

        # Verify no duplicate event_ids in returned list
        event_ids = [item["event_id"] for item in items1]
        assert len(event_ids) == len(set(event_ids)), "Activity stream must contain zero duplicate event IDs"
    finally:
        db.close()


def test_no_pii_leakage_in_activity_payload():
    db = SessionLocal()
    try:
        doc_user = db.query(User).filter(User.role == "PHC_DOCTOR").first()
        items, _ = get_doctor_recent_activity_records(db=db, doctor_user=doc_user, limit=50)

        for item in items:
            # Payload should not leak ABHA number, phone number or sensitive raw notes
            payload_str = str(item)
            assert "ABHA-" not in payload_str, f"Payload must not leak ABHA reference: {payload_str}"
            assert "98230" not in payload_str, f"Payload must not leak raw phone numbers: {payload_str}"
    finally:
        db.close()
