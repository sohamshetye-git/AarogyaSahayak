import pytest
from app.models import User, WorkerProfile, UserRoleEnum, Case, CitizenProfile, Referral, CaseStatusEnum, CasePriorityEnum
from app.auth.security import get_password_hash

def get_auth_token(client, identifier: str, password: str = "demo123") -> str:
    res = client.post("/api/auth/login", json={"identifier": identifier, "password": password})
    assert res.status_code == 200, f"Login failed for {identifier}: {res.text}"
    return res.json()["data"]["access_token"]

def test_new_asha_worker_identity_and_data_scoping(client, db_session):
    # 1. Admin login
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
        db_session.commit()

    admin_token = get_auth_token(client, "dho.admin", "demo123")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # 2. Create new ASHA Worker Aditi Mahesh Vishwakarma
    create_payload = {
        "name": "Aditi Mahesh Vishwakarma",
        "role": "ASHA_WORKER",
        "phone": "9823998877",
        "email": "aditi.vishwakarma@arogya.gov.in",
        "employee_id": "EMP-ASHA-ADITI-01",
        "preferred_language": "mr-IN",
        "district": "District 04",
        "village_name": "Shivaji Nagar",
        "coverage_area": "Sector 3"
    }
    create_res = client.post("/api/admin/staff", json=create_payload, headers=admin_headers)
    assert create_res.status_code == 201, f"Create ASHA failed: {create_res.text}"
    staff_data = create_res.json()["data"]
    staff_id = staff_data["staff_id"]
    temp_pwd = staff_data["temporary_password"]

    # 3. Login with temporary credentials
    login_res = client.post("/api/auth/login", json={"identifier": staff_id, "password": temp_pwd})
    assert login_res.status_code == 200
    user_payload = login_res.json()["data"]["user"]
    assert user_payload["name"] == "Aditi Mahesh Vishwakarma"
    assert user_payload["role"] == "ASHA_WORKER"
    assert user_payload["village_name"] == "Shivaji Nagar"
    assert user_payload["coverage_area"] == "Sector 3"
    assert user_payload["must_change_password"] is True
    assert "Sita Patel" not in user_payload["name"]

    token = login_res.json()["data"]["access_token"]
    auth_headers = {"Authorization": f"Bearer {token}"}

    # 4. Check /api/auth/me returns exact identity
    me_res = client.get("/api/auth/me", headers=auth_headers)
    assert me_res.status_code == 200
    me_data = me_res.json()["data"]
    assert me_data["name"] == "Aditi Mahesh Vishwakarma"
    assert me_data["village_name"] == "Shivaji Nagar"
    assert me_data["district_name"] == "District 04"

    # 5. Check ASHA Dashboard for Aditi
    dash_res = client.get("/api/asha/dashboard", headers=auth_headers)
    assert dash_res.status_code == 200
    dash_data = dash_res.json()["data"]
    assert dash_data["worker_name"] == "Aditi Mahesh Vishwakarma"
    assert dash_data["village"] == "Shivaji Nagar"
    assert dash_data["total_assigned"] == 0
    assert len(dash_data["recent_tasks"]) == 0
    assert "Sita Patel" not in dash_data["worker_name"]

    # 6. Check ASHA Village People list for Aditi
    people_res = client.get("/api/asha/people", headers=auth_headers)
    assert people_res.status_code == 200
    assert len(people_res.json()["data"]) == 0

    # 7. Check Investigation Tasks for Aditi
    inv_res = client.get("/api/asha/investigation-tasks", headers=auth_headers)
    assert inv_res.status_code == 200
    assert len(inv_res.json()["data"]) == 0

    # 8. Password Change flow
    change_res = client.post(
        "/api/auth/change-password",
        json={"old_password": temp_pwd, "new_password": "NewAditiPassword2026!"},
        headers=auth_headers
    )
    assert change_res.status_code == 200

    # Re-login with new password
    new_login_res = client.post("/api/auth/login", json={"identifier": staff_id, "password": "NewAditiPassword2026!"})
    assert new_login_res.status_code == 200
    assert new_login_res.json()["data"]["user"]["must_change_password"] is False


def test_new_phc_doctor_identity_and_data_scoping(client, db_session):
    # 1. Admin login
    admin_token = get_auth_token(client, "dho.admin", "demo123")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # 2. Create new PHC Doctor Dr. Ananya Kulkarni in a separate facility PHC-99
    create_doc_payload = {
        "name": "Dr. Ananya Kulkarni",
        "role": "PHC_DOCTOR",
        "phone": "9823887766",
        "email": "dr.ananya@phc.arogya.gov.in",
        "employee_id": "EMP-DOC-ANANYA-01",
        "medical_registration_number": "MMC-2026-99112",
        "specialization": "General Medicine",
        "preferred_language": "mr-IN",
        "district": "District 04",
        "facility_id": "PHC-99",
        "facility_name": "Chandrapur PHC"
    }
    doc_res = client.post("/api/admin/staff", json=create_doc_payload, headers=admin_headers)
    assert doc_res.status_code == 201
    doc_staff_data = doc_res.json()["data"]
    doc_staff_id = doc_staff_data["staff_id"]
    doc_temp_pwd = doc_staff_data["temporary_password"]

    # 3. Login as Dr. Ananya
    login_res = client.post("/api/auth/login", json={"identifier": doc_staff_id, "password": doc_temp_pwd})
    assert login_res.status_code == 200
    doc_user = login_res.json()["data"]["user"]
    assert doc_user["name"] == "Dr. Ananya Kulkarni"
    assert doc_user["role"] == "PHC_DOCTOR"
    assert doc_user["facility_id"] == "PHC-99"
    assert doc_user["facility_name"] == "Chandrapur PHC"
    assert "Dr. Abhinav Sharma" not in doc_user["name"]

    token = login_res.json()["data"]["access_token"]
    auth_headers = {"Authorization": f"Bearer {token}"}

    # 4. Check Doctor Dashboard for Dr. Ananya
    dash_res = client.get("/api/doctor/dashboard", headers=auth_headers)
    assert dash_res.status_code == 200
    dash_data = dash_res.json()["data"]
    assert dash_data["doctor_name"] == "Dr. Ananya Kulkarni"
    assert dash_data["facility_name"] == "Chandrapur PHC"
    assert len(dash_data["incoming_referrals"]) == 0
    assert "Dr. Abhinav Sharma" not in dash_data["doctor_name"]

    # 5. Check Recent Care Activity for Dr. Ananya
    act_res = client.get("/api/doctor/dashboard/recent-activity", headers=auth_headers)
    assert act_res.status_code == 200
    assert act_res.json()["data"]["total"] == 0
