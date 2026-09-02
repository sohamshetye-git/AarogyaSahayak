import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.config import settings

client = TestClient(app)

def test_health_check_endpoint():
    """Verify root /health endpoint accessible and returns HEALTHY status."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "HEALTHY"
    assert data["service"] == "aarogya-sahayak-backend"

def test_cors_preflight_healthcare_portal():
    """Verify CORS preflight for Healthcare Portal Vercel origin."""
    portal_origin = "https://aarogya-sahayak-healthcare-portal.vercel.app"
    headers = {
        "Origin": portal_origin,
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "authorization,content-type",
    }
    response = client.options("/api/auth/login", headers=headers)
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == portal_origin
    assert response.headers.get("access-control-allow-credentials") == "true"

def test_login_demo_staff_accounts():
    """Verify authentication for ASHA, Doctor, and Admin accounts with demo123."""
    portal_origin = "https://aarogya-sahayak-healthcare-portal.vercel.app"
    
    # 1. ASHA Login
    asha_resp = client.post(
        "/api/auth/login",
        json={"identifier": "sita.asha", "password": "demo123"},
        headers={"Origin": portal_origin}
    )
    assert asha_resp.status_code == 200, f"ASHA login failed: {asha_resp.text}"
    asha_json = asha_resp.json()
    asha_data = asha_json.get("data", asha_json)
    assert "access_token" in asha_data
    assert asha_data["user"]["role"] in ["ASHA_WORKER", "asha_worker"]
    
    # 2. Doctor Login
    doc_resp = client.post(
        "/api/auth/login",
        json={"identifier": "dr.sharma", "password": "demo123"},
        headers={"Origin": portal_origin}
    )
    assert doc_resp.status_code == 200, f"Doctor login failed: {doc_resp.text}"
    doc_json = doc_resp.json()
    doc_data = doc_json.get("data", doc_json)
    assert "access_token" in doc_data
    assert doc_data["user"]["role"] in ["PHC_DOCTOR", "phc_doctor"]

    # 3. Admin Login
    admin_resp = client.post(
        "/api/auth/login",
        json={"identifier": "dho.admin", "password": "demo123"},
        headers={"Origin": portal_origin}
    )
    assert admin_resp.status_code == 200, f"Admin login failed: {admin_resp.text}"
    admin_json = admin_resp.json()
    admin_data = admin_json.get("data", admin_json)
    assert "access_token" in admin_data
    assert admin_data["user"]["role"] in ["DISTRICT_ADMIN", "district_admin"]

def test_login_invalid_credentials():
    """Verify proper 401 response for bad credentials."""
    resp = client.post(
        "/api/auth/login",
        json={"identifier": "sita.asha", "password": "wrong_password_123"},
        headers={"Origin": "https://aarogya-sahayak-healthcare-portal.vercel.app"}
    )
    assert resp.status_code == 401
