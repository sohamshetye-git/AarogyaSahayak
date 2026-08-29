import pytest
from app.database import SessionLocal, Base, engine
from app.seeds.seed_facilities import seed_facilities_data
from app.schemas.facility import FacilitySearchRequestDTO
from app.services.facility_service import FacilityServiceEngine

@pytest.fixture(scope="module")
def db_session():
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    seed_facilities_data(session)
    yield session
    session.close()

def test_01_two_source_search_and_provenance(db_session):
    """Search must merge PostgreSQL verified and Google Places discovered results."""
    req = FacilitySearchRequestDTO(
        latitude=19.447,
        longitude=72.824,
        service_code="GENERAL_OPD",
        location_method="GPS"
    )
    results = FacilityServiceEngine.search_and_rank_facilities(db_session, req)
    assert len(results) >= 2
    
    # Must have explicit provenance values
    provenance_set = {r.verification_status for r in results}
    assert any(p in ["PROJECT_VERIFIED", "GOOGLE_DISCOVERED_UNVERIFIED", "PROJECT_AND_GOOGLE_MATCHED"] for p in provenance_set)

def test_02_google_failure_falls_back_to_postgresql(db_session, monkeypatch):
    """When Google Places adapter fails, PostgreSQL results must be returned smoothly."""
    from app.integrations.google_maps import google_maps_adapter
    
    def mock_fail(*args, **kwargs):
        raise Exception("Google API Down / 503 Service Unavailable")

    monkeypatch.setattr(google_maps_adapter, "search_nearby", mock_fail)
    monkeypatch.setattr(google_maps_adapter, "search_by_text", mock_fail)

    req = FacilitySearchRequestDTO(
        latitude=18.5204,
        longitude=73.8567,
        service_code="EMERGENCY"
    )
    results = FacilityServiceEngine.search_and_rank_facilities(db_session, req)
    assert len(results) >= 1
    assert results[0].emergency_capability is True
    assert results[0].source == "PROJECT_DATABASE"

def test_03_maternity_service_search_mapping(db_session):
    """Maternity service search maps to appropriate capability queries."""
    req = FacilitySearchRequestDTO(
        latitude=18.5204,
        longitude=73.8567,
        service_code="MATERNITY"
    )
    results = FacilityServiceEngine.search_and_rank_facilities(db_session, req)
    assert len(results) >= 1
    assert results[0].matching_service == "MATERNITY"
