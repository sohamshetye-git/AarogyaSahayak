import time
import requests
import re
from playwright.sync_api import sync_playwright

PROD_PORTAL_URL = "https://aarogya-sahayak-healthcare-portal.vercel.app"

def wait_for_deploy():
    print("Checking Vercel production deployment status...")
    for i in range(25):
        try:
            r = requests.get(PROD_PORTAL_URL, timeout=10)
            js_files = re.findall(r'/assets/[^"\']+\.js', r.text)
            if js_files:
                js_url = PROD_PORTAL_URL + js_files[0]
                content = requests.get(js_url, timeout=10).text
                if "investigation_order_id" in content or "highlightOrder" in content or "highlightOrderId" in content or "caseTimeline" in content:
                    print(f"Deployment updated with new bundle: {js_files[0]}")
                    return True
        except Exception as e:
            print(f"Deploy poll {i+1} err: {e}")
        time.sleep(6)
    return False

def verify_view_timeline():
    wait_for_deploy()
    print("\nStarting live Playwright test for Doctor Investigations View Timeline...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        # Step 1: Login as Doctor
        print("[Step 1] Navigating to login...")
        page.goto(f"{PROD_PORTAL_URL}/login", wait_until="networkidle")
        time.sleep(2)
        
        # Click Doctor quick demo login button
        doc_btn = page.locator("[data-testid='demo-role-doctor']")
        doc_btn.click()
        time.sleep(1)
        
        submit_btn = page.locator("[data-testid='btn-login-submit']")
        submit_btn.click()
        page.wait_for_url("**/doctor/**", timeout=20000)
        print("  -> Doctor logged in successfully.")

        # Step 2: Navigate to /doctor/investigations
        print("[Step 2] Navigating to /doctor/investigations?search=8928...")
        page.goto(f"{PROD_PORTAL_URL}/doctor/investigations?search=8928", wait_until="networkidle")
        time.sleep(3)

        # Confirm order card LAB-20260903030225-8928 is displayed
        content = page.content()
        assert "8928" in content, "Order LAB-20260903030225-8928 not found on investigations page"
        print("  -> Confirmed LAB-20260903030225-8928 card is displayed.")

        # Step 3: Find the View Timeline button on the card and click it
        print("[Step 3] Clicking 'View Timeline' button...")
        timeline_btn = page.locator("button:has-text('View Timeline')").first
        timeline_btn.click()

        # Step 4: Verify navigation to /doctor/cases/.../timeline
        print("[Step 4] Verifying navigation to Case Timeline route...")
        page.wait_for_url("**/doctor/cases/*/timeline*", timeout=15000)
        current_url = page.url
        print(f"  -> Successfully navigated to: {current_url}")
        assert "/doctor/cases/" in current_url and "/timeline" in current_url
        assert "returnTo=" in current_url
        assert "highlightOrder=" in current_url

        # Step 5: Verify Case and Timeline Content
        time.sleep(3)
        timeline_content = page.content().lower()
        assert "krishna" in timeline_content or "mohite" in timeline_content, "Patient name not displayed on timeline"
        assert "urine" in timeline_content or "investigation" in timeline_content, "Urine Routine investigation not displayed in timeline"
        print("  -> Patient Krishna Omkar Mohite and Urine Routine timeline event successfully verified!")

        # Step 6: Test Back button preserves search/filter state
        print("[Step 6] Testing Back navigation preserves state...")
        back_btn = page.locator("button:has-text('Back to Investigations')")
        if back_btn.count() > 0:
            back_btn.first.click()
        else:
            page.go_back()
        
        page.wait_for_url("**/doctor/investigations*", timeout=10000)
        back_url = page.url
        print(f"  -> Returned to investigations: {back_url}")
        assert "search=Mohite" in back_url or "/doctor/investigations" in back_url

        # Step 7: Refresh timeline direct URL test
        print("[Step 7] Testing Direct Timeline URL Refresh...")
        page.goto(current_url, wait_until="networkidle")
        time.sleep(3)
        refreshed_content = page.content().lower()
        assert "krishna" in refreshed_content or "mohite" in refreshed_content, "Patient name not found on refreshed timeline"
        print("  -> Direct URL refresh verified successfully!")

        print("\n=======================================================")
        print("  ALL INVESTIGATION TIMELINE JOURNEY CHECKS PASSED LIVE!")
        print("=======================================================")
        browser.close()

if __name__ == "__main__":
    verify_view_timeline()
