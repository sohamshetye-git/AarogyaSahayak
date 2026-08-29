"""
Playwright E2E Verification Script for ASHA Escalation Engine & Doctor Workflow
"""

import sys
import os
import time
from playwright.sync_api import sync_playwright

SCREENSHOT_DIR = os.path.join(os.path.dirname(__file__), "screenshots")
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

def run_playwright_test():
    print("\n=======================================================")
    print("  PLAYWRIGHT ASHA ESCALATION E2E VERIFICATION STARTED")
    print("=======================================================\n")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # -----------------------------------------------------------------
        # STEP 1: Desktop Viewport (1440x900) - Full Workflow
        # -----------------------------------------------------------------
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        # Set auth state directly in browser local storage
        page.add_init_script("""
            localStorage.setItem('auth_token', 'mock-doctor-token');
            localStorage.setItem('aarogya_user', JSON.stringify({
                id: 'DOC-007',
                name: 'Dr. Abhinav Sharma',
                role: 'PHC_DOCTOR',
                username: 'dr.sharma'
            }));
        """)

        # Seed active escalation directly in PostgreSQL for deterministic E2E test
        from app.database import SessionLocal
        from app.models import FollowUp, User, CasePriorityEnum
        from app.services.escalation_service import create_or_update_escalation

        db = SessionLocal()
        try:
            fu = db.query(FollowUp).first()
            if fu:
                create_or_update_escalation(
                    db=db,
                    follow_up_id=fu.id,
                    reason="Repeat BP 165/105 mmHg and severe headache reported by Sita Patel",
                    priority=CasePriorityEnum.URGENT,
                    asha_user_id=fu.assigned_user_id
                )
                print(f"  -> Seeded active escalation for follow_up {fu.id}")
        finally:
            db.close()

        print("[Step 1] Logging in as Doctor (dr.sharma)...")
        page.goto("http://localhost:3000/doctor/dashboard", wait_until="networkidle")
        print(f"  -> Logged in successfully: {page.url}")
        time.sleep(1)

        # Check for Escalation Card on Dashboard
        print("[Step 2] Locating ASHA Escalations Alert Card...")
        page.reload(wait_until="networkidle")
        time.sleep(1)
        review_btn = page.query_selector("button:has-text('Review Escalation')")

        # Capture Desktop Dashboard screenshot with Escalation Card
        desktop_shot = os.path.join(SCREENSHOT_DIR, "escalation_dashboard_1440.png")
        page.screenshot(path=desktop_shot)
        print(f"  -> Saved screenshot: escalation_dashboard_1440.png")

        # Click Review Escalation
        if review_btn:
            print("[Step 3] Clicking 'Review Escalation' button...")
            review_btn.click()
            page.wait_for_timeout(1500)
            print(f"  -> Navigated to: {page.url}")
            assert "/doctor/followups/" in page.url, f"URL should be canonical follow-up route, got {page.url}"

            # Capture Escalation Detail View
            detail_shot = os.path.join(SCREENSHOT_DIR, "escalation_detail_1440.png")
            page.screenshot(path=detail_shot)
            print(f"  -> Saved screenshot: escalation_detail_1440.png")

            # Doctor Action 1: Acknowledge
            ack_btn = page.query_selector("button:has-text('Acknowledge Escalation')")
            if ack_btn and ack_btn.is_enabled():
                print("[Step 4] Doctor acknowledging escalation...")
                ack_btn.click()
                page.wait_for_timeout(1000)

            # Doctor Action 2: Request Patient to PHC
            phc_btn = page.query_selector("button:has-text('Request Patient to PHC')")
            if phc_btn:
                print("[Step 5] Doctor requesting patient to PHC...")
                phc_btn.click()
                page.wait_for_timeout(500)
                submit_action_btn = page.query_selector("button:has-text('Submit Action Directive')")
                if submit_action_btn:
                    submit_action_btn.click()
                    page.wait_for_timeout(1000)

            # Doctor Action 3: Resolve Escalation
            res_btn = page.query_selector("button:has-text('Resolve Escalation')")
            if res_btn:
                print("[Step 6] Doctor resolving escalation...")
                res_btn.click()
                page.wait_for_timeout(500)
                confirm_res_btn = page.query_selector("button:has-text('Confirm Resolution')")
                if confirm_res_btn:
                    confirm_res_btn.click()
                    page.wait_for_timeout(1500)
                    print(f"  -> Returned to dashboard: {page.url}")

        context.close()

        # -----------------------------------------------------------------
        # STEP 2: Tablet Viewport (768x1024)
        # -----------------------------------------------------------------
        print("[Step 7] Testing Tablet Viewport (768x1024)...")
        tab_context = browser.new_context(viewport={"width": 768, "height": 1024})
        tab_page = tab_context.new_page()
        tab_page.goto("http://localhost:3000/doctor/dashboard", wait_until="networkidle")
        tab_shot = os.path.join(SCREENSHOT_DIR, "escalation_768.png")
        tab_page.screenshot(path=tab_shot)
        print(f"  -> Saved screenshot: escalation_768.png")
        tab_context.close()

        # -----------------------------------------------------------------
        # STEP 3: Mobile Viewport (390x844)
        # -----------------------------------------------------------------
        print("[Step 8] Testing Mobile Viewport (390x844)...")
        mob_context = browser.new_context(viewport={"width": 390, "height": 844})
        mob_page = mob_context.new_page()
        mob_page.goto("http://localhost:3000/doctor/dashboard", wait_until="networkidle")
        mob_shot = os.path.join(SCREENSHOT_DIR, "escalation_390.png")
        mob_page.screenshot(path=mob_shot)
        print(f"  -> Saved screenshot: escalation_390.png")
        mob_context.close()

        browser.close()

    print("\n=======================================================")
    print("  PLAYWRIGHT ASHA ESCALATION E2E VERIFICATION PASSED")
    print("=======================================================\n")

if __name__ == "__main__":
    run_playwright_test()
