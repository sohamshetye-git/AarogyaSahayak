export type SupportedLanguage = "en-IN" | "hi-IN" | "mr-IN";

export interface LanguageMeta {
  code: SupportedLanguage;
  name: string; // Native name
  englishName: string;
  subLabel?: string;
  isDefault?: boolean;
}

export const SUPPORTED_LANGUAGES: LanguageMeta[] = [
  {
    code: "mr-IN",
    name: "मराठी",
    englishName: "Marathi",
    isDefault: true,
  },
  {
    code: "hi-IN",
    name: "हिंदी",
    englishName: "Hindi",
  },
  {
    code: "en-IN",
    name: "English",
    englishName: "English",
    subLabel: "इंग्रजी",
  },
];

export const STORAGE_KEY_LANGUAGE = "aarogya_preferred_language";
export const STORAGE_KEY_LANGUAGE_CONFIRMED = "aarogya_language_confirmed";
export const STORAGE_KEY_LANGUAGE_SYNC_PENDING = "aarogya_language_sync_pending";

/**
 * Normalizes any language code format (e.g., 'en', 'en-US', 'hi', 'mr')
 * to standard Indian locales ('en-IN', 'hi-IN', 'mr-IN').
 */
export function normalizeLanguageCode(lang?: string | null, fallback: SupportedLanguage = "en-IN"): SupportedLanguage {
  if (!lang) return fallback;
  const cleaned = String(lang).trim().toLowerCase();
  if (cleaned.startsWith("hi") || cleaned === "hindi") return "hi-IN";
  if (cleaned.startsWith("mr") || cleaned === "marathi") return "mr-IN";
  if (cleaned.startsWith("en") || cleaned === "english") return "en-IN";
  return fallback;
}

/**
 * Returns scoped storage key for language preference isolation:
 * - Authenticated user: aarogya:locale:<role>:<userId>
 * - Role-only: aarogya:locale:<role>
 * - Guest/pre-auth: aarogya:locale:guest
 */
export function getScopedLocaleStorageKey(role?: string | null, userId?: string | null): string {
  if (role && userId) {
    return `aarogya:locale:${role.toLowerCase()}:${userId}`;
  }
  if (role) {
    return `aarogya:locale:${role.toLowerCase()}`;
  }
  return "aarogya:locale:guest";
}

/**
 * Four-tier language resolution:
 * 1. Authenticated user profile preference
 * 2. Scoped Local storage cached preference (role/userId or guest)
 * 3. Browser / Device language
 * 4. Fallback (en-IN or mr-IN depending on platform default)
 */
export function resolveInitialLanguage(
  userPref?: string | null,
  fallback: SupportedLanguage = "mr-IN",
  role?: string | null,
  userId?: string | null
): SupportedLanguage {
  if (userPref) {
    const normalized = normalizeLanguageCode(userPref);
    if (normalized) return normalized;
  }

  if (typeof window !== "undefined" && window.localStorage) {
    const scopedKey = getScopedLocaleStorageKey(role, userId);
    const cachedScoped = localStorage.getItem(scopedKey);
    if (cachedScoped) {
      return normalizeLanguageCode(cachedScoped, fallback);
    }
    
    // Legacy fallback keys
    const cached = localStorage.getItem(STORAGE_KEY_LANGUAGE) || localStorage.getItem("preferred_language");
    if (cached) {
      return normalizeLanguageCode(cached, fallback);
    }
  }

  if (typeof navigator !== "undefined") {
    const navLang = navigator.language || (navigator as any).userLanguage || "";
    if (navLang.startsWith("mr")) return "mr-IN";
    if (navLang.startsWith("hi")) return "hi-IN";
    if (navLang.startsWith("en")) return "en-IN";
  }

  return fallback;
}

export function getSpeechLocale(lang: SupportedLanguage): string {
  switch (lang) {
    case "mr-IN":
      return "mr-IN";
    case "hi-IN":
      return "hi-IN";
    case "en-IN":
    default:
      return "en-IN";
  }
}

