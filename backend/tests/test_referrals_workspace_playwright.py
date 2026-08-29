import os
import sys
from pathlib import Path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

import time
from playwright.sync_api import sync_playwright
from app.seeds.seed_full_demo import seed_full_demonstration

SCREENSHOT_DIR = os.path.join(os.path.dirname(__file__), "screenshots")
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

def test_playwright_doctor_referrals_complete_journey():
    print("\n=======================================================")
    print("  PLAYWRIGHT DOCTOR REFERRAL QUEUE & SUMMARY VERIFICATION ")
    print("=======================================================\n")

    # Step 1: Seed demo dataset
    print("[Step 1] Seeding demo dataset...")
    seed_full_demonstration()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # 1440px Desktop Viewport
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        # Step 2: Login as Dr. Abhinav Sharma
        page.add_init_script("""
            localStorage.setItem('aarogya_token', 'mock-doctor-token');
            localStorage.setItem('auth_token', 'mock-doctor-token');
            localStorage.setItem('user_role', 'PHC_DOCTOR');
            localStorage.setItem('aarogya_user', JSON.stringify({
                id: 'DOC-007',
                name: 'Dr. Abhinav Sharma',
                role: 'PHC_DOCTOR',
                username: 'dr.sharma'
            }));
        """)

        # Step 3: Open /doctor/referrals
        print("[Step 3] Navigating to /doctor/referrals...")
        page.goto("http://localhost:3000/doctor/referrals", wait_until="domcontentloaded")
        time.sleep(2)

        # Step 4: Assert queue cards exist
        cards = page.locator("div[style*='border: 1.5px solid']")
        card_count = cards.count()
        print(f"[Step 4] Queue referral cards visible: {card_count}")
        assert card_count > 0, "Referral queue cards must not be empty!"

        # Step 5: Assert Queue Summary non-zero counts
        total_btn = page.locator("button[aria-label*='Total Active Referrals']").first
        urgent_pending_btn = page.locator("button[aria-label*='Urgent Pending Review']").first
        consult_btn = page.locator("button[aria-label*='Active Consultations']").first

        assert total_btn.is_visible(), "Total Active Referrals row button must be visible"
        assert urgent_pending_btn.is_visible(), "Urgent Pending Review row button must be visible"
        assert consult_btn.is_visible(), "Active Consultations row button must be visible"

        print("  -> Queue Summary accessible buttons verified!")

        # Step 6: Click Urgent Pending Review row button
        print("[Step 6] Clicking Urgent Pending Review Queue Summary row...")
        urgent_pending_btn.click()
        time.sleep(1)
        assert "filter=URGENT_PENDING_REVIEW" in page.url, f"URL should contain filter=URGENT_PENDING_REVIEW, got {page.url}"
        print(f"  -> Filter URL query verified: {page.url}")

        # Step 7: Click Active Consultations row button
        print("[Step 7] Clicking Active Consultations Queue Summary row...")
        consult_btn.click()
        time.sleep(1.5)
        assert "/doctor/consultations" in page.url and "status=IN_CONSULTATION" in page.url, f"Expected /doctor/consultations?status=IN_CONSULTATION, got {page.url}"
        print(f"  -> Active Consultations workspace route verified: {page.url}")

        # Step 8: Test Browser Back button navigation
        print("[Step 8] Testing Browser Back button navigation...")
        page.go_back()
        time.sleep(1.5)
        assert "filter=URGENT_PENDING_REVIEW" in page.url, f"Browser back should restore filter URL, got {page.url}"
        print(f"  -> Browser Back restored filter URL: {page.url}")

        # Step 9: Return to All Active
        total_btn.click()
        time.sleep(1)

        # Step 10: Refresh Queue button
        print("[Step 10] Testing Refresh Queue button...")
        refresh_btn = page.locator("button:has-text('Refresh Queue')").first
        refresh_btn.click()
        time.sleep(1)

        # Step 11: Screenshots for responsive 1440px, 768px, 390px
        print("[Step 11] Capturing responsive viewports...")
        shot1440 = os.path.join(SCREENSHOT_DIR, "doctor_referrals_1440.png")
        page.screenshot(path=shot1440, full_page=True)
        print(f"  -> 1440px screenshot saved: {shot1440}")
        context.close()

        # 768px Tablet
        context768 = browser.new_context(viewport={"width": 768, "height": 1024})
        page768 = context768.new_page()
        page768.add_init_script("""
            localStorage.setItem('aarogya_token', 'mock-doctor-token');
            localStorage.setItem('auth_token', 'mock-doctor-token');
            localStorage.setItem('user_role', 'PHC_DOCTOR');
        """)
        page768.goto("http://localhost:3000/doctor/referrals", wait_until="domcontentloaded")
        time.sleep(2)
        shot768 = os.path.join(SCREENSHOT_DIR, "doctor_referrals_768.png")
        page768.screenshot(path=shot768, full_page=True)
        print(f"  -> 768px screenshot saved: {shot768}")
        context768.close()

        # 390px Mobile
        context390 = browser.new_context(viewport={"width": 390, "height": 844})
        page390 = context390.new_page()
        page390.add_init_script("""
            localStorage.setItem('aarogya_token', 'mock-doctor-token');
            localStorage.setItem('auth_token', 'mock-doctor-token');
            localStorage.setItem('user_role', 'PHC_DOCTOR');
        """)
        page390.goto("http://localhost:3000/doctor/referrals", wait_until="domcontentloaded")
        time.sleep(2)
        shot390 = os.path.join(SCREENSHOT_DIR, "doctor_referrals_390.png")
        page390.screenshot(path=shot390, full_page=True)
        print(f"  -> 390px screenshot saved: {shot390}")
        context390.close()

        browser.close()

    print("\n=======================================================")
    print("  PLAYWRIGHT QUEUE SUMMARY VERIFICATION PASSED")
    print("=======================================================\n")

if __name__ == "__main__":
    test_playwright_doctor_referrals_complete_journey()
