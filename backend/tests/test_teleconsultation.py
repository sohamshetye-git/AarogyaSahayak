import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app.models import (
    User, CitizenProfile, HouseholdMember, TeleconsultationRequest,
    Consultation, Prescription, FollowUp, Case
)

client = TestClient(app)

def test_teleconsultation_full_flow(client, db_session):
    db = db_session
    try:
        # 1. Citizen creates draft for household member (e.g. child)
        hm = db.query(HouseholdMember).first()
        hm_id = hm.id if hm else None

        draft_res = client.post("/api/citizen/doctor-requests/draft", json={
            "household_member_id": hm_id,
            "language_code": "mr-IN",
            "mode": "AUDIO"
        })
        assert draft_res.status_code == 200
        draft_data = draft_res.json()["data"]
        req_id = draft_data["id"]
        assert draft_data["status"] == "DRAFT"

        # 2. Update draft intake with symptoms
        intake_res = client.patch(f"/api/citizen/doctor-requests/{req_id}/draft", json={
            "chief_complaint": "Severe chest pain and shortness of breath for 2 days",
            "symptoms": ["Chest Pain", "Shortness of Breath"],
            "duration_text": "2 days",
            "severity_level": "SEVERE",
            "mode": "AUDIO"
        })
        assert intake_res.status_code == 200
        intake_data = intake_res.json()["data"]
        assert intake_data["priority"] == "EMERGENCY"
        assert intake_data["safety_rule_triggered"] is True

        # 3. Submit request with consent & idempotency key
        submit_res = client.post(f"/api/citizen/doctor-requests/{req_id}/submit", json={
            "idempotency_key": f"IDEM-TEST-{req_id}",
            "consents": {
                "share_concern": True,
                "share_medical_history": True,
                "audio_video_consent": True,
                "store_transcript_consent": True,
                "share_location_consent": False
            }
        })
        assert submit_res.status_code == 200
        submit_data = submit_res.json()["data"]
        assert submit_data["status"] == "WAITING_FOR_DOCTOR"
        assert submit_data["patient"] is not None

        # 4. In-waiting room messaging & symptom update
        msg_res = client.post(f"/api/citizen/doctor-requests/{req_id}/messages", json={
            "message_text": "Patient feeling slightly dizzy as well."
        })
        assert msg_res.status_code == 200

        # Login as doctor to get bearer token
        doc_login = client.post("/api/auth/login", json={
            "identifier": "dr.sharma",
            "password": "demo123"
        })
        assert doc_login.status_code == 200
        token = doc_login.json()["data"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 5. Doctor views direct requests queue
        doc_res = client.get("/api/doctor/direct-requests", headers=headers)
        assert doc_res.status_code == 200
        doc_data = doc_res.json()["data"]
        doc_list = doc_data["items"] if isinstance(doc_data, dict) and "items" in doc_data else doc_data
        srv_id = submit_data.get("service_request_id") or submit_data.get("id")
        assert any(r["id"] == req_id or r["id"] == srv_id or r.get("teleconsultation_request_id") == req_id or r.get("service_request_id") == srv_id for r in doc_list)

        # 6. Doctor accepts direct request
        accept_res = client.post(f"/api/doctor/direct-requests/{req_id}/accept", headers=headers)
        assert accept_res.status_code == 200
        assert accept_res.json()["data"]["status"] == "DOCTOR_ACCEPTED"

        # 7. Doctor starts consultation
        start_res = client.post(f"/api/doctor/direct-requests/{req_id}/start", headers=headers)
        assert start_res.status_code == 200
        assert start_res.json()["data"]["status"] == "IN_CONSULTATION"

        # 8. Doctor completes consultation with Signed Prescription and ASHA follow-up directive
        complete_res = client.post(f"/api/doctor/direct-requests/{req_id}/complete", headers=headers, json={
            "provisional_diagnosis": "Acute Angina Suspicion",
            "clinical_summary": "Emergency triage completed; advised urgent ECG and follow-up.",
            "patient_guidance": "Avoid exertion and take prescribed nitrates.",
            "disposition": "FOLLOW_UP_REQUIRED",
            "prescriptions": [
                {
                    "medicine_name": "Sorbitrate 5mg",
                    "formulation": "Tablet",
                    "dosage": "1 sublingual",
                    "frequency": "SOS",
                    "duration_days": 3,
                    "instructions": "Place under tongue if chest pain recurs"
                }
            ],
            "investigation_orders": [],
            "assign_asha_followup": True,
            "asha_task_type": "EMERGENCY_VITALS_CHECK",
            "asha_due_days": 1,
            "asha_instructions": "Visit home tomorrow morning, record BP and pulse.",
            "asha_escalation_conditions": "Escalate to 108 if chest pain returns."
        })
        assert complete_res.status_code == 200
        complete_data = complete_res.json()["data"]
        assert complete_data["status"] == "COMPLETED"

        # Verify DB records created
        db_req = db.query(TeleconsultationRequest).filter(TeleconsultationRequest.id == req_id).first()
        assert db_req.status == "COMPLETED"
        assert db_req.consultation_id is not None

        # Verify ASHA Follow-up row exists
        fu = db.query(FollowUp).filter(FollowUp.consultation_id == db_req.consultation_id).first()
        assert fu is not None
        assert fu.task_type == "EMERGENCY_VITALS_CHECK"

        # Verify Signed Prescription exists
        rx = db.query(Prescription).filter(Prescription.consultation_id == db_req.consultation_id).first()
        assert rx is not None
        assert rx.status == "SIGNED"

        # 9. Citizen gets summary
        sum_res = client.get(f"/api/citizen/doctor-requests/{req_id}/summary")
        assert sum_res.status_code == 200
        assert sum_res.json()["data"]["status"] == "COMPLETED"

        # 10. Idempotent re-submission check
        re_res = client.post(f"/api/citizen/doctor-requests/{req_id}/submit", json={
            "idempotency_key": f"IDEM-TEST-{req_id}"
        })
        assert re_res.status_code == 200
        assert re_res.json()["data"]["id"] == req_id

    finally:
        db.close()
