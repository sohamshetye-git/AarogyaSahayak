/**
 * Aarogya Sahayak - Shared Domain Types and Enums
 */

export enum UserRole {
  CITIZEN = "CITIZEN",
  ASHA_WORKER = "ASHA_WORKER",
  PHC_DOCTOR = "PHC_DOCTOR",
  DISTRICT_ADMIN = "DISTRICT_ADMIN",
  SYSTEM_ADMIN = "SYSTEM_ADMIN",
}

export enum CasePriority {
  URGENT = "URGENT",
  HIGH = "HIGH",
  FOLLOW_UP = "FOLLOW_UP",
  ROUTINE = "ROUTINE",
  INFORMATION = "INFORMATION",
}

export enum CaseStatus {
  NEW = "NEW",
  ASHA_ASSIGNED = "ASHA_ASSIGNED",
  ASHA_ACKNOWLEDGED = "ASHA_ACKNOWLEDGED",
  CITIZEN_CONTACTED = "CITIZEN_CONTACTED",
  VISIT_SCHEDULED = "VISIT_SCHEDULED",
  VISIT_IN_PROGRESS = "VISIT_IN_PROGRESS",
  ASHA_REVIEWED = "ASHA_REVIEWED",
  REFERRED_TO_PHC = "REFERRED_TO_PHC",
  DOCTOR_ACKNOWLEDGED = "DOCTOR_ACKNOWLEDGED",
  PATIENT_ARRIVED = "PATIENT_ARRIVED",
  CONSULTATION_IN_PROGRESS = "CONSULTATION_IN_PROGRESS",
  FOLLOW_UP_REQUIRED = "FOLLOW_UP_REQUIRED",
  REFERRED_TO_HIGHER_FACILITY = "REFERRED_TO_HIGHER_FACILITY",
  COMPLETED = "COMPLETED",
  UNREACHABLE = "UNREACHABLE",
  DECLINED = "DECLINED",
  PENDING_SYNC = "PENDING_SYNC",
}

export enum InformationSource {
  CITIZEN_REPORTED = "CITIZEN_REPORTED",
  ASHA_CONFIRMED = "ASHA_CONFIRMED",
  DEVICE_MEASURED = "DEVICE_MEASURED",
  AI_EXTRACTED = "AI_EXTRACTED",
  RULE_GENERATED = "RULE_GENERATED",
  DOCTOR_CONFIRMED = "DOCTOR_CONFIRMED",
}

export enum IntegrationStatus {
  PENDING = "PENDING",
  PROCESSING = "PROCESSING",
  SUCCESS = "SUCCESS",
  FAILED_RETRYABLE = "FAILED_RETRYABLE",
  FAILED_FINAL = "FAILED_FINAL",
  MOCKED = "MOCKED",
}

export enum SyncStatus {
  PENDING = "PENDING",
  SYNCING = "SYNCING",
  SYNCHRONIZED = "SYNCHRONIZED",
  FAILED_RETRYABLE = "FAILED_RETRYABLE",
  CONFLICT = "CONFLICT",
}

export interface UserDistrictInfo {
  id?: string;
  name?: string;
}

export interface UserFacilityInfo {
  id?: string;
  name?: string;
}

export interface UserCoverageInfo {
  village_id?: string;
  village_ids?: string[];
  village_name?: string;
  coverage_area?: string;
}

export interface UserSession {
  id: string;
  identifier?: string;
  staff_id?: string;
  name: string;
  full_name?: string;
  phone?: string;
  email?: string;
  role: UserRole;
  facility_id?: string;
  facility_name?: string;
  village_ids?: string[];
  village_name?: string;
  district_id?: string;
  district_name?: string;
  coverage_area?: string;
  district?: UserDistrictInfo;
  facility?: UserFacilityInfo;
  coverage?: UserCoverageInfo;
  preferred_language?: string;
  must_change_password?: boolean;
  account_status?: string;
}

export interface StaffMemberDTO {
  id: string;
  staff_id: string;
  identifier: string;
  name: string;
  role: string;
  phone?: string;
  phone_masked?: string;
  email?: string;
  employee_id?: string;
  assigned_facility_id?: string;
  assigned_facility_name?: string;
  district_id?: string;
  district_name?: string;
  village_ids?: string[];
  village_name?: string;
  coverage_area?: string;
  medical_registration_number?: string;
  specialization?: string;
  preferred_language?: string;
  account_status: string;
  must_change_password: boolean;
  last_login_at?: string;
  created_at?: string;
  updated_at?: string;
}

export interface StaffSummaryCountsDTO {
  total: number;
  active: number;
  suspended: number;
  asha_workers: number;
  phc_doctors: number;
}

export interface StaffListResponseData {
  summary: StaffSummaryCountsDTO;
  staff: StaffMemberDTO[];
  total: number;
  page: number;
  limit: number;
}

export interface StaffCreateInput {
  name: string;
  role: "ASHA_WORKER" | "PHC_DOCTOR" | string;
  phone: string;
  email?: string;
  employee_id?: string;
  preferred_language?: string;
  district?: string;
  district_id?: string;
  assigned_facility_id?: string;
  village_name?: string;
  village_ids?: string[];
  coverage_area?: string;
  medical_registration_number?: string;
  specialization?: string;
}

export interface StaffUpdateInput {
  name?: string;
  phone?: string;
  email?: string;
  preferred_language?: string;
  village_name?: string;
  coverage_area?: string;
  specialization?: string;
  medical_registration_number?: string;
}

export interface StaffTransferInput {
  facility_id?: string;
  facility_name?: string;
  village_name?: string;
  village_ids?: string[];
  coverage_area?: string;
  reason?: string;
}

export interface StaffCredentialsResponse {
  staff_id: string;
  identifier: string;
  name: string;
  role: string;
  temporary_password: string;
  must_change_password: boolean;
  notice: string;
}

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: UserSession;

}

export interface CitizenOtpRequestResponse {
  challenge_id: string;
  phone_masked: string;
  expires_in_seconds: number;
  cooldown_seconds: number;
  provider: string;
  mock_code?: string;
}

export interface CitizenOtpVerifyResponse {
  is_new_citizen: boolean;
  phone_normalized: string;
  access_token?: string | null;
  refresh_token?: string | null;
  token_type?: string | null;
  user?: UserSession | null;
  authorized_beneficiaries: BeneficiaryOption[];
}

export interface CitizenOnboardingRequest {
  phone: string;
  full_name: string;
  date_of_birth?: string;
  age?: number;
  gender: string;
  village?: string;
  district?: string;
  pincode?: string;
  preferred_language: string;
  emergency_contact_name?: string;
  emergency_contact_phone?: string;
  emergency_contact_relation?: string;
  abha_reference?: string;
  consent_obtained: boolean;
  confirm_potential_duplicate?: boolean;
  idempotency_key?: string;
}

export interface GuestSessionDTO {
  session_id: string;
  locale: string;
  context_data?: Record<string, any>;
  intended_action?: Record<string, any>;
  expires_at: string;
  is_migrated?: boolean;
}

export interface GuestSessionMigrationDTO {
  migration_id: string;
  status: string;
  user_id: string;
  guest_session_id?: string;
  intended_action?: Record<string, any>;
  context_data?: Record<string, any>;
  migrated_entities: {
    chat_sessions?: string[];
    needs?: string[];
    service_requests?: string[];
  };
}

export interface BeneficiaryOption {

  beneficiaryId: string;
  citizenId: string | null;
  householdMemberId: string | null;
  profileId: string | null;
  displayName: string;
  relationship: "SELF" | "CHILD" | "SPOUSE" | "PARENT" | "OTHER";
  age: number | null;
  gender: string | null;
  isRegisteredPatient: boolean;
  existingCaseId: string | null;
}

export interface VitalRecordDTO {
  id: string;
  case_id: string;
  systolic_bp?: number;
  diastolic_bp?: number;
  temperature_c?: number;
  spo2?: number;
  pulse?: number;
  respiratory_rate?: number;
  glucose_mg_dl?: number;
  weight_kg?: number;
  source_type: InformationSource;
  recorded_by?: string;
  recorded_at: string;
  is_warning_sign?: boolean;
}

export interface SymptomDTO {
  id: string;
  case_id: string;
  term: string;
  normalized_term: string;
  severity?: string;
  duration_text?: string;
  source_type: InformationSource;
}

export interface CaseDTO {
  id: string;
  reference: string;
  citizen_id: string;
  citizen_name: string;
  citizen_phone?: string;
  citizen_age?: number;
  is_pregnant?: boolean;
  gestational_weeks?: number;
  priority: CasePriority;
  status: CaseStatus;
  primary_concern: string;
  preferred_language: string;
  assigned_asha_id?: string;
  assigned_asha_name?: string;
  assigned_facility_id?: string;
  assigned_facility_name?: string;
  assigned_doctor_id?: string;
  assigned_doctor_name?: string;
  symptoms: SymptomDTO[];
  vitals?: VitalRecordDTO[];
  safety_rule_triggered?: boolean;
  safety_rule_reason?: string;
  citizen_guidance_text?: string;
  created_at: string;
  updated_at: string;
}

export interface ReferralDTO {
  id: string;
  reference: string;
  case_id: string;
  from_asha_id?: string;
  to_facility_id: string;
  to_facility_name?: string;
  urgency: CasePriority;
  reason: string;
  status: string;
  acknowledged_by?: string;
  acknowledged_at?: string;
  created_at: string;
}

export interface PrescriptionItemDTO {
  id?: string;
  medicine: string;
  strength?: string;
  form?: string;
  dose: string;
  frequency: string;
  duration: string;
  timing?: string;
  instructions?: string;
}

export interface ConsultationDTO {
  id: string;
  case_id: string;
  doctor_id: string;
  doctor_name: string;
  facility_id: string;
  examination_notes?: string;
  clinical_summary?: string;
  provisional_diagnosis?: string;
  confirmed_diagnosis?: string;
  icd10_code?: string;
  prescription_items: PrescriptionItemDTO[];
  investigation_orders: string[];
  care_plan_summary?: string;
  asha_followup_instructions?: string;
  followup_due_days?: number;
  status: string;
  completed_at?: string;
  created_at: string;
}

export interface FollowUpDTO {
  id: string;
  case_id: string;
  task_type: string;
  assigned_role: UserRole;
  assigned_user_id?: string;
  instructions: string;
  priority: CasePriority;
  due_at: string;
  status: string;
  result?: string;
  completed_at?: string;
}

export interface ClusterAlertDTO {
  id: string;
  alert_title: string;
  district_name: string;
  block_name: string;
  village_name: string;
  symptom_group: string;
  case_count: number;
  time_window_hours: number;
  risk_level: CasePriority;
  status: string;
  created_at: string;
}

export interface DistrictSummaryDTO {
  total_cases: number;
  urgent_cases: number;
  active_referrals: number;
  completed_consultations: number;
  pending_followups: number;
  active_cluster_alerts: number;
  maternal_high_risk_count: number;
  scheme_benefit_applications: number;
}

export interface DoctorReferralsSummaryDTO {
  new_referrals: number;
  active_urgent_referrals: number;
  urgent_pending_review: number;
  acknowledged: number;
  transport_arranged: number;
  patient_arrived: number;
  in_consultation: number;
  processed_today: number;
  transport_en_route: number;
  total_active_referrals: number;
}

export interface WaitingPatientItemDTO {
  citizen_id: string;
  citizen_name: string;
  age?: number;
  gender?: string;
  village_name?: string;
  case_id: string;
  case_reference: string;
  referral_id: string;
  referral_reference: string;
  consultation_id?: string | null;
  consultation_status?: string | null;
  priority: string;
  category: string;
  clinical_context?: string | null;
  chief_concern: string;
  arrived_at?: string | null;
  waiting_minutes: number;
  referring_asha_name?: string | null;
  referring_asha_phone?: string | null;
  latest_vitals?: {
    systolic_bp?: number;
    diastolic_bp?: number;
    spo2?: number;
    pulse?: number;
    temperature_c?: number;
  } | null;
}

export interface WaitingPatientsResponseDTO {
  items: WaitingPatientItemDTO[];
  total: number;
}

export type FacilityServiceCode =
  | "EMERGENCY_CARE"
  | "GENERAL_DOCTOR_PHC"
  | "PREGNANCY_DELIVERY"
  | "CHILD_HEALTH_VACCINATION"
  | "TESTS_DIAGNOSTICS"
  | "MEDICINES_PHARMACY"
  | "TB_SERVICES"
  | "DIABETES_BP_SERVICES"
  | "GOVERNMENT_SCHEME_DESK"
  | "DISTRICT_HOSPITAL_SURGERY"
  | "EMERGENCY"
  | "GENERAL_OPD"
  | "MATERNITY"
  | "CHILD_HEALTH"
  | "DIAGNOSTICS"
  | "PHARMACY"
  | "TB_DOTS"
  | "NCD"
  | "SCHEME_HELP"
  | "SURGERY";

export type FacilityLocationState =
  | {
      source: "GPS";
      latitude: number;
      longitude: number;
      accuracyMeters?: number;
    }
  | {
      source: "MANUAL";
      village: string;
      pincode: string;
      block?: string;
      district?: string;
      state?: string;
    };

export type FacilitySearchForm = {
  beneficiaryId: string | null;
  location: FacilityLocationState | null;
  healthcareNeed: {
    code: FacilityServiceCode;
    title: string;
    description: string;
  } | null;
};

export interface FacilitySearchResultItem {
  result_id: string;
  id: string;
  facility_id?: string | null;
  google_place_id?: string | null;
  name: string;
  display_name: string;
  official_name?: string | null;
  public_reference?: string | null;
  code?: string | null;
  type: string;
  facility_type: string;
  facility_type_label: string;
  ownership: string;
  authority?: string;
  district?: string;
  block?: string;
  village?: string | null;
  pincode?: string | null;
  address?: string | null;
  landmark?: string | null;
  latitude: number;
  longitude: number;
  distance_km: number;
  travel_minutes?: number | null;
  travel_time_minutes: number;
  travel_time_text: string;
  phone?: string | null;
  emergency_helpline: string;
  is_24x7_emergency: boolean;
  emergency_capability: boolean;
  is_open_now?: boolean | null;
  business_status?: string | null;
  operating_status_label: string;
  hours_note: string;
  is_hours_verified: boolean;
  google_maps_uri?: string | null;
  matching_service: string;
  recommendation_reason: string;
  suitability_score: number;
  suitability_reason: string;
  key_services: string[];
  empanelled_schemes: string[];
  verification_status: "PROJECT_VERIFIED" | "GOOGLE_DISCOVERED_UNVERIFIED" | "PROJECT_AND_GOOGLE_MATCHED" | string;
  source: "PROJECT_DATABASE" | "GOOGLE_PLACES" | "MERGED" | string;
  last_verified_date: string;
}

export interface FacilitySearchEnvelopeData {
  search_id: string;
  center?: {
    latitude: number;
    longitude: number;
  };
  service_code: string;
  radius_meters: number;
  items: FacilitySearchResultItem[];
  total: number;
  beneficiary_id?: string | null;
  resolved_location?: {
    source?: string;
    village?: string | null;
    pincode?: string | null;
    latitude?: number | null;
    longitude?: number | null;
    block?: string | null;
    district?: string | null;
    state?: string | null;
  } | null;
}

export interface GeocodedLocationResult {
  formatted_address: string;
  village?: string;
  pincode?: string;
  district?: string;
  state?: string;
  latitude: number;
  longitude: number;
  place_id?: string;
}

export type LocationSourceEnum =
  | "REGISTERED_HOME"
  | "DEVICE_GPS"
  | "MANUAL_VILLAGE"
  | "MANUAL_PINCODE"
  | "MAP_SELECTED"
  | "ASSIGNED_JURISDICTION"
  | "ASSIGNED_FACILITY";

export interface LocationDataContract {
  latitude: number;
  longitude: number;
  accuracy_meters?: number | null;
  altitude_meters?: number | null;
  captured_at: string;
  source: LocationSourceEnum;
  formatted_address?: string | null;
  village?: string | null;
  pincode?: string | null;
  block?: string | null;
  district?: string | null;
  state?: string | null;
  place_id?: string | null;
  is_confirmed: boolean;
}

export interface NearbyFacilityItemDTO {
  facility_id: string;
  name: string;
  facility_type: string;
  latitude: number;
  longitude: number;
  distance_km: number;
  verified_services: string[];
  verification_status: "GOVERNMENT_VERIFIED" | "UNVERIFIED" | "SUSPENDED" | string;
  open_status: "OPEN" | "CLOSED" | "UNKNOWN" | string;
  phone?: string | null;
  address?: string | null;
  place_id?: string | null;
  source: "POSTGRESQL_VERIFIED" | "GOOGLE_DISCOVERED" | string;
}

export interface NearbyFacilitiesResponseDTO {
  items: NearbyFacilityItemDTO[];
  total: number;
  search_id?: string | null;
}

export interface SchemeCategoryDTO {
  category_id: string;
  category_code: string;
  translated_name: string;
  translated_description: string;
  title_en: string;
  title_hi: string;
  title_mr: string;
  icon: string;
  active_scheme_count: number;
  count: number;
}

export interface SchemeListItemDTO {
  scheme_id: string;
  scheme_code: string;
  scheme_name: string;
  canonical_name: string;
  short_name: string;
  classification: string;
  entity_type: string;
  category_codes: string[];
  authority_name: string;
  government_level: "Central" | "State" | string;
  applicable_state: string;
  benefit_one_liner: string;
  description: string;
  summary: string;
  benefits: Array<{ description: string; amount?: number; currency?: string; period?: string }>;
  required_documents: Array<{ name: string; conditional?: boolean }>;
  last_verified_date: string;
  has_eligibility_rules: boolean;
  official_information_url?: string | null;
  official_application_url?: string | null;
  active_status: string;
}

export interface SchemeDetailDTO {
  scheme_id: string;
  scheme_code: string;
  scheme_name: string;
  official_scheme_name: string;
  short_name: string;
  entity_type: string;
  classification: string;
  category_codes: string[];
  description: string;
  authority: { name: string; authority_type?: string; government_level?: string };
  government_level: string;
  applicable_states: string[];
  applicable_districts: string[];
  benefits: Array<{ description: string; amount?: number; currency?: string; period?: string }>;
  structured_eligibility?: Record<string, any>;
  required_documents: Array<{ name: string; conditional?: boolean }>;
  application_methods: string[];
  application_steps: string[];
  access_locations: string[];
  help_centers: string[];
  helpline?: string | null;
  official_information_url?: string | null;
  official_application_url?: string | null;
  effective_date?: string | null;
  scheme_version?: string | null;
  last_verified_date: string;
  data_confidence: string;
  official_verification_disclaimer: string;
  warnings?: string[];
}

export interface SchemeApplicationGuidanceDTO {
  scheme_id: string;
  scheme_code: string;
  scheme_name: string;
  official_application_url?: string | null;
  official_information_url?: string | null;
  helpline?: string | null;
  authority_name: string;
  application_steps: string[];
  required_documents: Array<{ name: string; conditional?: boolean }>;
  help_centers: string[];
  official_verification_method: string;
  last_verified_date: string;
}

export interface SchemeHelpRequirementsDTO {
  scheme_id: string;
  scheme_code: string;
  scheme_name: string;
  scheme_version_id: string;
  version_label: string;
  authority_name: string;
  official_verification_required: boolean;
  required_capabilities: Array<{
    capability_code: string;
    name: string;
    description?: string;
    required_level: string;
    assistance_type: string;
    source_reference?: string;
  }>;
  application_modes: string[];
  helpline?: string | null;
  official_portal_url?: string | null;
  official_information_url?: string | null;
  verification_disclaimer: string;
}

export interface SchemeHelpCentreItemDTO {
  facility_id: string;
  public_reference: string;
  name: string;
  display_name: string;
  official_name?: string;
  facility_type: string;
  facility_type_label: string;
  ownership: string;
  authority?: string;
  state: string;
  district: string;
  block?: string;
  village?: string;
  pincode?: string;
  address?: string;
  landmark?: string;
  latitude: number;
  longitude: number;
  distance_km: number;
  travel_time_minutes: number;
  travel_time_text: string;
  phone?: string;
  emergency_helpline?: string;
  is_24x7_emergency: boolean;
  is_open_now?: boolean | null;
  operating_status_label: string;
  verification_status: "VERIFIED" | "UNVERIFIED" | "DISCOVERED_GOOGLE";
  source_authority: string;
  source_name: string;
  source_url?: string;
  last_verified_at?: string;
  matching_capabilities: string[];
  matching_services: string[];
  exact_capability_match: boolean;
  is_empanelled: boolean;
  empanelled_schemes: string[];
  documents_to_carry?: {
    general: string[];
    conditional: string[];
    missing_from_profile: string[];
  };
  google_maps_directions_url: string;
}

export interface SchemeHelpCentresSearchRequestDTO {
  scheme_version_id?: string;
  beneficiary_id?: string;
  location: {
    source: "CURRENT_GPS" | "REGISTERED_ADDRESS" | "MANUAL" | "MAP_SELECTED" | string;
    latitude: number;
    longitude: number;
    village?: string;
    pincode?: string;
    accuracy_m?: number;
    captured_at?: string;
  };
  radius_km?: number;
  language?: string;
}

export interface SchemeHelpCentresResponseDTO {
  scheme: {
    scheme_id: string;
    scheme_code: string;
    scheme_name: string;
    scheme_version_id: string;
    authority_name: string;
  };
  required_capabilities: Array<{
    capability_code: string;
    name: string;
    description?: string;
  }>;
  items: SchemeHelpCentreItemDTO[];
  total: number;
  search_location: {
    source: string;
    latitude: number;
    longitude: number;
    village?: string;
    pincode?: string;
    accuracy_m?: number;
    captured_at?: string;
  };
  verification_notice: string;
}

export interface SchemeFacilityDetailDTO {
  facility: SchemeHelpCentreItemDTO;
  scheme: {
    scheme_id: string;
    scheme_code: string;
    scheme_name: string;
    scheme_version_id: string;
    authority_name: string;
    official_verification_required: boolean;
  };
  required_documents: {
    general: string[];
    conditional: string[];
    missing_from_profile: string[];
  };
  application_guidance: {
    steps: string[];
    helpline?: string | null;
    official_portal_url?: string | null;
    verification_disclaimer: string;
  };
  operating_hours: Array<{
    day_of_week: string;
    opening_time?: string;
    closing_time?: string;
    is_24x7_emergency: boolean;
    hours_display: string;
  }>;
}

export interface CitizenProfileDTO {
  id: string;
  user_id?: string | null;
  display_name: string;
  legal_name?: string | null;
  preferred_name?: string | null;
  date_of_birth?: string | null;
  age?: number | null;
  sex?: string | null;
  phone?: string | null;
  alternate_phone?: string | null;
  is_phone_verified: boolean;
  emergency_contact_name?: string | null;
  emergency_contact_phone?: string | null;
  emergency_contact_relation?: string | null;
  address?: string | null;
  current_care_location?: string | null;
  village_name: string;
  gram_panchayat?: string | null;
  block_taluka: string;
  district: string;
  state: string;
  pincode?: string | null;
  preferred_language: string;
  abha_reference?: string | null;
  abha_masked?: string | null;
  abha_status: "NOT_LINKED" | "LINK_PENDING" | "LINKED_UNVERIFIED" | "VERIFIED_SANDBOX" | "VERIFIED_LIVE" | string;
  abha_status_label: string;
  blood_group?: string | null;
  allergies: string[];
  chronic_conditions: string[];
  is_pregnant: boolean;
  gestational_weeks?: number | null;
  updated_at?: string | null;
  household_count: number;
}

export interface CitizenProfileUpdateRequest {
  display_name?: string;
  legal_name?: string;
  preferred_name?: string;
  date_of_birth?: string;
  age?: number;
  sex?: string;
  phone?: string;
  alternate_phone?: string;
  emergency_contact_name?: string;
  emergency_contact_phone?: string;
  emergency_contact_relation?: string;
  address?: string;
  current_care_location?: string;
  village_name?: string;
  gram_panchayat?: string;
  block_taluka?: string;
  district?: string;
  state?: string;
  pincode?: string;
  preferred_language?: string;
  blood_group?: string;
  allergies?: string[];
  chronic_conditions?: string[];
  is_pregnant?: boolean;
  gestational_weeks?: number;
}

export interface HouseholdMemberDTO {
  id: string;
  citizen_id: string;
  linked_citizen_profile_id?: string | null;
  full_name: string;
  relationship_type: "SELF" | "CHILD" | "SPOUSE" | "MOTHER" | "FATHER" | "PARENT" | "ELDER" | "OTHER" | string;
  age?: number | null;
  sex?: string | null;
  phone?: string | null;
  abha_reference?: string | null;
  is_pregnant: boolean;
  gestational_weeks?: number | null;
  blood_group?: string | null;
  chronic_conditions: string[];
  health_notes?: string | null;
  is_active: boolean;
  has_clinical_records?: boolean;
  created_at?: string | null;
}

export interface HouseholdMemberCreateRequest {
  full_name: string;
  relationship_type: string;
  age?: number;
  sex?: string;
  phone?: string;
  abha_reference?: string;
  is_pregnant?: boolean;
  gestational_weeks?: number;
  blood_group?: string;
  chronic_conditions?: string[];
  health_notes?: string;
  consent_obtained?: boolean;
}

export interface HouseholdMemberUpdateRequest {
  full_name?: string;
  relationship_type?: string;
  age?: number;
  sex?: string;
  phone?: string;
  abha_reference?: string;
  is_pregnant?: boolean;
  gestational_weeks?: number;
  blood_group?: string;
  chronic_conditions?: string[];
  health_notes?: string;
  is_active?: boolean;
}

export interface CareTeamMemberDTO {
  id: string;
  role: "ASHA_WORKER" | "PHC_DOCTOR" | "PHC_FACILITY" | string;
  name: string;
  designation: string;
  facility_name?: string | null;
  facility_id?: string | null;
  phone?: string | null;
  action_type: "CALL" | "MESSAGE" | "TELECONSULT" | "VISIT" | string;
  is_verified: boolean;
  operating_hours?: string | null;
  address?: string | null;
}

export interface CareTeamResponseDTO {
  assigned_asha?: CareTeamMemberDTO | null;
  assigned_phc?: CareTeamMemberDTO | null;
  assigned_doctor?: CareTeamMemberDTO | null;
  emergency_contact_108: {
    service_name: string;
    ambulance_helpline: string;
    women_helpline?: string;
    national_health_helpline?: string;
    disclaimer: string;
  };
}

export interface ConsentRecordDTO {
  id: string;
  recipient_role: string;
  recipient_name?: string | null;
  purpose: string;
  purpose_label: string;
  scope: Record<string, any>;
  policy_version: string;
  consent_text?: string | null;
  consented_at: string;
  expires_at?: string | null;
  is_revoked: boolean;
  revoked_at?: string | null;
  can_revoke: boolean;
}

export interface AbhaLinkStatusDTO {
  status: "NOT_LINKED" | "LINK_PENDING" | "LINKED_UNVERIFIED" | "VERIFIED_SANDBOX" | "VERIFIED_LIVE" | string;
  status_label: string;
  status_badge_color: string;
  abha_number_masked?: string | null;
  abha_address?: string | null;
  is_live_abdm: boolean;
  verification_mode: string;
  disclaimer: string;
}
