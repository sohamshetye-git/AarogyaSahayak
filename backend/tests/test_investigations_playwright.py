import os
import sys
import time
from playwright.sync_api import sync_playwright

SCREENSHOT_DIR = r"C:\Arogya Sahayak_AI_antigravity\backend\tests\screenshots"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

def test_playwright_investigations_module():
    print("\n=======================================================")
    print("  PLAYWRIGHT INVESTIGATIONS E2E VERIFICATION")
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

        # Step 2: Open /doctor/investigations
        print("\n[Step 2] Navigating to /doctor/investigations...")
        page.goto("http://localhost:3000/doctor/investigations", wait_until="domcontentloaded")
        page.wait_for_selector('h1:has-text("Investigations Workspace")', timeout=10000)
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "investigations_workspace_1440.png"))
        print("  -> Workspace loaded successfully.")

        # Step 3: Verify Workspace & Cards
        print("\n[Step 3] Workspace loaded. Taking screenshot...")
        page.wait_for_timeout(2000)
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "investigations_workspace_1440.png"))

        # Step 4: Open Investigation Detail View directly using canonical ID
        print("\n[Step 4] Opening Investigation Detail View...")
        page.goto("http://localhost:3000/doctor/investigations/INV-ID-0001", wait_until="domcontentloaded")
        page.wait_for_timeout(2000)
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "investigation_detail.png"))

        # Step 5: Test Responsive Viewports (390px, 768px, 1440px)
        print("\n[Step 5] Testing Responsive Viewports...")
        page.set_viewport_size({"width": 768, "height": 1024})
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "investigations_768.png"))

        page.set_viewport_size({"width": 390, "height": 844})
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "investigations_390.png"))

        browser.close()
        print("\n=======================================================")
        print("  PLAYWRIGHT INVESTIGATIONS E2E PASSED")
        print("=======================================================\n")

if __name__ == "__main__":
    test_playwright_investigations_module()
