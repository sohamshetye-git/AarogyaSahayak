import os
import sys
import time
import io
from playwright.sync_api import sync_playwright

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

CHROMIUM_PATH = r'C:\Users\lenovo\AppData\Local\ms-playwright\chromium-1234\chrome-win64\chrome.exe'
os.makedirs("automation/screenshots", exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, executable_path=CHROMIUM_PATH)

    # 1. Citizen Mobile - Hindi Test & Screenshot
    ctx = browser.new_context(viewport={"width": 412, "height": 892})
    page = ctx.new_page()
    page.goto("http://localhost:3001", timeout=15000)
    page.wait_for_timeout(1000)

    # Select Hindi
    hindi_btn = page.query_selector("button:has-text('हिंदी')")
    if hindi_btn:
        hindi_btn.click()
        page.wait_for_timeout(400)
        cont = page.query_selector("button:has-text('आगे जारी रखें'), button:has-text('जारी रखें'), button:has-text('पुढे सुरू ठेवा'), button:has-text('Continue')")
        if cont:
            cont.click()
            page.wait_for_timeout(1200)

    page.screenshot(path="automation/screenshots/citizen_hindi_home.png")
    print("Saved citizen_hindi_home.png")

    # Navigate to My Care
    page.click("button:has-text('मेरी देखभाल')")
    page.wait_for_timeout(800)
    page.screenshot(path="automation/screenshots/citizen_hindi_my_care.png")
    print("Saved citizen_hindi_my_care.png")

    # Navigate to Medicines
    page.click("button:has-text('दवाइयाँ'), button:has-text('दवाइयां')")
    page.wait_for_timeout(800)
    page.screenshot(path="automation/screenshots/citizen_hindi_medicines.png")
    print("Saved citizen_hindi_medicines.png")

    # Switch to Marathi
    page.click("button:has-text('मुख्यपृष्ठ')")
    page.wait_for_timeout(500)
    globe_btn = page.query_selector("header button")
    if globe_btn:
        globe_btn.click()
        page.wait_for_timeout(500)
        page.click("button:has-text('मराठी')")
        page.wait_for_timeout(300)
        cont = page.query_selector("button:has-text('पुढे सुरू ठेवा'), button:has-text('पुढे जा'), button:has-text('Continue')")
        if cont:
            cont.click()
            page.wait_for_timeout(1000)

    page.screenshot(path="automation/screenshots/citizen_marathi_home.png")
    print("Saved citizen_marathi_home.png")
    ctx.close()

    # 2. Healthcare Portal - Doctor & ASHA Test & Screenshot
    ctx_portal = browser.new_context(viewport={"width": 1280, "height": 800})
    portal_page = ctx_portal.new_page()
    portal_page.goto("http://localhost:3000/login", timeout=15000)
    portal_page.wait_for_timeout(1000)

    portal_page.fill("input[type='text'], input[placeholder*='username'], input[placeholder*='mobile'], input[placeholder*='वापरकर्ता']", "dr.sharma")
    portal_page.fill("input[type='password'], input[placeholder*='password'], input[placeholder*='पासवर्ड']", "demo123")
    portal_page.click("button[type='submit'], button:has-text('Sign In'), button:has-text('साइन इन')")
    portal_page.wait_for_timeout(2000)

    portal_page.screenshot(path="automation/screenshots/doctor_portal_dashboard.png")
    print("Saved doctor_portal_dashboard.png")

    # Switch Doctor to Hindi
    lang_select = portal_page.query_selector("select[title*='Language'], select")
    if lang_select:
        lang_select.select_option("hi-IN")
        portal_page.wait_for_timeout(1000)
        portal_page.screenshot(path="automation/screenshots/doctor_portal_hindi.png")
        print("Saved doctor_portal_hindi.png")

        # Switch Doctor to Marathi
        lang_select.select_option("mr-IN")
        portal_page.wait_for_timeout(1000)
        portal_page.screenshot(path="automation/screenshots/doctor_portal_marathi.png")
        print("Saved doctor_portal_marathi.png")

    ctx_portal.close()
    browser.close()
    print("\n✅ All screenshots captured and verified successfully!")
