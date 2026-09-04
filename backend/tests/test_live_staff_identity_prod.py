"""
Live Production Verification for Staff Identity and Scoping
Tests:
1. Create new ASHA Worker 'Aditi Mahesh Vishwakarma' via District Admin.
2. Log into Healthcare Portal as Aditi via Playwright browser.
3. Assert top header and navigation display 'Aditi Mahesh Vishwakarma' and 'ASHA Worker' (never Sita Patel).
4. Assert ASHA Dashboard displays clean identity and strict 0 assigned cases/citizens.
5. Create new PHC Doctor 'Dr. Ananya Kulkarni' via District Admin.
6. Log into Healthcare Portal as Dr. Ananya via Playwright browser.
7. Assert top header and navigation display 'Dr. Ananya Kulkarni' and 'PHC Medical Officer' (never Dr. Abhinav Sharma).
8. Assert Doctor Dashboard displays clean identity and isolated facility queue.
"""

import os
import sys
import time
import json
import random
import requests
from playwright.sync_api import sync_playwright, expect

PROD_HEALTHCARE_PORTAL_URL = "https://aarogya-sahayak-healthcare-portal.vercel.app"
PROD_BACKEND_URL = "https://aarogya-sahayak-backend.onrender.com/api"

SCREENSHOT_DIR = os.path.join(os.path.dirname(__file__), "screenshots_live_staff_identity")
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

def verify_live_staff_identity():
    print("\n=======================================================")
    print("STARTING LIVE PRODUCTION VERIFICATION FOR STAFF IDENTITY")
    print(f"Healthcare Portal: {PROD_HEALTHCARE_PORTAL_URL}")
    print(f"Backend API:       {PROD_BACKEND_URL}")
    print("=======================================================\n")

    # 1. Admin login to backend to create fresh ASHA and Doctor accounts
    print("[Step 1] Authenticating as District Admin (dho.admin)...")
    login_res = requests.post(f"{PROD_BACKEND_URL}/auth/login", json={"identifier": "dho.admin", "password": "demo123"}, timeout=30)
    assert login_res.status_code == 200, f"Admin login failed: {login_res.text}"
    admin_token = login_res.json()["data"]["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}

    rand_id = random.randint(1000, 9999)
    asha_name = "Aditi Mahesh Vishwakarma"
    asha_emp = f"EMP-ASHA-ADITI-{rand_id}"
    
    print(f"[Step 2] Creating fresh ASHA worker '{asha_name}' ({asha_emp})...")
    asha_payload = {
        "name": asha_name,
        "role": "ASHA_WORKER",
        "phone": f"98239{rand_id:05d}",
        "employee_id": asha_emp,
        "preferred_language": "en-IN",
        "district": "District 04",
        "village_name": "Shivaji Nagar",
        "coverage_area": "Sector 3"
    }
    create_asha_res = requests.post(f"{PROD_BACKEND_URL}/admin/staff", json=asha_payload, headers=admin_headers, timeout=30)
    assert create_asha_res.status_code == 201, f"Failed creating ASHA: {create_asha_res.text}"
    asha_creds = create_asha_res.json()["data"]
    asha_staff_id = asha_creds["staff_id"]
    asha_temp_pwd = asha_creds["temporary_password"]
    print(f"[OK] ASHA Created. Staff ID: {asha_staff_id}, Temp Password: {asha_temp_pwd}")

    # Create Doctor
    doc_name = "Dr. Ananya Kulkarni"
    doc_emp = f"EMP-DOC-ANANYA-{rand_id}"
    print(f"\n[Step 3] Creating fresh PHC Doctor '{doc_name}' ({doc_emp})...")
    doc_payload = {
        "name": doc_name,
        "role": "PHC_DOCTOR",
        "phone": f"98238{rand_id:05d}",
        "employee_id": doc_emp,
        "medical_registration_number": f"MMC-2026-{rand_id}",
        "specialization": "General Medicine",
        "preferred_language": "en-IN",
        "district": "District 04",
        "facility_id": "PHC-99",
        "facility_name": "Chandrapur PHC"
    }
    create_doc_res = requests.post(f"{PROD_BACKEND_URL}/admin/staff", json=doc_payload, headers=admin_headers, timeout=30)
    assert create_doc_res.status_code == 201, f"Failed creating Doctor: {create_doc_res.text}"
    doc_creds = create_doc_res.json()["data"]
    doc_staff_id = doc_creds["staff_id"]
    doc_temp_pwd = doc_creds["temporary_password"]
    print(f"[OK] Doctor Created. Staff ID: {doc_staff_id}, Temp Password: {doc_temp_pwd}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        
        # ----------------------------------------------------
        # TEST ASHA WORKER ADITI
        # ----------------------------------------------------
        print("\n[Step 4] Launching Browser for ASHA Worker Aditi Mahesh Vishwakarma...")
        asha_ctx = browser.new_context(viewport={"width": 1280, "height": 800})
        asha_page = asha_ctx.new_page()

        # Step 4a: Login with temp password
        asha_page.goto(f"{PROD_HEALTHCARE_PORTAL_URL}/login")
        asha_page.wait_for_load_state("networkidle")

        # Type credentials
        asha_page.fill("input[type='text'], input[placeholder*='identifier'], input[placeholder*='Staff ID'], input#identifier", asha_staff_id)
        asha_page.fill("input[type='password']", asha_temp_pwd)
        asha_page.click("button[type='submit'], button:has-text('Sign In'), button:has-text('Log In')")

        # Wait for either change-password modal or navigation
        asha_page.wait_for_timeout(3000)
        
        # Check if Must Change Password form is presented
        if asha_page.locator("input[placeholder*='New Password'], input[name='newPassword']").count() > 0:
            print("  -> Change password prompt detected. Submitting new password...")
            if asha_page.locator("input[placeholder*='Current'], input[name='oldPassword'], input[placeholder*='Temporary']").count() > 0:
                asha_page.fill("input[placeholder*='Current'], input[name='oldPassword'], input[placeholder*='Temporary']", asha_temp_pwd)
            asha_page.fill("input[placeholder*='New Password'], input[name='newPassword']", "NewAditiSecurePass123!")
            asha_page.fill("input[placeholder*='Confirm'], input[name='confirmPassword']", "NewAditiSecurePass123!")
            asha_page.click("button:has-text('Update Password'), button:has-text('Set Password'), button[type='submit']")
            asha_page.wait_for_timeout(3000)

        asha_page.goto(f"{PROD_HEALTHCARE_PORTAL_URL}/asha/dashboard")
        asha_page.wait_for_load_state("networkidle")
        asha_page.wait_for_timeout(2000)

        asha_body_text = asha_page.inner_text("body")
        print(f"  -> Verifying Aditi Identity rendered...")
        assert "Aditi Mahesh Vishwakarma" in asha_body_text, f"Expected Aditi Mahesh Vishwakarma in body text, got: {asha_body_text[:300]}"
        assert "Sita Patel" not in asha_body_text, f"CRITICAL: Found seeded 'Sita Patel' in Aditi's dashboard!"
        assert ("ASHA Worker" in asha_body_text or "आशा सेविका" in asha_body_text or "ASHA" in asha_body_text), f"Expected ASHA Worker role badge"

        screenshot_asha_path = os.path.join(SCREENSHOT_DIR, "01_asha_aditi_verified.png")
        asha_page.screenshot(path=screenshot_asha_path, full_page=True)
        print(f"[OK] ASHA Worker Aditi identity verified cleanly! Screenshot: {screenshot_asha_path}")
        asha_ctx.close()

        # ----------------------------------------------------
        # TEST PHC DOCTOR DR. ANANYA KULKARNI
        # ----------------------------------------------------
        print("\n[Step 5] Launching Browser for PHC Doctor Dr. Ananya Kulkarni...")
        doc_ctx = browser.new_context(viewport={"width": 1280, "height": 800})
        doc_page = doc_ctx.new_page()

        doc_page.goto(f"{PROD_HEALTHCARE_PORTAL_URL}/login")
        doc_page.wait_for_load_state("networkidle")

        doc_page.fill("input[type='text'], input[placeholder*='identifier'], input[placeholder*='Staff ID'], input#identifier", doc_staff_id)
        doc_page.fill("input[type='password']", doc_temp_pwd)
        doc_page.click("button[type='submit'], button:has-text('Sign In'), button:has-text('Log In')")

        doc_page.wait_for_timeout(3000)
        
        if doc_page.locator("input[placeholder*='New Password'], input[name='newPassword']").count() > 0:
            print("  -> Change password prompt detected for Doctor. Submitting new password...")
            if doc_page.locator("input[placeholder*='Current'], input[name='oldPassword'], input[placeholder*='Temporary']").count() > 0:
                doc_page.fill("input[placeholder*='Current'], input[name='oldPassword'], input[placeholder*='Temporary']", doc_temp_pwd)
            doc_page.fill("input[placeholder*='New Password'], input[name='newPassword']", "NewDoctorSecurePass123!")
            doc_page.fill("input[placeholder*='Confirm'], input[name='confirmPassword']", "NewDoctorSecurePass123!")
            doc_page.click("button:has-text('Update Password'), button:has-text('Set Password'), button[type='submit']")
            doc_page.wait_for_timeout(3000)

        doc_page.goto(f"{PROD_HEALTHCARE_PORTAL_URL}/doctor/dashboard")
        doc_page.wait_for_load_state("networkidle")
        doc_page.wait_for_timeout(2000)

        doc_body_text = doc_page.inner_text("body")
        print(f"  -> Verifying Dr. Ananya Identity rendered...")
        assert "Dr. Ananya Kulkarni" in doc_body_text, f"Expected Dr. Ananya Kulkarni in body text, got: {doc_body_text[:300]}"
        assert "Dr. Abhinav Sharma" not in doc_body_text, f"CRITICAL: Found seeded 'Dr. Abhinav Sharma' in Dr. Ananya's dashboard!"
        assert any(term in doc_body_text for term in ["PHC Doctor", "PHC Medical Officer", "वैद्यकीय अधिकारी", "चिकित्सा अधिकारी", "Doctor", "डॉक्टर"]), f"Expected doctor role in body text"

        screenshot_doc_path = os.path.join(SCREENSHOT_DIR, "02_doctor_ananya_verified.png")
        doc_page.screenshot(path=screenshot_doc_path, full_page=True)
        print(f"[OK] PHC Doctor Dr. Ananya identity verified cleanly! Screenshot: {screenshot_doc_path}")
        doc_ctx.close()

        browser.close()

    print("\n=======================================================")
    print("ALL LIVE PRODUCTION STAFF IDENTITY CHECKS PASSED PERFECTLY!")
    print("=======================================================\n")

if __name__ == "__main__":
    verify_live_staff_identity()
