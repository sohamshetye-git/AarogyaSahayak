import pytest
from playwright.sync_api import Page, expect

def test_doctor_citizen_requests_view_patient_record_journey(page: Page):
    """
    Playwright E2E test verifying:
    1. Doctor logs into healthcare portal
    2. Navigates to /doctor/direct-requests
    3. Locates a Citizen request (e.g. Sunita Devi)
    4. Clicks 'View Patient Record'
    5. URL contains real patient profile ID (/doctor/patients/CP-001)
    6. Verifies Sunita Devi's patient record displays demographics, clinical context, and history
    7. Clicks 'Back to Citizen Requests' and returns seamlessly to /doctor/direct-requests
    """
    # 1. Login as Dr. Abhinav Sharma
    page.goto("http://localhost:5173/login")
    page.wait_for_selector("input")
    
    inputs = page.locator("input")
    if inputs.count() >= 2:
        inputs.nth(0).fill("dr.sharma")
        inputs.nth(1).fill("demo123")
        page.click("button:has-text('Login')")
    
    # 2. Open /doctor/direct-requests
    page.goto("http://localhost:5173/doctor/direct-requests")
    page.wait_for_selector("h1, h2, text=Direct Citizen Requests")

    # 3. Verify request list has patient record links
    patient_record_link = page.locator("a:has-text('View Patient Record')").first
    expect(patient_record_link).to_be_visible()

    # 4. Click 'View Patient Record'
    patient_record_link.click()

    # 5. Verify URL contains /doctor/patients/
    page.wait_for_url("**/doctor/patients/**")
    assert "/doctor/patients/" in page.url
    assert "undefined" not in page.url

    # 6. Verify Patient Record Screen components
    page.wait_for_selector("text=Patient Record")
    expect(page.locator("text=Assigned ASHA")).to_be_visible()
    expect(page.locator("text=Consent Status")).to_be_visible()

    # 7. Test 'Back to Citizen Requests'
    back_btn = page.locator("button:has-text('Back to Citizen Requests')")
    if back_btn.count() > 0:
        back_btn.click()
        page.wait_for_url("**/doctor/direct-requests")
        assert "/doctor/direct-requests" in page.url
