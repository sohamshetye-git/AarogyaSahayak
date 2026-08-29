import React, { useState } from "react";
import { useLanguage } from "@aarogya/i18n";
import { Check, Volume2, Globe, Shield, ArrowRight, Info } from "lucide-react";
import { LanguageService, SUPPORTED_LANGUAGES, LanguageCode } from "../services/languageService";

interface LanguageSelectionScreenProps {
  onLanguageSelected: (langCode: LanguageCode) => void;
  isFirstLaunch?: boolean;
}

export const LanguageSelectionScreen: React.FC<LanguageSelectionScreenProps> = ({
  onLanguageSelected,
  isFirstLaunch = true
}) => {
  const { t, locale, setLocale } = useLanguage();
  const [selectedLang, setSelectedLang] = useState<LanguageCode>(() => locale || LanguageService.resolveLanguage());
  const [statusNotice, setStatusNotice] = useState<string | null>(null);

  const handleSelectLanguage = async (code: LanguageCode) => {
    setSelectedLang(code);
    await setLocale(code);
    LanguageService.saveLocalPreference(code);
  };

  const handleSpeak = (e: React.MouseEvent, phrase: string, code: LanguageCode) => {
    e.stopPropagation();
    LanguageService.speakPhrase(phrase, code);
  };

  const handleContinue = async () => {
    await setLocale(selectedLang);
    const res = await LanguageService.syncPreferenceToBackend(selectedLang);
    if (res.offlineQueued) {
      setStatusNotice(t("citizen.language_saved_notice", "Saved on this device; will sync later"));
      setTimeout(() => {
        onLanguageSelected(selectedLang);
      }, 600);
    } else {
      onLanguageSelected(selectedLang);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col justify-between items-center p-4 sm:p-6 select-none">
      {/* Container max-w for Tablet/Desktop centering */}
      <div className="w-full max-w-md bg-white rounded-3xl shadow-xl border border-slate-100 overflow-hidden flex flex-col flex-1 my-auto min-h-[640px]">

        {/* Top Header & Branding */}
        <div className="bg-gradient-to-b from-blue-50/80 to-white p-6 pb-4 text-center relative border-b border-blue-50">
          {/* Step Indicator */}
          <div className="inline-flex items-center gap-1.5 px-3 py-1 bg-blue-100/80 text-blue-700 font-semibold text-xs rounded-full mb-4">
            <Globe className="w-3.5 h-3.5" />
            <span>{t("common.step_of", { current: 1, total: 3 })}</span>
          </div>

          {/* Logo & App Name */}
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

          {/* Screen Title */}
          <h2 className="text-2xl font-black text-slate-900 mt-2 mb-1 tracking-tight">
            {t("citizen.choose_language", "Choose Your Language")}
          </h2>
          <p className="text-sm font-medium text-slate-600">
            {t("citizen.choose_language_desc", "Select language to continue")}
          </p>
        </div>

        {/* Language Selection Grid */}
        <div className="p-5 flex-1 flex flex-col justify-center gap-3">
          <div className="grid grid-cols-2 gap-3">
            {SUPPORTED_LANGUAGES.map((lang) => {
              const isSelected = selectedLang === lang.code;

              return (
                <button
                  key={lang.code}
                  type="button"
                  onClick={() => handleSelectLanguage(lang.code)}
                  className={`p-4 rounded-2xl border-2 text-left transition-all duration-200 flex flex-col justify-between min-h-[96px] relative cursor-pointer outline-none focus:ring-4 focus:ring-blue-200 ${
                    isSelected
                      ? "border-blue-600 bg-blue-50/50 shadow-md shadow-blue-500/10"
                      : "border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50/50"
                  }`}
                  style={{ minHeight: "48px" }}
                  aria-selected={isSelected}
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

                  <div className="flex items-center justify-between w-full mt-2">
                    <span className="text-xs font-semibold text-slate-500">
                      {lang.englishLabel} {lang.subLabel ? `(${lang.subLabel})` : ""}
                    </span>

                    {/* Listen / TTS Button */}
                    <button
                      type="button"
                      onClick={(e) => handleSpeak(e, lang.ttsPhrase, lang.code)}
                      title={t("common.listen", "Listen")}
                      className="p-1.5 rounded-lg bg-blue-100/70 hover:bg-blue-200 text-blue-700 transition-colors flex items-center gap-1 text-[10px] font-bold"
                    >
                      <Volume2 className="w-3.5 h-3.5" />
                      <span className="hidden sm:inline">{t("common.listen", "Listen")}</span>
                    </button>
                  </div>
                </button>
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

        {/* Sticky Footer Continue Action */}
        <div className="p-5 pt-3 bg-white border-t border-slate-100">
          <button
            type="button"
            id="btn-language-continue"
            onClick={handleContinue}
            className="w-full py-4 px-6 bg-blue-600 hover:bg-blue-700 active:bg-blue-800 text-white font-bold text-base rounded-2xl shadow-lg shadow-blue-500/25 transition-all flex items-center justify-center gap-2 cursor-pointer min-h-[48px] focus:ring-4 focus:ring-blue-300"
          >
            <span>{t("common.continue", "Continue")}</span>
            <ArrowRight className="w-5 h-5 stroke-[2.5]" />
          </button>

        </div>
      </div>
    </div>
  );
};

