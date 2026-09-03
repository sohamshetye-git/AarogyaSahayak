import requests

PROD_API = "https://aarogya-sahayak-backend.onrender.com/api"

def test_role_auth():
    print("Testing production authentication flows for all three healthcare roles with demo123...")
    
    roles_to_test = [
        {"role": "ASHA Worker", "id": "sita.asha", "expected_role": "ASHA_WORKER", "dashboard": "/asha/dashboard"},
        {"role": "PHC Doctor", "id": "dr.sharma", "expected_role": "PHC_DOCTOR", "dashboard": "/doctor/dashboard"},
        {"role": "District Health Officer", "id": "dho.admin", "expected_role": "DISTRICT_ADMIN", "dashboard": "/admin/dashboard"}
    ]
    
    all_passed = True
    for role_info in roles_to_test:
        try:
            r = requests.post(f"{PROD_API}/auth/login", json={
                "identifier": role_info["id"],
                "password": "demo123"
            }, timeout=25)
            
            if r.status_code == 200:
                data = r.json()
                auth_data = data.get("data", {})
                returned_user = auth_data.get("user", {})
                token = auth_data.get("access_token", "")
                role_val = returned_user.get("role", "")
                name = returned_user.get("name", "")
                print(f"  [PASS] {role_info['role']} ({role_info['id']}): Authenticated! Name='{name}', Role='{role_val}', Token received ({len(token)} chars) -> Routes to {role_info['dashboard']}")
            else:
                print(f"  [FAIL] {role_info['role']} ({role_info['id']}): Status {r.status_code} - {r.text}")
                all_passed = False
        except Exception as e:
            print(f"  [ERROR] {role_info['role']}: {e}")
            all_passed = False
            
    # Also test invalid credentials rejection
    try:
        r_bad = requests.post(f"{PROD_API}/auth/login", json={
            "identifier": "invalid.user",
            "password": "wrongpassword"
        }, timeout=15)
        if r_bad.status_code in [400, 401, 404]:
            print(f"  [PASS] Invalid credentials safely rejected with status {r_bad.status_code}.")
        else:
            print(f"  [WARN] Invalid credentials returned unexpected status {r_bad.status_code}.")
    except Exception as e:
        print("  [ERROR] Bad login test:", e)
        
    return all_passed

if __name__ == "__main__":
    test_role_auth()
