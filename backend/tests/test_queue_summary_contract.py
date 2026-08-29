import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app.models import User, Referral, UserRoleEnum
from app.auth.security import create_access_token
from app.seeds.seed_full_demo import seed_full_demonstration
from app.services.referral_service import get_doctor_referrals_summary, get_doctor_referrals_list

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

def test_queue_summary_canonical_keys(db_session, doctor_headers):
    """Test that summary API returns exact canonical keys required by Requirement 1 & 5."""
    seed_full_demonstration()
    
    res = client.get("/api/doctor/referrals/summary", headers=doctor_headers)
    assert res.status_code == 200
    data = res.json()["data"]
    
    required_keys = [
        "total_active_referrals",
        "urgent_pending_review",
        "transport_en_route",
        "patient_arrived",
        "in_consultation",
        "processed_today"
    ]
    
    for key in required_keys:
        assert key in data, f"Summary payload missing canonical key: '{key}'"
        assert isinstance(data[key], int)

def test_summary_counts_reconcile_with_list_predicates(db_session, doctor_headers):
    """Test that summary counts match direct database queries and list endpoint filters."""
    doc = db_session.query(User).filter(User.id == "DOC-007").first()
    
    summary_direct = get_doctor_referrals_summary(db_session, doc)
    
    # 1. Total Active
    items_active, total_active = get_doctor_referrals_list(db_session, doc, status_filter="ALL_ACTIVE")
    assert summary_direct["total_active_referrals"] == total_active
    
    # 2. Urgent Pending Review
    items_urgent_pending, total_urgent_pending = get_doctor_referrals_list(db_session, doc, status_filter="URGENT_PENDING_REVIEW")
    assert summary_direct["urgent_pending_review"] == total_urgent_pending
    
    # 3. Transport Arranged / En Route
    items_transport, total_transport = get_doctor_referrals_list(db_session, doc, status_filter="TRANSPORT_ARRANGED")
    assert summary_direct["transport_arranged"] == total_transport
    
    # 4. Patient Arrived
    items_arrived, total_arrived = get_doctor_referrals_list(db_session, doc, status_filter="PATIENT_ARRIVED")
    assert summary_direct["patient_arrived"] == total_arrived
    
    # 5. Processed Today
    items_processed, total_processed = get_doctor_referrals_list(db_session, doc, status_filter="PROCESSED_TODAY")
    assert summary_direct["processed_today"] == total_processed

def test_unauthenticated_summary_request_fails():
    """Summary API must fail with 401 when unauthenticated, not return empty zeros."""
    res = client.get("/api/doctor/referrals/summary")
    assert res.status_code == 401
