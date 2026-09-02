import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app.models import (
    User, CitizenProfile, HouseholdMember, ServiceRequest, CareHandoff,
    Consultation, Prescription, InvestigationOrder, FollowUp, Case
)

client = TestClient(app)

def test_citizen_speak_to_doctor_e2e_all_channels(client, db_session):
    db = db_session
    try:
        # 1. Citizen retrieves authorized beneficiaries
        b_res = client.get("/api/citizen/beneficiaries")
        assert b_res.status_code == 200
        b_items = b_res.json()["data"]["items"]
        assert len(b_items) >= 1
        beneficiary = b_items[0]
        beneficiary_id = beneficiary["beneficiary_id"]

        # ----------------------------------------------------
        # TEST CHANNEL 1: CALLBACK (Doctor Phone Callback)
        # ----------------------------------------------------
        callback_payload = {
            "beneficiary_id": beneficiary_id,
            "channel": "CALLBACK",
            "chief_complaint": "Persistent high fever and body ache",
            "symptoms": ["High Fever", "Body Ache"],
            "preferred_language": "mr-IN",
            "sharing_scope": {
                "share_profile": True,
                "share_structured_summary": True,
                "share_location": True
            },
            "idempotency_key": f"IDEM-CALLBACK-{beneficiary_id}-001"
        }
        cb_create_res = client.post("/api/citizen/doctor/requests", json=callback_payload)
        assert cb_create_res.status_code == 200
        cb_data = cb_create_res.json()["data"]
        cb_req_id = cb_data["request_id"]
        assert cb_data["status"] == "WAITING_FOR_DOCTOR"

        # Verify CareHandoff v1 created
        handoff = db.query(CareHandoff).filter(CareHandoff.service_request_id == cb_req_id).first()
        assert handoff is not None
        assert handoff.beneficiary_id == beneficiary_id
        assert handoff.requested_channel == "CALLBACK"

        # ----------------------------------------------------
        # TEST CHANNEL 2: CHAT (Doctor Chat Advice)
        # ----------------------------------------------------
        chat_payload = {
            "beneficiary_id": beneficiary_id,
            "channel": "CHAT",
            "chief_complaint": "Mild rash on forearm with itching",
            "symptoms": ["Skin Rash", "Itching"],
            "preferred_language": "en-IN",
            "sharing_scope": {
                "share_profile": True,
                "share_structured_summary": True
            },
            "idempotency_key": f"IDEM-CHAT-{beneficiary_id}-002"
        }
        chat_create_res = client.post("/api/citizen/doctor/requests", json=chat_payload)
        assert chat_create_res.status_code == 200
        chat_data = chat_create_res.json()["data"]
        chat_req_id = chat_data["request_id"]

        # Citizen sends chat message while waiting
        msg_send_res = client.post(f"/api/citizen/doctor-requests/{chat_req_id}/messages", json={
            "message_text": "Rash started yesterday after gardening."
        })
        assert msg_send_res.status_code == 200

        # ----------------------------------------------------
        # TEST CHANNEL 3: IN_PERSON_PHC (OPD Appointment)
        # ----------------------------------------------------
        phc_payload = {
            "beneficiary_id": beneficiary_id,
            "channel": "IN_PERSON_PHC",
            "chief_complaint": "Routine blood pressure checkup and prenatal counseling",
            "symptoms": ["Routine Checkup"],
            "preferred_language": "mr-IN",
            "sharing_scope": {
                "share_profile": True,
                "share_structured_summary": True,
                "share_location": True
            },
            "idempotency_key": f"IDEM-PHC-{beneficiary_id}-003"
        }
        phc_create_res = client.post("/api/citizen/doctor/requests", json=phc_payload)
        assert phc_create_res.status_code == 200
        phc_data = phc_create_res.json()["data"]
        phc_req_id = phc_data["request_id"]

        # Verify IN_PERSON_PHC is NOT stripped to CALLBACK
        srv_phc = db.query(ServiceRequest).filter(ServiceRequest.id == phc_req_id).first()
        assert srv_phc.requested_channel == "IN_PERSON_PHC"

        # ----------------------------------------------------
        # DOCTOR PORTAL PROCESSING
        # ----------------------------------------------------
        doc_login = client.post("/api/auth/login", json={
            "identifier": "dr.sharma",
            "password": "demo123"
        })
        assert doc_login.status_code == 200
        doc_token = doc_login.json()["data"]["access_token"]
        doc_headers = {"Authorization": f"Bearer {doc_token}"}

        # 1. Doctor lists direct requests
        list_res = client.get("/api/doctor/direct-requests", headers=doc_headers)
        assert list_res.status_code == 200
        req_data = list_res.json()["data"]
        req_list = req_data.get("items", req_data) if isinstance(req_data, dict) else req_data
        assert any(r["id"] == cb_req_id for r in req_list)
        assert any(r["id"] == chat_req_id for r in req_list)
        assert any(r["id"] == phc_req_id for r in req_list)

        # 2. Doctor accepts the CHAT request
        doc_accept_res = client.post(f"/api/doctor/direct-requests/{chat_req_id}/accept", headers=doc_headers)
        assert doc_accept_res.status_code == 200
        assert doc_accept_res.json()["data"]["status"] == "DOCTOR_ACCEPTED"

        # 3. Doctor starts consultation on CHAT request
        doc_start_res = client.post(f"/api/doctor/direct-requests/{chat_req_id}/start", headers=doc_headers)
        assert doc_start_res.status_code == 200
        assert doc_start_res.json()["data"]["status"] == "IN_CONSULTATION"

        # 4. Doctor sends reply in chat
        doc_msg_res = client.post(f"/api/citizen/doctor-requests/{chat_req_id}/messages", json={
            "message_text": "Please apply calamine lotion and avoid scratching. Prescribed ointment below."
        })
        assert doc_msg_res.status_code == 200

        # 5. Doctor signs & completes consultation with Prescription, Lab Investigation, and ASHA Directive
        complete_payload = {
            "provisional_diagnosis": "Allergic Contact Dermatitis",
            "clinical_summary": "Erythematous pruritic maculopapular rash on left forearm. Mild allergic reaction.",
            "patient_guidance": "Wash with cold water, apply prescribed cream twice daily.",
            "disposition": "FOLLOW_UP_REQUIRED",
            "prescriptions": [
                {
                    "medicine_name": "Hydrocortisone 1% Cream",
                    "formulation": "Ointment",
                    "dosage": "Apply thin layer",
                    "frequency": "1-0-1",
                    "duration_days": 5,
                    "instructions": "Apply gently over affected skin twice daily"
                },
                {
                    "medicine_name": "Cetirizine 10mg",
                    "formulation": "Tablet",
                    "dosage": "1 tablet",
                    "frequency": "0-0-1",
                    "duration_days": 3,
                    "instructions": "Take at bedtime with water"
                }
            ],
            "investigation_orders": [
                {
                    "test_name": "Complete Blood Count (CBC)",
                    "category": "PATHOLOGY",
                    "urgency": "ROUTINE"
                }
            ],
            "assign_asha_followup": True,
            "asha_task_type": "POST_CONSULTATION_CHECK",
            "asha_due_days": 3,
            "asha_instructions": "Visit citizen at home on Day 3 and verify if rash has subsided."
        }
        complete_res = client.post(f"/api/doctor/direct-requests/{chat_req_id}/complete", headers=doc_headers, json=complete_payload)
        assert complete_res.status_code == 200
        assert complete_res.json()["data"]["status"] == "COMPLETED"

        # ----------------------------------------------------
        # CITIZEN MY CARE VERIFICATION
        # ----------------------------------------------------
        detail_res = client.get(f"/api/citizen/service-requests/{chat_req_id}")
        assert detail_res.status_code == 200
        care_detail = detail_res.json()["data"]
        assert care_detail["status"] == "COMPLETED"
        assert care_detail["requested_channel"] == "CHAT"
        assert len(care_detail["messages"]) >= 2
        assert care_detail["consultation"] is not None
        assert care_detail["consultation"]["provisional_diagnosis"] == "Allergic Contact Dermatitis"
        assert len(care_detail["prescriptions"]) >= 1
        assert len(care_detail["investigations"]) >= 1
        assert len(care_detail["followups"]) >= 1

        # ----------------------------------------------------
        # CITIZEN MY MEDICINES INTEGRATION VERIFICATION
        # ----------------------------------------------------
        rx_res = client.get("/api/citizen/prescriptions")
        assert rx_res.status_code == 200
        rx_data = rx_res.json()["data"]
        rx_list = rx_data.get("items", rx_data) if isinstance(rx_data, dict) else rx_data
        assert len(rx_list) >= 1
        latest_rx = rx_list[0]
        med_names = [it["medicine_name"] for it in latest_rx["items"]]
        assert "Hydrocortisone 1% Cream" in med_names or "Cetirizine 10mg" in med_names

        inv_res = client.get("/api/citizen/investigations")
        assert inv_res.status_code == 200
        inv_data = inv_res.json()["data"]
        inv_list = inv_data.get("items", inv_data) if isinstance(inv_data, dict) else inv_data
        assert len(inv_list) >= 1
        test_names = [o["test_name"] for o in inv_list]
        assert "Complete Blood Count (CBC)" in test_names

        fu_res = client.get("/api/citizen/followups")
        assert fu_res.status_code == 200
        fu_data = fu_res.json()["data"]
        fu_list = fu_data.get("items", fu_data) if isinstance(fu_data, dict) else fu_data
        assert len(fu_list) >= 1
        task_types = [f["task_type"] for f in fu_list]
        assert "POST_CONSULTATION_CHECK" in task_types

        # ----------------------------------------------------
        # ASHA PORTAL VERIFICATION
        # ----------------------------------------------------
        # Verify FollowUp directive exists in DB linked to case
        fu_db = db.query(FollowUp).filter(FollowUp.case_id == care_detail["case_id"]).first()
        assert fu_db is not None
        assert fu_db.task_type == "POST_CONSULTATION_CHECK"
        assert "Allergic Contact Dermatitis" in fu_db.reason or "rash" in fu_db.instructions.lower()

    finally:
        db.close()
