import time
import requests
import sys

PROD_BACKEND_URL = "https://aarogya-sahayak-backend.onrender.com/api"

def verify_live_staff_management():
    print("=== LIVE PRODUCTION VERIFICATION FOR STAFF MANAGEMENT ===")
    
    # 1. Check health
    health_url = "https://aarogya-sahayak-backend.onrender.com/health"
    try:
        r = requests.get(health_url, timeout=30)
        print(f"Health check status: {r.status_code}")
    except Exception as e:
        print(f"Health check error (waking up server): {e}")
        time.sleep(15)

    # 2. Login as District Admin
    print("\n1. Logging in as District Admin (dho.admin)...")
    login_res = requests.post(f"{PROD_BACKEND_URL}/auth/login", json={"identifier": "dho.admin", "password": "demo123"}, timeout=30)
    if login_res.status_code != 200:
        print(f"FAILED Admin login: {login_res.status_code} {login_res.text}")
        sys.exit(1)
    
    admin_token = login_res.json()["data"]["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}
    print("[OK] District Admin authenticated.")

    # 3. Create ASHA Worker on live backend
    rand_suffix = int(time.time()) % 10000
    asha_payload = {
        "name": f"Pooja Live ASHA {rand_suffix}",
        "role": "ASHA_WORKER",
        "phone": f"98231{rand_suffix:05d}",
        "employee_id": f"EMP-ASHA-PROD-{rand_suffix}",
        "preferred_language": "mr-IN",
        "district": "District 04",
        "village_name": "Kalyanpur",
        "coverage_area": "North Kalyanpur Zone"
    }
    print(f"\n2. Creating live ASHA worker: {asha_payload['name']}...")
    asha_res = requests.post(f"{PROD_BACKEND_URL}/admin/staff", json=asha_payload, headers=admin_headers, timeout=30)
    if asha_res.status_code != 201:
        print(f"FAILED to create ASHA worker: {asha_res.status_code} {asha_res.text}")
        sys.exit(1)
    
    creds_asha = asha_res.json()["data"]
    print(f"[OK] ASHA worker created with Staff ID: {creds_asha['staff_id']}")
    print(f"[OK] One-time Temporary Password: {creds_asha['temporary_password']}")

    # 4. Create PHC Doctor on live backend
    doc_payload = {
        "name": f"Dr. Rohan Live Doc {rand_suffix}",
        "role": "PHC_DOCTOR",
        "phone": f"98232{rand_suffix:05d}",
        "employee_id": f"EMP-DOC-PROD-{rand_suffix}",
        "medical_registration_number": f"MMC-PROD-{rand_suffix}",
        "specialization": "General Medicine",
        "preferred_language": "mr-IN",
        "district": "District 04"
    }
    print(f"\n3. Creating live PHC Doctor: {doc_payload['name']}...")
    doc_res = requests.post(f"{PROD_BACKEND_URL}/admin/staff", json=doc_payload, headers=admin_headers, timeout=30)
    if doc_res.status_code != 201:
        print(f"FAILED to create PHC doctor: {doc_res.status_code} {doc_res.text}")
        sys.exit(1)
    
    creds_doc = doc_res.json()["data"]
    print(f"[OK] PHC Doctor created with Staff ID: {creds_doc['staff_id']}")
    print(f"[OK] One-time Temporary Password: {creds_doc['temporary_password']}")

    # 5. Sign in as newly created ASHA -> verify mandatory password change requirement
    print(f"\n4. Verifying ASHA first sign-in ({creds_asha['staff_id']})...")
    asha_login_res = requests.post(
        f"{PROD_BACKEND_URL}/auth/login",
        json={"identifier": creds_asha["staff_id"], "password": creds_asha["temporary_password"]},
        timeout=30
    )
    if asha_login_res.status_code != 200:
        print(f"FAILED ASHA login: {asha_login_res.status_code} {asha_login_res.text}")
        sys.exit(1)
    
    asha_login_data = asha_login_res.json()["data"]
    assert asha_login_data["user"]["must_change_password"] is True
    print("[OK] Initial sign-in succeeded with must_change_password=True flag.")

    # 6. Change password for ASHA
    print("\n5. Executing mandatory password change for ASHA...")
    asha_token = asha_login_data["access_token"]
    new_asha_pwd = "AshaNewSecurePassword2026!"
    ch_res = requests.post(
        f"{PROD_BACKEND_URL}/auth/change-password",
        json={"old_password": creds_asha["temporary_password"], "new_password": new_asha_pwd},
        headers={"Authorization": f"Bearer {asha_token}"},
        timeout=30
    )
    if ch_res.status_code != 200:
        print(f"FAILED password change: {ch_res.status_code} {ch_res.text}")
        sys.exit(1)
    print("[OK] Password successfully updated.")

    # 7. Verify ASHA accesses scoped ASHA dashboard
    relogin_asha = requests.post(
        f"{PROD_BACKEND_URL}/auth/login",
        json={"identifier": creds_asha["staff_id"], "password": new_asha_pwd},
        timeout=30
    )
    assert relogin_asha.status_code == 200
    assert relogin_asha.json()["data"]["user"]["must_change_password"] is False
    updated_asha_token = relogin_asha.json()["data"]["access_token"]
    
    dash_res = requests.get(
        f"{PROD_BACKEND_URL}/asha/dashboard",
        headers={"Authorization": f"Bearer {updated_asha_token}"},
        timeout=30
    )
    assert dash_res.status_code == 200
    print("[OK] Newly created ASHA successfully signed in with new password and reached /asha/dashboard!")

    # 8. Sign in as newly created Doctor -> change password -> access doctor dashboard
    print(f"\n6. Verifying Doctor first sign-in ({creds_doc['staff_id']})...")
    doc_login_res = requests.post(
        f"{PROD_BACKEND_URL}/auth/login",
        json={"identifier": creds_doc["staff_id"], "password": creds_doc["temporary_password"]},
        timeout=30
    )
    assert doc_login_res.status_code == 200
    doc_token = doc_login_res.json()["data"]["access_token"]
    
    new_doc_pwd = "DocNewSecurePassword2026!"
    doc_ch_res = requests.post(
        f"{PROD_BACKEND_URL}/auth/change-password",
        json={"old_password": creds_doc["temporary_password"], "new_password": new_doc_pwd},
        headers={"Authorization": f"Bearer {doc_token}"},
        timeout=30
    )
    assert doc_ch_res.status_code == 200

    relogin_doc = requests.post(
        f"{PROD_BACKEND_URL}/auth/login",
        json={"identifier": creds_doc["staff_id"], "password": new_doc_pwd},
        timeout=30
    )
    assert relogin_doc.status_code == 200
    updated_doc_token = relogin_doc.json()["data"]["access_token"]

    doc_dash_res = requests.get(
        f"{PROD_BACKEND_URL}/doctor/dashboard",
        headers={"Authorization": f"Bearer {updated_doc_token}"},
        timeout=30
    )
    assert doc_dash_res.status_code == 200
    print("[OK] Newly created Doctor successfully signed in with new password and reached /doctor/dashboard!")

    print("\n=======================================================")
    print("ALL LIVE PRODUCTION VERIFICATION TESTS PASSED 100%!")
    print("=======================================================")

if __name__ == "__main__":
    verify_live_staff_management()
