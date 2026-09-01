import pytest
from playwright.sync_api import sync_playwright, expect

def test_doctor_direct_requests_e2e():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # 1. Desktop Viewport (1440x900)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        print("[Step 1] Navigating to login page...")
        page.goto("http://localhost:3000/login", wait_until="networkidle")

        # Fill doctor login credentials
        page.fill("input[type='text'], input[placeholder*='identifier']", "dr.sharma")
        page.fill("input[type='password']", "demo123")
        page.click("button[type='submit']")

        # Wait for navigation to dashboard or direct requests
        page.wait_for_timeout(2000)

        print("[Step 2] Navigating to Direct Citizen Requests...")
        page.goto("http://localhost:3000/doctor/direct-requests", wait_until="networkidle")
        page.wait_for_timeout(1500)

        # Verify Authoritative Doctor Principal in Sidebar / Header
        content = page.content()
        assert "Dr. Abhinav Sharma" in content, "Doctor name must be Dr. Abhinav Sharma"
        assert "Kalyanpur PHC" in content or "Primary Health" in content, "Doctor facility must be displayed"
        assert "Dr. Verma" not in content, "No Dr. Verma fallback identity"

        # Verify Metric Summary Cards have rendered numbers
        summary_cards = page.locator(".grid.grid-cols-2 button, .grid button")
        assert summary_cards.count() >= 6, "Must show at least 6 metric summary cards"
        print(f"[Step 3] Summary cards rendered successfully ({summary_cards.count()} cards)")

        # Verify Queue items
        queue_items = page.locator("div.divide-y > div")
        item_count = queue_items.count()
        print(f"[Step 4] Found {item_count} request item(s) in the queue")
        assert item_count > 0, "Queue must not be empty"

        # Take desktop screenshot
        page.screenshot(path="doctor_requests_queue_desktop.png")

        # 2. Tablet Viewport (768x1024)
        context_tab = browser.new_context(viewport={"width": 768, "height": 1024})
        page_tab = context_tab.new_page()
        page_tab.goto("http://localhost:3000/login", wait_until="networkidle")
        page_tab.fill("input[type='text'], input[placeholder*='identifier']", "dr.sharma")
        page_tab.fill("input[type='password']", "demo123")
        page_tab.click("button[type='submit']")
        page_tab.wait_for_timeout(1500)
        page_tab.goto("http://localhost:3000/doctor/direct-requests", wait_until="networkidle")
        page_tab.screenshot(path="doctor_requests_queue_tablet.png")

        # 3. Mobile Viewport (390x844)
        context_mob = browser.new_context(viewport={"width": 390, "height": 844})
        page_mob = context_mob.new_page()
        page_mob.goto("http://localhost:3000/login", wait_until="networkidle")
        page_mob.fill("input[type='text'], input[placeholder*='identifier']", "dr.sharma")
        page_mob.fill("input[type='password']", "demo123")
        page_mob.click("button[type='submit']")
        page_mob.wait_for_timeout(1500)
        page_mob.goto("http://localhost:3000/doctor/direct-requests", wait_until="networkidle")
        page_mob.screenshot(path="doctor_requests_queue_mobile.png")

        browser.close()
        print("[Step 5] All browser viewports verified successfully!")

if __name__ == "__main__":
    test_doctor_direct_requests_e2e()
