import React, { createContext, useContext, useState, useEffect, useCallback, useMemo } from "react";
import {
  SupportedLanguage,
  resolveInitialLanguage,
  normalizeLanguageCode,
  getScopedLocaleStorageKey,
  STORAGE_KEY_LANGUAGE,
  STORAGE_KEY_LANGUAGE_CONFIRMED,
  defaultI18n,
} from "@aarogya/i18n";
import { useAuth } from "../auth/AuthContext";
import { apiClient } from "@aarogya/api-client";

export interface LanguageContextType {
  locale: SupportedLanguage;
  currentLanguage: SupportedLanguage;
  setLocale: (lang: SupportedLanguage | string) => Promise<void>;
  setLanguage: (lang: SupportedLanguage | string) => Promise<void>;
  t: (key: string, optionsOrFallback?: any, extraOptions?: any) => string;
  isChanging: boolean;
  i18n: typeof defaultI18n;
}

const LanguageContext = createContext<LanguageContextType | undefined>(undefined);

export const LanguageProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user } = useAuth();
  const role = user?.role?.toLowerCase() || null;
  const userId = user?.id || (user as any)?.username || null;


  const [currentLanguage, setCurrentLanguageState] = useState<SupportedLanguage>(() => {
    return resolveInitialLanguage(user?.preferred_language, "en-IN", role, userId);
  });
  const [isChanging, setIsChanging] = useState<boolean>(false);

  // Sync language when authenticated user changes or on initial profile fetch
  useEffect(() => {
    const resolved = resolveInitialLanguage(user?.preferred_language, "en-IN", role, userId);
    if (resolved !== currentLanguage) {
      setCurrentLanguageState(resolved);
      defaultI18n.changeLanguage(resolved);
      const scopedKey = getScopedLocaleStorageKey(role, userId);
      if (typeof window !== "undefined" && window.localStorage) {
        localStorage.setItem(scopedKey, resolved);
        localStorage.setItem(STORAGE_KEY_LANGUAGE, resolved);
        localStorage.setItem("preferred_language", resolved);
      }
    }
  }, [user?.preferred_language, role, userId]);

  const setLocale = useCallback(
    async (lang: SupportedLanguage | string) => {
      const normalized = normalizeLanguageCode(lang, "en-IN");
      setIsChanging(true);
      try {
        setCurrentLanguageState(normalized);
        await defaultI18n.changeLanguage(normalized);

        const scopedKey = getScopedLocaleStorageKey(role, userId);
        if (typeof window !== "undefined" && window.localStorage) {
          localStorage.setItem(scopedKey, normalized);
          localStorage.setItem(STORAGE_KEY_LANGUAGE, normalized);
          localStorage.setItem("preferred_language", normalized);
          localStorage.setItem(STORAGE_KEY_LANGUAGE_CONFIRMED, "true");
        }

        // If authenticated, persist to user profile in backend
        if (user) {
          try {
            await apiClient.updateUserPreferences(normalized);
            const storedUser = localStorage.getItem("aarogya_user");
            if (storedUser) {
              const parsed = JSON.parse(storedUser);
              parsed.preferred_language = normalized;
              localStorage.setItem("aarogya_user", JSON.stringify(parsed));
            }
          } catch (err) {
            console.warn("Failed to persist user language preference to backend", err);
          }
        }
      } finally {
        setIsChanging(false);
      }
    },
    [user, role, userId]
  );

  const setLanguage = setLocale;

  const t = useCallback(
    (key: string, optionsOrFallback?: any, extraOptions?: any): string => {
      if (typeof optionsOrFallback === "string") {
        return (defaultI18n.t(key, { defaultValue: optionsOrFallback, ...(extraOptions && typeof extraOptions === "object" ? extraOptions : {}) }) as string) || optionsOrFallback;
      }
      return (defaultI18n.t(key, optionsOrFallback) as string) || (typeof optionsOrFallback === "string" ? optionsOrFallback : key);
    },
    [currentLanguage]
  );

  const contextValue = useMemo<LanguageContextType>(
    () => ({
      locale: currentLanguage,
      currentLanguage,
      setLocale,
      setLanguage,
      t,
      isChanging,
      i18n: defaultI18n,
    }),
    [currentLanguage, setLocale, setLanguage, t, isChanging]
  );

  return <LanguageContext.Provider value={contextValue}>{children}</LanguageContext.Provider>;
};

export function useLanguage(): LanguageContextType {
  const context = useContext(LanguageContext);
  if (!context) {
    return {
      locale: (normalizeLanguageCode(defaultI18n.language) || "en-IN") as SupportedLanguage,
      currentLanguage: (normalizeLanguageCode(defaultI18n.language) || "en-IN") as SupportedLanguage,
      setLocale: async (lang) => {
        const normalized = normalizeLanguageCode(lang);
        await defaultI18n.changeLanguage(normalized);
      },
      setLanguage: async (lang) => {
        const normalized = normalizeLanguageCode(lang);
        await defaultI18n.changeLanguage(normalized);
      },
      t: (key: string, optionsOrFallback?: any, extraOptions?: any): string => {
        if (typeof optionsOrFallback === "string") {
          return (defaultI18n.t(key, { defaultValue: optionsOrFallback, ...extraOptions }) as string) || optionsOrFallback;
        }
        return (defaultI18n.t(key, optionsOrFallback) as string) || key;
      },
      isChanging: false,
      i18n: defaultI18n,
    };
  }
  return context;
}

