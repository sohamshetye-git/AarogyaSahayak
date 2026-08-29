import pytest
from playwright.sync_api import Page, expect

def test_doctor_patients_directory_and_record_journey(page: Page):
    # 1. Login as Dr. Abhinav Sharma
    page.goto("http://localhost:5173/login")
    page.wait_for_selector("input")
    
    # Fill login details
    inputs = page.locator("input")
    if inputs.count() >= 2:
        inputs.nth(0).fill("dr.sharma")
        inputs.nth(1).fill("demo123")
        page.click("button:has-text('Login')")
    
    # 2. Open /doctor/patients
    page.goto("http://localhost:5173/doctor/patients")
    page.wait_for_selector("h1:has-text('Patients Directory')")

    # 3. Verify Header & Metrics
    expect(page.locator("h1:has-text('Patients Directory')")).to_be_visible()
    expect(page.locator("text=Total PHC Patients")).to_be_visible()

    # 4. Search Pooja Jadhav
    search_input = page.locator("input[placeholder*='Search patient name']")
    search_input.fill("Pooja")
    page.click("button:has-text('Search')")

    # 5. Open Pooja Jadhav's Patient Record
    page.wait_for_selector("text=Pooja Jadhav")
    page.click("button:has-text('Open Patient Record')")

    # 6. Verify Patient Record Screen details
    page.wait_for_selector("h1:has-text('Pooja Jadhav')")
    expect(page.locator("text=MATERNAL TRACK")).to_be_visible()
    expect(page.locator("text=Assigned ASHA")).to_be_visible()
    expect(page.locator("text=Deterministic Next Required Action")).to_be_visible()

    # 7. Test Phone Call modal trigger
    page.click("button:has-text('Call Patient')")
    page.wait_for_selector("text=Secure Tele-Consult Call")
    page.click("button:has-text('Cancel')")

    # 8. Open Case Timeline
    page.click("button:has-text('View Full Timeline')")
    page.wait_for_url("**/doctor/cases/**/timeline**")

    # 9. Test browser back
    page.go_back()
    page.wait_for_selector("h1:has-text('Pooja Jadhav')")
