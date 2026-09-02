import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from "react";
import { apiClient, ApiError } from "@aarogya/api-client";
import { UserSession, BeneficiaryOption, GuestSessionDTO } from "@aarogya/shared-types";
import { LanguageService, LanguageCode } from "../services/languageService";

export type CitizenAuthMode =
  | "INITIALIZING"
  | "LANGUAGE_SELECT"
  | "ENTRY_SELECT"
  | "PHONE_ENTRY"
  | "OTP_VERIFY"
  | "ONBOARDING"
  | "SELECT_BENEFICIARY"
  | "GUEST_ACTIVE"
  | "AUTHENTICATED"
  | "ERROR";

export interface PendingProtectedAction {
  actionType: "DOCTOR_CONSULTATION" | "ASHA_ASSISTANCE" | "SAVE_CARE" | "VIEW_RECORDS" | "SCHEME_ASSISTANCE";
  payload?: any;
  onSuccessResume?: (result?: any) => void;
}

interface CitizenAuthContextType {
  authMode: CitizenAuthMode;
  setAuthMode: (mode: CitizenAuthMode) => void;
  user: UserSession | null;
  token: string | null;
  guestSession: GuestSessionDTO | null;
  isAuthenticated: boolean;
  isGuest: boolean;
  isLoading: boolean;
  initError: string | null;
  retryInit: () => void;
  activeBeneficiary: BeneficiaryOption | null;
  authorizedBeneficiaries: BeneficiaryOption[];
  pendingPhone: string;
  maskedPhone: string;
  challengeId: string | null;
  cooldownSeconds: number;
  pendingProtectedAction: PendingProtectedAction | null;
  
  // Actions
  refreshBeneficiaries: () => Promise<void>;
  startPhoneLogin: (phone: string) => Promise<{ success: boolean; error?: string; mockCode?: string }>;
  resendOtp: () => Promise<boolean>;
  submitOtp: (otp: string) => Promise<{ isNewCitizen: boolean; error?: string }>;
  completeOnboarding: (data: any) => Promise<{ success: boolean; error?: string }>;
  continueAsGuest: () => Promise<void>;
  selectBeneficiary: (beneficiary: BeneficiaryOption) => void;
  triggerProtectedAction: (action: PendingProtectedAction) => void;
  cancelProtectedAction: () => void;
  resetOtpFlow: () => void;
  logout: () => Promise<void>;
}

const CitizenAuthContext = createContext<CitizenAuthContextType | undefined>(undefined);

export const CitizenAuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [authMode, setAuthMode] = useState<CitizenAuthMode>("INITIALIZING");
  const [user, setUser] = useState<UserSession | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [guestSession, setGuestSession] = useState<GuestSessionDTO | null>(null);

  const [activeBeneficiary, setActiveBeneficiary] = useState<BeneficiaryOption | null>(null);
  const [authorizedBeneficiaries, setAuthorizedBeneficiaries] = useState<BeneficiaryOption[]>([]);

  const [pendingPhone, setPendingPhone] = useState<string>(() => {
    return sessionStorage.getItem("aarogya_citizen_pending_phone") || "";
  });
  const [maskedPhone, setMaskedPhone] = useState<string>(() => {
    return sessionStorage.getItem("aarogya_citizen_masked_phone") || "";
  });
  const [challengeId, setChallengeId] = useState<string | null>(() => {
    return sessionStorage.getItem("aarogya_citizen_challenge_id") || null;
  });
  const [cooldownSeconds, setCooldownSeconds] = useState<number>(0);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [initError, setInitError] = useState<string | null>(null);
  const [pendingProtectedAction, setPendingProtectedAction] = useState<PendingProtectedAction | null>(null);

  const hasBootstrappedRef = useRef(false);

  // Helper to persist in-flight flow state during refresh
  const saveFlowState = useCallback((mode: CitizenAuthMode, phone?: string, masked?: string, challenge?: string | null) => {
    if (["PHONE_ENTRY", "OTP_VERIFY", "ONBOARDING", "ENTRY_SELECT"].includes(mode)) {
      sessionStorage.setItem("aarogya_citizen_flow_step", mode);
    } else {
      sessionStorage.removeItem("aarogya_citizen_flow_step");
    }
    if (phone !== undefined) {
      if (phone) sessionStorage.setItem("aarogya_citizen_pending_phone", phone);
      else sessionStorage.removeItem("aarogya_citizen_pending_phone");
    }
    if (masked !== undefined) {
      if (masked) sessionStorage.setItem("aarogya_citizen_masked_phone", masked);
      else sessionStorage.removeItem("aarogya_citizen_masked_phone");
    }
    if (challenge !== undefined) {
      if (challenge) sessionStorage.setItem("aarogya_citizen_challenge_id", challenge);
      else sessionStorage.removeItem("aarogya_citizen_challenge_id");
    }
  }, []);

  // Sync token changes to API client & listen for background auto-refresh
  useEffect(() => {
    if (token) {
      apiClient.setToken(token);
    }
    apiClient.setTokenRefreshedCallback((newToken, newUser) => {
      setToken(newToken);
      if (newUser) setUser(newUser);
    });
  }, [token]);

  // Initial Authentication & Route State Resolution (Single-flight bootstrap)
  const initAuth = useCallback(async () => {
    setIsLoading(true);
    setInitError(null);
    try {
      // Step 1: Check if an access token is already persisted in localStorage
      const cachedToken = typeof localStorage !== "undefined" ? localStorage.getItem("aarogya_citizen_token") : null;
      if (cachedToken) {
        apiClient.setToken(cachedToken);
        setToken(cachedToken);
        try {
          const meRes = await apiClient.getCitizenAuthMe();
          const meData = meRes?.data || meRes;
          if (meData?.user) {
            setUser(meData.user);
            const benList: BeneficiaryOption[] = meData.authorized_beneficiaries || [];
            setAuthorizedBeneficiaries(benList);

            const savedBenId = localStorage.getItem("aarogya_citizen_active_ben_id");
            const matched = benList.find(b => b.beneficiaryId === savedBenId);
            if (matched) {
              setActiveBeneficiary(matched);
            } else if (benList.length > 0) {
              setActiveBeneficiary(benList[0]);
              localStorage.setItem("aarogya_citizen_active_ben_id", benList[0].beneficiaryId);
            }

            if (meData.user.preferred_language) {
              LanguageService.saveLocalPreference(meData.user.preferred_language as any);
            }

            localStorage.removeItem("aarogya_guest_session");
            sessionStorage.removeItem("aarogya_citizen_flow_step");
            sessionStorage.removeItem("aarogya_citizen_pending_phone");
            sessionStorage.removeItem("aarogya_citizen_masked_phone");
            sessionStorage.removeItem("aarogya_citizen_challenge_id");
            setGuestSession(null);

            setAuthMode("AUTHENTICATED");
            setIsLoading(false);
            return;
          }
        } catch (meErr: any) {
          if (meErr?.status !== 401 && (meErr?.code === "BACKEND_UNREACHABLE" || meErr?.code === "TIMEOUT" || meErr?.status >= 500)) {
            // Keep authenticated token and show error state or retry
            setInitError(meErr.message || "We could not reach the server. Please check your network connection.");
            setAuthMode("ERROR");
            setIsLoading(false);
            return;
          }
          // If 401, token expired: fall through to attempt refresh
        }
      }

      // Step 2: Try refreshing token via HttpOnly cookie or refresh endpoint
      try {
        const refreshRes = await apiClient.performRefresh();
        if (refreshRes) {
          apiClient.setToken(refreshRes);
          setToken(refreshRes);

          const meRes = await apiClient.getCitizenAuthMe();
          const meData = meRes?.data || meRes;
          if (meData?.user) {
            setUser(meData.user);
            const benList: BeneficiaryOption[] = meData.authorized_beneficiaries || [];
            setAuthorizedBeneficiaries(benList);

            const savedBenId = localStorage.getItem("aarogya_citizen_active_ben_id");
            const matched = benList.find(b => b.beneficiaryId === savedBenId);
            if (matched) {
              setActiveBeneficiary(matched);
            } else if (benList.length > 0) {
              setActiveBeneficiary(benList[0]);
              localStorage.setItem("aarogya_citizen_active_ben_id", benList[0].beneficiaryId);
            }

            if (meData.user.preferred_language) {
              LanguageService.saveLocalPreference(meData.user.preferred_language as any);
            }

            localStorage.removeItem("aarogya_guest_session");
            sessionStorage.removeItem("aarogya_citizen_flow_step");
            sessionStorage.removeItem("aarogya_citizen_pending_phone");
            sessionStorage.removeItem("aarogya_citizen_masked_phone");
            sessionStorage.removeItem("aarogya_citizen_challenge_id");
            setGuestSession(null);

            setAuthMode("AUTHENTICATED");
            setIsLoading(false);
            return;
          }
        }
      } catch (err: any) {
        if (err?.code === "BACKEND_UNREACHABLE" || err?.code === "TIMEOUT" || err?.status >= 500) {
          setInitError(err.message || "We could not restore your session. Please check your network connection.");
          setAuthMode("ERROR");
          setIsLoading(false);
          return;
        }
      }

      // If refresh failed with 401 / no session:
      setToken(null);
      setUser(null);
      apiClient.setToken(null);

      // Check if this is a browser refresh restoring an in-progress flow step
      const savedStep = sessionStorage.getItem("aarogya_citizen_flow_step") as CitizenAuthMode | null;
      if (savedStep && ["PHONE_ENTRY", "OTP_VERIFY", "ONBOARDING", "ENTRY_SELECT"].includes(savedStep)) {
        const savedPhone = sessionStorage.getItem("aarogya_citizen_pending_phone") || "";
        const savedMasked = sessionStorage.getItem("aarogya_citizen_masked_phone") || "";
        const savedChallenge = sessionStorage.getItem("aarogya_citizen_challenge_id") || null;
        if (savedPhone) setPendingPhone(savedPhone);
        if (savedMasked) setMaskedPhone(savedMasked);
        if (savedChallenge) setChallengeId(savedChallenge);
        setAuthMode(savedStep);
        setIsLoading(false);
        return;
      }

      // Active guest session restore check
      const storedGuest = localStorage.getItem("aarogya_guest_session");
      if (storedGuest) {
        try {
          const gObj = JSON.parse(storedGuest);
          setGuestSession(gObj);
          setAuthMode("GUEST_ACTIVE");
          setIsLoading(false);
          return;
        } catch {
          localStorage.removeItem("aarogya_guest_session");
        }
      }

      // Fresh launch without authenticated session -> Language Selection
      setAuthMode("LANGUAGE_SELECT");
    } catch (e: any) {
      setAuthMode("LANGUAGE_SELECT");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!hasBootstrappedRef.current) {
      hasBootstrappedRef.current = true;
      initAuth();
    }
  }, [initAuth]);

  // Re-sync beneficiaries list from backend /auth/me
  const refreshBeneficiaries = useCallback(async () => {
    try {
      const meRes = await apiClient.getCitizenAuthMe();
      const meData = meRes?.data || meRes;
      if (meData?.authorized_beneficiaries) {
        const benList: BeneficiaryOption[] = meData.authorized_beneficiaries || [];
        setAuthorizedBeneficiaries(benList);
        // Reconcile active beneficiary
        const savedBenId = localStorage.getItem("aarogya_citizen_active_ben_id");
        const matched = benList.find((b: BeneficiaryOption) => b.beneficiaryId === savedBenId);
        if (matched) {
          setActiveBeneficiary(matched);
        } else if (benList.length > 0) {
          setActiveBeneficiary(benList[0]);
          localStorage.setItem("aarogya_citizen_active_ben_id", benList[0].beneficiaryId);
        }
      }
    } catch (e) {
      console.error("Failed to refresh beneficiaries", e);
    }
  }, []);

  // Cooldown timer interval
  useEffect(() => {
    if (cooldownSeconds <= 0) return;
    const timer = setInterval(() => {
      setCooldownSeconds((prev) => (prev > 0 ? prev - 1 : 0));
    }, 1000);
    return () => clearInterval(timer);
  }, [cooldownSeconds]);

  // Reset OTP flow state
  const resetOtpFlow = useCallback(() => {
    setPendingPhone("");
    setMaskedPhone("");
    setChallengeId(null);
    setCooldownSeconds(0);
    saveFlowState("ENTRY_SELECT", "", "", null);
    setAuthMode("ENTRY_SELECT");
  }, [saveFlowState]);

  // Custom setAuthMode wrapper that updates session persistence
  const updateAuthMode = useCallback((mode: CitizenAuthMode) => {
    saveFlowState(mode);
    setAuthMode(mode);
  }, [saveFlowState]);

  // Start Phone OTP
  const startPhoneLogin = async (phone: string) => {
    try {
      setPendingPhone(phone);
      saveFlowState("PHONE_ENTRY", phone);
      const res = await apiClient.requestCitizenOtp(phone);
      const data = res?.data || res;
      const masked = data.phone_masked || phone;
      const challenge = data.challenge_id || data.otp_request_id || null;
      setMaskedPhone(masked);
      setChallengeId(challenge);
      setCooldownSeconds(data.cooldown_seconds || 60);
      saveFlowState("OTP_VERIFY", phone, masked, challenge);
      setAuthMode("OTP_VERIFY");
      return { success: true, mockCode: data.mock_code };
    } catch (err: any) {
      let msg = "Failed to send OTP";
      if (typeof err?.message === "string") {
        msg = err.message;
      } else if (typeof err?.fields?.message === "string") {
        msg = err.fields.message;
      } else if (typeof err === "string") {
        msg = err;
      }
      return { success: false, error: msg };
    }
  };

  // Resend OTP
  const resendOtp = async () => {
    if (cooldownSeconds > 0 || !pendingPhone) return false;
    try {
      const res = await apiClient.requestCitizenOtp(pendingPhone);
      const data = res?.data || res;
      const challenge = data.challenge_id || data.otp_request_id || null;
      setChallengeId(challenge);
      saveFlowState("OTP_VERIFY", pendingPhone, maskedPhone, challenge);
      setCooldownSeconds(data.cooldown_seconds || 60);
      return true;
    } catch (e) {
      return false;
    }
  };

  // Submit OTP Verification
  const submitOtp = async (otp: string) => {
    try {
      const res = await apiClient.verifyCitizenOtp(
        pendingPhone,
        otp,
        undefined,
        undefined,
        challengeId || undefined
      );
      const data = res?.data || res;

      if (data.status === "ACCOUNT_RESOLUTION_REQUIRED" || data.error_code === "ACCOUNT_RESOLUTION_REQUIRED") {
        return {
          isNewCitizen: false,
          error: data.message || "Multiple citizen accounts found for this verified number. Please contact administration."
        };
      }

      if (data.onboarding_required || data.is_new_citizen) {
        saveFlowState("ONBOARDING", pendingPhone, maskedPhone, challengeId);
        setAuthMode("ONBOARDING");
        return { isNewCitizen: true };
      }

      if (data.access_token && data.user) {
        setToken(data.access_token);
        setUser(data.user);
        apiClient.setToken(data.access_token);

        const benList = data.authorized_beneficiaries || [];
        setAuthorizedBeneficiaries(benList);
        if (benList.length > 0) {
          const savedBenId = localStorage.getItem("aarogya_citizen_active_ben_id");
          const matched = benList.find((b: BeneficiaryOption) => b.beneficiaryId === savedBenId);
          if (matched) {
            setActiveBeneficiary(matched);
          } else {
            setActiveBeneficiary(benList[0]);
            localStorage.setItem("aarogya_citizen_active_ben_id", benList[0].beneficiaryId);
          }
        }

        // Migrate Guest session if present
        if (guestSession?.session_id) {
          try {
            await apiClient.migrateGuestSession(guestSession.session_id);
          } catch (migErr) {
            console.error("Guest migration error", migErr);
          }
        }
        localStorage.removeItem("aarogya_guest_session");
        sessionStorage.removeItem("aarogya_citizen_flow_step");
        sessionStorage.removeItem("aarogya_citizen_pending_phone");
        sessionStorage.removeItem("aarogya_citizen_masked_phone");
        sessionStorage.removeItem("aarogya_citizen_challenge_id");
        setGuestSession(null);

        // Resume protected action if pending
        if (pendingProtectedAction) {
          const resumeFn = pendingProtectedAction.onSuccessResume;
          setPendingProtectedAction(null);
          setAuthMode("AUTHENTICATED");
          if (resumeFn) resumeFn();
          return { isNewCitizen: false };
        }

        setAuthMode("AUTHENTICATED");
        return { isNewCitizen: false };
      }

      return { isNewCitizen: false, error: "Unexpected verification response" };
    } catch (err: any) {
      const code = err?.code || "";
      const rawMsg = err?.fields?.message || err?.message || "";

      if (code === "NO_ACTIVE_OTP" || rawMsg.includes("No active OTP request found")) {
        return { isNewCitizen: false, error: "No active OTP request found. Please request a new OTP." };
      }
      if (code === "OTP_EXPIRED" || rawMsg.includes("expired")) {
        return { isNewCitizen: false, error: "OTP has expired. Please request a new one." };
      }
      if (code === "OTP_MAX_ATTEMPTS_EXCEEDED" || rawMsg.includes("attempts exceeded") || rawMsg.includes("Limit reached")) {
        return { isNewCitizen: false, error: "Maximum OTP attempts exceeded. Please request a new OTP." };
      }
      if (code === "ACCOUNT_DEACTIVATED" || rawMsg.includes("deactivated")) {
        return { isNewCitizen: false, error: "Account is deactivated. Please contact support." };
      }

      if (
        rawMsg.includes("object has no attribute") ||
        rawMsg.includes("Traceback") ||
        rawMsg.includes("Internal Server Error") ||
        rawMsg.includes("IntegrityError") ||
        rawMsg.includes("KeyError") ||
        rawMsg.includes("TypeError") ||
        err?.status === 500
      ) {
        return { isNewCitizen: false, error: "We could not restore your account. Please try again." };
      }
      const msg = rawMsg || "Invalid OTP. Please try again.";
      return { isNewCitizen: false, error: msg };
    }
  };

  // Complete Onboarding for new mobile number
  const completeOnboarding = async (formData: any) => {
    try {
      const payload = {
        phone: pendingPhone,
        ...formData
      };
      const res = await apiClient.submitCitizenOnboarding(payload);
      const data = res?.data || res;

      if (data?.requires_duplicate_confirmation) {
        const retryRes = await apiClient.submitCitizenOnboarding({
          ...payload,
          confirm_potential_duplicate: true
        });
        const retryData = retryRes?.data || retryRes;
        if (retryData.access_token && retryData.user) {
          setToken(retryData.access_token);
          setUser(retryData.user);
          apiClient.setToken(retryData.access_token);
          const benList = retryData.authorized_beneficiaries || [];
          setAuthorizedBeneficiaries(benList);
          if (benList.length > 0) {
            setActiveBeneficiary(benList[0]);
            localStorage.setItem("aarogya_citizen_active_ben_id", benList[0].beneficiaryId);
          }
          localStorage.removeItem("aarogya_guest_session");
          sessionStorage.removeItem("aarogya_citizen_flow_step");
          sessionStorage.removeItem("aarogya_citizen_pending_phone");
          sessionStorage.removeItem("aarogya_citizen_masked_phone");
          sessionStorage.removeItem("aarogya_citizen_challenge_id");
          setGuestSession(null);
          setAuthMode("AUTHENTICATED");
          return { success: true };
        }
      }

      if (data.access_token && data.user) {
        setToken(data.access_token);
        setUser(data.user);
        apiClient.setToken(data.access_token);
        const benList = data.authorized_beneficiaries || [];
        setAuthorizedBeneficiaries(benList);
        if (benList.length > 0) {
          setActiveBeneficiary(benList[0]);
          localStorage.setItem("aarogya_citizen_active_ben_id", benList[0].beneficiaryId);
        }

        if (guestSession?.session_id) {
          try {
            await apiClient.migrateGuestSession(guestSession.session_id);
          } catch (migErr) {
            console.error("Guest migration error", migErr);
          }
        }
        localStorage.removeItem("aarogya_guest_session");
        sessionStorage.removeItem("aarogya_citizen_flow_step");
        sessionStorage.removeItem("aarogya_citizen_pending_phone");
        sessionStorage.removeItem("aarogya_citizen_masked_phone");
        sessionStorage.removeItem("aarogya_citizen_challenge_id");
        setGuestSession(null);

        if (pendingProtectedAction) {
          const resumeFn = pendingProtectedAction.onSuccessResume;
          setPendingProtectedAction(null);
          setAuthMode("AUTHENTICATED");
          if (resumeFn) resumeFn();
          return { success: true };
        }

        setAuthMode("AUTHENTICATED");
        return { success: true };
      }
      return { success: false, error: data?.message || "Registration failed" };
    } catch (err: any) {
      let msg = "Onboarding failed";
      if (typeof err?.message === "string") {
        msg = err.message;
      } else if (typeof err?.fields?.message === "string") {
        msg = err.fields.message;
      } else if (typeof err?.error === "string") {
        msg = err.error;
      } else if (typeof err === "string") {
        msg = err;
      }
      return { success: false, error: msg };
    }
  };

  // Continue as Guest
  const continueAsGuest = async () => {
    try {
      const locale = LanguageService.resolveLanguage();
      const res = await apiClient.createGuestSession(locale);
      const data = res?.data || res;
      const gObj: GuestSessionDTO = {
        session_id: data.session_id,
        locale: data.locale,
        expires_at: data.expires_at
      };
      setGuestSession(gObj);
      localStorage.setItem("aarogya_guest_session", JSON.stringify(gObj));
      sessionStorage.removeItem("aarogya_citizen_flow_step");
      setAuthMode("GUEST_ACTIVE");
    } catch (err) {
      console.error("Guest session creation error", err);
      const fallbackGuest: GuestSessionDTO = {
        session_id: `gst_local_${Date.now()}`,
        locale: "mr-IN",
        expires_at: new Date(Date.now() + 86400000).toISOString()
      };
      setGuestSession(fallbackGuest);
      localStorage.setItem("aarogya_guest_session", JSON.stringify(fallbackGuest));
      sessionStorage.removeItem("aarogya_citizen_flow_step");
      setAuthMode("GUEST_ACTIVE");
    }
  };

  const selectBeneficiary = (beneficiary: BeneficiaryOption) => {
    setActiveBeneficiary(beneficiary);
    localStorage.setItem("aarogya_citizen_active_ben_id", beneficiary.beneficiaryId);
  };

  const triggerProtectedAction = (action: PendingProtectedAction) => {
    setPendingProtectedAction(action);
  };

  const cancelProtectedAction = () => {
    setPendingProtectedAction(null);
  };

  const logout = async () => {
    try {
      await apiClient.logoutCitizen();
    } catch (e) {
      // ignore
    } finally {
      localStorage.removeItem("aarogya_citizen_token");
      localStorage.removeItem("aarogya_citizen_refresh_token");
      localStorage.removeItem("aarogya_citizen_user");
      localStorage.removeItem("aarogya_citizen_active_ben_id");
      localStorage.removeItem("aarogya_citizen_active_beneficiary");
      localStorage.removeItem("aarogya_guest_session");
      sessionStorage.removeItem("aarogya_citizen_flow_step");
      sessionStorage.removeItem("aarogya_citizen_pending_phone");
      sessionStorage.removeItem("aarogya_citizen_masked_phone");
      sessionStorage.removeItem("aarogya_citizen_challenge_id");
      apiClient.setToken(null);
      setToken(null);
      setUser(null);
      setGuestSession(null);
      setActiveBeneficiary(null);
      setAuthorizedBeneficiaries([]);
      setPendingProtectedAction(null);
      setPendingPhone("");
      setMaskedPhone("");
      setChallengeId(null);
      setCooldownSeconds(0);
      setAuthMode("LANGUAGE_SELECT");
    }
  };

  return (
    <CitizenAuthContext.Provider
      value={{
        authMode,
        setAuthMode: updateAuthMode,
        user,
        token,
        guestSession,
        isAuthenticated: !!token && !!user,
        isGuest: authMode === "GUEST_ACTIVE" && !token,
        isLoading,
        initError,
        retryInit: initAuth,
        activeBeneficiary,
        authorizedBeneficiaries,
        refreshBeneficiaries,
        pendingPhone,
        maskedPhone,
        challengeId,
        cooldownSeconds,
        pendingProtectedAction,
        startPhoneLogin,
        resendOtp,
        submitOtp,
        completeOnboarding,
        continueAsGuest,
        selectBeneficiary,
        triggerProtectedAction,
        cancelProtectedAction,
        resetOtpFlow,
        logout
      }}
    >
      {children}
    </CitizenAuthContext.Provider>
  );
};

export const useCitizenAuth = () => {
  const context = useContext(CitizenAuthContext);
  if (!context) {
    throw new Error("useCitizenAuth must be used within a CitizenAuthProvider");
  }
  return context;
};
