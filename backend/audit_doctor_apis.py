import requests
import json

BASE = 'http://localhost:8000/api'

def audit_api_truth():
    print("\n=======================================================")
    print("  VERIFYING REAL DOCTOR API TRUTH FROM POSTGRESQL")
    print("=======================================================\n")

    # 1. Doctor Login
    login_res = requests.post(f"{BASE}/auth/login", json={"identifier": "dr.sharma", "password": "demo123"}).json()
    doc_token = login_res.get("data", {}).get("access_token")
    if not doc_token:
        print("Login failed:", login_res)
        return

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
    status_counts = {}
    for r in refs_data:
        st = r.get('status')
        status_counts[st] = status_counts.get(st, 0) + 1
        print(f"  - Patient: {r.get('citizen_name')} | Status: {r.get('status')} | Urgency: {r.get('urgency')} | RefID: {r.get('id')}")

    print("\nReferrals Status Distribution:", json.dumps(status_counts, indent=2))

    # Doctor Consultation Workspace
    cons_res = requests.get(f"{BASE}/doctor/consultations", headers=doc_headers)
    print(f"\n[HTTP {cons_res.status_code}] Doctor Consultations Workspace API")
    cons_data = cons_res.json().get("data", [])
    if isinstance(cons_data, list):
        print(f"Total Workspace Consultations Returned: {len(cons_data)}")
    elif isinstance(cons_data, dict):
        print(f"Consultation Workspace Data Keys: {list(cons_data.keys())}")
        if 'consultations' in cons_data:
            print(f"Total Workspace Consultations Returned: {len(cons_data['consultations'])}")

if __name__ == "__main__":
    audit_api_truth()
