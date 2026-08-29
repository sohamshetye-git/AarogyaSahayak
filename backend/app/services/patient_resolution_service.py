import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func

from app.models import (
    CitizenProfile, HouseholdMember, User, Case, utc_now
)
from app.safety.pii_masking import PIIMaskingService

logger = logging.getLogger("aarogya.patient_resolution")

class PatientResolutionService:
    """
    Carefully resolves whether a care recipient is:
    1. Logged-in citizen
    2. Existing household member
    3. Existing CitizenProfile in system (potential duplicate or match)
    4. Genuinely new person

    Provides masked preview, duplicate detection, and explicit confirmation controls.
    """

    @staticmethod
    def mask_name(name: Optional[str]) -> str:
        if not name:
            return ""
        parts = name.strip().split()
        masked_parts = []
        for p in parts:
            if len(p) <= 2:
                masked_parts.append(p[0] + "*")
            else:
                masked_parts.append(p[:2] + "*" * (len(p) - 2))
        return " ".join(masked_parts)

    @classmethod
    def resolve_candidate(
        cls,
        db: Session,
        logged_in_citizen_id: str,
        beneficiary_id: Optional[str] = None,
        candidate_name: Optional[str] = None,
        phone: Optional[str] = None,
        abha_reference: Optional[str] = None,
        age: Optional[int] = None,
        gender: Optional[str] = None,
        village_name: Optional[str] = None,
        confirm_register_new_duplicate: bool = False
    ) -> Dict[str, Any]:
        
        logged_in_profile = db.query(CitizenProfile).filter(CitizenProfile.id == logged_in_citizen_id).first()
        if not logged_in_profile:
            raise ValueError("Logged in citizen profile not found")

        # 1. Explicit self selection or empty candidate
        is_explicit_self = beneficiary_id in ["self", logged_in_profile.id]
        is_candidate_self = (
            beneficiary_id is None
            and not candidate_name
            and (not phone or phone == logged_in_profile.phone)
            and (not abha_reference or abha_reference == logged_in_profile.abha_reference)
        ) or (
            candidate_name
            and candidate_name.strip().lower() == logged_in_profile.display_name.strip().lower()
            and (not phone or phone == logged_in_profile.phone)
        )

        if is_explicit_self or is_candidate_self:
            return {
                "resolution_type": "PRIMARY_CITIZEN",
                "citizen_id": logged_in_profile.id,
                "resolved_citizen_id": logged_in_profile.id,
                "resolved_household_member_id": None,
                "display_name": logged_in_profile.display_name,
                "is_registered": True,
                "requires_duplicate_confirmation": False,
                "potential_matches": []
            }

        # 2. Check if beneficiary_id matches an existing HouseholdMember
        hm = db.query(HouseholdMember).filter(
            HouseholdMember.id == beneficiary_id,
            HouseholdMember.citizen_id == logged_in_citizen_id
        ).first()

        if hm:
            return {
                "resolution_type": "HOUSEHOLD_MEMBER",
                "resolved_citizen_id": logged_in_citizen_id,
                "resolved_household_member_id": hm.id,
                "display_name": hm.full_name,
                "relationship_type": hm.relationship_type,
                "is_registered": True,
                "requires_duplicate_confirmation": False,
                "potential_matches": []
            }

        # 3. Duplicate Search across CitizenProfile table
        potential_matches: List[Dict[str, Any]] = []

        # (a) Search by ABHA
        if abha_reference and abha_reference.strip():
            clean_abha = abha_reference.strip()
            abha_match = db.query(CitizenProfile).filter(CitizenProfile.abha_reference == clean_abha).first()
            if abha_match and abha_match.id != logged_in_citizen_id:
                potential_matches.append({
                    "citizen_id": abha_match.id,
                    "masked_name": cls.mask_name(abha_match.display_name),
                    "masked_phone": PIIMaskingService.mask_phone(abha_match.phone) if abha_match.phone else None,
                    "masked_abha": PIIMaskingService.mask_abha(abha_match.abha_reference) if abha_match.abha_reference else None,
                    "village_name": abha_match.village_name or "Kalyanpur",
                    "age_estimate": abha_match.age_estimate,
                    "active_cases_count": len(abha_match.cases),
                    "similarity_reason": "Exact ABHA Identifier Match",
                    "assigned_asha_id": abha_match.assigned_asha_id
                })

        # (b) Search by Phone
        if phone and phone.strip() and len(phone.strip()) >= 10:
            clean_phone = phone.strip()
            phone_matches = db.query(CitizenProfile).filter(
                CitizenProfile.phone == clean_phone
            ).all()
            for pm in phone_matches:
                # If candidate name is different from the profile name or is a candidate member, it's a potential match
                if candidate_name and pm.display_name.strip().lower() != candidate_name.strip().lower():
                    if not any(m["citizen_id"] == pm.id for m in potential_matches):
                        potential_matches.append({
                            "citizen_id": pm.id,
                            "masked_name": cls.mask_name(pm.display_name),
                            "masked_phone": PIIMaskingService.mask_phone(pm.phone),
                            "masked_abha": PIIMaskingService.mask_abha(pm.abha_reference) if pm.abha_reference else None,
                            "village_name": pm.village_name or "Kalyanpur",
                            "age_estimate": pm.age_estimate,
                            "active_cases_count": len(pm.cases),
                            "similarity_reason": "Exact Phone Number Match",
                            "assigned_asha_id": pm.assigned_asha_id
                        })

        # (c) Search by Name + Village / Demographic Fuzzy Match
        if candidate_name and candidate_name.strip():
            c_name = candidate_name.strip().lower()
            name_matches = db.query(CitizenProfile).filter(
                func.lower(CitizenProfile.display_name).like(f"%{c_name}%"),
                CitizenProfile.id != logged_in_citizen_id
            ).all()
            for nm in name_matches:
                if not any(m["citizen_id"] == nm.id for m in potential_matches):
                    match_reason = "Name and Demographic Match"
                    if village_name and nm.village_name and village_name.lower() in nm.village_name.lower():
                        match_reason = f"Name & Village ({village_name}) Match"
                    potential_matches.append({
                        "citizen_id": nm.id,
                        "masked_name": cls.mask_name(nm.display_name),
                        "masked_phone": PIIMaskingService.mask_phone(nm.phone) if nm.phone else None,
                        "masked_abha": PIIMaskingService.mask_abha(nm.abha_reference) if nm.abha_reference else None,
                        "village_name": nm.village_name or "Kalyanpur",
                        "age_estimate": nm.age_estimate,
                        "active_cases_count": len(nm.cases),
                        "similarity_reason": match_reason,
                        "assigned_asha_id": nm.assigned_asha_id
                    })

        # (d) Also search household members under current citizen for similar name
        if candidate_name and candidate_name.strip():
            c_name = candidate_name.strip().lower()
            hm_matches = db.query(HouseholdMember).filter(
                HouseholdMember.citizen_id == logged_in_citizen_id,
                func.lower(HouseholdMember.full_name).like(f"%{c_name}%")
            ).all()
            for hmm in hm_matches:
                if not any(m.get("household_member_id") == hmm.id for m in potential_matches):
                    potential_matches.append({
                        "household_member_id": hmm.id,
                        "citizen_id": logged_in_citizen_id,
                        "masked_name": cls.mask_name(hmm.full_name),
                        "relationship_type": hmm.relationship_type,
                        "age_estimate": hmm.age,
                        "similarity_reason": f"Existing Household Member ({hmm.relationship_type})",
                        "is_household_member": True
                    })

        if potential_matches and not confirm_register_new_duplicate:
            return {
                "resolution_type": "POTENTIAL_DUPLICATE",
                "requires_duplicate_confirmation": True,
                "message": "This person may already be registered in the system.",
                "potential_matches": potential_matches,
                "actions": ["USE_EXISTING_PATIENT", "REVIEW_MATCH", "REGISTER_NEW_PERSON"]
            }

        # 4. Genuinely New Person / Confirmed Register New
        return {
            "resolution_type": "NEW_PERSON",
            "resolved_citizen_id": logged_in_citizen_id,
            "resolved_household_member_id": None,
            "display_name": candidate_name or "New Household Member",
            "is_registered": False,
            "requires_duplicate_confirmation": False,
            "potential_matches": potential_matches if confirm_register_new_duplicate else []
        }
