from typing import Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from app.models import (
    User, CitizenProfile, CitizenAuthIdentity, ServiceRequest, HouseholdMember
)
from app.services.citizen_auth_service import mask_phone_number

class IdentityDiagnosticService:
    """
    Diagnostic service for reporting citizen identity and relational integrity.
    Reports:
    - Duplicate normalized phone identities
    - Users with multiple primary citizen profiles
    - Orphaned CitizenProfiles
    - Service requests linked to mismatched or non-existent citizens
    - Broken household authorization relationships
    
    STRICT PRIVACY: Never outputs full phone numbers, passwords, transcripts or unnecessary PII.
    """

    @staticmethod
    def run_full_diagnostic(db: Session) -> Dict[str, Any]:
        report = {
            "duplicate_phone_identities": IdentityDiagnosticService.find_duplicate_phone_identities(db),
            "users_with_multiple_profiles": IdentityDiagnosticService.find_users_with_multiple_profiles(db),
            "orphaned_profiles": IdentityDiagnosticService.find_orphaned_profiles(db),
            "mismatched_service_requests": IdentityDiagnosticService.find_mismatched_service_requests(db),
            "broken_household_relationships": IdentityDiagnosticService.find_broken_household_relationships(db),
            "summary": {}
        }

        total_issues = (
            len(report["duplicate_phone_identities"]) +
            len(report["users_with_multiple_profiles"]) +
            len(report["orphaned_profiles"]) +
            len(report["mismatched_service_requests"]) +
            len(report["broken_household_relationships"])
        )

        report["summary"] = {
            "status": "HEALTHY" if total_issues == 0 else "ATTENTION_REQUIRED",
            "total_issues_found": total_issues,
            "duplicate_identities_count": len(report["duplicate_phone_identities"]),
            "multiple_profiles_count": len(report["users_with_multiple_profiles"]),
            "orphaned_profiles_count": len(report["orphaned_profiles"]),
            "mismatched_requests_count": len(report["mismatched_service_requests"]),
            "broken_household_links_count": len(report["broken_household_relationships"])
        }

        return report

    @staticmethod
    def find_duplicate_phone_identities(db: Session) -> List[Dict[str, Any]]:
        """
        Finds phone hashes or normalized phone identities mapped to multiple records.
        """
        duplicates = db.query(
            CitizenAuthIdentity.phone_normalized,
            func.count(CitizenAuthIdentity.id).label("count")
        ).group_by(CitizenAuthIdentity.phone_normalized).having(func.count(CitizenAuthIdentity.id) > 1).all()

        results = []
        for d in duplicates:
            phone_masked = mask_phone_number(d.phone_normalized) if d.phone_normalized else "***"
            records = db.query(CitizenAuthIdentity).filter(
                CitizenAuthIdentity.phone_normalized == d.phone_normalized
            ).all()
            results.append({
                "phone_masked": phone_masked,
                "record_count": d.count,
                "identity_ids": [r.id for r in records],
                "user_ids": [r.user_id for r in records]
            })
        return results

    @staticmethod
    def find_users_with_multiple_profiles(db: Session) -> List[Dict[str, Any]]:
        """
        Finds users linked to more than one primary CitizenProfile.
        """
        duplicates = db.query(
            CitizenProfile.user_id,
            func.count(CitizenProfile.id).label("count")
        ).filter(CitizenProfile.user_id.isnot(None))\
         .group_by(CitizenProfile.user_id)\
         .having(func.count(CitizenProfile.id) > 1).all()

        results = []
        for d in duplicates:
            profiles = db.query(CitizenProfile).filter(CitizenProfile.user_id == d.user_id).all()
            results.append({
                "user_id": d.user_id,
                "profile_count": d.count,
                "profile_ids": [p.id for p in profiles]
            })
        return results

    @staticmethod
    def find_orphaned_profiles(db: Session) -> List[Dict[str, Any]]:
        """
        Finds citizen profiles whose user_id is not null but points to a non-existent user.
        """
        user_ids = [u[0] for u in db.query(User.id).all()]
        orphaned = db.query(CitizenProfile).filter(
            CitizenProfile.user_id.isnot(None),
            CitizenProfile.user_id.notin_(user_ids)
        ).all()

        return [
            {
                "profile_id": p.id,
                "invalid_user_id": p.user_id,
                "village_name": p.village_name
            }
            for p in orphaned
        ]

    @staticmethod
    def find_mismatched_service_requests(db: Session) -> List[Dict[str, Any]]:
        """
        Finds ServiceRequests pointing to non-existent CitizenProfile.
        """
        profile_ids = [p[0] for p in db.query(CitizenProfile.id).all()]
        invalid_requests = db.query(ServiceRequest).filter(
            ServiceRequest.citizen_id.isnot(None),
            ServiceRequest.citizen_id.notin_(profile_ids)
        ).all()

        return [
            {
                "service_request_id": r.id,
                "invalid_citizen_id": r.citizen_id,
                "request_type": r.request_type,
                "status": r.status
            }
            for r in invalid_requests
        ]

    @staticmethod
    def find_broken_household_relationships(db: Session) -> List[Dict[str, Any]]:
        """
        Finds:
        1. HouseholdMembers with missing or empty relationship_type
        2. HouseholdMembers with citizen_id pointing to non-existent CitizenProfile (orphans)
        3. Duplicate household relationships within the same household
        """
        profile_ids = [p[0] for p in db.query(CitizenProfile.id).all()]
        all_members = db.query(HouseholdMember).all()
        issues = []

        seen_pairs = set()

        for m in all_members:
            # Check 1: Orphaned household member
            if m.citizen_id not in profile_ids:
                issues.append({
                    "household_member_id": m.id,
                    "issue_type": "ORPHANED_HOUSEHOLD_MEMBER",
                    "invalid_citizen_id": m.citizen_id,
                    "relationship": getattr(m, "relationship_type", None) or "UNKNOWN"
                })

            # Check 2: Missing relationship value
            rel = getattr(m, "relationship_type", None) or getattr(m, "relationship", None)
            if not rel or str(rel).strip() == "":
                issues.append({
                    "household_member_id": m.id,
                    "issue_type": "MISSING_RELATIONSHIP_VALUE",
                    "citizen_id": m.citizen_id,
                    "full_name": m.full_name
                })

            # Check 3: Duplicate relationship in same household (excluding non-unique relations like CHILD/ELDER)
            norm_rel = str(rel).upper().strip() if rel else "UNKNOWN"
            if norm_rel in ("SELF", "SPOUSE", "FATHER", "MOTHER"):
                pair_key = (m.citizen_id, norm_rel)
                if pair_key in seen_pairs:
                    issues.append({
                        "household_member_id": m.id,
                        "issue_type": "DUPLICATE_HOUSEHOLD_RELATIONSHIP",
                        "citizen_id": m.citizen_id,
                        "relationship": norm_rel
                    })
                else:
                    seen_pairs.add(pair_key)

        return issues


