import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={'width': 430, 'height': 932})
    
    # Listen to console logs
    page.on("console", lambda msg: print(f"[Browser Console] {msg.type}: {msg.text}"))
    page.on("pageerror", lambda err: print(f"[Browser Error] {err}"))
    page.on("response", lambda res: print(f"[Network Response] {res.status} {res.url}") if "otp" in res.url else None)

    page.goto('http://localhost:3001')
    page.wait_for_timeout(1000)
    
    if page.locator('#btn-language-continue').is_visible():
        page.locator('#btn-language-continue').click()
        page.wait_for_timeout(1000)
        
    if page.locator('#btn-entry-guest-access').is_visible():
        page.locator('#btn-entry-guest-access').click()
        page.wait_for_timeout(2000)
        
    doc_btn = page.locator("button:has-text('Speak to Doctor'), button:has-text('डॉक्टर'), button:has-text('ડોક્ટર')").first
    doc_btn.click()
    page.wait_for_timeout(1000)
    
    page.locator('#btn-protected-continue-otp').click()
    page.wait_for_timeout(1000)
    
    page.locator('#input-citizen-phone').fill('9876543210')
    page.wait_for_timeout(500)
    print("Clicking Send OTP button...")
    page.locator('#btn-citizen-send-otp').click()
    page.wait_for_timeout(3000)
    
    print('Error message text:', page.locator('[style*="FEF2F2"]').all_inner_texts())
    print('OTP inputs count:', page.locator('input[type="tel"]').count())
    for i in range(page.locator('input[type="tel"]').count()):
        el = page.locator('input[type="tel"]').nth(i)
        print(f"Tel input {i}: id={el.get_attribute('id')}")
        
    browser.close()
