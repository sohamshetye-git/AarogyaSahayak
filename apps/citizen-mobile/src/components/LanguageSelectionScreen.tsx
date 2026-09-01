import React, { useState, useEffect } from "react";
import { useLanguage } from "@aarogya/i18n";
import { Check, Volume2, Square, Loader2, RotateCcw, Globe, Shield, ArrowRight, ArrowLeft, Info, CheckCircle2 } from "lucide-react";
import { LanguageService, SUPPORTED_LANGUAGES, LanguageCode } from "../services/languageService";
import { ttsPlayerService, TtsButtonState } from "../services/ttsPlayerService";

export type LanguageScreenMode = "onboarding" | "change";

interface LanguageSelectionScreenProps {
  onLanguageSelected?: (langCode: LanguageCode) => void;
  isFirstLaunch?: boolean;
  mode?: LanguageScreenMode;
  onBack?: () => void;
  onSave?: (selectedLang: LanguageCode) => void;
  initialLanguage?: LanguageCode;
}

export const LanguageSelectionScreen: React.FC<LanguageSelectionScreenProps> = ({
  onLanguageSelected,
  isFirstLaunch = true,
  mode = "onboarding",
  onBack,
  onSave,
  initialLanguage
}) => {
  const { t, locale, setLocale } = useLanguage();
  const [selectedLang, setSelectedLang] = useState<LanguageCode>(() => {
    if (initialLanguage) return initialLanguage;
    if (locale) return locale;
    return LanguageService.resolveLanguage();
  });
  const [statusNotice, setStatusNotice] = useState<string | null>(null);
  const [ttsStates, setTtsStates] = useState<Record<string, TtsButtonState>>({});
  const [saving, setSaving] = useState<boolean>(false);

  useEffect(() => {
    const unsubscribe = ttsPlayerService.subscribe((states) => {
      setTtsStates(states);
    });
    return () => {
      unsubscribe();
      ttsPlayerService.stop();
    };
  }, []);

  const handleSelectLanguage = (code: LanguageCode) => {
    setSelectedLang(code);
    if (mode === "onboarding") {
      setLocale(code);
      LanguageService.saveLocalPreference(code);
    }
  };

  const handleListenClick = async (e: React.MouseEvent, lang: typeof SUPPORTED_LANGUAGES[0]) => {
    e.stopPropagation();
    e.preventDefault();

    // Synchronously unlock AudioContext within user event callstack
    ttsPlayerService.ensureAudioContextUnlocked();

    const currentState = ttsStates[lang.code] || "idle";
    if (currentState === "playing") {
      ttsPlayerService.stop();
      return;
    }

    const previewText = lang.ttsPhrase;
    await ttsPlayerService.playPreview(lang.code, previewText);
  };

  const handleContinue = async () => {
    ttsPlayerService.stop();
    await setLocale(selectedLang);
    const res = await LanguageService.syncPreferenceToBackend(selectedLang);
    if (res.offlineQueued) {
      setStatusNotice(t("citizen.language_saved_notice", "Saved on this device; will sync later"));
      setTimeout(() => {
        if (onLanguageSelected) {
          onLanguageSelected(selectedLang);
        }
      }, 600);
    } else {
      if (onLanguageSelected) {
        onLanguageSelected(selectedLang);
      }
    }
  };

  const handleSaveLanguage = async () => {
    setSaving(true);
    ttsPlayerService.stop();
    try {
      await setLocale(selectedLang);
      LanguageService.saveLocalPreference(selectedLang);
      await LanguageService.syncPreferenceToBackend(selectedLang);
      if (onSave) {
        onSave(selectedLang);
      }
    } finally {
      setSaving(false);
    }
  };

  const handleCancel = () => {
    ttsPlayerService.stop();
    if (onBack) {
      onBack();
    }
  };

  const isChangeMode = mode === "change";

  return (
    <div
      className="w-full flex-1 flex flex-col justify-between items-center sm:p-4 select-none"
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
      <div className="w-full sm:max-w-[430px] bg-white sm:rounded-3xl sm:shadow-xl sm:border sm:border-slate-200 overflow-hidden flex flex-col flex-1 sm:my-4 min-h-[100dvh] sm:min-h-[640px]">

        {/* Top Header & Branding */}
        <div className="bg-gradient-to-b from-blue-50/80 to-white p-6 pb-4 text-center relative border-b border-blue-50">
          {/* Header Action Row in Change Mode vs Step Badge in Onboarding Mode */}
          {isChangeMode ? (
            <div className="flex items-center justify-between w-full mb-3">
              <button
                type="button"
                id="btn-language-back"
                onClick={handleCancel}
                aria-label={t("common.back", "Back")}
                className="w-10 h-10 rounded-full bg-white hover:bg-slate-100 active:bg-slate-200 text-slate-700 flex items-center justify-center border border-slate-200 shadow-sm transition-colors cursor-pointer"
              >
                <ArrowLeft className="w-5 h-5" />
              </button>

              <div className="inline-flex items-center gap-1.5 px-3 py-1 bg-blue-100/80 text-blue-700 font-semibold text-xs rounded-full">
                <Globe className="w-3.5 h-3.5" />
                <span>{t("common.change_language", "Change Language")}</span>
              </div>

              <div className="w-10" />
            </div>
          ) : (
            <div
              id="badge-onboarding-step-1"
              className="inline-flex items-center gap-1.5 px-3 py-1 bg-blue-100/80 text-blue-700 font-semibold text-xs rounded-full mb-4"
            >
              <Globe className="w-3.5 h-3.5" />
              <span>{t("common.step_of", { current: 1, total: 3 })}</span>
            </div>
          )}

          {/* Logo & App Name (Only in onboarding mode or compact branding in change mode) */}
          {!isChangeMode ? (
            <div className="flex flex-col items-center mb-3">
              <div className="w-16 h-16 bg-blue-600 rounded-2xl flex items-center justify-center shadow-lg shadow-blue-500/30 mb-2 border-2 border-white">
                <Shield className="w-9 h-9 text-white" />
              </div>
              <h1 className="text-xl font-bold text-slate-900 tracking-tight">
                {t("common.app_name", "आरोग्य सहायक")}
              </h1>
              <p className="text-xs font-medium text-slate-500">
                {t("common.tagline", "AI-Powered Rural Healthcare Platform")}
              </p>
            </div>
          ) : (
            <div className="flex items-center justify-center gap-2 mb-2 text-slate-700">
              <Shield className="w-5 h-5 text-blue-600" />
              <span className="text-sm font-bold text-slate-800">{t("common.app_name", "आरोग्य सहायक")}</span>
            </div>
          )}

          {/* Screen Title */}
          <h2 className="text-2xl font-black text-slate-900 mt-1 mb-1 tracking-tight">
            {isChangeMode
              ? t("common.change_language", "Change Language")
              : t("citizen.choose_language", "Choose Your Language")}
          </h2>
          <p className="text-sm font-medium text-slate-600">
            {isChangeMode
              ? t("citizen.choose_language_desc", "Select the language you are most comfortable speaking and reading in.")
              : t("citizen.choose_language_desc", "Select language to continue")}
          </p>
        </div>

        {/* Language Selection Grid */}
        <div className="p-5 flex-1 flex flex-col justify-center gap-3">
          <div className="grid grid-cols-2 gap-3">
            {SUPPORTED_LANGUAGES.map((lang) => {
              const isSelected = selectedLang === lang.code;
              const buttonState = ttsStates[lang.code] || "idle";

              return (
                <div
                  key={lang.code}
                  role="button"
                  tabIndex={0}
                  id={`btn-select-lang-${lang.code}`}
                  onClick={() => handleSelectLanguage(lang.code)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      e.preventDefault();
                      handleSelectLanguage(lang.code);
                    }
                  }}
                  className={`p-4 rounded-2xl border-2 text-left transition-all duration-200 flex flex-col justify-between min-h-[104px] relative cursor-pointer outline-none focus:ring-4 focus:ring-blue-200 ${
                    isSelected
                      ? "border-blue-600 bg-blue-50/50 shadow-md shadow-blue-500/10"
                      : "border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50/50"
                  }`}
                  aria-selected={isSelected}
                  aria-label={`${lang.nativeName} (${lang.englishLabel})`}
                >
                  <div className="flex items-center justify-between w-full">
                    <span className={`text-xl font-bold tracking-wide ${isSelected ? "text-blue-700" : "text-slate-900"}`}>
                      {lang.nativeName}
                    </span>
                    {isSelected ? (
                      <div className="w-6 h-6 rounded-full bg-blue-600 flex items-center justify-center shadow-sm">
                        <Check className="w-4 h-4 text-white stroke-[3]" />
                      </div>
                    ) : (
                      <div className="w-6 h-6 rounded-full border-2 border-slate-300" />
                    )}
                  </div>

                  <div className="flex items-center justify-between w-full mt-2 gap-1">
                    <span className="text-xs font-semibold text-slate-500 truncate">
                      {lang.englishLabel} {lang.subLabel && lang.subLabel !== lang.englishLabel ? `(${lang.subLabel})` : ""}
                    </span>

                    {/* Listen / TTS Button */}
                    <button
                      type="button"
                      id={`btn-listen-${lang.code}`}
                      onClick={(e) => handleListenClick(e, lang)}
                      aria-label={`${buttonState === "playing" ? t("common.stop", "Stop") : buttonState === "error" ? t("common.retry", "Retry") : t("common.listen", "Listen")} preview in ${lang.englishLabel}`}
                      aria-pressed={buttonState === "playing"}
                      disabled={buttonState === "loading"}
                      className={`p-1.5 px-2 rounded-lg transition-all flex items-center gap-1 text-[11px] font-bold cursor-pointer shrink-0 outline-none focus:ring-2 focus:ring-blue-400 ${
                        buttonState === "playing"
                          ? "bg-amber-500 text-white shadow-sm hover:bg-amber-600 animate-pulse"
                          : buttonState === "loading"
                          ? "bg-slate-200 text-slate-500 cursor-not-allowed"
                          : buttonState === "error"
                          ? "bg-rose-100 text-rose-700 hover:bg-rose-200"
                          : "bg-blue-100/80 hover:bg-blue-200 text-blue-700 active:bg-blue-300"
                      }`}
                    >
                      {buttonState === "loading" ? (
                        <>
                          <Loader2 className="w-3.5 h-3.5 animate-spin" />
                          <span className="hidden sm:inline text-[10px]">...</span>
                        </>
                      ) : buttonState === "playing" ? (
                        <>
                          <Square className="w-3 h-3 fill-current" />
                          <span className="inline">{t("common.stop", "Stop")}</span>
                        </>
                      ) : buttonState === "error" ? (
                        <>
                          <RotateCcw className="w-3.5 h-3.5" />
                          <span className="hidden sm:inline">{t("common.retry", "Retry")}</span>
                        </>
                      ) : (
                        <>
                          <Volume2 className="w-3.5 h-3.5" />
                          <span className="hidden sm:inline">{t("common.listen", "Listen")}</span>
                        </>
                      )}
                    </button>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Localized Offline Sync Toast Notice */}
          {statusNotice && (
            <div className="mt-2 p-3 bg-amber-50 border border-amber-200 text-amber-800 rounded-xl text-xs font-semibold flex items-center gap-2 animate-fade-in">
              <Info className="w-4 h-4 text-amber-600 flex-shrink-0" />
              <span>{statusNotice}</span>
            </div>
          )}
        </div>

        {/* Sticky Footer Actions */}
        <div className="p-5 pt-3 bg-white border-t border-slate-100">
          {isChangeMode ? (
            <div className="flex items-center gap-3">
              <button
                type="button"
                id="btn-language-cancel"
                onClick={handleCancel}
                className="flex-1 py-3.5 px-4 bg-slate-100 hover:bg-slate-200 active:bg-slate-300 text-slate-700 font-bold text-sm rounded-2xl transition-all flex items-center justify-center cursor-pointer min-h-[48px]"
              >
                {t("common.cancel", "Cancel")}
              </button>
              <button
                type="button"
                id="btn-language-save"
                onClick={handleSaveLanguage}
                disabled={saving}
                className="flex-[2] py-3.5 px-6 bg-blue-600 hover:bg-blue-700 active:bg-blue-800 text-white font-bold text-sm rounded-2xl shadow-lg shadow-blue-500/25 transition-all flex items-center justify-center gap-2 cursor-pointer min-h-[48px] focus:ring-4 focus:ring-blue-300 disabled:opacity-60"
              >
                {saving ? <Loader2 className="w-5 h-5 animate-spin" /> : <CheckCircle2 className="w-5 h-5" />}
                <span>{t("citizen.save_language", "Save Language")}</span>
              </button>
            </div>
          ) : (
            <button
              type="button"
              id="btn-language-continue"
              onClick={handleContinue}
              className="w-full py-4 px-6 bg-blue-600 hover:bg-blue-700 active:bg-blue-800 text-white font-bold text-base rounded-2xl shadow-lg shadow-blue-500/25 transition-all flex items-center justify-center gap-2 cursor-pointer min-h-[48px] focus:ring-4 focus:ring-blue-300"
            >
              <span>{t("common.continue", "Continue")}</span>
              <ArrowRight className="w-5 h-5 stroke-[2.5]" />
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
