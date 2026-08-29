"""
Playwright E2E Test Suite for Doctor Dashboard Today's Clinical Work Component
"""

import os
import sys
import time
from playwright.sync_api import sync_playwright

SCREENSHOT_DIR = r"C:\Arogya Sahayak_AI_antigravity\backend\tests\screenshots"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

def run_e2e_verification():
    print("\n=======================================================")
    print("  PLAYWRIGHT CLINICAL WORK E2E VERIFICATION STARTED")
    print("=======================================================")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        # Step 1: Login as Doctor
        print("\n[Step 1] Logging in as Doctor (dr.sharma)...")
        page.goto("http://localhost:3000/login", wait_until="networkidle")
        page.fill('input[placeholder*="username" i], input[type="text"]', "dr.sharma")
        page.fill('input[type="password"]', "demo123")
        page.click('button:has-text("Sign In"), button[type="submit"]')
        page.wait_for_url("**/doctor/dashboard", timeout=10000)
        page.wait_for_selector('[data-testid="clinical-work-row-ready-to-start"]', timeout=15000)
        print(f"  -> Logged in successfully: {page.url}")

        # Capture initial summary counts
        row_ready = page.locator('[data-testid="clinical-work-row-ready-to-start"]')
        row_in_prog = page.locator('[data-testid="clinical-work-row-in-progress"]')
        row_results = page.locator('[data-testid="clinical-work-row-results-ready"]')
        row_followups = page.locator('[data-testid="clinical-work-row-followups-to-review"]')

        ready_cnt_text = row_ready.locator('span').last.inner_text()
        in_prog_cnt_text = row_in_prog.locator('span').last.inner_text()
        results_cnt_text = row_results.locator('span').last.inner_text()
        followups_cnt_text = row_followups.locator('span').last.inner_text()

        print(f"  -> Dashboard Counts | Ready: {ready_cnt_text}, In Progress: {in_prog_cnt_text}, Results Ready: {results_cnt_text}, Followups: {followups_cnt_text}")

        # Step 2: Test Row 1 - Ready to Start Consultations
        print("\n[Step 2] Clicking 'Ready to Start Consultations' row...")
        row_ready.click()
        page.wait_for_url("**/doctor/consultations?status=READY_TO_START", timeout=5000)
        print(f"  -> Successfully navigated to: {page.url}")
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "clinical_work_ready_to_start.png"))

        # Back to Dashboard
        page.goto("http://localhost:3000/doctor/dashboard", wait_until="networkidle")
        page.wait_for_selector('[data-testid="clinical-work-row-in-progress"]', timeout=10000)

        # Step 3: Test Row 2 - Consultations in Progress
        print("\n[Step 3] Clicking 'Consultations in Progress' row...")
        page.locator('[data-testid="clinical-work-row-in-progress"]').click()
        page.wait_for_url("**/doctor/consultations?status=IN_CONSULTATION", timeout=5000)
        print(f"  -> Successfully navigated to: {page.url}")
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "clinical_work_in_progress.png"))

        # Back to Dashboard
        page.goto("http://localhost:3000/doctor/dashboard", wait_until="networkidle")
        page.wait_for_selector('[data-testid="clinical-work-row-results-ready"]', timeout=10000)

        # Step 4: Test Row 3 - Results Ready for Review
        print("\n[Step 4] Clicking 'Results Ready for Review' row...")
        page.locator('[data-testid="clinical-work-row-results-ready"]').click()
        page.wait_for_url("**/doctor/investigations?status=RESULT_AVAILABLE", timeout=5000)
        print(f"  -> Successfully navigated to: {page.url}")
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "clinical_work_results_ready.png"))

        # Back to Dashboard
        page.goto("http://localhost:3000/doctor/dashboard", wait_until="networkidle")
        page.wait_for_selector('[data-testid="clinical-work-row-followups-to-review"]', timeout=10000)

        # Step 5: Test Row 4 - ASHA Follow-ups to Review
        print("\n[Step 5] Clicking 'ASHA Follow-ups to Review' row...")
        page.locator('[data-testid="clinical-work-row-followups-to-review"]').click()
        page.wait_for_url("**/doctor/followups?status=REVIEW_REQUIRED", timeout=5000)
        print(f"  -> Successfully navigated to: {page.url}")
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "clinical_work_followups_to_review.png"))

        # Step 6: Test Responsive Viewports
        print("\n[Step 6] Testing Responsive Viewports for Today's Clinical Work...")
        page.goto("http://localhost:3000/doctor/dashboard", wait_until="networkidle")
        page.wait_for_selector('[data-testid="clinical-work-row-ready-to-start"]', timeout=10000)

        # Desktop 1440px
        page.set_viewport_size({"width": 1440, "height": 900})
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "clinical_work_1440.png"))
        print("  -> Saved screenshot: clinical_work_1440.png")

        # Tablet 768px
        page.set_viewport_size({"width": 768, "height": 1024})
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "clinical_work_768.png"))
        print("  -> Saved screenshot: clinical_work_768.png")

        # Mobile 390px
        page.set_viewport_size({"width": 390, "height": 844})
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "clinical_work_390.png"))
        print("  -> Saved screenshot: clinical_work_390.png")

        browser.close()

        print("\n=======================================================")
        print("  PLAYWRIGHT CLINICAL WORK E2E VERIFICATION PASSED")
        print("=======================================================\n")

if __name__ == "__main__":
    run_e2e_verification()
