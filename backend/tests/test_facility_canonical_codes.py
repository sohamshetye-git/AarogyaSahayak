import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app.models.facilities import Facility, FacilityService, FacilityHours, FacilityTypeEnum, VerificationStatusEnum, ServiceAvailabilityStatusEnum

client = TestClient(app)

CANONICAL_SERVICE_CODES = [
    "EMERGENCY_CARE",
    "GENERAL_DOCTOR_PHC",
    "PREGNANCY_DELIVERY",
    "CHILD_HEALTH_VACCINATION",
    "TESTS_DIAGNOSTICS",
    "MEDICINES_PHARMACY",
    "TB_SERVICES",
    "DIABETES_BP_SERVICES",
    "GOVERNMENT_SCHEME_DESK",
    "DISTRICT_HOSPITAL_SURGERY"
]

@pytest.mark.parametrize("code", CANONICAL_SERVICE_CODES)
def test_all_canonical_service_codes_search(code):
    res = client.post("/api/citizen/facilities/search", json={
        "service_code": code,
        "latitude": 18.5204,
        "longitude": 73.8567,
        "radius_km": 25,
        "locale": "en"
    })
    assert res.status_code == 200
    data = res.json().get("data", {})
    assert "items" in data
    assert "total" in data
    assert data["service_code"] == code
    assert len(data["items"]) >= 1

def test_guest_search_without_fake_beneficiary():
    res = client.post("/api/citizen/facilities/search", json={
        "beneficiary_id": "guest",
        "service_code": "GENERAL_DOCTOR_PHC",
        "latitude": 18.5204,
        "longitude": 73.8567,
        "radius_km": 25
    })
    assert res.status_code == 200
    data = res.json().get("data", {})
    assert len(data["items"]) >= 1

def test_unauthorized_household_member_returns_403():
    res = client.post("/api/citizen/facilities/search", json={
        "beneficiary_id": "unauthorized-fake-id-12345",
        "service_code": "GENERAL_DOCTOR_PHC",
        "latitude": 18.5204,
        "longitude": 73.8567,
        "radius_km": 25
    })
    assert res.status_code == 403
    err = res.json().get("detail", "")
    assert "household" in err.lower()

def test_invalid_coordinates_validation():
    res = client.post("/api/citizen/facilities/search", json={
        "service_code": "GENERAL_DOCTOR_PHC",
        "latitude": 195.0,  # Invalid lat > 90
        "longitude": 73.8567,
        "radius_km": 25
    })
    assert res.status_code == 422

def test_invalid_radius_validation():
    res = client.post("/api/citizen/facilities/search", json={
        "service_code": "GENERAL_DOCTOR_PHC",
        "latitude": 18.5204,
        "longitude": 73.8567,
        "radius_km": -5
    })
    assert res.status_code == 422
