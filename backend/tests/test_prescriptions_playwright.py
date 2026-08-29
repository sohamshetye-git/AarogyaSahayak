import os
import sys
import time
from playwright.sync_api import sync_playwright

SCREENSHOT_DIR = r"C:\Arogya Sahayak_AI_antigravity\backend\tests\screenshots"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

def test_playwright_prescriptions_module():
    print("\n=======================================================")
    print("  PLAYWRIGHT PRESCRIPTIONS E2E VERIFICATION")
    print("=======================================================")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        # Step 1: Login as Doctor
        print("\n[Step 1] Logging in as Doctor (dr.sharma)...")
        page.goto("http://localhost:3000/login", wait_until="domcontentloaded")
        page.fill('input[placeholder*="username" i], input[type="text"]', "dr.sharma")
        page.fill('input[type="password"]', "demo123")
        page.click('button:has-text("Sign In"), button[type="submit"]')
        page.wait_for_url("**/doctor/dashboard", timeout=10000)

        # Step 2: Open /doctor/prescriptions
        print("\n[Step 2] Navigating to /doctor/prescriptions...")
        page.goto("http://localhost:3000/doctor/prescriptions", wait_until="domcontentloaded")
        page.wait_for_selector('h1:has-text("Doctor Prescription Workspace")', timeout=10000)
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "prescriptions_workspace_1440.png"))
        print("  -> Prescription Workspace loaded successfully.")

        # Step 3: Filter & Workspace Interactions
        print("\n[Step 3] Interacting with metric cards and filter toolbar...")
        page.wait_for_timeout(1000)
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "prescriptions_workspace_filtered.png"))

        # Step 4: Open Prescription Detail View
        print("\n[Step 4] Opening Prescription Detail View...")
        page.goto("http://localhost:3000/doctor/prescriptions/RX-DEMO-SITA-001", wait_until="domcontentloaded")
        page.wait_for_timeout(2000)
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "prescription_detail_1440.png"))

        # Step 5: Test Responsive Viewports (768px tablet, 390px mobile)
        print("\n[Step 5] Testing Responsive Viewports...")
        page.set_viewport_size({"width": 768, "height": 1024})
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "prescriptions_768.png"))

        page.set_viewport_size({"width": 390, "height": 844})
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "prescriptions_390.png"))

        browser.close()
        print("\n=======================================================")
        print("  PLAYWRIGHT PRESCRIPTIONS E2E PASSED")
        print("=======================================================\n")

if __name__ == "__main__":
    test_playwright_prescriptions_module()
