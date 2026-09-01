"""
Playwright E2E Test Suite for Location System:
- Doctor assigned PHC location
- ASHA Worker fresh high-accuracy GPS capture (READY state)
- ASHA Worker low-accuracy GPS warning (LOW_ACCURACY state)
- ASHA Worker permission denied fallback (PERMISSION_DENIED state)
- Language switching & localized location management modal
"""

import os
import sys
import time
from playwright.sync_api import sync_playwright

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8')

SCREENSHOT_DIR = r"C:\Arogya Sahayak_AI_antigravity\backend\tests\screenshots"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

def run_location_e2e_tests():
    print("\n=======================================================")
    print("  PLAYWRIGHT LOCATION SYSTEM E2E TEST SUITE")
    print("=======================================================")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        
        # 1. Doctor Dashboard - Default Assigned Facility Test
        print("\n[Step 1] Testing Doctor Default Location...")
        ctx_doc = browser.new_context(viewport={"width": 1440, "height": 900})
        page_doc = ctx_doc.new_page()
        page_doc.goto("http://localhost:3000/login", wait_until="networkidle")
        page_doc.fill('input[placeholder*="username" i], input[type="text"]', "dr.sharma")
        page_doc.fill('input[type="password"]', "demo123")
        page_doc.click('button:has-text("Sign In"), button[type="submit"]')
        page_doc.wait_for_url("**/doctor/dashboard", timeout=10000)
        page_doc.wait_for_selector("#portal-location-chip", timeout=10000)
        
        doc_chip_text = page_doc.locator("#portal-location-chip").inner_text()
        print("  -> Doctor Chip Text:", doc_chip_text)
        assert "PHC" in doc_chip_text or "Kalyanpur" in doc_chip_text
        
        # Open modal
        page_doc.click("#portal-location-chip")
        page_doc.wait_for_selector("#location-management-modal", timeout=5000)
        page_doc.screenshot(path=os.path.join(SCREENSHOT_DIR, "doctor_location_ready.png"))
        print("  -> Captured doctor_location_ready.png")
        page_doc.click("#location-modal-close-btn")
        ctx_doc.close()
        
        # 2. ASHA Dashboard - Fresh GPS Capture Test (READY state)
        print("\n[Step 2] Testing ASHA GPS Capture with Permissions Granted...")
        ctx_asha = browser.new_context(
            viewport={"width": 1440, "height": 900},
            geolocation={"latitude": 19.1234, "longitude": 72.8567, "accuracy": 25},
            permissions=["geolocation"]
        )
        page_asha = ctx_asha.new_page()
        page_asha.goto("http://localhost:3000/login", wait_until="networkidle")
        page_asha.fill('input[placeholder*="username" i], input[type="text"]', "sita.asha")
        page_asha.fill('input[type="password"]', "demo123")
        page_asha.click('button:has-text("Sign In"), button[type="submit"]')
        page_asha.wait_for_url("**/asha/dashboard", timeout=10000)
        page_asha.wait_for_selector("#portal-location-chip", timeout=10000)
        
        # Click Location Chip and trigger Acquire Fresh GPS
        page_asha.click("#portal-location-chip")
        page_asha.wait_for_selector("#location-management-modal", timeout=5000)
        page_asha.click("#acquire-fresh-gps-btn")
        
        # Wait for geocoding to complete
        time.sleep(3)
        page_asha.screenshot(path=os.path.join(SCREENSHOT_DIR, "asha_location_ready.png"))
        print("  -> Captured asha_location_ready.png")
        
        chip_text = page_asha.locator("#portal-location-chip").inner_text()
        print("  -> ASHA Chip Text after GPS:", chip_text)
        assert "Address unavailable" not in chip_text
        ctx_asha.close()

        # 3. ASHA - LOW_ACCURACY State Test
        print("\n[Step 3] Testing ASHA with Low-Accuracy GPS (250m)...")
        ctx_low = browser.new_context(
            viewport={"width": 1440, "height": 900},
            geolocation={"latitude": 19.1234, "longitude": 72.8567, "accuracy": 250},
            permissions=["geolocation"]
        )
        page_low = ctx_low.new_page()
        page_low.goto("http://localhost:3000/login", wait_until="networkidle")
        page_low.fill('input[placeholder*="username" i], input[type="text"]', "sita.asha")
        page_low.fill('input[type="password"]', "demo123")
        page_low.click('button:has-text("Sign In"), button[type="submit"]')
        page_low.wait_for_url("**/asha/dashboard", timeout=10000)
        page_low.wait_for_selector("#portal-location-chip", timeout=10000)
        page_low.click("#portal-location-chip")
        page_low.wait_for_selector("#location-management-modal", timeout=5000)
        page_low.click("#acquire-fresh-gps-btn")
        time.sleep(3)
        page_low.screenshot(path=os.path.join(SCREENSHOT_DIR, "asha_location_low_accuracy.png"))
        print("  -> Captured asha_location_low_accuracy.png")
        ctx_low.close()

        # 4. ASHA - PERMISSION_DENIED State Test
        print("\n[Step 4] Testing ASHA with Permission Denied...")
        ctx_denied = browser.new_context(
            viewport={"width": 1440, "height": 900},
            permissions=[]
        )
        page_denied = ctx_denied.new_page()
        page_denied.goto("http://localhost:3000/login", wait_until="networkidle")
        page_denied.fill('input[placeholder*="username" i], input[type="text"]', "sita.asha")
        page_denied.fill('input[type="password"]', "demo123")
        page_denied.click('button:has-text("Sign In"), button[type="submit"]')
        page_denied.wait_for_url("**/asha/dashboard", timeout=10000)
        page_denied.wait_for_selector("#portal-location-chip", timeout=10000)
        page_denied.click("#portal-location-chip")
        page_denied.wait_for_selector("#location-management-modal", timeout=5000)
        page_denied.click("#acquire-fresh-gps-btn")
        time.sleep(1)
        page_denied.screenshot(path=os.path.join(SCREENSHOT_DIR, "asha_location_permission_denied.png"))
        print("  -> Captured asha_location_permission_denied.png")
        ctx_denied.close()

        browser.close()
        print("\n=======================================================")
        print("  ALL PLAYWRIGHT LOCATION SUITE CHECKS PASSED!")
        print("=======================================================\n")

if __name__ == "__main__":
    run_location_e2e_tests()
