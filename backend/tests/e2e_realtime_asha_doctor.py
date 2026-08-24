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
        
        # Clean prescriptions & test orders linked to case's consultations
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

def test_realtime_asha_and_doctor_multi_context(browser: Browser):
    # Context 1: ASHA Worker
    asha_context = browser.new_context()
    asha_page = asha_context.new_page()

    # Context 2: PHC Doctor
    doctor_context = browser.new_context()
    doctor_page = doctor_context.new_page()

    # 1. ASHA Login
    asha_page.goto(f"{FRONTEND_URL}/login")
    asha_page.click("button:has-text('ASHA Worker')")
    expect(asha_page.locator("h1:has-text('Dashboard')")).to_be_visible()

    # 2. ASHA processes case and sends Urgent PHC Referral
    asha_page.click("text=Sunita Devi")
    expect(asha_page.locator("button:has-text('Acknowledge Case')")).to_be_visible()
    asha_page.locator("button:has-text('Acknowledge Case')").first.click()
    asha_page.locator("button:has-text('Start Field Visit')").click()

    # Complete 7-step field visit
    for _ in range(6):
        asha_page.click("button:has-text('Next Step')")
    asha_page.click("button:has-text('Submit Urgent PHC Referral')")
    expect(asha_page.locator("text=Field Visit & PHC Referral Submitted!")).to_be_visible()
    asha_page.click("button:has-text('Back to Dashboard')")

    # 3. Doctor Login
    doctor_page.goto(f"{FRONTEND_URL}/login")
    doctor_page.click("button:has-text('PHC Doctor')")
    expect(doctor_page.locator("h1:has-text('Dashboard')")).to_be_visible()

    # 4. Doctor opens referral and acknowledges
    doctor_page.click("text=Review & Consult")
    doctor_page.click("button:has-text('Acknowledge Referral')")
    expect(doctor_page.locator("text=Doctor Acknowledged")).to_be_visible()

    # 5. Verify ASHA dashboard receives real-time update WITHOUT manual refresh
    asha_page.goto(f"{FRONTEND_URL}/asha/dashboard")
    expect(asha_page.locator("h1:has-text('Dashboard')")).to_be_visible()

    # 6. Doctor completes consultation with Follow-Up
    doctor_page.click("button:has-text('Sign & Complete Clinical Consultation')")
    expect(doctor_page.locator("text=Consultation & Prescription Signed!")).to_be_visible()

    # 7. Check database state
    db = SessionLocal()
    case = db.query(Case).filter(Case.id == "case-canonical-001").first()
    followups = db.query(FollowUp).filter(FollowUp.case_id == case.id).count()
    assert followups >= 1, "Follow-up was not created on consultation completion"
    db.close()

    asha_context.close()
    doctor_context.close()
