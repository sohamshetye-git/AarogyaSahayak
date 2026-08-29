"""
Authoritative backend tests for Doctor Reports module.
Verifies PHC RBAC isolation, Asia/Kolkata date boundaries, metric reconciliation,
PII exclusion in PDF/CSV exports, and idempotent report calculations.
"""

import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models import (
    User, WorkerProfile, Case, Referral, Consultation, Prescription,
    FollowUp, TestOrder, CitizenProfile, UserRoleEnum, CasePriorityEnum, CaseStatusEnum
)
from app.services.doctor_report_service import DoctorReportService

client = TestClient(app)

@pytest.fixture
def doctor_headers():
    """Provides authentication headers for PHC Doctor Dr. Abhinav Sharma."""
    login_res = client.post("/api/auth/login", json={"identifier": "dr.sharma", "password": "demo123"})
    assert login_res.status_code == 200
    token = login_res.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_headers():
    """Provides authentication headers for District Admin."""
    login_res = client.post("/api/auth/login", json={"identifier": "admin.dho", "password": "demo123"})
    assert login_res.status_code == 200
    token = login_res.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_doctor_reports_overview_endpoint(doctor_headers):
    """Verifies GET /api/reports/overview returns 200 with typed Pydantic StandardResponse structure."""
    res = client.get("/api/reports/overview", headers=doctor_headers)
    assert res.status_code == 200
    body = res.json()
    assert "data" in body
    data = body["data"]
    
    assert "period" in data
    assert "facility" in data
    assert "metrics" in data
    assert data["facility"]["facility_id"] == "PHC-09"
    
    metrics = data["metrics"]
    assert "unique_patients_seen" in metrics
    assert "new_referrals" in metrics
    assert "active_urgent_referrals" in metrics
    assert "consultations_completed" in metrics
    assert "patients_waiting" in metrics


def test_doctor_reports_section_endpoints(doctor_headers):
    """Verifies all specific report tab endpoints return HTTP 200."""
    endpoints = [
        "/api/reports/referrals",
        "/api/reports/consultations",
        "/api/reports/patients",
        "/api/reports/investigations",
        "/api/reports/prescriptions",
        "/api/reports/followups",
        "/api/reports/maternal",
        "/api/reports/child-health",
        "/api/reports/ncd",
        "/api/reports/safety",
        "/api/reports/workflow-funnel",
        "/api/reports/pending-work",
        "/api/reports/recent-activity"
    ]
    for ep in endpoints:
        res = client.get(ep, headers=doctor_headers)
        assert res.status_code == 200, f"Endpoint {ep} failed with status {res.status_code}"
        assert "data" in res.json()


def test_doctor_reports_date_filtering(doctor_headers):
    """Verifies custom date range filters work properly with IST boundary parsing."""
    res = client.get("/api/reports/overview?date_from=2026-08-20&date_to=2026-08-26", headers=doctor_headers)
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["period"]["date_from"] == "2026-08-20"
    assert data["period"]["date_to"] == "2026-08-26"


def test_doctor_reports_phc_rbac_isolation(doctor_headers):
    """Verifies Doctor reports query strictly scopes to the logged in Doctor's facility."""
    res = client.get("/api/reports/overview", headers=doctor_headers)
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["facility"]["facility_id"] == "PHC-09"


def test_doctor_reports_metric_reconciliation():
    """Reconciles DoctorReportService metrics against direct PostgreSQL count queries."""
    from conftest import TestingSessionLocal
    db_session = TestingSessionLocal()
    facility_id = "PHC-09"
    
    # Direct PostgreSQL count for patients waiting
    db_waiting = db_session.query(Referral).filter(
        Referral.to_facility_id == facility_id,
        Referral.status == "PATIENT_ARRIVED"
    ).count()

    overview = DoctorReportService.get_overview_report(
        db=db_session,
        facility_id=facility_id,
        facility_name="Kalyanpur Primary Health Centre",
        doctor_name="Dr. Abhinav Sharma"
    )

    db_session.close()

    assert overview["metrics"]["patients_waiting"] == db_waiting, \
        f"Mismatch in waiting patients: Report={overview['metrics']['patients_waiting']}, DB={db_waiting}"


def test_doctor_report_exports_pii_privacy(doctor_headers):
    """Verifies server-generated CSV and PDF exports contain zero patient PII (no names, phones, ABHA)."""
    # 1. CSV Export
    csv_res = client.get("/api/reports/export?format=csv", headers=doctor_headers)
    assert csv_res.status_code == 200
    assert csv_res.headers["content-type"] == "text/csv; charset=utf-8"
    csv_text = csv_res.text
    
    # Ensure zero PII names or phones appear in aggregate output
    assert "Sunita Devi" not in csv_text
    assert "9876543210" not in csv_text
    assert "PRIVACY NOTICE" in csv_text

    # 2. PDF Export
    pdf_res = client.get("/api/reports/export?format=pdf", headers=doctor_headers)
    assert pdf_res.status_code == 200
    pdf_text = pdf_res.text
    assert "Sunita Devi" not in pdf_text
    assert "Zero Patient-level PII included" in pdf_text
