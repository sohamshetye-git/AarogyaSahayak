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

function getDeepKeys(obj: Record<string, any>, prefix = ""): string[] {
  return Object.keys(obj).reduce((res: string[], el: string) => {
    const name = prefix ? `${prefix}.${el}` : el;
    if (typeof obj[el] === "object" && obj[el] !== null && !Array.isArray(obj[el])) {
      return [...res, ...getDeepKeys(obj[el], name)];
    }
    return [...res, name];
  }, []);
}

export const ALL_LOCALES = {
  "en-IN": enIN,
  "hi-IN": hiIN,
  "mr-IN": mrIN,
  "gu-IN": guIN,
  "bn-IN": bnIN,
  "kn-IN": knIN,
  "te-IN": teIN,
  "ta-IN": taIN,
  "ml-IN": mlIN,
  "pa-IN": paIN,
  "od-IN": odIN,
};

export function validateLocaleParity(): {
  valid: boolean;
  totalKeys: number;
  missingInHi: string[];
  missingInMr: string[];
  extraInHi: string[];
  extraInMr: string[];
  missingByLocale: Record<string, string[]>;
  extraByLocale: Record<string, string[]>;
} {
  const enKeys = new Set(getDeepKeys(enIN));
  const missingByLocale: Record<string, string[]> = {};
  const extraByLocale: Record<string, string[]> = {};

  let allValid = true;

  for (const [locale, data] of Object.entries(ALL_LOCALES)) {
    if (locale === "en-IN") continue;
    const keys = new Set(getDeepKeys(data));
    const missing = [...enKeys].filter((k) => !keys.has(k));
    const extra = [...keys].filter((k) => !enKeys.has(k));

    missingByLocale[locale] = missing;
    extraByLocale[locale] = extra;

    if (missing.length > 0) {
      allValid = false;
    }
  }

  return {
    valid: allValid,
    totalKeys: enKeys.size,
    missingInHi: missingByLocale["hi-IN"] || [],
    missingInMr: missingByLocale["mr-IN"] || [],
    extraInHi: extraByLocale["hi-IN"] || [],
    extraInMr: extraByLocale["mr-IN"] || [],
    missingByLocale,
    extraByLocale,
  };
}
