import i18next, { i18n as I18nInstance } from "i18next";
import { initReactI18next } from "react-i18next";
import enIN from "./locales/en-IN.json";
import hiIN from "./locales/hi-IN.json";
import mrIN from "./locales/mr-IN.json";
import { SupportedLanguage, resolveInitialLanguage, normalizeLanguageCode } from "./config";

export * from "./config";
export * from "./formatters";
export * from "./translationKeys";
export * from "./validator";
export * from "./LanguageContext";

const bundleEn = { ...enIN, translation: enIN };
const bundleHi = { ...hiIN, translation: hiIN };
const bundleMr = { ...mrIN, translation: mrIN };

export const resources = {
  "en-IN": bundleEn,
  "hi-IN": bundleHi,
  "mr-IN": bundleMr,
  en: bundleEn,
  hi: bundleHi,
  mr: bundleMr,
};

export function createI18nInstance(
  initialLang?: SupportedLanguage | string | null,
  fallback: SupportedLanguage = "mr-IN"
): I18nInstance {
  const resolved = normalizeLanguageCode(resolveInitialLanguage(initialLang, fallback), fallback);
  const instance = i18next.createInstance();

  instance.use(initReactI18next).init({
    resources,
    lng: resolved,
    fallbackLng: "en-IN",
    supportedLngs: ["en-IN", "hi-IN", "mr-IN", "en", "hi", "mr"],
    interpolation: {
      escapeValue: false,
    },
    defaultNS: "translation",
    fallbackNS: [
      "common",
      "navigation",
      "authentication",
      "citizen",
      "chat",
      "asha",
      "doctor",
      "admin",
      "patient",
      "case",
      "referral",
      "consultation",
      "investigation",
      "prescription",
      "followup",
      "scheme",
      "facility",
      "safety",
      "status",
      "priority",
      "roles",
      "messages",
      "requestType",
      "validation",
      "errors",
      "loading",
      "emptyState",
      "offline",
      "notifications",
      "accessibility",
    ],
    react: {
      useSuspense: false,
    },
  });

  return instance;
}

export const defaultI18n = createI18nInstance();
export default defaultI18n;

