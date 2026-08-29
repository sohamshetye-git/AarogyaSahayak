import logging
from typing import Any, Dict, Optional
from app.models import HouseholdMember

logger = logging.getLogger(__name__)

def map_household_member_to_beneficiary_dict(
    member: Any,
    citizen_id: str,
    existing_case_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Canonical serializer for converting a HouseholdMember ORM instance or dictionary
    into a standardized BeneficiaryOption / BeneficiaryItemDTO payload.
    
    Guarantees:
    - Canonical API field: 'relationship' (and 'relationship_type' alias for backwards compat)
    - If relationship is missing/falsy, safely defaults to 'UNKNOWN' and logs a structured warning.
    - Resolves both ORM objects (with relationship_type / relationship property) and raw dictionaries.
    """
    if member is None:
        return {}

    # Extract member ID
    member_id = getattr(member, "id", None) or (member.get("id") if isinstance(member, dict) else None) or ""
    
    # Extract member full name / display name
    full_name = getattr(member, "full_name", None) or (member.get("full_name") if isinstance(member, dict) else None)
    if not full_name:
        display_name = getattr(member, "display_name", None) or (member.get("display_name") if isinstance(member, dict) else None)
        full_name = display_name or "Unknown Member"

    # Extract relationship explicitly and map to canonical field
    raw_rel = (
        getattr(member, "relationship_type", None) or
        getattr(member, "relationship_to_head", None) or
        getattr(member, "relation", None) or
        getattr(member, "relation_type", None) or
        getattr(member, "relationship", None)
    )
    if isinstance(member, dict) and not raw_rel:
        raw_rel = (
            member.get("relationship_type") or
            member.get("relationship_to_head") or
            member.get("relation") or
            member.get("relation_type") or
            member.get("relationship")
        )

    if not raw_rel or str(raw_rel).strip() == "":
        logger.warning(
            "DATA QUALITY WARNING: HouseholdMember id=%s has missing/empty relationship. Defaulting to UNKNOWN.",
            member_id
        )
        canonical_rel = "UNKNOWN"
    else:
        canonical_rel = str(raw_rel).strip().upper()

    # Extract demographic details
    age = getattr(member, "age", None) or (member.get("age") if isinstance(member, dict) else None)
    sex = getattr(member, "sex", None) or getattr(member, "gender", None)
    if isinstance(member, dict) and not sex:
        sex = member.get("sex") or member.get("gender")

    is_active = getattr(member, "is_active", True)
    if isinstance(member, dict) and "is_active" in member:
        is_active = member["is_active"]

    return {
        "beneficiaryId": str(member_id),
        "citizenId": str(citizen_id),
        "householdMemberId": str(member_id) if canonical_rel != "SELF" else None,
        "profileId": str(citizen_id),
        "displayName": full_name,
        "relationship": canonical_rel,
        "relationship_type": canonical_rel,
        "age": age,
        "gender": sex,
        "sex": sex,
        "isRegisteredPatient": True,
        "existingCaseId": existing_case_id,
        "is_active": bool(is_active)
    }

def map_household_member_to_dto(member: Any) -> Dict[str, Any]:
    """
    Standard serializer for HouseholdMember detail responses (e.g., /household endpoints).
    Guarantees canonical 'relationship' and 'relationship_type' fields.
    """
    if member is None:
        return {}

    member_id = getattr(member, "id", None) or (member.get("id") if isinstance(member, dict) else None) or ""
    citizen_id = getattr(member, "citizen_id", None) or (member.get("citizen_id") if isinstance(member, dict) else None) or ""
    linked_profile_id = getattr(member, "linked_citizen_profile_id", None) or (member.get("linked_citizen_profile_id") if isinstance(member, dict) else None)
    full_name = getattr(member, "full_name", None) or (member.get("full_name") if isinstance(member, dict) else None) or "Unknown Member"

    raw_rel = (
        getattr(member, "relationship_type", None) or
        getattr(member, "relationship_to_head", None) or
        getattr(member, "relation", None) or
        getattr(member, "relation_type", None) or
        getattr(member, "relationship", None)
    )
    if isinstance(member, dict) and not raw_rel:
        raw_rel = (
            member.get("relationship_type") or
            member.get("relationship_to_head") or
            member.get("relation") or
            member.get("relation_type") or
            member.get("relationship")
        )

    if not raw_rel or str(raw_rel).strip() == "":
        logger.warning(
            "DATA QUALITY WARNING: HouseholdMember id=%s has missing/empty relationship. Defaulting to UNKNOWN.",
            member_id
        )
        canonical_rel = "UNKNOWN"
    else:
        canonical_rel = str(raw_rel).strip().upper()

    age = getattr(member, "age", None) or (member.get("age") if isinstance(member, dict) else None)
    sex = getattr(member, "sex", None) or (member.get("sex") if isinstance(member, dict) else None)
    phone = getattr(member, "phone", None) or (member.get("phone") if isinstance(member, dict) else None)
    abha_ref = getattr(member, "abha_reference", None) or (member.get("abha_reference") if isinstance(member, dict) else None)
    is_preg = getattr(member, "is_pregnant", False) or (member.get("is_pregnant") if isinstance(member, dict) else False)
    gest_weeks = getattr(member, "gestational_weeks", None) or (member.get("gestational_weeks") if isinstance(member, dict) else None)
    blood_grp = getattr(member, "blood_group", None) or (member.get("blood_group") if isinstance(member, dict) else None)
    chronic = getattr(member, "chronic_conditions", []) or (member.get("chronic_conditions") if isinstance(member, dict) else [])
    notes = getattr(member, "health_notes", None) or (member.get("health_notes") if isinstance(member, dict) else None)
    is_act = getattr(member, "is_active", True) if getattr(member, "is_active", None) is not None else True
    created_at = getattr(member, "created_at", None) or (member.get("created_at") if isinstance(member, dict) else None)

    return {
        "id": str(member_id),
        "citizen_id": str(citizen_id),
        "linked_citizen_profile_id": str(linked_profile_id) if linked_profile_id else None,
        "full_name": full_name,
        "relationship": canonical_rel,
        "relationship_type": canonical_rel,
        "age": age,
        "sex": sex,
        "gender": sex,
        "phone": phone,
        "abha_reference": abha_ref,
        "is_pregnant": bool(is_preg),
        "gestational_weeks": gest_weeks,
        "blood_group": blood_grp,
        "chronic_conditions": chronic or [],
        "health_notes": notes,
        "is_active": bool(is_act),
        "created_at": created_at.isoformat() if hasattr(created_at, "isoformat") else (str(created_at) if created_at else None)
    }
