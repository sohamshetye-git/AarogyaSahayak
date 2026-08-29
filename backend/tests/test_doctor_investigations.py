import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import InvestigationOrder, InvestigationSample, InvestigationResult, InvestigationReview, User

def get_auth_headers(client: TestClient, identifier: str = "dr.sharma", password: str = "demo123"):
    resp = client.post("/api/auth/login", json={"identifier": identifier, "password": password})
    assert resp.status_code == 200, f"Login failed for {identifier}: {resp.json()}"
    token = resp.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_investigation_order_creation_and_lifecycle(client: TestClient):
    headers = get_auth_headers(client, "dr.sharma", "demo123")

    # 1. Create Investigation Order
    order_data = {
        "citizen_id": "CIT-SUNITA-001",
        "case_id": "CASE-SUNITA-001",
        "test_name": "Complete Blood Count (CBC)",
        "category": "HEMATOLOGY",
        "priority": "URGENT",
        "clinical_reason": "Anemia evaluation in pregnancy",
        "specimen_type": "Whole Blood",
        "idempotency_key": "TEST-KEY-00101"
    }

    res = client.post("/api/doctor/investigations", json=order_data, headers=headers)
    assert res.status_code == 200
    data = res.json()["data"]
    inv_id = data["id"]
    assert data["reference"].startswith("INV-")
    assert data["status"] in ["ORDERED", "SAMPLE_PENDING"]

    # 2. Record Sample Collection
    sample_res = client.post(
        f"/api/doctor/investigations/{inv_id}/collect",
        json={"sample_reference": "SMP-TEST-001", "specimen_type": "Whole Blood"},
        headers=headers
    )
    assert sample_res.status_code == 200
    assert sample_res.json()["data"]["status"] == "SAMPLE_COLLECTED"

    # 3. Enter Result (Mark Critical)
    result_res = client.post(
        f"/api/doctor/investigations/{inv_id}/result",
        json={
            "result_source": "PHC Manual/Demonstration Entry",
            "laboratory_name": "PHC Kalyanpur Central Lab",
            "critical_flag": True,
            "items": [
                {
                    "parameter_name": "Hemoglobin",
                    "parameter_code": "HGB",
                    "value": "6.8",
                    "unit": "g/dL",
                    "reference_low": "12.0",
                    "reference_high": "15.0",
                    "source_flag": "CRITICAL"
                }
            ]
        },
        headers=headers
    )
    assert result_res.status_code == 200
    assert result_res.json()["data"]["status"] == "CRITICAL_RESULT"

    # 4. Acknowledge Critical Result
    ack_res = client.post(
        f"/api/doctor/investigations/{inv_id}/acknowledge-critical",
        json={"notes": "Doctor notified. Immediate IV iron & referral planned."},
        headers=headers
    )
    assert ack_res.status_code == 200
    assert ack_res.json()["data"]["status"] == "DOCTOR_ACKNOWLEDGED"

    # 5. Doctor Review Result
    rev_res = client.post(
        f"/api/doctor/investigations/{inv_id}/review",
        json={
            "review_note": "Severe gestational anemia. Initiated high-priority management.",
            "outcome": "UPDATE_CARE_PLAN",
            "update_care_plan": True,
            "create_followup": True,
            "followup_instructions": "ASHA home visit to verify iron compliance."
        },
        headers=headers
    )
    assert rev_res.status_code == 200
    assert rev_res.json()["data"]["status"] == "REVIEWED"


def test_investigation_sample_rejection_and_recollection(client: TestClient):
    headers = get_auth_headers(client, "dr.sharma", "demo123")

    order_data = {
        "citizen_id": "CIT-MEENA-002",
        "case_id": "CASE-MEENA-002",
        "test_name": "Serum Creatinine",
        "category": "BIOCHEMISTRY",
        "priority": "URGENT",
        "clinical_reason": "Renal evaluation",
        "idempotency_key": "TEST-KEY-00202"
    }

    res = client.post("/api/doctor/investigations", json=order_data, headers=headers)
    assert res.status_code == 200
    inv_id = res.json()["data"]["id"]

    # Reject Specimen
    rej_res = client.post(
        f"/api/doctor/investigations/{inv_id}/collect",
        json={"rejection_reason": "Hemolyzed sample during transit", "recollection_required": True},
        headers=headers
    )
    assert rej_res.status_code == 200
    assert rej_res.json()["data"]["status"] == "RECOLLECTION_REQUIRED"


def test_citizen_and_asha_role_access(client: TestClient):
    # Citizen view
    cit_res = client.get("/api/citizen/investigations")
    assert cit_res.status_code == 200
    assert isinstance(cit_res.json()["data"], list)

    # ASHA tasks view
    asha_headers = get_auth_headers(client, "sita.asha", "demo123")
    asha_res = client.get("/api/asha/investigation-tasks", headers=asha_headers)
    assert asha_res.status_code == 200
    assert isinstance(asha_res.json()["data"], list)


def test_admin_anonymized_investigation_metrics(client: TestClient):
    admin_headers = get_auth_headers(client, "dho.admin", "demo123")
    res = client.get("/api/admin/dashboard", headers=admin_headers)
    assert res.status_code == 200
    summary = res.json()["data"]["summary"]
    assert "investigation_analytics" in summary
    analytics = summary["investigation_analytics"]
    assert "total_investigations_ordered" in analytics
    assert "recollection_rate_pct" in analytics


def test_view_order_canonical_contract_and_404(client: TestClient):
    headers = get_auth_headers(client, "dr.sharma", "demo123")

    # Ensure an order exists
    order_data = {
        "citizen_id": "CIT-SUNITA-001",
        "case_id": "CASE-SUNITA-001",
        "test_name": "Complete Blood Count (CBC)",
        "category": "HEMATOLOGY",
        "priority": "URGENT",
        "clinical_reason": "Anemia evaluation",
        "idempotency_key": "TEST-KEY-VIEW-ORDER-001"
    }
    client.post("/api/doctor/investigations", json=order_data, headers=headers)

    # 1. Fetch investigations list and verify canonical keys
    list_res = client.get("/api/doctor/investigations", headers=headers)
    assert list_res.status_code == 200
    orders = list_res.json()["data"]
    assert len(orders) > 0
    item = orders[0]
    inv_id = item["id"]
    inv_ref = item["reference"]

    assert "investigation_id" in item
    assert "investigation_reference" in item
    assert item["investigation_id"] == inv_id
    assert item["investigation_reference"] == inv_ref

    # 2. View Order by UUID
    detail_res1 = client.get(f"/api/doctor/investigations/{inv_id}", headers=headers)
    assert detail_res1.status_code == 200
    d1 = detail_res1.json()["data"]
    assert d1["investigation_id"] == inv_id
    assert d1["investigation_reference"] == inv_ref
    assert "test" in d1 and d1["test"]["name"] is not None
    assert "patient" in d1 and d1["patient"]["name"] is not None
    assert "order" in d1 and d1["order"]["ordered_at"] is not None

    # 3. View Order by Reference
    detail_res2 = client.get(f"/api/doctor/investigations/{inv_ref}", headers=headers)
    assert detail_res2.status_code == 200
    assert detail_res2.json()["data"]["investigation_id"] == inv_id

    # 4. View Order with Non-existent ID returns 404
    bad_res = client.get("/api/doctor/investigations/NON-EXISTENT-UUID-12345", headers=headers)
    assert bad_res.status_code == 404
    assert bad_res.json()["detail"]["code"] == "INVESTIGATION_NOT_FOUND"


def test_recollection_request_modal_api_and_normal_result_prohibition(client: TestClient):
    headers = get_auth_headers(client, "dr.sharma", "demo123")

    # 1. Order test for Pooja Jadhav
    order_data = {
        "citizen_id": "CIT-POOJA-005",
        "case_id": "CASE-POOJA-005",
        "test_name": "Urine Routine & Micro",
        "category": "BIOCHEMISTRY",
        "priority": "ROUTINE",
        "clinical_reason": "Gestational protein check",
        "idempotency_key": "TEST-KEY-POOJA-REC-01"
    }
    res = client.post("/api/doctor/investigations", json=order_data, headers=headers)
    assert res.status_code == 200
    inv_id = res.json()["data"]["id"]

    # 2. Collect sample and enter normal result
    client.post(f"/api/doctor/investigations/{inv_id}/collect", json={"sample_reference": "SMP-POOJA-01"}, headers=headers)
    client.post(f"/api/doctor/investigations/{inv_id}/result", json={
        "result_source": "PHC Lab",
        "critical_flag": False,
        "items": [{"parameter_name": "Protein", "value": "Negative", "source_flag": "NORMAL"}]
    }, headers=headers)

    # 3. Review normal result
    client.post(f"/api/doctor/investigations/{inv_id}/review", json={"review_note": "Normal protein", "outcome": "NO_CHANGE"}, headers=headers)

    # 4. Attempting recollection request on normal reviewed result should fail with 409
    rec_fail = client.post(
        f"/api/doctor/investigations/{inv_id}/request-recollection",
        json={
            "reason_code": "HEMOLYSED_SAMPLE",
            "reason_note": "Try recollect",
            "assign_asha_assistance": True
        },
        headers=headers
    )
    assert rec_fail.status_code == 409
    assert rec_fail.json()["detail"]["code"] == "NORMAL_RESULT_RECOLLECTION_PROHIBITED"

    # 5. Order sample rejection scenario and submit recollection request
    order_data2 = {
        "citizen_id": "CIT-SUNITA-001",
        "case_id": "CASE-SUNITA-001",
        "test_name": "Sputum AFB",
        "category": "MICROBIOLOGY",
        "priority": "URGENT",
        "clinical_reason": "Cough evaluation",
        "idempotency_key": "TEST-KEY-REJECT-02"
    }
    res2 = client.post("/api/doctor/investigations", json=order_data2, headers=headers)
    inv_id2 = res2.json()["data"]["id"]

    # Reject sample
    client.post(f"/api/doctor/investigations/{inv_id2}/collect", json={"rejection_reason": "Saliva submitted instead of sputum", "recollection_required": True}, headers=headers)

    # Submit Recollection Request with ASHA task
    rec_pass = client.post(
        f"/api/doctor/investigations/{inv_id2}/request-recollection",
        json={
            "reason_code": "INSUFFICIENT_SAMPLE",
            "reason_note": "Fresh early morning deep cough sputum sample required.",
            "priority": "URGENT",
            "collection_location": "PHC Kalyanpur Lab",
            "assign_asha_assistance": True
        },
        headers=headers
    )
    assert rec_pass.status_code == 200
    data2 = rec_pass.json()["data"]
    assert data2["status"] == "RECOLLECTION_REQUIRED"

    # Verify ASHA assistance task created
    asha_headers = get_auth_headers(client, "sita.asha", "demo123")
    tasks_res = client.get("/api/asha/investigation-tasks", headers=asha_headers)
    assert tasks_res.status_code == 200
    task_list = tasks_res.json()["data"]
    matching_tasks = [t for t in task_list if t["investigation_id"] == inv_id2]
    assert len(matching_tasks) > 0

