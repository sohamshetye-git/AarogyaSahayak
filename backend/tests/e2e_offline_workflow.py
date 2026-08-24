import os
import pytest
from playwright.sync_api import Page, expect
from app.database import SessionLocal
from app.models import Case, CaseStatusEnum, AshaVisit, Referral, IdempotencyRecord

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
        db.query(IdempotencyRecord).delete()
        db.commit()
    db.close()

def test_asha_offline_workflow_run_twice(page: Page):
    # ==================== RUN 1 ====================
    # --- 1. ASHA Login (Online) ---
    page.goto(f"{FRONTEND_URL}/login")
    page.click("button:has-text('ASHA Worker')")
    expect(page.locator("h1:has-text('Dashboard')")).to_be_visible()
    
    # --- 2. Open Urgent Case ---
    page.click("text=Sunita Devi")
    expect(page.locator("button:has-text('Start Field Visit')")).to_be_visible()
    
    # --- 3. Acknowledge Case (Online) ---
    page.locator("button:has-text('Acknowledge Case')").first.click()
    page.wait_for_timeout(1000)
    
    # --- 4. Go offline (Simulate walking to the field) ---
    page.context.set_offline(True)
    page.locator("button:has-text('Start Field Visit')").click()
    
    # Step 1-6
    for _ in range(6):
        page.click("button:has-text('Next Step')")
    
    # Step 7: Submit Offline
    page.click("button:has-text('Submit Urgent PHC Referral')")
    expect(page.locator("text=Saved Offline")).to_be_visible()
    expect(page.locator("text=will automatically sync when connection is restored")).to_be_visible()
    
    # Navigate back to dashboard
    page.click("button:has-text('Back to Dashboard')")
    
    # --- 5. Go Online & Sync ---
    page.context.set_offline(False)
    page.wait_for_timeout(8000)
    
    # Verify DB state after Run 1
    db = SessionLocal()
    case = db.query(Case).filter(Case.id == "case-canonical-001").first()
    visit_count_1 = db.query(AshaVisit).filter(AshaVisit.case_id == case.id).count()
    idemp_count_1 = db.query(IdempotencyRecord).count()
    assert visit_count_1 == 1, f"Visit was not synced to database on run 1 (count: {visit_count_1})"
    assert idemp_count_1 >= 1, "Idempotency record not created on run 1"
    db.close()

    # ==================== RUN 2 (Verification of duplicate prevention) ====================
    # Re-trigger sync manually or visit offline screen
    page.goto(f"{FRONTEND_URL}/asha/offline")
    expect(page.locator("text=Offline Queue & IndexedDB Sync")).to_be_visible()
    
    sync_btn = page.locator("button:has-text('Sync Pending Records')")
    if sync_btn.is_visible():
        sync_btn.click()
        page.wait_for_timeout(3000)

    # Verify that NO duplicate visits or referrals were inserted into PostgreSQL
    db = SessionLocal()
    case = db.query(Case).filter(Case.id == "case-canonical-001").first()
    visit_count_2 = db.query(AshaVisit).filter(AshaVisit.case_id == case.id).count()
    referral_count_2 = db.query(Referral).filter(Referral.case_id == case.id).count()
    
    assert visit_count_2 == 1, f"Duplicate visits detected on second run! Count: {visit_count_2}"
    assert referral_count_2 <= 1, f"Duplicate referrals detected on second run! Count: {referral_count_2}"
    db.close()
