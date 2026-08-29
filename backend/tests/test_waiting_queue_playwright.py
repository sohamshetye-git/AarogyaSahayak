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

def test_playwright_waiting_queue_journey():
    print("\n=======================================================")
    print("  PLAYWRIGHT PATIENTS WAITING AT PHC E2E VERIFICATION ")
    print("=======================================================\n")

    print("[Step 1] Seeding demo dataset...")
    seed_full_demonstration()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        viewports = [
            {"width": 1440, "height": 900, "name": "desktop"},
            {"width": 768, "height": 1024, "name": "tablet"},
            {"width": 390, "height": 844, "name": "mobile"}
        ]

        for vp in viewports:
            context = browser.new_context(viewport={"width": vp["width"], "height": vp["height"]})
            page = context.new_page()

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

            print(f"\n[{vp['name'].upper()}] Opening Doctor Consultation Workspace...", flush=True)
            page.goto("http://localhost:3000/doctor/consultations", wait_until="domcontentloaded")
            time.sleep(2)

            page.wait_for_selector('h4:has-text("Patients Waiting at PHC")', timeout=10000)

            waiting_heading = page.locator('h4:has-text("Patients Waiting at PHC")')
            assert waiting_heading.is_visible(), "Patients Waiting at PHC heading must be visible"

            duration_texts = page.locator('text=/Arrived.*ago|Arrived just now/')
            badge_count = duration_texts.count()
            print(f"[{vp['name'].upper()}] Rendered waiting duration items: {badge_count}", flush=True)
            assert badge_count > 0, "Waiting duration badges must be rendered"

            shot_path = os.path.join(SCREENSHOT_DIR, f"patients_waiting_{vp['name']}.png")
            page.screenshot(path=shot_path, full_page=True)
            print(f"[{vp['name'].upper()}] Screenshot saved: {shot_path}", flush=True)

            if vp["name"] == "desktop":
                # Verify View All button
                view_all_btn = page.locator('button:has-text("View All")')
                if view_all_btn.is_visible():
                    view_all_btn.click()
                    time.sleep(1)
                    print(f"[DESKTOP] View All clicked -> Current URL: {page.url}", flush=True)
                    assert "READY_TO_START" in page.url or "status=" in page.url

                # Return to consultations and test Start Consultation button
                page.goto("http://localhost:3000/doctor/consultations", wait_until="domcontentloaded")
                time.sleep(2)
                start_btn = page.locator('button:has-text("Start Consultation")').first
                if start_btn.is_visible():
                    start_btn.click()
                    time.sleep(1.5)
                    print(f"[DESKTOP] Start Consultation clicked -> Current URL: {page.url}", flush=True)
                    assert "/doctor/consultations/" in page.url or "/doctor/cases/" in page.url

            context.close()

        browser.close()
        print("\n=======================================================")
        print("  PLAYWRIGHT PATIENTS WAITING AT PHC VERIFICATION PASSED")
        print("=======================================================\n", flush=True)

if __name__ == "__main__":
    test_playwright_waiting_queue_journey()
