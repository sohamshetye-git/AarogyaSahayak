import urllib.request
import urllib.error
import json
import time

BASE = "http://127.0.0.1:8000/api"
HEALTH_URL = "http://127.0.0.1:8000/health"

print("==================================================")
print("VERIFYING CORE AAROGYA SAHAYAK API WORKFLOW")
print("==================================================")

def request(method, endpoint, data=None, token=None):
    url = f"{BASE}{endpoint}" if not endpoint.startswith("http") else endpoint
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(data).encode("utf-8") if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        res = urllib.request.urlopen(req, timeout=10)
        return res.status, json.loads(res.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8")
        try:
            err_json = json.loads(err_body)
        except:
            err_json = err_body
        return e.code, err_json
    except Exception as e:
        return 0, str(e)

# 0. Health check
status, res = request("GET", HEALTH_URL)
assert status == 200, f"Health check failed: {status}"
print(f"Health Check Passed: {res}")

# 1. Citizen case creation (Sunita Devi maternal red flag)
citizen_payload = {
    "preferred_language": "mr-IN",
    "spoken_transcript": "मला खूप डोकेदुखी होत आहे आणि डोळ्यांसमोर अंधारी येत आहे. पायावर सूज आली आहे.",
    "symptoms": ["blurred vision", "severe headache", "swollen feet"],
    "is_pregnant": True,
    "gestational_weeks": 28,
    "vitals": {"systolic_bp": 150, "diastolic_bp": 100, "spo2": 97}
}
status, res = request("POST", "/citizen/cases", citizen_payload)
assert status == 200, f"Case creation failed: {res}"
case_data = res["data"]
case_id = case_data["case_id"]
case_ref = case_data["case_reference"]
print(f"Step 1: Case Created: {case_ref} | ID: {case_id}")
print(f"        Priority: {case_data['priority']} | Safety Rule Triggered: {case_data['safety_rule_triggered']}")

# 2. ASHA login
asha_payload = {"identifier": "sita.asha", "password": "demo123"}
status, res = request("POST", "/auth/login", asha_payload)
assert status == 200, f"ASHA login failed: {res}"
asha_token = res["data"]["access_token"]
print(f"Step 2: ASHA Worker Sita Patel Logged In. Role: {res['data']['user']['role']}")

# 3. ASHA Acknowledgement (NEW -> ASHA_ACKNOWLEDGED)
status, res = request("POST", f"/asha/cases/{case_id}/acknowledge", {}, token=asha_token)
assert status == 200, f"ASHA ack failed: {res}"
print(f"Step 3: ASHA Acknowledged Case. Status updated to: {res['data']['status']}")

# 4. Contact result (ASHA_ACKNOWLEDGED -> CITIZEN_CONTACTED)
contact_payload = {
    "outcome": "SPOKE_TO_CITIZEN",
    "next_action": "PLAN_VISIT",
    "notes": "Spoke to Sunita Devi and planned a home visit immediately."
}
status, res = request("POST", f"/asha/cases/{case_id}/contact-result", contact_payload, token=asha_token)
assert status == 200, f"Contact result failed: {res}"
print(f"Step 4: Contact Result Recorded. Status updated to: {res['data']['status']}")

# 5. Field visit & vitals submission (CITIZEN_CONTACTED -> ASHA_REVIEWED -> REFERRED_TO_PHC)
visit_payload = {
    "case_id": case_id,
    "consent_obtained": True,
    "symptoms": ["blurred vision", "severe headache", "swollen feet"],
    "vitals": {"systolic_bp": 150, "diastolic_bp": 100, "spo2": 97, "pulse": 88, "temperature_c": 37.0},
    "notes": "Confirmed high blood pressure during home visit. Pregnancy is 7 months (28 weeks). Referring to PHC.",
    "next_action": "REFER_TO_PHC",
    "refer_to_facility_id": "PHC-09"
}
status, res = request("POST", "/asha/visits", visit_payload, token=asha_token)
assert status == 200, f"Field visit failed: {res}"
print(f"Step 5 & 6: ASHA Conducted Field Visit & Referred. Status updated to: {res['data']['case_status']}")
print(f"            Referral Reference: {res['data']['referral_reference']}")

# 7. Doctor login & Acknowledge (REFERRED_TO_PHC -> DOCTOR_ACKNOWLEDGED)
doc_payload = {"identifier": "dr.sharma", "password": "demo123"}
status, res = request("POST", "/auth/login", doc_payload)
assert status == 200, f"Doctor login failed: {res}"
doc_token = res["data"]["access_token"]
print(f"Step 7a: PHC Doctor Dr. Abhinav Sharma Logged In. Role: {res['data']['user']['role']}")

status, res = request("POST", f"/doctor/referrals/{case_id}/acknowledge", {}, token=doc_token)
assert status == 200, f"Doctor ack failed: {res}"
print(f"Step 7b: Doctor Acknowledged Referral. Status updated to: {res['data']['status']}")

# 8. Doctor consultation (DOCTOR_ACKNOWLEDGED -> FOLLOW_UP_REQUIRED)
consultation_payload = {
    "case_id": case_id,
    "examination_notes": "Patient reports severe headache and blurry vision. Vitals measured by ASHA confirmed: BP 150/100, SpO2 97%.",
    "clinical_summary": "Confirmed gestational hypertension with pre-eclampsia indicators. Commencing Labetalol 100mg twice daily.",
    "confirmed_diagnosis": "Gestational Hypertension with Pre-eclampsia",
    "icd10_code": "O14.9",
    "prescription_items": [
        {
            "medicine": "Labetalol",
            "strength": "100mg",
            "dose": "1 tablet",
            "frequency": "Twice daily",
            "duration": "14 days",
            "instructions": "Take after food. Monitor blood pressure twice daily."
        }
    ],
    "investigation_orders": ["CBC", "Urine Albumin (Dipstick)"],
    "care_plan_summary": "Strict left-lateral bed rest. Low salt intake. ASHA to check blood pressure every 3 days.",
    "asha_followup_instructions": "Visit patient every 3 days. Record vitals. Verify compliance with Labetalol.",
    "followup_due_days": 3
}
status, res = request("POST", "/doctor/consultations", consultation_payload, token=doc_token)
assert status == 200, f"Doctor consultation failed: {res}"
print(f"Step 8: Doctor Completed Consultation. Status updated to: {res['data']['status']}")

# 9. ASHA follow-up check
status, res = request("GET", "/asha/tasks", token=asha_token)
assert status == 200, f"ASHA task list failed: {res}"
tasks = res["data"]
followups = [t for t in tasks if t["status"] == "FOLLOW_UP_REQUIRED"]
print(f"Step 9: Checked ASHA Task List. Found {len(followups)} active follow-ups. Target Case ID present: {any(t['case_id'] == case_id for t in tasks)}")

# 10. Admin Aggregation PII check
admin_payload = {"identifier": "dho.admin", "password": "demo123"}
status, res = request("POST", "/auth/login", admin_payload)
assert status == 200, f"Admin login failed: {res}"
admin_token = res["data"]["access_token"]

status, res = request("GET", "/admin/dashboard", token=admin_token)
assert status == 200, f"Admin dashboard failed: {res}"
admin_dash = res["data"]
print("Step 10: Admin Dashboard Loaded successfully.")
print(f"         Total Cases: {admin_dash['summary']['total_cases']}")
print(f"         Maternal High Risk Cases: {admin_dash['summary']['maternal_high_risk_cases']}")
raw_admin_text = json.dumps(admin_dash)
has_pii = "9876543210" in raw_admin_text or "12-3456-7890-1234" in raw_admin_text or "Sunita" in raw_admin_text
print(f"         PII Leak Check (Should be False): {has_pii}")

print("\n==================================================")
print("CORE WORKFLOW VERIFICATION COMPLETED SUCCESSFULLY!")
print("==================================================")
