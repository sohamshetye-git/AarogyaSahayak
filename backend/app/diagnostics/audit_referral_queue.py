"""
Diagnostic script for auditing Referral Queue data integrity, database configuration,
facility mappings, status enums, and API outputs.
"""

import os, sys, json
from sqlalchemy import text
from app.config import settings
from app.database import SessionLocal, engine
from app.models import User, Referral, Case, Facility, WorkerProfile, UserRoleEnum

def audit():
    print("=======================================================")
    print("  AAROGYA SAHAYAK - REFERRAL QUEUE DIAGNOSTIC AUDIT")
    print("=======================================================\n")

    # 1. Environment & Database Configuration
    app_env = getattr(settings, "APP_ENV", os.getenv("APP_ENV", "development"))
    db_url = getattr(settings, "DATABASE_URL", os.getenv("DATABASE_URL", "not_set"))
    masked_db_url = db_url
    if "@" in db_url:
        prefix, rest = db_url.split("@", 1)
        masked_db_url = prefix.split(":")[0] + ":****@" + rest
    print(f"1. APP_ENV: {app_env}")
    print(f"   DATABASE_URL: {masked_db_url}")

    db = SessionLocal()
    try:
        # Check Alembic version if available
        try:
            res = db.execute(text("SELECT version_num FROM alembic_version")).fetchone()
            print(f"   Alembic Version: {res[0] if res else 'None'}")
        except Exception as e:
            print(f"   Alembic Table Warning: {e}")

        # 2. Doctor Information
        print("\n2. DOCTOR ACCOUNTS AUDIT:")
        doctors = db.query(User).filter(User.role == UserRoleEnum.PHC_DOCTOR).all()
        for doc in doctors:
            wp = db.query(WorkerProfile).filter(WorkerProfile.user_id == doc.id).first()
            fac_id = wp.facility_id if wp else "NO_WORKER_PROFILE"
            print(f"   - Doctor ID: {doc.id} | Name: {doc.name} | Role: {doc.role} | Facility ID: {fac_id}")

        # 3. Facility Table Audit
        print("\n3. FACILITIES IN DB:")
        facs = db.query(Facility).all()
        for f in facs:
            print(f"   - Facility ID: {f.id} | Name: {f.name} | Type: {getattr(f, 'facility_type', 'N/A')}")

        # 4. Total Referral Rows
        total_refs = db.query(Referral).count()
        print(f"\n4. TOTAL REFERRALS IN DB: {total_refs}")

        # 5. Referrals Grouped by Status
        print("\n5. REFERRALS GROUPED BY STATUS:")
        res_status = db.execute(text("SELECT status, count(*) FROM referrals GROUP BY status")).fetchall()
        for s, count in res_status:
            print(f"   - Status: '{s}': {count}")

        # 6. Referrals Grouped by Facility Column
        print("\n6. REFERRALS GROUPED BY FACILITY Foreign Keys:")
        # Check schema columns on referrals table
        cols = db.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='referrals'")).fetchall()
        col_names = [c[0] for c in cols]
        print(f"   - Referrals columns: {col_names}")

        fac_col = "to_facility_id" if "to_facility_id" in col_names else ("target_facility_id" if "target_facility_id" in col_names else "facility_id")
        res_fac = db.execute(text(f"SELECT {fac_col}, count(*) FROM referrals GROUP BY {fac_col}")).fetchall()
        for fid, count in res_fac:
            print(f"   - Facility Column ({fac_col}) = '{fid}': {count}")

        # 7. Cases Grouped by Status
        print("\n7. CASES GROUPED BY STATUS:")
        res_cases = db.execute(text("SELECT status, count(*) FROM cases GROUP BY status")).fetchall()
        for s, count in res_cases:
            print(f"   - Case Status: '{s}': {count}")

        # 8. Consultations Grouped by Status
        print("\n8. CONSULTATIONS GROUPED BY STATUS:")
        try:
            res_cons = db.execute(text("SELECT status, count(*) FROM consultations GROUP BY status")).fetchall()
            for s, count in res_cons:
                print(f"   - Consultation Status: '{s}': {count}")
        except Exception as e:
            print(f"   - Consultations Table Audit Error: {e}")

        # 9. Detailed Referrals Inspection & Relationship Integrity
        print("\n9. DETAILED REFERRAL RECORDS INSPECTION:")
        all_refs = db.query(Referral).all()
        broken_relationships = 0
        for r in all_refs:
            case = r.case
            citizen = case.citizen if case else None
            citizen_name = getattr(citizen, "display_name", getattr(citizen, "full_name", getattr(citizen, "name", "NO_CITIZEN"))) if citizen else "NO_CITIZEN"
            if not case or not citizen:
                broken_relationships += 1
            to_fac = getattr(r, "to_facility_id", getattr(r, "target_facility_id", getattr(r, "facility_id", "N/A")))
            print(f"   - [Ref ID: {r.id}] Ref#: {r.reference} | Case ID: {r.case_id} | Status: '{r.status}' | Urgency: '{r.urgency}' | To Fac ID: '{to_fac}' | Citizen: {citizen_name}")

        print(f"\nRelationship Audit: Total Broken Foreign Key Chains = {broken_relationships}")
    finally:
        db.close()

if __name__ == "__main__":
    audit()
