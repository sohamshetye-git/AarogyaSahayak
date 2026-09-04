from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, WorkerProfile, CitizenProfile, utc_now
from app.schemas import (
    LoginRequest, StandardResponse, AuthResponseData, UserSessionDTO,
    UserPreferencesUpdateRequest, ChangePasswordRequest,
    UserDistrictDTO, UserFacilityDTO, UserCoverageDTO
)
from app.auth.security import verify_password, create_access_token, create_refresh_token
from app.dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])

def build_user_session_dto(user: User) -> UserSessionDTO:
    facility_id = None
    facility_name = None
    village_ids = None
    village_name = None
    district_id = None
    district_name = None
    coverage_area = None

    if user.worker_profile:
        wp = user.worker_profile
        facility_id = wp.facility_id
        facility_name = wp.facility_name
        village_ids = wp.village_ids
        village_name = wp.village_name
        district_id = wp.district_id
        district_name = wp.district_name
        coverage_area = wp.coverage_area
    elif user.citizen_profile:
        cp = user.citizen_profile
        facility_id = cp.assigned_facility_id
        village_name = cp.village_name
        district_name = cp.district

    district_dto = None
    if district_id or district_name:
        district_dto = UserDistrictDTO(id=district_id, name=district_name or "Assigned District")

    facility_dto = None
    if facility_id or facility_name:
        facility_dto = UserFacilityDTO(id=facility_id, name=facility_name or "Assigned Facility")

    coverage_dto = None
    if village_ids or village_name or coverage_area:
        v_id = village_ids[0] if (village_ids and len(village_ids) > 0) else None
        coverage_dto = UserCoverageDTO(
            village_id=v_id,
            village_ids=village_ids,
            village_name=village_name,
            coverage_area=coverage_area or village_name
        )

    return UserSessionDTO(
        id=user.id,
        identifier=user.identifier,
        staff_id=user.staff_id or user.identifier,
        name=user.name,
        full_name=user.name,
        role=user.role.value if hasattr(user.role, "value") else str(user.role),
        preferred_language=user.preferred_language or "mr-IN",
        facility_id=facility_id,
        facility_name=facility_name,
        village_ids=village_ids,
        village_name=village_name,
        district_id=district_id,
        district_name=district_name,
        coverage_area=coverage_area,
        district=district_dto,
        facility=facility_dto,
        coverage=coverage_dto,
        must_change_password=bool(user.must_change_password),
        account_status=user.account_status or "ACTIVE"
    )

@router.post("/login", response_model=StandardResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(
        (User.identifier == req.identifier) | (User.staff_id == req.identifier) | (User.phone == req.identifier) | (User.email == req.identifier)
    ).first()

    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_CREDENTIALS", "message": "Invalid identifier or password"}
        )

    if not user.is_active or user.account_status == "SUSPENDED":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "ACCOUNT_INACTIVE", "message": "Account is deactivated or suspended"}
        )

    # Update last login timestamp
    user.last_login_at = utc_now()
    db.commit()

    user_dto = build_user_session_dto(user)

    access_token = create_access_token({"sub": user.id, "role": user.role.value if hasattr(user.role, "value") else str(user.role)})
    refresh_token = create_refresh_token({"sub": user.id})

    return StandardResponse(
        data=AuthResponseData(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            user=user_dto
        ).model_dump()
    )

@router.post("/change-password", response_model=StandardResponse)
def change_password(
    req: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    from app.services.staff_service import StaffManagementService
    res = StaffManagementService.change_password(
        db=db,
        current_user=current_user,
        old_password=req.old_password,
        new_password=req.new_password
    )
    return StandardResponse(data=res)

@router.get("/me", response_model=StandardResponse)
def get_current_user_profile(current_user: User = Depends(get_current_user)):
    if not current_user.is_active or current_user.account_status == "SUSPENDED":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "ACCOUNT_INACTIVE", "message": "Account is deactivated or suspended"}
        )
    user_dto = build_user_session_dto(current_user)
    return StandardResponse(data=user_dto.model_dump())

@router.patch("/me/preferences", response_model=StandardResponse)
def update_user_preferences(
    req: UserPreferencesUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    current_user.preferred_language = req.preferred_language
    if current_user.citizen_profile:
        current_user.citizen_profile.preferred_language = req.preferred_language
    db.commit()
    db.refresh(current_user)

    user_dto = build_user_session_dto(current_user)
    return StandardResponse(data=user_dto.model_dump())

@router.post("/logout", response_model=StandardResponse)
def logout():
    return StandardResponse(data={"message": "Logged out successfully"})

