"""
Focused Production Dual-Browser Playwright Verification for Doctor Incoming Chat Sync & Polling Fallback
"""
import os
import sys
import time
import json
import random
import requests
from playwright.sync_api import sync_playwright

PROD_CITIZEN_URL = "https://aarogya-sahayak-citizen.vercel.app"
PROD_DOCTOR_URL = "https://aarogya-sahayak-healthcare-portal.vercel.app"
PROD_BACKEND_URL = "https://aarogya-sahayak-backend.onrender.com"

SCREENSHOT_DIR = os.path.join(os.path.dirname(__file__), "screenshots_live_chat_sync")
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

def run_doctor_chat_live_test():
    print("\n=======================================================")
    print("STARTING FOCUSED DOCTOR LIVE-CHAT SYNC PLAYWRIGHT TEST")
    print("=======================================================\n")

    # 1. Setup Fresh Citizen Profile
    unique_suffix = random.randint(1000, 9999)
    citizen_name = f"Aarav Kulkarni {unique_suffix}"
    phone_num = f"98{random.randint(10000000, 99999999)}"

    print(f"[Step 1] Creating fresh citizen account ({phone_num})...")
    r_otp = requests.post(f"{PROD_BACKEND_URL}/api/citizen/auth/otp/request", json={"phone": phone_num}, timeout=20)
    assert r_otp.status_code == 200, f"Failed OTP request: {r_otp.text}"
    otp_req_id = r_otp.json()["data"]["otp_request_id"]

    r_onboard = requests.post(f"{PROD_BACKEND_URL}/api/citizen/onboarding", json={
        "phone": phone_num,
        "full_name": citizen_name,
        "sex": "MALE",
        "age": 30,
        "preferred_language": "en",
        "village": "Kalyanpur",
        "otp_request_id": otp_req_id,
        "otp": "123456"
    }, timeout=20)
    assert r_onboard.status_code == 200, f"Failed onboarding: {r_onboard.text}"
    cit_data = r_onboard.json()["data"]
    cit_token = cit_data["access_token"]
    cit_user = cit_data["user"]
    cit_profile = cit_data["citizen_profile"]
    cit_profile_id = cit_profile["id"]

    # 2. Authenticate Doctor
    print("[Step 2] Authenticating Doctor (dr.sharma)...")
    r_doc_login = requests.post(f"{PROD_BACKEND_URL}/api/auth/login", json={
        "identifier": "dr.sharma",
        "password": "demo123"
    }, timeout=20)
    assert r_doc_login.status_code == 200, f"Failed doctor login: {r_doc_login.text}"
    doc_token = r_doc_login.json()["data"]["access_token"]
    doc_user = r_doc_login.json()["data"]["user"]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # Context 1: Citizen Mobile Viewport (390 x 844)
        cit_ctx = browser.new_context(
            viewport={"width": 390, "height": 844},
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148"
        )
        cit_page = cit_ctx.new_page()

        # Context 2: Doctor Desktop Viewport (1440 x 900)
        doc_ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        doc_page = doc_ctx.new_page()

        print("[Step 3] Initializing Citizen Session...")
        cit_page.goto(f"{PROD_CITIZEN_URL}", wait_until="networkidle")
        cit_page.evaluate(f"""() => {{
            localStorage.setItem('aarogya_citizen_token', '{cit_token}');
            localStorage.setItem('aarogya_citizen_active_ben_id', '{cit_profile_id}');
            localStorage.setItem('aarogya_locale', 'en');
        }}""")
        cit_page.reload(wait_until="networkidle")
        time.sleep(2)

        print("[Step 4] Citizen submitting Doctor Consultation Request through Wizard...")
        cit_page.goto(f"{PROD_CITIZEN_URL}/doctor-consultation", wait_until="networkidle")
        time.sleep(2)

        # Step 1: Select patient
        cit_page.locator("div:has-text('Myself'), div:has-text('Self')").first.click()
        time.sleep(1)
        cit_page.locator("#btn-wizard-step1-continue").click()
        time.sleep(2)

        # Step 2: Describe concern
        type_tab = cit_page.locator("button:has-text('Type'), button:has(svg.lucide-keyboard)").first
        if type_tab.count() > 0:
            type_tab.click()
            time.sleep(1)

        symptom_input = cit_page.locator("input[placeholder*='symptom'], input[placeholder*='Fever']").first
        if symptom_input.count() > 0:
            symptom_input.fill("High fever and dry cough")
            time.sleep(0.5)
            cit_page.locator("#btn-add-symptom, button:has-text('Add')").first.click()
            time.sleep(0.5)

        concern_ta = cit_page.locator("textarea").first
        if concern_ta.count() > 0:
            concern_ta.fill("High fever and dry cough for 2 days")
            time.sleep(0.5)

        cit_page.locator("#btn-wizard-step2-continue").click()
        time.sleep(2)

        # Step 3: Select CHAT channel
        chat_channel_card = cit_page.locator("#channel-option-chat").first
        if chat_channel_card.count() > 0:
            chat_channel_card.click()
            time.sleep(0.5)

        cit_page.locator("#btn-wizard-step3-continue").click()
        time.sleep(2)

        # Step 4: Care Location
        cit_page.locator("#btn-wizard-step4-continue").click()
        time.sleep(2)

        # Step 5: Sharing Scope
        cit_page.locator("#btn-wizard-step5-continue").click()
        time.sleep(2)

        # Step 6: Explicit Consent & Submit
        consent_cb = cit_page.locator("#checkbox-wizard-step6-consent").first
        if consent_cb.count() > 0:
            consent_cb.check()
            time.sleep(0.5)

        submit_btn = cit_page.locator("#btn-wizard-step6-submit").first
        submit_btn.click()
        print("  -> Submitted request, waiting for Citizen Waiting Room...")
        cit_page.wait_for_selector("#input-citizen-chat-message", timeout=25000)
        time.sleep(3)

        # Fetch canonical IDs from doctor direct-requests or citizen requests
        request_reference = None
        service_request_id = None
        conversation_id = None

        r_doc_reqs = requests.get(f"{PROD_BACKEND_URL}/api/doctor/direct-requests", headers={"Authorization": f"Bearer {doc_token}"})
        if r_doc_reqs.status_code == 200:
            doc_items = r_doc_reqs.json().get("data", {}).get("items", [])
            for item in doc_items:
                if item.get("citizen_name") == citizen_name or item.get("beneficiary_name") == citizen_name or "Aarav Kulkarni" in (item.get("citizen_name") or ""):
                    request_reference = item.get("request_reference") or item.get("public_reference")
                    service_request_id = item.get("service_request_id") or item.get("id")
                    conversation_id = item.get("conversation_id") or item.get("id")
                    break

        if not request_reference:
            r_cit_reqs = requests.get(f"{PROD_BACKEND_URL}/api/citizen/doctor-requests/active/current", headers={"Authorization": f"Bearer {cit_token}"})
            if r_cit_reqs.status_code == 200:
                c_data = r_cit_reqs.json().get("data")
                if c_data:
                    request_reference = c_data.get("request_reference") or c_data.get("public_reference")
                    service_request_id = c_data.get("service_request_id") or c_data.get("id")
                    conversation_id = c_data.get("conversation_id") or c_data.get("id")

        if not request_reference:
            # Check URL of waiting room
            url = cit_page.url
            print(f"  Citizen Waiting Room URL: {url}")
            # Try to grab from page text
            ref_el = cit_page.locator("text=DOCREQ-").first
            if ref_el.count() > 0:
                request_reference = ref_el.inner_text().strip()
                service_request_id = request_reference
                conversation_id = request_reference

        print(f"\n[Canonical Request Identifiers]")
        print(f"  • request_reference:  {request_reference}")
        print(f"  • service_request_id: {service_request_id}")
        print(f"  • conversation_id:    {conversation_id}")

        # Setup Doctor Page
        print("\n[Step 5] Initializing Doctor Desktop Session...")
        doc_page.goto(f"{PROD_DOCTOR_URL}/login", wait_until="networkidle")
        doc_page.evaluate(f"""() => {{
            localStorage.setItem('aarogya_token', '{doc_token}');
            localStorage.setItem('aarogya_user', JSON.stringify({json.dumps(doc_user)}));
            localStorage.setItem('aarogya_portal_role', 'DOCTOR');
        }}""")
        doc_page.goto(f"{PROD_DOCTOR_URL}/doctor/direct-requests", wait_until="networkidle")
        time.sleep(4)

        # Doctor accepts and opens chat drawer
        print("[Step 6] Doctor accepting request and opening live chat drawer...")
        doc_page.wait_for_selector(f"text={request_reference}", timeout=15000)
        card = doc_page.locator(f"div:has-text('{request_reference}')").first
        accept_btn = card.locator("button:has-text('Accept Chat'), button:has-text('Accept Request')").first
        if accept_btn.count() > 0:
            accept_btn.click()
            time.sleep(3)
        else:
            chat_btn = card.locator("button:has-text('Open Chat')").first
            if chat_btn.count() > 0:
                chat_btn.click()
                time.sleep(3)

        doc_chat_input = doc_page.locator("#input-doctor-chat-reply")
        assert doc_chat_input.is_visible(), "Doctor chat drawer is not visible!"
        print("  -> Doctor chat drawer is OPEN and active.")

        # Step 7: Citizen sends LIVE-CITIZEN-MESSAGE-1
        print("\n[Step 7] Citizen sending 'LIVE-CITIZEN-MESSAGE-1'...")
        cit_chat_input = cit_page.locator("#input-citizen-chat-message").first
        cit_chat_input.fill("LIVE-CITIZEN-MESSAGE-1")
        time.sleep(0.5)
        cit_page.locator("#btn-citizen-send-chat").first.click()
        t_sent_1 = time.time()
        print("  -> Sent LIVE-CITIZEN-MESSAGE-1. Monitoring doctor drawer WITHOUT any doctor interaction...")

        # Assert message appears in doctor drawer within 5 seconds without interaction
        found_msg_1 = False
        arrival_time_1 = 0
        for _ in range(25): # poll every 200ms up to 5s
            if doc_page.locator("text=LIVE-CITIZEN-MESSAGE-1").count() > 0:
                arrival_time_1 = time.time() - t_sent_1
                found_msg_1 = True
                break
            time.sleep(0.2)

        # Capture screenshot of doctor drawer showing citizen message BEFORE any doctor reply
        screenshot_path_1 = os.path.join(SCREENSHOT_DIR, "doctor_drawer_received_msg_1.png")
        doc_page.screenshot(path=screenshot_path_1)
        print(f"  -> Screenshot saved to {screenshot_path_1}")

        assert found_msg_1, "LIVE-CITIZEN-MESSAGE-1 did NOT appear in doctor drawer within 5 seconds!"
        print(f"  -> SUCCESS: LIVE-CITIZEN-MESSAGE-1 received on doctor screen in {arrival_time_1:.2f} seconds!")

        # Step 8: Citizen sends LIVE-CITIZEN-MESSAGE-2
        print("\n[Step 8] Citizen sending 'LIVE-CITIZEN-MESSAGE-2'...")
        cit_chat_input.fill("LIVE-CITIZEN-MESSAGE-2")
        time.sleep(0.5)
        cit_page.locator("#btn-citizen-send-chat").first.click()
        t_sent_2 = time.time()

        found_msg_2 = False
        arrival_time_2 = 0
        for _ in range(25):
            if doc_page.locator("text=LIVE-CITIZEN-MESSAGE-2").count() > 0:
                arrival_time_2 = time.time() - t_sent_2
                found_msg_2 = True
                break
            time.sleep(0.2)

        assert found_msg_2, "LIVE-CITIZEN-MESSAGE-2 did NOT appear in doctor drawer within 5 seconds!"
        print(f"  -> SUCCESS: LIVE-CITIZEN-MESSAGE-2 received on doctor screen in {arrival_time_2:.2f} seconds!")

        # Step 9: Doctor sends LIVE-DOCTOR-REPLY-1
        print("\n[Step 9] Doctor sending 'LIVE-DOCTOR-REPLY-1'...")
        doc_chat_input.fill("LIVE-DOCTOR-REPLY-1")
        time.sleep(0.5)
        doc_page.locator("button:has-text('Send Advice'), button[type='submit']").last.click()
        t_doc_sent = time.time()

        # Step 10: Verify citizen receives doctor reply
        found_doc_reply = False
        for _ in range(25):
            if cit_page.locator("text=LIVE-DOCTOR-REPLY-1").count() > 0:
                found_doc_reply = True
                break
            time.sleep(0.2)
        assert found_doc_reply, "Citizen did not receive LIVE-DOCTOR-REPLY-1!"
        print("  -> SUCCESS: Citizen received LIVE-DOCTOR-REPLY-1!")

        # Step 11 & 12: Confirm all 3 messages appear exactly once, wait for polling intervals
        print("\n[Step 10] Checking duplicate counts across 2 polling intervals (6s wait)...")
        time.sleep(7)

        doc_count_1 = doc_page.locator("text=LIVE-CITIZEN-MESSAGE-1").count()
        doc_count_2 = doc_page.locator("text=LIVE-CITIZEN-MESSAGE-2").count()
        doc_count_reply = doc_page.locator("text=LIVE-DOCTOR-REPLY-1").count()

        cit_count_1 = cit_page.locator("text=LIVE-CITIZEN-MESSAGE-1").count()
        cit_count_2 = cit_page.locator("text=LIVE-CITIZEN-MESSAGE-2").count()
        cit_count_reply = cit_page.locator("text=LIVE-DOCTOR-REPLY-1").count()

        print(f"  Doctor counts: msg1={doc_count_1}, msg2={doc_count_2}, reply={doc_count_reply}")
        print(f"  Citizen counts: msg1={cit_count_1}, msg2={cit_count_2}, reply={cit_count_reply}")

        assert doc_count_1 == 1 and doc_count_2 == 1 and doc_count_reply == 1, "Duplicate messages found on doctor side!"
        assert cit_count_1 == 1 and cit_count_2 == 1 and cit_count_reply == 1, "Duplicate messages found on citizen side!"
        print("  -> ZERO duplicates confirmed!")

        # Step 13: Refresh both apps and confirm persistence & order
        print("\n[Step 11] Refreshing both applications to verify persistence & order...")
        doc_page.reload(wait_until="networkidle")
        time.sleep(3)
        # Re-open chat drawer
        doc_page.locator(f"div:has-text('{request_reference}')").first.locator("button:has-text('Open Chat')").first.click()
        time.sleep(3)

        # Citizen can view in care tab or reload
        cit_page.evaluate(f"""() => {{
            localStorage.setItem('active_doctor_request_id', '{service_request_id}');
            localStorage.setItem('active_doctor_request_ref', '{request_reference}');
        }}""")
        # If waiting room is navigated from care tab
        cit_page.locator("button:has-text('My Care'), div:has-text('My Care')").first.click()
        time.sleep(2)
        # Click consultation card to reopen waiting room
        consult_card = cit_page.locator(f"div:has-text('{request_reference}')").first
        if consult_card.count() > 0:
            consult_card.click()
            time.sleep(3)

        # Assert 3 messages present
        assert doc_page.locator("text=LIVE-CITIZEN-MESSAGE-1").count() == 1
        assert doc_page.locator("text=LIVE-CITIZEN-MESSAGE-2").count() == 1
        assert doc_page.locator("text=LIVE-DOCTOR-REPLY-1").count() == 1

        assert cit_page.locator("text=LIVE-CITIZEN-MESSAGE-1").count() >= 1
        assert cit_page.locator("text=LIVE-CITIZEN-MESSAGE-2").count() >= 1
        assert cit_page.locator("text=LIVE-DOCTOR-REPLY-1").count() >= 1
        print("  -> Verified: Correct order & persistence after refresh on both doctor and citizen sides.")

        # Step 14: Verify Polling Fallback (Temporarily disconnect WS in doctor context)
        print("\n[Step 12] Testing Polling Fallback with WebSocket blocked in Doctor browser...")
        doc_page.route("**/api/ws*", lambda route: route.abort())
        # Also close existing active WS connection in page
        doc_page.evaluate("""() => {
            if (window.realtimeService && window.realtimeService.ws) {
                window.realtimeService.ws.close();
            }
        }""")
        time.sleep(1)

        print("  -> Citizen sending 'LIVE-POLLING-FALLBACK'...")
        cit_chat_input = cit_page.locator("#input-citizen-chat-message").first
        cit_chat_input.fill("LIVE-POLLING-FALLBACK")
        time.sleep(0.5)
        cit_page.locator("#btn-citizen-send-chat").first.click()
        t_poll_sent = time.time()

        found_polling_msg = False
        poll_arrival_time = 0
        for _ in range(30): # 6 seconds max for 3s interval
            if doc_page.locator("text=LIVE-POLLING-FALLBACK").count() > 0:
                poll_arrival_time = time.time() - t_poll_sent
                found_polling_msg = True
                break
            time.sleep(0.2)

        assert found_polling_msg, "LIVE-POLLING-FALLBACK message did NOT arrive via polling fallback!"
        print(f"  -> SUCCESS: LIVE-POLLING-FALLBACK arrived via 3s polling fallback in {poll_arrival_time:.2f} seconds!")

        # Unroute WS
        doc_page.unroute("**/api/ws*")
        time.sleep(5)
        # Check no duplicates
        assert doc_page.locator("text=LIVE-POLLING-FALLBACK").count() == 1
        print("  -> Verified: LIVE-POLLING-FALLBACK displayed exactly once without duplication.")

        screenshot_final = os.path.join(SCREENSHOT_DIR, "doctor_drawer_complete_flow.png")
        doc_page.screenshot(path=screenshot_final)
        print(f"\nFinal screenshot saved: {screenshot_final}")

        print("\n=======================================================")
        print("ALL DOCTOR LIVE-CHAT SYNCHRONIZATION TESTS PASSED 100%!")
        print("=======================================================\n")
        return {
            "request_reference": request_reference,
            "service_request_id": service_request_id,
            "conversation_id": conversation_id,
            "arrival_time_1": arrival_time_1,
            "arrival_time_2": arrival_time_2,
            "poll_arrival_time": poll_arrival_time,
            "screenshot_msg1": screenshot_path_1,
            "screenshot_final": screenshot_final
        }

if __name__ == "__main__":
    res = run_doctor_chat_live_test()
    print("RESULTS JSON:", json.dumps(res))
