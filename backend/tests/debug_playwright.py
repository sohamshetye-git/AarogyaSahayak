import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import os
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={'width': 430, 'height': 932})
    page.goto('http://localhost:3001')
    page.wait_for_timeout(1000)
    print('URL:', page.url)
    
    if page.locator('#btn-language-continue').is_visible():
        print('Clicking language continue...')
        page.locator('#btn-language-continue').click()
        page.wait_for_timeout(1000)
        
    if page.locator('#btn-entry-mobile-otp').is_visible():
        print('Clicking mobile OTP...')
        page.locator('#btn-entry-mobile-otp').click()
        page.wait_for_timeout(1000)
        
        page.locator('#input-citizen-phone').fill('9876543210')
        page.wait_for_timeout(500)
        print('Phone entered, send OTP button enabled?:', page.locator('#btn-citizen-send-otp').is_enabled())
        page.locator('#btn-citizen-send-otp').click()
        page.wait_for_timeout(2500)
        print('Inputs count:', page.locator('input').count())
        for i in range(page.locator('input').count()):
            inp = page.locator('input').nth(i)
            print(f'Input {i}: id={inp.get_attribute("id")}, type={inp.get_attribute("type")}')
        
    browser.close()
