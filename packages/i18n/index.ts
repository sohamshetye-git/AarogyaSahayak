import i18next, { i18n as I18nInstance } from "i18next";
import { initReactI18next } from "react-i18next";
import enIN from "./locales/en-IN.json";
import hiIN from "./locales/hi-IN.json";
import mrIN from "./locales/mr-IN.json";
import guIN from "./locales/gu-IN.json";
import bnIN from "./locales/bn-IN.json";
import knIN from "./locales/kn-IN.json";
import teIN from "./locales/te-IN.json";
import taIN from "./locales/ta-IN.json";
import mlIN from "./locales/ml-IN.json";
import paIN from "./locales/pa-IN.json";
import odIN from "./locales/od-IN.json";
import { SupportedLanguage, resolveInitialLanguage, normalizeLanguageCode } from "./config";

export * from "./config";
export * from "./formatters";
export * from "./translationKeys";
export * from "./validator";
export * from "./LanguageContext";

const bundleEn = { ...enIN, translation: enIN };
const bundleHi = { ...hiIN, translation: hiIN };
const bundleMr = { ...mrIN, translation: mrIN };
const bundleGu = { ...guIN, translation: guIN };
const bundleBn = { ...bnIN, translation: bnIN };
const bundleKn = { ...knIN, translation: knIN };
const bundleTe = { ...teIN, translation: teIN };
const bundleTa = { ...taIN, translation: taIN };
const bundleMl = { ...mlIN, translation: mlIN };
const bundlePa = { ...paIN, translation: paIN };
const bundleOd = { ...odIN, translation: odIN };

export const resources = {
  "en-IN": bundleEn,
  "hi-IN": bundleHi,
  "mr-IN": bundleMr,
  "gu-IN": bundleGu,
  "bn-IN": bundleBn,
  "kn-IN": bundleKn,
  "te-IN": bundleTe,
  "ta-IN": bundleTa,
  "ml-IN": bundleMl,
  "pa-IN": bundlePa,
  "od-IN": bundleOd,
  en: bundleEn,
  hi: bundleHi,
  mr: bundleMr,
  gu: bundleGu,
  bn: bundleBn,
  kn: bundleKn,
  te: bundleTe,
  ta: bundleTa,
  ml: bundleMl,
  pa: bundlePa,
  od: bundleOd,
  or: bundleOd,
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
    supportedLngs: [
      "en-IN", "hi-IN", "mr-IN", "gu-IN", "bn-IN", "kn-IN", "te-IN", "ta-IN", "ml-IN", "pa-IN", "od-IN",
      "en", "hi", "mr", "gu", "bn", "kn", "te", "ta", "ml", "pa", "od", "or",
    ],
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

