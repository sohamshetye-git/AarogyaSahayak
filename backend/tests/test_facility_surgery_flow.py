import pytest
from app.database import SessionLocal, Base, engine
from app.seeds.seed_facilities import seed_facilities_data
from app.schemas.facility import FacilitySearchRequestDTO, SearchLocationDTO
from app.services.facility_service import FacilityServiceEngine

@pytest.fixture(scope="module")
def db_session():
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    seed_facilities_data(session)
    yield session
    session.close()

def test_surgery_category_end_to_end_matching(db_session):
    """
    Test example requested by user:
    Beneficiary: Myself
    Location: Kalyanpur / 415001
    Selected category: District Hospital / Surgery
    Canonical service code: SURGERY
    Expected: Returns verified facilities capable of surgery/district-hospital care.
    """
    req = FacilitySearchRequestDTO(
        service_code="SURGERY",
        location=SearchLocationDTO(
            source="MANUAL",
            village="Kalyanpur",
            pincode="415001",
            district="District 04"
        ),
        urgency="NORMAL",
        preferred_language="en-IN"
    )
    results = FacilityServiceEngine.search_and_rank_facilities(db_session, req)
    assert len(results) >= 2
    
    # Check top matches are District Hospital, CHC, or Hospital
    top = results[0]
    assert top.facility_type in ["DISTRICT_HOSPITAL", "CHC", "SPECIALIZED_HOSPITAL", "HOSPITAL"]
    assert "Surgery" in top.suitability_reason or "Hospital" in top.display_name or "Hospital" in top.official_name or "Surgery" in str(top.key_services)
    assert top.distance_km >= 0.0

def test_envelope_structure_compatibility(db_session):
    """Verifies that search results contain all required fields for envelope construction."""
    req = FacilitySearchRequestDTO(
        service_code="EMERGENCY",
        urgency="EMERGENCY",
        latitude=18.5204,
        longitude=73.8567
    )
    results = FacilityServiceEngine.search_and_rank_facilities(db_session, req)
    assert len(results) > 0
    top = results[0]
    assert top.id is not None
    assert top.display_name is not None
    assert top.facility_type is not None
    assert top.ownership is not None
    assert top.verification_status in ["PROJECT_VERIFIED", "VERIFIED", "PROJECT_AND_GOOGLE_MATCHED"]
