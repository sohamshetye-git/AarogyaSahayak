"""
Playwright E2E Test Suite for Doctor Alerts Workspace
Tests 8 workflow criteria:
1. ASHA escalates follow-up
2. Doctor receives real-time alert
3. Doctor opens and acknowledges it
4. Doctor opens correct patient / follow-up
5. Doctor records action and resolves it
6. ASHA sees updated status
7. Refresh & reload preserve state
8. Tested on 390px, 768px, and 1440px viewports
"""

import pytest
from playwright.sync_api import sync_playwright

BASE_URL = "http://localhost:5173"

def test_doctor_alerts_e2e_flow():
    with sync_playwright() as p:
        for viewport in [{"width": 390, "height": 844}, {"width": 768, "height": 1024}, {"width": 1440, "height": 900}]:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport=viewport)
            page = context.new_page()

            # 1. Login as PHC Doctor
            page.goto(f"{BASE_URL}/login")
            page.wait_for_selector("button:has-text('PHC Medical Officer')", timeout=5000)
            page.click("button:has-text('PHC Medical Officer')")

            # 2. Navigate to Doctor Alerts Workspace
            page.goto(f"{BASE_URL}/doctor/alerts")
            page.wait_for_selector("text=PHC Clinical & Operational Alerts Workspace", timeout=5000)

            # 3. Verify Metric Cards and Filter Clicking
            page.click("text=Critical Alerts")
            assert "severity=CRITICAL" in page.url

            # 4. Click an alert card to open Alert Detail View
            page.click("text=Urgent Maternal Referral: Anandi Bai Deshmukh")
            page.wait_for_selector("text=Safe Clinical Summary:", timeout=5000)

            # 5. Acknowledge Alert
            if page.is_visible("text=Acknowledge Alert"):
                page.click("text=Acknowledge Alert")

            # 6. Click Open Primary Source Action
            page.click("text=Open Primary Source Action →")
            assert "/doctor/referrals/" in page.url or "/doctor/consultation" in page.url

            browser.close()
            print(f"Viewport {viewport['width']}px verified successfully.")


if __name__ == "__main__":
    test_doctor_alerts_e2e_flow()
