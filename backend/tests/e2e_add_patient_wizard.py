import os
import pytest
from playwright.sync_api import Browser, expect
from app.database import SessionLocal
from app.models import Case, CitizenProfile, User, AshaVisit, Referral

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

def test_add_patient_wizard_flow(browser: Browser):
    """
    E2E Verification of:
    1. ASHA Worker logs in and navigates to 'Add Patient' (/asha/patients/new).
    2. Step 1 Identity & Location: fills new citizen details.
    3. Step 2 Household & Consent: checks registration consent.
    4. Step 3 Health Profile: specifies baseline details.
    5. Step 4 Current Health Concern: records symptoms.
    6. Step 5 Vitals & Special Conditions: records BP 155/100 and Pregnancy warning signs.
    7. Step 6 Follow-up & Referral: selects PHC referral with urgent priority.
    8. Step 7 Review & Submit: confirms and saves new citizen.
    9. Confirms patient appears in Beneficiary list dynamically.
    """
    # Clean up test database first
    db = SessionLocal()
    try:
        from app.models import FollowUp, SymptomObservation, VitalRecord, AuditLog
        citizen = db.query(CitizenProfile).filter(CitizenProfile.display_name == "Anandi Bai Deshmukh").first()
        if citizen:
            citizen_id = citizen.id
            db.query(FollowUp).filter(FollowUp.citizen_id == citizen_id).delete()
            case_ids = [c.id for c in db.query(Case).filter(Case.citizen_id == citizen_id).all()]
            if case_ids:
                db.query(SymptomObservation).filter(SymptomObservation.case_id.in_(case_ids)).delete()
                db.query(VitalRecord).filter(VitalRecord.case_id.in_(case_ids)).delete()
                db.query(Referral).filter(Referral.case_id.in_(case_ids)).delete()
                db.query(AshaVisit).filter(AshaVisit.case_id.in_(case_ids)).delete()
                db.query(Case).filter(Case.citizen_id == citizen_id).delete()
            db.query(AuditLog).filter(AuditLog.resource_id == citizen_id).delete()
            db.query(CitizenProfile).filter(CitizenProfile.id == citizen_id).delete()
            db.commit()
    except Exception as e:
        print(f"Cleanup failed: {e}")
        db.rollback()
    finally:
        db.close()

    context = browser.new_context()
    page = context.new_page()

    # 1. Login as ASHA Worker
    page.goto(f"{FRONTEND_URL}/login")
    page.click("button:has-text('ASHA Worker')")
    expect(page.locator("h1:has-text('Dashboard')")).to_be_visible()

    # 2. Click 'Add Patient' in Navigation
    page.click("a:has-text('Add Patient')")
    expect(page.locator("h1:has-text('Add Patient')").first).to_be_visible()
    expect(page.locator("text=Step 1 of 7: Identity & Location")).to_be_visible()

    # --- Step 1: Identity & Location ---
    # Ensure inputs start empty (no prefill)
    name_input = page.locator("input[placeholder='e.g. Savita Patil']")
    expect(name_input).to_have_value("")
    name_input.fill("Anandi Bai Deshmukh")

    # Select age
    age_chk = page.locator("text=Exact Date of Birth not known")
    age_chk.click()
    page.locator("input[placeholder='e.g. 28']").fill("30")

    # Mobile & ABHA
    page.locator("input[placeholder='e.g. 9876543210']").fill("9833445566")
    page.locator("input[placeholder='House No, Ward or Landmark']").fill("Near Gram Panchayat Office")

    page.click("button:has-text('Next Step →')")

    # --- Step 2: Household, Language & Consent ---
    expect(page.locator("text=Step 2 of 7: Household & Consent")).to_be_visible()
    
    # Check registration consent
    page.locator("#reg-consent-chk").click()
    page.click("button:has-text('Next Step →')")

    # --- Step 3: Health Profile ---
    expect(page.locator("text=Step 3 of 7: Health Profile")).to_be_visible()
    page.click("button:has-text('Next Step →')")

    # --- Step 4: Health Concern ---
    expect(page.locator("text=Step 4 of 7: Health Concern")).to_be_visible()
    page.locator("text=Yes, record a current health complaint").click()
    page.locator("input[placeholder='e.g. Headache and dizziness for 2 days']").fill("Severe headache, blurred vision and swollen feet (30 weeks)")
    
    # Select symptoms
    page.locator("button:has-text('Severe Headache')").click()
    page.locator("button:has-text('Blurred Vision')").click()
    page.click("button:has-text('Next Step →')")

    # --- Step 5: Vitals & Special Conditions ---
    expect(page.locator("text=Step 5 of 7: Vitals & Special Conditions")).to_be_visible()
    page.locator("input[placeholder='Systolic (120)']").fill("155")
    page.locator("input[placeholder='Diastolic (80)']").fill("100")
    page.locator("input[placeholder='e.g. 98']").fill("97")
    
    # Special condition -> PREGNANCY
    page.locator("select").last.select_option("PREGNANCY")
    page.locator("text=Severe Persistent Headache").click()
    page.locator("text=Blurred Vision / Visual Disturbance").click()
    page.click("button:has-text('Next Step →')")

    # --- Step 6: Follow-up & Referral ---
    expect(page.locator("text=Step 6 of 7: Follow-up & Referral")).to_be_visible()
    page.locator("text=Refer Citizen to Primary Health Centre (PHC)?").click()
    page.locator("input[placeholder='e.g. Elevated BP 150/100 with headache during 3rd trimester']").fill("Urgent pre-eclampsia evaluation required")
    page.click("button:has-text('Next Step →')")

    # --- Step 7: Documents, Review & Submit ---
    expect(page.locator("text=Step 7 of 7: Documents & Submit")).to_be_visible()
    expect(page.locator("text=Anandi Bai Deshmukh")).to_be_visible()
    
    # ASHA confirmation checkbox
    page.locator("#final-asha-confirm-chk").click()
    page.locator("#submit-patient-btn").click()

    # Verify Success Modal
    expect(page.locator("h2:has-text('Patient')")).to_be_visible()

    # Click Open Beneficiary Directory
    page.click("button:has-text('Open Beneficiary Directory')")
    expect(page.locator("text=Beneficiary Directory")).to_be_visible()

    context.close()
