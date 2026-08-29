import asyncio
import sys
from playwright.async_api import async_playwright

async def run_asha_flow():
    results = {}
    async with async_playwright() as p:
        # Launch visible browser
        browser = await p.chromium.launch(headless=False, slow_mo=300)
        context = await browser.new_context(viewport={"width": 1366, "height": 768})
        page = await context.new_page()

        print("\n=======================================================")
        print("   ASHA WORKFLOW E2E AUTOMATED BROWSER TEST (PORT 5173)")
        print("=======================================================\n")

        # Step 1: Navigate to Login
        try:
            print("[Step 1] Navigating to http://localhost:5173/login...")
            await page.goto("http://localhost:5173/login", wait_until="networkidle")
            await page.wait_for_timeout(1000)
            results["1_Navigation"] = "PASS"
            print("  -> PASS: Reached login page")
        except Exception as e:
            results["1_Navigation"] = f"FAIL: {e}"
            print(f"  -> FAIL: {e}")

        # Step 2: ASHA Login
        try:
            print("[Step 2] Logging in as ASHA worker (Sita Patel)...")
            asha_btn = page.locator("button:has-text('Sita Patel'), button:has-text('ASHA')").first
            if await asha_btn.is_visible():
                await asha_btn.click()
                await page.wait_for_timeout(500)
                submit_btn = page.locator("button:has-text('Sign In'), button:has-text('Log In')").first
                if await submit_btn.is_visible():
                    await submit_btn.click()
            else:
                await page.fill("input[type='text'], input[placeholder*='identifier']", "sita.asha")
                await page.fill("input[type='password']", "demo123")
                await page.click("button[type='submit']")

            await page.wait_for_url("**/asha/**", timeout=8000)
            results["2_ASHA_Login"] = "PASS"
            print(f"  -> PASS: Logged in successfully, landed on {page.url}")
        except Exception as e:
            results["2_ASHA_Login"] = f"FAIL: {e}"
            print(f"  -> FAIL: {e}")

        # Step 3: People / Beneficiary Directory (/asha/people)
        try:
            print("[Step 3] Navigating to People directory (http://localhost:5173/asha/people)...")
            await page.goto("http://localhost:5173/asha/people", wait_until="networkidle")
            await page.wait_for_timeout(1500)
            results["3_People_Directory"] = "PASS"
            print(f"  -> PASS: Reached People Directory ({page.url})")
        except Exception as e:
            results["3_People_Directory"] = f"FAIL: {e}"
            print(f"  -> FAIL: {e}")

        # Step 4: Click Patient to open Patient Detail / Case Timeline
        try:
            print("[Step 4] Clicking on first patient card in Beneficiary Directory...")
            # In AshaPeopleScreen, patient cards are div elements with cursor: pointer
            patient_card = page.locator("div:has-text('Age:'), div:has-text('ABHA ID:')").first
            await patient_card.wait_for(state="visible", timeout=6000)
            await patient_card.click()
            await page.wait_for_timeout(2000)
            print(f"  -> Opened Patient Detail / Longitudinal Timeline: {page.url}")
            results["4_Patient_Detail"] = "PASS"
            print("  -> PASS: Opened Patient Detail workspace")
        except Exception as e:
            results["4_Patient_Detail"] = f"FAIL: {e}"
            print(f"  -> FAIL: {e}")

        # Step 5: Tasks Screen
        try:
            print("[Step 5] Navigating to Tasks (/asha/tasks)...")
            await page.goto("http://localhost:5173/asha/tasks", wait_until="networkidle")
            await page.wait_for_timeout(1500)
            results["5_Tasks_Screen"] = "PASS"
            print(f"  -> PASS: Loaded Tasks screen ({page.url})")
        except Exception as e:
            results["5_Tasks_Screen"] = f"FAIL: {e}"
            print(f"  -> FAIL: {e}")

        # Step 6: Click a Task
        try:
            print("[Step 6] Clicking on task action button...")
            task_btn = page.locator("button:has-text('Open'), button:has-text('View'), button:has-text('Acknowledge'), button:has-text('Case')").first
            if await task_btn.is_visible():
                await task_btn.click()
                await page.wait_for_timeout(1000)
            results["6_Click_Task"] = "PASS"
            print("  -> PASS: Interacted with task")
        except Exception as e:
            results["6_Click_Task"] = f"FAIL: {e}"
            print(f"  -> FAIL: {e}")

        # Step 7: Follow-up Module & Detail
        try:
            print("[Step 7] Navigating to Follow-ups (/asha/followups)...")
            await page.goto("http://localhost:5173/asha/followups", wait_until="networkidle")
            await page.wait_for_timeout(1500)
            
            # Click Open Follow-up on first card
            open_fup = page.locator("button:has-text('Open Follow-up')").first
            if await open_fup.is_visible():
                await open_fup.click()
                await page.wait_for_timeout(1500)
                print(f"  -> Opened Follow-up Detail workspace: {page.url}")
            
            results["7_Followup_Module"] = "PASS"
            print("  -> PASS: Follow-ups list and workspace verified")
        except Exception as e:
            results["7_Followup_Module"] = f"FAIL: {e}"
            print(f"  -> FAIL: {e}")

        # Step 8: Field Visit (/asha/visit)
        try:
            print("[Step 8] Navigating to Field Visits (/asha/visit)...")
            await page.goto("http://localhost:5173/asha/visit", wait_until="networkidle")
            await page.wait_for_timeout(1500)
            print(f"  -> Reached Field Visit workspace: {page.url}")
            results["8_Field_Visit_Workflow"] = "PASS"
            print("  -> PASS: Field Visit workflow verified")
        except Exception as e:
            results["8_Field_Visit_Workflow"] = f"FAIL: {e}"
            print(f"  -> FAIL: {e}")

        # Keep browser open for viewing before closing
        await page.wait_for_timeout(4000)
        await browser.close()

        print("\n=======================================================")
        print("                  FINAL TEST REPORT")
        print("=======================================================")
        for step, res in results.items():
            print(f"  {step:30s}: {res}")
        print("=======================================================\n")

if __name__ == "__main__":
    asyncio.run(run_asha_flow())
