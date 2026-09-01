export type SupportedLanguage =
  | "en-IN"
  | "hi-IN"
  | "mr-IN"
  | "gu-IN"
  | "bn-IN"
  | "kn-IN"
  | "te-IN"
  | "ta-IN"
  | "ml-IN"
  | "pa-IN"
  | "od-IN";

export interface LanguageMeta {
  code: SupportedLanguage;
  name: string; // Native name in respective script
  englishName: string;
  subLabel?: string;
  region?: string;
  direction?: "ltr" | "rtl";
  voiceAvailable?: boolean;
  ttsPhrase?: string;
  isDefault?: boolean;
}

export const SUPPORTED_LANGUAGES: LanguageMeta[] = [
  {
    code: "en-IN",
    name: "English",
    englishName: "English",
    subLabel: "English",
    region: "National",
    direction: "ltr",
    voiceAvailable: true,
    ttsPhrase: "Choose English to use Aarogya Sahayak",
  },
  {
    code: "hi-IN",
    name: "हिंदी",
    englishName: "Hindi",
    subLabel: "Hindi",
    region: "National",
    direction: "ltr",
    voiceAvailable: true,
    ttsPhrase: "आरोग्य सहायक का उपयोग करने के लिए हिंदी चुनें",
  },
  {
    code: "mr-IN",
    name: "मराठी",
    englishName: "Marathi",
    subLabel: "Marathi",
    region: "Maharashtra",
    direction: "ltr",
    voiceAvailable: true,
    ttsPhrase: "आरोग्य सहाय्यक वापरण्यासाठी मराठी निवडा",
    isDefault: true,
  },
  {
    code: "gu-IN",
    name: "ગુજરાતી",
    englishName: "Gujarati",
    subLabel: "Gujarati",
    region: "Gujarat",
    direction: "ltr",
    voiceAvailable: true,
    ttsPhrase: "આરોગ્ય સહાયક વાપરવા માટે ગુજરાતી પસંદ કરો",
  },
  {
    code: "bn-IN",
    name: "বাংলা",
    englishName: "Bengali",
    subLabel: "Bengali",
    region: "West Bengal",
    direction: "ltr",
    voiceAvailable: true,
    ttsPhrase: "আরোগ্য সহায়ক ব্যবহার করার জন্য বাংলা বেছে নিন",
  },
  {
    code: "kn-IN",
    name: "ಕನ್ನಡ",
    englishName: "Kannada",
    subLabel: "Kannada",
    region: "Karnataka",
    direction: "ltr",
    voiceAvailable: true,
    ttsPhrase: "ಆರೋಗ್ಯ ಸಹಾಯಕ ಬಳಸಲು ಕನ್ನಡ ಆಯ್ಕೆಮಾಡಿ",
  },
  {
    code: "te-IN",
    name: "తెలుగు",
    englishName: "Telugu",
    subLabel: "Telugu",
    region: "Andhra Pradesh / Telangana",
    direction: "ltr",
    voiceAvailable: true,
    ttsPhrase: "ఆరోగ్య సహాయక్ ఉపయోగించడానికి తెలుగు ఎంచుకోండి",
  },
  {
    code: "ta-IN",
    name: "தமிழ்",
    englishName: "Tamil",
    subLabel: "Tamil",
    region: "Tamil Nadu",
    direction: "ltr",
    voiceAvailable: true,
    ttsPhrase: "ஆரோக்ய சஹாயக்கைப் பயன்படுத்த தமிழைத் தேர்வு செய்யவும்",
  },
  {
    code: "ml-IN",
    name: "മലയാളം",
    englishName: "Malayalam",
    subLabel: "Malayalam",
    region: "Kerala",
    direction: "ltr",
    voiceAvailable: true,
    ttsPhrase: "ആരോഗ്യ സഹായക് ഉപയോഗിക്കാൻ മലയാളം തിരഞ്ഞെടുക്കുക",
  },
  {
    code: "pa-IN",
    name: "ਪੰਜਾਬੀ",
    englishName: "Punjabi",
    subLabel: "Punjabi",
    region: "Punjab",
    direction: "ltr",
    voiceAvailable: true,
    ttsPhrase: "ਅਰੋਗਿਆ ਸਹਾਇਕ ਦੀ ਵਰਤੋਂ ਕਰਨ ਲਈ ਪੰਜਾਬੀ ਚੁਣੋ",
  },
  {
    code: "od-IN",
    name: "ଓଡ଼ିଆ",
    englishName: "Odia",
    subLabel: "Odia",
    region: "Odisha",
    direction: "ltr",
    voiceAvailable: true,
    ttsPhrase: "ଆରୋଗ୍ୟ ସହାୟକ ବ୍ୟବହାର କରିବା ପାଇଁ ଓଡ଼ିଆ ବାଛନ୍ତୁ",
  },
];

export const STORAGE_KEY_LANGUAGE = "aarogya_preferred_language";
export const STORAGE_KEY_LANGUAGE_CONFIRMED = "aarogya_language_confirmed";
export const STORAGE_KEY_LANGUAGE_SYNC_PENDING = "aarogya_language_sync_pending";

/**
 * Normalizes any language code format (e.g., 'en', 'hi', 'mr', 'gu', 'bn', 'kn', 'te', 'ta', 'ml', 'pa', 'od')
 * to standard Indian BCP-47 locales ('en-IN', 'hi-IN', 'mr-IN', etc.).
 */
export function normalizeLanguageCode(lang?: string | null, fallback: SupportedLanguage = "en-IN"): SupportedLanguage {
  if (!lang) return fallback;
  const cleaned = String(lang).trim().toLowerCase();
  if (cleaned.startsWith("hi") || cleaned === "hindi") return "hi-IN";
  if (cleaned.startsWith("mr") || cleaned === "marathi") return "mr-IN";
  if (cleaned.startsWith("gu") || cleaned === "gujarati") return "gu-IN";
  if (cleaned.startsWith("bn") || cleaned.startsWith("ben") || cleaned === "bengali") return "bn-IN";
  if (cleaned.startsWith("kn") || cleaned.startsWith("kan") || cleaned === "kannada") return "kn-IN";
  if (cleaned.startsWith("te") || cleaned.startsWith("tel") || cleaned === "telugu") return "te-IN";
  if (cleaned.startsWith("ta") || cleaned.startsWith("tam") || cleaned === "tamil") return "ta-IN";
  if (cleaned.startsWith("ml") || cleaned.startsWith("mal") || cleaned === "malayalam") return "ml-IN";
  if (cleaned.startsWith("pa") || cleaned.startsWith("pan") || cleaned === "punjabi") return "pa-IN";
  if (cleaned.startsWith("od") || cleaned.startsWith("or") || cleaned === "odia" || cleaned === "oriya") return "od-IN";
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
    const matched = normalizeLanguageCode(navLang, fallback);
    if (matched) return matched;
  }

  return fallback;
}

export function getSpeechLocale(lang: SupportedLanguage): string {
  switch (lang) {
    case "mr-IN":
      return "mr-IN";
    case "hi-IN":
      return "hi-IN";
    case "gu-IN":
      return "gu-IN";
    case "bn-IN":
      return "bn-IN";
    case "kn-IN":
      return "kn-IN";
    case "te-IN":
      return "te-IN";
    case "ta-IN":
      return "ta-IN";
    case "ml-IN":
      return "ml-IN";
    case "pa-IN":
      return "pa-IN";
    case "od-IN":
      return "od-IN";
    case "en-IN":
    default:
      return "en-IN";
  }
}

export function getLanguageBadgeLabel(lang?: string | null): string {
  const normalized = normalizeLanguageCode(lang);
  switch (normalized) {
    case "hi-IN":
      return "हि";
    case "mr-IN":
      return "म";
    case "gu-IN":
      return "ગુ";
    case "bn-IN":
      return "বা";
    case "kn-IN":
      return "ಕ";
    case "te-IN":
      return "తె";
    case "ta-IN":
      return "த";
    case "ml-IN":
      return "മ";
    case "pa-IN":
      return "ਪ";
    case "od-IN":
      return "ଓ";
    case "en-IN":
    default:
      return "EN";
  }
}


