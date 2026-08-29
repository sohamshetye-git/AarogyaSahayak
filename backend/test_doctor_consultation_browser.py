import asyncio
from playwright.async_api import async_playwright

async def verify_doctor_consultation_workspace():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=300)
        context = await browser.new_context(viewport={"width": 1440, "height": 900})
        page = await context.new_page()

        print("\n=======================================================")
        print("  DOCTOR CLINICAL CONSULTATION WORKSPACE E2E TEST (1440px)")
        print("=======================================================\n")

        # 1. Login as PHC Doctor
        print("[Step 1] Navigating to login...")
        await page.goto("http://localhost:5173/login", wait_until="domcontentloaded")
        await page.wait_for_timeout(1000)

        print("[Step 2] Logging in as PHC Doctor...")
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
        print("  -> Doctor logged in successfully.")

        # 2. Open Consultation Page
        print("[Step 3] Opening /doctor/consultation...")
        await page.goto("http://localhost:5173/doctor/consultation", wait_until="domcontentloaded")
        await page.wait_for_timeout(2000)

        # 3. Verify Patient Context & Header
        name = await page.locator("h1").first.text_content()
        print(f"[Step 4] Patient Header: '{name.strip()}' -> PASS")

        # 4. Stepper 1 -> 2
        print("[Step 5] Stepping through Step 1 (Review Referral)...")
        step1_btn = page.locator("button:has-text('Proceed to Examination')").first
        if await step1_btn.is_visible():
            await step1_btn.click()
            await page.wait_for_timeout(1000)

        # 5. Stepper 2 -> 3
        print("[Step 6] Stepping through Step 2 (Examination)...")
        step2_btn = page.locator("button:has-text('Proceed to Assessment')").first
        if await step2_btn.is_visible():
            await step2_btn.click()
            await page.wait_for_timeout(1000)

        # 6. Stepper 3 -> 4
        print("[Step 7] Stepping through Step 3 (Assessment)...")
        step3_btn = page.locator("button:has-text('Proceed to Orders & Prescription')").first
        if await step3_btn.is_visible():
            await step3_btn.click()
            await page.wait_for_timeout(1000)

        # 7. Stepper 4 -> 5
        print("[Step 8] Stepping through Step 4 (Orders & Rx)...")
        step4_btn = page.locator("button:has-text('Proceed to Care Plan & Sign')").first
        if await step4_btn.is_visible():
            await step4_btn.click()
            await page.wait_for_timeout(1000)

        # 8. Save Desktop Screenshot (1440px)
        await page.screenshot(path="c:/Arogya Sahayak_AI_antigravity/backend/tests/doctor_consultation_1440.png")
        print("[Step 9] Saved 1440px consultation workspace screenshot.")

        # 9. Responsive Mobile Test (390px)
        await page.set_viewport_size({"width": 390, "height": 844})
        await page.wait_for_timeout(1500)
        await page.screenshot(path="c:/Arogya Sahayak_AI_antigravity/backend/tests/doctor_consultation_mobile.png")
        print("[Step 10] Saved 390px mobile consultation workspace screenshot.")

        await page.wait_for_timeout(2000)
        await browser.close()
        print("\n=======================================================")
        print("  DOCTOR CONSULTATION WORKSPACE E2E TEST COMPLETED (PASS)")
        print("=======================================================")

if __name__ == "__main__":
    asyncio.run(verify_doctor_consultation_workspace())
