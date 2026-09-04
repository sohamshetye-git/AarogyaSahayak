import time
import requests
import sys

PROD_BACKEND_URL = "https://aarogya-sahayak-backend.onrender.com/api"

def wait_for_render_deploy():
    print("Polling Render backend until latest build with /admin/staff is deployed...")
    max_attempts = 30
    for i in range(1, max_attempts + 1):
        try:
            # Try logging in as admin
            login_res = requests.post(f"{PROD_BACKEND_URL}/auth/login", json={"identifier": "dho.admin", "password": "demo123"}, timeout=15)
            if login_res.status_code == 200:
                token = login_res.json()["data"]["access_token"]
                staff_res = requests.get(f"{PROD_BACKEND_URL}/admin/staff", headers={"Authorization": f"Bearer {token}"}, timeout=15)
                if staff_res.status_code == 200:
                    print(f"Render build deployed! /admin/staff endpoint returned 200 OK (Attempt {i})")
                    return True
                else:
                    print(f"Attempt {i}/{max_attempts}: /admin/staff returned {staff_res.status_code} (still deploying old image)...")
            else:
                print(f"Attempt {i}/{max_attempts}: /auth/login returned {login_res.status_code}...")
        except Exception as e:
            print(f"Attempt {i}/{max_attempts}: Connection wait ({e})...")
        time.sleep(10)
    return False

if __name__ == "__main__":
    deployed = wait_for_render_deploy()
    if not deployed:
        print("Timeout waiting for Render deployment.")
        sys.exit(1)
    
    # Run verification test once deployed
    from test_live_staff_management_prod import verify_live_staff_management
    verify_live_staff_management()
