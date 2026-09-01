import React, { createContext, useContext, useState, useEffect, useCallback, useMemo } from "react";
import { useTranslation } from "react-i18next";
import { i18n as I18nInstance } from "i18next";
import {
  SupportedLanguage,
  normalizeLanguageCode,
  getScopedLocaleStorageKey,
  resolveInitialLanguage,
  STORAGE_KEY_LANGUAGE,
  STORAGE_KEY_LANGUAGE_CONFIRMED,
  STORAGE_KEY_LANGUAGE_SYNC_PENDING,
} from "./config";
import defaultI18n from "./index";

export interface LanguageContextType {
  locale: SupportedLanguage;
  currentLanguage: SupportedLanguage;
  setLocale: (lang: SupportedLanguage | string) => Promise<void>;
  setLanguage: (lang: SupportedLanguage | string) => Promise<void>;
  t: (key: string, optionsOrFallback?: any, extraOptions?: any) => string;
  isChanging: boolean;
  i18n: I18nInstance;
}

export interface LanguageProviderProps {
  children: React.ReactNode;
  initialLanguage?: string | null;
  role?: string | null;
  userId?: string | null;
  fallback?: SupportedLanguage;
  onLanguageChange?: (lang: SupportedLanguage) => void | Promise<void>;
}

const LanguageContext = createContext<LanguageContextType | undefined>(undefined);

export const LanguageProvider: React.FC<LanguageProviderProps> = ({
  children,
  initialLanguage,
  role,
  userId,
  fallback = "en-IN",
  onLanguageChange,
}) => {
  const [currentLocale, setCurrentLocale] = useState<SupportedLanguage>(() => {
    return resolveInitialLanguage(initialLanguage, fallback, role, userId);
  });
  const [isChanging, setIsChanging] = useState<boolean>(false);

  // Keep i18next synchronized on mount and whenever locale changes
  useEffect(() => {
    const resolved = resolveInitialLanguage(initialLanguage, fallback, role, userId);
    if (resolved !== defaultI18n.language) {
      defaultI18n.changeLanguage(resolved);
    }
  }, [initialLanguage, fallback, role, userId]);

  // Synchronize when authenticated user profile changes
  useEffect(() => {
    if (initialLanguage) {
      const normalized = normalizeLanguageCode(initialLanguage, fallback);
      if (normalized !== currentLocale) {
        setCurrentLocale(normalized);
        defaultI18n.changeLanguage(normalized);
        const scopedKey = getScopedLocaleStorageKey(role, userId);
        if (typeof window !== "undefined" && window.localStorage) {
          localStorage.setItem(scopedKey, normalized);
          localStorage.setItem(STORAGE_KEY_LANGUAGE, normalized);
        }
      }
    }
  }, [initialLanguage, role, userId, fallback, currentLocale]);

  const setLocale = useCallback(
    async (newLang: SupportedLanguage | string) => {
      const normalized = normalizeLanguageCode(newLang, fallback);
      setIsChanging(true);
      try {
        setCurrentLocale(normalized);
        await defaultI18n.changeLanguage(normalized);

        if (typeof window !== "undefined" && window.localStorage) {
          const scopedKey = getScopedLocaleStorageKey(role, userId);
          localStorage.setItem(scopedKey, normalized);
          localStorage.setItem(STORAGE_KEY_LANGUAGE, normalized);
          localStorage.setItem("preferred_language", normalized);
          localStorage.setItem(STORAGE_KEY_LANGUAGE_CONFIRMED, "true");
        }

        if (onLanguageChange) {
          await onLanguageChange(normalized);
        }
      } catch (err) {
        console.error("Failed to change language", err);
      } finally {
        setIsChanging(false);
      }
    },
    [role, userId, fallback, onLanguageChange]
  );

  const setLanguage = setLocale;

  // Wrapped reactive translation function
  const t = useCallback(
    (key: string, optionsOrFallback?: any, extraOptions?: any): string => {
      if (typeof optionsOrFallback === "string") {
        return (defaultI18n.t(key, { defaultValue: optionsOrFallback, ...(extraOptions && typeof extraOptions === "object" ? extraOptions : {}) }) as string) || optionsOrFallback;
      }
      return (defaultI18n.t(key, optionsOrFallback) as string) || (typeof optionsOrFallback === "string" ? optionsOrFallback : key);
    },
    [currentLocale]
  );

  const contextValue = useMemo<LanguageContextType>(
    () => ({
      locale: currentLocale,
      currentLanguage: currentLocale,
      setLocale,
      setLanguage,
      t,
      isChanging,
      i18n: defaultI18n,
    }),
    [currentLocale, setLocale, setLanguage, t, isChanging]
  );

  return <LanguageContext.Provider value={contextValue}>{children}</LanguageContext.Provider>;
};

export function useLanguage(): LanguageContextType {
  const context = useContext(LanguageContext);
  if (!context) {
    // Graceful fallback if invoked outside of Provider
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
          return (defaultI18n.t(key, { defaultValue: optionsOrFallback, ...(extraOptions && typeof extraOptions === "object" ? extraOptions : {}) }) as string) || optionsOrFallback;
        }
        return (defaultI18n.t(key, optionsOrFallback) as string) || key;
      },
      isChanging: false,
      i18n: defaultI18n,
    };
  }
  return context;
}
