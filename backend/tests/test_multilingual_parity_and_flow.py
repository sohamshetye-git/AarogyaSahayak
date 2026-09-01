import os
import json
import pytest
from fastapi.testclient import TestClient

def test_i18n_locale_key_parity():
    """Verify that all 11 Indian locale JSON files contain identical keys."""
    def get_keys(d, prefix=""):
        keys = set()
        for k, v in d.items():
            curr = f"{prefix}.{k}" if prefix else k
            if isinstance(v, dict):
                keys.update(get_keys(v, curr))
            else:
                keys.add(curr)
        return keys

    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    locales_dir = os.path.join(base_dir, "packages", "i18n", "locales")

    with open(os.path.join(locales_dir, "en-IN.json"), encoding="utf-8") as f_en:
        en_keys = get_keys(json.load(f_en))

    assert len(en_keys) >= 600, f"Expected >=600 keys, found {len(en_keys)}"

    all_locales = [
        "hi-IN", "mr-IN", "gu-IN", "bn-IN", "kn-IN",
        "te-IN", "ta-IN", "ml-IN", "pa-IN", "od-IN"
    ]

    for locale in all_locales:
        locale_path = os.path.join(locales_dir, f"{locale}.json")
        assert os.path.exists(locale_path), f"Locale file missing: {locale_path}"
        with open(locale_path, encoding="utf-8") as f_loc:
            loc_keys = get_keys(json.load(f_loc))
        missing = en_keys - loc_keys
        extra = loc_keys - en_keys
        assert not missing, f"Missing keys in {locale}: {missing}"
        assert not extra, f"Extra keys in {locale}: {extra}"

def test_user_preference_persistence_and_independence(client: TestClient):
    """Verify that different roles persist independent language preferences."""
    # 1. Citizen sets Marathi
    citizen_login = client.post("/api/auth/login", json={"identifier": "sunita.devi", "password": "demo123"})
    assert citizen_login.status_code == 200
    citizen_token = citizen_login.json()["data"]["access_token"]
    citizen_headers = {"Authorization": f"Bearer {citizen_token}"}

    pref_res = client.patch("/api/auth/me/preferences", json={"preferred_language": "mr-IN"}, headers=citizen_headers)
    assert pref_res.status_code == 200
    assert pref_res.json()["data"]["preferred_language"] == "mr-IN"

    # 2. ASHA sets Hindi
    asha_login = client.post("/api/auth/login", json={"identifier": "sita.asha", "password": "demo123"})
    assert asha_login.status_code == 200
    asha_token = asha_login.json()["data"]["access_token"]
    asha_headers = {"Authorization": f"Bearer {asha_token}"}

    asha_pref = client.patch("/api/auth/me/preferences", json={"preferred_language": "hi-IN"}, headers=asha_headers)
    assert asha_pref.status_code == 200
    assert asha_pref.json()["data"]["preferred_language"] == "hi-IN"

    # 3. Doctor sets English
    doc_login = client.post("/api/auth/login", json={"identifier": "dr.sharma", "password": "demo123"})
    assert doc_login.status_code == 200
    doc_token = doc_login.json()["data"]["access_token"]
    doc_headers = {"Authorization": f"Bearer {doc_token}"}

    doc_pref = client.patch("/api/auth/me/preferences", json={"preferred_language": "en-IN"}, headers=doc_headers)
    assert doc_pref.status_code == 200
    assert doc_pref.json()["data"]["preferred_language"] == "en-IN"

    # 4. Verify Citizen is still mr-IN, ASHA is hi-IN, Doctor is en-IN
    c_me = client.get("/api/auth/me", headers=citizen_headers).json()["data"]
    a_me = client.get("/api/auth/me", headers=asha_headers).json()["data"]
    d_me = client.get("/api/auth/me", headers=doc_headers).json()["data"]

    assert c_me["preferred_language"] == "mr-IN"
    assert a_me["preferred_language"] == "hi-IN"
    assert d_me["preferred_language"] == "en-IN"

def test_canonical_codes_and_original_transcript_preservation(client: TestClient):
    """Verify backend maintains canonical codes and original transcript in Marathi."""
    marathi_transcript = "मला छातीत खूप दुखत आहे आणि श्वास घ्यायला त्रास होतोय."
    create_res = client.post(
        "/api/citizen/cases",
        json={
            "preferred_language": "mr-IN",
            "spoken_transcript": marathi_transcript,
            "symptoms": ["chest pain", "breathlessness"],
            "vitals": {"systolic_bp": 160, "diastolic_bp": 100, "spo2": 92}
        }
    )
    assert create_res.status_code == 200
    data = create_res.json()["data"]

    # Canonical status and priority
    assert data["status"] in ["NEW", "ASHA_ASSIGNED"]
    assert data["priority"] == "URGENT"
    assert data["safety_rule_triggered"] is True

    # Doctor views case and verifies original transcript is untouched
    doc_login = client.post("/api/auth/login", json={"identifier": "dr.sharma", "password": "demo123"})
    doc_token = doc_login.json()["data"]["access_token"]
    doc_headers = {"Authorization": f"Bearer {doc_token}"}

    case_res = client.get(f"/api/doctor/consultations/{data['case_id']}", headers=doc_headers)
    assert case_res.status_code == 200
    case_detail = case_res.json()["data"]
    assert case_detail["primary_concern"] == marathi_transcript
    assert case_detail["preferred_language"] == "mr-IN"
    assert case_detail["priority"] == "URGENT"



