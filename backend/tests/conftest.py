import pytest
import os
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Use in-memory SQLite with StaticPool so all connections share the same memory DB
TEST_DATABASE_URL = "sqlite:///:memory:"

from app.database import Base, get_db
import app.models  # Register all models on Base metadata
from app.main import app
from app.seeds.seed_data import seed_database
import app.seeds.seed_data as seed_module

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    import app.models  # Ensure all SQLAlchemy models are registered on Base
    from app.models import (
        CitizenProfile, HouseholdMember, CitizenChatSession, CitizenChatMessage, CitizenNeed,
        ServiceRequest, Case, Referral, Prescription, FollowUp, Facility, User,
        TeleconsultationRequest, TeleconsultationMessage, TeleconsultationConsent, TeleconsultationStatusHistory
    )
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    # Seed the test database
    seed_module.engine = test_engine
    seed_module.SessionLocal = TestingSessionLocal
    seed_module.seed_database()

    # Explicitly seed schemes into test in-memory DB
    import os
    from app.schemes.import_kb import import_knowledge_base
    kb_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../schemes"))
    if os.path.exists(kb_path):
        test_db = TestingSessionLocal()
        try:
            import_knowledge_base(kb_path, db_session=test_db)
        finally:
            test_db.close()

    yield
    Base.metadata.drop_all(bind=test_engine)

@pytest.fixture
def client():
    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture
def doctor_auth_headers():
    from app.auth.security import create_access_token
    token = create_access_token({"sub": "DOC-007", "role": "PHC_DOCTOR", "facility_id": "PHC-09"})
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def citizen_auth_headers():
    from app.auth.security import create_access_token
    token = create_access_token({"sub": "CP-001", "role": "CITIZEN", "phone": "9823012345"})
    return {"Authorization": f"Bearer {token}"}

