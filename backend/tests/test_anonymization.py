from fastapi.testclient import TestClient

def test_admin_dashboard_anonymization(client: TestClient):
    admin_login = client.post("/api/auth/login", json={"identifier": "dho.admin", "password": "demo123"})
    assert admin_login.status_code == 200
    token = admin_login.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get("/api/admin/dashboard", headers=headers)
    assert res.status_code == 200
    data = res.json()["data"]

    # Verify aggregates exist
    assert "summary" in data
    assert "total_cases" in data["summary"]
    assert "maternal_high_risk_cases" in data["summary"]

    # Ensure no patient PII fields exist in top-level or alerts
    raw_text = res.text
    assert "9876543210" not in raw_text # Phone number must not be exposed
    assert "12-3456-7890-1234" not in raw_text # ABHA number must not be exposed
