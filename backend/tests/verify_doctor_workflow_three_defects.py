import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import uuid
import time
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app.models import (
    User, CitizenProfile, HouseholdMember, ServiceRequest, CareHandoff,
    ServiceRequestStatusHistory, DoctorChatThread, DoctorChatMessage,
    TeleconsultationRequest, TeleconsultationMessage
)
from app.auth.security import create_access_token
from app.services.recent_activity_service import normalize_actor_name
from app.services.citizen_service import CitizenService

def test_verify_all_three_production_defects():
    print("\n=======================================================")
    print("RUNNING VERIFICATION SUITE FOR 3 PRODUCTION DEFECTS")
    print("=======================================================\n")

    client = TestClient(app)
    db = SessionLocal()

    try:
        # -------------------------------------------------------------
        # DEFECT 1 VERIFICATION: Patient List Deduplication & Doctor Title
        # -------------------------------------------------------------
        print("[TEST 1.1] Verifying Citizen Beneficiaries Deduplication...")
        
        # Ensure authenticated citizen with both profile and SELF household member
        test_cit_id = f"cit-test-{uuid.uuid4().hex[:6]}"
        test_phone = f"9198{int(time.time()*1000) % 100000000:08d}"
        test_cit_user = User(
            id=f"user-{uuid.uuid4().hex[:6]}",
            identifier=test_phone,
            phone=test_phone,
            name="Krishna Omkar Mohite",
            password_hash="mock_hash",
            role="CITIZEN",
            is_active=True
        )
        test_profile = CitizenProfile(
            id=test_cit_id,
            user_id=test_cit_user.id,
            display_name="Krishna Omkar Mohite",
            phone="919876543299",
            sex="MALE",
            age_estimate=32
        )
        self_hh = HouseholdMember(
            id=f"hh-self-{uuid.uuid4().hex[:6]}",
            citizen_id=test_cit_id,
            full_name="Krishna Omkar Mohite",
            relationship_type="SELF",
            sex="MALE",
            age=32,
            is_active=True
        )
        child_hh = HouseholdMember(
            id=f"hh-child-{uuid.uuid4().hex[:6]}",
            citizen_id=test_cit_id,
            full_name="Tanvi Mohite",
            relationship_type="CHILD",
            sex="FEMALE",
            age=7,
            is_active=True
        )
        db.add_all([test_cit_user, test_profile, self_hh, child_hh])
        db.commit()

        token = create_access_token({"sub": test_cit_user.id, "role": "CITIZEN", "phone": test_cit_user.phone})
        
        # Test GET /citizen/beneficiaries
        res = client.get("/api/citizen/beneficiaries", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
        res_json = res.json()
        payload = res_json.get("data") if isinstance(res_json, dict) else res_json
        bens = payload.get("items", []) if isinstance(payload, dict) else (payload if isinstance(payload, list) else [])
        
        self_items = [b for b in bens if isinstance(b, dict) and (b.get("relationship") == "SELF" or b.get("relationship_type") == "SELF")]
        print(f"  -> Found {len(self_items)} SELF record(s) in beneficiaries endpoint.")
        assert len(self_items) == 1, f"Defect 1 FAILED: Expected exactly 1 SELF record, got {len(self_items)}"
        assert self_items[0]["beneficiary_id"] == test_cit_id

        child_items = [b for b in bens if isinstance(b, dict) and (b.get("relationship") == "CHILD" or b.get("relationship_type") == "CHILD")]
        assert len(child_items) == 1, "Expected household child member to remain present"
        print("  -> Defect 1.1 PASSED: Duplicate SELF eliminated; household members preserved.")

        # Test Doctor Title Normalization
        print("\n[TEST 1.2] Verifying Doctor Title Normalization...")
        assert normalize_actor_name("Dr. Abhinav Sharma", role="PHC_DOCTOR") == "Dr. Abhinav Sharma"
        assert normalize_actor_name("Dr. Dr. Abhinav Sharma", role="PHC_DOCTOR") == "Dr. Abhinav Sharma"
        assert normalize_actor_name("Abhinav Sharma", role="PHC_DOCTOR") == "Dr. Abhinav Sharma"
        print("  -> Defect 1.2 PASSED: Double 'Dr. Dr.' strictly avoided.")

        # -------------------------------------------------------------
        # DEFECT 2 VERIFICATION: Bidirectional Chat Delivery & No Duplication
        # -------------------------------------------------------------
        print("\n[TEST 2] Verifying Realtime Chat Delivery & Message Deduplication...")
        
        # Create a test doctor
        doc_user = db.query(User).filter(User.role == "PHC_DOCTOR").first()
        if not doc_user:
            doc_user = User(
                id=f"doc-user-{uuid.uuid4().hex[:6]}",
                identifier="919876543200",
                phone="919876543200",
                name="Dr. Abhinav Sharma",
                password_hash="mock_hash",
                role="PHC_DOCTOR",
                facility_id="PHC-09",
                is_active=True
            )
            db.add(doc_user)
            db.commit()

        doc_token = create_access_token({"sub": doc_user.id, "role": "PHC_DOCTOR", "facility_id": "PHC-09"})

        # Create doctor consultation request
        create_res = client.post(
            "/api/citizen/doctor/requests",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "beneficiary_id": test_cit_id,
                "chief_complaint": "Persistent fever and headache",
                "symptoms": ["Fever", "Headache"],
                "channel": "CHAT"
            }
        )
        assert create_res.status_code == 200, f"Failed creating request: {create_res.text}"
        req_info = create_res.json().get("data", {})
        request_id = req_info["id"]
        srv_req_id = req_info.get("service_request_id") or request_id
        ref_code = req_info.get("request_reference")

        print(f"  -> Created Request: ID={request_id}, Ref={ref_code}")

        # Citizen sends message BEFORE doctor acceptance
        cit_client_msg_id = f"cmsg-{uuid.uuid4().hex[:8]}"
        msg_res1 = client.post(
            f"/api/citizen/doctor/requests/{request_id}/messages",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "message_text": "Doctor, my temperature is 101F since morning.",
                "body": "Doctor, my temperature is 101F since morning.",
                "client_message_id": cit_client_msg_id
            }
        )
        assert msg_res1.status_code == 200, f"Failed sending citizen message: {msg_res1.text}"
        print("  -> Citizen sent message before doctor acceptance.")

        # Doctor queries direct request detail
        doc_detail_res = client.get(
            f"/api/doctor/direct-requests/{request_id}",
            headers={"Authorization": f"Bearer {doc_token}"}
        )
        assert doc_detail_res.status_code == 200, f"Doctor detail failed: {doc_detail_res.text}"
        doc_detail = doc_detail_res.json().get("data", {})
        msgs_seen_by_doc = doc_detail.get("messages", [])
        
        # Verify no duplication (should be exactly 1 message)
        assert len(msgs_seen_by_doc) == 1, f"Defect 2 FAILED: Expected exactly 1 message, got {len(msgs_seen_by_doc)}"
        assert msgs_seen_by_doc[0]["body"] == "Doctor, my temperature is 101F since morning."
        print(f"  -> Doctor retrieved exact message history (count={len(msgs_seen_by_doc)}) without duplicates.")

        # Doctor accepts request
        accept_res = client.patch(
            f"/api/doctor/direct-requests/{request_id}/status",
            headers={"Authorization": f"Bearer {doc_token}"},
            json={"action": "ACCEPT"}
        )
        assert accept_res.status_code == 200

        # Doctor replies
        doc_client_msg_id = f"dmsg-{uuid.uuid4().hex[:8]}"
        doc_msg_res = client.post(
            f"/api/doctor/direct-requests/{request_id}/chat-messages",
            headers={"Authorization": f"Bearer {doc_token}"},
            json={
                "body": "Please take Paracetamol 500mg and drink plenty of fluids.",
                "client_message_id": doc_client_msg_id
            }
        )
        assert doc_msg_res.status_code == 200, f"Doctor reply failed: {doc_msg_res.text}"
        print("  -> Doctor sent clinical advice reply.")

        # Citizen queries messages
        cit_msgs_res = client.get(
            f"/api/citizen/doctor/requests/{request_id}/messages",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert cit_msgs_res.status_code == 200
        cit_msgs = cit_msgs_res.json().get("data", [])
        assert len(cit_msgs) == 2, f"Expected 2 total messages (1 cit, 1 doc), got {len(cit_msgs)}"
        print(f"  -> Citizen received doctor reply (total messages={len(cit_msgs)}).")
        print("  -> Defect 2 PASSED: Realtime chat delivery and zero-duplication verified.")

        # -------------------------------------------------------------
        # DEFECT 3 VERIFICATION: Update Symptoms, Re-triage & CareHandoff
        # -------------------------------------------------------------
        print("\n[TEST 3] Verifying 'Update Symptoms -> Submit & Re-triage'...")

        # 3.1 Verify empty input validation (400 rejection)
        empty_res = client.post(
            f"/api/citizen/doctor/requests/{request_id}/update-symptoms",
            headers={"Authorization": f"Bearer {token}"},
            json={"new_symptoms": ["   "]}
        )
        assert empty_res.status_code == 400, f"Expected 400 for empty symptom input, got {empty_res.status_code}"
        print("  -> Empty symptom input correctly rejected with 400 Bad Request.")

        # 3.2 Submit new critical red flag symptoms
        update_res = client.post(
            f"/api/citizen/doctor/requests/{request_id}/update-symptoms",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "new_symptoms": ["Chest pain", "Shortness of breath"],
                "notes": "Pain started radiating to left shoulder"
            }
        )
        assert update_res.status_code == 200, f"Update symptoms failed: {update_res.text}"
        up_data = update_res.json().get("data", {})
        print(f"  -> Update response: Priority={up_data.get('priority')}, HandoffVersion={up_data.get('handoff_version')}")

        assert up_data.get("priority") in ["EMERGENCY", "URGENT", "HIGH"], f"Expected upgraded priority, got {up_data.get('priority')}"
        assert up_data.get("handoff_version") == 2, f"Expected handoff version 2, got {up_data.get('handoff_version')}"
        
        # Verify CareHandoff audit trail in database
        handoff_records = db.query(CareHandoff).filter(
            CareHandoff.service_request_id == srv_req_id
        ).order_by(CareHandoff.version.asc()).all()
        assert len(handoff_records) >= 2, f"Expected at least 2 versions of CareHandoff in DB, found {len(handoff_records)}"
        v2_record = handoff_records[-1]
        assert v2_record.version == 2
        assert v2_record.source == "CITIZEN_UPDATE"
        print(f"  -> CareHandoff versioning verified in DB: v1 -> v2 (created_at={v2_record.created_at})")

        # Verify ServiceRequestStatusHistory event
        hist_events = db.query(ServiceRequestStatusHistory).filter(
            ServiceRequestStatusHistory.service_request_id == srv_req_id
        ).all()
        symptom_hist = [h for h in hist_events if "SYMPTOMS_UPDATED" in (h.reason or "")]
        assert len(symptom_hist) >= 1, "Expected SYMPTOMS_UPDATED status history record"
        print("  -> ServiceRequestStatusHistory audit record verified.")

        # Verify teleconsultation router endpoint compatibility as well
        tele_up_res = client.post(
            f"/api/citizen/doctor-requests/{request_id}/update-symptoms",
            headers={"Authorization": f"Bearer {token}"},
            json={"new_symptoms": ["Dizziness"]}
        )
        assert tele_up_res.status_code == 200
        print("  -> Teleconsultation router compatibility endpoint verified.")
        print("  -> Defect 3 PASSED: Symptom update, versioned handoff, and re-triage fully verified.")

        print("\n=======================================================")
        print("ALL 3 PRODUCTION DEFECT FIXES SUCCESSFULLY VERIFIED!")
        print("=======================================================\n")

    finally:
        db.close()

if __name__ == "__main__":
    test_verify_all_three_production_defects()
