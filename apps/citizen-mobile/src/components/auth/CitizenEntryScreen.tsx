import React, { useState } from "react";
import { useLanguage } from "@aarogya/i18n";
import { Phone, UserCheck, Shield, Mic, Volume2, AlertTriangle, ArrowRight, Loader2, Sparkles } from "lucide-react";
import { useCitizenAuth } from "../../context/CitizenAuthContext";
import { LanguageService } from "../../services/languageService";

interface CitizenEntryScreenProps {
  onSelectMobile: () => void;
  onSelectGuest: () => void;
  onChangeLanguage: () => void;
}

export const CitizenEntryScreen: React.FC<CitizenEntryScreenProps> = ({
  onSelectMobile,
  onSelectGuest,
  onChangeLanguage
}) => {
  const { t, locale } = useLanguage();
  const { continueAsGuest } = useCitizenAuth();
  const [isListening, setIsListening] = useState<boolean>(false);
  const [voiceNotice, setVoiceNotice] = useState<string | null>(null);
  const [guestLoading, setGuestLoading] = useState<boolean>(false);

  // Speak Options via TTS
  const handleHearOptions = () => {
    const langCode = (locale || "mr-IN") as any;
    const isHi = langCode.startsWith("hi");
    const isEn = langCode.startsWith("en");

    const phrase = isHi
      ? "आरोग्य सहायक में आपका स्वागत है। मोबाइल नंबर से जारी रखने के लिए पहला विकल्प चुनें, या बिना खाते के अतिथि के रूप में सहायता पाने के लिए दूसरा विकल्प चुनें। आपातकालीन सेवा के लिए १०८ पर कॉल करें।"
      : isEn
      ? "Welcome to Aarogya Sahayak. Select Continue with Mobile Number to save records, or Continue as Guest for health guidance. For emergencies, call 108."
      : "आरोग्य सहाय्यकमध्ये आपले स्वागत आहे. नोंदी जतन करण्यासाठी पहिला पर्याय मोबाईल नंबरने सुरू करा, किंवा खात्याशिवाय मार्गदर्शनासाठी दुसरा पर्याय अतिथी म्हणून सुरू करा निवडा. आपत्कालीन सेवेसाठी १०८ वर कॉल करा.";

    LanguageService.speakPhrase(phrase, langCode);
  };

  // Voice Selection with Speech Recognition fallback
  const handleSpeakSelection = () => {
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setVoiceNotice(t("citizen.speak_selection_prompt", "Say 'Mobile' or 'Guest' into the microphone"));
      setTimeout(() => setVoiceNotice(null), 3000);
      return;
    }

    try {
      const recognition = new SpeechRecognition();
      recognition.lang = locale || "mr-IN";
      recognition.continuous = false;
      recognition.interimResults = false;

      setIsListening(true);
      setVoiceNotice(t("citizen.speak_selection_prompt", "Say 'Mobile' or 'Guest' into the microphone"));

      recognition.onresult = (event: any) => {
        setIsListening(false);
        const transcript = event.results[0][0].transcript.toLowerCase();
        setVoiceNotice(null);

        if (transcript.includes("mobile") || transcript.includes("मोबाईल") || transcript.includes("phone") || transcript.includes("नंबर") || transcript.includes("पहिला")) {
          onSelectMobile();
        } else if (transcript.includes("guest") || transcript.includes("अतिथी") || transcript.includes("गेस्ट") || transcript.includes("दुसरा") || transcript.includes("मदत")) {
          handleGuestContinue();
        } else {
          setVoiceNotice(`"${transcript}" - ${t("citizen.voice_or_type_hint", "Please tap an option below")}`);
          setTimeout(() => setVoiceNotice(null), 3000);
        }
      };

      recognition.onerror = () => {
        setIsListening(false);
        setVoiceNotice(null);
      };

      recognition.onend = () => {
        setIsListening(false);
      };

      recognition.start();
    } catch (e) {
      setIsListening(false);
    }
  };

  const handleGuestContinue = async () => {
    setGuestLoading(true);
    try {
      await continueAsGuest();
      onSelectGuest();
    } finally {
      setGuestLoading(false);
    }
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        backgroundColor: "#F8FAFC",
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        alignItems: "center",
        padding: "16px 12px",
        fontFamily: "'Noto Sans', 'Noto Sans Devanagari', sans-serif"
      }}
    >
      <div
        style={{
          width: "100%",
          maxWidth: 480,
          backgroundColor: "#FFFFFF",
          borderRadius: 24,
          boxShadow: "0 12px 40px rgba(0, 0, 0, 0.08)",
          border: "1px solid #E2E8F0",
          overflow: "hidden",
          display: "flex",
          flexDirection: "column"
        }}
      >
        {/* Top Header Card */}
        <div
          style={{
            background: "linear-gradient(135deg, #1E40AF 0%, #2563EB 100%)",
            color: "#FFFFFF",
            padding: "24px 20px 20px",
            textAlign: "center",
            position: "relative"
          }}
        >
          {/* Quick Language Switcher Pill */}
          <button
            onClick={onChangeLanguage}
            style={{
              position: "absolute",
              top: 16,
              right: 16,
              padding: "6px 12px",
              backgroundColor: "rgba(255,255,255,0.2)",
              color: "#FFFFFF",
              borderRadius: 20,
              fontSize: 12,
              fontWeight: 700,
              border: "1px solid rgba(255,255,255,0.3)",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: 4
            }}
          >
            <span>{locale ? locale.substring(0, 2).toUpperCase() : "MR"}</span>
            <span style={{ fontSize: 10, opacity: 0.9 }}>▼</span>
          </button>

          {/* App Shield Icon */}
          <div
            style={{
              width: 60,
              height: 60,
              borderRadius: 20,
              backgroundColor: "#FFFFFF",
              color: "#2563EB",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              margin: "0 auto 12px",
              boxShadow: "0 8px 20px rgba(0, 0, 0, 0.15)"
            }}
          >
            <Shield size={32} />
          </div>

          <h1 style={{ fontSize: 22, fontWeight: 800, margin: "0 0 4px", letterSpacing: "-0.02em" }}>
            {t("common.app_name", "आरोग्य सहायक")}
          </h1>
          <p style={{ fontSize: 13, fontWeight: 500, margin: 0, opacity: 0.9 }}>
            {t("common.tagline", "AI-Powered Rural Healthcare Platform")}
          </p>

          {/* Voice Toolbar */}
          <div style={{ display: "flex", justifyContent: "center", gap: 10, marginTop: 16 }}>
            <button
              onClick={handleSpeakSelection}
              style={{
                minHeight: 48,
                padding: "8px 16px",
                backgroundColor: isListening ? "#EF4444" : "rgba(255,255,255,0.25)",
                color: "#FFFFFF",
                borderRadius: 24,
                border: "1px solid rgba(255,255,255,0.4)",
                fontSize: 13,
                fontWeight: 700,
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                gap: 6,
                transition: "all 0.2s"
              }}
            >
              <Mic size={18} />
              <span>{isListening ? "Listening..." : t("citizen.speak_selection", "Speak selection")}</span>
            </button>

            <button
              onClick={handleHearOptions}
              style={{
                minHeight: 48,
                padding: "8px 16px",
                backgroundColor: "rgba(255,255,255,0.25)",
                color: "#FFFFFF",
                borderRadius: 24,
                border: "1px solid rgba(255,255,255,0.4)",
                fontSize: 13,
                fontWeight: 700,
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                gap: 6
              }}
            >
              <Volume2 size={18} />
              <span>{t("citizen.hear_options", "Hear options")}</span>
            </button>
          </div>
        </div>

        {/* Voice Feedback Notice */}
        {voiceNotice && (
          <div
            style={{
              padding: "10px 16px",
              backgroundColor: "#EFF6FF",
              borderBottom: "1px solid #BFDBFE",
              color: "#1E40AF",
              fontSize: 12,
              fontWeight: 700,
              textAlign: "center"
            }}
          >
            {voiceNotice}
          </div>
        )}

        {/* Options Cards */}
        <div style={{ padding: "20px", display: "flex", flexDirection: "column", gap: 14 }}>
          {/* Option 1: Mobile Number OTP (Recommended) */}
          <button
            onClick={onSelectMobile}
            id="btn-entry-mobile-otp"
            style={{
              minHeight: 48,
              padding: "18px 16px",
              borderRadius: 20,
              border: "2px solid #2563EB",
              backgroundColor: "#EFF6FF",
              textAlign: "left",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: 16,
              boxShadow: "0 4px 14px rgba(37, 99, 235, 0.12)",
              transition: "transform 0.1s ease"
            }}
          >
            <div
              style={{
                width: 48,
                height: 48,
                borderRadius: 16,
                backgroundColor: "#2563EB",
                color: "#FFFFFF",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                flexShrink: 0
              }}
            >
              <Phone size={24} />
            </div>

            <div style={{ flex: 1 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 2 }}>
                <span style={{ fontSize: 16, fontWeight: 800, color: "#1E3A8A" }}>
                  {t("citizen.continue_with_mobile", "Continue with Mobile Number")}
                </span>
              </div>
              <p style={{ fontSize: 12, color: "#3B82F6", margin: 0, fontWeight: 600, lineHeight: 1.4 }}>
                {t("citizen.continue_with_mobile_desc", "Verify your number to securely save care records and contact ASHA or Doctor.")}
              </p>
            </div>

            <ArrowRight size={20} color="#2563EB" />
          </button>

          {/* Option 2: Continue as Guest */}
          <button
            onClick={handleGuestContinue}
            id="btn-entry-guest-access"
            disabled={guestLoading}
            style={{
              minHeight: 48,
              padding: "18px 16px",
              borderRadius: 20,
              border: "2px solid #CBD5E1",
              backgroundColor: "#FFFFFF",
              textAlign: "left",
              cursor: guestLoading ? "not-allowed" : "pointer",
              display: "flex",
              alignItems: "center",
              gap: 16,
              boxShadow: "0 2px 8px rgba(0, 0, 0, 0.04)",
              transition: "transform 0.1s ease"
            }}
          >
            <div
              style={{
                width: 48,
                height: 48,
                borderRadius: 16,
                backgroundColor: "#F1F5F9",
                color: "#475569",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                flexShrink: 0
              }}
            >
              {guestLoading ? <Loader2 size={24} className="animate-spin" /> : <UserCheck size={24} />}
            </div>

            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 16, fontWeight: 800, color: "#1E293B", marginBottom: 2 }}>
                {t("citizen.continue_as_guest", "Continue as Guest")}
              </div>
              <p style={{ fontSize: 12, color: "#64748B", margin: 0, fontWeight: 600, lineHeight: 1.4 }}>
                {t("citizen.continue_as_guest_desc", "Get general health guidance, emergency help, facility search and scheme information without creating an account.")}
              </p>
            </div>

            <ArrowRight size={20} color="#94A3B8" />
          </button>

          {/* Emergency 108 Standalone Button (Never requires login) */}
          <div style={{ marginTop: 10, paddingTop: 14, borderTop: "1px solid #F1F5F9" }}>
            <a
              href="tel:108"
              id="btn-emergency-108-dial"
              style={{
                minHeight: 48,
                padding: "14px 18px",
                borderRadius: 18,
                backgroundColor: "#DC2626",
                color: "#FFFFFF",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: 10,
                textDecoration: "none",
                fontSize: 15,
                fontWeight: 800,
                boxShadow: "0 4px 16px rgba(220, 38, 38, 0.35)",
                cursor: "pointer"
              }}
            >
              <AlertTriangle size={20} />
              <span>{t("citizen.emergency_help_108", "Call 108 Emergency Ambulance")}</span>
            </a>
          </div>
        </div>
      </div>
    </div>
  );
};
