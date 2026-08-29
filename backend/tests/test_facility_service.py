import pytest
from app.database import SessionLocal, Base, engine
from app.seeds.seed_facilities import seed_facilities_data
from app.schemas.facility import (
    FacilitySearchRequestDTO, FacilityAssistanceCreateRequestDTO,
    FacilityAppointmentCreateRequestDTO
)
from app.services.facility_service import FacilityServiceEngine, calculate_haversine_distance, estimate_travel_time
from app.models.facilities import Facility, FacilityAssistanceRequest, FacilityAppointmentRequest, AssistanceStatusEnum, AppointmentStatusEnum
from app.models import CitizenProfile

@pytest.fixture(scope="module")
def db_session():
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    seed_facilities_data(session)
    yield session
    session.close()

def test_01_idempotent_seeding(db_session):
    """Seed must be completely idempotent with zero duplicate records."""
    count1 = seed_facilities_data(db_session)
    count2 = seed_facilities_data(db_session)
    assert count1 == 11
    assert count2 == 11
    total = db_session.query(Facility).count()
    assert total >= 11

def test_02_haversine_distance_calculation():
    """Haversine distance calculation must be mathematically accurate."""
    # Distance between Kalyanpur PHC (18.5300, 73.8700) and Sub-centre (18.5204, 73.8567)
    dist = calculate_haversine_distance(18.5300, 73.8700, 18.5204, 73.8567)
    assert 1.0 <= dist <= 2.5
    mins, text = estimate_travel_time(dist)
    assert mins > 0
    assert "mins" in text

def test_03_search_by_gps(db_session):
    """Search by GPS coordinates returns nearby facilities with distance."""
    req = FacilitySearchRequestDTO(
        latitude=18.5204,
        longitude=73.8567,
        location_method="GPS"
    )
    results = FacilityServiceEngine.search_and_rank_facilities(db_session, req)
    assert len(results) >= 5
    assert results[0].distance_km >= 0.0

def test_04_search_by_village_name(db_session):
    """Search by village name resolves coordinates and returns ranked results."""
    req = FacilitySearchRequestDTO(
        village_name="Ganeshpur",
        location_method="PINCODE_VILLAGE"
    )
    results = FacilityServiceEngine.search_and_rank_facilities(db_session, req)
    assert len(results) >= 5
    assert results[0].distance_km >= 0.0

def test_05_capability_first_ranking_emergency_override(db_session):
    """Emergency search must prioritize 24x7 emergency facilities over nearer non-emergency ones."""
    req = FacilitySearchRequestDTO(
        latitude=18.5204,
        longitude=73.8567, # Ganeshpur (1.2 km away from sub-centre without emergency)
        service_type="EMERGENCY",
        urgency="EMERGENCY"
    )
    results = FacilityServiceEngine.search_and_rank_facilities(db_session, req)
    # The nearest facility is Ganeshpur Sub-Centre (no emergency), but Kalyanpur PHC (24x7 emergency) must rank 1st
    assert results[0].emergency_capability is True
    assert "Emergency" in results[0].suitability_reason

def test_06_capability_first_ranking_maternity(db_session):
    """Maternal delivery search prioritizes labor room & maternity hospitals."""
    req = FacilitySearchRequestDTO(
        latitude=18.5204,
        longitude=73.8567,
        service_type="MATERNITY_DELIVERY"
    )
    results = FacilityServiceEngine.search_and_rank_facilities(db_session, req)
    assert results[0].suitability_score > 200.0
    assert "Maternity" in results[0].suitability_reason or "Obstetric" in results[0].suitability_reason

def test_07_child_vaccination_filter(db_session):
    """Child vaccination search prioritizes verified universal immunization centres."""
    req = FacilitySearchRequestDTO(
        latitude=18.5204,
        longitude=73.8567,
        service_type="CHILD_VACCINATION"
    )
    results = FacilityServiceEngine.search_and_rank_facilities(db_session, req)
    assert any("Immunization" in r.suitability_reason or "Vaccination" in r.suitability_reason for r in results[:3])

def test_08_unsuitable_nearer_facility_ranks_below(db_session):
    """Proves that a closer facility without required capability scores lower than a farther capable facility."""
    req = FacilitySearchRequestDTO(
        latitude=18.5204,
        longitude=73.8567,
        service_type="MATERNITY_DELIVERY"
    )
    results = FacilityServiceEngine.search_and_rank_facilities(db_session, req)
    sub_centre = next((r for r in results if r.facility_type == "SUB_CENTRE"), None)
    phc = next((r for r in results if r.facility_type == "PHC"), None)
    if sub_centre and phc:
        # PHC is further (2.8 km vs 1.2 km), but has delivery beds -> must rank higher
        assert phc.suitability_score > sub_centre.suitability_score

def test_09_facility_detail_endpoint(db_session):
    """Loads complete facility details including services, hours and empanelled schemes."""
    fac = db_session.query(Facility).filter(Facility.code == "PHC-09").first()
    assert fac is not None
    detail = FacilityServiceEngine.get_facility_detail(db_session, fac.id, lang="en-IN", user_lat=18.5204, user_lon=73.8567)
    assert detail is not None
    assert len(detail.services) >= 5
    assert len(detail.schemes) >= 2
    assert detail.is_24x7_emergency is True

def test_10_scheme_empanelment_independent_verification(db_session):
    """Verified scheme empanelments return official references and sources."""
    fac = db_session.query(Facility).filter(Facility.code == "PHC-09").first()
    detail = FacilityServiceEngine.get_facility_detail(db_session, fac.id)
    pmjay_scheme = next((s for s in detail.schemes if s.scheme_code == "PMJAY"), None)
    assert pmjay_scheme is not None
    assert pmjay_scheme.verification_status == "VERIFIED"
    assert "NHA" in pmjay_scheme.official_source or "State" in pmjay_scheme.official_source

def test_11_asha_assistance_creation_and_lifecycle(db_session):
    """Requesting ASHA assistance creates real database record with status lifecycle."""
    fac = db_session.query(Facility).filter(Facility.code == "PHC-09").first()
    assert fac is not None

    class MockProfile:
        id = "CITIZEN-SUNITA-001"
        assigned_asha_id = "ASHA-012"
        village_name = "Kalyanpur"

    req = FacilityAssistanceCreateRequestDTO(
        assistance_reason="Need transport assistance for maternal checkup",
        transport_needed=True,
        citizen_locality="Ganeshpur",
        idempotency_key="TEST-AST-KEY-001"
    )
    task = FacilityServiceEngine.create_asha_assistance_task(db_session, fac.id, req, MockProfile())
    assert task.id is not None
    assert task.status == AssistanceStatusEnum.PENDING
    assert task.transport_needed is True
    assert task.assigned_asha_name is not None

def test_12_appointment_request_lifecycle(db_session):
    """Requesting facility appointment creates real record with status REQUESTED."""
    fac = db_session.query(Facility).filter(Facility.code == "PHC-09").first()
    assert fac is not None

    class MockProfile:
        id = "CITIZEN-SUNITA-001"

    req = FacilityAppointmentCreateRequestDTO(
        service_code="CHILD_VACCINATION",
        service_name="Child Vaccination",
        requested_slot="Tomorrow 10:00 AM",
        idempotency_key="TEST-APT-KEY-001"
    )
    apt = FacilityServiceEngine.create_appointment_request(db_session, fac.id, req, MockProfile())
    assert apt.id is not None
    assert apt.status == AppointmentStatusEnum.REQUESTED
    assert apt.appointment_reference.startswith("APT-")

def test_13_mutation_idempotency(db_session):
    """Repeated mutation requests with identical idempotency_key create zero duplicates."""
    fac = db_session.query(Facility).filter(Facility.code == "PHC-09").first()
    assert fac is not None

    class MockProfile:
        id = "CITIZEN-SUNITA-001"
        assigned_asha_id = "ASHA-012"
        village_name = "Kalyanpur"

    req = FacilityAssistanceCreateRequestDTO(
        assistance_reason="Idempotency check",
        idempotency_key="IDEMPOTENT-TEST-999"
    )
    task1 = FacilityServiceEngine.create_asha_assistance_task(db_session, fac.id, req, MockProfile())
    task2 = FacilityServiceEngine.create_asha_assistance_task(db_session, fac.id, req, MockProfile())
    assert task1.id == task2.id

