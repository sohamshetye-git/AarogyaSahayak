import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import os
import time
from playwright.sync_api import sync_playwright

SCREENSHOT_DIR = r"C:\Users\lenovo\.gemini\antigravity-ide\brain\2403270a-13e3-4be2-84fd-c75287acffb2\screenshots"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

languages = [
    {"code": "hi-IN", "name": "Hindi", "prefix": "hi"},
    {"code": "mr-IN", "name": "Marathi", "prefix": "mr"},
    {"code": "gu-IN", "name": "Gujarati", "prefix": "gu"}
]

def run_i18n_test():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        
        for lang in languages:
            print(f"\n================ Running for {lang['name']} ({lang['code']}) ================", flush=True)
            context = browser.new_context(viewport={"width": 430, "height": 932})
            page = context.new_page()
            
            # Step 1: Open App
            page.goto("http://localhost:3001")
            page.wait_for_timeout(1000)
            
            # If on Language Selection Screen, select language and continue
            if page.locator("#btn-language-continue").is_visible():
                page.locator("#btn-language-continue").click()
                page.wait_for_timeout(1000)
                
            # If on Entry Screen, click Continue with Mobile OTP
            if page.locator("#btn-entry-mobile-otp").is_visible():
                page.locator("#btn-entry-mobile-otp").click()
                page.wait_for_timeout(1000)
                
                # Fresh unique phone number to avoid OTP cooldown
                phone = f"98765{int(time.time()) % 100000:05d}"
                page.locator("#input-citizen-phone").fill(phone)
                page.wait_for_timeout(500)
                page.locator("#btn-citizen-send-otp").click()
                page.wait_for_timeout(2500)
                
                # Enter OTP digits (Backend mock code 123456)
                page.locator("#otp-input-0").wait_for(state="visible", timeout=10000)
                digits = "123456"
                for i in range(6):
                    page.locator(f"#otp-input-{i}").press_sequentially(digits[i])
                    page.wait_for_timeout(100)
                page.wait_for_timeout(2500)
                
                # If Onboarding Screen appears for new phone
                if page.locator("#btn-onboarding-submit").is_visible():
                    page.locator("#input-onboarding-fullname").fill("Sunita Devi")
                    page.locator("#btn-onboarding-submit").click()
                    page.wait_for_timeout(2500)

            # Wait for authenticated Home Screen
            page.locator("#bar-authenticated-identity-context").wait_for(state="attached", timeout=10000)
            print("Successfully reached Authenticated HomeScreen!", flush=True)

            # Set language using all storage keys including scoped key and reload
            page.evaluate("""(code) => {
                localStorage.setItem("aarogya:locale:citizen", code);
                localStorage.setItem("aarogya_citizen_lang", code);
                localStorage.setItem("aarogya_preferred_language", code);
                localStorage.setItem("preferred_language", code);
                localStorage.setItem("aarogya_locale", code);
                localStorage.setItem("aarogya_language_confirmed", "true");
                localStorage.setItem("aarogya_locale_confirmed", "true");
            }""", lang["code"])
            page.reload()
            page.wait_for_timeout(2000)

            # Click Speak to Doctor button on HomeScreen
            doc_btn = page.locator("button:has-text('डॉक्टर'), button:has-text('Doctor'), button:has-text('ડોક્ટર')").first
            doc_btn.click()
            page.wait_for_timeout(1500)
            
            # Wizard Step 1: Select Beneficiary -> Continue
            page.locator("#btn-wizard-step1-continue").wait_for(state="visible", timeout=10000)
            page.locator("#btn-wizard-step1-continue").click()
            page.wait_for_timeout(1500)

            # STEP 2: Describe Health Concern
            path_step2 = os.path.join(SCREENSHOT_DIR, f"{lang['prefix']}_step2_health_concern.png")
            page.screenshot(path=path_step2)
            print(f"Captured Step 2: {path_step2}", flush=True)

            # Step 2 -> Step 3
            page.locator("#btn-wizard-step2-continue").click()
            page.wait_for_timeout(1500)

            # Step 3 -> Step 4
            page.locator("#btn-wizard-step3-continue").click()
            page.wait_for_timeout(1500)

            # Step 4 -> Step 5
            page.locator("#btn-wizard-step4-continue").click()
            page.wait_for_timeout(1500)

            # STEP 5: Sharing Scope
            path_step5 = os.path.join(SCREENSHOT_DIR, f"{lang['prefix']}_step5_sharing_scope.png")
            page.screenshot(path=path_step5)
            print(f"Captured Step 5: {path_step5}", flush=True)

            # Step 5 -> Step 6
            page.locator("#btn-wizard-step5-continue").click()
            page.wait_for_timeout(1500)

            # STEP 6: Consent & Submit
            path_step6 = os.path.join(SCREENSHOT_DIR, f"{lang['prefix']}_step6_consent_submit.png")
            page.screenshot(path=path_step6)
            print(f"Captured Step 6: {path_step6}", flush=True)

            # Submit directly (explicitConsent defaults to true)
            page.locator("#btn-wizard-step6-submit").click()
            page.wait_for_timeout(3500)

            # WAITING ROOM
            path_wr = os.path.join(SCREENSHOT_DIR, f"{lang['prefix']}_waiting_room.png")
            page.screenshot(path=path_wr)
            print(f"Captured Waiting Room: {path_wr}", flush=True)

            # Navigate Back to Home via Waiting Room Header button if visible
            if page.locator("#btn-waiting-room-home").is_visible():
                page.locator("#btn-waiting-room-home").click()
                page.wait_for_timeout(1500)

            if page.locator("#nav-tab-care").is_visible():
                page.locator("#nav-tab-care").click()
                page.wait_for_timeout(2000)

            path_mc = os.path.join(SCREENSHOT_DIR, f"{lang['prefix']}_my_care.png")
            page.screenshot(path=path_mc)
            print(f"Captured My Care: {path_mc}", flush=True)

            context.close()

        browser.close()

if __name__ == "__main__":
    run_i18n_test()
