import os
import sys
import time
from playwright.sync_api import sync_playwright

# Set stdout encoding to UTF-8
sys.stdout.reconfigure(encoding='utf-8')

CHROMIUM_PATH = r'C:\Users\lenovo\AppData\Local\ms-playwright\chromium-1234\chrome-win64\chrome.exe'

def run_playwright_e2e_schemes():
    print("=== STARTING PLAYWRIGHT E2E ASHA SCHEMES WORKSPACE VERIFICATION ===")
    
    with sync_playwright() as p:
        launch_kwargs = {"headless": True}
        if os.path.exists(CHROMIUM_PATH):
            launch_kwargs["executable_path"] = CHROMIUM_PATH

        browser = p.chromium.launch(**launch_kwargs)

        viewports = [
            ("Desktop (1280x800)", {"width": 1280, "height": 800}),
            ("Tablet (768x1024)", {"width": 768, "height": 1024}),
            ("Mobile (375x812)", {"width": 375, "height": 812})
        ]

        for vp_name, vp_dim in viewports:
            print(f"\n--- Testing Viewport: {vp_name} ---")
            context = browser.new_context(viewport=vp_dim)
            page = context.new_page()

            # 1. Login as ASHA
            print(f"[{vp_name}] Navigating to login...")
            page.goto("http://localhost:3000/login")
            page.wait_for_timeout(1000)
            
            # Select ASHA Worker role
            page.click("text=ASHA Worker")
            page.click("button:has-text('Sign In to Healthcare Portal')")
            page.wait_for_url("**/asha/dashboard", timeout=10000)
            page.wait_for_timeout(1000)
            print(f"[{vp_name}] Logged in successfully as ASHA. Current URL: {page.url}")

            # 2. Navigate to /asha/schemes
            print(f"[{vp_name}] Navigating to /asha/schemes...")
            page.goto("http://localhost:3000/asha/schemes")
            page.wait_for_selector("h1:has-text('Government Health Schemes')", timeout=10000)

            # 3. Verify Header and no "ICMR" string
            h1_elem = page.locator("h1:has-text('Government Health Schemes')")
            header_text = h1_elem.inner_text()
            print(f"[{vp_name}] Page H1: {header_text}")
            assert "Government Health Schemes" in header_text
            assert "ICMR" not in header_text, "Error: Incorrect ICMR authority text should not be present"

            # 4. Verify Citizen Selector
            print(f"[{vp_name}] Verifying citizen dropdown selection...")
            page.wait_for_selector("#select-citizen option", state="attached", timeout=10000)
            select_elem = page.locator("#select-citizen")
            options = select_elem.locator("option").all_inner_texts()
            print(f"[{vp_name}] Citizen options found: {len(options)}")
            assert len(options) >= 2

            # 5. Verify Interactive Filters
            print(f"[{vp_name}] Verifying interactive status filter counters...")
            page.wait_for_selector("#filter-all-schemes", timeout=10000)
            assert page.locator("#filter-eligible").is_visible()
            assert page.locator("#filter-services").is_visible()
            assert page.locator("#filter-more-info").is_visible()
            assert page.locator("#filter-not-eligible").is_visible()
            
            # Click Universal Services filter
            page.click("#filter-services")
            page.wait_for_timeout(500)
            print(f"[{vp_name}] Clicked Universal Services filter.")

            # Click All Evaluated Schemes filter
            page.click("#filter-all-schemes")
            page.wait_for_timeout(500)

            # 6. Verify Missing Information Modal
            print(f"[{vp_name}] Testing 'Complete Eligibility Profile' modal...")
            page.wait_for_selector("#btn-complete-profile", timeout=10000)
            page.click("#btn-complete-profile")
            
            page.wait_for_selector("#modal-questionnaire-overlay", timeout=10000)
            assert page.locator("#modal-heading").is_visible()
            print(f"[{vp_name}] Questionnaire modal verified visible.")

            # Close modal
            page.click("#btn-close-modal")
            page.wait_for_timeout(500)
            print(f"[{vp_name}] Questionnaire modal closed.")

            # 7. Verify Scheme Card Elements
            print(f"[{vp_name}] Verifying scheme card content and links...")
            first_card = page.locator("h3").nth(1)
            assert first_card.is_visible()
            print(f"[{vp_name}] First Scheme Title: {first_card.inner_text()}")

            # Expand details on a scheme
            more_details_btn = page.locator("button:has-text('Documents & Application Steps')").first
            if more_details_btn.is_visible():
                more_details_btn.click()
                page.wait_for_timeout(500)
                assert page.locator("text=Required Documents").first.is_visible()
                assert page.locator("text=Application & Access Steps").first.is_visible()
                print(f"[{vp_name}] Expanded scheme details verified.")

            context.close()

        browser.close()
    print("\n=== ALL PLAYWRIGHT VIEWPORT TESTS (DESKTOP, TABLET, MOBILE) PASSED PERFECTLY! ===")

if __name__ == "__main__":
    run_playwright_e2e_schemes()
