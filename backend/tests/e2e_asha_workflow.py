import os
import pytest
from playwright.sync_api import Page, expect
from app.database import SessionLocal
from app.models import Case, CaseStatusEnum, AshaVisit, Referral

# Constants
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

@pytest.fixture(autouse=True)
def reset_case_state():
    # Database safety: abort if not using a test database environment
    assert os.environ.get("APP_ENV") == "test", "Safety block: E2E tests must be run with APP_ENV=test"
    
    # Reset the canonical case to NEW and clean up its visits/referrals before each test
    db = SessionLocal()
    case = db.query(Case).filter(Case.id == "case-canonical-001").first()
    if case:
        case.status = CaseStatusEnum.NEW
        # Delete old visits and referrals to avoid UniqueViolation
        db.query(AshaVisit).filter(AshaVisit.case_id == case.id).delete()
        db.query(Referral).filter(Referral.case_id == case.id).delete()
        db.commit()
    db.close()

def test_asha_end_to_end_workflow(page: Page):
    # --- 1. ASHA Login ---
    page.goto(f"{FRONTEND_URL}/login")
    
    # Use the 1-click login button for ASHA
    page.click("button:has-text('ASHA Worker')")
    
    # Verify Dashboard loaded
    expect(page.locator("h1:has-text('Dashboard')")).to_be_visible()
    
    # --- 2. Open Urgent Case ---
    if page.locator("a:has-text('Review Urgent Case')").count() > 0:
        page.locator("a:has-text('Review Urgent Case')").first.click()
    else:
        page.locator("text=Sunita Devi").first.click()
    
    # --- 3. Acknowledge ---
    page.locator("button:has-text('Acknowledge Case')").first.click()
    
    # --- 4. Contact Citizen ---
    page.locator("button:has-text('Spoke to Citizen')").click()
    
    # --- 5. Start Visit ---
    page.click("button:has-text('Start Field Visit')")
    
    # Step 1: Confirm
    page.click("button:has-text('Next Step')")
    
    # Step 2: Consent
    page.click("button:has-text('Next Step')")
    
    # Step 3: Symptoms
    page.click("button:has-text('Next Step')")
    
    # Step 4: Vitals (pre-filled to 150/100 in the UI component)
    expect(page.locator("text=Pregnancy-related warning signs detected")).to_be_visible()
    page.click("button:has-text('Next Step')")
    
    # Step 5: Protocol Review
    page.click("button:has-text('Next Step')")
    
    # Step 6: ASHA Notes
    page.click("button:has-text('Next Step')")
    
    # Step 7: Select PHC & Send Referral
    page.click("button:has-text('Submit Urgent PHC Referral')")
    
    # Wait for completion success message
    expect(page.locator("text=Field Visit & PHC Referral Submitted!")).to_be_visible()
    page.click("button:has-text('Back to Dashboard')")
    
    # --- 8. Doctor Login ---
    # Logout first (Look for a logout button or avatar)
    logout_btn = page.locator("button:has-text('Logout')").first
    if logout_btn.is_visible():
        logout_btn.click()
    else:
        # Fallback if no visible logout, just go to login directly
        page.goto(f"{FRONTEND_URL}/login")
    
    # Doctor Login
    page.click("button:has-text('PHC Doctor')")
    
    # Verify Doctor Dashboard loaded
    expect(page.locator("h1:has-text('Dashboard')")).to_be_visible()
    
    # --- 9. Doctor Acknowledge ---
    # Find the referral card for Sunita Devi and open it
    page.click("text=Review & Consult")
    
    # Acknowledge the referral
    page.click("button:has-text('Acknowledge Referral')")
    
    # Wait for the status to update
    expect(page.locator("text=Doctor Acknowledged")).to_be_visible()
