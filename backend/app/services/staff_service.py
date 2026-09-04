import secrets
import string
import uuid
import re
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func
from fastapi import HTTPException, status

from app.models import (
    User, WorkerProfile, UserRoleEnum, AuditLog, Facility, utc_now
)
from app.schemas import (
    StaffCreateRequest, StaffUpdateRequest, StaffTransferRequest,
    StaffSuspendRequest, StaffMemberDTO, StaffSummaryCountsDTO,
    StaffListResponseData, StaffCredentialsResponse
)
from app.auth.security import get_password_hash, verify_password
from app.safety.pii_masking import PIIMaskingService

class StaffManagementService:

    @staticmethod
    def generate_temporary_password(length: int = 12) -> str:
        """
        Generates a cryptographically secure temporary password.
        Must contain uppercase, lowercase, digits, and special chars.
        """
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        while True:
            pwd = ''.join(secrets.choice(alphabet) for _ in range(length))
            if (any(c.islower() for c in pwd)
                    and any(c.isupper() for c in pwd)
                    and any(c.isdigit() for c in pwd)
                    and any(c in "!@#$%^&*" for c in pwd)):
                return pwd

    @staticmethod
    def generate_collision_safe_staff_id(db: Session, role: UserRoleEnum, facility_code_or_dist: Optional[str] = None) -> str:
        """
        Generates a collision-safe Staff ID such as:
        ASHA-KAL-0042 or DOC-PHC09-0015
        Uses sequence detection + uniqueness check with retry.
        """
        prefix = "ASHA" if role == UserRoleEnum.ASHA_WORKER else "DOC"
        loc_tag = "KAL"
        if facility_code_or_dist:
            clean = re.sub(r'[^A-Z0-9]', '', facility_code_or_dist.upper())
            if clean:
                loc_tag = clean[:5]
        
        # Base count from DB for sequencing
        base_count = db.query(User).filter(User.role == role).count() + 1
        for attempt in range(100):
            seq_num = base_count + attempt
            candidate_id = f"{prefix}-{loc_tag}-{seq_num:04d}"
            # Verify uniqueness in both User.staff_id and User.identifier
            exists = db.query(User).filter(
                (User.staff_id == candidate_id) | (User.identifier == candidate_id)
            ).first()
            if not exists:
                return candidate_id
        
        # Random suffix fallback if high collisions
        rand_suffix = secrets.token_hex(2).upper()
        return f"{prefix}-{loc_tag}-{rand_suffix}"

    @classmethod
    def get_admin_district_scope(cls, admin_user: User) -> Tuple[Optional[str], Optional[str]]:
        """
        Retrieves the district_id and district_name authorized for this admin.
        System Admins can see all.
        """
        if admin_user.role == UserRoleEnum.SYSTEM_ADMIN:
            return None, None
        
        district_id = None
        district_name = None
        if admin_user.worker_profile:
            district_id = admin_user.worker_profile.district_id
            district_name = admin_user.worker_profile.district_name
        return district_id, district_name

    @classmethod
    def list_staff(
        cls,
        db: Session,
        admin_user: User,
        search: Optional[str] = None,
        role: Optional[str] = None,
        status_filter: Optional[str] = None,
        facility_id: Optional[str] = None,
        page: int = 1,
        limit: int = 20
    ) -> StaffListResponseData:
        admin_dist_id, admin_dist_name = cls.get_admin_district_scope(admin_user)
        
        # Base query for staff roles only
        query = db.query(User).join(WorkerProfile, User.id == WorkerProfile.user_id).filter(
            User.role.in_([UserRoleEnum.ASHA_WORKER, UserRoleEnum.PHC_DOCTOR])
        )

        # District Scope Filter
        if admin_dist_name:
            query = query.filter(
                or_(
                    WorkerProfile.district_name == admin_dist_name,
                    WorkerProfile.district_id == admin_dist_id
                )
            )

        # Calculate Summary Counts before narrowing search/filters
        all_district_staff = query.all()
        total_count = len(all_district_staff)
        active_count = sum(1 for u in all_district_staff if (u.account_status or "ACTIVE") == "ACTIVE" and u.is_active)
        suspended_count = sum(1 for u in all_district_staff if (u.account_status == "SUSPENDED" or not u.is_active))
        asha_count = sum(1 for u in all_district_staff if u.role == UserRoleEnum.ASHA_WORKER)
        doctor_count = sum(1 for u in all_district_staff if u.role == UserRoleEnum.PHC_DOCTOR)

        summary = StaffSummaryCountsDTO(
            total=total_count,
            active=active_count,
            suspended=suspended_count,
            asha_workers=asha_count,
            phc_doctors=doctor_count
        )

        # Apply search query
        if search:
            s = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    User.name.ilike(s),
                    User.staff_id.ilike(s),
                    User.identifier.ilike(s),
                    User.phone.ilike(s),
                    WorkerProfile.employee_id.ilike(s),
                    WorkerProfile.professional_registration.ilike(s)
                )
            )

        # Role filter
        if role and role.upper() in ["ASHA_WORKER", "PHC_DOCTOR"]:
            query = query.filter(User.role == UserRoleEnum(role.upper()))

        # Status filter
        if status_filter:
            st = status_filter.upper()
            if st == "ACTIVE":
                query = query.filter(or_(User.account_status == "ACTIVE", User.account_status.is_(None)), User.is_active == True)
            elif st == "SUSPENDED":
                query = query.filter(or_(User.account_status == "SUSPENDED", User.is_active == False))

        # Facility filter
        if facility_id:
            query = query.filter(WorkerProfile.facility_id == facility_id)

        filtered_total = query.count()
        offset = (page - 1) * limit
        users = query.order_by(User.created_at.desc()).offset(offset).limit(limit).all()

        staff_dtos = []
        for u in users:
            wp = u.worker_profile
            phone_masked = PIIMaskingService.mask_phone(u.phone) if u.phone else None
            staff_dtos.append(
                StaffMemberDTO(
                    id=u.id,
                    staff_id=u.staff_id or u.identifier,
                    identifier=u.identifier,
                    name=u.name,
                    role=u.role.value if hasattr(u.role, "value") else str(u.role),
                    phone=u.phone,
                    phone_masked=phone_masked,
                    email=u.email,
                    employee_id=wp.employee_id if wp else None,
                    assigned_facility_id=wp.facility_id if wp else None,
                    assigned_facility_name=wp.facility_name if wp else None,
                    district_id=wp.district_id if wp else admin_dist_id,
                    district_name=wp.district_name if wp else (admin_dist_name or "District 04"),
                    village_ids=wp.village_ids if wp else None,
                    village_name=wp.village_name if wp else None,
                    coverage_area=wp.coverage_area if wp else None,
                    medical_registration_number=wp.professional_registration if wp else None,
                    specialization=wp.specialization if wp else None,
                    preferred_language=u.preferred_language or "mr-IN",
                    account_status=u.account_status or ("ACTIVE" if u.is_active else "SUSPENDED"),
                    must_change_password=bool(u.must_change_password),
                    last_login_at=u.last_login_at,
                    created_at=u.created_at,
                    updated_at=u.updated_at
                )
            )

        return StaffListResponseData(
            summary=summary,
            staff=staff_dtos,
            total=filtered_total,
            page=page,
            limit=limit
        )

    @classmethod
    def get_staff_detail(cls, db: Session, admin_user: User, staff_id_or_user_id: str) -> StaffMemberDTO:
        admin_dist_id, admin_dist_name = cls.get_admin_district_scope(admin_user)
        
        user = db.query(User).filter(
            or_(
                User.id == staff_id_or_user_id,
                User.staff_id == staff_id_or_user_id,
                User.identifier == staff_id_or_user_id
            )
        ).first()

        if not user or user.role not in [UserRoleEnum.ASHA_WORKER, UserRoleEnum.PHC_DOCTOR]:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "STAFF_NOT_FOUND", "message": "Staff member not found"}
            )

        # District authorization check
        wp = user.worker_profile
        if admin_dist_name and wp and wp.district_name and wp.district_name != admin_dist_name:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "OUT_OF_DISTRICT", "message": "You cannot access staff from another district"}
            )

        phone_masked = PIIMaskingService.mask_phone(user.phone) if user.phone else None
        return StaffMemberDTO(
            id=user.id,
            staff_id=user.staff_id or user.identifier,
            identifier=user.identifier,
            name=user.name,
            role=user.role.value if hasattr(user.role, "value") else str(user.role),
            phone=user.phone,
            phone_masked=phone_masked,
            email=user.email,
            employee_id=wp.employee_id if wp else None,
            assigned_facility_id=wp.facility_id if wp else None,
            assigned_facility_name=wp.facility_name if wp else None,
            district_id=wp.district_id if wp else None,
            district_name=wp.district_name if wp else "District 04",
            village_ids=wp.village_ids if wp else None,
            village_name=wp.village_name if wp else None,
            coverage_area=wp.coverage_area if wp else None,
            medical_registration_number=wp.professional_registration if wp else None,
            specialization=wp.specialization if wp else None,
            preferred_language=user.preferred_language or "mr-IN",
            account_status=user.account_status or ("ACTIVE" if user.is_active else "SUSPENDED"),
            must_change_password=bool(user.must_change_password),
            last_login_at=user.last_login_at,
            created_at=user.created_at,
            updated_at=user.updated_at
        )

    @classmethod
    def create_staff(cls, db: Session, admin_user: User, req: StaffCreateRequest) -> StaffCredentialsResponse:
        role_str = req.role.upper()
        if role_str not in ["ASHA_WORKER", "PHC_DOCTOR"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "INVALID_ROLE", "message": "Only ASHA_WORKER or PHC_DOCTOR staff can be created"}
            )
        role_enum = UserRoleEnum(role_str)

        # Phone format validation (Indian 10-digit mobile)
        clean_phone = re.sub(r'[^0-9]', '', req.phone)
        if len(clean_phone) < 10 or len(clean_phone) > 13:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "INVALID_PHONE", "message": "Please enter a valid phone number"}
            )
        clean_phone_10 = clean_phone[-10:]

        # Validate duplicate employee_id
        if req.employee_id:
            emp_exists = db.query(WorkerProfile).filter(WorkerProfile.employee_id == req.employee_id.strip()).first()
            if emp_exists:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={"code": "DUPLICATE_EMPLOYEE_ID", "message": f"Employee ID '{req.employee_id}' is already assigned"}
                )

        # Validate duplicate medical registration number
        if req.medical_registration_number:
            reg_exists = db.query(WorkerProfile).filter(
                WorkerProfile.professional_registration == req.medical_registration_number.strip()
            ).first()
            if reg_exists:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={"code": "DUPLICATE_REGISTRATION_NUMBER", "message": f"Medical Registration '{req.medical_registration_number}' is already registered"}
                )

        # Resolve District & Facility
        admin_dist_id, admin_dist_name = cls.get_admin_district_scope(admin_user)
        target_district_name = req.district or admin_dist_name or "District 04"
        target_district_id = req.district_id or admin_dist_id or "dist-04"

        target_facility_id = req.assigned_facility_id or req.facility_id
        facility_name = req.facility_name
        facility_code = "FAC"
        if target_facility_id:
            fac = db.query(Facility).filter(
                or_(
                    Facility.id == target_facility_id,
                    Facility.code == target_facility_id,
                    Facility.public_reference == target_facility_id
                )
            ).first()
            if fac:
                facility_name = fac.official_name or fac.name
                facility_code = fac.code or "PHC"
                target_facility_id = fac.id
            elif not facility_name:
                facility_name = target_facility_id

        # Generate Collision-Safe Staff ID & Temporary Password
        generated_staff_id = cls.generate_collision_safe_staff_id(db, role_enum, facility_code)
        temp_password = cls.generate_temporary_password(12)
        pwd_hash = get_password_hash(temp_password)

        # Derive identifier (staff_id or clean username)
        user_id = str(uuid.uuid4())
        
        # ATOMIC TRANSACTION
        try:
            new_user = User(
                id=user_id,
                identifier=generated_staff_id,
                staff_id=generated_staff_id,
                name=req.name.strip(),
                phone=clean_phone_10,
                email=req.email.strip().lower() if req.email else None,
                password_hash=pwd_hash,
                role=role_enum,
                preferred_language=req.preferred_language or "mr-IN",
                is_active=True,
                account_status="ACTIVE",
                must_change_password=True,
                created_by_admin_id=admin_user.id
            )
            db.add(new_user)

            new_worker = WorkerProfile(
                user_id=user_id,
                worker_type="ASHA" if role_enum == UserRoleEnum.ASHA_WORKER else "DOCTOR",
                facility_id=target_facility_id,
                facility_name=facility_name,
                district_id=target_district_id,
                district_name=target_district_name,
                village_ids=req.village_ids or ([] if role_enum != UserRoleEnum.ASHA_WORKER else ([req.village_name] if req.village_name else [])),
                village_name=req.village_name,
                coverage_area=req.coverage_area,
                professional_registration=req.medical_registration_number.strip() if req.medical_registration_number else (f"ASHA-{secrets.token_hex(3).upper()}" if role_enum == UserRoleEnum.ASHA_WORKER else None),
                employee_id=req.employee_id.strip() if req.employee_id else None,
                specialization=req.specialization.strip() if req.specialization else None
            )
            db.add(new_worker)

            # Audit Log
            audit = AuditLog(
                actor_user_id=admin_user.id,
                actor_role=admin_user.role.value if hasattr(admin_user.role, "value") else str(admin_user.role),
                action="STAFF_CREATED",
                resource_type="User",
                resource_id=user_id,
                outcome="SUCCESS",
                metadata_json={
                    "staff_id": generated_staff_id,
                    "name": req.name,
                    "role": role_str,
                    "district": target_district_name,
                    "facility_id": req.assigned_facility_id,
                    "facility_name": facility_name
                }
            )
            db.add(audit)

            db.commit()
            db.refresh(new_user)

            return StaffCredentialsResponse(
                staff_id=generated_staff_id,
                identifier=generated_staff_id,
                name=new_user.name,
                role=role_str,
                temporary_password=temp_password,
                must_change_password=True,
                notice="Save these credentials now. The temporary password will not be shown again."
            )
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"code": "STAFF_CREATION_FAILED", "message": f"Could not create staff record: {str(e)}"}
            )

    @classmethod
    def update_staff(cls, db: Session, admin_user: User, staff_id_or_user_id: str, req: StaffUpdateRequest) -> StaffMemberDTO:
        admin_dist_id, admin_dist_name = cls.get_admin_district_scope(admin_user)
        user = db.query(User).filter(
            or_(
                User.id == staff_id_or_user_id,
                User.staff_id == staff_id_or_user_id,
                User.identifier == staff_id_or_user_id
            )
        ).first()

        if not user or user.role not in [UserRoleEnum.ASHA_WORKER, UserRoleEnum.PHC_DOCTOR]:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "STAFF_NOT_FOUND", "message": "Staff member not found"}
            )

        wp = user.worker_profile
        if admin_dist_name and wp and wp.district_name and wp.district_name != admin_dist_name:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "OUT_OF_DISTRICT", "message": "Cannot modify staff from another district"}
            )

        changes = {}
        if req.name and req.name.strip() != user.name:
            changes["name"] = {"old": user.name, "new": req.name.strip()}
            user.name = req.name.strip()

        if req.phone:
            clean_phone = re.sub(r'[^0-9]', '', req.phone)[-10:]
            if clean_phone != user.phone:
                changes["phone"] = {"old": user.phone, "new": clean_phone}
                user.phone = clean_phone

        if req.email is not None:
            new_email = req.email.strip().lower() if req.email else None
            if new_email != user.email:
                changes["email"] = {"old": user.email, "new": new_email}
                user.email = new_email

        if req.preferred_language and req.preferred_language != user.preferred_language:
            changes["preferred_language"] = {"old": user.preferred_language, "new": req.preferred_language}
            user.preferred_language = req.preferred_language

        if wp:
            if req.village_name is not None and req.village_name != wp.village_name:
                changes["village_name"] = {"old": wp.village_name, "new": req.village_name}
                wp.village_name = req.village_name

            if req.coverage_area is not None and req.coverage_area != wp.coverage_area:
                changes["coverage_area"] = {"old": wp.coverage_area, "new": req.coverage_area}
                wp.coverage_area = req.coverage_area

            if req.specialization is not None and req.specialization != wp.specialization:
                changes["specialization"] = {"old": wp.specialization, "new": req.specialization}
                wp.specialization = req.specialization

            if req.medical_registration_number is not None and req.medical_registration_number != wp.professional_registration:
                changes["medical_registration_number"] = {"old": wp.professional_registration, "new": req.medical_registration_number}
                wp.professional_registration = req.medical_registration_number

        user.updated_at = utc_now()

        # Audit
        audit = AuditLog(
            actor_user_id=admin_user.id,
            actor_role=admin_user.role.value if hasattr(admin_user.role, "value") else str(admin_user.role),
            action="STAFF_UPDATED",
            resource_type="User",
            resource_id=user.id,
            outcome="SUCCESS",
            metadata_json={
                "staff_id": user.staff_id or user.identifier,
                "changes": changes
            }
        )
        db.add(audit)
        db.commit()
        db.refresh(user)

        return cls.get_staff_detail(db, admin_user, user.id)

    @classmethod
    def suspend_staff(cls, db: Session, admin_user: User, staff_id_or_user_id: str, reason: Optional[str] = None) -> StaffMemberDTO:
        admin_dist_id, admin_dist_name = cls.get_admin_district_scope(admin_user)
        user = db.query(User).filter(
            or_(
                User.id == staff_id_or_user_id,
                User.staff_id == staff_id_or_user_id,
                User.identifier == staff_id_or_user_id
            )
        ).first()

        if not user or user.role not in [UserRoleEnum.ASHA_WORKER, UserRoleEnum.PHC_DOCTOR]:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "STAFF_NOT_FOUND", "message": "Staff member not found"}
            )

        wp = user.worker_profile
        if admin_dist_name and wp and wp.district_name and wp.district_name != admin_dist_name:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "OUT_OF_DISTRICT", "message": "Cannot suspend staff from another district"}
            )

        user.is_active = False
        user.account_status = "SUSPENDED"
        user.updated_at = utc_now()

        audit = AuditLog(
            actor_user_id=admin_user.id,
            actor_role=admin_user.role.value if hasattr(admin_user.role, "value") else str(admin_user.role),
            action="STAFF_SUSPENDED",
            resource_type="User",
            resource_id=user.id,
            outcome="SUCCESS",
            metadata_json={
                "staff_id": user.staff_id or user.identifier,
                "reason": reason or "Administrative suspension"
            }
        )
        db.add(audit)
        db.commit()
        db.refresh(user)

        return cls.get_staff_detail(db, admin_user, user.id)

    @classmethod
    def reactivate_staff(cls, db: Session, admin_user: User, staff_id_or_user_id: str) -> StaffMemberDTO:
        admin_dist_id, admin_dist_name = cls.get_admin_district_scope(admin_user)
        user = db.query(User).filter(
            or_(
                User.id == staff_id_or_user_id,
                User.staff_id == staff_id_or_user_id,
                User.identifier == staff_id_or_user_id
            )
        ).first()

        if not user or user.role not in [UserRoleEnum.ASHA_WORKER, UserRoleEnum.PHC_DOCTOR]:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "STAFF_NOT_FOUND", "message": "Staff member not found"}
            )

        wp = user.worker_profile
        if admin_dist_name and wp and wp.district_name and wp.district_name != admin_dist_name:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "OUT_OF_DISTRICT", "message": "Cannot reactivate staff from another district"}
            )

        user.is_active = True
        user.account_status = "ACTIVE"
        user.updated_at = utc_now()

        audit = AuditLog(
            actor_user_id=admin_user.id,
            actor_role=admin_user.role.value if hasattr(admin_user.role, "value") else str(admin_user.role),
            action="STAFF_REACTIVATED",
            resource_type="User",
            resource_id=user.id,
            outcome="SUCCESS",
            metadata_json={
                "staff_id": user.staff_id or user.identifier
            }
        )
        db.add(audit)
        db.commit()
        db.refresh(user)

        return cls.get_staff_detail(db, admin_user, user.id)

    @classmethod
    def transfer_staff(cls, db: Session, admin_user: User, staff_id_or_user_id: str, req: StaffTransferRequest) -> StaffMemberDTO:
        admin_dist_id, admin_dist_name = cls.get_admin_district_scope(admin_user)
        user = db.query(User).filter(
            or_(
                User.id == staff_id_or_user_id,
                User.staff_id == staff_id_or_user_id,
                User.identifier == staff_id_or_user_id
            )
        ).first()

        if not user or user.role not in [UserRoleEnum.ASHA_WORKER, UserRoleEnum.PHC_DOCTOR]:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "STAFF_NOT_FOUND", "message": "Staff member not found"}
            )

        wp = user.worker_profile
        if admin_dist_name and wp and wp.district_name and wp.district_name != admin_dist_name:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "OUT_OF_DISTRICT", "message": "Cannot transfer staff outside your district"}
            )

        old_facility_id = wp.facility_id if wp else None
        old_facility_name = wp.facility_name if wp else None
        old_village = wp.village_name if wp else None

        new_facility_name = req.facility_name
        if req.facility_id:
            fac = db.query(Facility).filter(
                or_(Facility.id == req.facility_id, Facility.code == req.facility_id)
            ).first()
            if fac:
                new_facility_name = fac.official_name or fac.name
                req.facility_id = fac.id

        if wp:
            if req.facility_id:
                wp.facility_id = req.facility_id
                wp.facility_name = new_facility_name
            if req.village_name:
                wp.village_name = req.village_name
            if req.village_ids:
                wp.village_ids = req.village_ids
            if req.coverage_area:
                wp.coverage_area = req.coverage_area

        user.updated_at = utc_now()

        audit = AuditLog(
            actor_user_id=admin_user.id,
            actor_role=admin_user.role.value if hasattr(admin_user.role, "value") else str(admin_user.role),
            action="STAFF_TRANSFERRED",
            resource_type="User",
            resource_id=user.id,
            outcome="SUCCESS",
            metadata_json={
                "staff_id": user.staff_id or user.identifier,
                "from_facility": old_facility_name or old_facility_id,
                "to_facility": new_facility_name or req.facility_id,
                "from_village": old_village,
                "to_village": req.village_name,
                "reason": req.reason or "Administrative Reassignment"
            }
        )
        db.add(audit)
        db.commit()
        db.refresh(user)

        return cls.get_staff_detail(db, admin_user, user.id)

    @classmethod
    def reset_staff_password(cls, db: Session, admin_user: User, staff_id_or_user_id: str) -> StaffCredentialsResponse:
        admin_dist_id, admin_dist_name = cls.get_admin_district_scope(admin_user)
        user = db.query(User).filter(
            or_(
                User.id == staff_id_or_user_id,
                User.staff_id == staff_id_or_user_id,
                User.identifier == staff_id_or_user_id
            )
        ).first()

        if not user or user.role not in [UserRoleEnum.ASHA_WORKER, UserRoleEnum.PHC_DOCTOR]:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "STAFF_NOT_FOUND", "message": "Staff member not found"}
            )

        wp = user.worker_profile
        if admin_dist_name and wp and wp.district_name and wp.district_name != admin_dist_name:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "OUT_OF_DISTRICT", "message": "Cannot reset password for staff outside your district"}
            )

        temp_password = cls.generate_temporary_password(12)
        pwd_hash = get_password_hash(temp_password)

        user.password_hash = pwd_hash
        user.must_change_password = True
        user.updated_at = utc_now()

        audit = AuditLog(
            actor_user_id=admin_user.id,
            actor_role=admin_user.role.value if hasattr(admin_user.role, "value") else str(admin_user.role),
            action="STAFF_PASSWORD_RESET",
            resource_type="User",
            resource_id=user.id,
            outcome="SUCCESS",
            metadata_json={
                "staff_id": user.staff_id or user.identifier
            }
        )
        db.add(audit)
        db.commit()
        db.refresh(user)

        return StaffCredentialsResponse(
            staff_id=user.staff_id or user.identifier,
            identifier=user.identifier,
            name=user.name,
            role=user.role.value if hasattr(user.role, "value") else str(user.role),
            temporary_password=temp_password,
            must_change_password=True,
            notice="Save these credentials now. The temporary password will not be shown again."
        )

    @classmethod
    def change_password(cls, db: Session, current_user: User, old_password: str, new_password: str) -> Dict[str, Any]:
        if not verify_password(old_password, current_user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "INVALID_CURRENT_PASSWORD", "message": "Current temporary/old password is incorrect"}
            )

        if len(new_password) < 6:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "PASSWORD_TOO_SHORT", "message": "New password must be at least 6 characters"}
            )

        current_user.password_hash = get_password_hash(new_password)
        current_user.must_change_password = False
        current_user.password_changed_at = utc_now()
        current_user.updated_at = utc_now()

        audit = AuditLog(
            actor_user_id=current_user.id,
            actor_role=current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role),
            action="STAFF_PASSWORD_CHANGED",
            resource_type="User",
            resource_id=current_user.id,
            outcome="SUCCESS",
            metadata_json={
                "staff_id": current_user.staff_id or current_user.identifier
            }
        )
        db.add(audit)
        db.commit()
        db.refresh(current_user)

        return {"message": "Password changed successfully", "must_change_password": False}
