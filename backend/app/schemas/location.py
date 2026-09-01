from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime

class LocationDataDTO(BaseModel):
    latitude: float
    longitude: float
    accuracy_meters: Optional[float] = None
    altitude_meters: Optional[float] = None
    captured_at: Optional[str] = None
    source: str = "DEVICE_GPS" # REGISTERED_HOME, DEVICE_GPS, MANUAL_VILLAGE, MANUAL_PINCODE, MAP_SELECTED, ASSIGNED_JURISDICTION, ASSIGNED_FACILITY
    formatted_address: Optional[str] = None
    village: Optional[str] = None
    pincode: Optional[str] = None
    block: Optional[str] = None
    district: Optional[str] = None
    state: Optional[str] = "Maharashtra"
    place_id: Optional[str] = None
    is_confirmed: bool = False

    @validator("latitude")
    def validate_lat(cls, v):
        if v < -90.0 or v > 90.0:
            raise ValueError("Latitude must be between -90 and 90 degrees")
        return v

    @validator("longitude")
    def validate_lng(cls, v):
        if v < -180.0 or v > 180.0:
            raise ValueError("Longitude must be between -180 and 180 degrees")
        return v

    @validator("accuracy_meters")
    def validate_accuracy(cls, v):
        if v is not None and v < 0:
            raise ValueError("Accuracy must be non-negative")
        return v


class ReverseGeocodeRequestDTO(BaseModel):
    latitude: float
    longitude: float
    accuracy_m: Optional[float] = None
    captured_at: Optional[str] = None
    language: Optional[str] = "mr-IN"

    @validator("latitude")
    def validate_lat(cls, v):
        if v < -90.0 or v > 90.0:
            raise ValueError("Latitude must be between -90 and 90 degrees")
        return v

    @validator("longitude")
    def validate_lng(cls, v):
        if v < -180.0 or v > 180.0:
            raise ValueError("Longitude must be between -180 and 180 degrees")
        return v


class ReverseGeocodeResponseDTO(BaseModel):
    formatted_address: str
    village: Optional[str] = None
    locality: Optional[str] = None
    block: Optional[str] = None
    district: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    pincode: Optional[str] = None
    latitude: float
    longitude: float
    accuracy_m: Optional[float] = None
    provider: str = "GOOGLE"
    resolved_at: Optional[str] = None
    place_id: Optional[str] = None


class FacilityNearbyRequestDTO(BaseModel):
    beneficiary_id: Optional[str] = None
    location: LocationDataDTO
    required_capabilities: Optional[List[str]] = Field(default_factory=lambda: ["GENERAL_PHC"])
    emergency: bool = False
    radius_km: float = 25.0


class NearbyFacilityItemDTO(BaseModel):
    facility_id: str
    name: str
    facility_type: str
    latitude: float
    longitude: float
    distance_km: float
    verified_services: List[str] = Field(default_factory=list)
    verification_status: str = "GOVERNMENT_VERIFIED" # GOVERNMENT_VERIFIED, UNVERIFIED, SUSPENDED
    open_status: str = "UNKNOWN" # OPEN, CLOSED, UNKNOWN
    phone: Optional[str] = None
    address: Optional[str] = None
    place_id: Optional[str] = None
    source: str = "POSTGRESQL_VERIFIED" # POSTGRESQL_VERIFIED, GOOGLE_DISCOVERED


class FacilityNearbyResponseDTO(BaseModel):
    items: List[NearbyFacilityItemDTO]
    total: int


class UserLocationPreferenceUpdateDTO(BaseModel):
    preferred_source: str # DEVICE_GPS, MANUAL_VILLAGE, MANUAL_PINCODE, REGISTERED_HOME
    manual_village_name: Optional[str] = None
    manual_pincode: Optional[str] = None


class AuthorizedJurisdictionsResponseDTO(BaseModel):
    worker_id: str
    worker_name: str
    role: str
    district_id: Optional[str] = None
    district_name: str
    assigned_villages: List[Dict[str, Any]] = Field(default_factory=list)
    assigned_panchayats: List[str] = Field(default_factory=list)


class AuthorizedFacilitiesResponseDTO(BaseModel):
    doctor_id: str
    doctor_name: str
    primary_facility_id: str
    primary_facility_name: str
    authorized_facilities: List[Dict[str, Any]] = Field(default_factory=list)
