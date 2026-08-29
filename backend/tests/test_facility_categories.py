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

# Test all 10 stable service codes mapped to verified capabilities
@pytest.mark.parametrize("service_code,expected_keyword", [
    ("EMERGENCY", "Emergency"),
    ("GENERAL_OPD", "Outpatient"),
    ("MATERNITY", "Maternity"),
    ("CHILD_HEALTH", "Immunization"),
    ("DIAGNOSTICS", "Laboratory"),
    ("PHARMACY", "Essential Medicines"),
    ("TB_DOTS", "Nikshay"),
    ("NCD", "NCD"),
    ("SCHEME_HELP", "Ayushman"),
    ("SURGERY", "Surgery")
])
def test_category_service_codes_ranking(db_session, service_code, expected_keyword):
    """Every healthcare category must map to stable backend service code and rank suitable facilities."""
    req = FacilitySearchRequestDTO(
        service_type=service_code,
        latitude=18.5204,
        longitude=73.8567,
        location_method="GPS",
        preferred_language="en-IN"
    )
    results = FacilityServiceEngine.search_and_rank_facilities(db_session, req)
    assert len(results) > 0
    top = results[0]
    assert top.suitability_score > 120.0
    assert any(expected_keyword.lower() in top.suitability_reason.lower() or expected_keyword.lower() in s.lower() for s in top.key_services + [top.suitability_reason])

def test_maternal_vs_child_beneficiary_context(db_session):
    """Maternal context must score obstetric facilities higher; child context scores pediatric immunization higher."""
    req_mat = FacilitySearchRequestDTO(
        service_type="MATERNITY",
        patient_category="MATERNAL",
        latitude=18.5204,
        longitude=73.8567
    )
    res_mat = FacilityServiceEngine.search_and_rank_facilities(db_session, req_mat)
    assert res_mat[0].suitability_score > 200.0

    req_child = FacilitySearchRequestDTO(
        service_type="CHILD_HEALTH",
        patient_category="CHILD",
        latitude=18.5204,
        longitude=73.8567
    )
    res_child = FacilityServiceEngine.search_and_rank_facilities(db_session, req_child)
    assert res_child[0].suitability_score > 200.0
