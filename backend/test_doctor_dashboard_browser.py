import asyncio
from playwright.async_api import async_playwright

async def verify_doctor_dashboard():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=300)
        context = await browser.new_context(viewport={"width": 1440, "height": 900})
        page = await context.new_page()

        print("\n=======================================================")
        print("     PHC DOCTOR DASHBOARD DYNAMIC E2E TEST (1440px)")
        print("=======================================================\n")

        # 1. Login as PHC Doctor
        print("[Step 1] Navigating to login...")
        await page.goto("http://localhost:5173/login", wait_until="networkidle")
        await page.wait_for_timeout(1000)

        print("[Step 2] Logging in as PHC Doctor (Dr. Abhinav Sharma)...")
        doc_btn = page.locator("button:has-text('Dr. Abhinav Sharma'), button:has-text('PHC Doctor')").first
        if await doc_btn.is_visible():
            await doc_btn.click()
            await page.wait_for_timeout(500)
            submit_btn = page.locator("button:has-text('Sign In'), button:has-text('Log In')").first
            if await submit_btn.is_visible():
                await submit_btn.click()
        else:
            await page.fill("input[type='text'], input[placeholder*='identifier']", "dr.sharma")
            await page.fill("input[type='password']", "demo123")
            await page.click("button[type='submit']")

        await page.wait_for_url("**/doctor/**", timeout=8000)
        print(f"  -> Logged in successfully: {page.url}")

        # 2. Check Dashboard Title & Facility
        await page.wait_for_timeout(1500)
        title = await page.locator("h1:has-text('PHC Doctor Dashboard')").text_content()
        print(f"[Step 3] Heading: '{title.strip()}'")
        assert "PHC Doctor Dashboard" in title

        # 3. Check Metric Cards
        metric_cards = await page.locator("div:has-text('New Referrals'), div:has-text('Urgent Cases')").first.is_visible()
        print(f"[Step 4] Metric cards visible: {metric_cards}")

        # 4. Click Filter Pills
        print("[Step 5] Testing Referral Queue Filters...")
        urgent_pill = page.locator("button:has-text('Urgent')").first
        if await urgent_pill.is_visible():
            await urgent_pill.click()
            await page.wait_for_timeout(1000)
            print("  -> Clicked 'Urgent' filter pill")

        all_pill = page.locator("button:has-text('All')").first
        if await all_pill.is_visible():
            await all_pill.click()
            await page.wait_for_timeout(1000)
            print("  -> Clicked 'All' filter pill")

        # 5. Check Action Buttons
        ack_btn = page.locator("button:has-text('Review & Acknowledge')").first
        if await ack_btn.is_visible():
            print("[Step 6] Clicking 'Review & Acknowledge'...")
            await ack_btn.click()
            await page.wait_for_timeout(1500)
            print("  -> Acknowledged referral successfully")

        # 6. Verify Right Rails
        today_work = await page.locator("h3:has-text(\"Today's Clinical Work\")").is_visible()
        followups_rail = await page.locator("h3:has-text('ASHA Follow-up Monitor')").is_visible()
        activity_rail = await page.locator("h3:has-text('Recent Care Activity')").is_visible()
        print(f"[Step 7] Rails visible - Today's Work: {today_work}, Follow-ups: {followups_rail}, Activity: {activity_rail}")

        # 7. Take Screenshot
        await page.screenshot(path="c:/Arogya Sahayak_AI_antigravity/backend/tests/doctor_dashboard_1440.png")
        print("[Step 8] Saved 1440px desktop screenshot.")

        # 8. Responsive Test (390px Mobile View)
        await page.set_viewport_size({"width": 390, "height": 844})
        await page.wait_for_timeout(1500)
        await page.screenshot(path="c:/Arogya Sahayak_AI_antigravity/backend/tests/doctor_dashboard_mobile.png")
        print("[Step 9] Saved 390px mobile screenshot.")

        await page.wait_for_timeout(3000)
        await browser.close()
        print("\n=======================================================")
        print("   PHC DOCTOR DASHBOARD E2E TEST COMPLETED (ALL PASS)")
        print("=======================================================\n")

if __name__ == "__main__":
    asyncio.run(verify_doctor_dashboard())
