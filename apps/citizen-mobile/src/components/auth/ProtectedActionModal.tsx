import React, { useState } from "react";
import { useLanguage } from "@aarogya/i18n";
import { Shield, X, ArrowRight, Loader2, Phone, AlertCircle } from "lucide-react";
import { useCitizenAuth } from "../../context/CitizenAuthContext";
import { CitizenPhoneOtpScreen } from "./CitizenPhoneOtpScreen";
import { CitizenOnboardingScreen } from "./CitizenOnboardingScreen";

export const ProtectedActionModal: React.FC = () => {
  const { t } = useLanguage();
  const { pendingProtectedAction, cancelProtectedAction, authMode } = useCitizenAuth();
  const [step, setStep] = useState<"PROMPT" | "OTP" | "ONBOARDING">("PROMPT");

  if (!pendingProtectedAction) return null;

  return (
    <div
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: "rgba(15, 23, 42, 0.65)",
        backdropFilter: "blur(4px)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 9999,
        padding: "16px"
      }}
    >
      {step === "PROMPT" && (
        <div
          style={{
            width: "100%",
            maxWidth: 420,
            backgroundColor: "#FFFFFF",
            borderRadius: 24,
            boxShadow: "0 20px 40px rgba(0, 0, 0, 0.2)",
            border: "1px solid #E2E8F0",
            overflow: "hidden",
            padding: "24px 20px",
            textAlign: "center"
          }}
        >
          <div
            style={{
              width: 56,
              height: 56,
              borderRadius: 18,
              backgroundColor: "#EFF6FF",
              color: "#2563EB",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              margin: "0 auto 14px"
            }}
          >
            <Shield size={30} />
          </div>

          <h3 style={{ fontSize: 18, fontWeight: 800, color: "#0F172A", margin: "0 0 8px" }}>
            {t("citizen.protected_action_title", "Mobile Verification Required")}
          </h3>

          <p style={{ fontSize: 14, color: "#475569", margin: "0 0 24px", lineHeight: 1.5, fontWeight: 600 }}>
            {t("citizen.protected_action_desc", "Verify your mobile number to securely share and save this information.")}
          </p>

          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            <button
              type="button"
              id="btn-protected-continue-otp"
              onClick={() => setStep("OTP")}
              style={{
                minHeight: 48,
                padding: "14px",
                borderRadius: 16,
                backgroundColor: "#2563EB",
                color: "#FFFFFF",
                border: "none",
                fontSize: 15,
                fontWeight: 800,
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: 8,
                boxShadow: "0 4px 14px rgba(37, 99, 235, 0.25)"
              }}
            >
              <span>{t("citizen.continue_with_otp", "Continue with OTP")}</span>
              <ArrowRight size={18} />
            </button>

            <button
              type="button"
              id="btn-protected-cancel-modal"
              onClick={cancelProtectedAction}
              style={{
                minHeight: 48,
                padding: "12px",
                borderRadius: 16,
                backgroundColor: "#F1F5F9",
                color: "#475569",
                border: "none",
                fontSize: 14,
                fontWeight: 700,
                cursor: "pointer"
              }}
            >
              {t("citizen.not_now", "Not Now")}
            </button>
          </div>
        </div>
      )}

      {step === "OTP" && (
        <div style={{ width: "100%", maxWidth: 440 }}>
          <CitizenPhoneOtpScreen
            onBack={() => setStep("PROMPT")}
            onSuccess={(isNew) => {
              if (isNew) {
                setStep("ONBOARDING");
              }
              // If not new, CitizenAuthContext automatically invokes resume callback and clears pending action
            }}
          />
        </div>
      )}

      {step === "ONBOARDING" && (
        <div style={{ width: "100%", maxWidth: 480 }}>
          <CitizenOnboardingScreen
            onSuccess={() => {
              // Onboarding complete, Context resumes action
            }}
          />
        </div>
      )}
    </div>
  );
};
