import React, { useState, useEffect, useCallback } from "react";
import { Home, HeartPulse, Pill, Award, User, AlertTriangle, Globe, Loader2, LogOut, UserCheck, CheckCircle2 } from "lucide-react";
import { LanguageProvider, useLanguage, getLanguageBadgeLabel } from "@aarogya/i18n";
import { CitizenAuthProvider, useCitizenAuth } from "./context/CitizenAuthContext";
import { LanguageSelectionScreen } from "./components/LanguageSelectionScreen";
import { CitizenEntryScreen } from "./components/auth/CitizenEntryScreen";
import { CitizenPhoneOtpScreen } from "./components/auth/CitizenPhoneOtpScreen";
import { CitizenOnboardingScreen } from "./components/auth/CitizenOnboardingScreen";
import { CitizenSelectBeneficiaryScreen } from "./components/auth/CitizenSelectBeneficiaryScreen";
import { ProtectedActionModal } from "./components/auth/ProtectedActionModal";
import { HomeScreen } from "./components/HomeScreen";
import { AssistantScreen } from "./components/AssistantScreen";
import { MyCareScreen } from "./components/MyCareScreen";
import { DoctorConsultationScreen } from "./components/DoctorConsultationScreen";
import { AshaScreen } from "./components/AshaScreen";
import { SchemesScreen } from "./components/SchemesScreen";
import { FacilitiesScreen } from "./components/FacilitiesScreen";
import { MedicinesScreen } from "./components/MedicinesScreen";
import { ProfileScreen } from "./components/ProfileScreen";
import { EmergencyModal } from "./components/EmergencyModal";
import { DoctorRequestWizard } from "./components/DoctorRequestWizard";
import { DoctorWaitingRoomScreen } from "./components/DoctorWaitingRoomScreen";
import { DoctorConsultationRoomScreen } from "./components/DoctorConsultationRoomScreen";
import { DoctorConsultationSummaryScreen } from "./components/DoctorConsultationSummaryScreen";
import { ServiceRequestDetailScreen } from "./components/ServiceRequestDetailScreen";
import { LanguageService, LanguageCode } from "./services/languageService";

type CitizenTab =
  | "home"
  | "care"
  | "medicines"
  | "schemes"
  | "profile"
  | "assistant"
  | "doctor"
  | "asha"
  | "facilities"
  | "doctor_request"
  | "doctor_waiting"
  | "doctor_session"
  | "doctor_summary"
  | "service_request_detail";

const ALLOWED_TABS: Record<string, CitizenTab> = {
  "/citizen/home": "home",
  "/citizen/care": "care",
  "/citizen/medicines": "medicines",
  "/citizen/schemes": "schemes",
  "/citizen/facilities": "facilities",
  "/citizen/profile": "profile",
  "/citizen/asha": "asha",
  "/citizen/doctor": "doctor",
  "/citizen/assistant": "assistant",
  "home": "home",
  "care": "care",
  "medicines": "medicines",
  "schemes": "schemes",
  "facilities": "facilities",
  "profile": "profile",
  "asha": "asha",
  "doctor": "doctor",
  "assistant": "assistant"
};

function sanitizeReturnRoute(returnTo?: string | null): CitizenTab {
  if (!returnTo) return "home";
  const clean = returnTo.trim();
  if (ALLOWED_TABS[clean]) return ALLOWED_TABS[clean];
  for (const [routeKey, tab] of Object.entries(ALLOWED_TABS)) {
    if (clean.startsWith(routeKey)) return tab;
  }
  return "home";
}

function CitizenAppInner() {
  const { t, locale, setLocale } = useLanguage();
  const {
    authMode,
    setAuthMode,
    user,
    isGuest,
    isAuthenticated,
    isLoading,
    initError,
    retryInit,
    triggerProtectedAction,
    activeBeneficiary,
    authorizedBeneficiaries,
    logout
  } = useCitizenAuth();

  const [activeTab, setActiveTab] = useState<CitizenTab>(() => {
    const path = window.location.pathname;
    if (path.includes("/schemes")) return "schemes";
    if (path.includes("/facilities")) return "facilities";
    if (path.includes("/medicines")) return "medicines";
    if (path.includes("/care")) return "care";
    if (path.includes("/profile")) return "profile";
    if (path.includes("/asha")) return "asha";
    if (path.includes("/doctor")) return "doctor";
    return "home";
  });

  const [activeRequestId, setActiveRequestId] = useState<string | null>(null);
  const [selectedServiceRequestId, setSelectedServiceRequestId] = useState<string | null>(null);
  const [showEmergencyModal, setShowEmergencyModal] = useState(false);

  // In-App Language Change State (Independent of Auth State)
  const [isChangingLanguage, setIsChangingLanguage] = useState<boolean>(() => {
    const params = new URLSearchParams(window.location.search);
    return params.get("mode") === "change" || window.location.pathname === "/language";
  });
  const [languageReturnTab, setLanguageReturnTab] = useState<CitizenTab>(() => {
    const params = new URLSearchParams(window.location.search);
    return sanitizeReturnRoute(params.get("returnTo"));
  });
  const [successToast, setSuccessToast] = useState<string | null>(null);

  useEffect(() => {
    // Flush pending offline language sync queue on mount
    LanguageService.flushPendingSyncQueue();

    const handleOnline = () => {
      LanguageService.flushPendingSyncQueue();
    };

    window.addEventListener("online", handleOnline);
    return () => window.removeEventListener("online", handleOnline);
  }, []);

  // Listen for browser URL changes / popstate for query param support
  useEffect(() => {
    const handleUrlCheck = () => {
      const params = new URLSearchParams(window.location.search);
      const isChange = params.get("mode") === "change" || (window.location.pathname === "/language" && (isAuthenticated || isGuest));
      if (isChange) {
        setIsChangingLanguage(true);
        const safeTab = sanitizeReturnRoute(params.get("returnTo") || activeTab);
        setLanguageReturnTab(safeTab);
      }
    };

    window.addEventListener("popstate", handleUrlCheck);
    return () => window.removeEventListener("popstate", handleUrlCheck);
  }, [activeTab, isAuthenticated, isGuest]);

  // Open in-app change language view safely
  const openChangeLanguage = useCallback((returnTab?: CitizenTab) => {
    const destination = returnTab || activeTab;
    setLanguageReturnTab(destination);
    setIsChangingLanguage(true);
    // Push or replace safe state in browser history
    const targetUrl = `/language?mode=change&returnTo=/citizen/${destination}`;
    window.history.pushState({ mode: "change", returnTo: `/citizen/${destination}` }, "", targetUrl);
  }, [activeTab]);

  // Close in-app change language and return to previous page
  const closeChangeLanguage = useCallback(() => {
    setIsChangingLanguage(false);
    setActiveTab(languageReturnTab);
    const safePath = `/citizen/${languageReturnTab}`;
    window.history.replaceState({}, "", safePath);
  }, [languageReturnTab]);

  // Save in-app language without altering session or auth state
  const handleSaveInAppLanguage = async (newLocale: LanguageCode) => {
    setIsChangingLanguage(false);
    setActiveTab(languageReturnTab);
    const safePath = `/citizen/${languageReturnTab}`;
    window.history.replaceState({}, "", safePath);

    // Show localized success toast
    const msg = t("citizen.language_changed_success", "Language changed successfully");
    setSuccessToast(msg);
    setTimeout(() => {
      setSuccessToast(null);
    }, 3500);
  };

  // Fresh Launch / Onboarding Language Selection
  const handleOnboardingLanguageSelected = async (langCode: LanguageCode) => {
    await setLocale(langCode);
    LanguageService.saveLocalPreference(langCode);
    setAuthMode("ENTRY_SELECT");
  };

  // Guard protected tabs for guest users
  const handleNavigateTab = (tabId: string) => {
    if (isGuest && (tabId === "care" || tabId === "medicines" || tabId === "profile")) {
      triggerProtectedAction({
        actionType: "VIEW_RECORDS",
        onSuccessResume: () => setActiveTab(tabId as any)
      });
      return;
    }
    setActiveTab(tabId as any);
  };

  // Guard Doctor Consultation with optional chat/home prefill data
  const [wizardPrefillData, setWizardPrefillData] = useState<{
    sessionId?: string;
    needId?: string;
    chiefComplaint?: string;
    symptoms?: string[];
    priority?: string;
    beneficiaryId?: string;
  } | null>(null);

  const handleOpenDoctor = (prefill?: {
    sessionId?: string;
    needId?: string;
    chiefComplaint?: string;
    symptoms?: string[];
    priority?: string;
    beneficiaryId?: string;
  }) => {
    if (prefill) {
      setWizardPrefillData(prefill);
    } else {
      setWizardPrefillData(null);
    }

    if (isGuest) {
      triggerProtectedAction({
        actionType: "DOCTOR_CONSULTATION",
        onSuccessResume: () => setActiveTab("doctor")
      });
      return;
    }
    setActiveTab("doctor");
  };

  // Guard ASHA Assistance
  const handleOpenAsha = () => {
    if (isGuest) {
      triggerProtectedAction({
        actionType: "ASHA_ASSISTANCE",
        onSuccessResume: () => setActiveTab("asha")
      });
      return;
    }
    setActiveTab("asha");
  };

  // -------------------------------------------------------------
  // Flow Screen Routing Transitions
  // -------------------------------------------------------------

  if (isLoading) {
    return (
      <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", backgroundColor: "#F8FAFC", gap: 16 }}>
        <Loader2 size={40} color="#2563EB" className="animate-spin" />
        <div style={{ fontSize: 16, fontWeight: 700, color: "#1E293B" }}>
          {t("citizen.restoring_account", "Restoring your account…")}
        </div>
      </div>
    );
  }

  // Error / Offline Retry Screen
  if (authMode === "ERROR") {
    return (
      <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", backgroundColor: "#F8FAFC", padding: 24, textAlign: "center", gap: 16 }}>
        <div style={{ width: 56, height: 56, borderRadius: "50%", backgroundColor: "#FEE2E2", display: "flex", alignItems: "center", justifyContent: "center" }}>
          <AlertTriangle size={28} color="#DC2626" />
        </div>
        <div style={{ fontSize: 18, fontWeight: 700, color: "#1E293B" }}>
          {t("common.connection_error", "Unable to connect to server")}
        </div>
        <div style={{ fontSize: 14, color: "#64748B", maxWidth: 320 }}>
          {initError || t("common.network_retry_msg", "Please check your network connection and try again.")}
        </div>
        <button
          onClick={retryInit}
          id="btn-retry-auth-bootstrap"
          style={{
            marginTop: 8,
            padding: "10px 24px",
            backgroundColor: "#2563EB",
            color: "#FFFFFF",
            border: "none",
            borderRadius: 8,
            fontWeight: 600,
            cursor: "pointer",
            fontSize: 14
          }}
        >
          {t("common.retry", "Retry")}
        </button>
      </div>
    );
  }

  // 1. Initial Fresh App Launch Language Selection Flow (Step 1 of 3)
  if (authMode === "LANGUAGE_SELECT") {
    return (
      <LanguageSelectionScreen
        mode="onboarding"
        onLanguageSelected={handleOnboardingLanguageSelected}
        isFirstLaunch={!LanguageService.hasConfirmedPreference()}
      />
    );
  }

  // 2. Citizen Entry Flow (Continue with Mobile OR Continue as Guest)
  if (authMode === "ENTRY_SELECT") {
    return (
      <CitizenEntryScreen
        onSelectMobile={() => setAuthMode("PHONE_ENTRY")}
        onSelectGuest={() => setAuthMode("GUEST_ACTIVE")}
        onChangeLanguage={() => setAuthMode("LANGUAGE_SELECT")}
      />
    );
  }

  // 3. Mobile Phone Entry & OTP Verification Flow
  if (authMode === "PHONE_ENTRY" || authMode === "OTP_VERIFY") {
    return (
      <CitizenPhoneOtpScreen
        onBack={() => setAuthMode("ENTRY_SELECT")}
        onSuccess={(isNew) => {
          if (isNew) {
            setAuthMode("ONBOARDING");
          } else {
            setAuthMode("AUTHENTICATED");
          }
        }}
      />
    );
  }

  // 4. Minimal Onboarding Flow for New Mobile Number
  if (authMode === "ONBOARDING") {
    return (
      <CitizenOnboardingScreen
        onSuccess={() => {
          setAuthMode("AUTHENTICATED");
        }}
      />
    );
  }

  // 5. Authorized Beneficiary Selection Flow
  if (authMode === "SELECT_BENEFICIARY") {
    return (
      <CitizenSelectBeneficiaryScreen
        onContinue={() => {
          setAuthMode("AUTHENTICATED");
        }}
      />
    );
  }

  // In-App Language Change Screen (Shown inside active session when opened from Header/Profile)
  if (isChangingLanguage) {
    return (
      <LanguageSelectionScreen
        mode="change"
        onBack={closeChangeLanguage}
        onSave={handleSaveInAppLanguage}
      />
    );
  }

  // 6. Citizen Home & Protected Feature Workspace
  const navTabs = [
    { id: "home", label: t("navigation.home"), icon: <Home size={22} /> },
    { id: "care", label: t("navigation.my_care"), icon: <HeartPulse size={22} /> },
    { id: "medicines", label: t("navigation.medicines"), icon: <Pill size={22} /> },
    { id: "schemes", label: t("navigation.schemes"), icon: <Award size={22} /> },
    { id: "profile", label: t("navigation.profile"), icon: <User size={22} /> }
  ];

  return (
    <div
      className="w-full flex-1 flex justify-center select-none"
      style={{
        minHeight: "100dvh",
        backgroundColor: "#F4F7FB",
        fontFamily: "'Noto Sans', 'Noto Sans Devanagari', sans-serif",
        paddingTop: "max(0px, var(--safe-area-top))",
        paddingBottom: "max(0px, var(--safe-area-bottom))",
        paddingLeft: "max(0px, var(--safe-area-left))",
        paddingRight: "max(0px, var(--safe-area-right))"
      }}
    >
      <div
        className="w-full sm:max-w-[430px] bg-white sm:rounded-3xl sm:shadow-xl sm:border sm:border-slate-200 overflow-hidden flex flex-col flex-1 sm:my-3 min-h-[100dvh] relative"
      >
        {/* App Top Header Bar */}
        <header
          style={{
            padding: "14px 16px",
            backgroundColor: "#1565C0",
            color: "#FFFFFF",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            boxShadow: "0 2px 8px rgba(0,0,0,0.1)"
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <div
              style={{
                width: 38,
                height: 38,
                borderRadius: "50%",
                backgroundColor: "#FFFFFF",
                color: "#1565C0",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontWeight: 800,
                fontSize: 16
              }}
            >
              AS
            </div>
            <div>
              <div style={{ fontSize: 16, fontWeight: 800, display: "flex", alignItems: "center", gap: 6 }}>
                <span>{t("common.app_name", "आरोग्य सहायक")}</span>
                {isGuest && (
                  <span
                    id="badge-citizen-guest-mode"
                    style={{
                      fontSize: 10,
                      backgroundColor: "rgba(255,255,255,0.25)",
                      padding: "2px 6px",
                      borderRadius: 10,
                      fontWeight: 700
                    }}
                  >
                    {t("citizen.guest_mode_badge", "Guest")}
                  </span>
                )}
              </div>
              <div style={{ fontSize: 11, opacity: 0.9, fontWeight: 600 }}>
                {activeBeneficiary ? (activeBeneficiary.relationship === "SELF" ? `${activeBeneficiary.displayName.replace(/\s*\(.*?\)\s*/g, "")} (${t("common.self", "Self")})` : `${activeBeneficiary.displayName.replace(/\s*\(.*?\)\s*/g, "")} (${t(`beneficiary.relationship.${activeBeneficiary.relationship || "OTHER"}`, activeBeneficiary.relationship)})`) : t("common.tagline", "AI-Powered Rural Healthcare")}
              </div>
            </div>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            {/* Quick Change Language Icon Button */}
            <button
              onClick={() => openChangeLanguage(activeTab)}
              id="btn-citizen-change-language"
              title={t("common.change_language", "Change Language")}
              style={{
                padding: "6px 10px",
                backgroundColor: "rgba(255,255,255,0.2)",
                color: "#FFFFFF",
                borderRadius: 20,
                fontSize: 12,
                fontWeight: 700,
                border: "none",
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                gap: 4
              }}
            >
              <Globe size={14} />
              <span>{getLanguageBadgeLabel(locale)}</span>
            </button>

            {/* Logout / Switch Profile if Authenticated */}
            {isAuthenticated && (
              <button
                onClick={logout}
                id="btn-citizen-logout"
                title={t("common.logout", "Sign Out")}
                style={{
                  padding: "6px 8px",
                  backgroundColor: "rgba(255,255,255,0.2)",
                  color: "#FFFFFF",
                  borderRadius: 20,
                  fontSize: 11,
                  fontWeight: 700,
                  border: "none",
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center"
                }}
              >
                <LogOut size={14} />
              </button>
            )}

            {/* Emergency Help Button (108) */}
            <button
              onClick={() => setShowEmergencyModal(true)}
              id="btn-app-emergency-108"
              style={{
                padding: "6px 12px",
                backgroundColor: "#C62828",
                color: "#FFFFFF",
                borderRadius: 20,
                fontSize: 12,
                fontWeight: 800,
                border: "none",
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                gap: 4,
                boxShadow: "0 2px 8px rgba(198, 40, 40, 0.4)"
              }}
            >
              <AlertTriangle size={14} /> 108
            </button>
          </div>
        </header>

        {/* Localized Toast Notification */}
        {successToast && (
          <div
            role="status"
            aria-live="polite"
            className="p-3 bg-emerald-600 text-white text-xs font-bold text-center flex items-center justify-center gap-2 shadow-md animate-in fade-in duration-200"
          >
            <CheckCircle2 size={16} />
            <span>{successToast}</span>
          </div>
        )}

        {/* Identity & Beneficiary Context Bar */}
        {isAuthenticated && user && (
          <div
            id="bar-authenticated-identity-context"
            style={{
              padding: "8px 14px",
              backgroundColor: "#EFF6FF",
              borderBottom: "1px solid #DBEAFE",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              fontSize: 12,
              color: "#1E40AF"
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 6, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
              <UserCheck size={14} color="#2563EB" />
              <span>
                {t("common.signed_in_as", "Signed in as")}: <strong>{user.name}</strong>
                {activeBeneficiary && activeBeneficiary.relationship !== "SELF" ? (
                  <span style={{ color: "#334155", marginLeft: 4 }}>
                    | {t("common.viewing_care_for", "Viewing care for")}: <strong>{activeBeneficiary.displayName}</strong>
                  </span>
                ) : (
                  <span style={{ color: "#64748B", marginLeft: 4 }}>
                    ({t("common.self", "Self")})
                  </span>
                )}
              </span>
            </div>
            {authorizedBeneficiaries && authorizedBeneficiaries.length > 1 && (
              <button
                onClick={() => setAuthMode("SELECT_BENEFICIARY")}
                id="btn-switch-active-beneficiary"
                style={{
                  background: "none",
                  border: "none",
                  color: "#2563EB",
                  fontSize: 11,
                  fontWeight: 700,
                  cursor: "pointer",
                  padding: "2px 6px",
                  borderRadius: 4,
                  textDecoration: "underline"
                }}
              >
                {t("common.switch", "Switch")}
              </button>
            )}
          </div>
        )}

        {/* Dynamic Screen View Content */}
        <main style={{ flex: 1, overflowY: "auto", paddingBottom: 72 }}>
          {activeTab === "home" && (
            <HomeScreen
              onStartVoiceChat={() => setActiveTab("assistant")}
              onOpenTypeChat={() => setActiveTab("assistant")}
              onNavigate={(tab) => handleNavigateTab(tab)}
              onOpenDoctor={handleOpenDoctor}
              onOpenEmergency={() => setShowEmergencyModal(true)}
              onOpenAsha={handleOpenAsha}
            />
          )}

          {activeTab === "assistant" && (
            <AssistantScreen
              onBack={() => setActiveTab("home")}
              onOpenDoctor={handleOpenDoctor}
              onOpenEmergency={() => setShowEmergencyModal(true)}
              onOpenAsha={handleOpenAsha}
              onOpenFacilities={() => setActiveTab("facilities")}
              onViewServiceRequest={(srId) => {
                setSelectedServiceRequestId(srId);
                setActiveTab("service_request_detail");
              }}
            />
          )}

          {activeTab === "care" && (
            <MyCareScreen
              onOpenDoctor={handleOpenDoctor}
              onOpenAsha={handleOpenAsha}
              onViewServiceRequest={(srId) => {
                setSelectedServiceRequestId(srId);
                setActiveTab("service_request_detail");
              }}
            />
          )}

          {activeTab === "service_request_detail" && selectedServiceRequestId && (
            <ServiceRequestDetailScreen
              requestId={selectedServiceRequestId}
              onBack={() => setActiveTab("care")}
            />
          )}

          {activeTab === "doctor" && (
            <DoctorRequestWizard
              onBack={() => setActiveTab("home")}
              initialChatSessionId={wizardPrefillData?.sessionId}
              initialCitizenNeedId={wizardPrefillData?.needId}
              initialChiefComplaint={wizardPrefillData?.chiefComplaint}
              initialSymptoms={wizardPrefillData?.symptoms}
              initialBeneficiaryId={wizardPrefillData?.beneficiaryId}
              initialPriority={wizardPrefillData?.priority}
              onRequestSubmitted={(reqId) => {
                setActiveRequestId(reqId);
                setActiveTab("doctor_waiting");
              }}
            />
          )}

          {activeTab === "doctor_request" && (
            <DoctorRequestWizard
              onBack={() => setActiveTab("home")}
              initialChatSessionId={wizardPrefillData?.sessionId}
              initialCitizenNeedId={wizardPrefillData?.needId}
              initialChiefComplaint={wizardPrefillData?.chiefComplaint}
              initialSymptoms={wizardPrefillData?.symptoms}
              initialBeneficiaryId={wizardPrefillData?.beneficiaryId}
              initialPriority={wizardPrefillData?.priority}
              onRequestSubmitted={(reqId) => {
                setActiveRequestId(reqId);
                setActiveTab("doctor_waiting");
              }}
            />
          )}

          {activeTab === "doctor_waiting" && (
            <DoctorWaitingRoomScreen
              requestId={activeRequestId || ""}
              onJoinConsultation={() => setActiveTab("doctor_session")}
              onViewSummary={() => setActiveTab("doctor_summary")}
              onBackToHome={() => setActiveTab("home")}
            />
          )}

          {activeTab === "doctor_session" && activeRequestId && (
            <DoctorConsultationRoomScreen
              requestId={activeRequestId}
              onEndConsultation={() => setActiveTab("doctor_summary")}
            />
          )}

          {activeTab === "doctor_summary" && activeRequestId && (
            <DoctorConsultationSummaryScreen
              requestId={activeRequestId}
              onBackToHome={() => setActiveTab("home")}
              onViewMedicines={() => setActiveTab("medicines")}
            />
          )}

          {activeTab === "asha" && (
            <AshaScreen onBack={() => setActiveTab("home")} />
          )}

          {activeTab === "schemes" && (
            <SchemesScreen
              onBack={() => setActiveTab("home")}
              onNavigateToFacilities={() => setActiveTab("facilities")}
              onNavigateToAsha={handleOpenAsha}
            />
          )}

          {activeTab === "facilities" && (
            <FacilitiesScreen onBack={() => setActiveTab("home")} />
          )}

          {activeTab === "medicines" && (
            <MedicinesScreen onBack={() => setActiveTab("home")} />
          )}

          {activeTab === "profile" && (
            <ProfileScreen
              onSelectLanguage={() => openChangeLanguage("profile")}
              onNavigateToTab={(tab: string) => handleNavigateTab(tab)}
            />
          )}
        </main>

        {/* Mobile Bottom Navigation Bar (5 tabs) */}
        <nav
          style={{
            position: "absolute",
            bottom: 0,
            left: 0,
            right: 0,
            backgroundColor: "#FFFFFF",
            borderTop: "1px solid #E2E8F0",
            display: "flex",
            justifyContent: "space-around",
            alignItems: "center",
            padding: "8px 0 10px",
            zIndex: 50,
            boxShadow: "0 -4px 16px rgba(0,0,0,0.06)"
          }}
        >
          {navTabs.map((tab) => {
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                id={`nav-tab-${tab.id}`}
                onClick={() => handleNavigateTab(tab.id)}
                style={{
                  border: "none",
                  background: "transparent",
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  gap: 3,
                  color: isActive ? "#1565C0" : "#64748B",
                  fontWeight: isActive ? 800 : 600,
                  fontSize: 11,
                  cursor: "pointer",
                  flex: 1
                }}
              >
                {React.cloneElement(tab.icon, { color: isActive ? "#1565C0" : "#64748B" })}
                <span>{tab.label}</span>
              </button>
            );
          })}
        </nav>

        {/* Emergency Modal */}
        {showEmergencyModal && (
          <EmergencyModal
            onClose={() => setShowEmergencyModal(false)}
            onOpenFacilities={() => setActiveTab("facilities")}
          />
        )}

        {/* Protected Action Prompt Modal for Guests */}
        <ProtectedActionModal />
      </div>
    </div>
  );
}

export function App() {
  return (
    <LanguageProvider role="citizen" fallback="mr-IN">
      <CitizenAuthProvider>
        <CitizenAppInner />
      </CitizenAuthProvider>
    </LanguageProvider>
  );
}

export default App;
