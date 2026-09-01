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

# 1. GPS Success & Accurate Coordinates
def test_01_gps_search_accuracy(db_session):
    req = FacilitySearchRequestDTO(
        latitude=18.5204,
        longitude=73.8567,
        location_method="GPS"
    )
    results = FacilityServiceEngine.search_and_rank_facilities(db_session, req)
    assert len(results) >= 5
    assert results[0].distance_km >= 0.0
    assert results[0].google_maps_uri.startswith("https://www.google.com/maps")

# 2. Manual Village / PIN Geocoding Search
def test_02_manual_village_and_pin_search(db_session):
    req_village = FacilitySearchRequestDTO(
        village_name="Ganeshpur",
        location_method="PINCODE_VILLAGE"
    )
    res_village = FacilityServiceEngine.search_and_rank_facilities(db_session, req_village)
    assert len(res_village) >= 5

    req_pin = FacilitySearchRequestDTO(
        pincode="415001",
        location_method="PINCODE_VILLAGE"
    )
    res_pin = FacilityServiceEngine.search_and_rank_facilities(db_session, req_pin)
    assert len(res_pin) >= 5

# 3. Every Service Mapping Verification (10 categories)
def test_03_every_service_mapping_and_ranking(db_session):
    # A. Emergency -> Emergency Capable 24x7
    res_emerg = FacilityServiceEngine.search_and_rank_facilities(
        db_session,
        FacilitySearchRequestDTO(latitude=18.5204, longitude=73.8567, service_type="EMERGENCY", urgency="EMERGENCY")
    )
    assert res_emerg[0].emergency_capability is True

    # B. General Doctor -> PHC / CHC
    res_opd = FacilityServiceEngine.search_and_rank_facilities(
        db_session,
        FacilitySearchRequestDTO(latitude=18.5204, longitude=73.8567, service_type="GENERAL_OPD")
    )
    assert res_opd[0].facility_type in ["PHC", "CHC", "SUB_CENTRE", "DISTRICT_HOSPITAL"]

    # C. Pregnancy -> Maternity / Delivery Facility
    res_mat = FacilityServiceEngine.search_and_rank_facilities(
        db_session,
        FacilitySearchRequestDTO(latitude=18.5204, longitude=73.8567, service_type="MATERNITY")
    )
    assert any("Maternity" in r.suitability_reason or "Obstetric" in r.suitability_reason for r in res_mat[:2])

    # D. Child Health -> Pediatric / Vaccination
    res_child = FacilityServiceEngine.search_and_rank_facilities(
        db_session,
        FacilitySearchRequestDTO(latitude=18.5204, longitude=73.8567, service_type="CHILD_HEALTH")
    )
    assert any("Immunization" in r.suitability_reason or "Vaccination" in r.suitability_reason for r in res_child[:2])

    # E. Diagnostics -> Laboratory / X-Ray
    res_diag = FacilityServiceEngine.search_and_rank_facilities(
        db_session,
        FacilitySearchRequestDTO(latitude=18.5204, longitude=73.8567, service_type="DIAGNOSTICS")
    )
    assert any("Laboratory" in r.suitability_reason or "Diagnostic" in r.suitability_reason for r in res_diag[:3])

    # F. Pharmacy -> Pharmacy / Jan Aushadhi
    res_pharm = FacilityServiceEngine.search_and_rank_facilities(
        db_session,
        FacilitySearchRequestDTO(latitude=18.5204, longitude=73.8567, service_type="PHARMACY")
    )
    assert any("Pharmacy" in r.suitability_reason or "Medicines" in r.suitability_reason for r in res_pharm[:3])

    # G. TB -> DOTS / NTEP Centre
    res_tb = FacilityServiceEngine.search_and_rank_facilities(
        db_session,
        FacilitySearchRequestDTO(latitude=18.5204, longitude=73.8567, service_type="TB_DOTS")
    )
    assert any("TB" in r.suitability_reason or "DOTS" in r.suitability_reason for r in res_tb[:2])

    # H. Diabetes / BP -> NCD Clinic
    res_ncd = FacilityServiceEngine.search_and_rank_facilities(
        db_session,
        FacilitySearchRequestDTO(latitude=18.5204, longitude=73.8567, service_type="NCD")
    )
    assert any("NCD" in r.suitability_reason or "Diabetes" in r.suitability_reason for r in res_ncd[:2])

    # I. Scheme Desk -> Ayushman Help Desk
    res_scheme = FacilityServiceEngine.search_and_rank_facilities(
        db_session,
        FacilitySearchRequestDTO(latitude=18.5204, longitude=73.8567, service_type="SCHEME_HELP")
    )
    assert any("Ayushman" in r.suitability_reason or "Scheme" in r.suitability_reason for r in res_scheme[:2])

    # J. Surgery -> District Hospital / CHC
    res_surg = FacilityServiceEngine.search_and_rank_facilities(
        db_session,
        FacilitySearchRequestDTO(latitude=18.5204, longitude=73.8567, service_type="SURGERY")
    )
    assert any("Surgery" in r.suitability_reason or "Operation Theatre" in r.suitability_reason for r in res_surg[:2])

# 4. Capability vs Distance Ranking
def test_04_capability_trumps_raw_distance(db_session):
    # Search for surgery from Ganeshpur coordinates (near sub-centre which has no surgery)
    req = FacilitySearchRequestDTO(
        latitude=18.5204,
        longitude=73.8567,
        service_type="SURGERY"
    )
    results = FacilityServiceEngine.search_and_rank_facilities(db_session, req)
    assert results[0].facility_type in ["CHC", "DISTRICT_HOSPITAL", "SPECIALIZED_HOSPITAL"]
    assert results[0].suitability_score > 150.0

# 5. Empty Results when outside coverage radius
def test_05_empty_results_handling(db_session):
    # Coordinate far away in the ocean
    req = FacilitySearchRequestDTO(
        latitude=0.0,
        longitude=0.0,
        max_distance_km=5.0
    )
    results = FacilityServiceEngine.search_and_rank_facilities(db_session, req)
    assert len(results) == 0

# 6. Google Places Labeling and Provenance
def test_06_google_places_unverified_label(db_session):
    req = FacilitySearchRequestDTO(
        latitude=18.5204,
        longitude=73.8567,
        service_type="GENERAL_OPD"
    )
    results = FacilityServiceEngine.search_and_rank_facilities(db_session, req)
    for r in results:
        if r.verification_status == "GOOGLE_DISCOVERED_UNVERIFIED":
            assert r.source == "GOOGLE_PLACES"
            assert "Unverified" in r.operating_status_label or "Google" in r.operating_status_label

# 7. Directions URL and Phone Formatting
def test_07_directions_and_phone(db_session):
    fac = db_session.query(Facility).filter(Facility.code == "PHC-09").first()
    assert fac is not None
    detail = FacilityServiceEngine.get_facility_detail(db_session, fac.id)
    assert detail.phone is not None
    assert detail.google_maps_uri.startswith("https://www.google.com/maps")

# 8. Request ASHA Assistance & Appointment
def test_08_service_requests_creation(db_session):
    fac = db_session.query(Facility).filter(Facility.code == "PHC-09").first()
    class MockProfile:
        id = "CITIZEN-TEST-001"
        assigned_asha_id = "ASHA-001"
        village_name = "Kalyanpur"

    # ASHA request
    asha_req = FacilityAssistanceCreateRequestDTO(
        assistance_reason="Escort to PHC for delivery check",
        transport_needed=True,
        citizen_locality="Kalyanpur",
        idempotency_key="TEST-AST-999"
    )
    task = FacilityServiceEngine.create_asha_assistance_task(db_session, fac.id, asha_req, MockProfile())
    assert task.status == AssistanceStatusEnum.PENDING

    # Appointment request
    apt_req = FacilityAppointmentCreateRequestDTO(
        service_code="GENERAL_OPD",
        service_name="General OPD",
        requested_slot="Tomorrow 10:00 AM",
        idempotency_key="TEST-APT-999"
    )
    apt = FacilityServiceEngine.create_appointment_request(db_session, fac.id, apt_req, MockProfile())
    assert apt.status == AppointmentStatusEnum.REQUESTED
