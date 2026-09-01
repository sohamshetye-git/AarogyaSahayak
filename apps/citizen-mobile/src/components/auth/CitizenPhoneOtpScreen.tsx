import React, { useState, useRef, useEffect } from "react";
import { useLanguage } from "@aarogya/i18n";
import { Phone, ArrowLeft, ArrowRight, Loader2, RefreshCw, Volume2, ShieldCheck, AlertCircle } from "lucide-react";
import { useCitizenAuth } from "../../context/CitizenAuthContext";
import { LanguageService } from "../../services/languageService";

interface CitizenPhoneOtpScreenProps {
  onBack: () => void;
  onSuccess: (isNewCitizen: boolean) => void;
}

export const CitizenPhoneOtpScreen: React.FC<CitizenPhoneOtpScreenProps> = ({
  onBack,
  onSuccess
}) => {
  const { t, locale } = useLanguage();
  const {
    authMode,
    startPhoneLogin,
    submitOtp,
    resendOtp,
    resetOtpFlow,
    cooldownSeconds,
    maskedPhone,
    pendingPhone
  } = useCitizenAuth();

  const [phoneInput, setPhoneInput] = useState<string>(pendingPhone || "");
  const [otpDigits, setOtpDigits] = useState<string[]>(["", "", "", "", "", ""]);
  const [loading, setLoading] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [mockHint, setMockHint] = useState<string | null>(null);

  const otpInputsRef = useRef<(HTMLInputElement | null)[]>([]);

  const [localStep, setLocalStep] = useState<"PHONE" | "OTP">(() => authMode === "OTP_VERIFY" ? "OTP" : "PHONE");
  const isOtpStep = authMode === "OTP_VERIFY" || localStep === "OTP";

  // Sync phone input if pendingPhone updates
  useEffect(() => {
    if (pendingPhone) {
      setPhoneInput(pendingPhone);
    }
  }, [pendingPhone]);

  // Auto focus first OTP input when entering OTP verify step
  useEffect(() => {
    if (isOtpStep) {
      setOtpDigits(["", "", "", "", "", ""]);
      setErrorMessage(null);
      setTimeout(() => {
        otpInputsRef.current[0]?.focus();
      }, 100);
    }
  }, [isOtpStep]);

  const handleBackToPhone = () => {
    setOtpDigits(["", "", "", "", "", ""]);
    setErrorMessage(null);
    setLocalStep("PHONE");
    resetOtpFlow();
    onBack();
  };

  // Handle phone submission
  const handleRequestOtp = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    setErrorMessage(null);
    setMockHint(null);

    const clean = phoneInput.replace(/\D/g, "");
    if (clean.length < 10) {
      setErrorMessage(t("citizen.invalid_phone", "Please enter a valid 10-digit Indian mobile number."));
      return;
    }

    setLoading(true);
    try {
      const res = await startPhoneLogin(clean);
      if (!res.success) {
        setErrorMessage(res.error || "Failed to send OTP");
      } else {
        setLocalStep("OTP");
        if (res.mockCode) {
          setMockHint(`Dev Demo OTP: ${res.mockCode}`);
        }
      }
    } finally {
      setLoading(false);
    }
  };

  const isVerifyingRef = useRef(false);

  // Handle OTP digit changes
  const handleOtpChange = (index: number, value: string) => {
    if (!/^\d*$/.test(value)) return;

    const newDigits = [...otpDigits];
    newDigits[index] = value.slice(-1); // Only take last char
    setOtpDigits(newDigits);
    setErrorMessage(null);

    // Auto advance
    if (value && index < 5) {
      otpInputsRef.current[index + 1]?.focus();
    }

    // Auto submit if all 6 digits filled
    if (newDigits.every((d) => d !== "") && index === 5) {
      handleVerifyOtp(newDigits.join(""));
    }
  };

  const handleOtpKeyDown = (index: number, e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Backspace" && !otpDigits[index] && index > 0) {
      otpInputsRef.current[index - 1]?.focus();
    }
  };

  // Handle OTP Paste (e.g. autofill or copy paste)
  const handleOtpPaste = (e: React.ClipboardEvent<HTMLInputElement>) => {
    e.preventDefault();
    const pasted = e.clipboardData.getData("text").replace(/\D/g, "").slice(0, 6);
    if (pasted.length === 6) {
      const newDigits = pasted.split("");
      setOtpDigits(newDigits);
      handleVerifyOtp(pasted);
    }
  };

  // Verify OTP submission
  const handleVerifyOtp = async (codeToVerify?: string) => {
    if (isVerifyingRef.current || loading) return;

    const fullCode = codeToVerify || otpDigits.join("");
    if (fullCode.length !== 6) {
      setErrorMessage(t("citizen.invalid_otp_format", "Please enter all 6 digits of the OTP."));
      return;
    }

    isVerifyingRef.current = true;
    setLoading(true);
    setErrorMessage(null);
    try {
      const res = await submitOtp(fullCode);
      if (res.error) {
        setErrorMessage(res.error);
      } else {
        onSuccess(res.isNewCitizen);
      }
    } finally {
      setLoading(false);
      isVerifyingRef.current = false;
    }
  };

  // Spoken instructions via TTS
  const handleHearInstructions = () => {
    const langCode = (locale || "mr-IN") as any;
    const isHi = langCode.startsWith("hi");
    const isEn = langCode.startsWith("en");

    let phrase = "";
    if (authMode === "OTP_VERIFY") {
      phrase = isHi
        ? `कृपया अपने मोबाइल नंबर ${maskedPhone} पर भेजा गया ६ अंकों का ओटीपी कोड दर्ज करें।`
        : isEn
        ? `Please enter the 6-digit verification code sent to your phone ${maskedPhone}.`
        : `कृपया आपल्या ${maskedPhone} या मोबाईल क्रमांकावर आलेला ६ अंकी ओटीपी कोड प्रविष्ट करा.`;
    } else {
      phrase = isHi
        ? "कृपया अपना १० अंकों का मोबाइल नंबर दर्ज करें और ओटीपी प्राप्त करें बटन दबाएं।"
        : isEn
        ? "Please enter your 10-digit mobile number and tap Send OTP."
        : "कृपया आपला १० अंकी मोबाईल नंबर प्रविष्ट करा आणि ओटीपी पाठवा बटण दाबा.";
    }

    LanguageService.speakPhrase(phrase, langCode);
  };

  return (
    <div
      className="w-full flex-1 flex flex-col justify-start sm:justify-center items-center select-none"
      style={{
        minHeight: "100dvh",
        backgroundColor: "#F8FAFC",
        paddingTop: "max(0px, var(--safe-area-top))",
        paddingBottom: "max(16px, var(--safe-area-bottom))",
        paddingLeft: "max(0px, var(--safe-area-left))",
        paddingRight: "max(0px, var(--safe-area-right))",
        fontFamily: "'Noto Sans', 'Noto Sans Devanagari', sans-serif"
      }}
    >
      <div
        className="w-full sm:max-w-[430px] bg-white sm:rounded-3xl sm:shadow-xl sm:border sm:border-slate-200 overflow-hidden flex flex-col flex-1 sm:flex-initial sm:my-4 min-h-[100dvh] sm:min-h-auto"
      >
        {/* Top Header */}
        <div
          style={{
            padding: "16px 20px",
            borderBottom: "1px solid #F1F5F9",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between"
          }}
        >
          <button
            onClick={handleBackToPhone}
            style={{
              border: "none",
              background: "#F1F5F9",
              borderRadius: "50%",
              width: 40,
              height: 40,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              cursor: "pointer",
              color: "#334155"
            }}
          >
            <ArrowLeft size={20} />
          </button>

          <span style={{ fontSize: 14, fontWeight: 700, color: "#64748B" }}>
            {isOtpStep ? "2 / 2" : "1 / 2"}
          </span>

          <button
            onClick={handleHearInstructions}
            title={t("common.listen", "Listen instructions")}
            style={{
              border: "none",
              background: "#EFF6FF",
              borderRadius: "50%",
              width: 40,
              height: 40,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              cursor: "pointer",
              color: "#2563EB"
            }}
          >
            <Volume2 size={20} />
          </button>
        </div>

        {/* Form Body */}
        <div style={{ padding: "24px 20px" }}>
          {!isOtpStep ? (
            /* Step 1: Mobile Number Entry */
            <form onSubmit={handleRequestOtp}>
              <div
                style={{
                  width: 52,
                  height: 52,
                  borderRadius: 16,
                  backgroundColor: "#EFF6FF",
                  color: "#2563EB",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  marginBottom: 16
                }}
              >
                <Phone size={28} />
              </div>

              <h2 style={{ fontSize: 20, fontWeight: 800, color: "#0F172A", margin: "0 0 6px" }}>
                {t("citizen.enter_mobile_title", "Enter Mobile Number")}
              </h2>
              <p style={{ fontSize: 13, color: "#64748B", margin: "0 0 20px", lineHeight: 1.4 }}>
                {t("citizen.enter_mobile_desc", "We will send a 6-digit verification code to your phone.")}
              </p>

              {/* Indian Mobile Input with +91 Prefix */}
              <div style={{ marginBottom: 16 }}>
                <label style={{ display: "block", fontSize: 12, fontWeight: 700, color: "#334155", marginBottom: 6 }}>
                  {t("common.phone", "Mobile Number")}
                </label>
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    border: "2px solid #CBD5E1",
                    borderRadius: 16,
                    overflow: "hidden",
                    backgroundColor: "#F8FAFC"
                  }}
                >
                  <div
                    style={{
                      padding: "14px 14px",
                      backgroundColor: "#E2E8F0",
                      fontWeight: 800,
                      color: "#334155",
                      fontSize: 15
                    }}
                  >
                    🇮🇳 +91
                  </div>
                  <input
                    type="tel"
                    id="input-citizen-phone"
                    value={phoneInput}
                    onChange={(e) => {
                      setPhoneInput(e.target.value);
                      setErrorMessage(null);
                    }}
                    placeholder={t("citizen.mobile_placeholder", "9876543210")}
                    maxLength={10}
                    autoFocus
                    style={{
                      flex: 1,
                      padding: "14px 16px",
                      border: "none",
                      outline: "none",
                      fontSize: 18,
                      fontWeight: 700,
                      color: "#0F172A",
                      backgroundColor: "transparent",
                      letterSpacing: "0.05em"
                    }}
                  />
                </div>
              </div>

              {errorMessage && (
                <div
                  style={{
                    padding: "10px 14px",
                    backgroundColor: "#FEF2F2",
                    borderRadius: 12,
                    border: "1px solid #FCA5A5",
                    color: "#B91C1C",
                    fontSize: 12,
                    fontWeight: 600,
                    marginBottom: 16,
                    display: "flex",
                    alignItems: "center",
                    gap: 6
                  }}
                >
                  <AlertCircle size={16} />
                  <span>{errorMessage}</span>
                </div>
              )}

              <button
                type="submit"
                id="btn-citizen-request-otp"
                disabled={loading || phoneInput.length < 10}
                style={{
                  minHeight: 48,
                  width: "100%",
                  padding: "14px",
                  borderRadius: 16,
                  backgroundColor: phoneInput.length >= 10 ? "#2563EB" : "#94A3B8",
                  color: "#FFFFFF",
                  border: "none",
                  fontSize: 16,
                  fontWeight: 800,
                  cursor: phoneInput.length >= 10 && !loading ? "pointer" : "not-allowed",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: 8,
                  boxShadow: "0 4px 14px rgba(37, 99, 235, 0.25)"
                }}
              >
                {loading ? <Loader2 size={20} className="animate-spin" /> : <ArrowRight size={20} />}
                <span>{t("citizen.get_otp", "Send OTP Code")}</span>
              </button>
            </form>
          ) : (
            /* Step 2: OTP Verification */
            <div>
              <div
                style={{
                  width: 52,
                  height: 52,
                  borderRadius: 16,
                  backgroundColor: "#ECFDF5",
                  color: "#059669",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  marginBottom: 16
                }}
              >
                <ShieldCheck size={28} />
              </div>

              <h2 style={{ fontSize: 20, fontWeight: 800, color: "#0F172A", margin: "0 0 6px" }}>
                {t("citizen.verify_otp_title", "Verify Mobile Number")}
              </h2>
              <p style={{ fontSize: 13, color: "#64748B", margin: "0 0 4px" }}>
                {t("citizen.otp_sent_to", { phone: maskedPhone })}
              </p>

              {/* Hackathon Demo Notice (Visible in staging/dev mode, absent in production) */}
              {((import.meta as any).env?.VITE_APP_ENV !== "production" &&
                (import.meta as any).env?.MODE !== "production") && (
                <div
                  id="notice-staging-demo-otp"
                  style={{
                    margin: "12px 0 16px",
                    padding: "10px 14px",
                    backgroundColor: "#EFF6FF",
                    border: "1px solid #BFDBFE",
                    borderRadius: 12,
                    display: "flex",
                    alignItems: "flex-start",
                    gap: 10
                  }}
                >
                  <ShieldCheck size={18} style={{ color: "#2563EB", flexShrink: 0, marginTop: 2 }} />
                  <div>
                    <div style={{ fontSize: 12, fontWeight: 800, color: "#1E40AF", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 2 }}>
                      {t("citizen.demo_otp_notice_title", "Hackathon Demo")}
                    </div>
                    <div style={{ fontSize: 13, fontWeight: 600, color: "#1E3A8A", lineHeight: 1.4 }}>
                      {t("citizen.demo_otp_notice", "For this hackathon demonstration, enter 123456 to continue.")}
                    </div>
                  </div>
                </div>
              )}

              {mockHint && !((import.meta as any).env?.VITE_APP_ENV !== "production") && (
                <div
                  style={{
                    padding: "6px 12px",
                    backgroundColor: "#FEF3C7",
                    color: "#92400E",
                    borderRadius: 10,
                    fontSize: 12,
                    fontWeight: 700,
                    display: "inline-block",
                    marginBottom: 16
                  }}
                >
                  {mockHint}
                </div>
              )}

              {/* 6-Digit OTP Blocks */}
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  gap: 8,
                  margin: "20px 0"
                }}
              >
                {otpDigits.map((digit, idx) => (
                  <input
                    key={idx}
                    ref={(el) => {
                      otpInputsRef.current[idx] = el;
                    }}
                    type="tel"

                    id={`otp-input-${idx}`}
                    maxLength={1}
                    value={digit}
                    onChange={(e) => handleOtpChange(idx, e.target.value)}
                    onKeyDown={(e) => handleOtpKeyDown(idx, e)}
                    onPaste={handleOtpPaste}
                    style={{
                      width: 48,
                      height: 56,
                      borderRadius: 14,
                      border: digit ? "2px solid #2563EB" : "2px solid #CBD5E1",
                      backgroundColor: digit ? "#EFF6FF" : "#F8FAFC",
                      textAlign: "center",
                      fontSize: 22,
                      fontWeight: 800,
                      color: "#0F172A",
                      outline: "none"
                    }}
                  />
                ))}
              </div>

              {errorMessage && (
                <div
                  style={{
                    padding: "12px 14px",
                    backgroundColor: "#FEF2F2",
                    borderRadius: 12,
                    border: "1px solid #FCA5A5",
                    color: "#B91C1C",
                    fontSize: 13,
                    fontWeight: 600,
                    marginBottom: 16,
                    display: "flex",
                    flexDirection: "column",
                    gap: 8
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    <AlertCircle size={16} />
                    <span>{errorMessage}</span>
                  </div>
                  {(errorMessage.includes("No active OTP") || errorMessage.includes("expired") || errorMessage.includes("exceeded")) && (
                    <button
                      type="button"
                      id="btn-request-new-otp-error"
                      onClick={handleRequestOtp}
                      disabled={loading || cooldownSeconds > 0}
                      style={{
                        alignSelf: "flex-start",
                        marginTop: 4,
                        padding: "6px 12px",
                        backgroundColor: "#DC2626",
                        color: "#FFFFFF",
                        border: "none",
                        borderRadius: 8,
                        fontSize: 12,
                        fontWeight: 700,
                        cursor: cooldownSeconds > 0 ? "not-allowed" : "pointer"
                      }}
                    >
                      {cooldownSeconds > 0 ? `Wait ${cooldownSeconds}s` : "Request New OTP"}
                    </button>
                  )}
                </div>
              )}

              {/* Verify Action Button */}
              <button
                type="button"
                id="btn-citizen-verify-otp-submit"
                onClick={() => handleVerifyOtp()}
                disabled={loading || otpDigits.some((d) => d === "")}
                style={{
                  minHeight: 48,
                  width: "100%",
                  padding: "14px",
                  borderRadius: 16,
                  backgroundColor: otpDigits.every((d) => d !== "") ? "#2563EB" : "#94A3B8",
                  color: "#FFFFFF",
                  border: "none",
                  fontSize: 16,
                  fontWeight: 800,
                  cursor: otpDigits.every((d) => d !== "") && !loading ? "pointer" : "not-allowed",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: 8,
                  boxShadow: "0 4px 14px rgba(37, 99, 235, 0.25)",
                  marginBottom: 16
                }}
              >
                {loading ? <Loader2 size={20} className="animate-spin" /> : <ShieldCheck size={20} />}
                <span>{t("citizen.verify_and_continue", "Verify & Continue")}</span>
              </button>

              {/* Resend OTP & Change Number Controls */}
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <button
                  type="button"
                  onClick={resendOtp}
                  disabled={cooldownSeconds > 0}
                  style={{
                    border: "none",
                    background: "none",
                    color: cooldownSeconds > 0 ? "#94A3B8" : "#2563EB",
                    fontSize: 13,
                    fontWeight: 700,
                    cursor: cooldownSeconds > 0 ? "not-allowed" : "pointer",
                    padding: 0
                  }}
                >
                  {cooldownSeconds > 0
                    ? t("citizen.resend_in_seconds", { seconds: cooldownSeconds })
                    : t("citizen.resend_otp", "Resend OTP")}
                </button>

                <button
                  type="button"
                  onClick={handleBackToPhone}
                  style={{
                    border: "none",
                    background: "none",
                    color: "#64748B",
                    fontSize: 13,
                    fontWeight: 700,
                    cursor: "pointer",
                    padding: 0
                  }}
                >
                  {t("citizen.change_number", "Change Number")}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
