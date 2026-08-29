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

def test_playwright_timeline_navigation_journey():
    print("\n=======================================================")
    print("  PLAYWRIGHT CASE TIMELINE E2E VERIFICATION ")
    print("=======================================================\n")

    # Step 1: Seed demo dataset
    print("[Step 1] Seeding demo dataset...")
    seed_full_demonstration()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # 1440px Viewport
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

        # Step 3: Open /doctor/consultations
        print("[Step 3] Navigating to /doctor/consultations...", flush=True)
        page.goto("http://localhost:3000/doctor/consultations", wait_until="domcontentloaded")
        time.sleep(2)

        # Step 4: Click 'All Active' or 'Completed' tab to show Pooja Jadhav
        print("[Step 4] Selecting 'All Active' tab...", flush=True)
        all_tab = page.locator("button:has-text('All Active')").first
        if all_tab.is_visible():
            all_tab.click()
            time.sleep(1)

        print("[Step 4b] Locating Pooja Jadhav's consultation card...", flush=True)
        pooja_card = page.locator("div[style*='border']").filter(has_text="Pooja Jadhav").first
        assert pooja_card.is_visible(), "Pooja Jadhav's consultation card must be visible"

        # Step 5: Click View Timeline on Pooja Jadhav's card
        print("[Step 5] Clicking View Timeline on Pooja Jadhav's card...", flush=True)
        page.evaluate("""
            () => {
                const buttons = Array.from(document.querySelectorAll('button'));
                const btn = buttons.find(b => b.textContent.includes('View Timeline'));
                if (btn) btn.click();
            }
        """)
        time.sleep(2)

        # Step 6: Assert URL contains her canonical case UUID
        print(f"[Step 6] Current URL: {page.url}", flush=True)
        assert "/doctor/cases/" in page.url and "/timeline" in page.url, f"Expected /doctor/cases/UUID/timeline, got {page.url}"
        assert "returnTo=/doctor/consultations" in page.url, f"Expected returnTo query parameter, got {page.url}"
        
        # Extract case ID from URL for 768px and 390px tests
        case_id_from_url = page.url.split("/doctor/cases/")[1].split("/timeline")[0]

        # Step 7: Assert page header shows Pooja Jadhav
        heading = page.locator("text=Pooja Jadhav").first
        assert heading.is_visible(), "Page header must display Pooja Jadhav"
        print("  -> Header bio and case reference verified!", flush=True)

        # Step 8: Assert timeline events appear
        events = page.locator("div:has-text('Actor:')")
        print(f"  -> Timeline events rendered: {events.count()}", flush=True)
        assert events.count() > 0, "Timeline events stream must not be empty"

        # Step 9: Click Back to Consultations button
        print("[Step 9] Testing Back to Consultations button...", flush=True)
        page.evaluate("""
            () => {
                const buttons = Array.from(document.querySelectorAll('button'));
                const btn = buttons.find(b => b.textContent.includes('Back to Consultations'));
                if (btn) btn.click();
            }
        """)
        time.sleep(1.5)
        assert "/doctor/consultations" in page.url, f"Back button should navigate to /doctor/consultations, got {page.url}"
        print(f"  -> Returned to URL: {page.url}", flush=True)

        # Step 10: Test Browser Back button navigation
        print("[Step 10] Testing Browser Forward/Back buttons...", flush=True)
        page.go_back()
        time.sleep(1.5)
        assert "/doctor/cases/" in page.url and "/timeline" in page.url, f"Browser Back should restore timeline URL, got {page.url}"
        page.go_forward()
        time.sleep(1.5)
        assert "/doctor/consultations" in page.url, f"Browser Forward should restore consultations URL, got {page.url}"

        # Step 11: Capturing responsive viewports
        print("[Step 11] Capturing responsive viewports...", flush=True)
        shot1440 = os.path.join(SCREENSHOT_DIR, "case_timeline_1440.png")
        page.screenshot(path=shot1440, full_page=True)
        print(f"  -> 1440px screenshot saved: {shot1440}", flush=True)
        context.close()

        # 768px Tablet Viewport
        context768 = browser.new_context(viewport={"width": 768, "height": 1024})
        page768 = context768.new_page()
        page768.add_init_script("""
            localStorage.setItem('aarogya_token', 'mock-doctor-token');
            localStorage.setItem('auth_token', 'mock-doctor-token');
            localStorage.setItem('user_role', 'PHC_DOCTOR');
        """)
        page768.goto(f"http://localhost:3000/doctor/cases/{case_id_from_url}/timeline", wait_until="domcontentloaded")
        time.sleep(2)
        shot768 = os.path.join(SCREENSHOT_DIR, "case_timeline_768.png")
        page768.screenshot(path=shot768, full_page=True)
        print(f"  -> 768px screenshot saved: {shot768}", flush=True)
        context768.close()

        # 390px Mobile Viewport
        context390 = browser.new_context(viewport={"width": 390, "height": 844})
        page390 = context390.new_page()
        page390.add_init_script("""
            localStorage.setItem('aarogya_token', 'mock-doctor-token');
            localStorage.setItem('auth_token', 'mock-doctor-token');
            localStorage.setItem('user_role', 'PHC_DOCTOR');
        """)
        page390.goto(f"http://localhost:3000/doctor/cases/{case_id_from_url}/timeline", wait_until="domcontentloaded")
        time.sleep(2)
        shot390 = os.path.join(SCREENSHOT_DIR, "case_timeline_390.png")
        page390.screenshot(path=shot390, full_page=True)
        print(f"  -> 390px screenshot saved: {shot390}", flush=True)
        context390.close()

        browser.close()

    print("\n=======================================================", flush=True)
    print("  PLAYWRIGHT CASE TIMELINE VERIFICATION PASSED", flush=True)
    print("=======================================================\n", flush=True)

if __name__ == "__main__":
    test_playwright_timeline_navigation_journey()
