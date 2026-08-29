import asyncio
import os
from playwright.async_api import async_playwright

PORTAL_URL = "http://localhost:3000"
SCREENSHOT_DIR = os.path.abspath("backend/tests/screenshots")

async def run_playwright_timeline_verification():
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)
    print("\n=======================================================")
    print("  PLAYWRIGHT DOCTOR CASE TIMELINE E2E VERIFICATION")
    print("=======================================================\n")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        
        # 1. Desktop 1440x900
        context = await browser.new_context(viewport={"width": 1440, "height": 900})
        page = await context.new_page()

        # Login as Doctor (dr.sharma)
        print("[Step 1] Logging in as Doctor (dr.sharma)...")
        await page.goto(f"{PORTAL_URL}/login")
        await page.wait_for_timeout(1000)

        dr_btn = page.locator("button:has-text('Dr. Abhinav Sharma'), button:has-text('Doctor')").first
        if await dr_btn.is_visible():
            await dr_btn.click()
            await page.wait_for_timeout(500)
            submit = page.locator("button:has-text('Sign In'), button:has-text('Log In')").first
            if await submit.is_visible():
                await submit.click()

        await page.wait_for_url("**/doctor/dashboard**", timeout=10000)
        print(f"  -> Logged in successfully: {page.url}")

        # 2. View Timeline for Laxmi Kamble
        print("\n[Step 2] Testing View Timeline for Laxmi Kamble...")
        laxmi_btn = page.locator("[data-testid='referral-card-CASE-LAXMI-008'] button:has-text('View Timeline')").first
        await laxmi_btn.wait_for(state="visible", timeout=10000)
        await laxmi_btn.click()

        await page.wait_for_url("**/doctor/cases/*/timeline", timeout=10000)
        laxmi_url = page.url
        print(f"  -> Successfully navigated to Laxmi Timeline URL: {laxmi_url}")
        assert "/doctor/cases/CASE-LAXMI-008/timeline" in laxmi_url, "URL does not match canonical Laxmi case timeline route"
        assert "/asha/" not in laxmi_url, "Incorrect cross-role route detected!"

        # Assert Laxmi Timeline Header & No Meena events
        await page.wait_for_selector("span:has-text('Laxmi Kamble')", timeout=10000)
        await page.wait_for_timeout(500)
        print("  -> Verified Laxmi header visible on timeline screen")
        
        body_text_laxmi = await page.locator("body").inner_text()
        assert "Laxmi Kamble" in body_text_laxmi, "Laxmi Kamble missing from page text"
        assert "Meena Bai" not in body_text_laxmi, "Cross-patient data leak: Meena Bai found in Laxmi's timeline!"
        print("  -> Verified Laxmi header, canonical caseId URL, and zero cross-patient data leakage.")

        # Save Screenshot: Laxmi Timeline 1440px
        screenshot_laxmi_1440 = os.path.join(SCREENSHOT_DIR, "doctor_case_timeline_1440.png")
        await page.screenshot(path=screenshot_laxmi_1440)
        print(f"  -> Saved screenshot: {screenshot_laxmi_1440}")

        # 3. Back to Dashboard
        print("\n[Step 3] Navigating Back to Doctor Dashboard...")
        back_btn = page.locator("button:has-text('Back to Dashboard')").first
        await back_btn.click()
        await page.wait_for_url("**/doctor/dashboard**", timeout=10000)
        print("  -> Successfully returned to Dashboard.")

        # 4. View Timeline for Meena Bai
        print("\n[Step 4] Testing View Timeline for Meena Bai...")
        meena_btn = page.locator("[data-testid='referral-card-CASE-MEENA-002'] button:has-text('View Timeline')").first
        await meena_btn.wait_for(state="visible", timeout=10000)
        await meena_btn.click()

        await page.wait_for_url("**/doctor/cases/*/timeline", timeout=10000)
        meena_url = page.url
        print(f"  -> Successfully navigated to Meena Timeline URL: {meena_url}")
        assert meena_url != laxmi_url, "Meena timeline URL is identical to Laxmi's URL!"

        await page.wait_for_selector("span:has-text('Meena Bai')", timeout=10000)
        await page.wait_for_timeout(500)
        print("  -> Verified Meena header visible on timeline screen")

        body_text_meena = await page.locator("body").inner_text()
        assert "Meena Bai" in body_text_meena, "Meena Bai missing from page text"
        assert "Laxmi Kamble" not in body_text_meena, "Cross-patient data leak: Laxmi Kamble found in Meena's timeline!"
        print("  -> Proved distinct Meena timeline opens with canonical caseId URL!")

        # 5. Responsive Viewports (390px Mobile & 768px Tablet)
        print("\n[Step 5] Testing Responsive Viewports for Case Timeline...")
        
        # Mobile 390x844
        mob_context = await browser.new_context(viewport={"width": 390, "height": 844})
        mob_page = await mob_context.new_page()
        await mob_page.goto(meena_url)
        # Auth headers shared via cookie/token in localStorage if any, or login
        await mob_page.goto(f"{PORTAL_URL}/login")
        await mob_page.wait_for_timeout(500)
        mob_dr_btn = mob_page.locator("button:has-text('Dr. Abhinav Sharma'), button:has-text('Doctor')").first
        if await mob_dr_btn.is_visible():
            await mob_dr_btn.click()
            await mob_page.locator("button:has-text('Sign In'), button:has-text('Log In')").first.click()
            await mob_page.wait_for_url("**/doctor/dashboard**")
        await mob_page.goto(meena_url)
        await mob_page.wait_for_selector("text=Meena Bai", timeout=8000)
        await mob_page.screenshot(path=os.path.join(SCREENSHOT_DIR, "doctor_case_timeline_390.png"))
        print("  -> Saved screenshot: doctor_case_timeline_390.png")

        # Tablet 768x1024
        tab_context = await browser.new_context(viewport={"width": 768, "height": 1024})
        tab_page = await tab_context.new_page()
        await tab_page.goto(f"{PORTAL_URL}/login")
        await tab_page.wait_for_timeout(500)
        tab_dr_btn = tab_page.locator("button:has-text('Dr. Abhinav Sharma'), button:has-text('Doctor')").first
        if await tab_dr_btn.is_visible():
            await tab_dr_btn.click()
            await tab_page.locator("button:has-text('Sign In'), button:has-text('Log In')").first.click()
            await tab_page.wait_for_url("**/doctor/dashboard**")
        await tab_page.goto(meena_url)
        await tab_page.wait_for_selector("text=Meena Bai", timeout=8000)
        await tab_page.screenshot(path=os.path.join(SCREENSHOT_DIR, "doctor_case_timeline_768.png"))
        print("  -> Saved screenshot: doctor_case_timeline_768.png")

        await context.close()
        await mob_context.close()
        await tab_context.close()
        await browser.close()

        print("\n=======================================================")
        print("  PLAYWRIGHT DOCTOR CASE TIMELINE VERIFICATION PASSED")
        print("=======================================================\n")

if __name__ == "__main__":
    asyncio.run(run_playwright_timeline_verification())
