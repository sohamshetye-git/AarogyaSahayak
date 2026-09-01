import React, { useState, useEffect, useRef } from "react";
import { useLanguage, SupportedLanguage } from "@aarogya/i18n";
import {
  Phone,
  UserCheck,
  Shield,
  Mic,
  Volume2,
  AlertTriangle,
  ArrowRight,
  Loader2,
  Globe,
  Sparkles,
  PhoneCall,
  X,
  MapPin,
  ChevronDown
} from "lucide-react";
import { useCitizenAuth } from "../../context/CitizenAuthContext";
import { LanguageService, SUPPORTED_LANGUAGES, LanguageCode } from "../../services/languageService";

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
  const { t, locale, setLocale } = useLanguage();
  const { continueAsGuest } = useCitizenAuth();

  const [isListening, setIsListening] = useState<boolean>(false);
  const [voiceNotice, setVoiceNotice] = useState<string | null>(null);
  const [guestLoading, setGuestLoading] = useState<boolean>(false);
  const [mobileLoading, setMobileLoading] = useState<boolean>(false);
  const [showEmergencyModal, setShowEmergencyModal] = useState<boolean>(false);
  const [showLangDropdown, setShowLangDropdown] = useState<boolean>(false);
  const langDropdownRef = useRef<HTMLDivElement>(null);

  // Close language dropdown on outside click
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (langDropdownRef.current && !langDropdownRef.current.contains(event.target as Node)) {
        setShowLangDropdown(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const currentLangObj = SUPPORTED_LANGUAGES.find((l) => l.code === locale) || SUPPORTED_LANGUAGES[0];

  const handleSelectLang = async (langCode: LanguageCode) => {
    setShowLangDropdown(false);
    await setLocale(langCode);
    LanguageService.saveLocalPreference(langCode);
  };

  // Speak Options via TTS
  const handleHearOptions = () => {
    const langCode = (locale || "mr-IN") as LanguageCode;
    const phrase = t(
      "citizen.entry_welcome_tts",
      "Welcome to Aarogya Sahayak. Choose Continue with Mobile Number to save records, or Continue as Guest for instant health guidance. For emergencies, call 108."
    );
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
        const transcript = (event.results[0][0].transcript || "").toLowerCase();
        setVoiceNotice(null);

        if (
          transcript.includes("mobile") ||
          transcript.includes("मोबाईल") ||
          transcript.includes("मोबाइल") ||
          transcript.includes("phone") ||
          transcript.includes("फोन") ||
          transcript.includes("पहिला") ||
          transcript.includes("पहला") ||
          transcript.includes("one") ||
          transcript.includes("1")
        ) {
          handleMobileContinue();
        } else if (
          transcript.includes("guest") ||
          transcript.includes("अतिथी") ||
          transcript.includes("गेस्ट") ||
          transcript.includes("दुसरा") ||
          transcript.includes("दूसरा") ||
          transcript.includes("two") ||
          transcript.includes("2")
        ) {
          handleGuestContinue();
        } else if (
          transcript.includes("emergency") ||
          transcript.includes("108") ||
          transcript.includes("१०८") ||
          transcript.includes("आपत्कालीन") ||
          transcript.includes("आपातकालीन") ||
          transcript.includes("ambulance")
        ) {
          setShowEmergencyModal(true);
        } else {
          setVoiceNotice(`"${transcript}" — ${t("citizen.voice_or_type_hint", "Please select an option below")}`);
          setTimeout(() => setVoiceNotice(null), 3500);
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

  const handleMobileContinue = () => {
    if (mobileLoading || guestLoading) return;
    setMobileLoading(true);
    onSelectMobile();
  };

  const handleGuestContinue = async () => {
    if (guestLoading || mobileLoading) return;
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
      className="w-full flex-1 flex flex-col items-center justify-start sm:justify-center"
      style={{
        minHeight: "100dvh",
        backgroundColor: "#F8FAFC",
        paddingTop: "max(0px, var(--safe-area-top))",
        paddingBottom: "max(16px, var(--safe-area-bottom))",
        paddingLeft: "max(0px, var(--safe-area-left))",
        paddingRight: "max(0px, var(--safe-area-right))"
      }}
    >
      {/* Container: 100% on Mobile (<=480px), Max 430px Centered on Tablet/Desktop */}
      <main
        className="w-full sm:max-w-[430px] flex-1 sm:flex-initial flex flex-col bg-white sm:rounded-3xl sm:shadow-2xl sm:border sm:border-slate-200 overflow-hidden sm:my-auto transition-all duration-200"
        style={{ minHeight: "100dvh" }}
      >
        {/* Compact Blue Brand Header */}
        <header
          className="relative bg-gradient-to-b from-[#1E3A8A] via-[#1E40AF] to-[#2563EB] text-white px-4 pt-4 pb-4 shrink-0 shadow-md"
        >
          {/* Top Row: Brand & Language Selector */}
          <div className="flex items-center justify-between gap-2 mb-3">
            {/* Logo Badge & Title Group */}
            <div className="flex items-center gap-3">
              <div
                className="w-11 h-11 rounded-2xl bg-white/10 backdrop-blur-md border border-white/30 flex items-center justify-center shadow-inner shrink-0"
                aria-hidden="true"
              >
                <Shield className="w-6 h-6 text-white drop-shadow" />
              </div>
              <div className="flex flex-col">
                <h1 className="text-lg font-extrabold tracking-tight text-white leading-tight">
                  {t("common.app_name", "आरोग्य सहायक")}
                </h1>
                <span className="text-[11px] font-medium text-blue-100/90 leading-none">
                  {t("citizen.entry_tagline", "ग्रामीण आरोग्यासाठी एआय सहाय्यक")}
                </span>
              </div>
            </div>

            {/* Quick Language Selector Pill */}
            <div className="relative" ref={langDropdownRef}>
              <button
                type="button"
                id="btn-entry-language-selector"
                onClick={() => setShowLangDropdown(!showLangDropdown)}
                aria-haspopup="listbox"
                aria-expanded={showLangDropdown}
                aria-label={t("citizen.select_language", "Select Language")}
                className="min-h-[44px] px-3 py-1.5 bg-white/15 hover:bg-white/25 active:bg-white/30 text-white rounded-full text-xs font-bold border border-white/30 flex items-center gap-1.5 transition-all cursor-pointer focus:outline-none focus:ring-2 focus:ring-white/80"
              >
                <Globe className="w-3.5 h-3.5" />
                <span className="max-w-[70px] truncate">{currentLangObj.nativeName}</span>
                <ChevronDown className={`w-3 h-3 transition-transform duration-200 ${showLangDropdown ? "rotate-180" : ""}`} />
              </button>

              {/* Language Dropdown Menu */}
              {showLangDropdown && (
                <div
                  role="listbox"
                  aria-label={t("citizen.select_language", "Select Language")}
                  className="absolute right-0 top-full mt-2 w-48 bg-white rounded-2xl shadow-2xl border border-slate-200 py-1.5 z-50 animate-in fade-in zoom-in-95 duration-150 overflow-hidden"
                >
                  <div className="px-3 py-1.5 text-[11px] font-bold text-slate-400 uppercase tracking-wider border-b border-slate-100">
                    {t("citizen.select_language", "Select Language")}
                  </div>
                  <div className="max-h-60 overflow-y-auto">
                    {SUPPORTED_LANGUAGES.map((lang) => {
                      const isSelected = lang.code === locale;
                      return (
                        <button
                          key={lang.code}
                          role="option"
                          aria-selected={isSelected}
                          onClick={() => handleSelectLang(lang.code)}
                          className={`w-full min-h-[44px] px-3 py-2 text-left flex items-center justify-between text-xs font-semibold transition-colors cursor-pointer ${
                            isSelected
                              ? "bg-blue-50 text-blue-700 font-bold"
                              : "text-slate-700 hover:bg-slate-50"
                          }`}
                        >
                          <div className="flex flex-col">
                            <span className="text-sm font-bold">{lang.nativeName}</span>
                            <span className="text-[10px] text-slate-400">{lang.englishLabel}</span>
                          </div>
                          {isSelected && <span className="w-2 h-2 rounded-full bg-blue-600"></span>}
                        </button>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Accessible Audio & Voice Secondary Controls Toolbar */}
          <div className="flex items-center gap-2 pt-2 border-t border-white/15">
            <button
              type="button"
              id="btn-entry-speak-selection"
              onClick={handleSpeakSelection}
              aria-label={t("citizen.speak_selection", "Speak Selection")}
              className={`flex-1 min-h-[48px] px-3 py-2 rounded-xl text-xs font-bold flex items-center justify-center gap-2 border transition-all cursor-pointer focus:outline-none focus:ring-2 focus:ring-white/80 ${
                isListening
                  ? "bg-rose-600 text-white border-rose-400 animate-pulse shadow-lg"
                  : "bg-white/15 hover:bg-white/20 active:bg-white/30 text-white border-white/25"
              }`}
            >
              <Mic className={`w-4 h-4 shrink-0 ${isListening ? "animate-bounce" : ""}`} />
              <span className="truncate">
                {isListening ? t("citizen.listening", "Listening...") : t("citizen.speak_selection", "Speak Selection")}
              </span>
            </button>

            <button
              type="button"
              id="btn-entry-hear-options"
              onClick={handleHearOptions}
              aria-label={t("citizen.hear_options", "Hear Options")}
              className="flex-1 min-h-[48px] px-3 py-2 bg-white/15 hover:bg-white/20 active:bg-white/30 text-white rounded-xl text-xs font-bold border border-white/25 flex items-center justify-center gap-2 transition-all cursor-pointer focus:outline-none focus:ring-2 focus:ring-white/80"
            >
              <Volume2 className="w-4 h-4 shrink-0" />
              <span className="truncate">{t("citizen.hear_options", "Hear Options")}</span>
            </button>
          </div>
        </header>

        {/* Voice Feedback Notice */}
        {voiceNotice && (
          <div
            role="status"
            aria-live="polite"
            className="px-4 py-2.5 bg-blue-50 border-b border-blue-200 text-blue-900 text-xs font-bold text-center flex items-center justify-center gap-2 animate-fadeIn"
          >
            <Sparkles className="w-4 h-4 text-blue-600 shrink-0" />
            <span className="break-words">{voiceNotice}</span>
          </div>
        )}

        {/* Scrollable Main Content Body */}
        <div className="flex-1 flex flex-col justify-between px-4 py-5 gap-4 overflow-y-auto">
          {/* Main Action Group */}
          <div className="flex flex-col gap-3.5">
            {/* Primary Action: Continue with Mobile Number */}
            <button
              type="button"
              id="btn-entry-mobile-otp"
              onClick={handleMobileContinue}
              disabled={mobileLoading || guestLoading}
              aria-label={t("citizen.continue_with_mobile", "Continue with Mobile Number")}
              className="group w-full min-h-[56px] p-4 rounded-2xl border-2 border-blue-600 bg-blue-50/70 hover:bg-blue-100/70 active:bg-blue-100 text-left transition-all duration-150 flex items-center gap-3.5 shadow-sm hover:shadow-md cursor-pointer focus:outline-none focus:ring-4 focus:ring-blue-300 disabled:opacity-60 disabled:cursor-not-allowed"
            >
              <div
                className="w-12 h-12 rounded-xl bg-blue-600 text-white flex items-center justify-center shrink-0 shadow-md group-hover:scale-105 transition-transform"
                aria-hidden="true"
              >
                {mobileLoading ? <Loader2 className="w-6 h-6 animate-spin" /> : <Phone className="w-6 h-6" />}
              </div>

              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-0.5 flex-wrap">
                  <span className="text-base font-extrabold text-blue-950 leading-tight">
                    {t("citizen.continue_with_mobile", "Continue with Mobile Number")}
                  </span>
                  <span className="px-2 py-0.5 rounded-full text-[10px] font-extrabold bg-blue-200/90 text-blue-800 tracking-wide uppercase shrink-0">
                    {t("citizen.primary_action_badge", "Recommended")}
                  </span>
                </div>
                <p className="text-xs text-blue-700/90 font-medium leading-relaxed break-words line-clamp-2">
                  {t(
                    "citizen.continue_with_mobile_desc",
                    "Verify your number to securely save care records and contact ASHA or Doctor."
                  )}
                </p>
              </div>

              <ArrowRight className="w-5 h-5 text-blue-600 shrink-0 group-hover:translate-x-1 transition-transform" />
            </button>

            {/* Secondary Action: Continue as Guest */}
            <button
              type="button"
              id="btn-entry-guest-access"
              onClick={handleGuestContinue}
              disabled={guestLoading || mobileLoading}
              aria-label={t("citizen.continue_as_guest", "Continue as Guest")}
              className="group w-full min-h-[56px] p-4 rounded-2xl border-2 border-slate-200 bg-white hover:bg-slate-50 active:bg-slate-100 text-left transition-all duration-150 flex items-center gap-3.5 shadow-sm hover:border-slate-300 cursor-pointer focus:outline-none focus:ring-4 focus:ring-slate-300 disabled:opacity-60 disabled:cursor-not-allowed"
            >
              <div
                className="w-12 h-12 rounded-xl bg-slate-100 text-slate-700 flex items-center justify-center shrink-0 border border-slate-200 group-hover:scale-105 transition-transform"
                aria-hidden="true"
              >
                {guestLoading ? <Loader2 className="w-6 h-6 animate-spin text-blue-600" /> : <UserCheck className="w-6 h-6" />}
              </div>

              <div className="flex-1 min-w-0">
                <div className="text-base font-extrabold text-slate-900 leading-tight mb-0.5">
                  {t("citizen.continue_as_guest", "Continue as Guest")}
                </div>
                <p className="text-xs text-slate-500 font-medium leading-relaxed break-words line-clamp-2">
                  {t(
                    "citizen.continue_as_guest_desc",
                    "Get general health guidance, emergency help, facility search and scheme information without creating an account."
                  )}
                </p>
              </div>

              <ArrowRight className="w-5 h-5 text-slate-400 shrink-0 group-hover:translate-x-1 transition-transform" />
            </button>
          </div>

          {/* Clearly Separated Emergency Action Footer */}
          <div className="pt-3 border-t border-slate-100 mt-auto">
            <button
              type="button"
              id="btn-emergency-108-entry"
              onClick={() => setShowEmergencyModal(true)}
              aria-label={t("citizen.emergency_call_108", "108 Emergency Ambulance")}
              className="w-full min-h-[48px] py-3.5 px-4 rounded-2xl bg-rose-600 hover:bg-rose-700 active:bg-rose-800 text-white font-extrabold text-sm flex items-center justify-center gap-2.5 shadow-md shadow-rose-600/20 hover:shadow-lg transition-all cursor-pointer focus:outline-none focus:ring-4 focus:ring-rose-300"
            >
              <div className="w-7 h-7 rounded-lg bg-white/20 flex items-center justify-center shrink-0" aria-hidden="true">
                <AlertTriangle className="w-4 h-4 text-white" />
              </div>
              <span className="tracking-wide">{t("citizen.emergency_call_108", "108 Emergency Ambulance")}</span>
            </button>
          </div>
        </div>
      </main>

      {/* Emergency Confirmation Sheet / Modal */}
      {showEmergencyModal && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="emergency-dialog-title"
          className="fixed inset-0 bg-slate-950/70 backdrop-blur-xs flex items-end sm:items-center justify-center z-50 p-0 sm:p-4 animate-in fade-in duration-200"
        >
          <div
            className="w-full sm:max-w-md bg-white rounded-t-3xl sm:rounded-3xl p-5 sm:p-6 flex flex-col gap-4 shadow-2xl border border-slate-100 animate-in slide-in-from-bottom sm:slide-in-from-bottom-6 duration-250"
            style={{
              paddingBottom: "max(24px, var(--safe-area-bottom))"
            }}
          >
            {/* Modal Header */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2.5 text-rose-600">
                <div className="w-9 h-9 rounded-xl bg-rose-100 flex items-center justify-center shrink-0">
                  <AlertTriangle className="w-5 h-5 text-rose-600" />
                </div>
                <h2 id="emergency-dialog-title" className="text-lg font-extrabold text-slate-900 leading-tight">
                  {t("citizen.emergency_confirm_title", "108 Emergency Ambulance Call")}
                </h2>
              </div>
              <button
                type="button"
                id="btn-close-emergency-modal"
                onClick={() => setShowEmergencyModal(false)}
                aria-label={t("common.close", "Close")}
                className="w-9 h-9 rounded-full bg-slate-100 hover:bg-slate-200 active:bg-slate-300 flex items-center justify-center text-slate-600 transition-colors cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Warning Message Card */}
            <div className="p-3.5 bg-rose-50 border border-rose-200 rounded-2xl text-xs font-semibold text-rose-900 leading-relaxed">
              {t(
                "citizen.emergency_confirm_desc",
                "You are about to dial the National 108 Emergency Service. Use this for severe medical emergencies, chest pain, trauma, unconsciousness, or maternity distress."
              )}
            </div>

            {/* Action Buttons */}
            <div className="flex flex-col gap-2.5 pt-1">
              <a
                href="tel:108"
                id="btn-confirm-dial-108"
                onClick={() => setShowEmergencyModal(false)}
                className="w-full min-h-[50px] py-3.5 px-4 rounded-2xl bg-rose-600 hover:bg-rose-700 active:bg-rose-800 text-white font-extrabold text-base flex items-center justify-center gap-2.5 shadow-lg shadow-rose-600/30 transition-all text-center no-underline cursor-pointer focus:outline-none focus:ring-4 focus:ring-rose-300"
              >
                <PhoneCall className="w-5 h-5" />
                <span>{t("citizen.emergency_confirm_call", "Call 108 Ambulance Now")}</span>
              </a>

              <button
                type="button"
                id="btn-cancel-emergency-dialog"
                onClick={() => setShowEmergencyModal(false)}
                className="w-full min-h-[46px] py-2.5 px-4 rounded-2xl bg-slate-100 hover:bg-slate-200 active:bg-slate-300 text-slate-700 font-bold text-sm transition-all cursor-pointer"
              >
                {t("citizen.emergency_confirm_cancel", "Cancel")}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
