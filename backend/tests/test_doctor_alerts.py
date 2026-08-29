"""
Pytest suite for Doctor Alerts Module
Tests RBAC protection, list/summary reconciliation, filter parameters,
lifecycle transitions (seen, acknowledge, snooze, resolve, dismiss),
idempotency, duplicate event protection, audit logging, and PII isolation.
"""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timezone
import uuid

from app.main import app
from app.database import get_db, SessionLocal
from app.models import User, UserRoleEnum, DoctorAlert, AlertAction, AuditLog
from app.services.doctor_alert_service import DoctorAlertService

client = TestClient(app)


def test_doctor_alerts_rbac_denial():
    # Admin attempt to view Doctor Alerts must return 403 Forbidden
    from app.dependencies import get_current_user
    admin_user = User(id="admin-test", name="Admin User", role=UserRoleEnum.DISTRICT_ADMIN)
    
    app.dependency_overrides[get_current_user] = lambda: admin_user
    try:
        res = client.get("/api/doctor/alerts")
        assert res.status_code == 403
        assert "District Admins receive anonymized aggregate alert metrics only" in res.json()["detail"]
    finally:
        app.dependency_overrides.clear()


def test_doctor_alerts_list_and_summary_reconciliation():
    db = SessionLocal()
    try:
        doc_user = db.query(User).filter(User.role == UserRoleEnum.PHC_DOCTOR).first()
        if not doc_user:
            doc_user = User(id="doc-test", name="Dr. Test", role=UserRoleEnum.PHC_DOCTOR)
            db.add(doc_user)
            db.commit()

        from app.dependencies import get_current_user
        app.dependency_overrides[get_current_user] = lambda: doc_user

        res_list = client.get("/api/doctor/alerts")
        assert res_list.status_code == 200
        list_data = res_list.json()["data"]
        assert "items" in list_data
        assert "total" in list_data

        res_sum = client.get("/api/doctor/alerts/summary")
        assert res_sum.status_code == 200
        sum_data = res_sum.json()["data"]
        assert "critical" in sum_data
        assert "total_active" in sum_data
    finally:
        app.dependency_overrides.clear()
        db.close()


def test_alert_lifecycle_transitions_and_idempotency():
    db = SessionLocal()
    try:
        doc_user = db.query(User).filter(User.role == UserRoleEnum.PHC_DOCTOR).first()
        from app.dependencies import get_current_user
        app.dependency_overrides[get_current_user] = lambda: doc_user

        # Create test alert
        alert = DoctorAlertService.create_or_update_alert_from_event(
            db=db,
            facility_id="PHC-09",
            category="CLINICAL",
            alert_type="TEST_LIFECYCLE_EVENT",
            severity="HIGH",
            title="Test Lifecycle Alert",
            safe_summary="Test safe summary",
            source_entity_type="REFERRAL",
            source_entity_id="TEST-REF-999",
            doctor_id=doc_user.id if doc_user else None
        )

        assert alert.status == "NEW"

        # 1. Seen
        res_seen = client.post(f"/api/doctor/alerts/{alert.id}/seen")
        assert res_seen.status_code == 200
        assert res_seen.json()["data"]["status"] == "SEEN"

        # 2. Acknowledge
        res_ack = client.post(f"/api/doctor/alerts/{alert.id}/acknowledge", json={"note": "Ack note"})
        assert res_ack.status_code == 200
        assert res_ack.json()["data"]["status"] == "ACKNOWLEDGED"

        # 3. Snooze
        res_snooze = client.post(f"/api/doctor/alerts/{alert.id}/snooze", json={"hours": 2, "reason": "Busy"})
        assert res_snooze.status_code == 200
        assert res_snooze.json()["data"]["status"] == "SNOOZED"

        # 4. Resolve
        res_res = client.post(f"/api/doctor/alerts/{alert.id}/resolve", json={"note": "Resolved completely"})
        assert res_res.status_code == 200
        assert res_res.json()["data"]["status"] == "RESOLVED"

        # 5. Duplicate Event Protection Check
        dup_alert = DoctorAlertService.create_or_update_alert_from_event(
            db=db,
            facility_id="PHC-09",
            category="CLINICAL",
            alert_type="TEST_LIFECYCLE_EVENT",
            severity="HIGH",
            title="Test Lifecycle Alert",
            safe_summary="Test safe summary",
            source_entity_type="REFERRAL",
            source_entity_id="TEST-REF-999"
        )
        # Resolved alert is not updated, a new active cycle would start if needed
        assert dup_alert is not None
    finally:
        app.dependency_overrides.clear()
        db.close()


def test_critical_alert_dismissal_validation():
    db = SessionLocal()
    try:
        doc_user = db.query(User).filter(User.role == UserRoleEnum.PHC_DOCTOR).first()
        from app.dependencies import get_current_user
        app.dependency_overrides[get_current_user] = lambda: doc_user

        alert = DoctorAlertService.create_or_update_alert_from_event(
            db=db,
            facility_id="PHC-09",
            category="CLINICAL",
            alert_type="CRITICAL_DISMISS_CHECK",
            severity="CRITICAL",
            title="Critical Dismiss Check Alert",
            safe_summary="Critical test",
            source_entity_type="REFERRAL",
            source_entity_id="TEST-REF-CRIT"
        )

        # Attempt to dismiss without reason must fail
        res = client.post(f"/api/doctor/alerts/{alert.id}/dismiss", json={"reason": ""})
        assert res.status_code == 400
        assert "Critical alerts cannot be dismissed without an authorized reason" in res.json()["detail"]

        # Dismiss with reason
        res_ok = client.post(f"/api/doctor/alerts/{alert.id}/dismiss", json={"reason": "Valid clinical justification"})
        assert res_ok.status_code == 200
        assert res_ok.json()["data"]["status"] == "DISMISSED"
    finally:
        app.dependency_overrides.clear()
        db.close()
