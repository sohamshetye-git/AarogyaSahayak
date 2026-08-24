import os
import pytest
from playwright.sync_api import Browser, expect
from app.database import SessionLocal
from app.models import Case, CaseStatusEnum, AshaVisit, Referral, Consultation, Prescription, PrescriptionItem, TestOrder, FollowUp, IdempotencyRecord

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

@pytest.fixture(autouse=True)
def reset_case_state():
    assert os.environ.get("APP_ENV") == "test", "Safety block: E2E tests must run with APP_ENV=test"
    db = SessionLocal()
    case = db.query(Case).filter(Case.id == "case-canonical-001").first()
    if case:
        case.status = CaseStatusEnum.NEW
        db.query(AshaVisit).filter(AshaVisit.case_id == case.id).delete()
        db.query(Referral).filter(Referral.case_id == case.id).delete()
        
        consultations = db.query(Consultation).filter(Consultation.case_id == case.id).all()
        for c in consultations:
            for p in c.prescriptions:
                db.query(PrescriptionItem).filter(PrescriptionItem.prescription_id == p.id).delete()
            db.query(Prescription).filter(Prescription.consultation_id == c.id).delete()
            db.query(TestOrder).filter(TestOrder.consultation_id == c.id).delete()

        db.query(Consultation).filter(Consultation.case_id == case.id).delete()
        db.query(FollowUp).filter(FollowUp.case_id == case.id).delete()
        db.query(IdempotencyRecord).delete()
        db.commit()
    db.close()

def test_full_four_role_journey_mvc(browser: Browser):
    # Context 1: ASHA Worker
    asha_context = browser.new_context()
    asha_page = asha_context.new_page()

    # Context 2: PHC Doctor
    doctor_context = browser.new_context()
    doctor_page = doctor_context.new_page()

    # Context 3: District Admin
    admin_context = browser.new_context()
    admin_page = admin_context.new_page()

    # ================= 1. ASHA LOGIN & TRIAGE =================
    asha_page.goto(f"{FRONTEND_URL}/login")
    asha_page.click("button:has-text('ASHA Worker')")
    expect(asha_page.locator("text=Priority Tasks & Field Visits")).to_be_visible()

    # Acknowledge & Refer Sunita Devi
    asha_page.click("text=Sunita Devi")
    expect(asha_page.locator("button:has-text('Acknowledge Case')")).to_be_visible()
    asha_page.locator("button:has-text('Acknowledge Case')").first.click()
    asha_page.locator("button:has-text('Start Field Visit')").click()

    for _ in range(6):
        asha_page.click("button:has-text('Next Step')")
    asha_page.click("button:has-text('Submit Urgent PHC Referral')")
    expect(asha_page.locator("text=Field Visit & PHC Referral Submitted!")).to_be_visible()
    asha_page.click("button:has-text('Back to Dashboard')")

    # ================= 2. DOCTOR LOGIN & CONSULTATION =================
    doctor_page.goto(f"{FRONTEND_URL}/login")
    doctor_page.click("button:has-text('PHC Doctor')")
    expect(doctor_page.locator("h1:has-text('Dashboard')")).to_be_visible()

    doctor_page.click("text=Review & Consult")
    doctor_page.click("button:has-text('Acknowledge Referral')")
    expect(doctor_page.locator("text=Doctor Acknowledged")).to_be_visible()

    # Doctor signs consultation with diagnosis & follow-up
    doctor_page.click("button:has-text('Sign & Complete Clinical Consultation')")
    expect(doctor_page.locator("text=Consultation & Prescription Signed!")).to_be_visible()

    # ================= 3. ASHA COMPLETES FOLLOW-UP =================
    asha_page.goto(f"{FRONTEND_URL}/asha/followups")
    expect(asha_page.locator("text=Doctor-Assigned Follow-up Tasks")).to_be_visible()

    # ================= 4. DISTRICT ADMIN AGGREGATE DASHBOARD =================
    admin_page.goto(f"{FRONTEND_URL}/login")
    admin_page.click("button:has-text('District Health Officer (Admin)')")
    expect(admin_page.locator("text=Privacy-Preserving Aggregate Mode Active")).to_be_visible()
    expect(admin_page.locator("text=Total District Cases")).to_be_visible()

    # Check Referral Analytics Screen
    admin_page.goto(f"{FRONTEND_URL}/admin/referrals")
    expect(admin_page.locator("text=Facility Referral & Response Analytics")).to_be_visible()

    # Check System Health Diagnostics
    admin_page.goto(f"{FRONTEND_URL}/admin/system-health")
    expect(admin_page.locator("text=Integration Diagnostics & Service Health")).to_be_visible()

    asha_context.close()
    doctor_context.close()
    admin_context.close()
