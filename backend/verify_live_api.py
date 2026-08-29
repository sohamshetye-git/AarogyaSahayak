import requests, sys

base = "http://localhost:8000/api"

# 1. Login
r = requests.post(f"{base}/auth/login", json={"identifier": "sita.asha", "password": "demo123"}, timeout=10)
assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
token = r.json()["data"]["access_token"]
headers = {"Authorization": f"Bearer {token}"}
print("[1] LOGIN: OK")

# 2. GET all followups
r2 = requests.get(f"{base}/asha/followups", headers=headers, timeout=10)
assert r2.status_code == 200, f"Followups failed: {r2.status_code} {r2.text}"
fups = r2.json()["data"]
print(f"[2] GET /asha/followups: {len(fups)} returned")
for f in fups[:5]:
    name = f.get("citizen_name", "?")
    src = f.get("source", "?")
    status = f.get("status", "?")
    due = (f.get("due_at") or "N/A")[:10]
    instr = (f.get("instructions") or "")[:50]
    print(f"    - {name} | {src} | {status} | Due:{due} | {instr}")

# 3. OVERDUE filter
r3 = requests.get(f"{base}/asha/followups?status_filter=OVERDUE", headers=headers, timeout=10)
assert r3.status_code == 200
od = r3.json()["data"]
print(f"[3] OVERDUE filter: {len(od)} results")

# 4. DOCTOR source filter
r4 = requests.get(f"{base}/asha/followups?source_filter=DOCTOR", headers=headers, timeout=10)
assert r4.status_code == 200
doc = r4.json()["data"]
print(f"[4] DOCTOR filter: {len(doc)} results")

# 5. ASHA_SCHEDULED filter
r5 = requests.get(f"{base}/asha/followups?source_filter=ASHA_SCHEDULED", headers=headers, timeout=10)
assert r5.status_code == 200
asha = r5.json()["data"]
print(f"[5] ASHA_SCHEDULED filter: {len(asha)} results")

# 6. COMPLETED filter
r6 = requests.get(f"{base}/asha/followups?status_filter=COMPLETED", headers=headers, timeout=10)
assert r6.status_code == 200
comp = r6.json()["data"]
print(f"[6] COMPLETED filter: {len(comp)} results")

# 7. Fetch a single followup detail
if fups:
    fid = fups[0]["id"]
    r7 = requests.get(f"{base}/asha/followups/{fid}", headers=headers, timeout=10)
    assert r7.status_code == 200, f"Detail failed: {r7.status_code}"
    detail = r7.json()["data"]
    print(f"[7] GET /asha/followups/{fid}: status={detail.get('status')}, citizen={detail.get('citizen_name')}")
else:
    print("[7] No followups to detail-test")

print("\nALL LIVE API CHECKS PASSED")
