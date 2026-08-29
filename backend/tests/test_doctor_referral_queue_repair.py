import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app.models import User, Referral, Case, Facility, WorkerProfile, CasePriorityEnum, UserRoleEnum
from app.auth.security import create_access_token
from app.seeds.seed_full_demo import seed_full_demonstration, verify_relationships
from app.services.referral_service import get_doctor_referrals_list, get_doctor_referrals_summary

client = TestClient(app)

@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture
def doctor_headers(db_session):
    doc = db_session.query(User).filter(User.id == "DOC-007").first()
    if not doc:
        doc = db_session.query(User).filter(User.role == UserRoleEnum.PHC_DOCTOR).first()
    token = create_access_token({"sub": doc.id, "role": "PHC_DOCTOR"})
    return {"Authorization": f"Bearer {token}"}

def test_development_seed_and_idempotency(db_session):
    """Test seed execution and zero-duplicate re-run."""
    seed_full_demonstration()
    verify_relationships()
    
    # Measure counts before second run
    ref_count_before = db_session.query(Referral).count()
    
    # Run seed second time
    seed_full_demonstration()
    ref_count_after = db_session.query(Referral).count()
    
    assert ref_count_after == ref_count_before, "Seed rerun created duplicate referrals!"

def test_summary_api_matches_database_queries(db_session, doctor_headers):
    """Test summary endpoint counts match direct database queries exactly."""
    res = client.get("/api/doctor/referrals/summary", headers=doctor_headers)
    assert res.status_code == 200
    data = res.json()["data"]
    
    doc = db_session.query(User).filter(User.id == "DOC-007").first()
    summary_direct = get_doctor_referrals_summary(db_session, doc)
    
    assert data["new_referrals"] == summary_direct["new_referrals"]
    assert data["active_urgent_referrals"] == summary_direct["active_urgent_referrals"]
    assert data["urgent_pending_review"] == summary_direct["urgent_pending_review"]
    assert data["acknowledged"] == summary_direct["acknowledged"]
    assert data["transport_arranged"] == summary_direct["transport_arranged"]
    assert data["patient_arrived"] == summary_direct["patient_arrived"]
    assert data["in_consultation"] == summary_direct["in_consultation"]
    assert data["processed_today"] == summary_direct["processed_today"]
    assert data["total_active_referrals"] == summary_direct["total_active_referrals"]

def test_list_api_response_contract_and_filters(db_session, doctor_headers):
    """Test GET /api/doctor/referrals returns items, total, page, page_size and respects filters."""
    res = client.get("/api/doctor/referrals", headers=doctor_headers)
    assert res.status_code == 200
    data = res.json()["data"]
    
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "page_size" in data
    assert isinstance(data["items"], list)
    assert data["total"] == len(data["items"])
    
    # Excludes processed/completed records from ALL_ACTIVE
    for item in data["items"]:
        assert item["status"] not in ["PROCESSED", "COMPLETED", "CLOSED"]

def test_optional_missing_vitals_do_not_remove_referral(db_session, doctor_headers):
    """Referrals without vitals or visits must still be returned in list API."""
    doc = db_session.query(User).filter(User.id == "DOC-007").first()
    
    # Create test case & referral with no vitals
    c = Case(
        reference="CASE-NO-VITALS-001",
        citizen_id=db_session.query(Referral).first().case.citizen_id,
        assigned_facility_id="PHC-09",
        primary_concern="No vitals test case",
        priority=CasePriorityEnum.ROUTINE,
        status="REFERRED_TO_PHC"
    )
    db_session.add(c)
    db_session.flush()
    
    ref = Referral(
        reference="REF-NO-VITALS-001",
        case_id=c.id,
        to_facility_id="PHC-09",
        urgency=CasePriorityEnum.ROUTINE,
        reason="Test referral with no vitals",
        status="PENDING_DOCTOR_REVIEW"
    )
    db_session.add(ref)
    db_session.commit()
    
    items, total = get_doctor_referrals_list(db_session, doc, status_filter="PENDING_DOCTOR_REVIEW")
    found = any(i["id"] == ref.id for i in items)
    assert found, "Referral with missing optional vitals was wrongly filtered out!"
    
    # Cleanup test referral
    db_session.delete(ref)
    db_session.delete(c)
    db_session.commit()

def test_unauthorized_request_fails(db_session):
    """API failures must return 401 and not empty list."""
    res = client.get("/api/doctor/referrals")
    assert res.status_code == 401
    assert "items" not in res.json()
