/**
 * Centralized typed route builders for Doctor Portal and linked views.
 * Strictly separates citizenId, caseId, referralId, consultationId, followUpId, investigationId, prescriptionId, and alertId.
 */

export interface DoctorRouteFilters {
  status?: string;
  priority?: string;
  active?: boolean;
  date?: string;
  search?: string;
  page?: number;
  [key: string]: any;
}

function buildQuery(filters?: DoctorRouteFilters): string {
  if (!filters) return "";
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([key, val]) => {
    if (val !== undefined && val !== null && val !== "") {
      params.append(key, String(val));
    }
  });
  const qs = params.toString();
  return qs ? `?${qs}` : "";
}

export const doctorPaths = {
  // Main
  dashboard: () => "/doctor/dashboard",
  directRequests: (filters?: DoctorRouteFilters) => `/doctor/direct-requests${buildQuery(filters)}`,
  activity: (filters?: DoctorRouteFilters) => `/doctor/activity${buildQuery(filters)}`,
  systemStatus: () => "/doctor/system-status",
  reports: (filters?: Record<string, any>) => `/doctor/reports${buildQuery(filters as any)}`,
  reportDetail: (type: string, filters?: Record<string, any>) => `/doctor/reports/${encodeURIComponent(type)}${buildQuery(filters as any)}`,

  // Referrals
  referrals: (filters?: DoctorRouteFilters) => `/doctor/referrals${buildQuery(filters)}`,
  referral: (referralId: string) => `/doctor/referrals/${encodeURIComponent(referralId)}`,

  // Consultations
  consultations: (filters?: DoctorRouteFilters) => `/doctor/consultations${buildQuery(filters)}`,
  consultation: (consultationId: string) => `/doctor/consultations/${encodeURIComponent(consultationId)}`,

  // Patient Record & Timeline
  patient: (citizenId: string, returnTo?: string) => `/doctor/patients/${encodeURIComponent(citizenId)}${returnTo ? `?returnTo=${encodeURIComponent(returnTo)}` : ""}`,
  patientRecord: (citizenId: string, returnTo?: string) => `/doctor/patients/${encodeURIComponent(citizenId)}${returnTo ? `?returnTo=${encodeURIComponent(returnTo)}` : ""}`,
  patients: (filters?: DoctorRouteFilters) => `/doctor/patients${buildQuery(filters)}`,
  timeline: (caseId: string, returnTo?: string, highlightOrderId?: string) => {
    const params = new URLSearchParams();
    if (returnTo) params.append("returnTo", returnTo);
    if (highlightOrderId) params.append("highlightOrder", highlightOrderId);
    const qs = params.toString();
    return `/doctor/cases/${encodeURIComponent(caseId)}/timeline${qs ? `?${qs}` : ""}`;
  },
  caseTimeline: (caseId: string, returnTo?: string, highlightOrderId?: string) => {
    const params = new URLSearchParams();
    if (returnTo) params.append("returnTo", returnTo);
    if (highlightOrderId) params.append("highlightOrder", highlightOrderId);
    const qs = params.toString();
    return `/doctor/cases/${encodeURIComponent(caseId)}/timeline${qs ? `?${qs}` : ""}`;
  },

  // Follow-ups & Escalations
  followUps: (filters?: DoctorRouteFilters) => `/doctor/followups${buildQuery(filters)}`,
  followUp: (followUpId: string, returnTo?: string) => `/doctor/followups/${encodeURIComponent(followUpId)}${returnTo ? `?returnTo=${encodeURIComponent(returnTo)}` : ""}`,
  followUpDetail: (followUpId: string, returnTo?: string) => `/doctor/followups/${encodeURIComponent(followUpId)}${returnTo ? `?returnTo=${encodeURIComponent(returnTo)}` : ""}`,

  // Investigations & Orders
  investigations: (filters?: DoctorRouteFilters) => `/doctor/investigations${buildQuery(filters)}`,
  investigation: (investigationId: string) => `/doctor/investigations/${encodeURIComponent(investigationId)}`,
  investigationDetail: (investigationId: string) => `/doctor/investigations/${encodeURIComponent(investigationId)}`,

  // Prescriptions
  prescriptions: (filters?: DoctorRouteFilters) => `/doctor/prescriptions${buildQuery(filters)}`,
  prescription: (prescriptionId: string) => `/doctor/prescriptions/${encodeURIComponent(prescriptionId)}`,
  prescriptionDetail: (prescriptionId: string) => `/doctor/prescriptions/${encodeURIComponent(prescriptionId)}`,

  // Alerts & Cluster Management
  alerts: (filters?: DoctorRouteFilters) => `/doctor/alerts${buildQuery(filters)}`,
  alert: (alertId: string) => `/doctor/alerts/${encodeURIComponent(alertId)}`,
};

export const doctorRoutes = doctorPaths;
