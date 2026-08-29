import pytest
import time
from playwright.sync_api import sync_playwright, expect

def test_citizen_auth_persistence_and_refresh_e2e():
    """
    E2E Test:
    1. Open Citizen Mobile app on http://localhost:3001
    2. Handle Language selection if on language screen -> proceed to Entry Screen
    3. Choose 'Continue with Mobile', enter demo number '9876543201', enter OTP '123456'
    4. Handle Onboarding or Beneficiary Selection if prompted
    5. Confirm Authenticated Home loads with canonical identity context
    6. Reload page (browser refresh) -> confirm session is restored automatically without OTP prompt
    7. Confirm Guest mode badge is absent and authenticated identity context is preserved
    8. Logout -> confirm return to entry screen and reload requires authentication
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        try:
            page.goto("http://localhost:3001", wait_until="networkidle")
            page.wait_for_timeout(1000)

            # 1. Handle Language selection if presented
            try:
                lang_btn = page.wait_for_selector("button:has-text('मराठी')", timeout=2000)
                if lang_btn:
                    lang_btn.click()
                    page.wait_for_timeout(500)
                    page.wait_for_selector("button:has-text('पुढे सुरू ठेवा')", timeout=2000).click()
                    page.wait_for_timeout(500)
            except Exception:
                pass

            # 2. On Entry Screen, click mobile login button
            page.wait_for_selector("#btn-entry-mobile-otp", timeout=8000).click()
            page.wait_for_timeout(500)

            # 3. Enter Phone Number (using unique test number to bypass cooldown)
            test_phone = f"98765{int(time.time()) % 100000:05d}"
            phone_input = page.wait_for_selector("#input-citizen-phone", timeout=5000)
            phone_input.fill(test_phone)
            page.wait_for_selector("#btn-citizen-send-otp", timeout=3000).click()
            page.wait_for_timeout(1500)

            # 4. Enter OTP (123456)
            page.wait_for_selector("#otp-input-0", timeout=8000)
            for idx, digit in enumerate("123456"):
                page.locator(f"#otp-input-{idx}").fill(digit)

            page.wait_for_timeout(2000)

            # If onboarding screen appears for fresh phone:
            try:
                name_input = page.wait_for_selector("#input-onboarding-fullname", timeout=3000)
                if name_input:
                    name_input.fill("Priya Sharma")
                    page.locator("#checkbox-onboarding-consent").check()
                    page.locator("#btn-onboarding-submit").click()
                    page.wait_for_timeout(2000)
            except Exception:
                pass

            # If beneficiary selection screen appears, select first beneficiary or click continue
            ben_card = page.locator("button[id^='btn-select-beneficiary-']").first
            if ben_card.is_visible():
                ben_card.click()
                page.wait_for_timeout(1000)

            ben_continue_btn = page.locator("button:has-text('पुढे जा'), button:has-text('Continue')").first
            if ben_continue_btn.is_visible():
                ben_continue_btn.click()
                page.wait_for_timeout(1000)

            page.screenshot(path="tests/screenshots/auth_flow_step1.png")
            
            # 5. Confirm Authenticated Home is rendered
            try:
                page.wait_for_selector("#bar-authenticated-identity-context, #btn-citizen-sign-out", timeout=8000)
            except Exception as e:
                page.screenshot(path="tests/screenshots/auth_flow_failure.png")
                raise e
            assert page.locator("#btn-citizen-sign-out").is_visible(), "Sign out button not visible on home screen!"
            assert not page.locator("text=Guest").first.is_visible()

            # 6. Browser Refresh (Page Reload)
            page.reload(wait_until="networkidle")
            page.wait_for_timeout(2500)
            page.screenshot(path="tests/screenshots/auth_flow_after_reload.png")

            # Confirm session is restored automatically without OTP screen
            assert page.locator("#btn-citizen-sign-out").is_visible(), "Session was not restored after page reload!"
            assert page.locator("#bar-authenticated-identity-context").is_visible(), "Identity context missing after reload!"
            assert not page.locator("input[placeholder*='98765']").is_visible(), "OTP login screen reappeared after reload!"

            # 7. Logout
            logout_btn = page.locator("#btn-citizen-sign-out").first
            logout_btn.click()
            page.wait_for_timeout(1500)

            # Confirm returned to entry selection and reload does not auto-login
            page.reload(wait_until="networkidle")
            page.wait_for_timeout(1500)
            assert not page.locator("#bar-authenticated-identity-context").is_visible(), "Session was not revoked after logout!"

        finally:
            browser.close()
