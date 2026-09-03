import pytest
from app.models import User, WorkerProfile, UserRoleEnum, AuditLog
from app.auth.security import get_password_hash, verify_password

def get_auth_token(client, identifier: str, password: str = "demo123") -> str:
    res = client.post("/api/auth/login", json={"identifier": identifier, "password": password})
    assert res.status_code == 200, f"Login failed for {identifier}: {res.text}"
    return res.json()["data"]["access_token"]

def test_admin_staff_management_complete_flow(client, db_session):
    # Ensure Admin user exists with staff fields
    admin = db_session.query(User).filter(User.identifier == "dho.admin").first()
    if not admin:
        admin = User(
            id="ADMIN-003",
            identifier="dho.admin",
            name="Dr. Rajesh Deshmukh",
            role=UserRoleEnum.DISTRICT_ADMIN,
            password_hash=get_password_hash("demo123"),
            is_active=True,
            account_status="ACTIVE"
        )
        db_session.add(admin)
        admin_wp = WorkerProfile(
            user_id="ADMIN-003",
            worker_type="ADMIN",
            district_name="District 04",
            district_id="dist-04"
        )
        db_session.add(admin_wp)
        db_session.commit()

    # 1. Admin login
    admin_token = get_auth_token(client, "dho.admin", "demo123")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # 2. Non-admin roles (ASHA) should receive 403 on staff endpoints
    asha_token = get_auth_token(client, "sita.asha", "demo123")
    asha_headers = {"Authorization": f"Bearer {asha_token}"}
    res_403 = client.get("/api/admin/staff", headers=asha_headers)
    assert res_403.status_code == 403, f"Expected 403 for ASHA, got: {res_403.status_code}"

    # 3. Create ASHA Worker
    create_asha_payload = {
        "name": "Pooja Santosh Shinde",
        "role": "ASHA_WORKER",
        "phone": "9823112233",
        "email": "pooja.shinde@arogya.gov.in",
        "employee_id": "EMP-ASHA-0099",
        "preferred_language": "mr-IN",
        "district": "District 04",
        "village_name": "Kalyanpur",
        "coverage_area": "Ward 4"
    }
    create_res = client.post("/api/admin/staff", json=create_asha_payload, headers=admin_headers)
    assert create_res.status_code == 201, f"Create ASHA failed: {create_res.text}"
    creds_asha = create_res.json()["data"]
    assert creds_asha["staff_id"].startswith("ASHA-")
    assert creds_asha["temporary_password"]
    assert creds_asha["must_change_password"] is True

    asha_staff_id = creds_asha["staff_id"]
    asha_temp_pwd = creds_asha["temporary_password"]

    # 4. Duplicate employee_id check returns 409
    dup_res = client.post("/api/admin/staff", json=create_asha_payload, headers=admin_headers)
    assert dup_res.status_code == 409, f"Expected 409 for duplicate employee_id, got {dup_res.status_code}"

    # 5. Create PHC Doctor
    create_doc_payload = {
        "name": "Dr. Vikas Deshpande",
        "role": "PHC_DOCTOR",
        "phone": "9823445566",
        "email": "dr.vikas@phc.arogya.gov.in",
        "employee_id": "EMP-DOC-0044",
        "medical_registration_number": "MMC-2024-88991",
        "specialization": "Pediatrics",
        "preferred_language": "mr-IN",
        "district": "District 04"
    }
    doc_res = client.post("/api/admin/staff", json=create_doc_payload, headers=admin_headers)
    assert doc_res.status_code == 201, f"Create Doctor failed: {doc_res.text}"
    creds_doc = doc_res.json()["data"]
    assert creds_doc["staff_id"].startswith("DOC-")
    assert creds_doc["temporary_password"]

    # Duplicate medical_registration_number returns 409
    dup_doc = client.post("/api/admin/staff", json={**create_doc_payload, "employee_id": "EMP-DOC-DIFF"}, headers=admin_headers)
    assert dup_doc.status_code == 409

    # 6. Newly created ASHA logs in with Staff ID and temporary password
    login_res = client.post("/api/auth/login", json={"identifier": asha_staff_id, "password": asha_temp_pwd})
    assert login_res.status_code == 200
    login_data = login_res.json()["data"]
    assert login_data["user"]["must_change_password"] is True
    assert login_data["user"]["role"] == "ASHA_WORKER"
    new_asha_token = login_data["access_token"]
    new_asha_headers = {"Authorization": f"Bearer {new_asha_token}"}

    # 7. Mandatory password change
    change_res = client.post(
        "/api/auth/change-password",
        json={"old_password": asha_temp_pwd, "new_password": "NewSecurePassword123!"},
        headers=new_asha_headers
    )
    assert change_res.status_code == 200

    # Verify old temporary password is no longer valid
    old_login = client.post("/api/auth/login", json={"identifier": asha_staff_id, "password": asha_temp_pwd})
    assert old_login.status_code == 401

    # Verify login with new password succeeds and must_change_password is False
    new_login = client.post("/api/auth/login", json={"identifier": asha_staff_id, "password": "NewSecurePassword123!"})
    assert new_login.status_code == 200
    assert new_login.json()["data"]["user"]["must_change_password"] is False

    # 8. Admin lists staff & verifies filtering
    list_res = client.get("/api/admin/staff?search=Pooja", headers=admin_headers)
    assert list_res.status_code == 200
    staff_items = list_res.json()["data"]["staff"]
    assert any(s["staff_id"] == asha_staff_id for s in staff_items)

    # 9. Admin suspends staff -> login and access blocked
    susp_res = client.post(f"/api/admin/staff/{asha_staff_id}/suspend", json={"reason": "Audit verification"}, headers=admin_headers)
    assert susp_res.status_code == 200
    assert susp_res.json()["data"]["account_status"] == "SUSPENDED"

    # Suspended user login fails with 403
    susp_login = client.post("/api/auth/login", json={"identifier": asha_staff_id, "password": "NewSecurePassword123!"})
    assert susp_login.status_code == 403

    # 10. Admin reactivates staff -> login restored
    react_res = client.post(f"/api/admin/staff/{asha_staff_id}/reactivate", headers=admin_headers)
    assert react_res.status_code == 200
    assert react_res.json()["data"]["account_status"] == "ACTIVE"

    restored_login = client.post("/api/auth/login", json={"identifier": asha_staff_id, "password": "NewSecurePassword123!"})
    assert restored_login.status_code == 200

    # 11. Admin resets password
    reset_res = client.post(f"/api/admin/staff/{asha_staff_id}/reset-password", headers=admin_headers)
    assert reset_res.status_code == 200
    reset_creds = reset_res.json()["data"]
    assert reset_creds["temporary_password"]
    assert reset_creds["must_change_password"] is True

    # 12. Transfer staff assignment
    transfer_res = client.post(
        f"/api/admin/staff/{asha_staff_id}/transfer",
        json={"village_name": "Rampur", "coverage_area": "East Rampur Sector", "reason": "Relocation"},
        headers=admin_headers
    )
    assert transfer_res.status_code == 200
    assert transfer_res.json()["data"]["village_name"] == "Rampur"
