import time
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app.models import CitizenProfile

client = TestClient(app)

def test_backend_language_profile_update():
    db = SessionLocal()
    try:
        # 1. Update language preference via API
        res = client.patch("/api/citizen/profile/language", json={
            "preferred_language": "hi-IN"
        })
        assert res.status_code == 200
        data = res.json().get("data")
        assert data["preferred_language"] == "hi-IN"
        assert data["language_confirmed_at"] is not None

        # Verify DB row
        profile = db.query(CitizenProfile).filter(CitizenProfile.id == data["id"]).first()
        assert profile is not None
        assert profile.preferred_language == "hi-IN"
        assert profile.language_confirmed_at is not None

        # 2. Update to Marathi
        res_mr = client.patch("/api/citizen/profile/language", json={
            "preferred_language": "mr-IN"
        })
        assert res_mr.status_code == 200
        assert res_mr.json()["data"]["preferred_language"] == "mr-IN"
    finally:
        db.close()
