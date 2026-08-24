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

export interface UserSession {
  id: string;
  name: string;
  phone?: string;
  email?: string;
  role: UserRole;
  facility_id?: string;
  facility_name?: string;
  village_ids?: string[];
  district_id?: string;
}

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: UserSession;
}

export interface CitizenProfileDTO {
  id: string;
  user_id?: string;
  display_name: string;
  age_estimate?: number;
  sex?: string;
  phone?: string;
  village_name?: string;
  preferred_language: string;
  abha_number?: string;
  is_pregnant?: boolean;
  gestational_weeks?: number;
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
