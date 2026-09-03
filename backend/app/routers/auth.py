from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, WorkerProfile, CitizenProfile, utc_now
from app.schemas import (
    LoginRequest, StandardResponse, AuthResponseData, UserSessionDTO,
    UserPreferencesUpdateRequest, ChangePasswordRequest
)
from app.auth.security import verify_password, create_access_token, create_refresh_token
from app.dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])

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

    # Build user session info
    facility_id = None
    facility_name = None
    village_ids = None
    district_id = None

    if user.worker_profile:
        facility_id = user.worker_profile.facility_id
        facility_name = user.worker_profile.facility_name
        village_ids = user.worker_profile.village_ids
        district_id = user.worker_profile.district_id

    user_dto = UserSessionDTO(
        id=user.id,
        identifier=user.identifier,
        staff_id=user.staff_id or user.identifier,
        name=user.name,
        role=user.role.value if hasattr(user.role, "value") else str(user.role),
        preferred_language=user.preferred_language or "mr-IN",
        facility_id=facility_id,
        facility_name=facility_name,
        village_ids=village_ids,
        district_id=district_id,
        must_change_password=bool(user.must_change_password),
        account_status=user.account_status or "ACTIVE"
    )

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
    facility_id = None
    facility_name = None
    village_ids = None
    district_id = None

    if current_user.worker_profile:
        facility_id = current_user.worker_profile.facility_id
        facility_name = current_user.worker_profile.facility_name
        village_ids = current_user.worker_profile.village_ids
        district_id = current_user.worker_profile.district_id

    user_dto = UserSessionDTO(
        id=current_user.id,
        identifier=current_user.identifier,
        staff_id=current_user.staff_id or current_user.identifier,
        name=current_user.name,
        role=current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role),
        preferred_language=current_user.preferred_language or "mr-IN",
        facility_id=facility_id,
        facility_name=facility_name,
        village_ids=village_ids,
        district_id=district_id,
        must_change_password=bool(current_user.must_change_password),
        account_status=current_user.account_status or "ACTIVE"
    )
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

    facility_id = None
    facility_name = None
    village_ids = None
    district_id = None

    if current_user.worker_profile:
        facility_id = current_user.worker_profile.facility_id
        facility_name = current_user.worker_profile.facility_name
        village_ids = current_user.worker_profile.village_ids
        district_id = current_user.worker_profile.district_id

    user_dto = UserSessionDTO(
        id=current_user.id,
        identifier=current_user.identifier,
        staff_id=current_user.staff_id or current_user.identifier,
        name=current_user.name,
        role=current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role),
        preferred_language=current_user.preferred_language,
        facility_id=facility_id,
        facility_name=facility_name,
        village_ids=village_ids,
        district_id=district_id,
        must_change_password=bool(current_user.must_change_password),
        account_status=current_user.account_status or "ACTIVE"
    )
    return StandardResponse(data=user_dto.model_dump())

@router.post("/logout", response_model=StandardResponse)
def logout():
    return StandardResponse(data={"message": "Logged out successfully"})

