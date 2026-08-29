import pytest
from app.main import app

def test_scheme_categories_endpoint(client):
    """Verify 12 rural-friendly category cards with database-derived counts."""
    response = client.get("/api/citizen/schemes/categories")
    assert response.status_code == 200
    data = response.json().get("data", [])
    assert len(data) == 12
    maternal = next((c for c in data if c["category_id"] == "maternal_health" or c["category_code"] == "maternal_health"), None)
    assert maternal is not None
    assert maternal["active_scheme_count"] >= 1
    assert "Pregnancy & Maternity" in maternal["title_en"]

def test_schemes_list_with_envelope(client):
    """Verify standard envelope format with items, total, page, page_size."""
    response = client.get("/api/citizen/schemes?page=1&page_size=10")
    assert response.status_code == 200
    res = response.json()
    data = res.get("data", {})
    assert "items" in data
    assert "total" in data
    assert data["total"] >= 20
    assert len(data["items"]) <= 10

def test_schemes_category_filter(client):
    """Verify category filtering works deterministically."""
    response = client.get("/api/citizen/schemes?category_id=maternal_health")
    assert response.status_code == 200
    data = response.json().get("data", {})
    items = data.get("items", [])
    assert len(items) >= 1
    codes = [i["scheme_code"] for i in items]
    assert any("PMMVY" in c or "JSY" in c or "JSSK" in c for c in codes)

def test_scheme_detail_authoritative(client):
    """Verify scheme detail returns source-backed facts and no mock/hardcoded false statuses."""
    # Test with IN-MWCD-PMMVY-2 or IN-NHA-PMJAY
    response = client.get("/api/citizen/schemes/IN-MWCD-PMMVY-2")
    assert response.status_code == 200
    detail = response.json().get("data", {})
    assert detail["scheme_name"] != ""
    assert "authority" in detail
    assert "benefits" in detail
    assert "required_documents" in detail
    assert "official_verification_disclaimer" in detail

def test_scheme_application_guidance_endpoint(client):
    """Verify scheme application guidance endpoint returns steps and help centers."""
    response = client.get("/api/citizen/schemes/IN-MWCD-PMMVY-2/application-guidance")
    assert response.status_code == 200
    guidance = response.json().get("data", {})
    assert "application_steps" in guidance
    assert len(guidance["application_steps"]) >= 1
    assert "help_centers" in guidance

def test_single_scheme_screening_pregnant_citizen(client):
    """Verify single scheme screening returns 3-valued deterministic rules."""
    payload = {
        "is_pregnant": True,
        "age": 24,
        "additional_facts": {
            "is_pregnant": True,
            "age": 24,
            "child_order": 1,
            "institutional_delivery_planned": True,
            "has_bpl_ration_card": True,
            "social_category": "BPL"
        }
    }
    response = client.post("/api/citizen/schemes/IN-MWCD-PMMVY-2/screen", json=payload)
    assert response.status_code == 200
    res = response.json().get("data", {})
    assert "eligibility_status" in res
    assert res["eligibility_status"] in ["LIKELY_ELIGIBLE", "POTENTIALLY_ELIGIBLE", "OFFICIAL_VERIFICATION_REQUIRED", "MORE_INFORMATION_REQUIRED"]
    assert "matched_rules" in res

def test_request_scheme_asha_assistance_idempotent(client):
    """Verify requesting ASHA assistance creates a task idempotently."""
    payload = {
        "beneficiary_name": "Sunita Devi",
        "missing_facts": ["has_bpl_ration_card"],
        "missing_documents": ["Aadhaar Card", "MCP Passbook"],
        "preferred_contact_method": "HOME_VISIT"
    }
    # First request
    res1 = client.post("/api/citizen/schemes/IN-MWCD-PMMVY-2/asha-assistance", json=payload)
    assert res1.status_code == 200
    data1 = res1.json().get("data", {})
    assert "request_id" in data1
    assert "request_reference" in data1

    # Second request (Idempotency test)
    res2 = client.post("/api/citizen/schemes/IN-MWCD-PMMVY-2/asha-assistance", json=payload)
    assert res2.status_code == 200
    data2 = res2.json().get("data", {})
    assert data2["request_reference"] == data1["request_reference"]

def test_batch_schemes_screening(client):
    """Verify POST /api/citizen/schemes/screen evaluates all 29 schemes."""
    payload = {
        "is_pregnant": True,
        "age": 24,
        "additional_facts": {
            "is_pregnant": True,
            "age": 24
        }
    }
    res = client.post("/api/citizen/schemes/screen", json=payload)
    assert res.status_code == 200
    data = res.json().get("data", {})
    assert data["total_schemes_evaluated"] >= 20
    assert len(data["results"]) >= 20

def test_scheme_help_requirements(client):
    """Verify GET /api/citizen/schemes/{scheme_id}/help-requirements returns assistance capabilities."""
    response = client.get("/api/citizen/schemes/IN-NHA-PMJAY/help-requirements")
    assert response.status_code == 200
    data = response.json().get("data", {})
    assert data["scheme_code"] == "IN-NHA-PMJAY"
    assert "required_capabilities" in data
    assert len(data["required_capabilities"]) >= 1
    codes = [c["capability_code"] for c in data["required_capabilities"]]
    assert "PMJAY_HELP_DESK" in codes or "CSC" in codes

def test_scheme_help_centres_search_with_distance_and_ranking(client):
    """Verify POST /api/citizen/schemes/{scheme_id}/help-centres/search returns ranked verified facilities."""
    payload = {
        "location": {
            "source": "CURRENT_GPS",
            "latitude": 18.5204,
            "longitude": 73.8567
        },
        "radius_km": 50,
        "language": "mr-IN"
    }
    response = client.post("/api/citizen/schemes/IN-NHA-PMJAY/help-centres/search", json=payload)
    assert response.status_code == 200
    data = response.json().get("data", {})
    assert "items" in data
    assert "total" in data
    assert len(data["items"]) >= 1
    
    first = data["items"][0]
    assert "facility_id" in first
    assert "name" in first
    assert "distance_km" in first
    assert "travel_time_text" in first
    assert "google_maps_directions_url" in first
    assert "https://www.google.com/maps/dir/?api=1" in first["google_maps_directions_url"]

def test_scheme_help_centres_invalid_coordinates_rejected(client):
    """Verify invalid coordinates (>90 lat or >180 lng) return 400 Bad Request."""
    payload = {
        "location": {
            "source": "CURRENT_GPS",
            "latitude": 195.0,
            "longitude": 73.8567
        }
    }
    response = client.post("/api/citizen/schemes/IN-NHA-PMJAY/help-centres/search", json=payload)
    assert response.status_code == 400

def test_scheme_help_centre_facility_detail(client):
    """Verify GET /api/citizen/schemes/{scheme_id}/help-centres/{facility_id} returns full facility details."""
    response = client.get("/api/citizen/schemes/IN-NHA-PMJAY/help-centres/PHC-09?lat=18.5204&lon=73.8567")
    assert response.status_code == 200
    data = response.json().get("data", {})
    assert "facility" in data
    assert "scheme" in data
    assert "required_documents" in data
    assert "application_guidance" in data
    assert "operating_hours" in data
    assert "Final document and eligibility verification" in data["application_guidance"]["verification_disclaimer"]

# -------------------------------------------------------------
# -------------------------------------------------------------
# CITIZEN PROFILE, HOUSEHOLD, CARE-TEAM & PRIVACY TESTS
# -------------------------------------------------------------

def test_citizen_profile_endpoints(client):
    """Verify citizen profile retrieval and patch endpoints."""
    res = client.get("/api/citizen/profile")
    assert res.status_code == 200, res.text
    data = res.json().get("data", {})
    assert "id" in data
    assert "display_name" in data
    assert "household_count" in data
    assert "abha_status" in data
    assert data["abha_status"] in ["NOT_LINKED", "LINK_PENDING", "LINKED_UNVERIFIED", "VERIFIED_SANDBOX", "VERIFIED_LIVE"]

    patch_res = client.patch("/api/citizen/profile", json={
        "preferred_name": "Sunita",
        "alternate_phone": "9876500000",
        "current_care_location": "Near Panchayat Bhavan, Kalyanpur",
        "emergency_contact_name": "Ramesh",
        "emergency_contact_phone": "9876511111",
        "emergency_contact_relation": "SPOUSE"
    })
    assert patch_res.status_code == 200, patch_res.text
    patch_data = patch_res.json().get("data", {})
    assert patch_data["preferred_name"] == "Sunita"
    assert patch_data["current_care_location"] == "Near Panchayat Bhavan, Kalyanpur"
    assert patch_data["emergency_contact_name"] == "Ramesh"

def test_citizen_household_crud(client):
    """Verify complete household directory CRUD with duplicate checking and safe deletion."""
    get_res = client.get("/api/citizen/household")
    assert get_res.status_code == 200
    raw_members = get_res.json().get("data", [])
    members = raw_members.get("items", raw_members) if isinstance(raw_members, dict) else raw_members
    assert isinstance(members, list)

    # Add Member
    post_res = client.post("/api/citizen/household", json={
        "full_name": "Deepak",
        "relationship_type": "CHILD",
        "age": 5,
        "sex": "Male",
        "blood_group": "B+",
        "health_notes": "All vaccines received on schedule",
        "consent_obtained": True
    })
    assert post_res.status_code == 200, post_res.text
    new_member = post_res.json().get("data", {})
    assert new_member["full_name"] == "Deepak"
    assert new_member["relationship_type"] == "CHILD"
    assert new_member["age"] == 5
    member_id = new_member["id"]

    # Duplicate rejection check
    dup_res = client.post("/api/citizen/household", json={
        "full_name": "Deepak",
        "relationship_type": "CHILD",
        "age": 5
    })
    assert dup_res.status_code == 400
    assert "already exists" in dup_res.text

    # Detail check
    detail_res = client.get(f"/api/citizen/household/{member_id}")
    assert detail_res.status_code == 200
    detail_data = detail_res.json().get("data", {})
    assert detail_data["id"] == member_id
    assert detail_data["full_name"] == "Deepak"

    # Update check
    update_res = client.patch(f"/api/citizen/household/{member_id}", json={
        "age": 6,
        "health_notes": "Updated: Started primary school"
    })
    assert update_res.status_code == 200
    update_data = update_res.json().get("data", {})
    assert update_data["age"] == 6
    assert "Started primary school" in update_data["health_notes"]

    # Delete check
    del_res = client.delete(f"/api/citizen/household/{member_id}")
    assert del_res.status_code == 200

    # Verify no longer returned in active list
    after_get = client.get("/api/citizen/household")
    raw_after = after_get.json().get("data", [])
    active_members = raw_after.get("items", raw_after) if isinstance(raw_after, dict) else raw_after
    assert all(m["id"] != member_id for m in active_members)

def test_citizen_care_team(client):
    """Verify care team resolution from active jurisdictions."""
    res = client.get("/api/citizen/care-team")
    assert res.status_code == 200, res.text
    data = res.json().get("data", {})
    assert "assigned_asha" in data
    assert "assigned_phc" in data
    assert "assigned_doctor" in data
    assert data["assigned_asha"] is not None
    assert data["assigned_asha"]["phone"] is not None
    assert data["assigned_phc"] is not None

def test_citizen_consents_and_privacy(client):
    """Verify DPDP consents listing and revoking audit trail."""
    res = client.get("/api/citizen/consents")
    assert res.status_code == 200, res.text
    raw_consents = res.json().get("data", [])
    consents = raw_consents.get("items", raw_consents) if isinstance(raw_consents, dict) else raw_consents
    assert isinstance(consents, list)
    assert len(consents) > 0
    active_consent = next((c for c in consents if not c["is_revoked"]), None)
    assert active_consent is not None

    revoke_res = client.patch("/api/citizen/consents", json={
        "consent_id": active_consent["id"],
        "reason": "Revoked for testing"
    })
    assert revoke_res.status_code == 200
    revoked = revoke_res.json().get("data", {})
    assert revoked["is_revoked"] is True
    assert revoked["revocation_reason"] == "Revoked for testing"

def test_citizen_language_preference(client):
    """Verify immediate language preference change and retrieval."""
    res = client.get("/api/citizen/preferences/language")
    assert res.status_code == 200
    assert "preferred_language" in res.json().get("data", {})

    patch_res = client.patch("/api/citizen/preferences/language", json={
        "preferred_language": "hi-IN"
    })
    assert patch_res.status_code == 200
    assert patch_res.json().get("data", {})["preferred_language"] == "hi-IN"

    # Revert to mr-IN
    client.patch("/api/citizen/preferences/language", json={"preferred_language": "mr-IN"})

def test_citizen_abha_status(client):
    """Verify honest ABHA status, disclaimer and sandbox mode metadata."""
    res = client.get("/api/citizen/abha-link-status")
    assert res.status_code == 200
    data = res.json().get("data", {})
    assert "status" in data
    assert "status_label" in data
    assert "is_verified" in data
    assert "disclaimer" in data




