import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={'width': 430, 'height': 932})
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
    print('Clicked Speak to Doctor. Is Continue with OTP button visible?', page.locator('#btn-protected-continue-otp').is_visible())
    
    page.locator('#btn-protected-continue-otp').click()
    page.wait_for_timeout(1000)
    print('Phone input visible?', page.locator('#input-citizen-phone').is_visible())
    
    page.locator('#input-citizen-phone').fill('9876543210')
    page.wait_for_timeout(500)
    page.locator('#btn-citizen-send-otp').click()
    page.wait_for_timeout(2500)
    print('OTP inputs visible?', page.locator('#otp-input-0').is_visible())
    
    digits = '123456'
    for i in range(6):
        page.locator(f'#otp-input-{i}').press_sequentially(digits[i])
        page.wait_for_timeout(100)
    page.wait_for_timeout(3000)
    
    print('After OTP verified, current Wizard Step / Heading:', page.locator('h2').all_inner_texts())
    print('Wizard buttons:', [b.inner_text().strip() for b in page.locator('main button').all() if b.is_visible()])
    browser.close()
