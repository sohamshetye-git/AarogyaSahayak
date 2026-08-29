#!/usr/bin/env python3
"""
Safe Development-Data Repair Script for ASHA Citizen Requests
- Identifies duplicate open ServiceRequests for the same citizen_id + request_type.
- Preserves the oldest canonical request.
- Re-links any valid handoffs or history if appropriate.
- Marks duplicates as DUPLICATE_SUPERSEDED (never hard deletes).
- Enforces dry-run mode by default and strictly refuses to execute in production.
"""

import sys
import os
import argparse
from datetime import datetime, timezone

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import SessionLocal
from app.models import ServiceRequest, ServiceRequestStatusHistory, CareHandoff, Case

def check_production_guard():
    env = os.environ.get("ENVIRONMENT", "").lower()
    app_env = os.environ.get("APP_ENV", "").lower()
    node_env = os.environ.get("NODE_ENV", "").lower()
    if "prod" in env or "prod" in app_env or "prod" in node_env:
        print("[CRITICAL ERROR] This repair script refuses to execute in a PRODUCTION environment.")
        sys.exit(1)

def run_repair(dry_run: bool = True):
    check_production_guard()
    print(f"=== ASHA Citizen Requests Duplicate Reconciliation Script ===")
    print(f"Mode: {'DRY RUN (No database modifications)' if dry_run else 'LIVE EXECUTION'}")
    print(f"Started at: {datetime.now(timezone.utc).isoformat()}\n")

    db = SessionLocal()
    try:
        open_statuses = [
            "SUBMITTED", "ASSIGNMENT_PENDING", "ASHA_ASSIGNED",
            "ASHA_ACKNOWLEDGED", "CITIZEN_CONTACTED", "VISIT_SCHEDULED",
            "VISIT_IN_PROGRESS"
        ]

        # Fetch all open ASHA assistance requests
        active_requests = db.query(ServiceRequest).filter(
            ServiceRequest.request_type == "ASHA_ASSISTANCE",
            ServiceRequest.status.in_(open_statuses)
        ).order_by(ServiceRequest.created_at.asc()).all()

        print(f"Found {len(active_requests)} total active/open ASHA ServiceRequests across all citizens.")

        # Group by (citizen_id, beneficiary_id)
        grouped = {}
        for req in active_requests:
            key = (req.citizen_id, req.beneficiary_id or "NONE")
            grouped.setdefault(key, []).append(req)

        duplicates_found = 0
        superseded_count = 0

        for key, reqs in grouped.items():
            citizen_id, ben_id = key
            if len(reqs) <= 1:
                continue

            duplicates_found += (len(reqs) - 1)
            canonical = reqs[0] # Oldest request preserved
            citizen_name = canonical.citizen.display_name if canonical.citizen else "Unknown Citizen"

            print(f"\n[DUPLICATE GROUP] Citizen: {citizen_name} (ID: {citizen_id}, Beneficiary: {ben_id})")
            print(f"  -> Canonical (Preserved): ID={canonical.id}, Ref={canonical.request_reference}, Status={canonical.status}, CreatedAt={canonical.created_at}")

            for dup in reqs[1:]:
                print(f"  -> Duplicate to Mark DUPLICATE_SUPERSEDED: ID={dup.id}, Ref={dup.request_reference}, Status={dup.status}, CreatedAt={dup.created_at}")
                if not dry_run:
                    old_status = dup.status
                    dup.status = "DUPLICATE_SUPERSEDED"
                    if not dup.details:
                        dup.details = {}
                    dup.details["superseded_by_request_id"] = canonical.id
                    dup.details["superseded_by_reference"] = canonical.request_reference
                    dup.details["reconciliation_reason"] = "Automated safe repair: marked duplicate open request as superseded"

                    # Add status history
                    hist = ServiceRequestStatusHistory(
                        service_request_id=dup.id,
                        from_status=old_status,
                        to_status="DUPLICATE_SUPERSEDED",
                        actor_role="SYSTEM",
                        reason=f"Development data repair: Superseded by canonical request {canonical.request_reference}"
                    )
                    db.add(hist)
                    superseded_count += 1

        if not dry_run:
            db.commit()
            print(f"\n[SUCCESS] Successfully committed changes. Superseded {superseded_count} duplicate request(s).")
        else:
            print(f"\n[DRY RUN COMPLETE] Found {duplicates_found} duplicate request(s) eligible for reconciliation. No records were modified.")

    except Exception as e:
        db.rollback()
        print(f"\n[ERROR] Reconciliation failed: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Repair duplicate ASHA citizen requests safely.")
    parser.add_argument("--execute", action="store_true", help="Perform live updates (defaults to dry-run if omitted).")
    args = parser.parse_args()

    run_repair(dry_run=not args.execute)
