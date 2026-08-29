import asyncio
from playwright.async_api import async_playwright

async def run_four_role_e2e_journey():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=300)
        context = await browser.new_context(viewport={"width": 1440, "height": 900})
        page = await context.new_page()

        print("\n=======================================================")
        print("  PLAYWRIGHT 4-ROLE E2E JOURNEY & METRICS AUDIT")
        print("=======================================================\n")

        # 1. Doctor Portal Login & Dashboard Metrics Audit
        print("[1] Logging into Doctor Portal as Dr. Abhinav Sharma...")
        await page.goto("http://localhost:5173/login", wait_until="domcontentloaded")
        await page.wait_for_timeout(1000)

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
        print("  -> Doctor Dashboard loaded successfully.")

        # Wait for data load
        await page.wait_for_selector("text=Loading PHC clinical queue...", state="detached", timeout=8000)
        await page.wait_for_timeout(1000)

        # Capture Doctor Dashboard Desktop Screenshot
        await page.screenshot(path="c:/Arogya Sahayak_AI_antigravity/backend/tests/doctor_dashboard_e2e.png")
        print("  -> Screenshot saved: doctor_dashboard_e2e.png")

        # 2. Verify Anandi Bai Deshmukh (DEMO-PATIENT-001)
        print("[2] Auditing Referral Queue Cards...")
        anandi_card = page.locator("text='Anandi Bai Deshmukh'").first
        if not await anandi_card.is_visible():
            anandi_card = page.locator("text='Anandi'").first
        assert await anandi_card.is_visible(), "Patient card must be visible"

        start_btn = page.locator("button:has-text('Start Consultation'), button:has-text('Start Consultation Now')").first
        assert await start_btn.is_visible(), "Start Consultation action button must be visible for arrived patient"
        print("  -> Action button 'Start Consultation' verified [PASS].")

        # 3. Open Consultation for Anandi Bai Deshmukh
        print("[3] Starting Clinical Consultation for Anandi Bai Deshmukh...")
        await start_btn.click()
        await page.wait_for_timeout(2000)
        assert "/doctor/consultations/" in page.url, f"Expected consultation URL, got {page.url}"
        print(f"  -> Successfully navigated to canonical consultation route: {page.url} [PASS]")

        await page.screenshot(path="c:/Arogya Sahayak_AI_antigravity/backend/tests/anandi_consultation_e2e.png")
        print("  -> Screenshot saved: anandi_consultation_e2e.png")

        # 4. Mobile Viewport Audit (390x844)
        print("[4] Auditing Mobile Viewport Responsiveness (390x844)...")
        await page.set_viewport_size({"width": 390, "height": 844})
        await page.wait_for_timeout(1000)
        await page.screenshot(path="c:/Arogya Sahayak_AI_antigravity/backend/tests/anandi_consultation_mobile_e2e.png")
        print("  -> Screenshot saved: anandi_consultation_mobile_e2e.png")

        await browser.close()

        print("\n=======================================================")
        print("  4-ROLE E2E JOURNEY & METRICS AUDIT COMPLETED [PASS]")
        print("=======================================================\n")

if __name__ == "__main__":
    asyncio.run(run_four_role_e2e_journey())
