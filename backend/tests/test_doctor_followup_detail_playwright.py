"""
Playwright E2E Verification Script for Doctor Portal Follow-Up Detail Status & Data Consistency
"""

import sys
import os
import time
from playwright.sync_api import sync_playwright

SCREENSHOT_DIR = os.path.join(os.path.dirname(__file__), "screenshots")
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

def run_playwright_test():
    print("\n=======================================================")
    print("  PLAYWRIGHT FOLLOW-UP DETAIL DATA CONSISTENCY TEST")
    print("=======================================================\n")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        page.add_init_script("""
            localStorage.setItem('aarogya_token', 'mock-doctor-token');
            localStorage.setItem('auth_token', 'mock-doctor-token');
            localStorage.setItem('aarogya_user', JSON.stringify({
                id: 'DOC-007',
                name: 'Dr. Abhinav Sharma',
                role: 'PHC_DOCTOR',
                username: 'dr.sharma'
            }));
        """)

        # -------------------------------------------------------------
        # TEST 1: Pending Follow-up (FUP-003: Laxmi Kamble)
        # -------------------------------------------------------------
        print("[Step 1] Navigating to Pending Follow-Up FUP-003 (Laxmi Kamble)...")
        page.goto("http://localhost:3000/doctor/followups/FUP-003", wait_until="networkidle")
        time.sleep(1)

        # Assert correct header info
        patient_name = page.query_selector("span:has-text('Laxmi Kamble')")
        assert patient_name is not None, "Patient name Laxmi Kamble must be rendered"

        # Assert status
        status_elem = page.query_selector("div:has-text('Status: PENDING')")
        assert status_elem is not None, "Status must show PENDING / OVERDUE"

        # Assert doctor identity is NOT Sita Patel
        doctor_elem = page.query_selector("span:has-text('Assigned Doctor:')")
        assert doctor_elem is not None
        doc_text = doctor_elem.inner_text()
        print(f"  -> Assigned Doctor Text: {doc_text}")
        assert "Sita Patel" not in doc_text, "ASHA worker Sita Patel must not be rendered as Assigned Doctor"

        # Assert ASHA Visit result shows "Visit Not Started / Awaiting ASHA Visit"
        visit_status_elem = page.query_selector("*:has-text('Visit Not Started')") or page.query_selector("*:has-text('Awaiting ASHA Visit')")
        assert visit_status_elem is not None, "Pending visit must show visit not started / awaiting"

        # Assert no fake "IMPROVED" or fake completion notes
        notes_box = page.query_selector("*:has-text('Measured BP and verified medication adherence')")
        assert notes_box is None, "Pending visit must NOT show completed visit notes"

        # Assert repeat vitals show awaiting
        awaiting_vitals = page.query_selector("*:has-text('Awaiting ASHA visit')")
        assert awaiting_vitals is not None, "Repeat measurements column must show 'Awaiting ASHA visit'"

        # Assert available actions on Pending
        call_asha_btn = page.query_selector("button:has-text('Call ASHA')")
        assert call_asha_btn is not None, "Pending follow-up must have Call ASHA button"
        modify_dir_btn = page.query_selector("button:has-text('Modify Directive')")
        assert modify_dir_btn is not None, "Pending follow-up must have Modify Directive button"
        resched_btn = page.query_selector("button:has-text('Reschedule')")
        assert resched_btn is not None, "Pending follow-up must have Reschedule button"

        # Assert 'Accept Result & Mark Reviewed' is NOT available
        review_btn = page.query_selector("button:has-text('Accept Result & Mark Reviewed')")
        assert review_btn is None, "Pending follow-up must NOT offer Mark Reviewed action"

        fup3_shot = os.path.join(SCREENSHOT_DIR, "followup_detail_fup003_pending_1440.png")
        page.screenshot(path=fup3_shot)
        print(f"  -> Saved screenshot: followup_detail_fup003_pending_1440.png")

        # -------------------------------------------------------------
        # TEST 2: Completed Follow-up (FUP-005: Sunita Devi / Routine BP)
        # -------------------------------------------------------------
        print("\n[Step 2] Navigating to Completed Follow-Up FUP-005...")
        page.goto("http://localhost:3000/doctor/followups/FUP-005", wait_until="networkidle")
        time.sleep(2)

        # Print page text snippet for debug
        content_text = page.content()
        buttons = page.query_selector_all("button")
        button_texts = [b.inner_text().encode("ascii", "ignore").decode() for b in buttons]
        print(f"  -> Rendered Buttons on FUP-005: {button_texts}")

        # Assert status text
        assert "COMPLETED" in content_text or "COMPLETED BY ASHA" in content_text, "FUP-005 status must be COMPLETED"

        # Assert symptom outcome IMPROVED is shown
        assert "IMPROVED" in content_text, "Completed visit must show actual symptom outcome IMPROVED"

        # Assert review decision buttons are present
        mark_reviewed_btn = page.query_selector("button:has-text('Mark Reviewed')")
        assert mark_reviewed_btn is not None, "Completed visit must have Mark Reviewed button"

        fup5_shot = os.path.join(SCREENSHOT_DIR, "followup_detail_fup005_completed_1440.png")
        page.screenshot(path=fup5_shot)
        print("  -> Saved screenshot: followup_detail_fup005_completed_1440.png")

        context.close()
        browser.close()

    print("\n=======================================================")
    print("  PLAYWRIGHT FOLLOW-UP DETAIL DATA CONSISTENCY PASSED")
    print("=======================================================\n")

if __name__ == "__main__":
    run_playwright_test()
