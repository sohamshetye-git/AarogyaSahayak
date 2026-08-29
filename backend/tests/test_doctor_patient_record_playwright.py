"""
Playwright E2E Test Suite for Doctor Patient Record Action and Longitudinal Patient Record View
"""

import os
import sys
import time
from playwright.sync_api import sync_playwright

SCREENSHOT_DIR = r"C:\Arogya Sahayak_AI_antigravity\backend\tests\screenshots"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

def run_patient_record_e2e_verification():
    print("\n=======================================================")
    print("  PLAYWRIGHT PATIENT RECORD ACTION & VIEW E2E STARTED")
    print("=======================================================")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # 1. Desktop 1440px Verification
        print("\n[Step 1] Testing 1440px Desktop View...")
        context_desktop = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context_desktop.new_page()

        # Login as Dr. Abhinav Sharma
        page.goto("http://localhost:3000/login", wait_until="networkidle")
        page.fill('input[placeholder*="username" i], input[type="text"]', "dr.sharma")
        page.fill('input[type="password"]', "demo123")
        page.click('button:has-text("Sign In"), button[type="submit"]')
        page.wait_for_url("**/doctor/dashboard", timeout=10000)
        print("  -> Logged in as Dr. Abhinav Sharma")

        # Navigate directly to Pooja's Consultation or Patient Record
        page.goto("http://localhost:3000/doctor/consultations/case-routine-002", wait_until="networkidle")
        page.wait_for_selector('button:has-text("View Patient Record")', timeout=10000)
        print("  -> Loaded Doctor Consultation Screen")

        # Click View Patient Record
        page.click('button:has-text("View Patient Record")')
        page.wait_for_url("**/doctor/patients/*", timeout=10000)
        print(f"  -> Navigated to Patient Record URL: {page.url}")
        assert "/doctor/patients/CP-003" in page.url or "/doctor/patients/" in page.url

        # Assert Header details
        page.wait_for_selector('h1:has-text("Pooja Jadhav")', timeout=10000)
        assert page.locator('h1:has-text("Pooja Jadhav")').is_visible()
        print("  -> Verified Patient Name: Pooja Jadhav")

        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "doctor_patient_record_1440.png"))

        # Test Tab switching: Vitals & Trends
        page.click('button:has-text("Vitals & Trends")')
        page.wait_for_selector('h3:has-text("Longitudinal Vitals")', timeout=5000)
        print("  -> Switched tab to Vitals & Trends")

        # Test Tab switching: Signed Prescriptions
        page.click('button:has-text("Signed Prescriptions")')
        page.wait_for_selector('h3:has-text("Doctor-Signed Prescriptions")', timeout=5000)
        print("  -> Switched tab to Signed Prescriptions")

        # Test Back to Consultation
        page.click('button:has-text("Back to Active Consultation"), button:has-text("Back")')
        page.wait_for_url("**/doctor/consultations/*", timeout=10000)
        print(f"  -> Successfully returned to Consultation URL: {page.url}")

        context_desktop.close()

        # 2. Mobile 390px Verification
        print("\n[Step 2] Testing 390px Mobile View...")
        context_mobile = browser.new_context(viewport={"width": 390, "height": 844})
        page_m = context_mobile.new_page()

        page_m.goto("http://localhost:3000/login", wait_until="networkidle")
        page_m.fill('input[placeholder*="username" i], input[type="text"]', "dr.sharma")
        page_m.fill('input[type="password"]', "demo123")
        page_m.click('button:has-text("Sign In"), button[type="submit"]')
        page_m.wait_for_url("**/doctor/dashboard", timeout=10000)

        page_m.goto("http://localhost:3000/doctor/patients/CP-003", wait_until="networkidle")
        page_m.wait_for_selector('h1:has-text("Pooja Jadhav")', timeout=10000)
        print("  -> Mobile view loaded successfully")
        page_m.screenshot(path=os.path.join(SCREENSHOT_DIR, "doctor_patient_record_mobile.png"))

        context_mobile.close()
        browser.close()

    print("\n=======================================================")
    print("  PLAYWRIGHT PATIENT RECORD E2E PASSED PERFECTLY!")
    print("=======================================================\n")

if __name__ == "__main__":
    run_patient_record_e2e_verification()
