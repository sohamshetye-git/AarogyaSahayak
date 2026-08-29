"""
Playwright E2E Verification Script for Doctor ASHA Follow-ups Workspace
"""

import sys
import os
import time
from playwright.sync_api import sync_playwright

SCREENSHOT_DIR = os.path.join(os.path.dirname(__file__), "screenshots")
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

def run_playwright_test():
    print("\n=======================================================")
    print("  PLAYWRIGHT ASHA FOLLOW-UPS WORKSPACE E2E VERIFICATION ")
    print("=======================================================\n")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # -----------------------------------------------------------------
        # STEP 1: Desktop Viewport (1440x900) - Doctor Login & Sidebar Nav
        # -----------------------------------------------------------------
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        page.add_init_script("""
            localStorage.setItem('aarogya_token', 'mock-doctor-token');
            localStorage.setItem('auth_token', 'mock-doctor-token');
            localStorage.setItem('aarogya_user', JSON.stringify({
                id: 'DOC-007',
                name: 'Dr. Abhinav Sharma',
                role: 'PHC_DOCTOR',
                username: 'dr.sharma'
            }));
        """)

        print("[Step 1] Logging in as Doctor (dr.sharma)...")
        page.goto("http://localhost:3000/doctor/dashboard", wait_until="networkidle")
        time.sleep(1)

        print("[Step 2] Clicking Doctor sidebar 'ASHA Follow-ups' link...")
        followups_link = page.query_selector("a:has-text('ASHA Follow-ups')")
        assert followups_link is not None, "ASHA Follow-ups sidebar link must exist"
        followups_link.click()
        page.wait_for_timeout(1000)

        print(f"  -> Current URL: {page.url}")
        assert "/doctor/followups" in page.url, f"Expected URL /doctor/followups, got {page.url}"

        print("[Step 3] Asserting heading and verifying Referral Queue is NOT rendered...")
        heading = page.query_selector("h2:has-text('ASHA Follow-up Review Workspace')")
        assert heading is not None, "Workspace heading 'ASHA Follow-up Review Workspace' must exist"

        ref_queue_heading = page.query_selector("h2:has-text('PHC Referral Queue')")
        assert ref_queue_heading is None, "Referral Queue heading MUST NOT be rendered on /doctor/followups"

        dash_shot = os.path.join(SCREENSHOT_DIR, "followups_workspace_1440.png")
        page.screenshot(path=dash_shot)
        print("  -> Saved screenshot: followups_workspace_1440.png")

        print("[Step 4] Clicking 'All Records' tab and opening follow-up detail using followUpId...")
        all_tab = page.query_selector("button:has-text('All Records')")
        if all_tab:
            all_tab.click()
            page.wait_for_timeout(1500)

        buttons = page.query_selector_all("button")
        safe_texts = [b.inner_text().encode('ascii', 'ignore').decode('ascii') for b in buttons]
        print(f"  -> Total buttons found: {len(buttons)}. Texts: {safe_texts[:10]}")

        detail_btn = page.query_selector("button[data-testid^='fup-review-detail-btn-']")
        assert detail_btn is not None, f"Follow-up detail button must exist on page. Found buttons: {safe_texts}"
        detail_btn.click()
        page.wait_for_timeout(1000)

        print(f"  -> Navigated to detail URL: {page.url}")
        assert "/doctor/followups/" in page.url, f"Expected /doctor/followups/:followUpId, got {page.url}"

        detail_shot = os.path.join(SCREENSHOT_DIR, "followup_detail_1440.png")
        page.screenshot(path=detail_shot)
        print("  -> Saved screenshot: followup_detail_1440.png")

        # Step 5: Test Route Ownership across all Doctor Sidebar Links
        print("[Step 5] Testing Route Ownership across Doctor Sidebar Links...")
        sidebar_routes = [
          ("/doctor/dashboard", "PHC Doctor Dashboard"),
          ("/doctor/referrals", "Referral Queue"),
          ("/doctor/consultations", "Consultation Workspace"),
          ("/doctor/followups", "ASHA Follow-up Review Workspace"),
          ("/doctor/activity", "Recent Care Activity")
        ]

        for path, expected_text in sidebar_routes:
            page.goto(f"http://localhost:3000{path}", wait_until="networkidle")
            page.wait_for_timeout(500)
            elem = page.query_selector(f"*:has-text('{expected_text}')")
            assert elem is not None, f"Path {path} must render unique page with text '{expected_text}'"
            print(f"  -> Verified route ownership for {path}: rendered '{expected_text}'")

        context.close()

        # -----------------------------------------------------------------
        # STEP 2: Tablet Viewport (768x1024)
        # -----------------------------------------------------------------
        print("[Step 6] Testing Tablet Viewport (768x1024)...")
        tab_context = browser.new_context(viewport={"width": 768, "height": 1024})
        tab_page = tab_context.new_page()
        tab_page.goto("http://localhost:3000/doctor/followups", wait_until="networkidle")
        tab_shot = os.path.join(SCREENSHOT_DIR, "followups_workspace_768.png")
        tab_page.screenshot(path=tab_shot)
        print("  -> Saved screenshot: followups_workspace_768.png")
        tab_context.close()

        # -----------------------------------------------------------------
        # STEP 3: Mobile Viewport (390x844)
        # -----------------------------------------------------------------
        print("[Step 7] Testing Mobile Viewport (390x844)...")
        mob_context = browser.new_context(viewport={"width": 390, "height": 844})
        mob_page = mob_context.new_page()
        mob_page.goto("http://localhost:3000/doctor/followups", wait_until="networkidle")
        mob_shot = os.path.join(SCREENSHOT_DIR, "followups_workspace_390.png")
        mob_page.screenshot(path=mob_shot)
        print("  -> Saved screenshot: followups_workspace_390.png")
        mob_context.close()

        browser.close()

    print("\n=======================================================")
    print("  PLAYWRIGHT ASHA FOLLOW-UPS WORKSPACE E2E VERIFICATION PASSED")
    print("=======================================================\n")

if __name__ == "__main__":
    run_playwright_test()
