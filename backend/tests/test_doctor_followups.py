import pytest
from fastapi.testclient import TestClient

def get_auth_headers(client: TestClient):
    login_res = client.post("/api/auth/login", json={"identifier": "dr.sharma", "password": "demo123"})
    assert login_res.status_code == 200
    token = login_res.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}

def test_get_doctor_followups_summary(client: TestClient):
    """Verify GET /api/doctor/followups/summary returns valid distinct metric counts."""
    headers = get_auth_headers(client)
    response = client.get("/api/doctor/followups/summary", headers=headers)
    assert response.status_code == 200, response.text
    data = response.json().get("data", {})
    assert "result_ready" in data
    assert "escalated" in data
    assert "overdue" in data
    assert "actionable" in data
    assert isinstance(data["actionable"], int)

def test_get_doctor_followups_list(client: TestClient):
    """Verify GET /api/doctor/followups returns non-null patient names, ages, and directives."""
    headers = get_auth_headers(client)
    response = client.get("/api/doctor/followups?status=ACTIONABLE", headers=headers)
    assert response.status_code == 200, response.text
    res_data = response.json().get("data", {})
    items = res_data.get("items", [])
    assert len(items) > 0
    for f in items:
        assert f.get("patient_name") is not None
        assert f.get("patient_name") != "(y"
        assert f.get("patient_age") is not None
        assert isinstance(f.get("patient_age"), int)
        assert f.get("directive") is not None

def test_get_doctor_followup_detail_and_lifecycle(client: TestClient):
    """Verify GET /api/doctor/followups/{followup_id} and action endpoints."""
    headers = get_auth_headers(client)
    list_res = client.get("/api/doctor/followups?status=ALL", headers=headers)
    items = list_res.json().get("data", {}).get("items", [])
    assert len(items) > 0
    test_fup = items[0]
    fup_id = test_fup["follow_up_id"]

    # 1. Detail endpoint
    detail_res = client.get(f"/api/doctor/followups/{fup_id}", headers=headers)
    assert detail_res.status_code == 200, detail_res.text
    detail = detail_res.json().get("data", {})
    assert detail["follow_up_id"] == fup_id
    assert detail["patient_name"] is not None
    assert "timeline" in detail

    # 2. Update directive
    dir_res = client.post(
        f"/api/doctor/followups/{fup_id}/directive",
        headers=headers,
        json={"instructions": "Updated directive instructions test"}
    )
    assert dir_res.status_code == 200, dir_res.text

    # 3. Mark Reviewed
    rev_res = client.post(
        f"/api/doctor/followups/{fup_id}/review",
        headers=headers,
        json={"notes": "Doctor verified patient progress."}
    )
    assert rev_res.status_code == 200, rev_res.text
    assert rev_res.json().get("data", {}).get("status") == "REVIEWED"
