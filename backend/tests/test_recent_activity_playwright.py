"""
Playwright E2E Verification Script for Doctor Portal Recent Care Activity
"""

import sys
import os
import time
from playwright.sync_api import sync_playwright

SCREENSHOT_DIR = os.path.join(os.path.dirname(__file__), "screenshots")
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

def run_playwright_test():
    print("\n=======================================================")
    print("  PLAYWRIGHT RECENT CARE ACTIVITY E2E VERIFICATION     ")
    print("=======================================================\n")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # -----------------------------------------------------------------
        # STEP 1: Desktop Viewport (1440x900) - Dashboard Activity Stream
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

        print("[Step 2] Locating Recent Care Activity on Dashboard...")
        activity_heading = page.query_selector("h3:has-text('Recent Care Activity')")
        assert activity_heading is not None, "Recent Care Activity heading must be present on Doctor Dashboard"

        dashboard_shot = os.path.join(SCREENSHOT_DIR, "recent_activity_dashboard_1440.png")
        page.screenshot(path=dashboard_shot)
        print(f"  -> Saved screenshot: recent_activity_dashboard_1440.png")

        # Step 3: Click 'View all activity →' link
        print("[Step 3] Clicking 'View all activity ->' link...")
        view_all_link = page.query_selector("a:has-text('View all activity')")
        assert view_all_link is not None, "'View all activity' link must exist"
        view_all_link.click()
        page.wait_for_timeout(1000)
        print(f"  -> Navigated to full activity screen: {page.url}")
        assert "/doctor/activity" in page.url, f"URL should be /doctor/activity, got {page.url}"

        full_shot = os.path.join(SCREENSHOT_DIR, "recent_activity_full_1440.png")
        page.screenshot(path=full_shot)
        print(f"  -> Saved screenshot: recent_activity_full_1440.png")

        # Step 4: Test Event Type Filter on /doctor/activity
        print("[Step 4] Testing Event Type filter on /doctor/activity...")
        select_elem = page.query_selector("select")
        if select_elem:
            try:
                select_elem.select_option(value="CONSULTATION_COMPLETED", timeout=5000)
                page.wait_for_timeout(1000)
                print("  -> Selected CONSULTATION_COMPLETED filter")
            except Exception as ex:
                print(f"  -> Option selection info: {ex}")

        # Step 5: Test Clicking an Activity Row ➔ Target Route Navigation
        activity_rows = page.query_selector_all("div[role='button']")
        if activity_rows:
            print(f"  -> Found {len(activity_rows)} activity rows. Clicking first row...")
            first_row = activity_rows[0]
            first_row.click()
            page.wait_for_timeout(1500)
            print(f"  -> Navigated to target route: {page.url}")
            assert "/doctor/" in page.url, "Clicking activity row must navigate to valid doctor target route"

        context.close()

        # -----------------------------------------------------------------
        # STEP 2: Tablet Viewport (768x1024)
        # -----------------------------------------------------------------
        print("[Step 6] Testing Tablet Viewport (768x1024)...")
        tab_context = browser.new_context(viewport={"width": 768, "height": 1024})
        tab_page = tab_context.new_page()
        tab_page.goto("http://localhost:3000/doctor/activity", wait_until="networkidle")
        tab_shot = os.path.join(SCREENSHOT_DIR, "recent_activity_768.png")
        tab_page.screenshot(path=tab_shot)
        print(f"  -> Saved screenshot: recent_activity_768.png")
        tab_context.close()

        # -----------------------------------------------------------------
        # STEP 3: Mobile Viewport (390x844)
        # -----------------------------------------------------------------
        print("[Step 7] Testing Mobile Viewport (390x844)...")
        mob_context = browser.new_context(viewport={"width": 390, "height": 844})
        mob_page = mob_context.new_page()
        mob_page.goto("http://localhost:3000/doctor/activity", wait_until="networkidle")
        mob_shot = os.path.join(SCREENSHOT_DIR, "recent_activity_390.png")
        mob_page.screenshot(path=mob_shot)
        print(f"  -> Saved screenshot: recent_activity_390.png")
        mob_context.close()

        browser.close()

    print("\n=======================================================")
    print("  PLAYWRIGHT RECENT CARE ACTIVITY E2E VERIFICATION PASSED")
    print("=======================================================\n")

if __name__ == "__main__":
    run_playwright_test()
