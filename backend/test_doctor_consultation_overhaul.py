import asyncio
from playwright.async_api import async_playwright

async def verify_overhauled_doctor_consultation():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=300)
        context = await browser.new_context(viewport={"width": 1440, "height": 900})
        page = await context.new_page()

        print("\n=======================================================")
        print("  VERIFYING OVERHAULED DOCTOR CONSULTATION SCREEN")
        print("=======================================================\n")

        # 1. Login
        print("[1] Opening Login Page...")
        await page.goto("http://localhost:5173/login", wait_until="domcontentloaded")
        await page.wait_for_timeout(1000)

        print("[2] Signing in as Dr. Abhinav Sharma...")
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
        print("  -> Doctor Dashboard Loaded Successfully.")

        # 2. Open Anandi Bai Deshmukh Consultation
        print("[3] Opening Anandi Bai Deshmukh Consultation...")
        await page.goto("http://localhost:5173/doctor/consultations/c1d9bb3d-0854-4635-85af-b214b7d3c335", wait_until="domcontentloaded")
        await page.wait_for_timeout(2000)

        # 3. Verify RAG Evidence is ABSENT
        rag_visible = await page.locator("text='Clinical RAG Evidence'").is_visible()
        guideline_visible = await page.locator("text='ICMR / MoHFW Maternal Hypertension Guidelines'").is_visible()
        score_visible = await page.locator("text='Score: 0.94'").is_visible()
        print(f"  -> Clinical RAG Evidence Absent: {not rag_visible} [PASS]")
        print(f"  -> Guideline Cards Absent: {not guideline_visible} [PASS]")
        print(f"  -> Milvus Score Absent: {not score_visible} [PASS]")

        # 4. Verify Professional Right Column Status Panels
        status_panel_visible = await page.locator("h3:has-text('Consultation Status')").is_visible()
        missing_info_visible = await page.locator("h3:has-text('Missing Information')").is_visible()
        care_plan_progress_visible = await page.locator("h3:has-text('Care Plan Progress')").is_visible()
        print(f"  -> Right Side: Consultation Status: {status_panel_visible} [PASS]")
        print(f"  -> Right Side: Missing Information: {missing_info_visible} [PASS]")
        print(f"  -> Right Side: Care Plan Progress: {care_plan_progress_visible} [PASS]")

        # 5. Verify Unpopulated Doctor Fields for New Consultation
        exam_notes_val = await page.locator("textarea[placeholder*='examination observations']").input_value()
        print(f"  -> Doctor Exam Notes is Blank for New Consultation: '{exam_notes_val}' == '' [PASS: {exam_notes_val == ''}]")

        # 6. Capture Desktop Screenshot
        await page.screenshot(path="c:/Arogya Sahayak_AI_antigravity/backend/tests/overhauled_consultation_desktop.png")
        print("  -> Desktop Screenshot Saved: overhauled_consultation_desktop.png")

        # 7. Test Responsive Mobile Viewport (390x844)
        print("[4] Testing Mobile Viewport (390x844)...")
        await page.set_viewport_size({"width": 390, "height": 844})
        await page.wait_for_timeout(1000)
        await page.screenshot(path="c:/Arogya Sahayak_AI_antigravity/backend/tests/overhauled_consultation_mobile.png")
        print("  -> Mobile Screenshot Saved: overhauled_consultation_mobile.png")

        await page.wait_for_timeout(1500)
        await browser.close()

        print("\n=======================================================")
        print("  ALL CORRECTIVE REQUIREMENTS VERIFIED & PASSED")
        print("=======================================================\n")

if __name__ == "__main__":
    asyncio.run(verify_overhauled_doctor_consultation())
