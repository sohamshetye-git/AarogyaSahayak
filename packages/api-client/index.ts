import type { WaitingPatientItemDTO, WaitingPatientsResponseDTO } from "@aarogya/shared-types";

export interface ApiResponse<T> {
  data: T;
  request_id?: string;
}

export interface ApiErrorResponse {
  error: {
    code: string;
    message: string;
    fields?: Record<string, string>;
  };
  request_id?: string;
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

export class ApiError extends Error {
  code: string;
  status?: number;
  statusCode?: number;
  fields?: Record<string, string>;
  requestId?: string;

  constructor(message: string, code = "API_ERROR", fields?: Record<string, string>, requestId?: string, status?: number) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.status = status;
    this.statusCode = status;
    this.fields = fields;
    this.requestId = requestId;
  }
}

export class AarogyaApiClient {
  private baseUrl: string;
  private token: string | null = null;
  private refreshPromise: Promise<string | null> | null = null;
  private onTokenRefreshedCallback?: (token: string, user?: any) => void;

  constructor(baseUrl?: string) {
    const isBrowser = typeof window !== "undefined";
    const isProductionBrowser =
      isBrowser &&
      window.location.hostname !== "localhost" &&
      window.location.hostname !== "127.0.0.1";

    const defaultFallback = isProductionBrowser
      ? "https://aarogya-sahayak-backend.onrender.com/api"
      : "http://localhost:8000/api";

    const rawUrl =
      baseUrl ||
      (typeof import.meta !== "undefined" && (import.meta as any).env?.VITE_API_BASE_URL) ||
      (typeof process !== "undefined" && process.env?.VITE_API_BASE_URL) ||
      defaultFallback;

    this.baseUrl = this.normalizeBaseUrl(rawUrl, defaultFallback);
  }

  private normalizeBaseUrl(url: string, fallback: string): string {
    let clean = (url || "").trim();
    if (!clean) return fallback;
    // Strip trailing slashes
    clean = clean.replace(/\/+$/, "");
    // If url does not end with /api and does not point directly to an API subpath, append /api
    if (!clean.endsWith("/api")) {
      // Check if it's just origin e.g. https://domain.com
      try {
        const parsed = new URL(clean);
        if (parsed.pathname === "" || parsed.pathname === "/") {
          clean = `${parsed.origin}/api`;
        }
      } catch {
        // Keep as is if invalid URL format
      }
    }
    return clean;
  }

  getBaseUrl(): string {
    return this.baseUrl;
  }

  getOrigin(): string {
    try {
      return new URL(this.baseUrl).origin;
    } catch {
      return "https://aarogya-sahayak-backend.onrender.com";
    }
  }

  async checkHealth(timeoutMs: number = 5000): Promise<{ status: string; ok: boolean; data?: any }> {
    const healthUrl = `${this.getOrigin()}/health`;
    try {
      const controller = typeof AbortController !== "undefined" ? new AbortController() : null;
      const timeoutId = controller ? setTimeout(() => controller.abort(), timeoutMs) : null;
      try {
        const res = await fetch(healthUrl, {
          method: "GET",
          signal: controller ? controller.signal : undefined,
        });
        if (res.ok) {
          const data = await res.json().catch(() => ({}));
          return { status: "ONLINE", ok: true, data };
        }
        return { status: "DEGRADED", ok: false };
      } finally {
        if (timeoutId) clearTimeout(timeoutId);
      }
    } catch {
      return { status: "OFFLINE", ok: false };
    }
  }

  setToken(token: string | null) {
    this.token = token;
    if (typeof localStorage !== "undefined") {
      if (token) {
        localStorage.setItem("aarogya_citizen_token", token);
      } else {
        localStorage.removeItem("aarogya_citizen_token");
      }
    }
  }

  getToken(): string | null {
    if (this.token) return this.token;
    if (typeof localStorage !== "undefined") {
      return localStorage.getItem("aarogya_citizen_token") || localStorage.getItem("aarogya_token");
    }
    return null;
  }

  setTokenRefreshedCallback(callback: (token: string, user?: any) => void) {
    this.onTokenRefreshedCallback = callback;
  }

  private isAuthEndpoint(endpoint: string): boolean {
    return (
      endpoint.includes("/auth/login") ||
      endpoint.includes("/citizen/auth/otp") ||
      endpoint.includes("/citizen/auth/refresh") ||
      endpoint.includes("/citizen/auth/register") ||
      endpoint.includes("/citizen/auth/guest") ||
      endpoint.includes("/health")
    );
  }

  public async performRefresh(): Promise<string | null> {
    if (this.refreshPromise) {
      return this.refreshPromise;
    }
    this.refreshPromise = (async () => {
      try {
        const res = await fetch(`${this.baseUrl}/citizen/auth/refresh`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
          body: JSON.stringify({}),
        });
        if (!res.ok) {
          if (res.status === 401) {
            this.setToken(null);
            return null;
          }
          const errData = await res.json().catch(() => ({}));
          const error: any = new Error(errData?.detail || `Refresh failed with status ${res.status}`);
          error.status = res.status;
          error.code = res.status >= 500 ? "BACKEND_ERROR" : "REFRESH_ERROR";
          throw error;
        }
        const json = await res.json();
        const data = json.data !== undefined ? json.data : json;
        const newToken = data?.access_token;
        if (newToken) {
          this.setToken(newToken);
          if (this.onTokenRefreshedCallback) {
            this.onTokenRefreshedCallback(newToken, data.user);
          }
          return newToken;
        }
        return null;
      } catch (err: any) {
        if (err?.name === "TypeError" || err?.message?.includes("Failed to fetch") || err?.message?.includes("NetworkError")) {
          const networkErr: any = new Error("Backend service unreachable or network error.");
          networkErr.code = "BACKEND_UNREACHABLE";
          throw networkErr;
        }
        if (err?.code) throw err;
        return null;
      } finally {
        this.refreshPromise = null;
      }
    })();
    return this.refreshPromise;
  }

  public get<T>(endpoint: string, params?: Record<string, any>, options: RequestInit = {}): Promise<T> {
    let url = endpoint;
    if (params) {
      const searchParams = new URLSearchParams();
      Object.entries(params).forEach(([key, val]) => {
        if (val !== undefined && val !== null && val !== "") {
          searchParams.append(key, String(val));
        }
      });
      const qs = searchParams.toString();
      if (qs) {
        url += (url.includes("?") ? "&" : "?") + qs;
      }
    }
    return this.request<T>(url, { ...options, method: "GET" });
  }

  public post<T>(endpoint: string, body?: any, options: RequestInit = {}): Promise<T> {
    return this.request<T>(endpoint, {
      ...options,
      method: "POST",
      body: body ? JSON.stringify(body) : undefined,
    });
  }

  public async request<T>(endpoint: string, options: RequestInit = {}, isRetry: boolean = false): Promise<T> {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      ...(options.headers as Record<string, string>),
    };

    const activeToken = this.getToken();
    if (activeToken) {
      headers["Authorization"] = `Bearer ${activeToken}`;
    }

    if (!headers["Accept-Language"] && typeof localStorage !== "undefined") {
      const activeLang =
        localStorage.getItem("aarogya_preferred_language") ||
        localStorage.getItem("preferred_language") ||
        "en-IN";
      headers["Accept-Language"] = activeLang;
    }

    const url = `${this.baseUrl}${endpoint.startsWith("/") ? "" : "/"}${endpoint}`;
    
    let response: Response;
    try {
      const controller = typeof AbortController !== "undefined" ? new AbortController() : null;
      const timeoutId = controller ? setTimeout(() => controller.abort(), 20000) : null;
      
      try {
        response = await fetch(url, {
          credentials: "include",
          ...options,
          headers,
          signal: options.signal || (controller ? controller.signal : undefined),
        });
      } finally {
        if (timeoutId) clearTimeout(timeoutId);
      }
    } catch (fetchErr: any) {
      if (fetchErr.name === "AbortError") {
        throw new ApiError("Request timed out. Please verify your network and retry.", "TIMEOUT");
      }
      // Network failure / connection refused / DNS lookup error
      throw new ApiError(
        "Backend unreachable. Please ensure the backend server is running and accessible.",
        "BACKEND_UNREACHABLE"
      );
    }

    // Auto-refresh once on 401 for non-auth endpoints
    if (response.status === 401 && !isRetry && !this.isAuthEndpoint(endpoint)) {
      const newToken = await this.performRefresh();
      if (newToken) {
        return this.request<T>(endpoint, options, true);
      }
    }

    if (!response.ok) {
      let rawErrorData: any = null;
      try {
        rawErrorData = await response.json();
      } catch {
        // Response was not JSON
      }

      if (response.status === 401 || response.status === 403) {
        const msg =
          (typeof rawErrorData?.detail === "string" ? rawErrorData.detail : rawErrorData?.detail?.message) ||
          rawErrorData?.error?.message ||
          "Sign-in details incorrect. Please check your credentials.";
        const isAuth = this.isAuthEndpoint(endpoint);
        const code = isAuth ? "INVALID_CREDENTIALS" : (response.status === 401 ? "UNAUTHORIZED" : "FORBIDDEN");
        throw new ApiError(msg, code, rawErrorData?.error?.fields, rawErrorData?.request_id, response.status);
      }

      if (response.status >= 500) {
        const msg =
          (typeof rawErrorData?.detail === "string" ? rawErrorData.detail : rawErrorData?.detail?.message) ||
          rawErrorData?.error?.message ||
          "Server error occurred. Please try again later.";
        throw new ApiError(msg, "SERVER_ERROR", rawErrorData?.error?.fields, rawErrorData?.request_id, response.status);
      }

      let message = "Request failed";
      if (typeof rawErrorData?.error?.message === "string") {
        message = rawErrorData.error.message;
      } else if (typeof rawErrorData?.detail === "string") {
        message = rawErrorData.detail;
      } else if (typeof rawErrorData?.detail?.message === "string") {
        message = rawErrorData.detail.message;
      } else if (Array.isArray(rawErrorData?.detail)) {
        message = rawErrorData.detail.map((d: any) => d?.msg || (typeof d === "string" ? d : JSON.stringify(d))).join(", ");
      } else if (typeof rawErrorData?.message === "string") {
        message = rawErrorData.message;
      } else if (rawErrorData?.detail && typeof rawErrorData.detail === "object") {
        message = rawErrorData.detail.message || JSON.stringify(rawErrorData.detail);
      } else {
        message = `Request failed with status ${response.status}`;
      }

      const code = rawErrorData?.error?.code || rawErrorData?.detail?.code || (rawErrorData?.detail ? "HTTP_EXCEPTION" : "HTTP_ERROR");

      const fields = rawErrorData?.error?.fields;
      const requestId = rawErrorData?.request_id;

      throw new ApiError(message, code, fields, requestId, response.status);

    }

    if (response.status === 204) {
      return {} as T;
    }

    const json = await response.json();
    return json.data !== undefined ? json.data : json;
  }

  public patch<T>(endpoint: string, body?: any, options: RequestInit = {}): Promise<T> {
    return this.request<T>(endpoint, {
      ...options,
      method: "PATCH",
      body: body ? JSON.stringify(body) : undefined,
    });
  }

  // Auth
  login(identifier: string, password: string) {
    return this.request<any>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ identifier, password }),
    });
  }

  changePassword(oldPassword: string, newPassword: string) {
    return this.request<any>("/auth/change-password", {
      method: "POST",
      body: JSON.stringify({ old_password: oldPassword, new_password: newPassword }),
    });
  }

  updateUserPreferences(preferredLanguage: string) {
    return this.patch<any>("/auth/me/preferences", {
      preferred_language: preferredLanguage,
    });
  }

  getCurrentUser() {
    return this.request<any>("/auth/me");
  }

  // Voice & Speech Synthesis
  synthesizeSpeech(data: {
    text: string;
    language_code: string;
    context?: string;
    speaker?: string;
  }): Promise<{
    audio_base64: string;
    mime_type: string;
    language_code: string;
    provider: string;
    model: string;
  }> {
    return this.request<any>("/voice/tts", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  getVoiceDiagnostics(): Promise<{
    sarvam_key_configured: boolean;
    tts_enabled: boolean;
    model: string;
    speaker: string;
    api_connectivity: string;
    last_status_code?: number | null;
  }> {
    return this.request<any>("/voice/diagnostics", {
      method: "GET",
    });
  }

  // Citizen
  createCitizenCase(data: any) {
    return this.request<any>("/citizen/cases", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  getCitizenCase(caseId: string) {
    return this.request<any>(`/citizen/cases/${caseId}`);
  }

  // ASHA
  getAshaDashboard() {
    return this.request<any>("/asha/dashboard");
  }

  getAshaCase(caseId: string) {
    return this.request<any>(`/asha/cases/${caseId}`);
  }

  getAshaTasks() {
    return this.request<any>("/asha/tasks");
  }

  acknowledgeAshaCase(caseId: string, idempotencyKey?: string) {
    const headers: Record<string, string> = {};
    if (idempotencyKey) headers["Idempotency-Key"] = idempotencyKey;
    return this.request<any>(`/asha/cases/${caseId}/acknowledge`, {
      method: "POST",
      headers,
    });
  }

  recordContactResult(caseId: string, data: any) {
    return this.request<any>(`/asha/cases/${caseId}/contact-result`, {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  addAshaCaseSymptoms(caseId: string, data: { symptoms: string[]; onset_duration?: string; severity?: string; notes?: string; followup_id?: string }, idempotencyKey?: string) {
    const headers: Record<string, string> = {};
    if (idempotencyKey) headers["Idempotency-Key"] = idempotencyKey;
    return this.request<any>(`/asha/cases/${encodeURIComponent(caseId)}/symptoms`, {
      method: "POST",
      headers,
      body: JSON.stringify(data),
    });
  }

  recordAshaCaseVitals(caseId: string, data: { systolic_bp?: number; diastolic_bp?: number; spo2?: number; pulse?: number; temperature_c?: number; weight_kg?: number; glucose_mg_dl?: number; respiratory_rate?: number; notes?: string; followup_id?: string }, idempotencyKey?: string) {
    const headers: Record<string, string> = {};
    if (idempotencyKey) headers["Idempotency-Key"] = idempotencyKey;
    return this.request<any>(`/asha/cases/${encodeURIComponent(caseId)}/vitals`, {
      method: "POST",
      headers,
      body: JSON.stringify(data),
    });
  }

  getAshaCaseVitalsTrends(caseId: string) {
    return this.request<any>(`/asha/cases/${encodeURIComponent(caseId)}/vitals/trends`);
  }

  referAshaCase(caseId: string, data: { facility_id: string; urgency?: string; reason: string; transport_required?: boolean }, idempotencyKey?: string) {
    const headers: Record<string, string> = {};
    if (idempotencyKey) headers["Idempotency-Key"] = idempotencyKey;
    return this.request<any>(`/asha/cases/${encodeURIComponent(caseId)}/refer`, {
      method: "POST",
      headers,
      body: JSON.stringify(data),
    });
  }

  getAshaFollowups(params?: { status_filter?: string; source_filter?: string; query_str?: string }) {
    const q = new URLSearchParams();
    if (params?.status_filter) q.set("status_filter", params.status_filter);
    if (params?.source_filter) q.set("source_filter", params.source_filter);
    if (params?.query_str) q.set("query_str", params.query_str);
    const qs = q.toString();
    return this.request<any>(`/asha/followups${qs ? `?${qs}` : ""}`);
  }

  getAshaFollowup(followupId: string) {
    return this.request<any>(`/asha/followups/${encodeURIComponent(followupId)}`);
  }

  startAshaFollowup(followupId: string, idempotencyKey?: string) {
    const headers: Record<string, string> = {};
    if (idempotencyKey) headers["Idempotency-Key"] = idempotencyKey;
    return this.request<any>(`/asha/followups/${encodeURIComponent(followupId)}/start`, {
      method: "POST",
      headers,
    });
  }

  draftAshaFollowup(followupId: string, data: any) {
    return this.request<any>(`/asha/followups/${encodeURIComponent(followupId)}/draft`, {
      method: "PATCH",
      body: JSON.stringify(data),
    });
  }

  completeAshaFollowup(followupId: string, data: any, idempotencyKey?: string) {
    const headers: Record<string, string> = {};
    if (idempotencyKey) headers["Idempotency-Key"] = idempotencyKey;
    return this.request<any>(`/asha/followups/${encodeURIComponent(followupId)}/complete`, {
      method: "POST",
      headers,
      body: JSON.stringify(data),
    });
  }

  rescheduleAshaFollowup(followupId: string, data: { new_due_date: string; reason: string }, idempotencyKey?: string) {
    const headers: Record<string, string> = {};
    if (idempotencyKey) headers["Idempotency-Key"] = idempotencyKey;
    return this.request<any>(`/asha/followups/${encodeURIComponent(followupId)}/reschedule`, {
      method: "POST",
      headers,
      body: JSON.stringify(data),
    });
  }

  escalateAshaFollowup(followupId: string, data: { reason: string; urgency?: string; notes?: string }, idempotencyKey?: string) {
    const headers: Record<string, string> = {};
    if (idempotencyKey) headers["Idempotency-Key"] = idempotencyKey;
    return this.request<any>(`/asha/followups/${encodeURIComponent(followupId)}/escalate`, {
      method: "POST",
      headers,
      body: JSON.stringify(data),
    });
  }

  submitFieldVisit(caseIdOrPayload: string | any, dataOrIdempotency?: any, maybeIdempotency?: string) {
    if (typeof caseIdOrPayload === "string") {
      const headers: Record<string, string> = {};
      if (maybeIdempotency) headers["Idempotency-Key"] = maybeIdempotency;
      return this.request<any>(`/asha/cases/${caseIdOrPayload}/visit`, {
        method: "POST",
        headers,
        body: JSON.stringify(dataOrIdempotency),
      });
    } else {
      const caseId = caseIdOrPayload.case_id || "default";
      const headers: Record<string, string> = {};
      if (typeof dataOrIdempotency === "string") headers["Idempotency-Key"] = dataOrIdempotency;
      return this.request<any>(`/asha/cases/${caseId}/visit`, {
        method: "POST",
        headers,
        body: JSON.stringify(caseIdOrPayload),
      });
    }
  }

  getPatientRegistrationOptions() {
    return this.request<any>("/asha/patient-registration/options");
  }

  checkDuplicatePatient(data: any) {
    return this.request<any>("/asha/patient-registration/duplicate-check", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  checkDuplicatePatients(data: any) {
    return this.checkDuplicatePatient(data);
  }

  submitPatientRegistration(data: any, idempotencyKey?: string) {
    const headers: Record<string, string> = {};
    if (idempotencyKey) {
      headers["Idempotency-Key"] = idempotencyKey;
    }
    return this.request<any>("/asha/patient-registration", {
      method: "POST",
      headers,
      body: JSON.stringify(data),
    });
  }

  registerPatient(data: any, idempotencyKey?: string) {
    return this.submitPatientRegistration(data, idempotencyKey);
  }

  voiceStructuredIntake(data: any) {
    return this.request<any>("/voice/structured-intake", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  getBeneficiaryDirectory(search?: string, village_id?: string) {
    const params = new URLSearchParams();
    if (search) params.append("search", search);
    if (village_id) params.append("village_id", village_id);
    const q = params.toString();
    return this.request<any>(`/asha/patients${q ? `?${q}` : ""}`);
  }

  // Doctor
  getDoctorDashboard() {
    return this.request<any>("/doctor/dashboard");
  }

  getDoctorReferralQueue(params?: { urgency?: string; priority?: string; status_filter?: string; sort_by?: string; search?: string; page?: number; limit?: number }) {
    const p = new URLSearchParams();
    if (params?.urgency || params?.priority) p.append("urgency", (params.urgency || params.priority)!);
    if (params?.status_filter) p.append("status_filter", params.status_filter);
    if (params?.sort_by) p.append("sort_by", params.sort_by);
    if (params?.search) p.append("search", params.search);
    if (params?.page) p.append("page", params.page.toString());
    if (params?.limit) p.append("limit", params.limit.toString());
    const q = p.toString();
    return this.request<any>(`/doctor/referrals${q ? `?${q}` : ""}`);
  }

  getDoctorReferralsSummary(): Promise<DoctorReferralsSummaryDTO> {
    return this.request<DoctorReferralsSummaryDTO>("/doctor/referrals/summary");
  }

  getDoctorReferrals(params?: any) {
    return this.getDoctorReferralQueue(params);
  }

  acknowledgeDoctorReferral(referralId: string) {
    return this.request<any>(`/doctor/referrals/${encodeURIComponent(referralId)}/acknowledge`, {
      method: "POST",
    });
  }

  markTransportArranged(referralId: string) {
    return this.request<any>(`/doctor/referrals/${encodeURIComponent(referralId)}/transport`, {
      method: "POST",
    });
  }

  markPatientArrived(referralId: string) {
    return this.request<any>(`/doctor/referrals/${encodeURIComponent(referralId)}/arrive`, {
      method: "POST",
    });
  }

  getDoctorCaseDetails(caseId: string) {
    return this.request<any>(`/doctor/referrals/${caseId}`);
  }

  getDoctorCaseTimeline(caseId: string) {
    return this.request<any>(`/doctor/cases/${encodeURIComponent(caseId)}/timeline`);
  }

  getClinicalWorkSummary() {
    return this.request<any>("/doctor/dashboard/clinical-work");
  }

  getDoctorConsultations(params?: { status_filter?: string; status?: string }) {
    const p = new URLSearchParams();
    const st = params?.status_filter || params?.status;
    if (st) p.append("status_filter", st);
    const q = p.toString();
    return this.request<any>(`/doctor/consultations${q ? `?${q}` : ""}`);
  }

  getDoctorInvestigations(params?: { status_filter?: string; status?: string; category?: string; priority?: string; search?: string; sort_by?: string; page?: number; limit?: number }) {
    const p = new URLSearchParams();
    const st = params?.status_filter || params?.status;
    if (st) p.append("status_filter", st);
    if (params?.category) p.append("category", params.category);
    if (params?.priority) p.append("priority", params.priority);
    if (params?.search) p.append("search", params.search);
    if (params?.sort_by) p.append("sort_by", params.sort_by);
    if (params?.page) p.append("page", String(params.page));
    if (params?.limit) p.append("limit", String(params.limit));
    const q = p.toString();
    return this.request<any>(`/doctor/investigations${q ? `?${q}` : ""}`);
  }

  getDoctorInvestigationsSummary() {
    return this.request<any>("/doctor/investigations/summary");
  }

  getInvestigation(investigationId: string) {
    return this.request<any>(`/doctor/investigations/${encodeURIComponent(investigationId)}`);
  }

  getDoctorInvestigation(investigationId: string) {
    return this.getInvestigation(investigationId);
  }

  getDoctorInvestigationDetail(investigationId: string) {
    return this.getInvestigation(investigationId);
  }

  createInvestigationOrder(data: any) {
    return this.request<any>("/doctor/investigations", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  collectInvestigationSample(investigationId: string, data: any) {
    return this.request<any>(`/doctor/investigations/${encodeURIComponent(investigationId)}/collect`, {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  recordSampleCollection(investigationId: string, data: any) {
    return this.collectInvestigationSample(investigationId, data);
  }

  enterInvestigationResult(investigationId: string, data: any) {
    return this.request<any>(`/doctor/investigations/${encodeURIComponent(investigationId)}/result`, {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  acknowledgeCriticalResult(investigationId: string, data?: any) {
    return this.request<any>(`/doctor/investigations/${encodeURIComponent(investigationId)}/acknowledge-critical`, {
      method: "POST",
      body: JSON.stringify(data || {}),
    });
  }

  acknowledgeInvestigationCritical(investigationId: string, data?: any) {
    return this.acknowledgeCriticalResult(investigationId, data);
  }

  reviewInvestigationResult(investigationId: string, data?: any) {
    const payload = typeof data === "string" ? { notes: data, review_note: data, outcome: "NO_CHANGE" } : (data || { outcome: "NO_CHANGE", review_note: "Normal findings" });
    return this.request<any>(`/doctor/investigations/${encodeURIComponent(investigationId)}/review`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  }

  requestInvestigationRecollection(investigationId: string, data: string | {
    sample_id?: string;
    reason_code?: string;
    reason_note?: string;
    reason?: string;
    priority?: string;
    due_at?: string;
    collection_location?: string;
    assign_asha_assistance?: boolean;
  }) {
    const payload = typeof data === "string" ? { reason_code: "SAMPLE_REJECTED", reason_note: data } : data;
    return this.request<any>(`/doctor/investigations/${encodeURIComponent(investigationId)}/request-recollection`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  }

  cancelInvestigationOrder(investigationId: string, reason: string) {
    return this.request<any>(`/doctor/investigations/${encodeURIComponent(investigationId)}/cancel`, {
      method: "POST",
      body: JSON.stringify({ reason }),
    });
  }

  // Citizen Investigation Methods
  getCitizenInvestigations() {
    return this.request<any>("/citizen/investigations");
  }

  getCitizenInvestigationInstructions(investigationId: string) {
    return this.request<any>(`/citizen/investigations/${encodeURIComponent(investigationId)}/instructions`);
  }

  acknowledgeCitizenInvestigationInstruction(investigationId: string, data?: any) {
    return this.request<any>(`/citizen/investigations/${encodeURIComponent(investigationId)}/acknowledge`, {
      method: "POST",
      body: JSON.stringify(data || {}),
    });
  }

  // ASHA Investigation Task Methods
  getAshaInvestigationTasks(params?: { status_filter?: string }) {
    const p = new URLSearchParams();
    if (params?.status_filter) p.append("status_filter", params.status_filter);
    const q = p.toString();
    return this.request<any>(`/asha/investigation-tasks${q ? `?${q}` : ""}`);
  }

  submitAshaInvestigationContact(taskId: string, data: any) {
    return this.request<any>(`/asha/investigation-tasks/${encodeURIComponent(taskId)}/contact-result`, {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  submitAshaInvestigationAttendance(taskId: string, data: any) {
    return this.request<any>(`/asha/investigation-tasks/${encodeURIComponent(taskId)}/attendance`, {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  escalateAshaInvestigationTask(taskId: string, data: any) {
    return this.request<any>(`/asha/investigation-tasks/${encodeURIComponent(taskId)}/escalate`, {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  getDoctorFollowups(params?: { status?: string; status_filter?: string; query?: string; priority?: string; village?: string; page?: number; limit?: number }) {
    const p = new URLSearchParams();
    const st = params?.status_filter || params?.status;
    if (st) p.append("status_filter", st);
    if (params?.query) p.append("query_str", params.query);
    if (params?.priority) p.append("priority_filter", params.priority);
    if (params?.village) p.append("village_filter", params.village);
    if (params?.page) p.append("page", String(params.page));
    if (params?.limit) p.append("limit", String(params.limit));
    const q = p.toString();
    return this.request<any>(`/doctor/followups${q ? `?${q}` : ""}`);
  }

  getDoctorFollowupDetail(followupId: string) {
    return this.request<any>(`/doctor/followups/${encodeURIComponent(followupId)}`);
  }

  getDoctorFollowUpDetail(followupId: string) {
    return this.getDoctorFollowupDetail(followupId);
  }

  reviewAshaFollowup(followupId: string, action = "MARK_REVIEWED", notes?: string) {
    return this.request<any>(`/doctor/followups/${encodeURIComponent(followupId)}/review`, {
      method: "POST",
      body: JSON.stringify({ action, notes, review_notes: notes }),
    });
  }

  reviewDoctorFollowup(followupId: string, data: any) {
    return this.request<any>(`/doctor/followups/${encodeURIComponent(followupId)}/review`, {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  rescheduleDoctorFollowup(followupId: string, data: any) {
    return this.request<any>(`/doctor/followups/${encodeURIComponent(followupId)}/reschedule`, {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  cancelDoctorFollowup(followupId: string, data: { reason: string }) {
    return this.request<any>(`/doctor/followups/${encodeURIComponent(followupId)}/cancel`, {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  recordAshaContact(followupId: string) {
    return this.request<any>(`/doctor/followups/${encodeURIComponent(followupId)}/contact-asha`, {
      method: "POST",
    });
  }

  getDoctorFollowupsSummary() {
    return this.request<any>("/doctor/followups/summary");
  }

  acknowledgeDoctorFollowup(followupId: string, notes?: string) {
    return this.request<any>(`/doctor/followups/${encodeURIComponent(followupId)}/acknowledge`, {
      method: "POST",
      body: JSON.stringify({ notes }),
    });
  }

  updateDoctorFollowupDirective(followupId: string, data: any) {
    return this.request<any>(`/doctor/followups/${encodeURIComponent(followupId)}/directive`, {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  resolveDoctorFollowup(followupId: string, data: any) {
    return this.request<any>(`/doctor/followups/${encodeURIComponent(followupId)}/resolve`, {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  requestRepeatVitals(followupId: string, data: any) {
    return this.request<any>(`/doctor/followups/${encodeURIComponent(followupId)}/request-repeat`, {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  getDoctorRecentActivity(params?: { limit?: number; offset?: number }) {
    const p = new URLSearchParams();
    if (params?.limit) p.append("limit", String(params.limit));
    if (params?.offset) p.append("offset", String(params.offset));
    const q = p.toString();
    return this.request<any>(`/doctor/dashboard/recent-activity${q ? `?${q}` : ""}`);
  }

  getDoctorPatientsSummary() {
    return this.request<any>("/doctor/patients/summary");
  }

  getDoctorPatients(params?: {
    filter?: string;
    category?: string;
    village?: string;
    asha_id?: string;
    search?: string;
    sort_by?: string;
    page?: number;
    page_size?: number;
  }) {
    const p = new URLSearchParams();
    if (params?.filter) p.append("filter", params.filter);
    if (params?.category) p.append("category", params.category);
    if (params?.village) p.append("village", params.village);
    if (params?.asha_id) p.append("asha_id", params.asha_id);
    if (params?.search) p.append("search", params.search);
    if (params?.sort_by) p.append("sort_by", params.sort_by);
    if (params?.page) p.append("page", String(params.page));
    if (params?.page_size) p.append("page_size", String(params.page_size));
    const q = p.toString();
    return this.request<any>(`/doctor/patients${q ? `?${q}` : ""}`);
  }

  getPatientRecord(citizenId: string) {
    return this.request<any>(`/doctor/patients/${encodeURIComponent(citizenId)}`);
  }

  recordDoctorPHCMeasurement(citizenId: string, data: { systolic_bp?: number; diastolic_bp?: number; spo2?: number; pulse?: number; temperature_c?: number }) {
    return this.request<any>(`/doctor/patients/${encodeURIComponent(citizenId)}/measurements`, {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  recordDoctorContactAttempt(citizenId: string, data: { target?: string; outcome?: string; notes?: string }) {
    return this.request<any>(`/doctor/patients/${encodeURIComponent(citizenId)}/contact-attempt`, {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  requestDoctorDemographicUpdate(citizenId: string, data: { corrections?: Record<string, any>; verification_note?: string }) {
    return this.request<any>(`/doctor/patients/${encodeURIComponent(citizenId)}/request-demographic-update`, {
      method: "POST",
      body: JSON.stringify(data),
    });
  }


  getDoctorActivityList(params?: {
    event_type_filter?: string;
    start_date?: string;
    end_date?: string;
    search_query?: string;
    page?: number;
    limit?: number;
  }) {
    const p = new URLSearchParams();
    if (params?.event_type_filter) p.append("event_type_filter", params.event_type_filter);
    if (params?.start_date) p.append("start_date", params.start_date);
    if (params?.end_date) p.append("end_date", params.end_date);
    if (params?.search_query) p.append("search_query", params.search_query);
    if (params?.page) p.append("page", String(params.page));
    if (params?.limit) p.append("limit", String(params.limit));
    const q = p.toString();
    return this.request<any>(`/doctor/activity${q ? `?${q}` : ""}`);
  }

  getEscalations(params?: { status?: string }) {
    const p = new URLSearchParams();
    if (params?.status) p.append("status_filter", params.status);
    const q = p.toString();
    return this.request<any>(`/doctor/escalations${q ? `?${q}` : ""}`);
  }

  getEscalation(escalationId: string) {
    return this.request<any>(`/doctor/escalations/${encodeURIComponent(escalationId)}`);
  }

  acknowledgeEscalation(escalationId: string) {
    return this.request<any>(`/doctor/escalations/${encodeURIComponent(escalationId)}/acknowledge`, {
      method: "POST",
    });
  }

  assignEscalationAction(escalationId: string, data: { action_type: string; action_notes: string }) {
    return this.request<any>(`/doctor/escalations/${encodeURIComponent(escalationId)}/action`, {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  resolveEscalation(escalationId: string, data: { resolution_notes: string; resolution_outcome: string }) {
    return this.request<any>(`/doctor/escalations/${encodeURIComponent(escalationId)}/resolve`, {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  callAshaOutcome(escalationId: string, notes?: string) {
    return this.request<any>(`/doctor/escalations/${encodeURIComponent(escalationId)}/call-asha`, {
      method: "POST",
      body: JSON.stringify({ notes }),
    });
  }

  getClinicalEvidence(caseIdOrQuery: string | any) {
    if (typeof caseIdOrQuery === "string") {
      return this.request<any>(`/clinical/evidence/${caseIdOrQuery}`);
    }
    return this.request<any>(`/clinical/evidence`, {
      method: "POST",
      body: JSON.stringify(caseIdOrQuery),
    });
  }



  getConsultationById(consultationId: string) {
    return this.request<any>(`/doctor/consultations/${consultationId}`);
  }

  completeConsultation(data: any) {
    return this.request<any>("/doctor/consultations", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  requestMissingInfo(caseId: string, infoRequested: string) {
    return this.request<any>(`/doctor/referrals/${caseId}/request-info`, {
      method: "POST",
      body: JSON.stringify({ info_requested: infoRequested }),
    });
  }

  recordDoctorVitals(caseId: string, vitals: any) {
    return this.request<any>(`/doctor/consultations/record-vitals`, {
      method: "POST",
      body: JSON.stringify({ case_id: caseId, ...vitals }),
    });
  }

  acknowledgeReferral(caseOrReferralId: string) {
    return this.request<any>(`/doctor/referrals/${caseOrReferralId}/acknowledge`, {
      method: "POST",
    });
  }



  acknowledgeDoctorEscalation(followupId: string) {
    return this.request<any>(`/doctor/escalations/${followupId}/acknowledge`, {
      method: "POST",
    });
  }

  submitConsultation(referralId: string, data: any) {
    return this.request<any>(`/doctor/referrals/${referralId}/consultation`, {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  submitDoctorConsultation(data: any) {
    return this.request<any>("/doctor/consultations", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  createReferral(caseId: string, data: any, idempotencyKey?: string) {
    const headers: Record<string, string> = {};
    if (idempotencyKey) headers["Idempotency-Key"] = idempotencyKey;
    return this.request<any>(`/asha/cases/${caseId}/referral`, {
      method: "POST",
      headers,
      body: JSON.stringify(data),
    });
  }

  // Admin
  getAdminDashboard() {
    return this.request<any>("/admin/dashboard");
  }

  getAdminStaffList(params?: { search?: string; role?: string; status?: string; facility_id?: string; page?: number; limit?: number }) {
    const searchParams = new URLSearchParams();
    if (params?.search) searchParams.append("search", params.search);
    if (params?.role) searchParams.append("role", params.role);
    if (params?.status) searchParams.append("status", params.status);
    if (params?.facility_id) searchParams.append("facility_id", params.facility_id);
    if (params?.page) searchParams.append("page", String(params.page));
    if (params?.limit) searchParams.append("limit", String(params.limit));

    const qs = searchParams.toString();
    return this.request<any>(`/admin/staff${qs ? `?${qs}` : ""}`);
  }

  createStaff(data: any) {
    return this.request<any>("/admin/staff", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  getStaffDetail(staffId: string) {
    return this.request<any>(`/admin/staff/${encodeURIComponent(staffId)}`);
  }

  updateStaff(staffId: string, data: any) {
    return this.request<any>(`/admin/staff/${encodeURIComponent(staffId)}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    });
  }

  suspendStaff(staffId: string, reason?: string) {
    return this.request<any>(`/admin/staff/${encodeURIComponent(staffId)}/suspend`, {
      method: "POST",
      body: JSON.stringify({ reason: reason || "Administrative suspension" }),
    });
  }

  reactivateStaff(staffId: string) {
    return this.request<any>(`/admin/staff/${encodeURIComponent(staffId)}/reactivate`, {
      method: "POST",
    });
  }

  transferStaff(staffId: string, data: any) {
    return this.request<any>(`/admin/staff/${encodeURIComponent(staffId)}/transfer`, {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  resetStaffPassword(staffId: string) {
    return this.request<any>(`/admin/staff/${encodeURIComponent(staffId)}/reset-password`, {
      method: "POST",
    });
  }


  getAdminReferralAnalytics() {
    return this.request<any>("/admin/referrals/analytics");
  }

  getReferralAnalytics() {
    return this.getAdminReferralAnalytics();
  }

  getAdminSchemeAnalytics() {
    return this.request<any>("/admin/schemes/analytics");
  }

  getSchemeAnalytics() {
    return this.getAdminSchemeAnalytics();
  }

  getAdminSystemHealth() {
    return this.request<any>("/admin/system-health");
  }

  getSystemHealth() {
    return this.getAdminSystemHealth();
  }

  getIntegrationsHealth() {
    return this.request<any>("/admin/system-health");
  }

  getAiMetrics() {
    return this.request<any>("/admin/ai-governance");
  }

  // Common / Case Details & Timeline
  getCaseDetails(caseId: string) {
    return this.request<any>(`/cases/${caseId}`);
  }

  getCaseTimeline(caseId: string) {
    return this.request<any>(`/asha/cases/${caseId}/timeline`);
  }

  // Doctor Reports API Methods
  getDoctorReportsOverview(filters?: Record<string, any>) {
    return this.get<any>("/reports/overview", filters);
  }

  getDoctorReferralsReport(filters?: Record<string, any>) {
    return this.get<any>("/reports/referrals", filters);
  }

  getDoctorConsultationsReport(filters?: Record<string, any>) {
    return this.get<any>("/reports/consultations", filters);
  }

  getDoctorPatientsReport(filters?: Record<string, any>) {
    return this.get<any>("/reports/patients", filters);
  }

  getDoctorInvestigationsReport(filters?: Record<string, any>) {
    return this.get<any>("/reports/investigations", filters);
  }

  getDoctorPrescriptionsReport(filters?: Record<string, any>) {
    return this.get<any>("/reports/prescriptions", filters);
  }

  getDoctorFollowupsReport(filters?: Record<string, any>) {
    return this.get<any>("/reports/followups", filters);
  }

  getDoctorMaternalReport(filters?: Record<string, any>) {
    return this.get<any>("/reports/maternal", filters);
  }

  getDoctorChildHealthReport(filters?: Record<string, any>) {
    return this.get<any>("/reports/child-health", filters);
  }

  getDoctorNcdReport(filters?: Record<string, any>) {
    return this.get<any>("/reports/ncd", filters);
  }

  getDoctorSafetyReport(filters?: Record<string, any>) {
    return this.get<any>("/reports/safety", filters);
  }

  getDoctorWorkflowFunnel(filters?: Record<string, any>) {
    return this.get<any>("/reports/workflow-funnel", filters);
  }

  getDoctorPendingWork() {
    return this.get<any>("/reports/pending-work");
  }



  downloadDoctorReportExport(filters?: Record<string, any>, format = "csv") {
    const p = new URLSearchParams();
    p.append("format", format);
    if (filters) {
      Object.entries(filters).forEach(([k, v]) => {
        if (v !== undefined && v !== null && v !== "") {
          p.append(k, String(v));
        }
      });
    }
    const token = this.token || (typeof localStorage !== "undefined" ? localStorage.getItem("aarogya_token") : null);
    const url = `${this.baseUrl}/reports/export?${p.toString()}`;
    return fetch(url, {
      method: "GET",
      headers: {
        Authorization: `Bearer ${token}`
      }
    });
  }

  // Doctor Alerts API Methods
  getDoctorAlerts(filters?: Record<string, any>) {
    return this.get<any>("/doctor/alerts", filters);
  }

  getDoctorAlertsSummary() {
    return this.get<any>("/doctor/alerts/summary");
  }

  getDoctorAlert(alertId: string) {
    return this.get<any>(`/doctor/alerts/${alertId}`);
  }

  markDoctorAlertSeen(alertId: string) {
    return this.post<any>(`/doctor/alerts/${alertId}/seen`, {});
  }

  acknowledgeDoctorAlert(alertId: string, note?: string) {
    return this.post<any>(`/doctor/alerts/${alertId}/acknowledge`, { note });
  }

  snoozeDoctorAlert(alertId: string, hours: number = 4, reason?: string) {
    return this.post<any>(`/doctor/alerts/${alertId}/snooze`, { hours, reason });
  }

  resolveDoctorAlert(alertId: string, note: string) {
    return this.post<any>(`/doctor/alerts/${alertId}/resolve`, { note });
  }

  dismissDoctorAlert(alertId: string, reason: string) {
    return this.post<any>(`/doctor/alerts/${alertId}/dismiss`, { reason });
  }

  revealDoctorAlertPhone(alertId: string) {
    return this.post<any>(`/doctor/alerts/${alertId}/reveal-phone`, {});
  }

  // Realtime WS Ticket Issuance
  issueRealtimeTicket() {
    return this.request<any>("/realtime/ticket", {
      method: "POST",
    });
  }

  // Voice STT Transcription
  transcribeVoice(audioBase64: string, language: string = "mr-IN", promptContext?: string) {
    return this.request<any>("/voice/transcribe", {
      method: "POST",
      body: JSON.stringify({
        audio_base64: audioBase64,
        language: language,
        prompt_context: promptContext
      }),
    });
  }

  // Scheme Integration Endpoints
  listSchemes() {
    return this.request<any>("/schemes");
  }

  getSchemeDetails(schemeCode: string) {
    return this.request<any>(`/schemes/${schemeCode}`);
  }

  evaluateSchemes(payload: {
    citizen_id?: string | null;
    case_id?: string | null;
    additional_facts?: Record<string, any>;
    locale?: string;
    persist?: boolean;
  }) {
    return this.request<any>("/schemes/evaluate", {
      method: "POST",
      body: JSON.stringify(payload)
    });
  }

  submitSchemeVerification(payload: {
    scheme_id: string;
    citizen_id: string;
    verification_method: string;
    official_reference_number?: string;
    notes?: string;
  }) {
    return this.request<any>("/schemes/verification", {
      method: "POST",
      body: JSON.stringify(payload)
    });
  }

  getSchemeEligibilityProfile(citizenId: string) {
    return this.request<any>(`/schemes/profile/${citizenId}`);
  }

  updateSchemeEligibilityProfile(citizenId: string, facts: Record<string, any>, consentObtained: boolean = true, notes?: string) {
    return this.request<any>(`/schemes/profile/${citizenId}`, {
      method: "POST",
      body: JSON.stringify({ facts, consent_obtained: consentObtained, notes })
    });
  }

  getSchemeMissingQuestionnaire(citizenId: string) {
    return this.request<any>(`/schemes/questionnaire/${citizenId}`);
  }

  getAdminSourceHealth() {
    return this.request<any>("/schemes/admin/source-health");
  }

  // Doctor Consultation Workspace - Waiting Patients & Start/Resume
  getWaitingPatients(params?: { priority?: string; search?: string; sort?: string; page?: number; page_size?: number }) {
    const searchParams = new URLSearchParams();
    if (params?.priority) searchParams.append("priority", params.priority);
    if (params?.search) searchParams.append("search", params.search);
    if (params?.sort) searchParams.append("sort", params.sort);
    if (params?.page) searchParams.append("page", String(params.page));
    if (params?.page_size) searchParams.append("page_size", String(params.page_size));

    const qs = searchParams.toString();
    return this.request<WaitingPatientsResponseDTO>(`/doctor/consultations/waiting${qs ? `?${qs}` : ""}`);
  }

  startOrResumeConsultation(referralIdOrData: string | { referral_id?: string; case_id?: string }, idempotencyKey?: string) {
    const payload = typeof referralIdOrData === "string"
      ? { referral_id: referralIdOrData, idempotency_key: idempotencyKey }
      : { referral_id: referralIdOrData?.referral_id || referralIdOrData?.case_id, idempotency_key: idempotencyKey };

    return this.request<any>("/doctor/consultations/start-or-resume", {
      method: "POST",
      body: JSON.stringify(payload)
    });
  }

  startConsultation(data: { referral_id?: string; case_id?: string }) {
    return this.startOrResumeConsultation(data);
  }

  // Doctor Prescription Module
  getDoctorPrescriptionsSummary() {
    return this.request<any>("/doctor/prescriptions/summary");
  }

  getDoctorPrescriptions(params?: Record<string, any>) {
    return this.get<any>("/doctor/prescriptions", params);
  }

  getDoctorPrescriptionDetail(prescriptionId: string) {
    return this.request<any>(`/doctor/prescriptions/${encodeURIComponent(prescriptionId)}`);
  }

  getDoctorConsultationPrescriptions(consultationId: string) {
    return this.request<any>(`/doctor/consultations/${encodeURIComponent(consultationId)}/prescriptions`);
  }

  createPrescriptionDraft(data: any) {
    return this.request<any>("/doctor/prescriptions/draft", {
      method: "POST",
      body: JSON.stringify(data)
    });
  }

  updatePrescriptionDraft(prescriptionId: string, data: any) {
    return this.request<any>(`/doctor/prescriptions/${encodeURIComponent(prescriptionId)}/draft`, {
      method: "PUT",
      body: JSON.stringify(data)
    });
  }

  validatePrescriptionSafety(prescriptionId: string) {
    return this.request<any>(`/doctor/prescriptions/${encodeURIComponent(prescriptionId)}/validate`, {
      method: "POST"
    });
  }

  signPrescription(prescriptionId: string, data?: any, idempotencyKey?: string) {
    const headers: Record<string, string> = {};
    if (idempotencyKey) {
      headers["Idempotency-Key"] = idempotencyKey;
    }
    return this.request<any>(`/doctor/prescriptions/${encodeURIComponent(prescriptionId)}/sign`, {
      method: "POST",
      headers,
      body: JSON.stringify(data || {})
    });
  }

  amendPrescription(prescriptionId: string, data: any) {
    return this.request<any>(`/doctor/prescriptions/${encodeURIComponent(prescriptionId)}/amend`, {
      method: "POST",
      body: JSON.stringify(data)
    });
  }

  stopPrescriptionItem(prescriptionId: string, itemId: string, data: any) {
    return this.request<any>(`/doctor/prescriptions/${encodeURIComponent(prescriptionId)}/items/${encodeURIComponent(itemId)}/stop`, {
      method: "POST",
      body: JSON.stringify(data)
    });
  }

  cancelPrescription(prescriptionId: string, data: any) {
    return this.request<any>(`/doctor/prescriptions/${encodeURIComponent(prescriptionId)}/cancel`, {
      method: "POST",
      body: JSON.stringify(data)
    });
  }

  assignPrescriptionAdherenceFollowup(prescriptionId: string, data: any) {
    return this.request<any>(`/doctor/prescriptions/${encodeURIComponent(prescriptionId)}/assign-followup`, {
      method: "POST",
      body: JSON.stringify(data)
    });
  }

  getMedicineCatalog(params?: Record<string, any>) {
    return this.get<any>("/doctor/medicine-catalog", params);
  }

  getDoctorPatientPrescriptions(citizenId: string) {
    return this.request<any>(`/doctor/patients/${encodeURIComponent(citizenId)}/prescriptions`);
  }

  // Citizen Prescriptions
  getCitizenPrescriptions() {
    return this.request<any>("/citizen/prescriptions");
  }

  getCitizenPrescriptionDetail(prescriptionId: string) {
    return this.request<any>(`/citizen/prescriptions/${encodeURIComponent(prescriptionId)}`);
  }

  acknowledgeCitizenPrescription(prescriptionId: string, data: any) {
    return this.request<any>(`/citizen/prescriptions/${encodeURIComponent(prescriptionId)}/acknowledge`, {
      method: "POST",
      body: JSON.stringify(data)
    });
  }

  requestHelpCitizenPrescription(prescriptionId: string, data: any) {
    return this.request<any>(`/citizen/prescriptions/${encodeURIComponent(prescriptionId)}/request-help`, {
      method: "POST",
      body: JSON.stringify(data)
    });
  }

  // ASHA Adherence
  getAshaAdherenceFollowups() {
    return this.request<any>("/asha/adherence-followups");
  }

  recordAshaAdherenceOutcome(followUpId: string, data: any) {
    return this.request<any>(`/asha/adherence-followups/${encodeURIComponent(followUpId)}/outcome`, {
      method: "POST",
      body: JSON.stringify(data)
    });
  }

  escalateAshaAdherenceFollowup(followUpId: string, data: any) {
    return this.request<any>(`/asha/adherence-followups/${encodeURIComponent(followUpId)}/escalate`, {
      method: "POST",
      body: JSON.stringify(data)
    });
  }

  // Admin Prescription Analytics
  getAdminPrescriptionAnalytics() {
    return this.request<any>("/admin/analytics/prescriptions");
  }

  // Citizen App API Extensions
  getCitizenHomeSummary() {
    return this.request<any>("/citizen/home-summary");
  }

  transcribeCitizenVoice(data: { audio_base64: string; preferred_language?: string; audio_format?: string; duration_seconds?: number }) {
    return this.request<any>("/citizen/voice/transcribe", {
      method: "POST",
      body: JSON.stringify(data)
    });
  }

  getActiveCitizenChatSession() {
    return this.request<any>("/citizen/chat/session/active");
  }

  getCitizenChatHistory(sessionId: string) {
    return this.request<any>(`/citizen/chat/session/${encodeURIComponent(sessionId)}/history`);
  }

  startCitizenChatSession(data: any) {
    return this.request<any>("/citizen/chat/session", {
      method: "POST",
      body: JSON.stringify(data)
    });
  }

  addCitizenChatMessage(sessionId: string, data: any) {
    return this.request<any>(`/citizen/chat/session/${encodeURIComponent(sessionId)}/message`, {
      method: "POST",
      body: JSON.stringify(data)
    });
  }

  confirmCitizenTranscript(sessionId: string, data: any) {
    return this.request<any>(`/citizen/chat/session/${encodeURIComponent(sessionId)}/confirm-transcript`, {
      method: "POST",
      body: JSON.stringify(data)
    });
  }

  confirmCitizenUnderstanding(sessionId: string, data: any) {
    return this.request<any>(`/citizen/chat/session/${encodeURIComponent(sessionId)}/confirm-understanding`, {
      method: "POST",
      body: JSON.stringify(data)
    });
  }

  createCitizenNeed(data: any) {
    return this.request<any>("/citizen/need", {
      method: "POST",
      body: JSON.stringify(data)
    });
  }

  updateCitizenLanguage(languageCode: string) {
    return this.request<any>("/citizen/profile/language", {
      method: "PATCH",
      body: JSON.stringify({ preferred_language: languageCode })
    });
  }

  getCitizenTimeline(caseId: string) {
    return this.request<any>(`/citizen/cases/${encodeURIComponent(caseId)}/timeline`);
  }

  getCitizenBeneficiaries() {
    return this.request<{ items: any[] }>("/citizen/beneficiaries");
  }

  getCitizenProfile() {
    return this.request<any>("/citizen/profile");
  }

  updateCitizenProfile(data: any) {
    return this.request<any>("/citizen/profile", {
      method: "PATCH",
      body: JSON.stringify(data)
    });
  }

  getCitizenHouseholdMembers() {
    return this.request<any>("/citizen/household");
  }

  addCitizenHouseholdMember(data: any) {
    return this.request<any>("/citizen/household", {
      method: "POST",
      body: JSON.stringify(data)
    });
  }

  getCitizenHouseholdMemberDetail(memberId: string) {
    return this.request<any>(`/citizen/household/${encodeURIComponent(memberId)}`);
  }

  updateCitizenHouseholdMember(memberId: string, data: any) {
    return this.request<any>(`/citizen/household/${encodeURIComponent(memberId)}`, {
      method: "PATCH",
      body: JSON.stringify(data)
    });
  }

  deleteCitizenHouseholdMember(memberId: string) {
    return this.request<any>(`/citizen/household/${encodeURIComponent(memberId)}`, {
      method: "DELETE"
    });
  }

  getHouseholdMembers() {
    return this.request<any>("/citizen/household");
  }

  getCitizenCareTeam() {
    return this.request<any>("/citizen/care-team");
  }

  getCitizenConsents() {
    return this.request<any>("/citizen/consents");
  }

  revokeCitizenConsent(consentId: string, reason?: string) {
    return this.request<any>("/citizen/consents", {
      method: "PATCH",
      body: JSON.stringify({ consent_id: consentId, reason })
    });
  }

  getCitizenLanguagePreference() {
    return this.request<any>("/citizen/preferences/language");
  }

  setCitizenLanguagePreference(preferredLanguage: string) {
    return this.request<any>("/citizen/preferences/language", {
      method: "PATCH",
      body: JSON.stringify({ preferred_language: preferredLanguage })
    });
  }

  getCitizenAbhaLinkStatus() {
    return this.request<any>("/citizen/abha-link-status");
  }

  getCitizenFollowups() {
    return this.request<any>("/citizen/followups");
  }



  getCitizenAppointments() {
    return this.request<any>("/citizen/appointments");
  }

  // --- Speak to Doctor / Teleconsultation API Methods ---
  createDoctorRequestDraft(data: { household_member_id?: string; language_code?: string; mode?: string }) {
    return this.request<any>("/citizen/doctor-requests/draft", {
      method: "POST",
      body: JSON.stringify(data)
    });
  }

  updateDoctorRequestDraft(requestId: string, data: any) {
    return this.request<any>(`/citizen/doctor-requests/${encodeURIComponent(requestId)}/draft`, {
      method: "PATCH",
      body: JSON.stringify(data)
    });
  }

  submitDoctorRequest(requestId: string, data: { idempotency_key?: string; consents?: any }) {
    return this.request<any>(`/citizen/doctor-requests/${encodeURIComponent(requestId)}/submit`, {
      method: "POST",
      body: JSON.stringify(data)
    });
  }

  getDoctorRequest(requestId: string) {
    return this.request<any>(`/citizen/doctor-requests/${encodeURIComponent(requestId)}`);
  }

  getDoctorRequestStatus(requestId: string) {
    return this.request<any>(`/citizen/doctor-requests/${encodeURIComponent(requestId)}/status`);
  }

  cancelDoctorRequest(requestId: string, reason?: string) {
    return this.request<any>(`/citizen/doctor-requests/${encodeURIComponent(requestId)}/cancel`, {
      method: "POST",
      body: JSON.stringify({ reason })
    });
  }

  sendDoctorRequestMessage(requestId: string, message_text: string, client_message_id?: string) {
    return this.request<any>(`/citizen/doctor-requests/${encodeURIComponent(requestId)}/messages`, {
      method: "POST",
      body: JSON.stringify({ message_text, body: message_text, client_message_id })
    });
  }

  // --- Canonical Doctor Chat Advice APIs ---
  getCitizenDoctorRequest(requestId: string) {
    return this.request<any>(`/citizen/doctor/requests/${encodeURIComponent(requestId)}`);
  }

  getCareRequestConversation(requestId: string) {
    return this.request<any>(`/citizen/doctor/requests/${encodeURIComponent(requestId)}`);
  }

  getCareConversationMessages(conversationId: string, after?: string) {
    const qs = after ? `?after=${encodeURIComponent(after)}` : "";
    return this.request<any>(`/care-conversations/${encodeURIComponent(conversationId)}/messages${qs}`);
  }

  postCareConversationMessage(conversationId: string, body: string, client_message_id: string, message_type: string = "TEXT") {
    return this.request<any>(`/care-conversations/${encodeURIComponent(conversationId)}/messages`, {
      method: "POST",
      body: JSON.stringify({ body, client_message_id, message_type })
    });
  }

  getConversationMessages(conversationId: string, after?: string) {
    const qs = after ? `?after=${encodeURIComponent(after)}` : "";
    return this.request<any>(`/care-conversations/${encodeURIComponent(conversationId)}/messages${qs}`);
  }

  postConversationMessage(conversationId: string, body: string, client_message_id: string, message_type: string = "TEXT") {
    return this.request<any>(`/care-conversations/${encodeURIComponent(conversationId)}/messages`, {
      method: "POST",
      body: JSON.stringify({ body, client_message_id, message_type })
    });
  }

  markConversationRead(conversationId: string, up_to_message_id?: string, message_ids?: string[]) {
    return this.request<any>(`/care-conversations/${encodeURIComponent(conversationId)}/read`, {
      method: "POST",
      body: JSON.stringify({ up_to_message_id, message_ids })
    });
  }

  getDoctorChatThread(requestId: string) {
    return this.request<any>(`/citizen/doctor/requests/${encodeURIComponent(requestId)}`);
  }

  getDoctorChatMessages(conversationId: string, after?: string) {
    const qs = after ? `?after=${encodeURIComponent(after)}` : "";
    return this.request<any>(`/care-conversations/${encodeURIComponent(conversationId)}/messages${qs}`);
  }

  sendDoctorChatMessage(conversationId: string, body: string, client_message_id: string, message_type: string = "TEXT") {
    return this.request<any>(`/care-conversations/${encodeURIComponent(conversationId)}/messages`, {
      method: "POST",
      body: JSON.stringify({ body, client_message_id, message_type })
    });
  }

  markDoctorChatRead(conversationId: string, up_to_message_id?: string, message_ids?: string[]) {
    return this.request<any>(`/care-conversations/${encodeURIComponent(conversationId)}/read`, {
      method: "POST",
      body: JSON.stringify({ up_to_message_id, message_ids })
    });
  }

  getDoctorRequestConversation(requestRef: string) {
    return this.request<any>(`/citizen/doctor/requests/${encodeURIComponent(requestRef)}`);
  }

  getDoctorRequestMessages(requestRef: string, after?: string) {
    const qs = after ? `?after=${encodeURIComponent(after)}` : "";
    return this.request<any>(`/care-conversations/${encodeURIComponent(requestRef)}/messages${qs}`);
  }

  sendDoctorRequestChatMessage(requestRef: string, body: string, client_message_id?: string) {
    const cid = client_message_id || `cmsg-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`;
    return this.request<any>(`/care-conversations/${encodeURIComponent(requestRef)}/messages`, {
      method: "POST",
      body: JSON.stringify({ body, client_message_id: cid, message_type: "TEXT" })
    });
  }

  sendDoctorReplyMessage(requestRef: string, body: string, client_message_id?: string) {
    const cid = client_message_id || `dmsg-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`;
    return this.request<any>(`/care-conversations/${encodeURIComponent(requestRef)}/messages`, {
      method: "POST",
      body: JSON.stringify({ body, client_message_id: cid, message_type: "TEXT" })
    });
  }

  markChatMessageRead(messageId: string) {
    return this.request<any>(`/citizen/messages/${encodeURIComponent(messageId)}/read`, {
      method: "PATCH"
    });
  }

  updateDoctorRequestSymptoms(requestId: string, new_symptoms: string[], notes?: string) {
    return this.request<any>(`/citizen/doctor-requests/${encodeURIComponent(requestId)}/update-symptoms`, {
      method: "POST",
      body: JSON.stringify({ new_symptoms, notes })
    });
  }

  getActiveDoctorRequest() {
    return this.request<any>("/citizen/doctor-requests/active/current");
  }



  // --- Citizen Government Benefits & Schemes APIs ---
  getCitizenSchemesHome() {
    return this.request<any>("/citizen/schemes/home");
  }

  getCitizenSchemeCategories() {
    return this.request<any>("/citizen/schemes/categories");
  }

  getCitizenSchemes(params?: { category?: string; category_id?: string; state?: string; query?: string; status?: string; page?: number; page_size?: number }) {
    const searchParams = new URLSearchParams();
    if (params?.category_id) searchParams.append("category_id", params.category_id);
    else if (params?.category) searchParams.append("category_id", params.category);
    if (params?.state) searchParams.append("state", params.state);
    if (params?.query) searchParams.append("query", params.query);
    if (params?.status) searchParams.append("status", params.status);
    if (params?.page) searchParams.append("page", String(params.page));
    if (params?.page_size) searchParams.append("page_size", String(params.page_size));
    const qs = searchParams.toString();
    return this.request<any>(`/citizen/schemes${qs ? `?${qs}` : ""}`);
  }

  getCitizenSchemeDetail(schemeId: string) {
    return this.request<any>(`/citizen/schemes/${encodeURIComponent(schemeId)}`);
  }

  getCitizenSchemeApplicationGuidance(schemeId: string) {
    return this.request<any>(`/citizen/schemes/${encodeURIComponent(schemeId)}/application-guidance`);
  }

  screenCitizenSchemeSingle(schemeId: string, data: { household_member_id?: string; is_pregnant?: boolean; age?: number; additional_facts?: any }) {
    return this.request<any>(`/citizen/schemes/${encodeURIComponent(schemeId)}/screen`, {
      method: "POST",
      body: JSON.stringify(data)
    });
  }

  screenCitizenSchemes(data: { household_member_id?: string; is_pregnant?: boolean; age?: number; additional_facts?: any }) {
    return this.request<any>("/citizen/schemes/screen", {
      method: "POST",
      body: JSON.stringify(data)
    });
  }


  getCitizenScreeningSession(screeningId: string) {
    return this.request<any>(`/citizen/schemes/screenings/${encodeURIComponent(screeningId)}`);
  }

  updateScreeningFacts(screeningId: string, facts: Record<string, any>) {
    return this.request<any>(`/citizen/schemes/screenings/${encodeURIComponent(screeningId)}/facts`, {
      method: "PATCH",
      body: JSON.stringify({ facts })
    });
  }

  saveCitizenScheme(schemeId: string) {
    return this.request<any>(`/citizen/schemes/${encodeURIComponent(schemeId)}/save`, {
      method: "POST"
    });
  }

  unsaveCitizenScheme(schemeId: string) {
    return this.request<any>(`/citizen/schemes/${encodeURIComponent(schemeId)}/save`, {
      method: "DELETE"
    });
  }

  getSavedCitizenSchemes() {
    return this.request<any>("/citizen/saved-schemes");
  }

  requestSchemeAshaAssistance(schemeId: string, data: any) {
    return this.request<any>(`/citizen/schemes/${encodeURIComponent(schemeId)}/asha-assistance`, {
      method: "POST",
      body: JSON.stringify(data)
    });
  }

  getCitizenSchemeAssistance() {
    return this.request<any>("/citizen/scheme-assistance");
  }

  getCitizenSchemeApplications() {
    return this.request<any>("/citizen/scheme-applications");
  }

  getCitizenSchemeHelpCentres() {
    return this.searchCitizenFacilities({ service_type: "AYUSHMAN_HELP_DESK" });
  }

  getCitizenSchemeHelpRequirements(schemeId: string) {
    return this.request<any>(`/citizen/schemes/${encodeURIComponent(schemeId)}/help-requirements`);
  }

  searchCitizenSchemeHelpCentres(schemeId: string, params: {
    scheme_version_id?: string;
    beneficiary_id?: string;
    location: {
      source: string;
      latitude: number;
      longitude: number;
      village?: string;
      pincode?: string;
      accuracy_m?: number;
      captured_at?: string;
    };
    radius_km?: number;
    language?: string;
  }) {
    return this.request<any>(`/citizen/schemes/${encodeURIComponent(schemeId)}/help-centres/search`, {
      method: "POST",
      body: JSON.stringify(params)
    });
  }

  getCitizenSchemeHelpCentreDetail(schemeId: string, facilityId: string, params?: { language?: string; lat?: number; lon?: number }) {
    const searchParams = new URLSearchParams();
    if (params?.language) searchParams.append("language", params.language);
    if (params?.lat !== undefined) searchParams.append("lat", String(params.lat));
    if (params?.lon !== undefined) searchParams.append("lon", String(params.lon));
    const qs = searchParams.toString();
    return this.request<any>(`/citizen/schemes/${encodeURIComponent(schemeId)}/help-centres/${encodeURIComponent(facilityId)}${qs ? `?${qs}` : ""}`);
  }



  // --- Citizen Health Centre & Facility APIs ---
  searchCitizenFacilities(params?: {
    service_code?: string;
    service_type?: string;
    urgency?: string;
    patient_category?: string;
    beneficiary_id?: string;
    active_case_id?: string;
    location?: {
      source?: string;
      village?: string;
      pincode?: string;
      district?: string;
      taluka?: string;
      landmark?: string;
      latitude?: number;
      longitude?: number;
    };
    latitude?: number;
    longitude?: number;
    village_name?: string;
    pincode?: string;
    location_method?: string;
    scheme_code?: string;
    government_only?: boolean;
    max_distance_km?: number;
    radius_km?: number;
    preferred_language?: string;
    locale?: string;
    idempotency_key?: string;
  }) {
    const payload = {
      ...(params || {}),
      max_distance_km: params?.max_distance_km ?? params?.radius_km ?? 25,
      preferred_language: params?.preferred_language ?? params?.locale ?? "en"
    };
    return this.request<any>("/citizen/facilities/search", {
      method: "POST",
      body: JSON.stringify(payload)
    });
  }

  getCitizenSearchById(searchId: string) {
    return this.request<any>(`/citizen/facilities/search/${encodeURIComponent(searchId)}`);
  }


  getCitizenFacilityDetail(facilityId: string, params?: { language?: string; lat?: number; lon?: number }) {
    const searchParams = new URLSearchParams();
    if (params?.language) searchParams.append("language", params.language);
    if (params?.lat) searchParams.append("lat", String(params.lat));
    if (params?.lon) searchParams.append("lon", String(params.lon));
    const qs = searchParams.toString();
    return this.request<any>(`/citizen/facilities/${encodeURIComponent(facilityId)}${qs ? `?${qs}` : ""}`);
  }

  getCitizenFacilityServices(facilityId: string, language?: string) {
    const qs = language ? `?language=${encodeURIComponent(language)}` : "";
    return this.request<any>(`/citizen/facilities/${encodeURIComponent(facilityId)}/services${qs}`);
  }

  getCitizenFacilityHours(facilityId: string) {
    return this.request<any>(`/citizen/facilities/${encodeURIComponent(facilityId)}/hours`);
  }

  getCitizenFacilitySchemes(facilityId: string) {
    return this.request<any>(`/citizen/facilities/${encodeURIComponent(facilityId)}/schemes`);
  }

  selectCitizenFacility(facilityId: string, data?: any) {
    return this.request<any>(`/citizen/facilities/${encodeURIComponent(facilityId)}/select`, {
      method: "POST",
      body: JSON.stringify(data || { selected_facility_id: facilityId })
    });
  }

  logFacilityCallEvent(facilityId: string, data: { dialled_phone: string; event_type?: string }) {
    return this.request<any>(`/citizen/facilities/${encodeURIComponent(facilityId)}/call-events`, {
      method: "POST",
      body: JSON.stringify(data)
    });
  }

  requestFacilityAshaAssistance(facilityId: string, data: {
    beneficiary_id?: string;
    case_id?: string;
    need_id?: string;
    assistance_type?: string;
    assistance_reason: string;
    transport_needed?: boolean;
    preferred_contact?: string;
    citizen_lat?: number;
    citizen_lng?: number;
    citizen_locality?: string;
    consent_given?: boolean;
    idempotency_key?: string;
  }) {
    return this.request<any>(`/citizen/facilities/${encodeURIComponent(facilityId)}/asha-assistance`, {
      method: "POST",
      body: JSON.stringify(data)
    });
  }

  requestFacilityAppointment(facilityId: string, data: {
    beneficiary_id?: string;
    service_code: string;
    service_name: string;
    requested_slot: string;
    notes?: string;
    idempotency_key?: string;
  }) {
    return this.request<any>(`/citizen/facilities/${encodeURIComponent(facilityId)}/appointment-requests`, {
      method: "POST",
      body: JSON.stringify(data)
    });
  }

  getCitizenFacilityAssistance() {
    return this.request<any>("/citizen/facility-assistance");
  }

  getCitizenFacilityAppointments() {
    return this.request<any>("/citizen/facility-appointments");
  }

  geocodeManualLocation(query: string, language?: string) {
    return this.request<any>("/citizen/facilities/geocode", {
      method: "POST",
      body: JSON.stringify({ query, preferred_language: language || "mr-IN" })
    });
  }

  // Structured Care Handoffs & Cross-Role Requests
  resolveCareHandoffCandidate(data: {
    beneficiary_id?: string;
    candidate_name?: string;
    phone?: string;
    abha_reference?: string;
    age?: number;
    gender?: string;
    village_name?: string;
    confirm_register_new_duplicate?: boolean;
  }) {
    return this.request<any>("/citizen/care-handoffs/resolve-candidate", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  previewCareHandoff(data: {
    session_id?: string;
    need_id?: string;
    beneficiary_id?: string;
    request_type?: string;
    requested_channel?: string;
    chief_concern?: string;
    symptoms?: string[];
  }) {
    return this.request<any>("/citizen/care-handoffs/preview", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  createCitizenDoctorRequest(data: any) {
    return this.request<any>("/citizen/doctor/requests", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  createCitizenAshaRequest(data: any) {
    return this.request<any>("/citizen/asha/requests", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  getCitizenServiceRequests() {
    return this.request<any>("/citizen/service-requests");
  }

  getCitizenServiceRequestDetail(requestId: string) {
    return this.request<any>(`/citizen/service-requests/${encodeURIComponent(requestId)}`);
  }

  updateCitizenServiceRequest(requestId: string, data: any) {
    return this.request<any>(`/citizen/service-requests/${encodeURIComponent(requestId)}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    });
  }

  cancelCitizenServiceRequest(requestId: string, reason: string) {
    return this.request<any>(`/citizen/service-requests/${encodeURIComponent(requestId)}/cancel`, {
      method: "POST",
      body: JSON.stringify({ reason }),
    });
  }

  getAshaCitizenRequests() {
    return this.request<any>("/asha/citizen-requests");
  }

  getAshaCitizenRequestDetail(requestId: string) {
    return this.request<any>(`/asha/citizen-requests/${encodeURIComponent(requestId)}`);
  }

  patchAshaCitizenRequestStatus(requestId: string, data: { action: string; [key: string]: any }) {
    return this.request<any>(`/asha/citizen-requests/${encodeURIComponent(requestId)}/status`, {
      method: "PATCH",
      body: JSON.stringify(data),
    });
  }

  acknowledgeAshaCitizenRequest(requestId: string) {
    return this.patchAshaCitizenRequestStatus(requestId, { action: "ACKNOWLEDGE" });
  }

  scheduleAshaCitizenRequest(requestId: string, data: { scheduled_date: string; scheduled_time_slot?: string }) {
    return this.patchAshaCitizenRequestStatus(requestId, { action: "SCHEDULE_VISIT", ...data });
  }

  getDoctorDirectRequests(params?: { status?: string }) {
    return this.get<any>("/doctor/direct-requests", params);
  }

  getDoctorDirectRequestsSummary() {
    return this.get<any>("/doctor/direct-requests/summary");
  }

  getDoctorDirectRequestDetail(requestId: string) {
    return this.get<any>(`/doctor/direct-requests/${encodeURIComponent(requestId)}`);
  }

  patchDoctorDirectRequestStatus(requestId: string, data: { action: string; [key: string]: any }) {
    return this.request<any>(`/doctor/direct-requests/${encodeURIComponent(requestId)}/status`, {
      method: "PATCH",
      body: JSON.stringify(data),
    });
  }

  acceptDoctorDirectRequest(requestId: string) {
    return this.post<any>(`/doctor/direct-requests/${encodeURIComponent(requestId)}/accept`);
  }

  startDoctorDirectConsultation(requestId: string) {
    return this.post<any>(`/doctor/direct-requests/${encodeURIComponent(requestId)}/start`);
  }

  completeDoctorDirectConsultation(requestId: string, data: any) {
    return this.post<any>(`/doctor/direct-requests/${encodeURIComponent(requestId)}/complete`, data);
  }

  declineDoctorDirectRequest(requestId: string, reason: string) {
    return this.post<any>(`/doctor/direct-requests/${encodeURIComponent(requestId)}/decline`, { reason });
  }

  // Location APIs
  reverseGeocodeLocation(latitude: number, longitude: number, language = "mr-IN", accuracy_m?: number | null, captured_at?: string | null) {
    return this.post<any>("/locations/reverse-geocode", {
      latitude,
      longitude,
      accuracy_m,
      captured_at: captured_at || new Date().toISOString(),
      language
    });
  }

  searchLocationsQuery(q: string) {
    return this.get<any>("/locations/search", { q });
  }

  getNearbyFacilities(payload: {
    beneficiary_id?: string | null;
    location: any;
    required_capabilities?: string[];
    emergency?: boolean;
    radius_km?: number;
  }) {
    return this.post<any>("/facilities/nearby", payload);
  }

  updateLocationPreference(data: {
    preferred_source: string;
    manual_village_name?: string | null;
    manual_pincode?: string | null;
  }) {
    return this.request<any>("/users/me/location-preference", {
      method: "PATCH",
      body: JSON.stringify(data)
    });
  }

  getAshaJurisdictions() {
    return this.get<any>("/asha/authorized-jurisdictions");
  }

  getDoctorAuthorizedFacilities() {
    return this.get<any>("/doctor/authorized-facilities");
  }

  // Citizen Authentication & Guest Access APIs
  requestCitizenOtp(phone: string) {
    return this.post<any>("/citizen/auth/otp/request", { phone });
  }

  verifyCitizenOtp(phone: string, otp: string, deviceId?: string, idempotencyKey?: string, otpRequestId?: string) {
    return this.post<any>("/citizen/auth/otp/verify", {
      phone,
      otp,
      device_id: deviceId,
      idempotency_key: idempotencyKey,
      otp_request_id: otpRequestId,
      purpose: "LOGIN"
    });
  }

  refreshCitizenToken(refreshToken?: string) {
    return this.post<any>("/citizen/auth/refresh", refreshToken ? { refresh_token: refreshToken } : {});
  }

  logoutCitizen() {
    return this.post<any>("/citizen/auth/logout");
  }

  getCitizenAuthMe() {
    return this.get<any>("/citizen/auth/me");
  }

  submitCitizenOnboarding(data: any) {
    return this.post<any>("/citizen/onboarding", data);
  }

  getAuthorizedBeneficiaries() {
    return this.get<any>("/citizen/authorized-beneficiaries");
  }

  createGuestSession(locale: string = "mr-IN", deviceHash?: string) {
    return this.post<any>("/citizen/guest/session", { locale, device_hash: deviceHash });
  }

  getGuestSession(sessionId: string) {
    return this.get<any>(`/citizen/guest/session/${sessionId}`);
  }

  migrateGuestSession(sessionId: string, idempotencyKey?: string) {
    return this.post<any>(`/citizen/guest/session/${sessionId}/migrate`, {
      idempotency_key: idempotencyKey
    });
  }
}



export type {
  WaitingPatientItemDTO,
  WaitingPatientsResponseDTO,
  FacilityServiceCode,
  FacilityLocationState,
  FacilitySearchForm,
  FacilitySearchResultItem,
  FacilitySearchEnvelopeData,
  GeocodedLocationResult,
  LocationDataContract,
  LocationSourceEnum,
  NearbyFacilityItemDTO,
  NearbyFacilitiesResponseDTO
} from "@aarogya/shared-types";
export const apiClient = new AarogyaApiClient();



