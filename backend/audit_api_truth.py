import requests
import json

BASE = 'http://localhost:8000/api'

def audit_api_truth():
    print("\n=======================================================")
    print("  VERIFYING REAL API TRUTH FROM POSTGRESQL DATABASE")
    print("=======================================================\n")

    # 1. Doctor Login
    login_res = requests.post(f"{BASE}/auth/login", json={"identifier": "dr.sharma", "password": "demo123"}).json()
    doc_token = login_res.get("data", {}).get("token")
    doc_headers = {"Authorization": f"Bearer {doc_token}"}

    # Doctor Dashboard
    dash_res = requests.get(f"{BASE}/doctor/dashboard", headers=doc_headers)
    print(f"[HTTP {dash_res.status_code}] Doctor Dashboard API")
    dash_data = dash_res.json().get("data", {})
    metrics = dash_data.get("metrics", {})
    print("Doctor Dashboard Metrics:")
    print(json.dumps(metrics, indent=2))

    # Doctor Referrals List
    refs_res = requests.get(f"{BASE}/doctor/referrals", headers=doc_headers)
    print(f"\n[HTTP {refs_res.status_code}] Doctor Referrals API")
    refs_data = refs_res.json().get("data", [])
    print(f"Total Referrals Returned: {len(refs_data)}")
    for r in refs_data:
        print(f"  - Patient: {r.get('citizen_name')} | Status: {r.get('status')} | Priority: {r.get('urgency')} | ReferralID: {r.get('id')}")

    # 2. ASHA Login & Dashboard
    asha_login = requests.post(f"{BASE}/auth/login", json={"identifier": "sita.asha", "password": "demo123"}).json()
    asha_token = asha_login.get("data", {}).get("token")
    asha_headers = {"Authorization": f"Bearer {asha_token}"}
    asha_dash = requests.get(f"{BASE}/asha/dashboard", headers=asha_headers)
    print(f"\n[HTTP {asha_dash.status_code}] ASHA Dashboard API")
    print("ASHA Dashboard Metrics:")
    print(json.dumps(asha_dash.json().get("data", {}).get("metrics", {}), indent=2))

    # 3. Admin Login & Aggregates
    admin_login = requests.post(f"{BASE}/auth/login", json={"identifier": "dho.admin", "password": "demo123"}).json()
    admin_token = admin_login.get("data", {}).get("token")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    admin_dash = requests.get(f"{BASE}/admin/dashboard", headers=admin_headers)
    print(f"\n[HTTP {admin_dash.status_code}] District Admin Aggregates API (Anonymized)")
    print("Admin Metrics:")
    print(json.dumps(admin_dash.json().get("data", {}).get("metrics", {}), indent=2))

if __name__ == "__main__":
    audit_api_truth()
