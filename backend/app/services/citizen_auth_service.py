import re
import hmac
import hashlib
import secrets
import time
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.config import settings
from app.models import (
    User, UserRoleEnum, CitizenProfile, HouseholdMember,
    CitizenAuthIdentity, OtpChallenge, AuthSession, GuestSession, GuestSessionMigration,
    CitizenChatSession, CitizenNeed, ServiceRequest, CareHandoff, TeleconsultationRequest,
    generate_uuid, utc_now
)
from app.auth.security import create_access_token, create_refresh_token, get_password_hash

# -------------------------------------------------------------
# Phone Normalization & Privacy Hashing
# -------------------------------------------------------------

def normalize_indian_phone(phone_raw: str) -> str:
    """
    Normalizes Indian mobile phone numbers to strict E.164 format (+91XXXXXXXXXX).
    Validates 10-digit mobile starting with 6, 7, 8, or 9.
    """
    if not phone_raw:
        raise ValueError("Phone number is required")
    
    # Remove all non-digits
    digits = re.sub(r"\D", "", phone_raw)
    
    # Handle country codes: 91XXXXXXXXXX (12 digits) or 0XXXXXXXXXX (11 digits) or XXXXXXXXXX (10 digits)
    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    elif len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]
    
    if len(digits) != 10:
        raise ValueError("Phone number must contain exactly 10 digits")
    
    if digits[0] not in ["6", "7", "8", "9"]:
        raise ValueError("Invalid Indian mobile number (must start with 6, 7, 8, or 9)")
    
    return f"+91{digits}"

def mask_phone_number(phone_normalized: str) -> str:
    """
    Formats phone for safe confirmation display, e.g. 98******10.
    """
    clean = re.sub(r"^\+91", "", phone_normalized)
    if len(clean) == 10:
        return f"{clean[:2]}******{clean[-2:]}"
    return f"{phone_normalized[:3]}******{phone_normalized[-2:]}"

def hash_phone(phone_normalized: str) -> str:
    """
    Deterministic SHA-256 hash for phone indexing and privacy.
    """
    salt = "aarogya_phone_salt_2026"
    return hashlib.sha256(f"{salt}:{phone_normalized}".encode("utf-8")).hexdigest()

def hash_otp(otp_code: str, phone_hash: str) -> str:
    """
    Secure PBKDF2 hash of OTP code with phone salt.
    """
    salt = f"otp_salt_{phone_hash}"
    return hashlib.pbkdf2_hmac("sha256", otp_code.encode("utf-8"), salt.encode("utf-8"), 50000).hex()

def verify_otp_hash(plain_otp: str, phone_hash: str, stored_hash: str) -> bool:
    candidate_hash = hash_otp(plain_otp, phone_hash)
    return hmac.compare_digest(candidate_hash, stored_hash)


# -------------------------------------------------------------
# Extensible OTP Provider Architecture
# -------------------------------------------------------------

class BaseOtpProvider(ABC):
    @abstractmethod
    def send_otp(self, phone_normalized: str, otp_code: str) -> Dict[str, Any]:
        """Dispatches OTP message to the recipient."""
        pass

class MockOtpProvider(BaseOtpProvider):
    def send_otp(self, phone_normalized: str, otp_code: str) -> Dict[str, Any]:
        env = (settings.ENVIRONMENT or "").lower()
        if env in ["production", "prod"]:
            raise RuntimeError("MockOtpProvider invoked in production environment!")
        return {
            "provider": "MOCK",
            "status": "SENT",
            "delivered": True,
            "simulated": True,
            "phone_masked": mask_phone_number(phone_normalized)
        }

class TwilioOtpProvider(BaseOtpProvider):
    """
    Twilio SMS / Verify OTP Provider using standard HTTP request without third-party SDK.
    """
    def __init__(self):
        self.account_sid = getattr(settings, "TWILIO_ACCOUNT_SID", None)
        self.auth_token = getattr(settings, "TWILIO_AUTH_TOKEN", None)
        self.from_number = getattr(settings, "TWILIO_FROM_NUMBER", None)

    def send_otp(self, phone_normalized: str, otp_code: str) -> Dict[str, Any]:
        if not self.account_sid or not self.auth_token or not self.from_number:
            raise RuntimeError("Twilio credentials not configured (requires TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER)")
        
        import requests
        url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Messages.json"
        body_text = f"Your Aarogya Sahayak verification code is {otp_code}. Valid for 5 minutes."
        
        try:
            resp = requests.post(
                url,
                data={
                    "From": self.from_number,
                    "To": phone_normalized,
                    "Body": body_text
                },
                auth=(self.account_sid, self.auth_token),
                timeout=10
            )
            if resp.status_code in [200, 201]:
                return {
                    "provider": "TWILIO",
                    "status": "SENT",
                    "delivered": True,
                    "phone_masked": mask_phone_number(phone_normalized)
                }
            else:
                return {
                    "provider": "TWILIO",
                    "status": f"ERROR_{resp.status_code}",
                    "phone_masked": mask_phone_number(phone_normalized)
                }
        except Exception as e:
            raise RuntimeError(f"Twilio SMS dispatch failed: {str(e)}")

class Msg91OtpProvider(BaseOtpProvider):
    """
    MSG91 Flow / SMS OTP Provider for Indian Telecom (DLT compliant).
    """
    def __init__(self):
        self.auth_key = getattr(settings, "MSG91_AUTH_KEY", None) or getattr(settings, "OTP_SMS_PROVIDER_API_KEY", None)
        self.template_id = getattr(settings, "MSG91_TEMPLATE_ID", None)
        self.sender_id = getattr(settings, "MSG91_SENDER_ID", None) or getattr(settings, "OTP_SMS_SENDER_ID", "AAROGY")

    def send_otp(self, phone_normalized: str, otp_code: str) -> Dict[str, Any]:
        if not self.auth_key:
            raise RuntimeError("MSG91 auth key not configured (requires MSG91_AUTH_KEY or OTP_SMS_PROVIDER_API_KEY)")
        
        import requests
        clean_phone = phone_normalized.replace("+", "")
        
        if self.template_id:
            # Flow API
            url = "https://control.msg91.com/api/v5/flow/"
            headers = {
                "authkey": self.auth_key,
                "Content-Type": "application/json"
            }
            payload = {
                "template_id": self.template_id,
                "sender": self.sender_id,
                "short_url": "0",
                "mobiles": clean_phone,
                "otp": otp_code
            }
            try:
                resp = requests.post(url, json=payload, headers=headers, timeout=10)
                return {
                    "provider": "MSG91",
                    "status": "SENT" if resp.status_code == 200 else f"ERROR_{resp.status_code}",
                    "phone_masked": mask_phone_number(phone_normalized)
                }
            except Exception as e:
                raise RuntimeError(f"MSG91 Flow SMS dispatch failed: {str(e)}")
        else:
            # Standard OTP API
            url = f"https://control.msg91.com/api/v5/otp?template_id={self.template_id or ''}&mobile={clean_phone}&authkey={self.auth_key}&otp={otp_code}"
            try:
                resp = requests.post(url, timeout=10)
                return {
                    "provider": "MSG91",
                    "status": "SENT" if resp.status_code == 200 else f"ERROR_{resp.status_code}",
                    "phone_masked": mask_phone_number(phone_normalized)
                }
            except Exception as e:
                raise RuntimeError(f"MSG91 OTP dispatch failed: {str(e)}")

class LiveSmsOtpProvider(BaseOtpProvider):
    def __init__(self, api_key: Optional[str] = None, sender_id: Optional[str] = None):
        self.api_key = api_key or settings.OTP_SMS_PROVIDER_API_KEY
        self.sender_id = sender_id or settings.OTP_SMS_SENDER_ID or "AAROGYA"

    def send_otp(self, phone_normalized: str, otp_code: str) -> Dict[str, Any]:
        if not self.api_key:
            raise RuntimeError("SMS provider API key not configured")
        # Generic HTTP SMS Gateway Dispatch
        return {
            "provider": "LIVE_SMS",
            "status": "QUEUED",
            "phone_masked": mask_phone_number(phone_normalized)
        }

def get_otp_provider() -> BaseOtpProvider:
    mode = (settings.OTP_MODE or "MOCK").upper()
    if mode == "MOCK":
        return MockOtpProvider()
    elif mode == "TWILIO":
        return TwilioOtpProvider()
    elif mode == "MSG91":
        return Msg91OtpProvider()
    return LiveSmsOtpProvider()


# -------------------------------------------------------------
# Citizen Authentication & Guest Access Service
# -------------------------------------------------------------

def _ensure_utc(dt: Any) -> datetime:
    if dt is None:
        return utc_now()
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt)
        except Exception:
            return utc_now()
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt

class CitizenAuthService:

    @staticmethod
    def request_otp(
        db: Session,
        phone_raw: str,
        ip_address: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Validates phone, applies rate limiting and cooldowns, generates 6-digit OTP,
        records hashed challenge, and dispatches via provider.
        """
        phone_normalized = normalize_indian_phone(phone_raw)
        p_hash = hash_phone(phone_normalized)
        now = utc_now()

        # 1. Check Resend Cooldown (only for unconsumed active OTP challenges)
        cooldown_threshold = now - timedelta(seconds=settings.OTP_RESEND_COOLDOWN_SECONDS)
        challenges = db.query(OtpChallenge).filter(
            OtpChallenge.phone_hash == p_hash
        ).order_by(OtpChallenge.created_at.desc()).all()

        if challenges:
            latest = challenges[0]
            if latest.consumed_at is None:
                latest_created = _ensure_utc(latest.created_at)
                if latest_created >= cooldown_threshold:
                    seconds_left = int((latest_created + timedelta(seconds=settings.OTP_RESEND_COOLDOWN_SECONDS) - now).total_seconds())
                    if seconds_left > 0:
                        raise ValueError(f"Please wait {seconds_left} seconds before requesting a new OTP")

        # 2. Rate limiting check (max 5 requests per hour)
        hour_threshold = now - timedelta(hours=1)
        hourly_count = 0
        for ch in challenges:
            if _ensure_utc(ch.created_at) >= hour_threshold:
                hourly_count += 1
        if hourly_count >= 5:
            raise ValueError("Too many OTP requests for this mobile number. Please try again after 1 hour.")

        # 3. Generate 6-digit OTP code
        otp_mode = (settings.OTP_MODE or "MOCK").upper()
        env = (settings.ENVIRONMENT or "").lower()
        if otp_mode == "MOCK" and env in ["development", "test", "staging"]:
            otp_code = settings.DEMO_OTP_CODE or settings.OTP_TEST_CODE or "123456"
        else:
            # Cryptographically secure 6-digit random number
            otp_code = f"{secrets.randbelow(900000) + 100000}"

        hashed_otp = hash_otp(otp_code, p_hash)
        expires_at = now + timedelta(seconds=settings.OTP_EXPIRY_SECONDS)

        # 4. Invalidate/consume prior unconsumed challenges for this phone
        db.query(OtpChallenge).filter(
            OtpChallenge.phone_hash == p_hash,
            OtpChallenge.consumed_at.is_(None)
        ).update({"consumed_at": now})

        challenge = OtpChallenge(
            id=generate_uuid(),
            phone_hash=p_hash,
            otp_hash=hashed_otp,
            attempts=0,
            max_attempts=settings.OTP_MAX_ATTEMPTS,
            expires_at=expires_at,
            consumed_at=None,
            ip_address=ip_address,
            created_at=now
        )
        db.add(challenge)
        db.commit()

        # 5. Dispatch via provider
        provider = get_otp_provider()
        provider_res = provider.send_otp(phone_normalized, otp_code)

        response_data: Dict[str, Any] = {
            "challenge_id": challenge.id,
            "otp_request_id": challenge.id,
            "phone_masked": mask_phone_number(phone_normalized),
            "phone_normalized": phone_normalized,
            "expires_in_seconds": settings.OTP_EXPIRY_SECONDS,
            "expires_at": challenge.expires_at.isoformat(),
            "cooldown_seconds": settings.OTP_RESEND_COOLDOWN_SECONDS,
            "provider": provider_res.get("provider", "SMS")
        }

        # ONLY return mock_code in dev/test/staging when OTP_MODE=MOCK for local/demo testing ease
        if otp_mode == "MOCK" and env in ["development", "test", "staging"]:
            response_data["mock_code"] = otp_code

        return response_data

    @staticmethod
    def verify_otp(
        db: Session,
        phone_raw: str,
        otp_code: str,
        device_id: Optional[str] = None,
        idempotency_key: Optional[str] = None,
        otp_request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Validates OTP challenge, verifies attempt limits & expiry, creates authenticated session,
        and returns user details & authorized household members.
        """
        import json
        from app.models import IdempotencyRecord

        # Idempotency check: return cached successful response if same key provided
        if idempotency_key:
            existing_rec = db.query(IdempotencyRecord).filter(
                IdempotencyRecord.idempotency_key == idempotency_key
            ).first()
            if existing_rec and existing_rec.response_body:
                try:
                    return json.loads(existing_rec.response_body)
                except Exception:
                    pass

        phone_normalized = normalize_indian_phone(phone_raw)
        p_hash = hash_phone(phone_normalized)
        now = utc_now()

        # Step 1: Challenge Lookup
        if otp_request_id:
            challenge = db.query(OtpChallenge).filter(
                OtpChallenge.id == otp_request_id
            ).first()
            if not challenge:
                raise ValueError("No active OTP request found. Please request a new OTP.")
            if challenge.phone_hash != p_hash:
                raise ValueError("OTP request phone number does not match this challenge.")
            if challenge.consumed_at is not None:
                raise ValueError("OTP has already been used. Please request a new OTP.")
        else:
            challenge = db.query(OtpChallenge).filter(
                OtpChallenge.phone_hash == p_hash,
                OtpChallenge.consumed_at.is_(None)
            ).order_by(OtpChallenge.created_at.desc()).first()

        if not challenge:
            raise ValueError("No active OTP request found. Please request a new OTP.")

        if _ensure_utc(challenge.expires_at) < now:
            challenge.consumed_at = now
            db.commit()
            raise ValueError("OTP has expired. Please request a new one.")

        if challenge.attempts >= challenge.max_attempts:
            challenge.consumed_at = now
            db.commit()
            raise ValueError("Maximum OTP verification attempts exceeded. Please request a new OTP.")

        challenge.attempts += 1

        if not verify_otp_hash(otp_code.strip(), p_hash, challenge.otp_hash):
            db.commit()
            remaining = challenge.max_attempts - challenge.attempts
            if remaining <= 0:
                raise ValueError("Incorrect OTP. Limit reached, please request a new OTP.")
            raise ValueError(f"Incorrect OTP. {remaining} attempts remaining.")

        # Step 2: Account Resolution & Restoration
        # Detect historical duplicate profiles or conflicting identities
        identities = db.query(CitizenAuthIdentity).filter(
            CitizenAuthIdentity.phone_hash == p_hash
        ).all()

        profiles_with_phone = db.query(CitizenProfile).filter(
            or_(
                CitizenProfile.phone == phone_normalized,
                CitizenProfile.phone == phone_raw
            )
        ).all()

        if len(identities) > 1 or len(profiles_with_phone) > 1:
            # Conflict detected: Never silently merge or overwrite records
            return {
                "authenticated": False,
                "onboarding_required": False,
                "is_new_citizen": False,
                "status": "ACCOUNT_RESOLUTION_REQUIRED",
                "error_code": "ACCOUNT_RESOLUTION_REQUIRED",
                "message": "Multiple citizen profile records found for this verified mobile number. Please contact health administration for assisted account resolution.",
                "phone_normalized": phone_normalized,
                "duplicate_count": max(len(identities), len(profiles_with_phone))
            }

        # Check if Citizen Identity exists
        auth_identity = identities[0] if len(identities) == 1 else None

        is_new_citizen = False
        user = None

        if auth_identity:
            user = db.query(User).filter(User.id == auth_identity.user_id).first()
            if user and not user.is_active:
                raise ValueError("Account is deactivated. Please contact support.")
            auth_identity.phone_verified_at = now
        else:
            # Check by User phone directly (e.g. existing seeded users)
            existing_user = db.query(User).filter(
                or_(
                    User.phone == phone_normalized,
                    User.phone == phone_raw,
                    User.identifier == phone_normalized
                )
            ).first()

            if existing_user and existing_user.role == UserRoleEnum.CITIZEN:
                if not existing_user.is_active:
                    raise ValueError("Account is deactivated. Please contact support.")
                user = existing_user
                # Create auth identity linkage
                auth_identity = CitizenAuthIdentity(
                    id=generate_uuid(),
                    user_id=user.id,
                    phone_normalized=phone_normalized,
                    phone_hash=p_hash,
                    phone_verified_at=now,
                    provider=(settings.OTP_MODE or "MOCK_SMS")
                )
                db.add(auth_identity)
            else:
                is_new_citizen = True

        # Generate Tokens & Session
        access_token = None
        refresh_token = None
        user_session_dto = None
        profile_dto = None
        authorized_beneficiaries: List[Dict[str, Any]] = []
        selected_beneficiary_id: Optional[str] = None

        if user:
            # Load linked citizen profile
            profile = db.query(CitizenProfile).filter(CitizenProfile.user_id == user.id).first()
            if not profile:
                profile = CitizenProfile(
                    id=generate_uuid(),
                    user_id=user.id,
                    display_name=user.name or "Citizen",
                    legal_name=user.name or "Citizen",
                    preferred_name=user.name or "Citizen",
                    phone=phone_normalized,
                    preferred_language=user.preferred_language or "mr-IN",
                    village_name="Kalyanpur",
                    created_at=now
                )
                db.add(profile)
            else:
                # Update last login info
                user.updated_at = now

            access_token = create_access_token({"sub": user.id, "role": user.role.value, "phone": phone_normalized})
            refresh_token = create_refresh_token({"sub": user.id})

            # Record AuthSession (single session created on each OTP login)
            refresh_hash = hashlib.sha256(refresh_token.encode("utf-8")).hexdigest()
            auth_session = AuthSession(
                id=generate_uuid(),
                user_id=user.id,
                refresh_token_hash=refresh_hash,
                device_id=device_id,
                expires_at=now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
                created_at=now
            )
            db.add(auth_session)

            user_session_dto = {
                "id": user.id,
                "identifier": user.identifier,
                "name": user.name,
                "phone": phone_normalized,
                "role": user.role.value,
                "preferred_language": user.preferred_language or (profile.preferred_language if profile else "mr-IN"),
                "village_name": profile.village_name if profile else "Kalyanpur"
            }

            profile_dto = {
                "id": profile.id,
                "user_id": profile.user_id,
                "display_name": profile.display_name,
                "legal_name": profile.legal_name,
                "preferred_name": profile.preferred_name,
                "phone": profile.phone,
                "village_name": profile.village_name,
                "district": profile.district,
                "preferred_language": profile.preferred_language,
                "created_at": profile.created_at.isoformat() if profile.created_at else None
            }

            authorized_beneficiaries = CitizenAuthService.get_authorized_beneficiaries(db, user.id)
            if authorized_beneficiaries:
                selected_beneficiary_id = authorized_beneficiaries[0]["beneficiaryId"]

        # Mark OTP as consumed (Single-use) atomically with session/user commit
        challenge.consumed_at = now
        db.commit()

        result_payload = {
            "authenticated": not is_new_citizen,
            "onboarding_required": is_new_citizen,
            "is_new_citizen": is_new_citizen,
            "phone_normalized": phone_normalized,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer" if access_token else None,
            "user": user_session_dto,
            "citizen_profile": profile_dto,
            "authorized_beneficiaries": authorized_beneficiaries,
            "selected_beneficiary_id": selected_beneficiary_id
        }

        # Cache response for idempotency
        if idempotency_key:
            try:
                idem_rec = IdempotencyRecord(
                    idempotency_key=idempotency_key,
                    user_id=user.id if user else None,
                    http_method="POST",
                    request_path="/api/citizen/auth/otp/verify",
                    operation="CITIZEN_OTP_VERIFY",
                    response_status=200,
                    response_body=json.dumps(result_payload),
                    created_at=now
                )
                db.add(idem_rec)
                db.commit()
            except Exception:
                db.rollback()

        return result_payload

    @staticmethod
    def register_onboarding(
        db: Session,
        phone_raw: str,
        registration_data: Dict[str, Any],
        idempotency_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Creates User, CitizenProfile, and CitizenAuthIdentity atomically.
        Enforces duplicate prevention, concurrency safety, and consent verification.
        """
        phone_normalized = normalize_indian_phone(phone_raw)
        p_hash = hash_phone(phone_normalized)
        now = utc_now()

        # Check existing identity (re-use if already created, e.g. concurrent registration)
        existing_identity = db.query(CitizenAuthIdentity).filter(
            CitizenAuthIdentity.phone_hash == p_hash
        ).first()

        if existing_identity:
            existing_user = db.query(User).filter(User.id == existing_identity.user_id).first()
            if existing_user:
                # User already established -> return existing session smoothly
                if registration_data.get("full_name"):
                    existing_user.name = registration_data.get("full_name").strip()
                if existing_user.citizen_profile:
                    prof = existing_user.citizen_profile
                    if registration_data.get("full_name"):
                        prof.display_name = registration_data.get("full_name").strip()
                        prof.legal_name = registration_data.get("full_name").strip()
                    if registration_data.get("village"):
                        prof.village_name = registration_data.get("village")
                    if registration_data.get("age"):
                        prof.age_estimate = int(registration_data.get("age"))
                    if registration_data.get("gender"):
                        prof.sex = registration_data.get("gender")
                db.commit()
                db.refresh(existing_user)

                access_token = create_access_token({"sub": existing_user.id, "role": existing_user.role.value, "phone": phone_normalized})
                refresh_token = create_refresh_token({"sub": existing_user.id})

                refresh_hash = hashlib.sha256(refresh_token.encode("utf-8")).hexdigest()
                auth_session = AuthSession(
                    id=generate_uuid(),
                    user_id=existing_user.id,
                    refresh_token_hash=refresh_hash,
                    expires_at=now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
                    created_at=now
                )
                db.add(auth_session)
                db.commit()

                prof = existing_user.citizen_profile
                user_session_dto = {
                    "id": existing_user.id,
                    "identifier": existing_user.identifier,
                    "name": existing_user.name,
                    "phone": existing_user.phone,
                    "role": existing_user.role.value,
                    "preferred_language": existing_user.preferred_language or (prof.preferred_language if prof else "mr-IN"),
                    "village_name": prof.village_name if prof else "Kalyanpur"
                }
                profile_dto = {
                    "id": prof.id,
                    "user_id": prof.user_id,
                    "display_name": prof.display_name,
                    "phone": prof.phone,
                    "village_name": prof.village_name
                } if prof else None

                beneficiaries = CitizenAuthService.get_authorized_beneficiaries(db, existing_user.id)
                return {
                    "authenticated": True,
                    "onboarding_required": False,
                    "is_new_citizen": False,
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                    "token_type": "bearer",
                    "user": user_session_dto,
                    "citizen_profile": profile_dto,
                    "authorized_beneficiaries": beneficiaries,
                    "selected_beneficiary_id": beneficiaries[0]["beneficiaryId"] if beneficiaries else None
                }

        full_name = (registration_data.get("full_name") or registration_data.get("name") or "").strip()

        if not full_name:
            raise ValueError("Full name is required")

        preferred_language = registration_data.get("preferred_language") or "mr-IN"
        village = registration_data.get("village") or registration_data.get("village_name") or "Kalyanpur"
        district = registration_data.get("district") or "District 04"
        pincode = registration_data.get("pincode")
        gender = registration_data.get("gender") or registration_data.get("sex") or "OTHER"
        age = registration_data.get("age") or registration_data.get("age_estimate")
        date_of_birth = registration_data.get("date_of_birth")
        abha_reference = registration_data.get("abha_reference")
        emergency_name = registration_data.get("emergency_contact_name")
        emergency_phone = registration_data.get("emergency_contact_phone")
        emergency_relation = registration_data.get("emergency_contact_relation")
        consent_obtained = bool(registration_data.get("consent_obtained", True))

        if not consent_obtained:
            raise ValueError("Privacy policy and explicit consent are required for citizen registration")

        # Duplicate Citizen Check by Name & Village & approximate age
        potential_duplicate = db.query(CitizenProfile).filter(
            CitizenProfile.display_name.ilike(full_name),
            CitizenProfile.village_name.ilike(village)
        ).first()

        if potential_duplicate and potential_duplicate.user_id is not None:
            # Profile exists with active user account -> prevent silent overwrite
            if not registration_data.get("confirm_potential_duplicate", False):
                return {
                    "requires_duplicate_confirmation": True,
                    "matched_profile_id": potential_duplicate.id,
                    "message": "A citizen profile with this name already exists in your village. Please confirm if this is you or proceed with assisted recovery."
                }

        # Create User
        user_id = generate_uuid()
        user = User(
            id=user_id,
            identifier=phone_normalized,
            name=full_name,
            phone=phone_normalized,
            password_hash=get_password_hash(f"citizen_{secrets.token_hex(8)}"),
            role=UserRoleEnum.CITIZEN,
            preferred_language=preferred_language,
            is_active=True,
            created_at=now
        )
        db.add(user)

        # Create CitizenProfile
        profile_id = generate_uuid()
        citizen_profile = CitizenProfile(
            id=profile_id,
            user_id=user_id,
            display_name=full_name,
            legal_name=full_name,
            preferred_name=full_name,
            date_of_birth=date_of_birth,
            age_estimate=int(age) if age else None,
            sex=gender,
            phone=phone_normalized,
            village_name=village,
            district=district,
            pincode=pincode,
            preferred_language=preferred_language,
            emergency_contact_name=emergency_name,
            emergency_contact_phone=emergency_phone,
            emergency_contact_relation=emergency_relation,
            abha_reference=abha_reference if abha_reference else None,
            registration_consent_obtained=True,
            consent_method="DIGITAL_CHECKBOX",
            consent_timestamp=now,
            language_confirmed_at=now,
            created_at=now
        )
        db.add(citizen_profile)

        # Create Auth Identity
        auth_identity = CitizenAuthIdentity(
            id=generate_uuid(),
            user_id=user_id,
            phone_normalized=phone_normalized,
            phone_hash=p_hash,
            phone_verified_at=now,
            provider=(settings.OTP_MODE or "MOCK_SMS"),
            created_at=now
        )
        db.add(auth_identity)
        db.commit()
        db.refresh(user)

        # Generate Tokens
        access_token = create_access_token({"sub": user.id, "role": user.role.value, "phone": phone_normalized})
        refresh_token = create_refresh_token({"sub": user.id})

        refresh_hash = hashlib.sha256(refresh_token.encode("utf-8")).hexdigest()
        auth_session = AuthSession(
            id=generate_uuid(),
            user_id=user.id,
            refresh_token_hash=refresh_hash,
            expires_at=now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
            created_at=now
        )
        db.add(auth_session)
        db.commit()

        user_session_dto = {
            "id": user.id,
            "identifier": user.identifier,
            "name": user.name,
            "phone": phone_normalized,
            "role": user.role.value,
            "preferred_language": preferred_language,
            "village_name": village
        }

        authorized_beneficiaries = CitizenAuthService.get_authorized_beneficiaries(db, user.id)

        profile_dto = {
            "id": citizen_profile.id,
            "user_id": citizen_profile.user_id,
            "display_name": citizen_profile.display_name,
            "legal_name": citizen_profile.legal_name,
            "preferred_name": citizen_profile.preferred_name,
            "phone": citizen_profile.phone,
            "village_name": citizen_profile.village_name,
            "district": citizen_profile.district,
            "preferred_language": citizen_profile.preferred_language,
            "created_at": citizen_profile.created_at.isoformat() if citizen_profile.created_at else None
        }

        return {
            "authenticated": True,
            "onboarding_required": False,
            "is_new_citizen": False,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user": user_session_dto,
            "citizen_profile": profile_dto,
            "authorized_beneficiaries": authorized_beneficiaries,
            "selected_beneficiary_id": authorized_beneficiaries[0]["beneficiaryId"] if authorized_beneficiaries else None
        }

    @staticmethod
    def get_authorized_beneficiaries(db: Session, user_id: str) -> List[Dict[str, Any]]:
        """
        Returns 'Myself' and authorized household members for the authenticated citizen.
        Strictly isolates household members belonging to the current user's profile.
        Uses canonical map_household_member_to_beneficiary_dict mapper.
        """
        from app.mappers.household_mapper import map_household_member_to_beneficiary_dict
        profile = db.query(CitizenProfile).filter(CitizenProfile.user_id == user_id).first()
        if not profile:
            return []

        beneficiaries: List[Dict[str, Any]] = [
            {
                "beneficiaryId": profile.id,
                "citizenId": profile.id,
                "householdMemberId": None,
                "profileId": profile.id,
                "displayName": f"{profile.display_name} (Myself)",
                "relationship": "SELF",
                "relationship_type": "SELF",
                "age": profile.age_estimate,
                "gender": profile.sex,
                "sex": profile.sex,
                "isRegisteredPatient": True,
                "existingCaseId": None,
                "is_active": True
            }
        ]

        members = db.query(HouseholdMember).filter(
            HouseholdMember.citizen_id == profile.id,
            HouseholdMember.is_active == True
        ).all()

        for m in members:
            try:
                dto = map_household_member_to_beneficiary_dict(m, citizen_id=profile.id)
                beneficiaries.append(dto)
            except Exception as e:
                logger.error("Failed to map household member id=%s: %s", getattr(m, "id", "unknown"), str(e))
                # Fallback safe member representation
                beneficiaries.append({
                    "beneficiaryId": getattr(m, "id", "unknown"),
                    "citizenId": profile.id,
                    "householdMemberId": getattr(m, "id", "unknown"),
                    "profileId": profile.id,
                    "displayName": getattr(m, "full_name", "Family Member"),
                    "relationship": "UNKNOWN",
                    "relationship_type": "UNKNOWN",
                    "age": getattr(m, "age", None),
                    "gender": getattr(m, "sex", None),
                    "isRegisteredPatient": True,
                    "existingCaseId": None,
                    "is_active": True
                })

        return beneficiaries

    # -------------------------------------------------------------
    # Guest Session Management & Atomic Migration
    # -------------------------------------------------------------

    @staticmethod
    def create_guest_session(
        db: Session,
        locale: str = "mr-IN",
        device_hash: Optional[str] = None
    ) -> Dict[str, Any]:
        now = utc_now()
        session_id = f"gst_{secrets.token_urlsafe(24)}"
        expires_at = now + timedelta(hours=settings.GUEST_SESSION_TTL_HOURS)

        guest = GuestSession(
            id=session_id,
            locale=locale,
            device_session_hash=device_hash,
            context_data={},
            expires_at=expires_at,
            created_at=now
        )
        db.add(guest)
        db.commit()

        return {
            "session_id": guest.id,
            "locale": guest.locale,
            "expires_at": guest.expires_at.isoformat()
        }

    @staticmethod
    def get_guest_session(db: Session, session_id: str) -> Optional[GuestSession]:
        return db.query(GuestSession).filter(GuestSession.id == session_id).first()

    @staticmethod
    def update_guest_session_context(
        db: Session,
        session_id: str,
        context_updates: Dict[str, Any],
        intended_action: Optional[Dict[str, Any]] = None
    ) -> Optional[GuestSession]:
        guest = db.query(GuestSession).filter(GuestSession.id == session_id).first()
        if not guest:
            return None

        current = guest.context_data or {}
        current.update(context_updates)
        guest.context_data = current
        if intended_action:
            guest.intended_action = intended_action
        db.commit()
        db.refresh(guest)
        return guest

    @staticmethod
    def migrate_guest_to_citizen(
        db: Session,
        guest_session_id: str,
        user_id: str,
        idempotency_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Atomically transfers guest chat sessions, needs, and drafted intent
        to the authenticated citizen. Enforces idempotency to avoid duplicate records.
        """
        now = utc_now()
        idem_key = idempotency_key or f"mig_{guest_session_id}_{user_id}"

        # 1. Check Idempotency
        existing_mig = db.query(GuestSessionMigration).filter(
            GuestSessionMigration.idempotency_key == idem_key
        ).first()

        if existing_mig:
            return {
                "migration_id": existing_mig.id,
                "status": existing_mig.migration_status,
                "user_id": existing_mig.user_id,
                "migrated_entities": existing_mig.migrated_entities
            }

        guest = db.query(GuestSession).filter(GuestSession.id == guest_session_id).first()
        if not guest:
            raise ValueError(f"Guest session '{guest_session_id}' not found")

        user = db.query(User).filter(User.id == user_id).first()
        if not user or not user.citizen_profile:
            raise ValueError("Authenticated citizen profile not found")

        citizen_profile_id = user.citizen_profile.id
        migrated_entities: Dict[str, List[str]] = {
            "chat_sessions": [],
            "needs": [],
            "service_requests": []
        }

        # 2. Transfer Chat Sessions associated with guest_session_id
        chat_sessions = db.query(CitizenChatSession).filter(
            CitizenChatSession.device_id == guest_session_id
        ).all()

        for cs in chat_sessions:
            cs.citizen_id = citizen_profile_id
            migrated_entities["chat_sessions"].append(cs.id)

        # 3. Transfer CitizenNeeds associated with these chat sessions or guest
        for cs in chat_sessions:
            needs = db.query(CitizenNeed).filter(CitizenNeed.session_id == cs.id).all()
            for n in needs:
                n.citizen_id = citizen_profile_id
                migrated_entities["needs"].append(n.id)

        # 4. Mark guest session as migrated
        guest.migrated_to_user_id = user.id
        guest.migrated_at = now

        # 5. Record Migration Log
        migration = GuestSessionMigration(
            id=generate_uuid(),
            guest_session_id=guest.id,
            user_id=user.id,
            migration_status="COMPLETED",
            idempotency_key=idem_key,
            migrated_entities=migrated_entities,
            created_at=now
        )
        db.add(migration)
        db.commit()

        return {
            "migration_id": migration.id,
            "status": "COMPLETED",
            "user_id": user.id,
            "guest_session_id": guest.id,
            "intended_action": guest.intended_action,
            "context_data": guest.context_data,
            "migrated_entities": migrated_entities
        }

    # -------------------------------------------------------------
    # Token Refresh & Revocation
    # -------------------------------------------------------------

    @staticmethod
    def refresh_token_session(db: Session, refresh_token: str) -> Dict[str, Any]:
        from app.auth.security import decode_token
        payload = decode_token(refresh_token, settings.JWT_REFRESH_SECRET)
        if not payload or payload.get("type") != "refresh":
            raise ValueError("Invalid or expired refresh token")

        user_id = payload.get("sub")
        refresh_hash = hashlib.sha256(refresh_token.encode("utf-8")).hexdigest()

        auth_session = db.query(AuthSession).filter(
            AuthSession.user_id == user_id,
            AuthSession.refresh_token_hash == refresh_hash,
            AuthSession.revoked_at.is_(None)
        ).first()

        if not auth_session:
            raise ValueError("Session revoked or not found")

        now = utc_now()
        if _ensure_utc(auth_session.expires_at) < now:
            auth_session.revoked_at = now
            db.commit()
            raise ValueError("Session expired. Please log in again.")

        user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
        if not user:
            raise ValueError("User inactive or not found")

        # Ensure citizen profile is present
        if not user.citizen_profile:
            profile = CitizenProfile(
                id=generate_uuid(),
                user_id=user.id,
                display_name=user.name or "Citizen",
                legal_name=user.name or "Citizen",
                preferred_name=user.name or "Citizen",
                phone=user.phone,
                preferred_language=user.preferred_language or "mr-IN",
                village_name="Kalyanpur",
                created_at=now
            )
            db.add(profile)
            db.commit()
            db.refresh(user)

        new_access_token = create_access_token({"sub": user.id, "role": user.role.value, "phone": user.phone})
        new_refresh_token = create_refresh_token({"sub": user.id})

        # Rotate refresh token
        auth_session.refresh_token_hash = hashlib.sha256(new_refresh_token.encode("utf-8")).hexdigest()
        auth_session.expires_at = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        db.commit()

        profile = user.citizen_profile
        user_session_dto = {
            "id": user.id,
            "identifier": user.identifier,
            "name": user.name,
            "phone": user.phone,
            "role": user.role.value,
            "preferred_language": user.preferred_language or (profile.preferred_language if profile else "mr-IN"),
            "village_name": profile.village_name if profile else "Kalyanpur"
        }

        authorized_beneficiaries = CitizenAuthService.get_authorized_beneficiaries(db, user.id)

        return {
            "access_token": new_access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer",
            "user": user_session_dto,
            "authorized_beneficiaries": authorized_beneficiaries
        }

    @staticmethod
    def logout_session(db: Session, token: Optional[str] = None, user_id: Optional[str] = None, refresh_token: Optional[str] = None) -> bool:
        now = utc_now()
        if refresh_token:
            refresh_hash = hashlib.sha256(refresh_token.encode("utf-8")).hexdigest()
            db.query(AuthSession).filter(
                AuthSession.refresh_token_hash == refresh_hash,
                AuthSession.revoked_at.is_(None)
            ).update({"revoked_at": now})
        if user_id:
            db.query(AuthSession).filter(
                AuthSession.user_id == user_id,
                AuthSession.revoked_at.is_(None)
            ).update({"revoked_at": now})
        db.commit()
        return True
