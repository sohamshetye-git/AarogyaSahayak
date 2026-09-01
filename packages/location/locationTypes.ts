/**
 * Aarogya Sahayak - Shared Location Types & Data Contracts
 */

export type LocationSource =
  | "REGISTERED_HOME"
  | "DEVICE_GPS"
  | "MANUAL_VILLAGE"
  | "MANUAL_PINCODE"
  | "MAP_SELECTED"
  | "LAST_KNOWN"
  | "ASSIGNED_JURISDICTION"
  | "ASSIGNED_FACILITY";

export type LocationReactiveState =
  | "IDLE"
  | "REQUESTING_PERMISSION"
  | "LOCATING"
  | "RESOLVING_ADDRESS"
  | "READY"
  | "PERMISSION_DENIED"
  | "UNAVAILABLE"
  | "TIMEOUT"
  | "LOW_ACCURACY"
  | "VERY_LOW_ACCURACY"
  | "REVERSE_GEOCODE_FAILED"
  | "STALE"
  | "ERROR";

export interface LocationData {
  latitude: number;
  longitude: number;
  accuracy_meters?: number | null;
  altitude_meters?: number | null;
  captured_at: string;
  source: LocationSource;
  formatted_address?: string | null;
  village?: string | null;
  pincode?: string | null;
  block?: string | null;
  district?: string | null;
  state?: string | null;
  place_id?: string | null;
  is_confirmed: boolean;
  provider?: string;
}

export interface UserLocationPreference {
  user_id?: string;
  preferred_source: LocationSource;
  manual_village_id?: string | null;
  manual_village_name?: string | null;
  manual_pincode?: string | null;
  updated_at: string;
}

export interface CareRequestLocationPayload {
  service_request_id?: string | null;
  latitude: number;
  longitude: number;
  accuracy_meters?: number | null;
  altitude_meters?: number | null;
  source: LocationSource;
  formatted_address?: string | null;
  village?: string | null;
  pincode?: string | null;
  block?: string | null;
  district?: string | null;
  state?: string | null;
  place_id?: string | null;
  captured_at: string;
  confirmed_at: string;
}

export interface VisitLocationPayload {
  visit_id?: string | null;
  latitude: number;
  longitude: number;
  accuracy_meters?: number | null;
  source: LocationSource;
  captured_at: string;
}

export interface ReverseGeocodeResult {
  formatted_address: string;
  village?: string | null;
  locality?: string | null;
  pincode?: string | null;
  postal_code?: string | null;
  block?: string | null;
  district?: string | null;
  state?: string | null;
  latitude: number;
  longitude: number;
  accuracy_m?: number | null;
  place_id?: string | null;
  provider?: string;
  source?: string;
  resolved_at?: string | null;
}

export interface NearbyFacilityItem {
  facility_id: string;
  name: string;
  facility_type: string;
  latitude: number;
  longitude: number;
  distance_km: number;
  verified_services: string[];
  verification_status: "GOVERNMENT_VERIFIED" | "UNVERIFIED" | "SUSPENDED" | string;
  open_status: "OPEN" | "CLOSED" | "UNKNOWN";
  phone?: string | null;
  address?: string | null;
  place_id?: string | null;
  source: "POSTGRESQL_VERIFIED" | "GOOGLE_DISCOVERED" | string;
}

export interface NearbyFacilitiesResponse {
  items: NearbyFacilityItem[];
  total: number;
  search_id?: string | null;
}

export interface LocationDiagnostic {
  source: LocationSource;
  latitude: number;
  longitude: number;
  accuracy_meters?: number | null;
  captured_at: string;
  resolved_at?: string | null;
  is_cached: boolean;
  cache_age_seconds?: number | null;
  permission_state: string;
  provider: string;
}

export interface LocationState {
  currentLocation: LocationData | null;
  cachedLocation: LocationData | null;
  reactiveState: LocationReactiveState;
  errorMessage: string | null;
  permissionStatus: "prompt" | "granted" | "denied" | "unavailable";
  isFresh: boolean;
  lastUpdated: string | null;
  diagnostic?: LocationDiagnostic | null;
}
