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
        
    doc_btn = page.locator('button:has-text("डॉक्टर"), button:has-text("Doctor"), button:has-text("ડોક્ટર")').first
    doc_btn.click()
    page.wait_for_timeout(1500)
    print('URL:', page.url)
    print('Modal or Wizard visible?')
    count = page.locator('button').count()
    print('Total buttons:', count)
    for i in range(count):
        btn = page.locator('button').nth(i)
        txt = btn.inner_text().strip()
        vis = btn.is_visible()
        print(f'Btn {i}: text="{txt}", visible={vis}')
    browser.close()
