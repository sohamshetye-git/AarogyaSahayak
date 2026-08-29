import pytest
from app.integrations.google_maps import (
    GoogleMapsAdapter, GoogleMapsAuthException, GoogleMapsQuotaException,
    GoogleMapsTimeoutException, google_maps_adapter
)

def test_01_google_maps_adapter_field_mask():
    """Verify that Google Maps adapter uses strict required field masks and never wildcard *."""
    adapter = GoogleMapsAdapter(server_key="AIzaSyTestKey123", mode="live")
    assert "*" not in adapter.FIELD_MASK
    assert "places.id" in adapter.FIELD_MASK
    assert "places.displayName" in adapter.FIELD_MASK
    assert "places.formattedAddress" in adapter.FIELD_MASK
    assert "places.location" in adapter.FIELD_MASK
    assert "places.primaryType" in adapter.FIELD_MASK
    assert "places.googleMapsUri" in adapter.FIELD_MASK

def test_02_mock_nearby_search():
    """Test nearby search returns mock structured facilities when in mock mode."""
    adapter = GoogleMapsAdapter(server_key=None, mode="mock")
    places = adapter.search_nearby(lat=19.447, lon=72.824, radius_meters=10000, included_types=["hospital"])
    assert len(places) >= 2
    assert "displayName" in places[0]
    assert "location" in places[0]
    assert "hospital" in places[0]["types"]

def test_03_mock_text_search():
    """Test capability text search returns targeted capability centres."""
    adapter = GoogleMapsAdapter(server_key=None, mode="mock")
    maternity = adapter.search_by_text("maternity hospital delivery centre", lat=19.447, lon=72.824)
    assert len(maternity) >= 1
    assert "Maternity" in maternity[0]["displayName"]["text"]

    tb = adapter.search_by_text("DOTS centre TB clinic", lat=19.447, lon=72.824)
    assert len(tb) >= 1
    assert "TB" in tb[0]["displayName"]["text"] or "Nikshay" in tb[0]["displayName"]["text"]

def test_04_mock_geocoding():
    """Test manual village and PIN geocoding."""
    adapter = GoogleMapsAdapter(server_key=None, mode="mock")
    results = adapter.geocode_manual_location("Ganeshpur")
    assert len(results) >= 1
    assert "formatted_address" in results[0]
    assert "geometry" in results[0]
    assert results[0]["geometry"]["location"]["lat"] == 18.5204

def test_05_auth_error_when_missing_key_in_live_mode():
    """Live mode must raise typed auth exception if key is missing."""
    adapter = GoogleMapsAdapter(server_key="", mode="live")
    with pytest.raises(GoogleMapsAuthException):
        adapter._make_places_request("https://places.googleapis.com/v1/places:searchNearby", {})
