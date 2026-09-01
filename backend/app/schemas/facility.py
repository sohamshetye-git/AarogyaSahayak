from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class SearchLocationDTO(BaseModel):
    source: Optional[str] = "GPS"
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    village: Optional[str] = None
    pincode: Optional[str] = None
    district: Optional[str] = None
    taluka: Optional[str] = None
    landmark: Optional[str] = None

class FacilitySearchRequestDTO(BaseModel):
    service_code: Optional[str] = Field(None, description="Canonical service code e.g. SURGERY, EMERGENCY, MATERNITY, CHILD_HEALTH, DIAGNOSTICS, PHARMACY, TB_DOTS, NCD, SCHEME_HELP, GENERAL_OPD")
    service_type: Optional[str] = Field(None, description="Alias for service_code")
    urgency: Optional[str] = Field("ROUTINE", description="Urgency level: ROUTINE, HIGH, URGENT, EMERGENCY, NORMAL")
    patient_category: Optional[str] = Field("GENERAL", description="Beneficiary category: MATERNAL, CHILD, ADULT, ELDERLY, NCD")
    beneficiary_id: Optional[str] = Field(None, description="CitizenProfile ID or HouseholdMember ID")
    active_case_id: Optional[str] = Field(None, description="Optional linked Citizen case ID")
    location: Optional[SearchLocationDTO] = Field(None, description="Nested location object")
    latitude: Optional[float] = Field(None, description="Citizen current latitude")
    longitude: Optional[float] = Field(None, description="Citizen current longitude")
    village_name: Optional[str] = Field(None, description="Manual locality/village")
    pincode: Optional[str] = Field(None, description="Manual pincode")
    location_method: Optional[str] = Field("GPS", description="GPS, PINCODE_VILLAGE, SAVED, ASHA_HELP, MANUAL")
    scheme_code: Optional[str] = Field(None, description="Filter by empanelled scheme e.g. PMJAY, MJPJAY, JSY")
    government_only: Optional[bool] = Field(False, description="Filter only government facilities")
    radius_km: Optional[float] = Field(None, description="Alias for max_distance_km")
    max_distance_km: Optional[float] = Field(50.0, description="Maximum search radius in kilometers")
    preferred_language: Optional[str] = Field("mr-IN", description="Preferred response language")
    locale: Optional[str] = Field(None, description="Alias for preferred_language")
    location_consent: Optional[bool] = Field(True, description="Explicit user consent to process coordinates")

class FacilityServiceDTO(BaseModel):

    id: str
    service_code: str
    service_name: str
    service_level: str
    availability_status: str
    emergency_capability: bool
    appointment_requirement: bool
    cost_type: str
    last_verified_at: Optional[str] = None

class FacilityHoursDTO(BaseModel):
    day_of_week: str
    opening_time: Optional[str] = None
    closing_time: Optional[str] = None
    is_24x7_emergency: bool
    verification_status: str
    hours_display: str

class FacilitySchemeDTO(BaseModel):
    scheme_code: str
    scheme_name: str
    empanelment_reference: Optional[str] = None
    verification_status: str
    official_source: str


class FacilitySearchResultDTO(BaseModel):
    result_id: str
    id: str  # Legacy & primary key compatibility
    facility_id: Optional[str] = None
    google_place_id: Optional[str] = None
    name: str
    display_name: str
    official_name: Optional[str] = None
    public_reference: Optional[str] = None
    code: Optional[str] = None
    type: str = "HOSPITAL"
    facility_type: str = "PHC"
    facility_type_label: str = "Primary Health Centre"
    ownership: str = "GOVERNMENT"
    authority: Optional[str] = "Public Health Department, Maharashtra"
    district: Optional[str] = "District 04"
    block: Optional[str] = "Kalyanpur Block"
    village: Optional[str] = None
    pincode: Optional[str] = None
    address: Optional[str] = None
    landmark: Optional[str] = None
    latitude: float
    longitude: float
    distance_km: float
    travel_minutes: Optional[int] = None
    travel_time_minutes: int = 15
    travel_time_text: str = "~15 mins"
    phone: Optional[str] = None
    emergency_helpline: str = "108"
    is_24x7_emergency: bool = False
    emergency_capability: bool = False
    is_open_now: Optional[bool] = None
    business_status: Optional[str] = "OPERATIONAL"
    operating_status_label: str = "Hours Unconfirmed"
    hours_note: str = ""
    is_hours_verified: bool = False
    google_maps_uri: Optional[str] = None
    matching_service: str = "GENERAL_OPD"
    recommendation_reason: str = "Nearby healthcare facility"
    suitability_score: float = 100.0
    suitability_reason: str = ""
    key_services: List[str] = []
    empanelled_schemes: List[str] = []
    verification_status: str = "PROJECT_VERIFIED"
    source: str = "PROJECT_DATABASE"
    last_verified_date: str = "August 2026"

class ResolvedLocationDTO(BaseModel):
    source: Optional[str] = "GPS"
    village: Optional[str] = None
    pincode: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    block: Optional[str] = None
    district: Optional[str] = None
    state: Optional[str] = None

class SearchCenterDTO(BaseModel):
    latitude: float
    longitude: float

class FacilitySearchEnvelopeDataDTO(BaseModel):
    search_id: str
    center: Optional[SearchCenterDTO] = None
    service_code: str = "GENERAL_OPD"
    radius_meters: int = 10000
    items: List[FacilitySearchResultDTO]
    total: int
    beneficiary_id: Optional[str] = None
    resolved_location: Optional[ResolvedLocationDTO] = None

class FacilitySearchResponseEnvelopeDTO(BaseModel):
    data: FacilitySearchEnvelopeDataDTO
    request_id: Optional[str] = None

class ManualLocationGeocodeRequestDTO(BaseModel):
    query: str
    preferred_language: Optional[str] = "mr-IN"

class GeocodedLocationItemDTO(BaseModel):
    formatted_address: str
    village: Optional[str] = None
    pincode: Optional[str] = None
    district: Optional[str] = None
    state: Optional[str] = None
    latitude: float
    longitude: float
    place_id: Optional[str] = None

class ManualLocationGeocodeResponseDTO(BaseModel):
    locations: List[GeocodedLocationItemDTO]
    total: int


class FacilityDetailDTO(BaseModel):
    id: str
    public_reference: str
    code: Optional[str] = None
    official_name: str
    display_name: str
    facility_type: str
    facility_type_label: str
    ownership: str
    authority: str
    state: str
    district: str
    block: str
    village: Optional[str] = None
    pincode: Optional[str] = None
    address: Optional[str] = None
    landmark: Optional[str] = None
    latitude: float
    longitude: float
    distance_km: Optional[float] = None
    travel_time_text: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    emergency_helpline: str = "108"
    verification_status: str
    source_name: str
    last_verified_date: str
    is_24x7_emergency: bool
    operating_status_label: str
    hours_disclaimer: str
    services: List[FacilityServiceDTO]
    weekly_hours: List[FacilityHoursDTO]
    schemes: List[FacilitySchemeDTO]
    google_maps_uri: Optional[str] = None
    google_place_id: Optional[str] = None
    directions_text: Optional[str] = None

class FacilitySelectionRequestDTO(BaseModel):
    selected_facility_id: str
    case_id: Optional[str] = None
    search_reference_id: Optional[str] = None
    reason: Optional[str] = None

class FacilityCallEventRequestDTO(BaseModel):
    dialled_phone: str
    event_type: str = "CALL_INITIATED"

class FacilityCallFeedbackRequestDTO(BaseModel):
    contact_feedback: str # CONNECTED, UNREACHABLE, BUSY, CANCELLED_BY_USER

class FacilityAssistanceCreateRequestDTO(BaseModel):
    beneficiary_id: Optional[str] = None # Citizen or Household member ID
    case_id: Optional[str] = None
    need_id: Optional[str] = None
    assistance_type: str = "TRANSPORT_AND_DIRECTION" # TRANSPORT, DIRECTION_GUIDANCE, ACCOMPANY_VISIT, EMERGENCY_EVACUATION
    assistance_reason: str
    transport_needed: bool = True
    preferred_contact: str = "PHONE"
    citizen_lat: Optional[float] = None
    citizen_lng: Optional[float] = None
    citizen_locality: Optional[str] = None
    consent_given: bool = True
    idempotency_key: Optional[str] = None

class FacilityAppointmentCreateRequestDTO(BaseModel):
    beneficiary_id: Optional[str] = None
    service_code: str
    service_name: str
    requested_slot: str
    notes: Optional[str] = None
    idempotency_key: Optional[str] = None

class FacilityAssistanceResponseDTO(BaseModel):
    id: str
    request_reference: str
    facility_id: str
    facility_name: str
    beneficiary_name: str
    assistance_type: str
    status: str
    status_label: str
    assigned_asha_name: str
    due_at: Optional[str] = None
    created_at: str

class FacilityAppointmentResponseDTO(BaseModel):
    id: str
    appointment_reference: str
    facility_id: str
    facility_name: str
    service_name: str
    beneficiary_name: str
    requested_slot: str
    status: str
    status_label: str
    created_at: str
