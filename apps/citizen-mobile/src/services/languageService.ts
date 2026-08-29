import { apiClient } from "@aarogya/api-client";
import {
  SupportedLanguage,
  normalizeLanguageCode,
  getScopedLocaleStorageKey,
  STORAGE_KEY_LANGUAGE,
  STORAGE_KEY_LANGUAGE_CONFIRMED,
  STORAGE_KEY_LANGUAGE_SYNC_PENDING,
} from "@aarogya/i18n";

export const STORAGE_KEY_LANG = "aarogya_citizen_lang";
export const STORAGE_KEY_LANG_CONFIRMED = STORAGE_KEY_LANGUAGE_CONFIRMED;
export const STORAGE_KEY_SYNC_QUEUE = STORAGE_KEY_LANGUAGE_SYNC_PENDING;

export type LanguageCode = SupportedLanguage;

export interface LanguageOption {
  code: LanguageCode;
  nativeName: string;
  englishLabel: string;
  subLabel?: string;
  enabled: boolean;
  ttsPhrase: string;
}

export const SUPPORTED_LANGUAGES: LanguageOption[] = [
  {
    code: "mr-IN",
    nativeName: "मराठी",
    englishLabel: "Marathi",
    enabled: true,
    ttsPhrase: "आरोग्य सहाय्यक वापरण्यासाठी मराठी निवडा"
  },
  {
    code: "hi-IN",
    nativeName: "हिंदी",
    englishLabel: "Hindi",
    enabled: true,
    ttsPhrase: "आरोग्य सहायक का उपयोग करने के लिए हिंदी चुनें"
  },
  {
    code: "en-IN",
    nativeName: "English",
    englishLabel: "English",
    subLabel: "इंग्रजी",
    enabled: true,
    ttsPhrase: "Choose English to use Aarogya Sahayak"
  }
];

export class LanguageService {
  /**
   * Resolves language preference in 4-tier order:
   * 1. Profile preference (if provided)
   * 2. Scoped Local storage preference (aarogya:locale:citizen)
   * 3. Browser language
   * 4. Fallback: mr-IN
   */
  static resolveLanguage(profileLang?: string): LanguageCode {
    if (profileLang) {
      return normalizeLanguageCode(profileLang, "mr-IN");
    }

    const scopedKey = getScopedLocaleStorageKey("citizen");
    const scopedVal = localStorage.getItem(scopedKey);
    if (scopedVal) {
      return normalizeLanguageCode(scopedVal, "mr-IN");
    }

    const legacyVal = localStorage.getItem(STORAGE_KEY_LANG) || localStorage.getItem(STORAGE_KEY_LANGUAGE);
    if (legacyVal) {
      return normalizeLanguageCode(legacyVal, "mr-IN");
    }

    const browserLang = navigator.language || (navigator as any).userLanguage || "";
    if (browserLang.startsWith("hi")) return "hi-IN";
    if (browserLang.startsWith("en")) return "en-IN";

    return "mr-IN";
  }

  static hasConfirmedPreference(): boolean {
    const scopedKey = getScopedLocaleStorageKey("citizen");
    return localStorage.getItem(STORAGE_KEY_LANG_CONFIRMED) === "true" || !!localStorage.getItem(scopedKey);
  }

  static saveLocalPreference(lang: LanguageCode): void {
    const normalized = normalizeLanguageCode(lang, "mr-IN");
    const scopedKey = getScopedLocaleStorageKey("citizen");
    localStorage.setItem(scopedKey, normalized);
    localStorage.setItem(STORAGE_KEY_LANG, normalized);
    localStorage.setItem(STORAGE_KEY_LANGUAGE, normalized);
    localStorage.setItem(STORAGE_KEY_LANG_CONFIRMED, "true");
  }

  static async syncPreferenceToBackend(lang: LanguageCode): Promise<{ success: boolean; offlineQueued: boolean }> {
    const normalized = normalizeLanguageCode(lang, "mr-IN");
    this.saveLocalPreference(normalized);

    if (!navigator.onLine) {
      localStorage.setItem(STORAGE_KEY_SYNC_QUEUE, normalized);
      return { success: false, offlineQueued: true };
    }

    try {
      await apiClient.updateCitizenLanguage(normalized);
      localStorage.removeItem(STORAGE_KEY_SYNC_QUEUE);
      return { success: true, offlineQueued: false };
    } catch (err) {
      // Backend unavailable or user not logged in yet -> Queue for sync
      localStorage.setItem(STORAGE_KEY_SYNC_QUEUE, normalized);
      return { success: false, offlineQueued: true };
    }
  }

  static async flushPendingSyncQueue(): Promise<void> {
    const pending = localStorage.getItem(STORAGE_KEY_SYNC_QUEUE) as LanguageCode | null;
    if (pending && navigator.onLine) {
      try {
        await apiClient.updateCitizenLanguage(normalizeLanguageCode(pending, "mr-IN"));
        localStorage.removeItem(STORAGE_KEY_SYNC_QUEUE);
      } catch (err) {
        // Will retry on next online event
      }
    }
  }

  static speakPhrase(phrase: string, langCode: LanguageCode): void {
    if ("speechSynthesis" in window && phrase) {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(phrase);
      utterance.lang = langCode.startsWith("mr") ? "mr-IN" : (langCode.startsWith("hi") ? "hi-IN" : "en-US");
      utterance.rate = 0.9;
      window.speechSynthesis.speak(utterance);
    }
  }
}

