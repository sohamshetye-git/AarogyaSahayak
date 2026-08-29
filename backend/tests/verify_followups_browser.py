import asyncio
from playwright.async_api import async_playwright

async def verify_followups_ui():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1280, "height": 800})
        page = await context.new_page()

        print("[1] Navigating to login...")
        await page.goto("http://localhost:5173/login", wait_until="networkidle")

        # Select ASHA Worker role
        print("[2] Logging in as ASHA worker...")
        # Check if Sita Asha quick card exists
        try:
            asha_btn = page.locator("button:has-text('Sita Patel'), button:has-text('ASHA')").first
            await asha_btn.click()
            await page.wait_for_timeout(1000)
            submit_btn = page.locator("button:has-text('Sign In'), button:has-text('Log In')").first
            if await submit_btn.is_visible():
                await submit_btn.click()
        except Exception:
            # Type manual credentials
            await page.fill("input[name='identifier'], input[placeholder*='identifier'], input[type='text']", "sita.asha")
            await page.fill("input[name='password'], input[placeholder*='password'], input[type='password']", "demo123")
            await page.click("button[type='submit']")

        await page.wait_for_timeout(2000)
        print(f"[3] Current URL after login: {page.url}")

        # Navigate to /asha/followups
        print("[4] Navigating to /asha/followups...")
        await page.goto("http://localhost:5173/asha/followups", wait_until="networkidle")
        await page.wait_for_timeout(1500)

        # Check title
        title_text = await page.locator("h2").text_content()
        print(f"[5] Page heading: {title_text.strip()}")
        assert "Follow-ups" in title_text

        # Check filter tabs
        filter_tabs = await page.locator("button[id^='filter-tab-']").all_text_contents()
        safe_tabs = [t.encode('ascii', 'replace').decode('ascii') for t in filter_tabs]
        print(f"[6] Available filter tabs: {safe_tabs}")
        assert any("All" in tab for tab in filter_tabs)
        assert any("Overdue" in tab for tab in filter_tabs)
        assert any("Due Today" in tab for tab in filter_tabs)
        assert any("Doctor Directives" in tab for tab in filter_tabs)

        # Click on Doctor Directives filter
        doc_tab = page.locator("#filter-tab-doctor_directives")
        if await doc_tab.is_visible():
            await doc_tab.click()
            await page.wait_for_timeout(1000)
            print("[7] Clicked Doctor Directives filter.")

        # Click on Open Follow-up on first card if present
        open_btn = page.locator("button:has-text('Open Follow-up')").first
        if await open_btn.is_visible():
            print("[8] Clicking Open Follow-up...")
            await open_btn.click()
            await page.wait_for_timeout(2000)
            print(f"[9] Follow-up Detail URL: {page.url}")

            # Verify detail screen elements
            detail_heading = await page.locator("h3").all_text_contents()
            safe_headings = [h.encode('ascii', 'replace').decode('ascii') for h in detail_heading]
            print(f"[10] Headings in detail screen: {safe_headings}")

            # Check if Start Follow-up button or form exists
            start_btn = page.locator("#start-followup-btn")
            if await start_btn.is_visible():
                print("[11] Clicking Start Follow-up Visit...")
                await start_btn.click()
                await page.wait_for_timeout(1500)

            # Check form fields
            has_bp_inputs = await page.locator("#input-systolic").is_visible()
            print(f"[12] Vitals form visible: {has_bp_inputs}")

        # Capture screenshot
        await page.screenshot(path="c:/Arogya Sahayak_AI_antigravity/backend/tests/followup_verification.png")
        print("[13] Verification completed successfully. Screenshot saved.")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(verify_followups_ui())
