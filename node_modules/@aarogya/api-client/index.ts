/**
 * Aarogya Sahayak - Centralized API Client with standard error handling & JWT header attachment
 */

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

export class ApiError extends Error {
  code: string;
  fields?: Record<string, string>;
  requestId?: string;

  constructor(message: string, code = "API_ERROR", fields?: Record<string, string>, requestId?: string) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.fields = fields;
    this.requestId = requestId;
  }
}

export class AarogyaApiClient {
  private baseUrl: string;
  private token: string | null = null;

  constructor(baseUrl = "http://localhost:8000/api") {
    this.baseUrl = baseUrl;
  }

  setToken(token: string | null) {
    this.token = token;
  }

  public async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      ...(options.headers as Record<string, string>),
    };

    if (this.token) {
      headers["Authorization"] = `Bearer ${this.token}`;
    }

    const url = `${this.baseUrl}${endpoint.startsWith("/") ? "" : "/"}${endpoint}`;
    
    try {
      const response = await fetch(url, {
        ...options,
        headers,
      });

      if (!response.ok) {
        let errorData: ApiErrorResponse | null = null;
        try {
          errorData = await response.json();
        } catch {
          // Response was not JSON
        }

        const message = errorData?.error?.message || `Request failed with status ${response.status}`;
        const code = errorData?.error?.code || "HTTP_ERROR";
        const fields = errorData?.error?.fields;
        const requestId = errorData?.request_id;

        throw new ApiError(message, code, fields, requestId);
      }

      if (response.status === 204) {
        return {} as T;
      }

      const json = await response.json();
      return json.data !== undefined ? json.data : json;
    } catch (err: any) {
      if (err instanceof ApiError) {
        throw err;
      }
      throw new ApiError(err.message || "Network request failed", "NETWORK_ERROR");
    }
  }

  // Auth
  login(identifier: string, password: string) {
    return this.request<any>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ identifier, password }),
    });
  }

  getCurrentUser() {
    return this.request<any>("/auth/me");
  }

  // Citizen
  createCitizenCase(data: any) {
    return this.request<any>("/citizen/cases", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  getCitizenCases() {
    return this.request<any[]>("/citizen/cases");
  }

  getCitizenCaseDetails(caseId: string) {
    return this.request<any>(`/citizen/cases/${caseId}`);
  }

  // ASHA
  getAshaDashboard() {
    return this.request<any>("/asha/dashboard");
  }

  getAshaTasks(params?: Record<string, string>) {
    const query = params ? `?${new URLSearchParams(params).toString()}` : "";
    return this.request<any[]>(`/asha/tasks${query}`);
  }

  getAshaCase(caseId: string) {
    return this.request<any>(`/asha/cases/${caseId}`);
  }

  acknowledgeAshaCase(caseId: string, idempotencyKey?: string) {
    const headers = idempotencyKey ? { "Idempotency-Key": idempotencyKey } : undefined;
    return this.request<any>(`/asha/cases/${caseId}/acknowledge`, {
      method: "POST",
      headers,
      body: JSON.stringify({ acknowledged_at: new Date().toISOString() }),
    });
  }

  submitFieldVisit(visitData: any, idempotencyKey?: string) {
    const headers = idempotencyKey ? { "Idempotency-Key": idempotencyKey } : undefined;
    return this.request<any>("/asha/visits", {
      method: "POST",
      headers,
      body: JSON.stringify(visitData),
    });
  }

  createReferral(caseId: string, referralData: any, idempotencyKey?: string) {
    const headers = idempotencyKey ? { "Idempotency-Key": idempotencyKey } : undefined;
    return this.request<any>(`/asha/cases/${caseId}/refer`, {
      method: "POST",
      headers,
      body: JSON.stringify(referralData),
    });
  }

  getAshaFollowups(params?: Record<string, string>) {
    const query = params ? `?${new URLSearchParams(params).toString()}` : "";
    return this.request<any[]>(`/asha/followups${query}`);
  }

  completeAshaFollowup(followupId: string, data: any, idempotencyKey?: string) {
    const headers = idempotencyKey ? { "Idempotency-Key": idempotencyKey } : undefined;
    return this.request<any>(`/asha/followups/${followupId}/complete`, {
      method: "POST",
      headers,
      body: JSON.stringify(data),
    });
  }

  getCaseTimeline(caseId: string) {
    return this.request<any[]>(`/asha/cases/${caseId}/timeline`);
  }

  transcribeVoice(preferredLanguage = "mr-IN") {
    return this.request<any>("/asha/voice/transcribe", {
      method: "POST",
      body: JSON.stringify({ preferred_language: preferredLanguage }),
    });
  }

  // Doctor
  getDoctorDashboard() {
    return this.request<any>("/doctor/dashboard");
  }

  getDoctorReferrals(params?: Record<string, string>) {
    const query = params ? `?${new URLSearchParams(params).toString()}` : "";
    return this.request<any[]>(`/doctor/referrals${query}`);
  }

  getDoctorCaseDetails(caseId: string) {
    return this.request<any>(`/doctor/referrals/${caseId}`);
  }

  acknowledgeReferral(caseId: string) {
    return this.request<any>(`/doctor/referrals/${caseId}/acknowledge`, {
      method: "POST",
    });
  }

  completeConsultation(data: any) {
    return this.request<any>("/doctor/consultations", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  // Admin
  getAdminDashboard() {
    return this.request<any>("/admin/dashboard");
  }

  getClusterAlerts() {
    return this.request<any[]>("/admin/cluster-alerts");
  }

  getReferralAnalytics() {
    return this.request<any>("/admin/referral-analytics");
  }

  getSchemeAnalytics() {
    return this.request<any>("/admin/scheme-analytics");
  }

  getSystemHealth() {
    return this.request<any>("/admin/system-health");
  }
}

export const apiClient = new AarogyaApiClient();
