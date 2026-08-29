"""
Backend Unit & Integration Tests for Doctor Clinical Work Component & Endpoints
"""

import os
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

os.environ["APP_ENV"] = "test"

from app.main import app
from app.seeds.seed_full_demo import seed_full_demonstration
from app.database import SessionLocal
from app.models import (
    User, WorkerProfile, Case, Referral, Consultation, TestOrder, FollowUp, CitizenProfile
)

client = TestClient(app)

@pytest.fixture(scope="module", autouse=True)
def setup_demo_data():
    seed_full_demonstration()
    yield

def get_auth_token(username="dr.sharma", password="demo123"):
    resp = client.post("/api/auth/login", json={"identifier": username, "password": password})
    assert resp.status_code == 200, f"Login failed for {username}: {resp.text}"
    return resp.json()["data"]["access_token"]


def test_clinical_work_summary_endpoint():
    token = get_auth_token("dr.sharma", "demo123")
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/api/doctor/dashboard/clinical-work", headers=headers)
    assert response.status_code == 200
    data = response.json()["data"]
    assert "ready_to_start" in data
    assert "consultations_in_progress" in data
    assert "results_ready_for_review" in data
    assert "asha_followups_to_review" in data
    assert "phc_id" in data


def test_clinical_work_summary_destination_count_match():
    token = get_auth_token("dr.sharma", "demo123")
    headers = {"Authorization": f"Bearer {token}"}
    sum_res = client.get("/api/doctor/dashboard/clinical-work", headers=headers).json()["data"]
    
    # Ready to start referrals destination
    ref_res = client.get("/api/doctor/referrals?status_filter=READY_TO_START", headers=headers).json()["data"]
    assert sum_res["ready_to_start"] == len(ref_res)

    # In progress consultations destination
    cons_res = client.get("/api/doctor/consultations?status_filter=IN_CONSULTATION", headers=headers).json()["data"]
    assert sum_res["consultations_in_progress"] == len(cons_res)

    # Results ready for review destination
    inv_res = client.get("/api/doctor/investigations?status_filter=RESULT_AVAILABLE", headers=headers).json()["data"]
    assert sum_res["results_ready_for_review"] == len(inv_res)

    # Followups to review destination
    fu_data = client.get("/api/doctor/followups?status_filter=REVIEW_REQUIRED", headers=headers).json()["data"]
    fu_list = fu_data.get("items", fu_data) if isinstance(fu_data, dict) else fu_data
    assert sum_res["asha_followups_to_review"] == len(fu_list)


def test_clinical_work_state_mutations():
    token = get_auth_token("dr.sharma", "demo123")
    headers = {"Authorization": f"Bearer {token}"}
    
    # Check initial summary
    initial_sum = client.get("/api/doctor/dashboard/clinical-work", headers=headers).json()["data"]

    # Review investigation if any
    inv_data = client.get("/api/doctor/investigations?status_filter=RESULT_AVAILABLE", headers=headers).json()["data"]
    inv_list = inv_data.get("items", inv_data) if isinstance(inv_data, dict) else inv_data
    if len(inv_list) > 0:
        inv_id = inv_list[0]["id"]
        review_res = client.post(f"/api/doctor/investigations/{inv_id}/review", json={"notes": "Normal"}, headers=headers)
        assert review_res.status_code == 200
        assert review_res.json()["data"]["status"] == "REVIEWED"

    # Review followup if any
    fu_data = client.get("/api/doctor/followups?status_filter=REVIEW_REQUIRED", headers=headers).json()["data"]
    fu_list = fu_data.get("items", fu_data) if isinstance(fu_data, dict) else fu_data
    if len(fu_list) > 0:
        fu_id = fu_list[0]["id"]
        fu_review_res = client.post(f"/api/doctor/followups/{fu_id}/review", json={"action": "MARK_REVIEWED"}, headers=headers)
        assert fu_review_res.status_code == 200
        assert fu_review_res.json()["data"]["status"] == "REVIEWED"

    # Verify updated summary
    updated_sum = client.get("/api/doctor/dashboard/clinical-work", headers=headers).json()["data"]
    if len(inv_list) > 0:
        assert updated_sum["results_ready_for_review"] == initial_sum["results_ready_for_review"] - 1
    if len(fu_list) > 0:
        assert updated_sum["asha_followups_to_review"] == initial_sum["asha_followups_to_review"] - 1
