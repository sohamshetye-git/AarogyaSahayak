from fastapi.testclient import TestClient

def test_login_success(client: TestClient):
    response = client.post(
        "/api/auth/login",
        json={"identifier": "sita.asha", "password": "demo123"}
    )
    assert response.status_code == 200
    json_data = response.json()
    assert "data" in json_data
    assert json_data["data"]["user"]["role"] == "ASHA_WORKER"
    assert "access_token" in json_data["data"]

def test_login_invalid_password(client: TestClient):
    response = client.post(
        "/api/auth/login",
        json={"identifier": "sita.asha", "password": "wrongpassword"}
    )
    assert response.status_code == 401

def test_role_protected_route_forbidden_for_unauthenticated(client: TestClient):
    response = client.get("/api/asha/dashboard")
    assert response.status_code == 401
