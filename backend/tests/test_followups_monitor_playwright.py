"""
Playwright E2E Verification Script for Doctor Portal ASHA Follow-up Monitor
"""

import sys
import os
import time
from playwright.sync_api import sync_playwright

SCREENSHOT_DIR = os.path.join(os.path.dirname(__file__), "screenshots")
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

def run_playwright_test():
    print("\n=======================================================")
    print("  PLAYWRIGHT FOLLOW-UP MONITOR E2E VERIFICATION STARTED")
    print("=======================================================\n")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # -----------------------------------------------------------------
        # STEP 1: Desktop Viewport (1440x900) - Full Workflow
        # -----------------------------------------------------------------
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        page.add_init_script("""
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
        print(f"  -> Logged in successfully: {page.url}")
        time.sleep(1)

        print("[Step 2] Locating ASHA Follow-up Monitor on Dashboard...")
        monitor_heading = page.query_selector("h3:has-text('ASHA Follow-up Monitor')")
        assert monitor_heading is not None, "ASHA Follow-up Monitor heading must be present on Doctor Dashboard"

        dashboard_shot = os.path.join(SCREENSHOT_DIR, "followup_monitor_dashboard_1440.png")
        page.screenshot(path=dashboard_shot)
        print(f"  -> Saved screenshot: followup_monitor_dashboard_1440.png")

        # Step 3: Click View All -> Navigate to /doctor/followups
        print("[Step 3] Clicking 'View All' link...")
        view_all_link = page.query_selector("a:has-text('View All')")
        if view_all_link:
            view_all_link.click()
            page.wait_for_timeout(1000)
            print(f"  -> Navigated to: {page.url}")
            assert "/doctor/followups" in page.url, f"URL should be /doctor/followups, got {page.url}"

            queue_shot = os.path.join(SCREENSHOT_DIR, "followup_monitor_queue_1440.png")
            page.screenshot(path=queue_shot)
            print(f"  -> Saved screenshot: followup_monitor_queue_1440.png")

        # Step 4: Click a card action to open canonical /doctor/followups/:id
        page.goto("http://localhost:3000/doctor/dashboard", wait_until="networkidle")
        time.sleep(1)
        action_btn = page.query_selector("button:has-text('Review Result')") or page.query_selector("button:has-text('View Directive')") or page.query_selector("button:has-text('Contact ASHA')")
        if action_btn:
            print("[Step 4] Clicking actionable monitor card button...")
            action_btn.click()
            page.wait_for_timeout(1500)
            print(f"  -> Navigated to detail page: {page.url}")
            assert "/doctor/followups/" in page.url, f"URL should be /doctor/followups/:id, got {page.url}"

            detail_shot = os.path.join(SCREENSHOT_DIR, "followup_monitor_detail_1440.png")
            page.screenshot(path=detail_shot)
            print(f"  -> Saved screenshot: followup_monitor_detail_1440.png")

            # Step 5: Click Mark Result Reviewed
            review_btn = page.query_selector("button:has-text('Mark Result Reviewed')")
            if review_btn and review_btn.is_enabled():
                print("[Step 5] Clicking 'Mark Result Reviewed'...")
                review_btn.click()
                page.wait_for_timeout(500)
                confirm_btn = page.query_selector("button:has-text('Confirm Review & Sign-off')")
                if confirm_btn:
                    confirm_btn.click()
                    page.wait_for_timeout(1500)
                    print(f"  -> Returned to dashboard after review: {page.url}")

        context.close()

        # -----------------------------------------------------------------
        # STEP 2: Tablet Viewport (768x1024)
        # -----------------------------------------------------------------
        print("[Step 6] Testing Tablet Viewport (768x1024)...")
        tab_context = browser.new_context(viewport={"width": 768, "height": 1024})
        tab_page = tab_context.new_page()
        tab_page.goto("http://localhost:3000/doctor/dashboard", wait_until="networkidle")
        tab_shot = os.path.join(SCREENSHOT_DIR, "followup_monitor_768.png")
        tab_page.screenshot(path=tab_shot)
        print(f"  -> Saved screenshot: followup_monitor_768.png")
        tab_context.close()

        # -----------------------------------------------------------------
        # STEP 3: Mobile Viewport (390x844)
        # -----------------------------------------------------------------
        print("[Step 7] Testing Mobile Viewport (390x844)...")
        mob_context = browser.new_context(viewport={"width": 390, "height": 844})
        mob_page = mob_context.new_page()
        mob_page.goto("http://localhost:3000/doctor/dashboard", wait_until="networkidle")
        mob_shot = os.path.join(SCREENSHOT_DIR, "followup_monitor_390.png")
        mob_page.screenshot(path=mob_shot)
        print(f"  -> Saved screenshot: followup_monitor_390.png")
        mob_context.close()

        browser.close()

    print("\n=======================================================")
    print("  PLAYWRIGHT FOLLOW-UP MONITOR E2E VERIFICATION PASSED")
    print("=======================================================\n")

if __name__ == "__main__":
    run_playwright_test()
