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

def test_ai_dual_rag_e2e_journey(browser: Browser):
    context = browser.new_context()
    page = context.new_page()

    # 1. ASHA worker acknowledges and refers Sunita Devi
    page.goto(f"{FRONTEND_URL}/login")
    page.click("button:has-text('ASHA Worker')")
    expect(page.locator("text=Priority Tasks & Field Visits")).to_be_visible()

    page.click("text=Sunita Devi")
    expect(page.locator("button:has-text('Acknowledge Case')")).to_be_visible()
    page.locator("button:has-text('Acknowledge Case')").first.click()
    page.locator("button:has-text('Start Field Visit')").click()

    for _ in range(6):
        page.click("button:has-text('Next Step')")
    page.click("button:has-text('Submit Urgent PHC Referral')")
    expect(page.locator("text=Field Visit & PHC Referral Submitted!")).to_be_visible()

    # 2. Doctor logs in and inspects the urgent referral with Milvus evidence
    page.goto(f"{FRONTEND_URL}/login")
    page.click("button:has-text('PHC Doctor')")
    expect(page.locator("h1:has-text('Dashboard')")).to_be_visible()

    page.click("text=Review & Consult")
    expect(page.locator("h1:has-text('Sunita Devi')")).to_be_visible()

    # 2. Verify Clinical RAG Evidence section is populated
    expect(page.locator("text=Clinical RAG Evidence")).to_be_visible()
    expect(page.locator("text=ASHA Field Reference Manual - Maternal Danger Signs & High Risk Pregnancy Triage")).to_be_visible()
    expect(page.locator("text=Standard Treatment Workflow Reference - Hypertensive Disorders in Pregnancy")).to_be_visible()
    expect(page.locator("text=Match Score:").first).to_be_visible()

    # 3. Doctor signs clinical consultation with Labetalol prescription and follow-up
    page.click("button:has-text('Acknowledge Referral')")
    expect(page.locator("text=Doctor Acknowledged")).to_be_visible()

    page.click("button:has-text('Sign & Complete Clinical Consultation')")
    expect(page.locator("text=Consultation & Prescription Signed!")).to_be_visible()

    context.close()
