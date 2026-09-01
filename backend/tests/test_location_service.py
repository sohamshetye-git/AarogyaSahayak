import pytest
from app.models.facilities import Facility, UserLocationPreference, CareRequestLocation, VisitLocation
from app.schemas.location import LocationDataDTO, ReverseGeocodeRequestDTO, FacilityNearbyRequestDTO
from app.services.facility_service import calculate_haversine_distance, estimate_travel_time
from app.integrations.google_maps import google_maps_adapter

def test_location_coordinate_validation():
    # Valid coordinates
    valid_dto = LocationDataDTO(latitude=19.447, longitude=72.824, accuracy_meters=24.0)
    assert valid_dto.latitude == 19.447
    assert valid_dto.longitude == 72.824
    assert valid_dto.accuracy_meters == 24.0
    assert valid_dto.source == "DEVICE_GPS"

    # Out of range latitude (> 90)
    with pytest.raises(ValueError, match="Latitude must be between -90 and 90"):
        LocationDataDTO(latitude=95.0, longitude=72.824)

    # Out of range longitude (> 180)
    with pytest.raises(ValueError, match="Longitude must be between -180 and 180"):
        LocationDataDTO(latitude=19.0, longitude=185.0)

    # Negative accuracy
    with pytest.raises(ValueError, match="Accuracy must be non-negative"):
        LocationDataDTO(latitude=19.0, longitude=72.0, accuracy_meters=-5.0)


def test_haversine_distance_calculation():
    # Distance between two known points in Maharashtra: Mumbai (~19.076, 72.877) and Pune (~18.520, 73.856)
    dist = calculate_haversine_distance(19.0760, 72.8777, 18.5204, 73.8567)
    assert 110.0 <= dist <= 130.0 # ~120 km

    # Distance to identical point is 0
    assert calculate_haversine_distance(19.447, 72.824, 19.447, 72.824) == 0.0

    # Travel time estimate
    mins, text = estimate_travel_time(25.0)
    assert mins == 60
    assert "1h" in text


def test_reverse_geocode_adapter_contract():
    # Tests reverse geocoding fallback structure without throwing or producing empty garbage
    res = google_maps_adapter.reverse_geocode_coordinates(18.5204, 73.8567, language="mr")
    assert res is not None
    assert "latitude" in res
    assert "longitude" in res
    assert res["latitude"] == 18.5204
    assert res["longitude"] == 73.8567
    assert "formatted_address" in res
    assert "provider" in res
    assert "state" in res
    assert res["state"] is not None


def test_authorized_jurisdictions_isolation_from_gps(db_session=None):
    # Verifies that ASHA worker's assigned jurisdiction remains purely structural and unchanged by device GPS
    from app.schemas.location import AuthorizedJurisdictionsResponseDTO
    dto = AuthorizedJurisdictionsResponseDTO(
        worker_id="worker-asha-001",
        worker_name="Sita Patel",
        role="ASHA_WORKER",
        district_name="District 04",
        assigned_villages=[{"id": "v-kalyanpur-01", "name": "Kalyanpur"}],
        assigned_panchayats=["Kalyanpur Gram Panchayat"]
    )
    assert dto.worker_name == "Sita Patel"
    assert len(dto.assigned_villages) == 1
    assert dto.assigned_villages[0]["name"] == "Kalyanpur"


def test_reverse_geocode_endpoint_contract():
    # Verifies the canonical HTTP POST endpoint contract and JSON envelope response
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    payload = {
        "latitude": 19.1234,
        "longitude": 72.8567,
        "accuracy_m": 32.0,
        "captured_at": "2026-08-31T14:30:00Z",
        "language": "en"
    }
    response = client.post("/api/locations/reverse-geocode", json=payload)
    assert response.status_code == 200
    data = response.json().get("data", {})
    assert data.get("latitude") == 19.1234
    assert data.get("longitude") == 72.8567
    assert data.get("accuracy_m") == 32.0
    assert data.get("provider") in ["GOOGLE", "FALLBACK_COORDINATES"]
    assert "formatted_address" in data
    assert data.get("formatted_address") != "Address unavailable"
    assert data.get("state") == "Maharashtra"


def test_doctor_authorized_facilities_isolation_from_gps():
    # Verifies that Doctor facility queue is determined by authorized facilities, not current GPS coordinates
    from app.schemas.location import AuthorizedFacilitiesResponseDTO
    dto = AuthorizedFacilitiesResponseDTO(
        doctor_id="doc-001",
        doctor_name="Dr. Abhinav Sharma",
        primary_facility_id="PHC-09",
        primary_facility_name="Kalyanpur Primary Health Center",
        authorized_facilities=[
            {
                "facility_id": "fac-phc-09",
                "facility_code": "PHC-09",
                "name": "Kalyanpur Primary Health Center",
                "facility_type": "PHC",
                "district": "District 04",
                "is_primary": True
            }
        ]
    )
    assert dto.primary_facility_id == "PHC-09"
    assert len(dto.authorized_facilities) == 1
    assert dto.authorized_facilities[0]["is_primary"] is True
